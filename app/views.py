import json
import os
from datetime import timedelta
from pathlib import Path

from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from app import paths
from app.emails import helper as emails
from app.exports import bundle
from app.profiles.env_mapping import import_dotenv, provided_fields
from app.profiles.forms import STEP_KEYS, STEPS
from app.profiles.models import Profile
from app.runs import worker
from app.runs.models import ScraperRun
from app.scrapers import registry
from app.submissions.models import SubmittedRequest
from src.state_privacy_request_factory.states_that_have_privacy_laws import StateHasPrivacyLaws

REPO_ENV = paths.REPO_ROOT / ".env"


def _state_has_law(state: str) -> bool:
    try:
        return StateHasPrivacyLaws[state.upper().replace(" ", "_")].value
    except KeyError:
        return False


def welcome(request):
    p = Profile.current()
    return render(request, "welcome.html", {"profile": p, "env_available": REPO_ENV.exists() and bool(os.environ.get("BROKER_POKER_DEV"))})


def step(request, key):
    if key not in STEP_KEYS:
        raise Http404
    idx = STEP_KEYS.index(key)
    _, title, Form = STEPS[idx]
    profile = Profile.current()
    data = profile.data
    initial = {**data, "delete_enabled": profile.delete_enabled, "captcha_mode": profile.captcha_mode}
    if request.method == "POST":
        form = Form(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            if key == "rights":
                profile.delete_enabled = bool(cd["delete_enabled"])
            elif key == "captcha":
                profile.captcha_mode = cd["captcha_mode"]
            else:
                data.update({k: (v or "").strip() for k, v in cd.items()})
                profile.data = data
            if idx == len(STEPS) - 1:
                profile.complete = True
            profile.save()  # saved after every step so closing the app loses nothing
            if idx == len(STEPS) - 1:
                return redirect("summary")
            return redirect("step", key=STEP_KEYS[idx + 1])
    else:
        form = Form(initial=initial)
    state = data.get("STATE", "")
    return render(request, "step.html", {
        "form": form, "title": title, "key": key, "n": idx + 1, "total": len(STEPS),
        "prev": STEP_KEYS[idx - 1] if idx else None,
        "no_law_warning": key == "rights" and bool(state) and not _state_has_law(state), "state": state})


def _site_rows(profile):
    infos = registry.all_scrapers()
    skip = profile.captcha_mode == "skip"
    rows = []
    for i in infos:
        reason = i.skip_reason if not i.runnable else ("CAPTCHA/verification needed — skip mode is on." if skip and i.needs_human else "")
        rows.append({"info": i, "skipped": bool(reason), "reason": reason})
    rows.sort(key=lambda r: (r["skipped"], not r["info"].needs_human, r["info"].slug))
    return rows


def summary(request):
    profile = Profile.current()
    if not profile.complete:
        return redirect("step", key="identity")
    data = profile.data
    if request.method == "POST":
        dry = request.POST.get("mode") != "live"
        if not dry and request.POST.get("confirm_live") != "on":
            return redirect("summary")
        only = [s.strip() for s in request.POST.get("only", "").split(",") if s.strip()] or None
        run = worker.create_run(profile, dry_run=dry, only_slugs=only)
        worker.start_run(run.id)
        return redirect("run", run_id=run.id)
    rows = _site_rows(profile)
    batches = emails.batches()
    return render(request, "summary.html", {
        "profile": profile, "data": data, "rows": rows,
        "n_run": sum(not r["skipped"] for r in rows), "n_skip": sum(r["skipped"] for r in rows),
        "n_human": sum(1 for r in rows if not r["skipped"] and r["info"].needs_human),
        "email_batches": [{"n": n + 1, "to": ", ".join(b), "count": len(b), "mailto": emails.mailto(b)}
                          for n, b in enumerate(batches)],
        "email_subject": emails.subject(), "email_body": emails.body(data, profile.delete_enabled),
        "email_state_warning": data.get("STATE", "").lower() != "minnesota",
        "no_law": not _state_has_law(data.get("STATE", "")),
        "fields": provided_fields(data), "previous_runs": ScraperRun.objects.order_by("-id")[:5]})


@ensure_csrf_cookie
def run_page(request, run_id):
    run = get_object_or_404(ScraperRun, pk=run_id)
    if run.status in ("complete", "cancelled") and request.GET.get("live") != "1":
        return redirect("done", run_id=run.id)
    return render(request, "run.html", {"run": run, "sites": run.sites.all()})


def done(request, run_id):
    run = get_object_or_404(ScraperRun, pk=run_id)
    sites = list(run.sites.all())
    c = {k: sum(s.status == k for s in sites) for k in ("completed", "failed", "skipped")}
    followups = [s for s in sites if s.status != "completed" or (run.dry_run)]
    profile = Profile.current()
    return render(request, "done.html", {
        "run": run, "sites": sites, "c": c, "total": len(sites), "profile": profile,
        "email_batches": [{"n": n + 1, "count": len(b), "mailto": emails.mailto(b)} for n, b in enumerate(emails.batches())],
        "followups": len(followups)})


def screenshot(request, run_id, slug, name):
    base = (paths.runs_dir() / f"run_{run_id}" / slug).resolve()
    target = (base / name).resolve()
    if base not in target.parents or target.suffix != ".png" or not target.is_file():
        raise Http404
    return FileResponse(open(target, "rb"), content_type="image/png")


def reminders(request, run_id):
    run = get_object_or_404(ScraperRun, pk=run_id)
    months = 12 if request.GET.get("months") == "12" else 6
    when = (timezone.now() + timedelta(days=30 * months)).strftime("%Y%m%d")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Broker Poker//EN"]
    # Only sites where opt-out AND delete weren't both completed need a follow-up.
    for s in run.sites.exclude(status="skipped", note__startswith="Already"):
        if run.dry_run or s.status != "completed" or "delete" not in (s.rights_used or []):
            lines += ["BEGIN:VEVENT", f"UID:bp-{run.id}-{s.slug}@broker-poker", f"DTSTAMP:{timezone.now():%Y%m%dT%H%M%SZ}",
                      f"DTSTART;VALUE=DATE:{when}",
                      f"SUMMARY:Follow up with {s.display_name} (privacy request)", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    resp = HttpResponse("\r\n".join(lines) + "\r\n", content_type="text/calendar")
    resp["Content-Disposition"] = f'attachment; filename="broker-poker-{months}mo.ics"'
    return resp


def export_profile(request):
    profile = Profile.current()
    if request.method == "POST":
        pw, plain = request.POST.get("password", ""), request.POST.get("plaintext") == "on"
        if not plain and len(pw) < 8:
            return render(request, "export.html", {"error": "Choose a password of at least 8 characters, or tick plaintext."})
        run_id = request.POST.get("run_id")
        runs = None
        if run_id:
            runs = [{"id": r.id, "dry_run": r.dry_run, "status": r.status, "started": str(r.started_at),
                     "sites": [{"slug": s.slug, "status": s.status, "note": s.note, "rights": s.rights_used,
                                "fields": s.fields_available} for s in r.sites.all()]}
                    for r in ScraperRun.objects.filter(status__in=["complete", "cancelled"])]
        blob = bundle.export_bundle({"profile": profile.data, "settings": {
            "delete_enabled": profile.delete_enabled, "captcha_mode": profile.captcha_mode}}, None if plain else pw, runs)
        resp = HttpResponse(blob, content_type="application/zip")
        resp["Content-Disposition"] = 'attachment; filename="broker_poker_export.zip"'
        return resp
    return render(request, "export.html", {"run_id": request.GET.get("run")})


def import_profile(request):
    ctx = {}
    if request.method == "POST" and request.FILES.get("file"):
        blob = request.FILES["file"].read(20_000_000)
        try:
            doc = bundle.import_bundle(blob, request.POST.get("password") or None)
            p = Profile.current()
            p.data = doc["profile"]
            p.delete_enabled = bool(doc.get("settings", {}).get("delete_enabled"))
            p.captcha_mode = doc.get("settings", {}).get("captcha_mode", "solve")
            p.complete = True
            p.save()
            return redirect("summary")
        except (bundle.BundleError, KeyError) as e:
            ctx["error"] = str(e) if isinstance(e, bundle.BundleError) else "The export is incomplete."
    return render(request, "import.html", ctx)


@require_POST
def import_env(request):
    if not (REPO_ENV.exists() and os.environ.get("BROKER_POKER_DEV")):
        raise Http404
    p = Profile.current()
    p.data = import_dotenv(REPO_ENV)
    p.complete = True
    p.save()
    return redirect("summary")


def history(request):
    if request.method == "POST":
        SubmittedRequest.objects.filter(slug=request.POST.get("slug")).delete()
        return redirect("history")
    return render(request, "history.html", {"rows": SubmittedRequest.objects.order_by("slug")})

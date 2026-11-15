"""Sequential run worker: one scraper at a time (see design doc §10)."""
from __future__ import annotations

import os
import threading
import time

from django.db import close_old_connections
from django.utils import timezone

from app import paths
from app.profiles.env_mapping import profile_to_env, provided_fields
from app.profiles.models import Profile
from app.runs import runner
from app.runs.models import CaptchaSession, ScraperRun, SiteRunStatus
from app.scrapers import registry
from app.submissions.models import SubmittedRequest

SITE_TIMEOUT = float(os.environ.get("BP_SITE_TIMEOUT", "300"))
_threads: dict[int, threading.Thread] = {}


def create_run(profile: Profile, *, dry_run=True, only_slugs=None) -> ScraperRun:
    run = ScraperRun.objects.create(dry_run=dry_run, delete_enabled=profile.delete_enabled,
                                    captcha_mode=profile.captcha_mode, only_slugs=only_slugs)
    infos = registry.all_scrapers()
    if only_slugs:
        infos = [i for i in infos if i.slug in set(only_slugs)]
    skip_mode = run.captcha_mode == "skip"
    runnable = [i for i in infos if i.runnable and not (skip_mode and i.needs_human)]
    skipped = [i for i in infos if i not in runnable]
    # Human-attention sites first (solve mode) so the user can walk away afterwards.
    runnable.sort(key=lambda i: (not i.needs_human, i.slug))
    fields = provided_fields(profile.data)
    rows = []
    for n, i in enumerate(runnable):
        rows.append(SiteRunStatus(run=run, slug=i.slug, display_name=i.display_name, order=n,
                                  needs_human=i.needs_human, fields_available=fields))
    for n, i in enumerate(skipped, start=len(runnable)):
        reason = "CAPTCHA/verification required, skip mode selected." if i.runnable else i.skip_reason
        rows.append(SiteRunStatus(run=run, slug=i.slug, display_name=i.display_name, order=n,
                                  needs_human=i.needs_human, status="skipped", note=reason))
    SiteRunStatus.objects.bulk_create(rows)
    return run


def _rights(run: ScraperRun) -> list:
    r = ["access", "opt_out", "list_of_third_parties"]
    return r + ["delete"] if run.delete_enabled else r


def _wait_for_user(site: SiteRunStatus, prompt: str, kind: str):
    cs = CaptchaSession.objects.create(site_run=site, kind=kind, prompt=prompt)
    SiteRunStatus.objects.filter(pk=site.pk).update(status="waiting_captcha")
    deadline = time.monotonic() + runner.WAIT_LIMIT_SECONDS
    while time.monotonic() < deadline:
        cs.refresh_from_db()
        if cs.status == "answered":
            SiteRunStatus.objects.filter(pk=site.pk).update(status="in_progress")
            return cs.answer
        if ScraperRun.objects.filter(pk=site.run_id, cancel_requested=True).exists():
            break
        time.sleep(0.5)
    cs.status = "timed_out"
    cs.save(update_fields=["status"])
    return None


def process_run(run_id: int) -> None:
    """Synchronous body of the worker (the thread target)."""
    run = ScraperRun.objects.get(pk=run_id)
    profile = Profile.current()
    data = profile.data
    run.status, run.started_at = "running", timezone.now()
    run.save(update_fields=["status", "started_at"])
    for site in list(run.sites.filter(status="pending")):
        if ScraperRun.objects.filter(pk=run_id, cancel_requested=True).exists():
            break
        info = registry.get(site.slug)
        if info is None:
            site.status, site.note = "skipped", "Scraper no longer exists."
            site.save()
            continue
        if not run.dry_run:
            _, created = SubmittedRequest.objects.get_or_create(slug=site.slug, defaults={"run_id": run.id})
            if not created:
                site.status, site.note = "skipped", "Already submitted once — blocked to avoid a duplicate request."
                site.save()
                continue
        headless = not site.needs_human
        env = profile_to_env(data, dry_run=run.dry_run, delete=run.delete_enabled, headless=headless)
        site.status, site.started_at, site.rights_used = "in_progress", timezone.now(), _rights(run)
        site.save()
        cwd = paths.runs_dir() / f"run_{run.id}" / site.slug
        result = runner.run_scraper(
            info.path, env, cwd, no_human=run.captcha_mode == "skip", timeout=SITE_TIMEOUT,
            on_wait=lambda p, k, s=site: _wait_for_user(s, p, k),
            should_cancel=lambda: ScraperRun.objects.filter(pk=run_id, cancel_requested=True).exists())
        site.status, site.note, site.warnings = result.status, result.note, result.warnings
        site.screenshots, site.log_tail, site.finished_at = result.screenshots, result.log_tail, timezone.now()
        site.save()
    run.refresh_from_db()
    # Anything still pending after a cancel is marked skipped.
    run.sites.filter(status__in=["pending"]).update(status="skipped", note="Run cancelled.")
    run.status = "cancelled" if run.cancel_requested else "complete"
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "finished_at"])


def _thread_main(run_id: int) -> None:
    try:
        process_run(run_id)
    finally:
        close_old_connections()


def start_run(run_id: int) -> None:
    t = threading.Thread(target=_thread_main, args=(run_id,), daemon=True, name=f"run-{run_id}")
    _threads[run_id] = t
    t.start()


def recover_interrupted() -> None:
    """On launch: a run left 'running' by a closed app is resumable; rows left in progress failed."""
    SiteRunStatus.objects.filter(status__in=["in_progress", "waiting_captcha"]).update(
        status="failed", note="Interrupted (app was closed during this site).")
    for run in ScraperRun.objects.filter(status="running"):
        start_run(run.id)

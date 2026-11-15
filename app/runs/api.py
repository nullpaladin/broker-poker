from datetime import datetime

from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework.authentication import BaseAuthentication, SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from app.runs.models import CaptchaSession, ScraperRun, SiteRunStatus


class CsrfProtected(BaseAuthentication):
    """DRF views are csrf_exempt and there are no users here, so enforce Django's CSRF check
    explicitly on unsafe methods — otherwise any website open in the browser could POST to the
    local API (answer a CAPTCHA prompt, cancel a run)."""

    def authenticate(self, request):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            SessionAuthentication().enforce_csrf(request)
        return None


def site_dict(s: SiteRunStatus) -> dict:
    cs = s.captchas.filter(status="waiting").first()
    return {
        "id": s.id, "slug": s.slug, "name": s.display_name, "status": s.status, "note": s.note,
        "warnings": s.warnings, "needs_human": s.needs_human, "rights": s.rights_used,
        "fields": s.fields_available, "screenshots": s.screenshots, "log_tail": s.log_tail,
        "updated_at": s.updated_at.isoformat(),
        "captcha": {"id": cs.id, "kind": cs.kind, "prompt": cs.prompt} if cs else None,
    }


def counts(run: ScraperRun) -> dict:
    c = {k: 0 for k, _ in SiteRunStatus.STATUS}
    for s in run.sites.values_list("status", flat=True):
        c[s] += 1
    c["total"] = sum(c.values())
    return c


class RunStatus(APIView):
    def get(self, request, run_id):
        run = get_object_or_404(ScraperRun, pk=run_id)
        qs = run.sites.all()
        since = parse_datetime(request.query_params.get("since", ""))
        if since:
            qs = qs.filter(updated_at__gt=since)
        w = run.sites.filter(status="waiting_captcha").first()
        return Response({"run": {"id": run.id, "status": run.status, "dry_run": run.dry_run},
                         "counts": counts(run), "sites": [site_dict(s) for s in qs],
                         "waiting": site_dict(w) if w else None})


class CaptchaAnswer(APIView):
    authentication_classes = [CsrfProtected]

    def post(self, request, run_id, captcha_id):
        cs = get_object_or_404(CaptchaSession, pk=captcha_id, site_run__run_id=run_id)
        if cs.status != "waiting":
            return Response({"error": "already handled"}, status=409)
        answer = str(request.data.get("answer", ""))[:255]
        if cs.kind == "text" and not answer.strip():
            return Response({"error": "An answer is required."}, status=400)
        cs.answer, cs.status = answer, "answered"
        cs.save(update_fields=["answer", "status"])
        return Response({"ok": True})


class CancelRun(APIView):
    authentication_classes = [CsrfProtected]

    def post(self, request, run_id):
        ScraperRun.objects.filter(pk=run_id).update(cancel_requested=True)
        return Response({"ok": True})

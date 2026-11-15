import json
from pathlib import Path

import pytest
from django.test import Client

from app.profiles.models import Profile
from app.runs.models import CaptchaSession, ScraperRun, SiteRunStatus
from app.submissions.models import SubmittedRequest

FX = Path(__file__).parent / "fixtures"


@pytest.fixture
def client():
    return Client(enforce_csrf_checks=True)


def csrf_post(c, url, data=None, **kw):
    c.get("/import/")  # form page sets the csrf cookie
    token = c.cookies["csrftoken"].value
    return c.post(url, {**(data or {}), "csrfmiddlewaretoken": token}, **kw)


def test_pages_render(db, client):
    assert client.get("/").status_code == 200
    for k in ("identity", "address", "contact", "optional", "rights", "captcha"):
        assert client.get(f"/setup/{k}/").status_code == 200
    assert client.get("/history/").status_code == 200 and client.get("/import/").status_code == 200
    assert client.get("/setup/nope/").status_code == 404


def test_post_without_csrf_rejected(db, client):
    assert client.post("/setup/identity/", {"FIRST_NAME": "x"}).status_code == 403


def test_setup_flow_saves_each_step_encrypted(db, client):
    r = csrf_post(client, "/setup/identity/", {"FIRST_NAME": "Jo", "LAST_NAME": "Doe"})
    assert r.status_code == 302 and r["Location"].endswith("/setup/address/")
    assert Profile.current().data["FIRST_NAME"] == "Jo"  # saved immediately
    assert csrf_post(client, "/setup/identity/", {"FIRST_NAME": ""}).status_code == 200  # validation
    csrf_post(client, "/setup/address/", {"ADDRESS": "1 Main", "CITY": "X", "STATE": "Minnesota", "ZIP_CODE": "55101"})
    csrf_post(client, "/setup/contact/", {"EMAIL": "a@b.co", "PHONE_NUMBER": "651-555-0100"})
    csrf_post(client, "/setup/optional/", {})
    csrf_post(client, "/setup/rights/", {"delete_enabled": "on"})
    r = csrf_post(client, "/setup/captcha/", {"captcha_mode": "skip"})
    p = Profile.current()
    assert r["Location"] == "/summary/" and p.complete and p.delete_enabled and p.captcha_mode == "skip"
    assert p.state == "Minnesota" and b"a@b.co" not in bytes(p.encrypted_pii)
    s = client.get("/summary/")
    assert s.status_code == 200 and b"Practice run" in s.content and b"Batch 1" in s.content


def test_summary_requires_profile(db, client):
    assert client.get("/summary/").status_code == 302


def test_live_requires_confirmation(db, client):
    p = Profile.current(); p.data = {"STATE": "Minnesota"}; p.complete = True; p.save()
    r = csrf_post(client, "/summary/", {"mode": "live"})
    assert r.status_code == 302 and ScraperRun.objects.count() == 0


def test_api_and_captcha_answer(db, client):
    run = ScraperRun.objects.create(status="running")
    s = SiteRunStatus.objects.create(run=run, slug="a", display_name="a.com", status="waiting_captcha")
    cs = CaptchaSession.objects.create(site_run=s, kind="text", prompt="code")
    d = client.get(f"/api/runs/{run.id}/status/").json()
    assert d["waiting"]["captcha"]["id"] == cs.id and d["counts"]["waiting_captcha"] == 1
    url = f"/api/runs/{run.id}/captcha/{cs.id}/answer/"
    client.get(f"/runs/{run.id}/?live=1")
    tok = client.cookies["csrftoken"].value
    hdr = {"HTTP_X_CSRFTOKEN": tok}
    assert client.post(url, json.dumps({"answer": ""}), content_type="application/json", **hdr).status_code == 400
    assert client.post(url, json.dumps({"answer": "xyz"}), content_type="application/json", **hdr).status_code == 200
    cs.refresh_from_db()
    assert cs.status == "answered" and cs.answer == "xyz"
    assert client.post(url, json.dumps({"answer": "again"}), content_type="application/json", **hdr).status_code == 409
    since = d["sites"][0]["updated_at"]
    assert client.get(f"/api/runs/{run.id}/status/", {"since": since}).json()["sites"] == []


def test_screenshot_path_traversal_blocked(db, client, tmp_path):
    from app import paths
    d = paths.runs_dir() / "run_1" / "a"; d.mkdir(parents=True)
    (d / "ok.png").write_bytes(b"\x89PNG")
    (paths.runs_dir() / "run_1" / "secret.png").write_bytes(b"x")
    assert client.get("/runs/1/shot/a/ok.png").status_code == 200
    assert client.get("/runs/1/shot/a/../secret.png").status_code == 404
    assert client.get("/runs/1/shot/a/%2e%2e/secret.png").status_code == 404


def test_export_import_via_views(db, client):
    p = Profile.current(); p.data = {"EMAIL": "a@b.co", "STATE": "Iowa"}; p.complete = True; p.save()
    r = csrf_post(client, "/export/", {"password": "longenough"})
    assert r.status_code == 200 and r["Content-Type"] == "application/zip"
    assert csrf_post(client, "/export/", {"password": "short"}).status_code == 200
    Profile.objects.all().delete()
    from django.core.files.uploadedfile import SimpleUploadedFile
    f = SimpleUploadedFile("e.zip", r.content)
    bad = csrf_post(client, "/import/", {"file": f, "password": "wrong"})
    assert b"Wrong password" in bad.content
    ok = csrf_post(client, "/import/", {"file": SimpleUploadedFile("e.zip", r.content), "password": "longenough"})
    assert ok.status_code == 302 and Profile.current().data["EMAIL"] == "a@b.co"


def test_history_reset_and_reminders(db, client):
    SubmittedRequest.objects.create(slug="zzz")
    assert csrf_post(client, "/history/", {"slug": "zzz"}).status_code == 302
    assert SubmittedRequest.objects.count() == 0
    run = ScraperRun.objects.create(status="complete", dry_run=False)
    SiteRunStatus.objects.create(run=run, slug="a", display_name="a.com", status="completed", rights_used=["access"])
    SiteRunStatus.objects.create(run=run, slug="b", display_name="b.com", status="completed", rights_used=["access", "delete"])
    ics = client.get(f"/runs/{run.id}/reminders.ics").content.decode()
    assert "a.com" in ics and "b.com" not in ics


def test_api_posts_enforce_csrf(db, client):
    run = ScraperRun.objects.create(status="running")
    r = client.post(f"/api/runs/{run.id}/cancel/", "{}", content_type="application/json")
    assert r.status_code == 403
    run.refresh_from_db()
    assert not run.cancel_requested

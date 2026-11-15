import threading
import time
from pathlib import Path

import pytest

from app.profiles.models import Profile
from app.runs import worker
from app.runs.models import CaptchaSession, ScraperRun
from app.scrapers.registry import ScraperInfo
from app.submissions.models import SubmittedRequest

FX = Path(__file__).parent / "fixtures"


def info(slug, file, **kw):
    return ScraperInfo(slug=slug, display_name=slug + ".com", path=FX / file, **kw)


@pytest.fixture
def fake_registry(monkeypatch):
    infos = [info("okp", "ok_scraper.py"), info("prompt", "prompt_scraper.py", needs_human=True),
             info("dead", "ok_scraper.py", status="not_automatable")]
    monkeypatch.setattr("app.scrapers.registry.all_scrapers", lambda *a, **k: infos)
    monkeypatch.setattr("app.scrapers.registry.get", lambda s: next((i for i in infos if i.slug == s), None))


@pytest.fixture
def profile(db):
    p = Profile.current()
    p.data = {"FIRST_NAME": "Jo", "EMAIL": "a@b.c", "STATE": "Minnesota"}
    p.save()
    return p


def test_profile_pii_is_encrypted(profile):
    assert b"a@b.c" not in bytes(profile.encrypted_pii)
    assert Profile.objects.get().data["EMAIL"] == "a@b.c"


def test_create_run_orders_human_first_and_skips(fake_registry, profile):
    run = worker.create_run(profile)
    s = list(run.sites.all())
    assert [x.slug for x in s][:2] == ["prompt", "okp"]
    assert s[2].slug == "dead" and s[2].status == "skipped"


def test_skip_mode_filters_human(fake_registry, profile):
    profile.captcha_mode = "skip"
    run = worker.create_run(profile)
    assert run.sites.get(slug="prompt").status == "skipped"


@pytest.mark.django_db(transaction=True)
def test_full_run_with_pause(fake_registry, profile):
    run = worker.create_run(profile)

    def answerer():
        for _ in range(100):
            cs = CaptchaSession.objects.filter(status="waiting").first()
            if cs:
                cs.answer, cs.status = "42", "answered"
                cs.save()
                if cs.kind == "text":
                    return
            time.sleep(0.2)
    t = threading.Thread(target=answerer)
    t.start()
    worker.process_run(run.id)
    t.join()
    run.refresh_from_db()
    assert run.status == "complete"
    assert run.sites.get(slug="prompt").status == "completed"
    assert run.sites.get(slug="okp").status == "completed"
    assert CaptchaSession.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_ledger_blocks_second_live_launch(fake_registry, profile):
    profile.captcha_mode = "skip"
    r1 = worker.create_run(profile, dry_run=False)
    worker.process_run(r1.id)
    assert SubmittedRequest.objects.filter(slug="okp").exists()
    r2 = worker.create_run(profile, dry_run=False)
    worker.process_run(r2.id)
    s = r2.sites.get(slug="okp")
    assert s.status == "skipped" and "duplicate" in s.note


@pytest.mark.django_db(transaction=True)
def test_dry_run_does_not_write_ledger(fake_registry, profile):
    profile.captcha_mode = "skip"
    worker.process_run(worker.create_run(profile).id)
    assert SubmittedRequest.objects.count() == 0

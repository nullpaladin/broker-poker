import os
import time
from pathlib import Path

from app.runs import runner

FX = Path(__file__).parent / "fixtures"
ENV = {"PATH": os.environ["PATH"], "EMAIL": "a@b.c", "DRY_RUN": "True", "FIRST_NAME": "Jo", "BP_HEADLESS": "0"}


def run(name, tmp_path, no_human=False, timeout=20, on_wait=lambda p, k: ""):
    return runner.run_scraper(FX / name, ENV, tmp_path, no_human=no_human, timeout=timeout, on_wait=on_wait)


def test_ok_gets_profile_env_and_no_dotenv(tmp_path):
    r = run("ok_scraper.py", tmp_path)
    assert r.status == "completed"
    assert "EMAIL=a@b.c" in r.log_tail and "DRY=True" in r.log_tail


def test_warning_counts(tmp_path):
    r = run("warn_scraper.py", tmp_path)
    assert r.status == "completed" and r.warnings == 1


def test_crash_and_exit(tmp_path):
    assert run("crash_scraper.py", tmp_path).status == "failed"
    assert run("exit_scraper.py", tmp_path / "b").status == "failed"


def test_skip_line(tmp_path):
    assert run("skip_scraper.py", tmp_path).status == "skipped"


def test_prompts_answered(tmp_path):
    seen = []
    r = run("prompt_scraper.py", tmp_path, on_wait=lambda p, k: (seen.append((p, k)), "XYZ")[1])
    assert r.status == "completed" and "GOT XYZ" in r.log_tail
    assert seen == [("", "continue"), ("CAPTCHA code: ", "text")]


def test_no_human_skips(tmp_path):
    assert run("prompt_scraper.py", tmp_path, no_human=True).status == "skipped"


def test_timeout_kills_process(tmp_path):
    t = time.time()
    r = run("hang_scraper.py", tmp_path, timeout=1)
    assert r.status == "failed" and "timed out" in r.note and time.time() - t < 15

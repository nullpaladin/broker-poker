"""Run one scraper in a child process and classify the outcome. No Django/DB here, so it is
unit-testable with fake scrapers."""
from __future__ import annotations

import os
import queue
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from app import paths
from app.runs import protocol

WAIT_LIMIT_SECONDS = 30 * 60


@dataclass
class SiteResult:
    status: str            # completed | failed | skipped
    note: str = ""
    warnings: int = 0
    screenshots: list = field(default_factory=list)
    log_tail: str = ""


def _kill_tree(proc: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def run_scraper(scraper_path: Path, env: dict, cwd: Path, *, no_human: bool, timeout: float,
                on_wait: Callable[[str, str], str | None],
                should_cancel: Callable[[], bool] = lambda: False) -> SiteResult:
    """``on_wait(prompt, kind)`` blocks until the user answers and returns the answer text
    (or None to abort). Time spent in ``on_wait`` does not count toward ``timeout``."""
    cwd.mkdir(parents=True, exist_ok=True)
    (cwd / "resources" / "screenshots").mkdir(parents=True, exist_ok=True)
    env = dict(env)
    env["PYTHONPATH"] = str(paths.REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUNBUFFERED"] = "1"
    env["BP_NO_HUMAN"] = "1" if no_human else "0"
    kwargs = {"start_new_session": True} if os.name != "nt" else {"creationflags": 0x00000200}
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.runs.child", str(scraper_path)],
        cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, **kwargs)
    q: queue.Queue = queue.Queue()

    def reader():
        for line in proc.stdout:
            q.put(line)
        q.put(None)
    threading.Thread(target=reader, daemon=True).start()

    log: list[str] = []
    needs_human = False
    skip_note = ""
    active = 0.0
    last = time.monotonic()
    aborted = ""
    while True:
        try:
            line = q.get(timeout=0.25)
        except queue.Empty:
            line = ""
        now = time.monotonic()
        active += now - last
        last = now
        if should_cancel():
            aborted = "cancelled"
            break
        if active > timeout:
            aborted = f"timed out after {int(timeout)}s"
            break
        if line is None:
            break
        if not line:
            continue
        ev = protocol.decode(line)
        if ev is None:
            log.append(line.rstrip("\n"))
            if line.startswith("SKIP "):
                skip_note = line.strip()
            continue
        if ev.get("event") == "needs_human":
            needs_human = True
        elif ev.get("event") == "wait":
            log.append(f"[paused: {ev.get('prompt') or 'manual step'}]")
            answer = on_wait(ev.get("prompt", ""), ev.get("kind", "continue"))
            last = time.monotonic()  # do not count the wait
            if answer is None:
                aborted = "no answer received"
                break
            try:
                proc.stdin.write(answer + "\n")
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
                pass
    if aborted:
        _kill_tree(proc)
    try:
        code = proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        code = proc.wait()
    # drain anything left
    while True:
        try:
            line = q.get_nowait()
        except queue.Empty:
            break
        if line:
            log.append(line.rstrip("\n"))
    (cwd / "log.txt").write_text("\n".join(log), encoding="utf-8")
    shots = sorted(str(p.relative_to(cwd)) for p in cwd.rglob("*.png"))
    tail = "\n".join(log[-40:])
    warnings = sum("was not found" in l for l in log)
    if aborted:
        return SiteResult("failed", aborted, warnings, shots, tail)
    if code == protocol.EXIT_NEEDS_HUMAN or needs_human:
        return SiteResult("skipped", "Needs a human (CAPTCHA/verification) and skip mode is on.", 0, shots, tail)
    if skip_note:
        return SiteResult("skipped", skip_note, 0, shots, tail)
    if code != 0:
        last_line = next((l for l in reversed(log) if l.strip()), f"exit code {code}")
        return SiteResult("failed", f"Scraper crashed: {last_line[:300]}", warnings, shots, tail)
    note = f"{warnings} form element(s) were not found — check the screenshots." if warnings else ""
    return SiteResult("completed", note, warnings, shots, tail)

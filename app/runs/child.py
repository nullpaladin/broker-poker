"""Runs ONE scraper in this process: python -m app.runs.child <scraper.py>

Scrapers end in a bare ``asyncio.run(main())`` and read their config from the environment, so we
run them as ``__main__`` via runpy after: neutralising dotenv, routing ``input()`` pauses to the
parent over a sentinel-line protocol, and (optionally) forcing headless Chromium.
"""
import builtins
import os
import re
import runpy
import sys

from app.runs import protocol


def _emit(event: dict) -> None:
    print(protocol.encode(event), flush=True)


def _kind(prompt: str) -> str:
    p = prompt.lower()
    return "text" if re.search(r"code|text|answer", p) and "press" not in p else "continue"


def _input(prompt=""):
    prompt = str(prompt)
    if os.environ.get("BP_NO_HUMAN") == "1":
        _emit({"event": "needs_human", "prompt": prompt})
        sys.exit(protocol.EXIT_NEEDS_HUMAN)
    _emit({"event": "wait", "prompt": prompt, "kind": _kind(prompt)})
    line = sys.stdin.readline()
    if line == "":
        raise EOFError("app closed the pause channel")
    return line.rstrip("\r\n")


def main(argv) -> int:
    scraper = argv[1]
    import dotenv
    dotenv.load_dotenv = lambda *a, **k: False  # never read a developer .env
    builtins.input = _input
    if os.environ.get("BP_HEADLESS") == "1":
        from pydoll.browser.options import ChromiumOptions
        orig = ChromiumOptions.__init__

        def patched(self, *a, **k):
            orig(self, *a, **k)
            self.add_argument("--headless=new")
        ChromiumOptions.__init__ = patched
    sys.argv = [scraper]
    sys.path.insert(0, os.path.dirname(os.path.abspath(scraper)))
    runpy.run_path(scraper, run_name="__main__")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

#!/usr/bin/env python3
"""Import every scraper module without launching a browser.

Each scraper ends in ``asyncio.run(main())``; we stub ``asyncio.run`` (and
``input`` / ``time.sleep``) to no-ops so importing a module only *evaluates its
body* — module-level constants, ``RIGHT_MAP`` dicts, ``SuperScraper`` attribute
references, imports. This catches typos and broken imports after a sweep without
needing Chrome or the network.

Run from the repo root:  ``python scripts/smoke_import.py``
Exit code is non-zero if any module fails to import.
"""

from __future__ import annotations

import asyncio
import builtins
import importlib.util
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BROKER_SITES = REPO_ROOT / "src" / "dsar" / "broker_sites"

sys.path.insert(0, str(REPO_ROOT))

# Neutralise the module-level side effects every scraper has. Close the coroutine
# handed to asyncio.run so it doesn't emit a "never awaited" RuntimeWarning.
def _noop_run(coro=None, *a, **k):
    if hasattr(coro, "close"):
        coro.close()


asyncio.run = _noop_run
time.sleep = lambda *a, **k: None             # noqa: E731
builtins.input = lambda *a, **k: ""           # noqa: E731


def _iter_scraper_files():
    yield from sorted(BROKER_SITES.glob("*/*_scraper.py"))


def main() -> int:
    failures: list[tuple[str, str]] = []
    count = 0
    for path in _iter_scraper_files():
        count += 1
        mod_name = "smoke_" + path.parent.name.replace("-", "_") + "_" + path.stem
        spec = importlib.util.spec_from_file_location(mod_name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:  # noqa: BLE001 - we want every failure, not the first
            failures.append((str(path.relative_to(REPO_ROOT)), traceback.format_exc()))

    print(f"imported {count} scraper modules, {len(failures)} failed")
    for rel, tb in failures:
        print(f"\n===== {rel} =====\n{tb}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

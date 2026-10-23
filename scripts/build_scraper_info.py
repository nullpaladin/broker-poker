#!/usr/bin/env python3
"""Regenerate src/dsar/scraper_info.json from the scraper modules (no browser).

One entry per broker: URL(S), the rights it exposes (RIGHT_MAP), every option the page
lists (PAGE_RIGHTS), health-check status, and whether it can run unattended. The scrapers
stay the source of truth; this file is generated, so edit the scraper and re-run:

    python scripts/build_scraper_info.py

HEALTH_CHECK_STATUS: NOT_AUTOMATABLE | AUDITED (PAGE_RIGHTS recorded) |
NEEDS_LIVE_CAPTURE (PAGE_RIGHTS empty, TODO) | NO_RIGHTS_CHOOSER (no PAGE_RIGHTS).
"""
from __future__ import annotations

import asyncio
import builtins
import importlib.util
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BROKER_SITES = REPO_ROOT / "src" / "dsar" / "broker_sites"
OUT = REPO_ROOT / "src" / "dsar" / "scraper_info.json"
sys.path.insert(0, str(REPO_ROOT))


def _noop_run(coro=None, *a, **k):
    if hasattr(coro, "close"):
        coro.close()


asyncio.run = _noop_run
time.sleep = lambda *a, **k: None
builtins.input = lambda *a, **k: ""


def _right_name(r):
    return r.name if r is not None else None


def main() -> int:
    info = {}
    for path in sorted(BROKER_SITES.glob("*/*_scraper.py")):
        name = path.parent.name
        spec = importlib.util.spec_from_file_location("info_" + name.replace("-", "_"), path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        automatable = not getattr(mod, "NOT_AUTOMATABLE", False)
        page_rights = getattr(mod, "PAGE_RIGHTS", None)
        if not automatable:
            status = "NOT_AUTOMATABLE" if page_rights is None else ("AUDITED" if page_rights else "NEEDS_LIVE_CAPTURE")
        elif page_rights is None:
            status = "NO_RIGHTS_CHOOSER"
        else:
            status = "AUDITED" if page_rights else "NEEDS_LIVE_CAPTURE"
        entry = {
            "URLS": [{"GENERAL": mod.URL}] if getattr(mod, "URL", None) else [],
            "RIGHTS": [r.name for r in getattr(mod, "RIGHT_MAP", {})],
            "OPTIONS": {label: _right_name(r) for label, r in (page_rights or {}).items()},
            "HEALTH_CHECK_STATUS": status,
            "AUTOMATABLE": automatable,
        }
        if not automatable:
            entry["NOT_AUTOMATABLE_REASON"] = getattr(mod, "NOT_AUTOMATABLE_REASON", "")
        info[name] = entry
    OUT.write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(info)} scrapers to {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

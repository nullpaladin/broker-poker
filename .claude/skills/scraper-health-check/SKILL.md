---
name: scraper-health-check
description: Add the standard HEALTH_CHECK block to DSAR scrapers - a committed PAGE_RIGHTS inventory compared against the live page plus required-field assertions. Use on a batch of already-audited scraper directories, e.g. "/scraper-health-check 33across clickagy ...".
---

# scraper-health-check

Gives each named scraper (`src/dsar/broker_sites/<name>/<name>_scraper.py`) the **standard health
check** exactly as shown in `src/dsar/template_scraper.py` (read it, plus
`SuperScraper.read_option_labels`, `audit_rights`, `assert_fields_filled` in
`src/dsar/super_scraper.py`). Run `/scraper-audit` on the scraper first if it still uses old
`wants()` / `REMOVE_INFORMATION` / string right codes. Do not run scrapers or a browser; never commit.

A health check never submits (it implies DRY_RUN) and keeps screenshots on for the later LLM-review
stage. It must catch two kinds of drift:

1. **Rights drift.** Add `PAGE_RIGHTS = {"<option label exactly as shown>": Right.X or None, ...}` —
   *every* right/request-type option the page offers, including ones we don't automate
   (`None`, e.g. "Correct my information"), plus `RIGHTS_OPTIONS_CSS` selecting the elements that
   list them. Before the submit step, under `if SuperScraper.HEALTH_CHECK:` open the dropdown/accordion
   if needed (the same clicks the scraper already does), then
   `offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)` and
   `SuperScraper.audit_rights(offered, PAGE_RIGHTS)`. It prints the full list and raises on any new or
   vanished option. Every `RIGHT_MAP` entry must correspond to a `PAGE_RIGHTS` label mapped to the same
   Right. Forms with one fixed purpose (no chooser) get `PAGE_RIGHTS` with the single option and the
   CSS of its heading/checkbox label.
2. **Field drift.** Under `if SuperScraper.HEALTH_CHECK:` just before the DRY_RUN return, call
   `await SuperScraper.assert_fields_filled(tab, {"<human label>": "<xpath>", ...})` for every field the
   scraper fills (use the element constants / names in the header comment). One check per right path.

## Rules
- Build `PAGE_RIGHTS` only from what the scraper code, its header comments and docs/ already record about
  the page. Never invent option text. If the full option list isn't recorded, set
  `PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list` and report
  the scraper — the first live run prints every option so a human can paste them in.
- Keep gating through `SuperScraper.rights_to_exercise(RIGHT_MAP)`; health checks run for the rights the
  user selected like any other run. (Rights drift is still audited for the whole page.)
- NOT_AUTOMATABLE scrapers: add `PAGE_RIGHTS` (so drift is visible) but do not add a running path.
- Wrap nothing in try/except — a failing check must fail loudly.

## Verify, then report
- `venv/bin/python -m py_compile <file>`; `grep -c "audit_rights\|assert_fields_filled" <file>` ≥ 2
  (except NOT_AUTOMATABLE and TODO cases).
- Final message: one line per scraper (`name: done` / `name: TODO needs live capture` / `name: skipped (not automatable)`),
  then any selector or flow doubts.

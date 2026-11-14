# Health checks

A health check is a scraper run with `HEALTH_CHECK=True`. It opens the live form, fills it in, and **never
submits** (`HEALTH_CHECK` implies `DRY_RUN`). Its job is to tell us when a broker changed its form.

## What a run does
1. Navigates and opens the rights chooser (the same clicks the scraper already does).
2. **Rights drift** — `offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)` then
   `SuperScraper.audit_rights(offered, PAGE_RIGHTS)`. Prints every option with the `Right` it maps to
   (`NEW` / `(not automated)`), and raises `RightsChangedError` if a known option vanished or an unknown one appeared.
3. Fills the form for each right chosen by `SuperScraper.rights_to_exercise(RIGHT_MAP)`.
4. **Field drift** — `await SuperScraper.assert_fields_filled(tab, {label: xpath})` just before the submit step;
   raises `RequiredFieldError` listing any field that is missing or empty.
5. **Screenshots** — `SuperScraper.screenshot(tab, label)` saves one shot per scrolled viewport to `resources/screenshots/<scraper>/`
   for a later human/LLM visual review.

## The per-scraper data
- `PAGE_RIGHTS = {"<option label exactly as shown>": Right.X or None}` — **every** option the page offers; `None`
  for ones we don't automate (e.g. "Correct my information"). Every `RIGHT_MAP` entry must appear here with the same `Right`.
- `RIGHTS_OPTIONS_CSS` — CSS selecting the elements that list those options.
- `PAGE_RIGHTS = {}  # TODO(health-check)` means the option text was never recorded. Run once live; the audit prints
  the full list to paste in. Never invent option text.
- `NOT_AUTOMATABLE = True` scrapers (mid-run SMS/email code) keep `PAGE_RIGHTS` so drift is visible but are skipped.

## Statuses (`src/dsar/scraper_info.json`)
`AUDITED` (PAGE_RIGHTS recorded) · `NEEDS_LIVE_CAPTURE` (TODO above) · `NO_RIGHTS_CHOOSER` (single-purpose form) ·
`NOT_AUTOMATABLE`. Regenerate the file with `python scripts/build_scraper_info.py`.

## Maintainer skills (Claude Code)
`/scraper-review <names>` = `/scraper-audit` (conventions) → `/scraper-health-check` (adds the data above) →
shared-helper and residency checks → `compileall` + `scripts/smoke_import.py`. Skills never run a browser or commit;
the live health-check run is done by a human.

## Running
```bash
HEALTH_CHECK=True python src/dsar/broker_sites/<broker>/<broker>_scraper.py
```

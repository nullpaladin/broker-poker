---
name: scraper-review
description: Run the full per-scraper checklist in one pass - /scraper-audit conventions first, then the /scraper-health-check scaffolding, then the shared-helper and residency checks. Use on a batch of scraper directories, e.g. "/scraper-review 33across clickagy ...".
---

# scraper-review

One pass per scraper (`src/dsar/broker_sites/<name>/<name>_scraper.py`), in this order. Do not run a
browser; never commit unless asked.

1. **Conventions** — follow `.claude/skills/scraper-audit/SKILL.md` (Right enum, single
   `rights_to_exercise` gate, `request_statement` wording, no speculation, element notes, screenshots).
2. **Health check** — follow `.claude/skills/scraper-health-check/SKILL.md` (`PAGE_RIGHTS`,
   `RIGHTS_OPTIONS_CSS`, `audit_rights`, `assert_fields_filled`; `TODO(health-check)` when the option text was never recorded).
3. **Shared helpers** — replace inline `execute_script` that duplicates a `src/dsar/js_utils.py`
   helper (`js_set_value`, `js_check`, `select_native_option`, `js_eval`, `js_click`, `page_text`,
   `fill_autocomplete`). Keep page-specific scripts (shadow DOM, custom widgets) as they are.
4. **Residency** — if the form (or its header comments) is only for residents of privacy-law
   states, set `SERVES_NO_LAW_STATES = False` and call `SuperScraper.bail_if_state_unsupported(globals())`.
5. **Verify** — `python -m compileall -q src && python scripts/smoke_import.py`, then
   `python scripts/build_scraper_info.py` if rights/URLs changed.

Report one line per scraper plus any selector doubts.

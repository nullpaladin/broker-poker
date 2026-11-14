---
name: scraper-audit
description: Audit and migrate DSAR scrapers in src/dsar/broker_sites to the current SuperScraper conventions (4-Right enum, rights_to_exercise gate, request_statement wording, no speculation, element notes). Use on a batch of scraper directories, e.g. "/scraper-audit 33across affinityanswers ...".
---

# scraper-audit

Brings each named scraper (`src/dsar/broker_sites/<name>/<name>_scraper.py`) up to the
conventions in `src/dsar/template_scraper.py` — **read the template first**, and read
`src/dsar/super_scraper.py`, `src/dsar/rights.py`, `src/dsar/js_utils.py` for the helper API.
Work on exactly the scrapers you are given, one at a time. Do NOT run scrapers, open a browser,
or touch files outside your scrapers (shared code is changed by the main session, not you —
report what you'd need instead). Never `git commit`.

## Checklist (apply to every scraper)

1. **Rights → `Right` enum.** `from src.dsar.rights import Right`. `RIGHT_MAP` is keyed by
   `Right.RIGHT_TO_ACCESS / RIGHT_TO_OPT_OUT / RIGHT_TO_DELETE / RIGHT_TO_LIST_OF_THIRD_PARTIES`.
   Old-code mapping: `access`, `portability` → ACCESS; `opt_out_sale_share`, `opt_out_targeted_ads`,
   `opt_out_profiling`, `limit_sensitive_pi` → OPT_OUT; `know_third_parties` → LIST_OF_THIRD_PARTIES;
   `delete` → DELETE; `correct` → drop from RIGHT_MAP (not automatable; list it as `None` in the
   health-check PAGE_RIGHTS instead). When several old codes collapse into OPT_OUT/ACCESS and the
   form has a separate choice for each, the value becomes a **list of entries** and the submit loop
   iterates them (template shows how). If the form has a single choice covering them, keep one entry.
   Not every site has every right — only map what the form offers.
2. **One gate.** `rights = SuperScraper.rights_to_exercise(RIGHT_MAP)` decides what is submitted.
   Remove every `SuperScraper.wants(...)`, `REMOVE_INFORMATION`, `REQUESTED_RIGHTS`, hand-rolled
   `if delete:` gate, and `HEADED`. Deletion is just `Right.RIGHT_TO_DELETE` going through the gate.
   Scrapers that have no RIGHT_MAP (older ones that gated on REMOVE_INFORMATION) get one built from
   what the code already submits. **Do not change what a scraper submits or its selectors** — only how it
   is gated. Rename `code(s)` → `right(s)` variables/prints; wording "codes" → "rights" everywhere.
3. **Wording.** Free-text details/message boxes use `SuperScraper.request_statement([right...], broker="X")`
   (cites the state's law only when it has one). Delete hand-written "I am a ... resident ... under
   applicable (state and) federal privacy law" sentences, `LAW_FULL_NAME or 'applicable state and
   federal privacy law'` fallbacks, and any mention of "federal privacy law" (no federal consumer
   privacy law applies). If a form's field wants a short fixed phrase, still no "federal".
4. **No speculation.** Remove (a) success/confirmation detection built from guessed words
   ("thank", "success", "received", "submitted"...) for any site where a real submission was never
   observed — print `Submitted '<RIGHT>' for <email> — confirm in the browser.` instead; keep exact-text
   checks only where the file records that text was observed; (b) answers that misstate facts about the
   user (e.g. claiming California residency); (c) options/selectors invented without the page showing
   them — if you suspect an option doesn't exist on the page, **leave the code and add it to your
   report**; do not guess either way.
5. **Element notes.** The header comment lists every element the code touches with a human-readable
   name (like `src/dsar/broker_sites/lizdev/lizdev_scraper.py`). Replace opaque ids as constants:
   `CHECK_OWN_PI = "choice_2_14_1"  # "I want to know my own personal information"`, and use the
   constants in code. Keep it accurate — do not invent labels you can't see in the code/comments.
6. **Screenshots.** Only `await SuperScraper.screenshot(tab, "<label>")` (label like `dry_run_access`;
   never a path, never a hard-coded scraper name, never `tab.take_screenshot`). It already no-ops outside
   DRY_RUN/HEALTH_CHECK and scrolls multiple pages.
7. **Shared helpers.** In-page JS goes through `src.dsar.js_utils` (`js_eval`, `js_set_value`,
   `js_check`, `select_native_option`, ...). Replace local copies (`_js_fill`, `_select_native_option`,
   inline `execute_script` snippets that duplicate one) when it is a faithful substitution; leave
   genuinely site-specific JS. Math CAPTCHAs: `captcha_solutions_util.solve_math_captcha`.
   Browser options: `SuperScraper.build_chromium_options()`.
8. **Residency scope.** If the form itself is only for residents of states with a privacy law (or
   rejects others), add module-level `SERVES_NO_LAW_STATES = False` and call
   `if SuperScraper.bail_if_state_unsupported(globals()): return` at the top of `main()`
   (right after `bail_if_not_automatable`). If it accepts anyone, say nothing (default True) —
   but add a one-line header note when the page makes this explicit.
9. **NOT_AUTOMATABLE scrapers** (`NOT_AUTOMATABLE = True`) are skipped entirely by design; still apply
   items 1, 3-7 so they're correct when reactivated, but do not make them run.

## Verify, then report
- `venv/bin/python -m py_compile <file>` for each file touched.
- `grep -nE "REMOVE_INFORMATION|REQUESTED_RIGHTS|\.wants\(|HEADED|federal|take_screenshot|opt_out_sale_share|opt_out_targeted_ads|opt_out_profiling|know_third_parties|limit_sensitive_pi|portability" <file>` must come back clean
  (except `portability`/old names inside a header comment describing the *site's* own wording).
- Final message: one line per scraper (`name: done` / `name: done, MANUAL REVIEW: <specific doubt>`), then a
  short list of anything that needs a live browser, a design decision, or a change to shared code.

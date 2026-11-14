# broker-poker
Broker Poker is an application that assists users to receive a copy of and delete their personal data from registered or otherwise known data brokers.

# Status
- Near-MVP. A user can email data brokers today, and ~270 per-broker web-form scrapers exist in `src/dsar/broker_sites/` (run one at a time from a terminal; the GUI/orchestrator is not built yet). Most scrapers have never been run against a live submission, which is what health checks (below) are for.

# Acronyms
- DSAR: Data Subject Access Request (the method of communication from a consumer to a controller in order to exercise data privacy rights)

# AI usage disclosure
- Generative AI (LLMs) are used in this project only for the following:
  - To generate broker opt-out scrapers in `src/dsar/`
    - Why? There are too many data brokers that require DSAR forms (hundreds) to generate myself. The output is deterministic (the scraper will fail if it cannot insert a piece of information) and relatively easy to validate by a human.
      - `pydoll` makes this easy since I can take a screenshot of the site before and after the scraper runs, so I can view the output before committing anything to main.
- Generative AI (LLMs) are not used in any decision making, nor to generate infrastructure. All design decisions are my own and are unassisted by LLMs.
- All code is reviewed by myself and no code will be allowed to make it to main without a thorough review (and later CICD checks to make sure all scrapers are valid and healthchecks pass).
- Captcha bypass is either done by the end user or via captcha solution services (which as far as I am aware do not use LLMs or other forms of machine learning for these tasks).
- Generative AI (LLMs) may be used to critique frontend (GUI) code before it hits version control, however LLMs will have no say in the design or final output.
  - I'm not very good at frontend design, however I will not rely on LLMs as a crutch since this is part learning exercise for frontend design and implementation.

# Repo layout
```
broker-poker/
├── AGENTS.md                 # Conventions for any LLM/agent (CLAUDE.md just imports it)
├── SITES.md                  # Per-broker checklist: URL, status, notes (long; see "Broker sites")
├── src/
│   ├── dsar/
│   │   ├── super_scraper.py  # Shared base class: env config, form helpers, screenshots, health-check helpers
│   │   ├── js_utils.py       # Shared in-page JS helpers (set value, check, select option...)
│   │   ├── rights.py         # The 4 `Right`s a scraper can exercise
│   │   ├── template_scraper.py   # Copy this to start a new scraper
│   │   ├── scraper_info.json # GENERATED per-broker map (URLs, rights, health-check status)
│   │   ├── broker_sites/<name>/<name>_scraper.py   # one scraper per broker
│   │   └── emails/           # Email template + verified broker email list
│   └── state_privacy_request_factory/   # State -> privacy-law data (json + loader)
├── scripts/                  # smoke_import.py (import every scraper), build_scraper_info.py
├── docs/                     # scrapers/ (how-to + reference), data/ (schemas), infrastructure/ (GUI plan); see docs/README.md
├── .github/workflows/        # CI: compile + smoke import + scraper_info.json freshness
└── .claude/skills/           # Claude Code skills: scraper-audit, scraper-health-check, scraper-review
```

# Quickstart
```bash
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
# .env needs: FIRST_NAME LAST_NAME EMAIL ADDRESS CITY STATE ZIP_CODE DATE_OF_BIRTH PHONE_NUMBER
#             RIGHTS_TO_EXERCISE (comma-separated RIGHT_TO_ACCESS / RIGHT_TO_OPT_OUT / RIGHT_TO_DELETE / RIGHT_TO_LIST_OF_THIRD_PARTIES)
#             DRY_RUN HEALTH_CHECK HEADLESS_BROWSER_MODE CHROMIUM_LOCATION
python src/dsar/broker_sites/<broker>/<broker>_scraper.py     # DRY_RUN=True fills the form and screenshots; it never submits
python scripts/smoke_import.py                                # sanity check: every scraper still imports
```
`DRY_RUN=True` is the default. Deletion only runs if `RIGHT_TO_DELETE` is in `RIGHTS_TO_EXERCISE`.
Full development conventions live in [AGENTS.md](AGENTS.md); reference docs are in [docs/](docs/).

# Health checks
Brokers change their forms without telling anyone. A **health check** is a scraper run (`HEALTH_CHECK=True`) that
opens the live form, fills it in, and **never submits**, so it is safe to run repeatedly. It checks three things:

1. **Rights drift** — each scraper commits `PAGE_RIGHTS`, an inventory of every request option the page offers
   (e.g. "Delete my data" -> `RIGHT_TO_DELETE`, "Correct my data" -> `None` = not automated). The run reads the options
   currently on the page (`RIGHTS_OPTIONS_CSS`) and fails if one **vanished** or a **new** one appeared.
2. **Field drift** — just before the would-be submit, `assert_fields_filled` confirms every field the scraper fills is
   actually populated, so a renamed or removed input fails loudly instead of silently submitting a blank form.
3. **Screenshots** — a full-page series (`..._p01.png`, `_p02`, ...) is saved to `resources/screenshots/<scraper>/` for a later human or
   LLM review, since the automated checks can't tell whether the page *looks* right.

`HEALTH_CHECK` implies `DRY_RUN`. A scraper whose `PAGE_RIGHTS` is `{}` with a `TODO(health-check)` has never been
run live; the first health-check run prints the page's full option list so it can be pasted in. `HEALTH_CHECK_STATUS`
per broker (AUDITED / NEEDS_LIVE_CAPTURE / NO_RIGHTS_CHOOSER / NOT_AUTOMATABLE) is in `src/dsar/scraper_info.json`.
Scrapers that need a mid-run SMS/email code are marked `NOT_AUTOMATABLE` and skipped.
More detail: [docs/scrapers/health_checks.md](docs/scrapers/health_checks.md).

## Claude Code skills (maintainer tooling)
Run in batches over scraper directories, e.g. `/scraper-review 33across clickagy`. They edit code only; they never run a browser or commit.

| Skill | What it does |
|-------|--------------|
| `/scraper-audit` | Brings a scraper up to the current conventions: the 4-`Right` enum, one `rights_to_exercise` gate, law-aware wording, no guessing about post-submit pages, element notes, shared helpers, residency scope. |
| `/scraper-health-check` | Adds the `PAGE_RIGHTS` inventory and the field assertions described above. Writes `TODO(health-check)` where the page's options were never recorded. |
| `/scraper-review` | Runs both in order plus the helper and residency checks, then the smoke import. Start here. |

# Infrastructure
Legend: `[x]` done, `[~]` partly done, `[ ]` not started. The GUI/distribution design is in [docs/infrastructure/frontend_implementation_plan.md](docs/infrastructure/frontend_implementation_plan.md).
- `src/dsar/emails` (+ `src/state_privacy_request_factory`)
  - [~] per-state factory with exercisable rights, citing specific statutes — the data side exists (`state_privacy_data.json`: law, citation, `request_basis`, rights per state; `SuperScraper.request_statement` uses it for web forms), but nothing generates the *email* text per state yet; only the Minnesota template (`mcdpa_email_template.txt`) exists
  - [ ] simple GUI to generate the above per-state factory for emails
  - [ ] batched list of 100 each emails — `verified_email_list.txt` has ~224 addresses, but they are not split into batches of 100
- `src/dsar`
  - [x] directories of each verified dsar-only broker created (~270 under `broker_sites/`; a few are still empty, see SITES.md)
  - [~] user-solved captcha — scrapers pause for a manual solve (`input()`), but there is no GUI for it
  - [~] captcha bypass service — only a local math/image solver (`captcha_solutions_util.py`); 2captcha is a `TODO` in `tapad` and `directmail`
  - [~] health checks — scaffolding is in every scraper; most `PAGE_RIGHTS` still need a first live run (see "Health checks")
- misc
  - [ ] Explanation for brokers with a very complex DSAR setup (e.g. TransUnion), opt-out guides
  - [ ] Create a "learn more" section for the readme

# Where the state privacy-law data lives
- `src/dsar/scraper_info.json` — generated per-broker map: URL(S), rights offered (`RIGHT_MAP`), every page option (`PAGE_RIGHTS`), `HEALTH_CHECK_STATUS`, `AUTOMATABLE`. The scrapers are the source of truth; regenerate with `python scripts/build_scraper_info.py` after changing one.
- `src/state_privacy_request_factory/state_privacy_data.json` — one row per state: abbreviation, whether it has a comprehensive privacy law, the law's name and citation, the `request_basis` phrase used in request messages, and which rights it grants. **Update this file when a state's law changes** (schema: `docs/data/state_privacy_data.md`).
- Rights the scrapers can exercise: `RIGHT_TO_ACCESS`, `RIGHT_TO_OPT_OUT`, `RIGHT_TO_DELETE`, `RIGHT_TO_LIST_OF_THIRD_PARTIES` (`src/dsar/rights.py`); which ones run is the `RIGHTS_TO_EXERCISE` setting in `.env`.

# How To Email Data Brokers
- 200+ data brokers allow users to exercise their data privacy rights through email.
  - This is advantageous, as you can theoretically send one email via a template to hundreds of data brokers and have your information removed with minimal effort on the consumers' end.
- The basic idea of how to send these mass emails:
  1. Open your email client and draft a new email
  2. Instead of adding emails to the `To:` or `CC:` fields, add emails to the `BCC:` field so each recipient doesn't see the others that you're emailing.
  3. Gather up to 100 emails at a time from the email list that lives at [verified_email_list.txt](src/dsar/emails/verified_email_list.txt) and put them in the BCC field
  4. Set the subject to `<state privacy act name> Request`
  5. Copy the email template found at [mcdpa_email_template.txt](src/dsar/emails/mcdpa_email_template.txt) into the email body and add in your personal information, including Mobile Advertising IDs. You can find your Mobile Advertising ID (MAID) by following these guides:
    - Android 
      - https://privacyinternational.org/guide-step/4317/android-opt-out-targeted-ads-and-renew-your-advertising-id
      - Note that this is per-device, so if you have multiple devices, place them on separate lines in the email template. This goes for any old phones that you still have in your possession.
      - Note that you can permanently remove your MAID), but you should absolutely write down this value before doing so as it will be permanently deleted once removed.
    - Apple / iOS
      - You can't natively view your advertising ID (IDFA), however there are apps on the app store that will display this value for you.

# Broker sites
The per-broker checklist (URL, status, and notes for ~270 brokers, grouped into "cannot be automated", "manual lookup first", "retry later" and "automated") lives in **[SITES.md](SITES.md)**. It is long, so it is kept out of this file. For a machine-readable version see `src/dsar/scraper_info.json`.

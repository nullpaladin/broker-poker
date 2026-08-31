# Broker Poker: Frontend, Distribution & User Experience Implementation Plan

## Purpose of this document

This is the full design/implementation plan for turning broker-poker from a
CLI-driven, `.env`-configured tool (~189 per-site scrapers under
`src/dsar/broker_sites/`, run one-by-one from a terminal) into a distributable,
GUI-driven application: a user downloads a release, runs an installer, fills
out a guided onboarding flow, watches a live-updating list of ~200 DSAR
scrapers run against their information, and exports the results.

This document is meant to be **self-sufficient** — written so it can be
implemented from cold, without re-deriving the reasoning behind each
decision. Where a decision has a non-obvious "why," that reasoning is
included inline rather than left implicit.

**Relationship to `docs/next_phase_implementation_plan.md`**: that document
covers hardening the *existing* scraper backend (2Captcha integration
architecture, complaints cleanup). This document builds the GUI/distribution
layer on top of that work and reuses the `captcha_solver.py` interface from
it. The **one-time-submission ledger is NOT taken from that document** — it
is designed self-contained in [§4](#4-data-model) here, and
`next_phase_implementation_plan.md` §3 is superseded. Read that document for
the `captcha_solver.py` design; ignore its §3.

## Table of contents

1. [Guiding constraints](#1-guiding-constraints)
2. [End-to-end user experience](#2-end-to-end-user-experience)
3. [Architecture overview](#3-architecture-overview)
4. [Data model](#4-data-model)
5. [Redaction levels and field gating](#5-redaction-levels-and-field-gating)
6. [Rights and state gating](#6-rights-and-state-gating)
7. [Scraper manifest — declarative per-site metadata](#7-scraper-manifest--declarative-per-site-metadata)
8. [CAPTCHA handling](#8-captcha-handling)
9. [Frontend architecture](#9-frontend-architecture)
10. [Background job execution](#10-background-job-execution)
11. [Export / import format](#11-export--import-format)
12. [Distribution and installation](#12-distribution-and-installation)
13. [Trust and security posture (no code signing)](#13-trust-and-security-posture-no-code-signing)
14. [Migration path from the current CLI scrapers](#14-migration-path-from-the-current-cli-scrapers)
15. [Phased rollout plan](#15-phased-rollout-plan)
16. [Open questions to verify before/during build](#16-open-questions-to-verify-beforeduring-build)
17. [Decision log](#17-decision-log)

---

## 1. Guiding constraints

These were established through discussion and should override instinct if
they ever conflict with something that "seems easier" mid-implementation:

- **Single user, single machine, local-only.** This is not a multi-tenant
  web app. No auth system, no multi-user concerns, no need for Redis/Celery/
  message brokers — those add operational weight this project doesn't need
  at its actual scale (~200 sequential scraper runs, one profile).
- **Maintained by one person who is not a frontend developer.** Every
  frontend decision below was chosen to minimize ongoing JS/tooling burden.
  No `npm`, no JS build step, no framework. Plain Django templates + one
  page using hand-written `fetch()` JS.
- **Scrapers run headless by default.** Chrome is launched with
  `--headless=new` unless a debug/developer flag is set (a `.env` flag for
  CLI/MVP runs, a hidden developer-section toggle in the Full-Release UI).
  Showing the browser is a debugging affordance, not the normal mode.
  **Exception:** widget-CAPTCHA "solve in UI" v1 (§8.3.2) requires a visible
  window, so selecting that mode with widget-type sites in the run forces
  headed mode for the run (see §8.3.2).
- **The host must nonetheless be *able* to show a visible browser window.**
  Even though headless is the default, the debug flag and the widget-CAPTCHA
  v1 flow both need a real window to appear on the user's desktop. This
  capability requirement is what ruled out containerizing the *scraper
  execution* step on Windows and is why Docker is not the default Windows
  path.
- **PII is being collected at an uncomfortable level** (SSN last-4, DL
  images, VINs, full address). Every design choice involving storage or
  export defaults to the safer option, with the less-safe option available
  but requiring explicit, slightly-frictioned opt-in.
- **No budget.** No paid code signing, no paid audits, no paid CAPTCHA
  solving beyond what the user explicitly opts into and pays for themselves
  (their own 2Captcha key).
- **This is a personal/small-audience open-source tool**, not an enterprise
  product. Trust-building tools chosen below (build provenance, VirusTotal,
  source availability) reflect that scale — don't over-invest here.

---

## 2. End-to-end user experience

This is the full flow, expanded with the details from every design
discussion. Treat this section as the product spec; everything after it is
implementation detail in service of this flow.

### 2.0 Scope: MVP UI vs Full-Release UI

This document specifies the **Full-Release UI**. There is an earlier,
deliberately minimal **MVP UI** that is a strict subset — build it first,
ship it, then grow it into the Full-Release UI. The MVP UI corresponds to
GitHub Epic #9 / issue #34; the Full-Release UI to Epic #10 / issues
#35–#37.

| Aspect | MVP UI | Full-Release UI |
|---|---|---|
| Config input | `.env` file only — no info-entry forms | Guided multi-step onboarding (§2.3) |
| Screens | One: the live run list (§2.5) | Welcome, info entry, redaction/rights/CAPTCHA steps, pre-run summary, live run, completion |
| Import / export | None | Encrypted profile bundle + returning-user flow (§11) |
| CAPTCHA handling | **None.** CAPTCHA-requiring sites are skipped and shown as ➖, with the reason visible. (If the run is started headed via the debug flag, they fall back to the existing blocking terminal prompt that ~63 scrapers already use.) | Three modes: 2Captcha, skip, solve-in-UI (§8) |
| State handling | Assumes Minnesota. No state gating and no hard block — the UI states plainly "no guarantees this works outside Minnesota" and runs everything anyway. | All states selectable, per-state rights + warnings (§6) |
| Browser visibility | Headless; debug `.env` flag shows it | Headless default; headed only for widget-CAPTCHA solve-in-UI (§8.3.2) |
| Health status | Not shown | 🟥 / ❓ overlays from the nightly remote health file (§2.5) |
| Backend | Same background worker (§10) + polling API (§9) | Same |

The MVP UI is *only* the live run screen (§2.5) driven by the polling
backend (§9) and the sequential worker (§10), reading a `Profile` populated
from `.env` instead of from forms. Everything else in this section and this
document is Full-Release scope.

### 2.1 Acquisition & install

1. User downloads a release from GitHub: a Windows executable, or (Linux) a
   Docker Compose bundle + install script.
2. Windows: user runs the `.exe`. First run does a **dependency preflight**
   (see [§12](#12-distribution-and-installation)) — checks for Chrome,
   offers to install it if missing, via a tiered fallback chain. Python,
   Django, and all other app dependencies are already bundled inside the
   `.exe` — nothing else to install.
3. Linux: user runs an install script that checks for Docker, brings up the
   Compose stack (`docker compose up`), and opens the app in the default
   browser at `http://localhost:8000`. The container is configured for
   Wayland socket passthrough so the automated Chrome window can display on
   the user's real desktop for CAPTCHA-solving flows that need it.

### 2.2 Welcome screen

4. First screen: plain-language explanation of what the app does, what
   states/rights are supported, how submitted information is used, what
   information is needed and why, what "Right to Access / Opt-Out / Delete"
   mean in practice, and how import/export works. This is server-rendered,
   static content — no interactivity needed beyond "Next" / "Skip" buttons.
   The welcome screen must also carry two disclosures (GitHub issues #32,
   #33), shown here rather than buried elsewhere:
   - **Legal disclaimer**: this tool is for exercising *your own* privacy
     rights over *your own* information only; the user is acting on their
     own behalf, **not as an "authorized agent"** (the DSAR forms are
     filled autonomously and the emails sent manually, but in both cases it
     is the consumer themselves acting); do not use it against anyone
     else's data or in any way that breaks the law.
   - **Privacy practices disclosure**: everything runs on-device; the
     maintainer receives no user data except whatever a user chooses to put
     in a GitHub issue or pull request; the only outbound API traffic is to
     the broker sites themselves and (only if the user opts into 2Captcha
     mode) to 2Captcha — API calls never carry consumer PII, only
     data-broker identifiers. This mirrors the `SECURITY.md` in §13 but is
     stated in the app itself so the user doesn't have to go read a file.
5. A **"Returning user?"** option at the bottom, gated behind an import
   step: user uploads their exported profile bundle (see
   [§11](#11-export--import-format)), the app validates/decrypts it
   (prompting for the password if it's encrypted), and if successful skips
   straight to the site-run screen (§2.5), bypassing data entry entirely.

### 2.3 Information entry

6. A multi-step Django form (plain HTML, POST/redirect between steps — no
   JS required for this part) collects:
   - Name
   - Address(es) — repeatable, for apartment/multi-line cases
   - Phone number(s)
   - Email address(es)
   - Vehicle Identification Number(s) (VIN), optional
   - Last 4 of SSN, optional
   - Driver's license image, optional but "highly encouraged" per copy on
     the form
   - **Redaction level** selection (radio, see [§5](#5-redaction-levels-and-field-gating))
   - **Rights to exercise** selection. Every US state is selectable — the
     app never hard-blocks on state. If the chosen state has no active
     consumer-privacy law, the user sees a warning ("your state has no
     active privacy bill — these requests may not be honored and no
     state-specific rights apply") but can still proceed. Per-state rights
     differ (e.g. Wisconsin has none; Minnesota has Right to List of Third
     Parties; Colorado writes health-data handling into its bill), so the
     selectable rights list is filtered by state (see
     [§6](#6-rights-and-state-gating)).
   - **CAPTCHA handling mode** selection (radio, three options, see
     [§8](#8-captcha-handling)) — appears as its own step immediately after
     the main info form, per the original spec.
7. On submission of each step, the app writes to the local `Profile` model
   immediately (not just at the very end) — if the user closes the app
   mid-entry, progress isn't lost. See [§4](#4-data-model).
8. Once the profile is complete, the app **automatically writes an export
   file** (see [§11](#11-export--import-format)) without the user having to
   ask — this is the "two copies" behavior from the original spec: one
   plain profile-data export, and one with run metadata attached (populated
   later, once a run has actually happened).

### 2.4 Pre-run summary / site list preview

9. Before starting, the app shows the computed list of applicable sites —
   filtered by which scrapers' `REQUIRED_FIELDS` the profile actually
   satisfies given the chosen redaction level, and which rights/states
   apply (see [§6](#6-rights-and-state-gating), [§7](#7-scraper-manifest--declarative-per-site-metadata)).
   Sites that will be skipped due to the CAPTCHA-skip option are shown
   struck through, with the reason visible.
10. **Email-based brokers are surfaced here too, before the run starts.**
    Some brokers only accept DSAR requests by email, not a web form. The
    pre-run screen tells the user about this list and offers to **generate
    per-state pre-filled email links** — `mailto:` links (or a copyable
    list) with recipient, subject, and body all populated for the user's
    state and selected rights, which the user clicks to send straight from
    their own email client. This is presented *before* the scrapers run so
    the user can knock out the email requests while the automation works.
    (Link generation reuses the state privacy-law data from §6; the
    recipient list is the broker-email JSON from GitHub issue #23.)
11. **CAPTCHA-requiring sites are ordered first in the run queue** (see
    §10) so the user handles all human-interaction sites up front and can
    then leave the run unattended. The pre-run summary states this.
12. User confirms and starts the run.

### 2.5 Live run screen

13. The core screen. Matches the original mock, with the following
    concrete rendering rules:
    - Emoji/icon key always visible in a sticky header. Two groups:
      - **Run status** (this run, live): ✅ complete, ❌ unable to
        complete, ➖ skipped, 🔄 in progress, ⏳ waiting on user (CAPTCHA).
      - **Health status** (from the nightly remote file, see below): 🟥
        the site's most recent nightly health check failed, ❓ health
        status unknown (the site is not present in the remote health
        file). A site with no health marker passed its last check.
    - Health status is a per-site badge shown *alongside* the run-status
      icon, not instead of it — e.g. a site can be 🔄 in progress and 🟥
      known-unhealthy at the same time. It is read from a remote file that
      the maintainer's overnight health-check job publishes and updates
      nightly (a flat `site -> ok|fail` map; see
      `next_phase_implementation_plan.md` §4). The app fetches this file
      once at run start (and it is the *only* non-broker, non-2Captcha
      network call the app makes); if the fetch fails, every site shows ❓.
    - Header also shows running counts: sites total, completed, failed,
      skipped, remaining, plus known-unhealthy (🟥) — updates live.
    - The scrollable site list is a separate pane from the header/stats,
      so stats are always visible regardless of scroll position.
    - **Horizontal scroll must work via Shift+Scroll** — this is a native
      browser behavior for any element with `overflow-x: auto` and content
      wider than its container; it does not need custom JS, but it
      **must be manually tested** across Chrome/Firefox on both Windows
      and Linux, and at multiple window sizes/aspect ratios, since this
      was flagged as a hard requirement, not a nice-to-have.
    - Each site entry expands to show info sent (which fields), and which
      rights were requested/completed, matching the original mock's
      per-site checklist format.
14. A **right-hand panel** appears only when a CAPTCHA needs the user's
    attention (see [§8](#8-captcha-handling) for the two different UIs this
    panel renders depending on CAPTCHA type). When nothing needs attention,
    this panel is empty/collapsed.
15. This whole screen polls the backend (see [§9](#9-frontend-architecture),
    [§10](#10-background-job-execution)) — no websockets, no SSE, plain
    `fetch()` on an interval.

### 2.6 Completion

16. Once all sites have been attempted, a final export is generated
    (profile + full run metadata: what was sent, when, what rights were
    used, per-site outcome).
17. Options offered:
    - Save the final export to a user-chosen location (native file-save
      dialog via the browser's download flow, or a filesystem path input
      if running in a context without one).
    - Generate a calendar reminder (`.ics` file — no external calendar API
      needed, `.ics` is a static file format any calendar app can import)
      for a 6-month or 1-year follow-up, **only offered for sites where
      opt-out + delete were *not* both completed** — if both are done, a
      reminder isn't useful, so don't offer it for those sites.
    - A reminder of the email-based brokers (§2.4 item 10): re-offer the
      per-state pre-filled email links for any the user didn't send before
      the run.
    - Links out: back to the project repo, to the email/blog resources
      (GitHub issues #19, #37).

---

## 3. Architecture overview

```
┌─────────────────────────────────────────────────────────┐
│  Windows: single PyInstaller-bundled .exe                │
│  Linux: Docker container (Compose-managed)                │
│                                                             │
│   ┌───────────────────────────────────────────────────┐  │
│   │  Django app (runserver on localhost)                │  │
│   │                                                       │  │
│   │   - Server-rendered templates: welcome, info entry,  │  │
│   │     redaction/CAPTCHA-mode settings, export/import,  │  │
│   │     completion screen. Zero JS.                      │  │
│   │                                                       │  │
│   │   - DRF API (JSON) + one hand-written-JS page:        │  │
│   │     live run screen (site list + CAPTCHA panel).      │  │
│   │                                                       │  │
│   │   - SQLite database (single file, encrypted PII       │  │
│   │     columns — see §11).                               │  │
│   │                                                       │  │
│   │   - Background worker thread: pulls the next site off │  │
│   │     a queue, drives pydoll against real Chrome,        │  │
│   │     writes status to SQLite as it goes. Sequential,    │  │
│   │     not parallel (see §10 for why).                    │  │
│   └───────────────────────────────────────────────────┘  │
│                                                             │
│   Real Chrome/Chromium process, driven by pydoll over CDP. │
│   Headless by default; headed only for the debug flag or   │
│   widget-CAPTCHA solve-in-UI (§1, §8.3.2). When headed, on │
│   Linux this is the container's Wayland-forwarded display, │
│   on Windows just a normal window.                         │
└─────────────────────────────────────────────────────────┘
```

Key architectural decisions and why:

- **Django templates for everything except one page.** Resolves the
  "minimal JS, but I want some corporate-flavor full-stack exposure"
  tension: Django REST Framework (a very standard piece of real-world
  Django stacks) powers the one page that's genuinely dynamic, consumed by
  plain `fetch()` rather than a JS framework. See [§9](#9-frontend-architecture).
- **No Celery/Redis/message broker.** At this scale (one profile, ~200
  sites run sequentially, single user), a plain Python background thread
  reading/writing a SQLite-backed queue table is sufficient and removes an
  entire category of operational complexity (broker install, worker
  process management) that would otherwise need to ship inside the
  installer too. See [§10](#10-background-job-execution).
- **SQLite stays.** Confirmed appropriate at this scale — the earlier
  concern was specifically about SQLite *inside a Docker bind-mount on
  Windows* (file-locking quirks across the WSL2/VM boundary), which is
  moot now that Windows doesn't use Docker as its primary path.
- **Docker only on Linux, only for the end-user runtime**, not for
  Windows distribution and not for development-only parity. Windows ships
  as a bundled native executable instead. See [§12](#12-distribution-and-installation).

---

## 4. Data model

Proposed Django apps and models. Field lists are the minimum needed to
support everything in §2 — add fields as needed during implementation, but
don't remove the encryption/versioning-relevant ones without re-reading
§11.

### `profiles` app

```python
class Profile(models.Model):
    # Encrypted at rest — see §11 for the encryption scheme. In practice
    # this likely means storing these as encrypted blobs in a single
    # `encrypted_pii` field rather than plain columns, OR using
    # field-level encryption (e.g. a custom EncryptedTextField). Decide
    # during implementation; either satisfies "PII isn't plaintext on
    # disk outside of export files."
    name = EncryptedTextField()
    phone_numbers = EncryptedJSONField()   # list of strings
    email_addresses = EncryptedJSONField() # list of strings
    vin = EncryptedTextField(blank=True)
    ssn_last4 = EncryptedTextField(blank=True)
    dl_image = EncryptedFileField(blank=True)
    dl_number = EncryptedTextField(blank=True)  # if OCR'd or user-entered

    redaction_level = models.IntegerField(choices=REDACTION_LEVEL_CHOICES)
    captcha_mode = models.CharField(choices=CAPTCHA_MODE_CHOICES)  # see §8
    twocaptcha_api_key = EncryptedTextField(blank=True)  # only if captcha_mode == "2captcha"

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Address(models.Model):
    profile = models.ForeignKey(Profile, related_name="addresses", on_delete=models.CASCADE)
    line1 = EncryptedTextField()
    line2 = EncryptedTextField(blank=True)  # apt/unit
    city = EncryptedTextField()
    state = models.CharField(max_length=2)   # NOT encrypted — needed for
                                              # rights/state-gating queries
    zip_code = EncryptedTextField()
    is_primary = models.BooleanField(default=True)
```

Note: `state` is deliberately left unencrypted on `Address` — it's needed
to drive the rights-gating logic in [§6](#6-rights-and-state-gating) via
plain SQL/ORM queries, and a two-letter state code isn't sensitive on its
own.

### `rights` app

```python
class Right(models.Model):
    # e.g. "access", "opt_out", "delete", "correct", "know_third_parties"
    code = models.SlugField(unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField()

class StateRightAvailability(models.Model):
    # Seeded from the shipped state -> privacy-rights data file (see §6),
    # re-seeded on app update. The file is source of truth and is what
    # GitHub issues edit; this table is just the queryable form of it.
    state = models.CharField(max_length=2)
    right = models.ForeignKey(Right, on_delete=models.CASCADE)
    available = models.BooleanField(default=True)
    statute_cite = models.CharField(max_length=100, blank=True)  # e.g. "325M.14 subd. 1(h)"

    class Meta:
        unique_together = ("state", "right")

class ProfileRightSelection(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    right = models.ForeignKey(Right, on_delete=models.CASCADE)
    selected = models.BooleanField(default=False)
```

### `scrapers` app — no model

Per-site metadata is **not** stored in the database. It lives as class
attributes on each scraper (see [§7](#7-scraper-manifest--declarative-per-site-metadata))
and is read at runtime by importing the scraper modules under
`src/dsar/broker_sites/`. A small helper (`scrapers/registry.py`) walks
those modules once per process, reads the attributes off each class, and
returns a list of plain in-memory records:

```python
@dataclass(frozen=True)
class ScraperInfo:
    site_domain: str
    display_name: str
    module_path: str            # for dynamic import at run time
    captcha_type: str           # "none" | "image" | "widget"
    required_fields: list[str]
    optional_fields: list[str]
    rights_supported: list[str]
```

At ~189 modules this import walk is cheap (well under a second) and removes
a whole sync-command + cache-table + staleness class of problems. The git
source is the only source of truth. If startup cost ever becomes a
concern, memoize the walk in module scope — still no database.

### `runs` app

```python
class ScraperRun(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(choices=[("pending","Pending"),("running","Running"),("complete","Complete")])

class SiteRunStatus(models.Model):
    run = models.ForeignKey(ScraperRun, related_name="sites", on_delete=models.CASCADE)
    site_domain = models.CharField(max_length=255)   # from ScraperInfo (§4 scrapers app)
    module_path = models.CharField(max_length=255)   # snapshotted at run start for dynamic import
    status = models.CharField(choices=[
        ("pending", "Pending"), ("in_progress", "In Progress"),
        ("waiting_captcha", "Waiting on CAPTCHA"),
        ("completed", "Completed"), ("failed", "Failed"),
        ("skipped", "Skipped"),
    ])
    info_sent = models.JSONField(default=list)     # field names actually sent
    rights_used = models.JSONField(default=list)    # right codes actually requested
    screenshot_path = models.CharField(max_length=500, blank=True)
    error_note = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

class CaptchaSession(models.Model):
    """One row per CAPTCHA the running scraper hits. Polled by the frontend
    and written to by the background worker — see §8, §10."""
    site_run = models.OneToOneField(SiteRunStatus, on_delete=models.CASCADE)
    captcha_type = models.CharField(choices=[("image","Image/Text"),("widget","Widget")])
    status = models.CharField(choices=[
        ("waiting", "Waiting on user"), ("answered", "Answered"),
        ("timed_out", "Timed out"),
    ])
    # image type:
    image_data_b64 = models.TextField(blank=True)
    user_answer = models.CharField(max_length=255, blank=True)
    # widget type (v1 = bring-window-forward, see §8.2):
    user_confirmed_continue = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

### `submissions` app — the one-time-submission ledger

Self-contained here (this supersedes `next_phase_implementation_plan.md` §3;
do not cross-reference it). The purpose: a real, non-dry-run submit to a
given broker must be **physically impossible to fire twice**, independent of
which `ScraperRun` it is, whether dry-run mode is toggled, or a bug in a
single site's scraper. A duplicate DSAR to the same broker reads as
spam/abuse and cannot be undone.

```python
class SubmittedRequest(models.Model):
    """Permanent record — NOT tied to a single ScraperRun. One row per
    broker that has ever received a real submission."""
    site_domain = models.CharField(max_length=255, unique=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    dry_run_at_time = models.BooleanField(default=False)  # always False for real rows; kept for audit
    screenshot_path = models.CharField(max_length=500)
```

**Mechanism** — a single `submit_once(site_domain, submit_locator, *, dry_run)`
helper in the `submissions` app that every scraper calls instead of a
hand-rolled submit/dry-run branch:

1. If a `SubmittedRequest` row exists for `site_domain` → **hard stop**:
   log a clear error, return without touching the submit control at all,
   regardless of `dry_run`. This is the one path that overrides
   `dry_run=False`.
2. Else if `dry_run` → screenshot + log intent + return. No row written
   (nothing was submitted).
3. Else (`dry_run=False`, no prior row) → click submit, take a post-submit
   screenshot, create the `SubmittedRequest` row, log confirmation.

Deleting a `SubmittedRequest` row is the *only* way to re-enable a real
submission to that site, and it is a deliberate manual action the user
takes by hand — never automated, and never done by the health-check job.
Document this in `docs/submission_safety.md` before migrating any scraper,
and roll out by migrating 1–2 low-risk scrapers first for sign-off on the
mechanism before sweeping the rest.

---

## 5. Redaction levels and field gating

Directly from the original spec, formalized as an explicit enum:

| Level | Name | Fields included |
|---|---|---|
| 0 | No redaction (not preferred) | Name, address, state, phone, email, DL image (full), DL number |
| 1 | Minimal | Name, address, state only |
| 2 | Minimal + photo | Name, address, state, DL photo |
| 3 | Minimal + DL number | Name, address, state, DL number (no photo) |
| 4 | Name + photo only | Name, DL photo only (no address/state) |

Level 0 is selectable but the form should show a plain-language warning
("this sends your unredacted driver's license photo and full details — not
recommended unless a specific site requires it") requiring the user to
actively confirm, same friction pattern as the plaintext-export choice in
[§11](#11-export--import-format).

**Important distinction**: phone, email, VIN, and SSN-last4 are **not**
part of the redaction level numbering above (the original spec's examples
only combine name/address/state/photo/DL#). These are gated independently,
per-scraper, via each scraper's `REQUIRED_FIELDS` / `OPTIONAL_FIELDS`
attributes (§7) — a site that needs a phone number to process a request
asks for it regardless of redaction level, and the pre-run summary screen
(§2.4) is where the user sees "this site requires fields your current
redaction level doesn't provide" and can choose to skip that site or supply
the field anyway.

The exact field set collected, and which fields each level and each scraper
actually needs, is **finalized by the maintainer in a dedicated PII
code-review pass**, not derived here — the tables above are the working
model, not the last word. (This is why `dob` appears in the §7 attribute
list but not in the level table: whether it's collected at all is part of
that review.)

---

## 6. Rights and state gating

**No state is ever hard-blocked.** Every US state is selectable. State
gating only *filters which rights are offered* and *warns* — it never stops
a user from running.

The driver is a **maintained state → privacy-rights map**, shipped as a
data file in the final release (JSON), seeded from the existing
`src/state_privacy_request_factory/` module (`StateHasPrivacyLaws` +
`state_name_abbreviation`). New and updated states are added over time
**via GitHub issues**, same cadence as the README's per-site notes — a
living reference, not a one-time migration. Where possible it should also
carry statute metadata (e.g. `325M.14 subd. 1(h)` for Minnesota's Right to
List of Third Parties) so the email generator (GitHub issue #24) can reuse
the same file.

On the info-entry rights step (§2.3):

1. Compute the user's state(s) from their `Address` rows.
2. Look each state up in the map.
   - **State has no active privacy law** → show a non-blocking warning
     ("your state has no active consumer-privacy law — requests may not be
     honored"), offer the generic access/opt-out/delete set, and let the
     user proceed.
   - **State has a law** → show exactly the rights that state grants; rights
     it doesn't grant (e.g. Right to List of Third Parties outside MN/OR)
     are shown disabled with the reason.
3. Selected rights become `ProfileRightSelection` rows, which then filter
   which rights each per-site scraper run attempts (cross-referenced
   against that scraper's `RIGHTS_SUPPORTED` attribute, §7).

---

## 7. Scraper manifest — declarative per-site metadata

Every scraper class (`src/dsar/broker_sites/<site>/*.py`, subclassing
`SuperScraper`) gets new declarative class attributes, added to the base
class with safe defaults so existing scrapers don't break:

```python
class SuperScraper:
    # existing attributes (DRY_RUN, REMOVE_INFORMATION, etc.) unchanged

    CAPTCHA_TYPE = "none"          # "none" | "image" | "widget"
    REQUIRED_FIELDS = []           # subset of: name, address, email, phone,
                                    # dob, vin, ssn_last4, dl_image, dl_number
    OPTIONAL_FIELDS = []
    RIGHTS_SUPPORTED = ["access", "opt_out", "delete"]  # sane default
    STATE_RESTRICTIONS = None      # e.g. {"know_third_parties": ["CA","CO",...]}
```

**These attributes are read directly at runtime — there is no database
table and no sync command.** `scrapers/registry.py` (§4) imports every
module under `src/dsar/broker_sites/` once per process and returns a list
of `ScraperInfo` records built from these attributes. The git source is
the only source of truth. This walk is cheap at ~189 modules; memoize it
in module scope if startup cost ever matters.

`CAPTCHA_TYPE` is the load-bearing one — it drives skip-CAPTCHA mode
(§8.2), CAPTCHA-site frontloading (§2.4, §10), and the MVP UI's
skip-all-CAPTCHA behavior (§2.0). `REQUIRED_FIELDS` / `OPTIONAL_FIELDS` /
`RIGHTS_SUPPORTED` are lower-stakes: an un-annotated scraper just defaults
to "no CAPTCHA, no required fields, generic rights" and gets corrected
when someone next touches that file (see
[§14](#14-migration-path-from-the-current-cli-scrapers)) — incremental,
not a blocking up-front pass over all ~189.

---

## 8. CAPTCHA handling

Three mutually-exclusive modes, chosen via radio button on its own step
right after the main info-entry form (§2.3):

### 8.1 Mode: 2Captcha API key

- Link to 2Captcha's signup page + a text input for the API key.
- Key stored encrypted on the `Profile` (§4).
- Wires directly into the `TwoCaptchaSolver` design from
  `docs/next_phase_implementation_plan.md` §2 — no new design needed here,
  just a UI to collect the key.
- **Fail fast on a missing key**: if this mode is selected, the CAPTCHA
  step will not let the user advance with the key field empty (client- and
  server-side validation). No "start the run and discover it later."
- **Validate the key at entry**: on submit of the CAPTCHA step, make one
  cheap 2Captcha API call (e.g. `getBalance`) to confirm the key is real
  and the account has a positive balance. A bad key or zero balance blocks
  advancing, with the specific reason shown.
- **Handle mid-flight failure**: the account can run dry during a run. When
  a solve call comes back with an out-of-balance / invalid-key error, the
  worker (a) stops attempting 2Captcha, (b) auto-skips the remaining
  CAPTCHA sites (marks them `skipped`, reason "2Captcha key stopped working
  mid-run"), (c) sets a persistent, dismissible warning banner on the live
  run screen so the user knows some sites were skipped and why. The run
  otherwise continues to completion — a dead key never aborts the whole
  run.

### 8.2 Mode: Skip CAPTCHA sites

- Simplest mode. At run-start (§2.4), any site whose `CAPTCHA_TYPE != "none"`
  (§7) is filtered out of the run entirely and shown as `skipped` with
  reason "CAPTCHA required, skip mode selected."
- No further design needed — this is a pure filter against the `ScraperInfo`
  data already described in §7. This is also the mode the MVP UI hard-codes
  (§2.0).

### 8.3 Mode: Solve in UI

This is the most involved mode and splits into two genuinely different
implementations depending on `captcha_type`:

#### 8.3.1 Image/text CAPTCHAs (`captcha_type == "image"`)

Straightforward, build this first:

1. Background worker detects the CAPTCHA element, crops/screenshots just
   that element (pydoll's existing screenshot capability, scoped to the
   element rather than full page).
2. Writes a `CaptchaSession` row: `captcha_type="image"`, `image_data_b64`
   set, `status="waiting"`. Also sets the parent `SiteRunStatus.status =
   "waiting_captcha"`.
3. Frontend's polling loop (§9) sees the `waiting_captcha` status, renders
   the image in the right-hand panel with a text input + submit button.
4. User submits an answer → `POST` to a DRF endpoint → writes
   `user_answer`, `status="answered"`.
5. Background worker, on its next poll of this `CaptchaSession`, picks up
   the answer, types it into the real page's CAPTCHA input field, and
   continues the scraper.

#### 8.3.2 Interactive widget CAPTCHAs (`captcha_type == "widget"`)

**The hard requirement driving this design: the user must never need to
interact with the actual pydoll-controlled Chrome window directly** — doing
so risks disrupting the automation (focus stealing, unexpected navigation,
breaking whatever wait/detection logic the scraper is mid-way through).

**Why you can't just re-render the widget in the Django app's own page**:
reCAPTCHA/hCaptcha/Turnstile validate the requesting origin against the
sitekey's registered domain allowlist. Rendering the widget on
`localhost:8000` (or wherever the Django app lives) instead of the broker
site's real domain will generally fail domain validation. This rules out
the "just show the widget in an iframe on our own page" approach as
unreliable — it needs to run in the context of the real page.

**v1 (build first) — bring the real window to the foreground**:

> **Headless interaction with the headless default (§1):** v1 needs a
> visible window, but scrapers run headless by default. Resolution: if the
> user picks "Solve in UI" mode *and* the computed run contains any
> `CAPTCHA_TYPE == "widget"` site, the app runs the whole run **headed**,
> regardless of the debug flag, and says so on the pre-run summary. Image
> CAPTCHAs (§8.3.1) don't need this — they're screenshotted and solved in
> the panel, so a run with only image CAPTCHAs stays headless.

1. Background worker detects the widget CAPTCHA, sets
   `SiteRunStatus.status = "waiting_captcha"` and creates a
   `CaptchaSession` with `captcha_type="widget"`.
2. Worker brings the real Chrome window to the foreground (OS-level
   window-focus call) so it's immediately visible to the user, exactly
   like the existing `input()`-blocking pattern already used in ~63
   scrapers today — just adapted from "blocks on stdin" to "blocks on a
   DB flag."
3. Frontend's right-hand panel shows: "A CAPTCHA needs solving — please
   switch to the browser window that just came to the front, solve it,
   then click Continue here." with a Continue button.
4. User solves it directly in the real window (this is the one narrow
   exception to "never interact with the real browser" — acceptable as a
   v1 because it's exactly what the existing 63 scrapers already require
   today; the real goal is to *not regress* the UX, and to build toward
   eliminating it in v2).
5. User clicks Continue in the web UI → `CaptchaSession.user_confirmed_continue = True` → worker resumes.

**v2 (stretch goal, build after v1 ships) — CDP screencast + input relay**:

This achieves the "never touch the real browser" goal fully, using Chrome
DevTools Protocol's native remote-viewing/remote-control support — the
same class of mechanism headless-browser cloud providers use for
"interact with a remote browser via a web UI":

1. `Page.startScreencast` (a real CDP method) streams live JPEG/PNG frames
   of the actual tab over the same CDP connection pydoll already holds —
   this requires access to the raw CDP session, not just pydoll's
   higher-level `tab.find()`/`execute_script()` wrapper (see
   [§16](#16-open-questions-to-verify-beforeduring-build) — verify pydoll
   exposes this before committing to this design).
2. Backend relays each frame to the frontend (plain HTTP polling of a
   "latest frame" endpoint is sufficient — CAPTCHA-solving doesn't need
   sub-100ms websocket-grade latency, a few hundred ms polling interval on
   a still image is fine).
3. Frontend renders the frame as an `<img>`, hand-written JS captures click
   coordinates (and drag, for slider-style challenges) relative to the
   image, `POST`s them to a DRF endpoint.
4. Backend replays those coordinates into the real tab via
   `Input.dispatchMouseEvent` (another real CDP method).
5. Because this is still the *same real page/session/cookies*, domain
   validation and fingerprinting stay correct — unlike re-rendering the
   widget elsewhere.

Do not attempt v2 before v1 ships and works reliably — v1 alone already
removes the CLI-only limitation (a GUI Continue button instead of a
terminal prompt) and is far lower risk to build.

---

## 9. Frontend architecture

- **Every page except the live run screen (§2.5)**: plain Django templates,
  standard `<form method="post">` submissions, Django's built-in CSRF
  protection, server-side validation, redirect-after-post. Zero JavaScript.
  This covers: welcome screen, info entry (multi-step), redaction/rights/
  CAPTCHA-mode selection, import/export screens, completion screen.
- **The live run screen**: server-rendered shell (the header/stats/list
  structure, initial site list from the `ScraperInfo` registry, §4/§7),
  plus one hand-written `<script>` block (no build step, no npm, no
  framework) that:
  - Polls a DRF endpoint (`GET /api/runs/<id>/status/`) every 1–2 seconds,
    diffs the returned site statuses against the DOM, and updates only
    what changed (don't re-render the whole list every poll — with ~200
    rows this matters for smoothness).
  - When a `waiting_captcha` status appears, fetches the relevant
    `CaptchaSession` and renders the appropriate panel (§8.3.1 or §8.3.2).
  - Submits CAPTCHA answers / continue-clicks via `fetch()` `POST`.
- **DRF's role**: a small, well-scoped API surface — this is deliberately
  the "corporate-pattern" piece (typed serializers, `APIView`/`ViewSet`
  classes) even though its only consumer is hand-written JS, not a SPA
  framework:
  - `GET /api/runs/<run_id>/status/` — list of site statuses.
  - `GET /api/runs/<run_id>/captcha/<site_run_id>/` — CAPTCHA session detail (image data, type, status).
  - `POST /api/runs/<run_id>/captcha/<site_run_id>/answer/` — image CAPTCHA text answer.
  - `POST /api/runs/<run_id>/captcha/<site_run_id>/continue/` — widget CAPTCHA v1 continue signal.
  - `GET /api/runs/<run_id>/captcha/<site_run_id>/frame/` — latest screencast frame (v2 only).
  - `POST /api/runs/<run_id>/captcha/<site_run_id>/click/` — relayed click coordinates (v2 only).

No CSS framework mandated here either — keep styling plain/hand-written CSS
given the "maintainable by one non-frontend person" constraint; a CSS
framework is optional polish, not a requirement of this plan.

---

## 10. Background job execution

**Sequential, not parallel.** Run one scraper at a time, not a pool. Two
independent reasons this is the right call, not just the simplest:

1. **Resource contention** — each scraper drives its own Chrome instance
   (headless or, for widget-CAPTCHA runs, headed); running many
   concurrently would be heavy on an ordinary user's machine and would
   make the "bring window to foreground" CAPTCHA flow (§8.3.2) ambiguous
   (which of N windows?).
2. **Bot-detection risk** — already observed and documented in project
   memory: TrustArc and app.termly.io both threw Cloudflare/PerimeterX
   "confirm you're human" walls after 5–8 rapid automated requests during
   testing. Sequential execution naturally paces requests; parallel
   execution across many sites sharing infra (many brokers use the same
   DSAR vendor platforms — OneTrust, TrustArc, Trust Superset, etc.) would
   multiply this risk.

**Queue ordering — CAPTCHA sites first.** When the run's `SiteRunStatus`
rows are created (at run start), order them so every site that needs human
CAPTCHA attention under the chosen mode comes first: solve-in-UI →
`CAPTCHA_TYPE != "none"` sites first; 2Captcha mode → no reordering needed
(solves are automatic); skip mode → moot (they're filtered out). This lets
the user clear all the interactive sites up front and then walk away while
the rest run unattended. The pre-run summary (§2.4) states the ordering.

**Implementation**: a single background thread (started when a
`ScraperRun` begins) that:
1. Pulls the next `pending` `SiteRunStatus` row for the current run, in the
   queue order above.
2. Dynamically imports the scraper module (`SiteRunStatus.module_path`),
   instantiates it with the `Profile` data (filtered by redaction level +
   that site's `REQUIRED_FIELDS`/`OPTIONAL_FIELDS`).
3. Runs it, updating `SiteRunStatus.status` as it progresses
   (`in_progress` → `waiting_captcha` (0+ times) → `completed`/`failed`).
4. On CAPTCHA, writes a `CaptchaSession` and polls it (in-process, e.g.
   `time.sleep(1)` loop with a timeout) until answered/timed-out, then
   resumes.
5. Real submits go through `submit_once()` (§4 `submissions` app), never a
   direct click — so a site that already has a `SubmittedRequest` row is
   hard-stopped even if it somehow re-enters the queue.
6. Repeats for the next site.

This is a plain Python thread — no task queue library needed. If the app
process restarts mid-run, the run can resume from the first `pending`
row on next launch (already-`completed`/`failed`/`skipped` rows aren't
re-attempted).

---

## 11. Export / import format

### 11.1 File format

A **zip bundle**, not raw JSON, once DL images are involved — base64-in-JSON
was considered and rejected: it bloats the file and makes it unreviewable
as "just my info." Bundle contents:

```
profile_export.zip
├── manifest.json          # schema_version, encrypted flag, KDF params if encrypted
├── profile.json.enc       # (or profile.json if plaintext) — all Profile/Address/rights fields
└── images/
    └── dl_image.jpg.enc   # (or .jpg if plaintext)
```

Two variants are generated automatically, matching the original spec's
"two copies" requirement:
- `profile_export.zip` — profile data only.
- `profile_export_with_run_history.zip` — same, plus a `runs/` directory
  containing every `ScraperRun`/`SiteRunStatus` record ever produced for
  this profile (what was sent, when, which rights, per-site outcome).

### 11.2 Schema versioning

`manifest.json` always includes a top-level `schema_version` integer.
**This is non-negotiable from the very first release** — the whole point
of the returning-user import flow (§2.2) is that an old export must still
import cleanly (or fail with a clear migration message) after the app has
been updated. On import:
1. Read `schema_version`.
2. If it matches current → import directly.
3. If older → run through a chain of versioned migration functions
   (`migrate_v1_to_v2`, etc.) before importing — same idea as Django's own
   migration system, just applied to the export format.
4. If newer than the running app supports → refuse with a clear "please
   update the app" message, don't attempt a lossy downgrade.

### 11.3 Encryption

Default: **encrypted**. Plaintext is an explicit, frictioned opt-out (a
confirmation checkbox: "this file will contain your unredacted PII in
plain text — are you sure?").

Correct primitives (not the originally-suggested "SHA-256 the password" —
hashing alone isn't encryption):

1. User provides a password at export time.
2. Generate a random 16-byte salt.
3. Derive a key via **PBKDF2-HMAC-SHA256**, salt as above, **600,000
   iterations** (current OWASP-recommended minimum for PBKDF2-SHA256 as of
   this writing — re-check the current recommendation at implementation
   time, this number drifts upward over the years), producing a 32-byte
   key, base64-urlsafe-encoded as required by `Fernet`.
4. Encrypt the JSON payload (and each image file) with `cryptography`'s
   `Fernet` (AES-128-CBC + HMAC under the hood — deliberately chosen over
   hand-rolled AES-GCM calls because Fernet is much harder to misuse).
5. Store `salt` (base64, not secret — needed to re-derive the key on
   import) and the KDF parameters in `manifest.json` alongside the
   ciphertext files.

On import with a password: re-derive the key from the stored salt +
provided password, attempt decryption — a wrong password naturally fails
Fernet's built-in authentication check, which doubles as a "wrong
password" detector without needing a separate check.

---

## 12. Distribution and installation

### 12.1 Linux (Docker, preferred)

- Ship a `docker-compose.yml` + a small install script (`install.sh`).
- The install script checks for Docker; if absent, prints install
  instructions for the user's detected package manager (or a link to
  Docker's own install docs) rather than attempting to install Docker
  itself — Docker installation varies too much across distros to safely
  automate.
- **Wayland, not X11, as the primary target** — X11 is no longer the
  default on most major distributions. The Compose file mounts
  `$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY` into the container and sets the
  corresponding env vars; Chromium is launched with
  `--ozone-platform=wayland`. Document XWayland as a fallback note, not
  the primary supported path.
- `docker compose up` brings up the Django app + dependencies; the
  install script opens `http://localhost:8000` in the default browser
  once the container reports healthy.

### 12.2 Windows (bundled executable, preferred)

- **Python + Django + all pip dependencies are bundled into a single
  `.exe` via PyInstaller (or Briefcase)** — this is a well-supported,
  standard PyInstaller use case, not a stretch. There is no separate
  "install Python" step for the end user at all.
- **Chrome is the one remaining external OS-level dependency.** First-run
  preflight, tiered fallback chain:
  1. Check `winget --version`. If present:
     `winget install -e --id Google.Chrome --silent`.
  2. If winget is absent: fall back to a PowerShell script (`Invoke-WebRequest`
     — built into PowerShell since v3, more universally available than
     depending on `curl.exe`) that downloads Google's stable direct-download
     Chrome Enterprise MSI and runs `msiexec /i chrome_installer.msi /qn`.
  3. If both fail (no internet, policy-blocked environment): show manual
     install instructions, with the Windows+Docker path (below) documented
     as a last-resort alternative.
- Rationale for this ordering (not defaulting to Docker on Windows, per
  earlier discussion): Docker Desktop requires enabling virtualization,
  WSL2, a multi-hundred-MB install, and is only free for individuals/
  small business/education under Docker's subscription terms — meaningfully
  heavier than checking for/installing a browser that's very likely already
  present. Winget itself ships preinstalled on Windows 11 and via the
  Store's App Installer on most current Windows 10 — the PowerShell
  fallback exists specifically to cover the minority of locked-down/older
  environments where it's missing, without making Docker the default
  answer to that gap.

### 12.3 Windows (Docker, documented secondary option)

- Feasible via WSL2 + WSLg (Windows 11, and backported to recent Windows
  10 builds, ships GUI support for WSL2/Linux containers natively — no
  separate X server needed).
- Document as an alternative in the README for users who prefer it or
  already have Docker set up, with the caveat that it's a deeper
  prerequisite stack (WSL2 → WSLg → Docker Desktop) than the bundled-exe
  path, which is why it isn't the default.

### 12.4 Build pipeline

- Both artifacts (Windows `.exe`, Linux Compose bundle) should be produced
  by **GitHub Actions from tagged source**, not built locally and
  uploaded — this matters for the trust story in [§13](#13-trust-and-security-posture-no-code-signing).
- No manifest sync step is needed — per-site metadata is read from the
  scraper classes at runtime (§7), so a "stale manifest" cannot ship. The
  build should still run the `ScraperInfo` registry walk once as a smoke
  test that every scraper module imports cleanly.

---

## 13. Trust and security posture (no code signing)

**Decision: no code signing.** Standard (non-EV) Windows Authenticode
certs run ~$70–250/year, EV certs (instant SmartScreen trust) run
$300–600+/year and typically require a registered business entity — not
proportionate for a project that's explicitly not generating any revenue.
Linux/AppImage has no equivalent signing ecosystem in practice regardless.

Given this handles PII "at an uncomfortable level," the trust story
matters more than for a typical unsigned hobby tool. The free stack that
substitutes for signing:

1. **Build provenance**: GitHub Actions builds each release directly from
   tagged source (§12.4), using GitHub's free **artifact attestation**
   feature (available for public repos) to cryptographically tie each
   release binary to the exact commit/workflow that built it. This is a
   *stronger*, independently-checkable claim than a signing cert for an
   open-source project: "this exact binary came from this exact public
   source," rather than "a certificate authority verified an identity."
2. **VirusTotal scan per release** — free, ~2 minutes, link the report in
   each release's notes. The de facto standard trust signal for small
   OSS Windows/Linux tools.
3. **"Run from source" stays a first-class, documented option** — for any
   user who doesn't want to trust a binary at all, given the sensitivity
   of what this handles. Don't bury this as an afterthought.
4. **A `SECURITY.md` documenting exactly what network calls the app
   makes** — the broker sites themselves, plus 2Captcha only if the user
   opts into that CAPTCHA mode. This lets a skeptical (rightly so, given
   PII) user verify with their own firewall/traffic monitor rather than
   take the README's word for it.
5. **Static/dependency scanning in CI** (e.g. `bandit` for Python security
   lint, `pip-audit` for known-vulnerable dependencies) — free, catches
   accidental issues, and is another concrete "something checked this"
   signal worth mentioning in the README.

If a release is ever incorrectly flagged by Windows SmartScreen/Defender,
Microsoft has a free false-positive submission portal — use it reactively
if/when it actually happens, not proactively.

---

## 14. Migration path from the current CLI scrapers

The ~189 existing scrapers don't need a big-bang rewrite. Sequenced to
avoid blocking the GUI work on annotating all of them up front:

1. **Add the new declarative class attributes to `SuperScraper`** (§7)
   with safe defaults (`CAPTCHA_TYPE = "none"`, empty field lists, default
   rights). Existing scrapers keep working unmodified — nothing breaks.
2. **Build `scrapers/registry.py`** (§4) — the runtime import walk that
   turns those attributes into `ScraperInfo` records. Against unmodified
   scrapers it just yields the safe defaults. No management command, no
   table, no migration.
3. **Build the Django app against these "mostly default" `ScraperInfo`
   records first.** The GUI, data model, run screen, and CAPTCHA-mode
   plumbing can all be built and tested before every scraper is accurately
   annotated — a scraper still on `CAPTCHA_TYPE = "none"` just won't get
   filtered by skip-CAPTCHA mode until someone sets it, which is a
   data-quality gap to close over time, not a blocker.
4. **Annotate scrapers incrementally**, same cadence as the original
   per-site build effort tracked in project memory — when touching a
   scraper for any reason (fixing a bug, verifying it still works), fill
   in its real `CAPTCHA_TYPE`/`REQUIRED_FIELDS`/`OPTIONAL_FIELDS`/
   `RIGHTS_SUPPORTED`. Keep a checklist (README or a plain list) of which
   sites still have default metadata so progress is visible. Getting
   `CAPTCHA_TYPE` right everywhere is the priority; the field/rights lists
   can lag and get finalized in the maintainer's PII code-review pass
   (§5).
5. **Replace `.env`-driven config with the `Profile` model** — the
   scraper classes themselves change least here; what changes is what
   constructs and passes them their input data (the background worker
   from §10, instead of a CLI entrypoint reading `.env`). The MVP UI
   (§2.0) is the intermediate step: it still reads `.env`, but through the
   same `Profile` object the worker expects.
6. **Wire `captcha_solver.py`** (from `next_phase_implementation_plan.md`
   §2) as the backend for the 2Captcha mode: `TwoCaptchaSolver` unchanged;
   add a new `WebUISolver` implementing the same interface, backed by the
   `CaptchaSession` polling loop from §8.
7. **Build the submission ledger** (§4's `submissions` app) as specified
   there — self-contained, not carried over from
   `next_phase_implementation_plan.md` §3.

---

## 15. Phased rollout plan

Suggested build order — each phase should be independently testable/usable
before moving to the next, so the project never has a long stretch of
"nothing runs end-to-end."

- **Phase 0 — environment setup.** Django project skeleton, SQLite,
  `profiles`/`rights`/`runs`/`submissions` apps scaffolded (empty models
  are fine initially) plus `scrapers/registry.py` (no models). 
- **Phase 1 — MVP UI (Epic #9 / issue #34).** `SuperScraper` gets the §7
  attributes (at least `CAPTCHA_TYPE`); `scrapers/registry.py`; a
  `Profile` populated from `.env`; the sequential worker (§10); the live
  run screen (§2.5) with polling (§9). CAPTCHA sites are skipped (§2.0).
  No forms, no export, no state gating, headless. This is the first
  end-to-end runnable thing.
- **Phase 2 — data entry & export (Full-Release, no scraper changes).**
  Welcome screen (incl. the §2.2 disclosures), full info-entry flow,
  redaction levels, rights selection driven by the state → rights data
  file (§6), encrypted export/import round-trip end to end. Independently
  testable — PII handling and the returning-user flow before any further
  scraper work.
- **Phase 3 — pre-run summary + full sequential execution.** The pre-run
  summary screen (§2.4) rendering a real filtered site list (incl.
  email-broker links and CAPTCHA-first ordering) against a form-entered
  profile; worker + run screen driven by that profile instead of `.env`.
  CAPTCHA sites still auto-skipped so the pipeline is validated without
  CAPTCHA complexity.
- **Phase 4 — CAPTCHA modes (a) and (b) for real, plus image CAPTCHAs
  under (c).** 2Captcha key collection + `TwoCaptchaSolver` wiring, real
  skip-mode filtering, image-CAPTCHA-in-panel (§8.3.1).
- **Phase 5 — widget CAPTCHA v1** (§8.3.2: bring-window-forward +
  Continue button). This unblocks the majority of currently-manual sites
  for GUI use without needing the CDP relay yet.
- **Phase 6 — packaging & distribution.** Linux Docker Compose + Wayland
  passthrough, Windows PyInstaller build + dependency preflight chain
  (§12).
- **Phase 7 — trust/security stack.** GitHub Actions provenance builds,
  VirusTotal scanning, `SECURITY.md`, CI static/dependency scanning
  (§13).
- **Phase 8 — stretch: CDP screencast + input relay for widget
  CAPTCHAs** (§8.3.2 v2). Only after confirming pydoll exposes the needed
  raw CDP access (§16) — this is genuinely the highest-uncertainty piece
  of the whole plan and shouldn't be scheduled before everything else
  works.

---

## 16. Open questions to verify before/during build

These are things this plan assumes or estimates that should be confirmed
against real code/behavior before or during implementation, not taken as
settled fact:

1. **Does pydoll expose the raw CDP session/websocket**, or only its
   higher-level wrapper methods (`tab.find()`, `execute_script()`,
   `take_screenshot()`)? This determines whether §8.3.2's v2 design
   (`Page.startScreencast` / `Input.dispatchMouseEvent`) is buildable as
   described, or needs a second CDP connection opened alongside pydoll's.
   Check pydoll's source/docs directly.
2. **Confirm reCAPTCHA/hCaptcha/Turnstile's actual domain-validation
   behavior** empirically against 2–3 real broker sites before investing
   engineering time in the v2 CDP relay — the plan assumes rendering a
   widget off-domain fails, which is the documented general behavior, but
   worth a quick real check given how much of §8.3.2's design rests on it.
3. **PBKDF2 iteration count (600,000)** is current OWASP guidance as of
   this writing but drifts upward over time and trades off against
   encrypt/decrypt latency on lower-end machines — re-check the current
   recommended figure at implementation time, and sanity-test the actual
   wall-clock cost on a modest machine (this runs client-side on export/
   import, not per-request, so even a few hundred ms is likely fine, but
   verify rather than assume).
4. **Exact field list per scraper and overall** (`REQUIRED_FIELDS`/
   `OPTIONAL_FIELDS` in §7, and which fields the app collects at all) — the
   maintainer owns this as a dedicated PII code-review pass (§5), done
   once the rest is working. Not a blocker for earlier phases; the safe
   defaults hold until then. Includes deciding whether `dob` and any other
   currently-collected field is actually needed (GitHub issue #28's "cull
   unnecessary PII").
5. **Windows winget/Chrome MSI URLs**: confirm the current stable
   direct-download URL for the Chrome Enterprise MSI at implementation
   time (Google occasionally changes these) rather than hardcoding
   whatever's found during planning.

---

## 17. Decision log

Chronological record of decisions made across the design discussions that
produced this plan, for anyone (including future-you) wondering "why is it
built this way":

- Docker was the original default assumption for everything; narrowed to
  Linux-only after establishing that the workflow must be *able* to show a
  visible browser window (for widget-CAPTCHA solving and the debug flag),
  which containers handle poorly on Windows specifically (no native GUI
  passthrough without extra layers), and that requiring Docker Desktop is a
  heavier install-time ask than a bundled native executable.
- Headed-by-default was the original assumption; flipped to **headless by
  default** (debug flag or widget-CAPTCHA-solve-in-UI to show the window)
  per GitHub issue #35 — a visible automated browser during a normal run is
  noise, not a feature.
- The one-time-submission ledger was originally specced in
  `next_phase_implementation_plan.md` §3 as a flat JSON file; that document
  is now superseded for the ledger and the design lives self-contained in
  §4 here as a Django model.
- A `ScraperManifest` DB table + `sync_scraper_manifest` command was
  proposed to cache per-site metadata; dropped in favor of reading the
  scraper class attributes directly at runtime (§7) — at ~189 modules the
  import walk is cheap and a cache table only adds a staleness failure
  mode.
- HTMX/Alpine.js was proposed first as a low-JS middle ground, then
  dropped in favor of plain Django templates + one hand-written-JS page
  after establishing that (a) minimal JS/no build tooling was a hard
  requirement and (b) HTMX isn't actually representative of common
  corporate stacks either, so it satisfied neither goal as well as the
  final split.
- A React+TypeScript island (via Vite) was proposed as the "corporate
  pattern" option for the one dynamic page; rejected specifically because
  it requires npm alongside the existing pip-based toolchain, which the
  user explicitly did not want to maintain solo. Resolved by keeping DRF
  (a real corporate-pattern piece) as the API layer, consumed by
  hand-written JS instead of a framework.
- AppImage was the original day-one proposal for Linux distribution;
  superseded by Docker Compose + Wayland passthrough once Docker was
  established as the preferred Linux path specifically (not superseded on
  Windows, where Docker was ruled out in favor of a bundled exe).
- "SHA-256 the password" was the originally-proposed encryption approach;
  corrected to PBKDF2 (key derivation) + Fernet (actual symmetric cipher),
  since hashing alone isn't encryption.
- Code signing was ruled out entirely on cost grounds (project generates
  no revenue); replaced with a free trust stack (build provenance,
  VirusTotal, source availability, documented network behavior) rather
  than left unaddressed, given the PII sensitivity involved.

import asyncio
import inspect
import os
import random
import time

import dotenv

from pydoll.browser.options import ChromiumOptions

from src.dsar import js_utils
from src.dsar.exceptions import RequiredFieldError, RightsChangedError
from src.dsar.rights import RIGHT_DISPLAY, Right
from src.state_privacy_request_factory import state_privacy_data
from src.state_privacy_request_factory.state_privacy_data import (
    UnknownStateError,
    law_name,
    request_basis,
    rights_available,
    state_abbreviation,
    state_has_privacy_law,
    statute_cite,
)


class SuperScraper:
    Right = Right  # SuperScraper.Right.RIGHT_TO_ACCESS etc.

    dotenv.load_dotenv()
    # System-related information
    # NOTE: flags are compared against a stripped/upper-cased string rather than truthiness —
    # os.getenv("DRY_RUN") returns the literal string "False" when the .env value is False,
    # and non-empty strings are truthy in Python.
    HEALTH_CHECK = (os.getenv("HEALTH_CHECK") or "").strip().upper() in ("TRUE", "1", "YES")
    # A health check never submits, so it implies a dry run.
    DRY_RUN = HEALTH_CHECK or (os.getenv("DRY_RUN") or "True").strip().upper() in ("TRUE", "1", "YES")
    # Like DRY_RUN (never submits) but additionally asserts every required field could be
    # filled and that the page's offered rights still match the scraper's PAGE_RIGHTS
    # inventory. Screenshots are taken (for the LLM-review stage of the health pipeline).
    # Run Chromium with no visible window. Default False — several forms need a visible
    # window for a manual CAPTCHA solve during a live (non-DRY_RUN) run.
    HEADLESS_BROWSER_MODE = (os.getenv("HEADLESS_BROWSER_MODE") or "False").strip().upper() in ("TRUE", "1", "YES")
    TWO_CAPTCHA_API_KEY = os.getenv("TWO_CAPTCHA_API_KEY")
    # Cast to int — pydoll compares this against a float clock, so a raw
    # os.getenv() string ("10") raises "'>' not supported between float and str"
    # the moment any find() has to poll for a missing/slow element.
    BASE_TIMEOUT_IN_SECONDS = int(os.getenv("BASE_TIMEOUT_IN_SECONDS") or "10")
    CHROMIUM_LOCATION = os.getenv("CHROMIUM_LOCATION")

    # Personal information
    FIRST_NAME = os.getenv("FIRST_NAME")
    LAST_NAME = os.getenv("LAST_NAME")
    EMAIL = os.getenv("EMAIL")
    ADDRESS = os.getenv("ADDRESS")
    ADDRESS_LINE_TWO = os.getenv("ADDRESS_LINE_TWO")
    CITY = os.getenv("CITY")
    STATE = os.getenv("STATE")
    ZIP_CODE = os.getenv("ZIP_CODE")
    DATE_OF_BIRTH = os.getenv("DATE_OF_BIRTH")
    LAST_FOUR_SSN = os.getenv("LAST_FOUR_SSN")
    LINKEDIN_URL = os.getenv("LINKEDIN_URL")
    FACEBOOK_URL = os.getenv("FACEBOOK_URL")
    TWITTER_URL = os.getenv("TWITTER_URL")
    INSTAGRAM_URL = os.getenv("INSTAGRAM_URL")
    JOB_TITLE = os.getenv("JOB_TITLE")
    COMPANY_NAME = os.getenv("COMPANY_NAME")
    PHONE_NUMBER = os.getenv("PHONE_NUMBER")

    ADVERTISING_ID = os.getenv("ADVERTISING_ID")
    OOPS = ""

    # --- State-derived config (from src/state_privacy_request_factory/state_privacy_data.json) ---
    # Computed once here so scrapers don't re-derive it on every run. Wrapped so a
    # missing/misspelled STATE degrades to None + a warning instead of failing every import.
    try:
        STATE_ABBREVIATED = state_abbreviation(STATE) if STATE else None
        LAW_FULL_NAME = law_name(STATE) if STATE else None
        LAW_SHORT_NAME = law_name(STATE, short=True) if STATE else None
        # e.g. "under the Minnesota Consumer Data Privacy Act"; None for no-law states.
        REQUEST_BASIS = request_basis(STATE) if STATE else None
    except UnknownStateError:
        print(f"{__name__}: WARNING — STATE={STATE!r} is not a recognised US state; "
              "STATE_ABBREVIATED / LAW_* left unset.")
        STATE_ABBREVIATED = None
        LAW_FULL_NAME = None
        LAW_SHORT_NAME = None
        REQUEST_BASIS = None

    # --- Which privacy rights the user wants to exercise (set from the UI's user input) ---
    # .env RIGHTS_TO_EXERCISE is a comma-separated list of Right names. Unset => access,
    # opt-out and list-of-third-parties; deletion is destructive so it must be asked for
    # explicitly (RIGHT_TO_DELETE).
    _requested_raw = [c for c in (os.getenv("RIGHTS_TO_EXERCISE") or "").split(",") if c.strip()]
    _parsed = [Right.parse(c) for c in _requested_raw]
    if any(r is None for r in _parsed):
        print(f"{__name__}: WARNING — ignoring unknown RIGHTS_TO_EXERCISE values: "
              f"{[c for c, r in zip(_requested_raw, _parsed) if r is None]}")
    RIGHTS_TO_EXERCISE = frozenset(r for r in _parsed if r is not None) if _requested_raw else frozenset(
        {Right.RIGHT_TO_ACCESS, Right.RIGHT_TO_OPT_OUT, Right.RIGHT_TO_LIST_OF_THIRD_PARTIES}
    )

    # --- Declarative per-scraper metadata (frontend_implementation_plan.md §7). Safe
    # defaults; individual scrapers override at module or class level as they are touched. ---
    CAPTCHA_TYPE = "none"          # "none" | "image" | "widget"
    REQUIRED_FIELDS = ()
    OPTIONAL_FIELDS = ()
    RIGHTS_SUPPORTED = ()          # Right members this scraper's form can exercise
    STATE_RESTRICTIONS = None
    NOT_AUTOMATABLE = False        # True => cannot run unattended (mid-run OTP, etc.)
    NOT_AUTOMATABLE_REASON = ""
    SITE_SLUG = ""                # canonical slug for screenshot filenames

    def __init__(self):
        rand = random.randrange(start=1, stop=100)
        if rand == 100:
            SuperScraper.OOPS = "FUCK"
        elif SuperScraper.STATE and SuperScraper.STATE.upper() != "MINNESOTA":
            SuperScraper.OOPS = "Oops!"
        elif rand % 2:
            SuperScraper.OOPS = "Ope!"
        else:
            SuperScraper.OOPS = "Uufda!"

    # ------------------------------------------------------------------ #
    #  Rights selection                                                   #
    # ------------------------------------------------------------------ #
    @classmethod
    def rights_to_exercise(cls, right_map) -> list:
        """Ordered ``Right`` members to actually exercise for this run — THE gate every
        scraper uses (never read RIGHTS_TO_EXERCISE directly).

        ``right_map`` is the scraper's ``RIGHT_MAP`` (``Right`` -> that scraper's own
        entry or list of entries). A right is kept when it is in ``RIGHTS_TO_EXERCISE``
        AND (the user's state grants it, OR the state has no comprehensive privacy law —
        a site written for CCPA applies the same way). Returned in ``right_map`` order.
        """
        granted = rights_available(cls.STATE) if cls.STATE else frozenset()
        no_law = not (state_has_privacy_law(cls.STATE) if cls.STATE else False)
        return [
            right for right in right_map
            if right in cls.RIGHTS_TO_EXERCISE and (no_law or right.value in granted)
        ]

    @classmethod
    def request_statement(cls, rights, *, broker: str | None = None) -> str:
        """Freeform "I am a <state> resident ..." sentence for a message / details
        textarea. Cites the state's law (from state_privacy_data.json ``request_basis``)
        only when the state has one."""
        state_title = cls.STATE or "US"
        basis = f" {cls.REQUEST_BASIS}" if cls.REQUEST_BASIS else ""
        cites = [c for c in (statute_cite(cls.STATE, r.value) for r in rights) if c] if cls.REQUEST_BASIS else []
        cite_clause = f" (see {'; '.join(dict.fromkeys(cites))})" if cites else ""
        human = ", ".join(RIGHT_DISPLAY[r] for r in rights) or "my applicable privacy rights"
        held = f" that {broker} and its affiliates hold about me" if broker else " held about me"
        return (
            f"I am a {state_title} resident and I am exercising my privacy rights{basis}{cite_clause}. "
            f"I request the following with respect to the personal information{held}: {human}."
        )

    # ------------------------------------------------------------------ #
    #  Not-automatable guard                                              #
    # ------------------------------------------------------------------ #
    @staticmethod
    def bail_if_not_automatable(namespace) -> bool:
        """Call at the very top of ``main()`` as
        ``if SuperScraper.bail_if_not_automatable(globals()): return``.
        Returns True (and prints why) if the scraper declares ``NOT_AUTOMATABLE``.
        """
        if namespace.get("NOT_AUTOMATABLE"):
            reason = namespace.get("NOT_AUTOMATABLE_REASON") or (
                "requires a human to enter a verification code (SMS/email) mid-run"
            )
            slug = namespace.get("SITE_SLUG") or namespace.get("__name__", "scraper")
            print(f"SKIP {slug}: not automatable — {reason}")
            return True
        return False

    @staticmethod
    def bail_if_state_unsupported(namespace) -> bool:
        """Call right after ``bail_if_not_automatable`` in ``main()``. Returns True (and
        prints why) when the user's state has no comprehensive privacy law but the
        scraper declares ``SERVES_NO_LAW_STATES = False`` (its form only takes residents
        of states with a privacy law). Scrapers that don't declare it serve everyone."""
        if namespace.get("SERVES_NO_LAW_STATES", True):
            return False
        if SuperScraper.state_has_privacy_law(SuperScraper.STATE):
            return False
        slug = namespace.get("SITE_SLUG") or namespace.get("__name__", "scraper")
        print(f"SKIP {slug}: form is only for residents of states with a privacy law "
              f"(STATE={SuperScraper.STATE!r} has none).")
        return True

    # ------------------------------------------------------------------ #
    #  Browser options / screenshots                                      #
    # ------------------------------------------------------------------ #
    @classmethod
    def build_chromium_options(cls, *, extra_args=()) -> ChromiumOptions:
        """Standard ChromiumOptions: binary location + --no-sandbox, headless only if
        not HEADLESS_BROWSER_MODE, and never a --window-size (those were a screenshot-testing artifact)."""
        options = ChromiumOptions()
        if cls.CHROMIUM_LOCATION:
            options.binary_location = cls.CHROMIUM_LOCATION
        options.add_argument("--no-sandbox")
        if cls.HEADLESS_BROWSER_MODE:
            options.add_argument("--headless=new")
        for arg in extra_args:
            options.add_argument(arg)
        return options

    @staticmethod
    def _calling_scraper_name(default="scraper") -> str:
        """Name of the scraper that called us: the directory of the nearest
        ``*_scraper.py`` frame on the stack (``broker_sites/<name>/<name>_scraper.py``)."""
        for frame in inspect.stack()[2:]:
            if frame.filename.endswith("_scraper.py"):
                return os.path.basename(os.path.dirname(frame.filename)) or default
        return default

    @staticmethod
    async def screenshot(tab, label, *, max_pages=20):
        """Screenshot the whole page as a series of viewport shots — ONLY in DRY_RUN or
        HEALTH_CHECK (no-op on a live run). Saved to
        ``resources/screenshots/<scraper>/<label>_p01.png`` ``_p02`` ...; the scraper
        name is taken from the calling scraper file, never hard-coded.

        Scrolls to the top, then repeats: shoot, page down, stop when scroll position
        no longer changes (so each viewport is audited, not one stretched capture).
        """
        if not (SuperScraper.DRY_RUN or SuperScraper.HEALTH_CHECK):
            return []
        directory = os.path.join("resources", "screenshots", SuperScraper._calling_scraper_name())
        os.makedirs(directory, exist_ok=True)
        await js_utils.js_eval(tab, "window.scrollTo(0, 0); return window.scrollY;")
        saved = []
        for page in range(1, max_pages + 1):
            await asyncio.sleep(0.3)
            before = await js_utils.js_eval(tab, "return window.scrollY;")
            path = os.path.join(directory, f"{label}_p{page:02d}.png")
            await tab.take_screenshot(path=path)
            saved.append(path)
            await js_utils.js_eval(tab, "window.scrollBy(0, window.innerHeight - 40); return window.scrollY;")
            await asyncio.sleep(0.3)
            after = await js_utils.js_eval(tab, "return window.scrollY;")
            if after == before:
                break
        print(f"Screenshots saved: {saved[0]}" + (f" … {saved[-1]} ({len(saved)} pages)" if len(saved) > 1 else ""))
        return saved

    # ------------------------------------------------------------------ #
    #  Health-check field validation                                      #
    # ------------------------------------------------------------------ #
    @staticmethod
    async def assert_fields_filled(tab, fields, *, raise_on_fail=True):
        """``fields``: {label: xpath}. Reads each element's value/checked/text and
        collects the labels that are still empty. Raises RequiredFieldError if any
        (and ``raise_on_fail``). Intended for HEALTH_CHECK runs, where nothing is
        submitted so an unfilled required field would otherwise go unnoticed."""
        missing = []
        for label, xpath in fields.items():
            el = await tab.find(xpath=xpath, raise_exc=False)
            if not el:
                missing.append(label)
                continue
            value = await js_utils.js_eval(
                el,
                "return ((this.value != null ? this.value : (this.textContent || '')).trim())"
                " || (this.checked ? 'x' : '');",
            )
            if not value:
                missing.append(label)
        if missing and raise_on_fail:
            raise RequiredFieldError(missing)
        return {label: (label not in missing) for label in fields}

    @staticmethod
    async def read_option_labels(tab, css):
        """Visible text of every element matching ``css`` (e.g. ``"#rights option"``,
        ``"[role=option]"``, ``"fieldset label"``), whitespace-collapsed, blanks dropped.
        Open any dropdown/accordion first. Feed the result to ``audit_rights``."""
        raw = await js_utils.js_eval(
            tab,
            f"return Array.from(document.querySelectorAll({css!r})).map(function(e)"
            "{return (e.innerText||e.textContent||'').replace(/\\s+/g,' ').trim();});",
        )
        return [t for t in (raw or []) if t]

    @staticmethod
    def audit_rights(offered, page_rights, *, raise_on_fail=True):
        """Compare the right options the page offers now with the scraper's committed
        ``PAGE_RIGHTS`` inventory ({exact option label: Right or None}; ``None`` marks an
        option we deliberately don't automate, e.g. right to correct).

        Prints the full list, then raises ``RightsChangedError`` if a mapped label has
        vanished OR the page offers a label not in the inventory. HEALTH_CHECK only.
        """
        norm = lambda t: " ".join(t.split()).casefold()
        offered_n = {norm(o): o for o in offered}
        known_n = {norm(k): k for k in page_rights}
        print("Rights offered on page:")
        for o in offered:
            mapped = page_rights.get(known_n.get(norm(o)))
            print(f"  - {o}  ->  {mapped.name if mapped else ('(not automated)' if norm(o) in known_n else 'NEW')}")
        missing = [known_n[k] for k in known_n if k not in offered_n]
        new = [offered_n[k] for k in offered_n if k not in known_n]
        if (missing or new) and raise_on_fail:
            raise RightsChangedError(missing, new)
        return missing, new

    # ------------------------------------------------------------------ #
    #  Misc                                                               #
    # ------------------------------------------------------------------ #
    @classmethod
    def social_urls(cls) -> dict:
        """Non-empty social profile URLs, keyed by platform."""
        return {
            key: url
            for key, url in (
                ("facebook", cls.FACEBOOK_URL),
                ("twitter", cls.TWITTER_URL),
                ("instagram", cls.INSTAGRAM_URL),
                ("linkedin", cls.LINKEDIN_URL),
            )
            if url
        }

    @staticmethod
    def state_full_name_to_abbreviated(state_name: str | None = None) -> str:
        """Full state name -> 2-letter code. Now sync (was async, never awaited).

        Prefer ``SuperScraper.STATE_ABBREVIATED`` for the configured state; this is
        kept for the rare call that abbreviates some other state name.
        """
        return state_abbreviation(state_name or SuperScraper.STATE)

    @staticmethod
    def state_has_privacy_law(state_name: str | None = None) -> bool:
        """True if ``state_name`` (default: the configured STATE) has an active
        comprehensive consumer-privacy law."""
        return state_privacy_data.state_has_privacy_law(state_name or SuperScraper.STATE or "")

    @staticmethod
    def state_camel_key(state_name: str | None = None, *, suffix: str = "Usa") -> str:
        """``"Rhode Island" -> "rhodeIslandUsa"`` for form vendors that key options that way."""
        return state_privacy_data.state_camel_key(state_name or SuperScraper.STATE, suffix=suffix)

    @staticmethod
    def state_law_citation(right: "Right | None" = None, state_name: str | None = None):
        """Statute citation for a right in the given state (default: configured STATE)."""
        return state_privacy_data.statute_cite(state_name or SuperScraper.STATE, right.value if right else None)

    @staticmethod
    async def choose_dropdown_option_by_xpath(tab, input_xpath, dropdown_item_xpath, sleep=0, double_click=False, timeout=BASE_TIMEOUT_IN_SECONDS):
        input_field = await tab.find(
            xpath=input_xpath,
            timeout=timeout,
            raise_exc=False
        )
        if not input_field:
            print(f"{SuperScraper.OOPS} The input field with xpath {input_xpath} was not found.")
            return

        if sleep:
            time.sleep(sleep)

        await input_field.click()
        if double_click:
            await input_field.click()  # Sometimes need a double click for dropdown options to appear
        dropdown_option = await tab.find(
            xpath=dropdown_item_xpath,
            timeout=timeout,
            raise_exc=False
        )
        if not dropdown_option:
            print(f"{SuperScraper.OOPS} The dropdown option with xpath {dropdown_item_xpath} was not found.")
            return

        if sleep:
            time.sleep(sleep)

        await dropdown_option.click()

    @staticmethod
    async def choose_dropdown_option_by_text(tab, input_xpath, dropdown_option_text, sleep=0, double_click=False, timeout=BASE_TIMEOUT_IN_SECONDS):
        input_field = await tab.find(
            xpath=input_xpath,
            timeout=timeout,
            raise_exc=False
        )
        if not input_field:
            print(f"{SuperScraper.OOPS} The input field with xpath {input_xpath} was not found.")
            return

        if sleep:
            time.sleep(sleep)

        await input_field.click()
        if double_click:
            await input_field.click()

        await SuperScraper.click_item_by_text(tab=tab, text=dropdown_option_text)

    @staticmethod
    async def click_item_by_text(tab, text, sleep=0, timeout=BASE_TIMEOUT_IN_SECONDS):
        button = await tab.find(
            text=text,
            timeout=timeout,
            raise_exc=False
        )
        if not button:
            print(f"{SuperScraper.OOPS} The clickable element with text {text} was not found.")
            return

        if sleep:
            time.sleep(sleep)

        await button.click()

    @staticmethod
    async def click_item_by_xpath(tab, xpath, sleep=0, timeout=BASE_TIMEOUT_IN_SECONDS):
        button = await tab.find(
            xpath=xpath,
            timeout=timeout,
            raise_exc=False
        )
        if not button:
            print(f"{SuperScraper.OOPS} The clickable item with xpath {xpath} was not found.")
            return

        if sleep:
            time.sleep(sleep)

        await button.click()

    @staticmethod
    async def input_text_field(tab, xpath, text, sleep=0, timeout=BASE_TIMEOUT_IN_SECONDS):
        input_field = await tab.find(
            xpath=xpath,
            timeout=timeout,
            raise_exc=False
        )
        if not input_field:
            print(f"{SuperScraper.OOPS} The input field with xpath {xpath} was not found.")
            return

        if sleep:
            time.sleep(sleep)

        await input_field.click()
        await tab.keyboard.type_text(text=text)

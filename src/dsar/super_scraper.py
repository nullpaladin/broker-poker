import asyncio
import os
import random
import re
import time

import dotenv

from pydoll.browser.options import ChromiumOptions

from src.dsar.exceptions import RequiredFieldError
from src.state_privacy_request_factory import state_privacy_data
from src.state_privacy_request_factory.state_privacy_data import (
    RIGHT_CODES,
    UnknownStateError,
    law_name,
    rights_available,
    state_abbreviation,
    state_has_privacy_law,
    statute_cite,
)


# Human-readable phrasing for each canonical right code — used by request_statement().
RIGHT_DISPLAY = {
    "access": "access to and a copy of my personal data",
    "delete": "deletion of my personal data",
    "correct": "correction of inaccuracies in my personal data",
    "portability": "a portable copy of my personal data",
    "opt_out_sale_share": "opt-out of the sale or sharing of my personal data",
    "opt_out_targeted_ads": "opt-out of targeted advertising",
    "opt_out_profiling": "opt-out of profiling in furtherance of decisions that produce "
    "legal or similarly significant effects",
    "know_third_parties": "a list of the specific third parties to which my personal data "
    "has been disclosed",
    "limit_sensitive_pi": "limiting the use and disclosure of my sensitive personal information",
}


class SuperScraper:
    dotenv.load_dotenv()
    # System-related information
    # NOTE: compared against a stripped/upper-cased string rather than truthiness —
    # os.getenv("REMOVE_INFORMATION") returns the literal string "False" when the .env
    # value is False, and non-empty strings are truthy in Python, so `if REMOVE_INFORMATION`
    # would always be True regardless of the .env setting.
    REMOVE_INFORMATION = (os.getenv("REMOVE_INFORMATION") or "").strip().upper() in ("TRUE", "1", "YES")
    DRY_RUN = (os.getenv("DRY_RUN") or "True").strip().upper() in ("TRUE", "1", "YES")
    # Like DRY_RUN (never submits) but additionally asserts every required field could be
    # filled and never writes screenshots — for a future automated health-check runner.
    HEALTH_CHECK = (os.getenv("HEALTH_CHECK") or "").strip().upper() in ("TRUE", "1", "YES")
    # Show the automated browser window. Default True — several forms need a visible
    # window for a manual CAPTCHA solve during a live (non-DRY_RUN) run.
    HEADED = (os.getenv("HEADED") or "True").strip().upper() in ("TRUE", "1", "YES")
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
    except UnknownStateError:
        print(f"{__name__}: WARNING — STATE={STATE!r} is not a recognised US state; "
              "STATE_ABBREVIATED / LAW_* left unset.")
        STATE_ABBREVIATED = None
        LAW_FULL_NAME = None
        LAW_SHORT_NAME = None

    # --- Which privacy rights the user wants to exercise (PR comment: user choice) ---
    # .env REQUESTED_RIGHTS is a comma-separated list of canonical right codes. Unset/empty
    # => all codes. `delete` is additionally gated on REMOVE_INFORMATION (see rights_to_exercise).
    _requested = [c.strip().lower() for c in (os.getenv("REQUESTED_RIGHTS") or "").split(",") if c.strip()]
    _unknown_rights = [c for c in _requested if c not in RIGHT_CODES]
    if _unknown_rights:
        print(f"{__name__}: WARNING — ignoring unknown REQUESTED_RIGHTS codes: {_unknown_rights}")
    REQUESTED_RIGHTS = frozenset(c for c in _requested if c in RIGHT_CODES) or frozenset(RIGHT_CODES)

    # --- Declarative per-scraper metadata (frontend_implementation_plan.md §7). Safe
    # defaults; individual scrapers override at module or class level as they are touched. ---
    CAPTCHA_TYPE = "none"          # "none" | "image" | "widget"
    REQUIRED_FIELDS = ()
    OPTIONAL_FIELDS = ()
    RIGHTS_SUPPORTED = ()          # canonical right codes this scraper's form can exercise
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
    def wants(cls, *right_codes) -> bool:
        """True if the user asked for ANY of ``right_codes`` for their state.

        A right is wanted when it is in ``REQUESTED_RIGHTS`` AND (the user's state
        grants it, OR the state has no comprehensive privacy law at all — in which
        case the generic set is still attempted, since a site written for CCPA
        applies the same way). ``delete`` additionally requires REMOVE_INFORMATION.
        """
        granted = rights_available(cls.STATE) if cls.STATE else frozenset()
        no_law = not (state_has_privacy_law(cls.STATE) if cls.STATE else False)
        for code in right_codes:
            if code not in cls.REQUESTED_RIGHTS:
                continue
            if code == "delete" and not cls.REMOVE_INFORMATION:
                continue
            if no_law or code in granted:
                return True
        return False

    @classmethod
    def rights_to_exercise(cls, right_map) -> list:
        """Ordered canonical right codes to actually exercise for this run.

        ``right_map`` is the scraper's ``RIGHT_MAP`` (canonical code -> that
        scraper's own entry). Returns the keys the user wants, in ``right_map``
        order.
        """
        return [code for code in right_map if cls.wants(code)]

    @classmethod
    def request_statement(cls, rights, *, broker: str | None = None) -> str:
        """Freeform "I am a <state> resident exercising ..." sentence for a
        message / details textarea, with the correct per-state law name."""
        state_title = cls.STATE or "US"
        law = cls.LAW_FULL_NAME or "applicable state and federal privacy law"
        short = f" ({cls.LAW_SHORT_NAME})" if cls.LAW_SHORT_NAME else ""
        human = ", ".join(RIGHT_DISPLAY.get(r, r) for r in rights) or "my applicable privacy rights"
        held = f" that {broker} and its affiliates hold about me" if broker else " held about me"
        cites = [c for c in (statute_cite(cls.STATE, r) for r in rights) if c] if cls.STATE else []
        cite_clause = f" (see {'; '.join(dict.fromkeys(cites))})" if cites else ""
        return (
            f"I am a {state_title} resident and I am exercising my privacy rights under the "
            f"{law}{short}{cite_clause}. I request the following with respect to the personal "
            f"information{held}: {human}."
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

    # ------------------------------------------------------------------ #
    #  Browser options / screenshots                                      #
    # ------------------------------------------------------------------ #
    @classmethod
    def build_chromium_options(cls, *, extra_args=()) -> ChromiumOptions:
        """Standard ChromiumOptions: binary location + --no-sandbox, headless unless
        HEADED, and never a --window-size (those were a screenshot-testing artifact)."""
        options = ChromiumOptions()
        if cls.CHROMIUM_LOCATION:
            options.binary_location = cls.CHROMIUM_LOCATION
        options.add_argument("--no-sandbox")
        if not cls.HEADED:
            options.add_argument("--headless=new")
        for arg in extra_args:
            options.add_argument(arg)
        return options

    @staticmethod
    async def screenshot(tab, path, *, force=False, beyond_viewport=False):
        """Take a screenshot ONLY in DRY_RUN (or force=True); no-op otherwise.

        Screenshots are a dry-run verification artifact — a live run has nothing to
        screenshot, and a health-check run must not litter the disk.
        """
        if not force and (not SuperScraper.DRY_RUN or SuperScraper.HEALTH_CHECK):
            return None
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        await tab.take_screenshot(path=path, beyond_viewport=beyond_viewport)
        print(f"Screenshot saved to {path}")
        return path

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
            value = await SuperScraper.js_eval(
                el,
                "return ((this.value != null ? this.value : (this.textContent || '')).trim())"
                " || (this.checked ? 'x' : '');",
            )
            if not value:
                missing.append(label)
        if missing and raise_on_fail:
            raise RequiredFieldError(missing)
        return {label: (label not in missing) for label in fields}

    # ------------------------------------------------------------------ #
    #  Shared embedded-JS helpers (see docs/development_reference/embedded_js_audit.md)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _unwrap_js(raw):
        """pydoll's execute_script returns {'result': {'result': {'value': X}}}; some
        call paths already hand back X. Return X either way."""
        node = raw
        for _ in range(3):
            if isinstance(node, dict) and "result" in node:
                node = node["result"]
            else:
                break
        if isinstance(node, dict) and "value" in node:
            return node["value"]
        return raw if not isinstance(raw, dict) else node

    @staticmethod
    async def js_eval(target, script):
        """Run ``script`` on a tab or element and return the unwrapped value.
        The script needs a top-level ``return`` (not a wrapping IIFE)."""
        return SuperScraper._unwrap_js(await target.execute_script(script))

    @staticmethod
    async def js_click(element):
        """`element.click()` in JS — bypasses overlay interception / ElementNotVisible."""
        await element.execute_script("this.click();")

    @staticmethod
    async def js_check(element, checked=True, *, dispatch=("click", "change")):
        """Set a checkbox/radio's checked state in JS + dispatch events. For custom-
        styled / 1x1px / visually-hidden inputs that ignore a native .click()."""
        want = "true" if checked else "false"
        events = ";".join(
            f"this.dispatchEvent(new Event('{e}',{{bubbles:true}}))" for e in dispatch
        )
        await element.execute_script(f"if(this.checked!=={want}){{this.checked={want};{events};}}")

    @staticmethod
    async def js_set_value(element, value, *, blur=False):
        """Set an <input>/<textarea> value via the native prototype setter + dispatch
        input/change[/blur]. For React/Angular controlled fields where click()+type
        silently fails. ``element`` may be the input itself or a wrapper around it."""
        events = (
            "el.dispatchEvent(new Event('input',{bubbles:true}));"
            "el.dispatchEvent(new Event('change',{bubbles:true}));"
        )
        if blur:
            events += "el.dispatchEvent(new Event('blur',{bubbles:true}));"
        await element.execute_script(
            "var el=(this.tagName==='INPUT'||this.tagName==='TEXTAREA')?this:"
            "this.querySelector('input,textarea')||this;"
            "var d=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el),'value');"
            f"if(d&&d.set){{d.set.call(el,{value!r});}}else{{el.value={value!r};}}"
            + events
        )

    @staticmethod
    async def select_native_option(
        select_element, *, value=None, text=None, index=None, ci=False,
        dispatch=("input", "change"),
    ):
        """Select an <option> in a native <select> by value / visible text / index,
        then dispatch input+change. Replaces the ~80 hand-copied ``_select_native_option``
        helpers across the scrapers."""
        events = ";".join(
            f"this.dispatchEvent(new Event('{e}',{{bubbles:true}}))" for e in dispatch
        )
        if value is not None:
            match = "o.value.toLowerCase()===V.toLowerCase()" if ci else "o.value===V"
            body = f"var V={value!r};"
        elif text is not None:
            match = "T.toLowerCase()===V.toLowerCase()" if ci else "T===V"
            body = f"var V={text!r};"
        elif index is not None:
            await select_element.execute_script(f"this.selectedIndex={int(index)};{events};")
            return
        else:
            raise ValueError("select_native_option needs value=, text= or index=")
        await select_element.execute_script(
            body
            + "for(var i=0;i<this.options.length;i++){var o=this.options[i];"
            "var T=(o.text||o.textContent||'').trim();"
            f"if({match}){{this.selectedIndex=i;break;}}}}"
            + events + ";"
        )

    @staticmethod
    async def check_termly_attestations(tab):
        """Force every Termly ``__doNotSubmit__``-prefixed attestation checkbox
        checked + dispatch. These gate submission regardless of request type."""
        await tab.execute_script(
            "document.querySelectorAll('input[name^=\"__doNotSubmit__\"]').forEach(function(cb){"
            "cb.checked=true;"
            "cb.dispatchEvent(new Event('click',{bubbles:true}));"
            "cb.dispatchEvent(new Event('change',{bubbles:true}));"
            "});"
        )

    @staticmethod
    async def page_text(tab):
        """`document.body.innerText` — for post-submit confirmation checks."""
        return await SuperScraper.js_eval(tab, "return document.body.innerText;")

    @staticmethod
    async def fill_autocomplete(tab, field, value, *, option_text=None, settle=1.3):
        """OneTrust-style autocomplete combobox: clear via JS, type, then click the
        matching role=option (falling back to trusting the typed value). Returns
        True on apparent success."""
        await field.execute_script(
            "this.value='';this.dispatchEvent(new Event('input',{bubbles:true}));"
        )
        await field.click()
        await tab.keyboard.type_text(text=value)
        await asyncio.sleep(settle)
        target = option_text or value
        opt = await tab.find(
            xpath=f"//*[@role='option' and normalize-space()={target!r}]", raise_exc=False
        )
        if opt:
            await opt.click()
            return True
        current = await SuperScraper.js_eval(field, "return this.value;")
        return bool(current)

    # ------------------------------------------------------------------ #
    #  Math ("what is 6 minus 1?") CAPTCHA solver                         #
    # ------------------------------------------------------------------ #
    _WORD_NUMBERS = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
        "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
        "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
        "eighteen": 18, "nineteen": 19, "twenty": 20,
    }
    _OPS = {
        "+": "add", "plus": "add", "add": "add", "sum": "add",
        "-": "sub", "minus": "sub", "subtract": "sub", "less": "sub",
        "*": "mul", "x": "mul", "×": "mul", "times": "mul",
        "multiplied by": "mul", "multiply": "mul",
        "/": "div", "÷": "div", "divided by": "div", "divide": "div", "over": "div",
    }

    @staticmethod
    def _num(token: str):
        token = token.strip().lower()
        if token.lstrip("-").isdigit():
            return int(token)
        return SuperScraper._WORD_NUMBERS.get(token)

    @staticmethod
    def solve_math_captcha(question: str):
        """Parse "<a> <op> <b>" (digits or words zero..twenty; op = add/sub/mul/div,
        symbol or word) and return the integer answer as a string, or None."""
        if not question:
            return None
        text = question.strip().lower().rstrip("=?").strip()
        op_alt = "|".join(re.escape(k) for k in sorted(SuperScraper._OPS, key=len, reverse=True))
        num_alt = r"-?\d+|" + "|".join(SuperScraper._WORD_NUMBERS)
        m = re.search(rf"({num_alt})\s*({op_alt})\s*({num_alt})", text)
        if not m:
            return None
        a, b = SuperScraper._num(m.group(1)), SuperScraper._num(m.group(3))
        if a is None or b is None:
            return None
        op = SuperScraper._OPS[m.group(2)]
        if op == "add":
            return str(a + b)
        if op == "sub":
            return str(a - b)
        if op == "mul":
            return str(a * b)
        if op == "div":
            if b == 0:
                return None
            return str(a // b if a % b == 0 else round(a / b))
        return None

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
    def state_law_citation(right_code: str | None = None, state_name: str | None = None):
        """Statute citation for a right in the given state (default: configured STATE)."""
        return state_privacy_data.statute_cite(state_name or SuperScraper.STATE, right_code)

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

    @staticmethod
    async def solve_captcha(tab, image_xpath, input_field_xpath, sleep=0, timeout=BASE_TIMEOUT_IN_SECONDS):
        captcha_image = await tab.find(
            xpath=image_xpath,
            timeout=timeout,
            raise_exc=False
        )
        if not captcha_image:
            print(f"{SuperScraper.OOPS} The captcha image with xpath {image_xpath} was not found.")
            return

        # TODO: need to integrate 2captcha
        if sleep:
            time.sleep(sleep)

        captcha_input_field = await tab.find(
            xpath=input_field_xpath,
            timeout=timeout,
            raise_exc=False
        )
        if not captcha_input_field:
            print(f"{SuperScraper.OOPS} The captcha image field with xpath {input_field_xpath} was not found.")

        await captcha_input_field.click()
        await tab.keyboard.type_text("Here's the solved captcha!")

        print(f"Here's where I do the captcha stuff: {captcha_image}")

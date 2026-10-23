# oracle.com — the "Privacy Choices and Data Subject Rights" page
# (oracle.com/legal/data-privacy-inquiry-form/) embeds a TrustArc IRM form
# (submit-irm.trustarc.com/services/validation/742d5422-...), navigable
# directly. Same react-select Angular scaffold as ariza.com / liveramp.com
# elsewhere in this repo, but the CSS class prefix is "ta-upm-select__"
# rather than plain "select__" — a bare ".select__option" selector matches
# nothing, so options are matched with contains(@class,'select__option').
#
# Page elements (ids are "00000000-0000-0000-0000-000000001XXX" + suffix):
#   ...1004  "Resident of"   -> type a US STATE name directly ("Minnesota");
#            there is NO separate country field, and typing "United States"
#            hits a known site-side filter bug that only ever returns
#            "United States Minor Outlying Islands" / "...Virgin Islands" —
#            selecting the state by name sidesteps it entirely.
#   ...1001  "I Am"          -> "Consumer / Customer"
#   ...1005  "Type of Request" (single-select — one submission per right;
#            options populate only after "Resident of" is chosen)
#   ...1002fn / ...1002ln / ...1003  First / Last / Email
#   ...1007checkbox  accuracy/verification consent (hidden -> set via JS)
#
# One submission per "Type of Request" option (see RIGHT_MAP); which rights run is
# decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). "Correct or Update My
# Information" (not automated) and "Other Privacy Inquiry – Contact our DPO" (not a
# rights request) are offered but skipped.
#
# Oracle sends a verification email that must be actioned before the request
# is processed — that step is manual. An invisible reCAPTCHA v2 (site key
# 6LdSn6gUAAAAAKZ5SiEQ8PdCUOgV9sf1ei4utXrB) may pop a challenge on submit,
# so the form is filled and left for a manual submit.
# **CAPTCHA solution required**
#
# NOTE: name/email/consent ids start with a digit -> tab.find(id=...) builds
# an invalid CSS selector; every field is reached by xpath (same workaround
# as ariza.com).
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://submit-irm.trustarc.com/services/validation/742d5422-26ad-45bc-89b1-05e40e58b59d"

RESIDENT_CONTAINER = "00000000-0000-0000-0000-000000001004-select-container"
IAM_CONTAINER = "00000000-0000-0000-0000-000000001001-select-container"
REQUEST_TYPE_CONTAINER = "00000000-0000-0000-0000-000000001005-select-container"

# Right -> "Type of Request" option(s) in the ...1005 chooser.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Access My Information"],
    Right.RIGHT_TO_OPT_OUT: [
        "Do Not Sell My Personal Information",
        "Marketing e-Mail Opt-out or Unsubscribe",
    ],
    Right.RIGHT_TO_DELETE: ["Delete My Information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option in the "Type of Request" react-select, as displayed -> the Right it maps to (None = not automated).
PAGE_RIGHTS = {
    "Access My Information": Right.RIGHT_TO_ACCESS,
    "Do Not Sell My Personal Information": Right.RIGHT_TO_OPT_OUT,
    "Marketing e-Mail Opt-out or Unsubscribe": Right.RIGHT_TO_OPT_OUT,
    "Delete My Information": Right.RIGHT_TO_DELETE,
    "Correct or Update My Information": None,
    "Other Privacy Inquiry – Contact our DPO": None,
}
RIGHTS_OPTIONS_CSS = "[class*='select__option']"  # only rendered while the request-type menu is open (class prefix is ta-upm-select__)

FIELD_XPATHS = {
    "First name": "//input[@id='00000000-0000-0000-0000-000000001002fn']",
    "Last name": "//input[@id='00000000-0000-0000-0000-000000001002ln']",
    "Email": "//input[@id='00000000-0000-0000-0000-000000001003']",
}


async def _select_option(tab, container_id, text):
    ctrl = await tab.find(
        xpath=f"//div[@id='{container_id}']//div[contains(@class,'select__control')]",
        raise_exc=False,
    )
    if not ctrl:
        return False
    await ctrl.click()
    await asyncio.sleep(0.6)
    await tab.keyboard.type_text(text)
    await asyncio.sleep(1.3)
    opt = await tab.find(
        xpath=f"//div[contains(@class,'select__option') and normalize-space()={text!r}]",
        raise_exc=False,
    )
    if opt:
        await opt.click()
        await asyncio.sleep(0.5)
        return True
    return False


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    await _select_option(tab, RESIDENT_CONTAINER, SuperScraper.STATE)
    await _select_option(tab, IAM_CONTAINER, "Consumer / Customer")
    if SuperScraper.HEALTH_CHECK:
        # Options only populate after "Resident of"; open the menu, read it, close it again.
        ctrl = await tab.find(
            xpath=f"//div[@id='{REQUEST_TYPE_CONTAINER}']//div[contains(@class,'select__control')]",
            raise_exc=False,
        )
        if ctrl:
            await ctrl.click()
            await asyncio.sleep(1)
            offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
            SuperScraper.audit_rights(offered, PAGE_RIGHTS)
            await tab.keyboard.press(Key.ESCAPE)
            await asyncio.sleep(0.5)

    await _select_option(tab, REQUEST_TYPE_CONTAINER, request_type)
    await asyncio.sleep(1)

    first = await tab.find(xpath="//input[@id='00000000-0000-0000-0000-000000001002fn']", raise_exc=False)
    if first:
        await first.scroll_into_view()
        await first.type_text(SuperScraper.FIRST_NAME)
    last = await tab.find(xpath="//input[@id='00000000-0000-0000-0000-000000001002ln']", raise_exc=False)
    if last:
        await last.scroll_into_view()
        await last.type_text(SuperScraper.LAST_NAME)
    email = await tab.find(xpath="//input[@id='00000000-0000-0000-0000-000000001003']", raise_exc=False)
    if email:
        await email.scroll_into_view()
        await email.type_text(SuperScraper.EMAIL)

    consent = await tab.find(
        xpath="//input[@id='00000000-0000-0000-0000-000000001007checkbox']", raise_exc=False
    )
    if consent:
        await consent.execute_script(
            "this.checked=true;"
            "this.dispatchEvent(new Event('click', {bubbles:true}));"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    label = request_type.lower().split("–")[0].strip().replace(" ", "_").replace("/", "_")

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{request_type}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    print(f"\nForm filled for '{request_type}'. Solve the reCAPTCHA if one appears,")
    print("click Submit Request, action Oracle's verification email, then press Enter...")
    input()

    print(f"Submitted '{request_type}' for {SuperScraper.EMAIL} — confirm in the browser "
          "and action Oracle's verification email.")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for request_type in RIGHT_MAP[right]:
                await submit_request(tab, request_type, super_scraper)


asyncio.run(main())

# ariza.com (branded "Azira") — TrustArc IRM privacy request form. Custom
# react-select comboboxes for "I am" (Individual/Agent), "Resident of"
# (state/country full names), and "Type of Request" (single-select — one
# submission per right; the request-type options only populate after
# "Resident of" is chosen). Click the .select__control div, type the target
# text, then click the matching .select__option. Rights the form exposes: Access,
# Correct (not automated), Limit Sensitive PI Use / Do Not Sell or Share / Opt-out or
# Unsubscribe / Withdraw Consent (all RIGHT_TO_OPT_OUT, one submission each) and Delete.
# Which run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). MAID
# (Mobile Ad ID) is optional — filled from ADVERTISING_ID when set. The
# consent checkbox is a standard accuracy/TrustArc-role attestation (not an
# anti-automation notice) — safe to check. reCAPTCHA v2 requires manual solve.
#
# CAUTION: earlier in development this TrustArc-hosted form threw a
# PerimeterX-style "Let's confirm you are human" interstitial after ~8 rapid
# requests, blocking further automated access for the rest of that session
# (same pattern documented for oracle.com and liveramp.com elsewhere in this
# repo). On a later, separate session the form loaded cleanly again with no
# interstitial — it was rapid repeated testing traffic, not a permanent
# block. Seen loading cleanly in a DRY_RUN screenshot (no live submission observed).
#
# NOTE: First/Last Name, Email, MAID, and the consent checkbox all have ids
# starting with a digit (e.g. "00000000-0000-0000-0000-000000001002fn").
# `tab.find(id=...)` builds an unescaped `#{id}` CSS selector, which is
# invalid syntax for an id starting with a digit — it silently resolves to
# the wrong (invisible) element instead of raising, so `.type_text()` then
# fails with ElementNotVisible even though the real field is on-screen and
# fillable. Every one of these fields is targeted by xpath instead, same
# workaround as the colon-id bug documented elsewhere in this repo.
#
# Page elements (keep this list current; ids are TrustArc-generated):
#   ...1001-select-container   "I am" react-select -> "Individual"
#   ...1002fn / ...1002ln      First / Last name
#   ...1003                    Email
#   ...1004-select-container   "Resident of" react-select (state full name)
#   ...1005-select-container   "Type of Request" react-select (see RIGHT_MAP)
#   77916532-b470-4337-8bc5-269104f7eaf9   MAID (Mobile Ad ID), optional
#   ...1007                    Consent checkbox (custom hidden checkbox)
#   (ids shown with the "00000000-0000-0000-0000-00000000" prefix elided)
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://submit-irm.trustarc.com/services/validation/0a80503b-1d56-4d50-a898-4377a0227dab"

IAM_CONTAINER = "00000000-0000-0000-0000-000000001001-select-container"
RESIDENT_CONTAINER = "00000000-0000-0000-0000-000000001004-select-container"
REQUEST_TYPE_CONTAINER = "00000000-0000-0000-0000-000000001005-select-container"

# "Correct or Update My Information" is also offered but is not automatable, so unmapped.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Access My Information"],
    Right.RIGHT_TO_OPT_OUT: [
        "Limit the Use of My Sensitive Personal Information",
        "Do not Sell or Share My Personal Information",
        "Opt-out or Unsubscribe",
        "Withdraw My Consent",
    ],
    Right.RIGHT_TO_DELETE: ["Delete My Information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option in the "Type of Request" react-select, as displayed -> the Right it maps to.
PAGE_RIGHTS = {
    "Access My Information": Right.RIGHT_TO_ACCESS,
    "Correct or Update My Information": None,
    "Limit the Use of My Sensitive Personal Information": Right.RIGHT_TO_OPT_OUT,
    "Do not Sell or Share My Personal Information": Right.RIGHT_TO_OPT_OUT,
    "Opt-out or Unsubscribe": Right.RIGHT_TO_OPT_OUT,
    "Withdraw My Consent": Right.RIGHT_TO_OPT_OUT,
    "Delete My Information": Right.RIGHT_TO_DELETE,
}
RIGHTS_OPTIONS_CSS = ".select__option"  # only rendered while the request-type menu is open

FIRST_NAME_XPATH = "//input[@id='00000000-0000-0000-0000-000000001002fn']"
LAST_NAME_XPATH = "//input[@id='00000000-0000-0000-0000-000000001002ln']"
EMAIL_XPATH = "//input[@id='00000000-0000-0000-0000-000000001003']"


async def _select_option(tab, container_id, text):
    ctrl = await tab.find(
        xpath=f"//div[@id='{container_id}']//div[contains(@class,'select__control')]",
        raise_exc=False,
    )
    if not ctrl:
        return False
    await ctrl.click()
    await asyncio.sleep(0.5)
    await tab.keyboard.type_text(text)
    await asyncio.sleep(1)
    opt = await tab.find(
        xpath=f"//div[contains(@class,'select__option') and contains(text(),'{text}')]",
        raise_exc=False,
    )
    if opt:
        await opt.click()
        await asyncio.sleep(0.5)
        return True
    return False


async def submit_request(tab, right, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    await _select_option(tab, IAM_CONTAINER, "Individual")

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

    if SuperScraper.ADVERTISING_ID:
        maid = await tab.find(xpath="//input[@id='77916532-b470-4337-8bc5-269104f7eaf9']", raise_exc=False)
        if maid:
            await maid.scroll_into_view()
            await maid.type_text(SuperScraper.ADVERTISING_ID)

    await _select_option(tab, RESIDENT_CONTAINER, SuperScraper.STATE)
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

    consent = await tab.find(xpath="//input[@id='00000000-0000-0000-0000-000000001007']", raise_exc=False)
    if consent:
        # custom-styled hidden checkbox (ta-custom-hidden-checkbox)
        await js_utils.js_check(consent)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(
            tab, {"First name": FIRST_NAME_XPATH, "Last name": LAST_NAME_XPATH, "Email": EMAIL_XPATH}
        )

    label = request_type.lower().replace(" ", "_").replace("/", "_")

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' ('{request_type}') for {SuperScraper.EMAIL}"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    print(f"\nForm filled for '{right.name}' ('{request_type}'). Solve the reCAPTCHA, click Submit Request,")
    print("then press Enter once the confirmation page appears...")
    input()
    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for request_type in RIGHT_MAP[right]:
                await submit_request(tab, right, request_type, super_scraper)


asyncio.run(main())

# finthrive.com — Custom OneTrust Angular DSAR portal. "State Selection"
# (formField81DSARElement) must be filled FIRST to reveal the subject-type
# and request-type buttons — matches STATE from .env (autocomplete: type +
# ArrowDown+Enter). Subject type "I am a(n)" defaults to "Website Visitor"
# (no formal customer/employee/vendor relationship assumed).
#
# NOTE: the form's disclaimer states this process is "reserved for residents
# of California at this time" and submitting attests CA residency (or acting
# as an agent for one) — same CA-only framing already used by other shipped
# scrapers in this repo (e.g. reonomy.com's "California Consumer" subject
# type); the form is therefore only run for users whose state has a privacy law
# (SERVES_NO_LAW_STATES = False). The user's own STATE is what gets entered.
#
# Request type is single-select (one submission per request type): Know - Specific
# Pieces, Know - Categories & Sources, Opt-Out, Delete (Correct is offered but not
# automatable, so it is not in RIGHT_MAP). Country/State (personal, separate from
# the initial State Selection gate) are vt-autocomplete comboboxes. captchaCode
# is a BotDetect image CAPTCHA requiring manual entry in live mode.
#
# Page elements:
#   #formField81DSARElement        "State Selection" autocomplete (filled first)
#   aria-label="Website Visitor"   subject-type button ("I am a(n)")
#   aria-label=<request type>      request-type buttons (labels in RIGHT_MAP)
#   #firstNameDSARElement / #lastNameDSARElement / #emailDSARElement   First / Last name / Email
#   #countryDSARElement / #stateDSARElement                            Country / State comboboxes
#   #requestDetailsDSARElement     request details textarea
#   #captchaCode                   image CAPTCHA text input
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

# The form says this process is reserved for California residents, so it is only run for
# residents of states that have a privacy law.
SERVES_NO_LAW_STATES = False

URL = "https://privacyportal.onetrust.com/webform/e2abd578-6539-47f6-9895-b18d23b76ac4/c3d22390-d038-4464-83d3-3f0c91c76a01"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [
        "Request to Know - Specific Pieces of Personal Information",
        "Request to Know - Categories of Personal Information & Sources",
    ],
    Right.RIGHT_TO_OPT_OUT: ["Request to Opt-Out (Do Not Sell or Share My Personal Information)"],
    Right.RIGHT_TO_DELETE: ["Request to Delete Personal Information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Recorded request types are aria-labels; the visible text may differ, so they are not copied in.)

FIELD_XPATHS = {
    "State selection": "//*[@id='formField81DSARElement']",
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Country": "//*[@id='countryDSARElement']",
    "State": "//*[@id='stateDSARElement']",
    "Request details": "//*[@id='requestDetailsDSARElement']",
}


async def _fill_autocomplete(tab, field_id, value):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return False
    await field.click()
    await tab.keyboard.type_text(value)
    await asyncio.sleep(2)
    await tab.keyboard.press(Key.ARROWDOWN)
    await asyncio.sleep(0.3)
    await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(0.5)
    return True


async def submit_request(tab, right, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    await _fill_autocomplete(tab, "formField81DSARElement", SuperScraper.STATE)

    visitor_btn = await tab.find(**{"aria-label": "Website Visitor"}, raise_exc=False)
    if visitor_btn:
        await visitor_btn.click_using_js()
        await asyncio.sleep(1)

    req_btn = await tab.find(**{"aria-label": request_type}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request type button '{request_type}' not found")
        return
    await req_btn.click_using_js()
    await asyncio.sleep(1)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)
    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)
    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    await _fill_autocomplete(tab, "countryDSARElement", "United States")
    await _fill_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)

    request_details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if request_details:
        await request_details.type_text(SuperScraper.request_statement([right], broker="FinThrive"))

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    label = "".join(c if c.isalnum() else "_" for c in request_type.lower())[:40].strip("_")

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' ({request_type}) for {SuperScraper.EMAIL}"
        )
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}_{label}")
        return

    print(f"\nForm filled for '{request_type}'. Enter the CAPTCHA code, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()

    print(f"Submitted '{right.name}' ({request_type}) for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    if SuperScraper.bail_if_state_unsupported(globals()):
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

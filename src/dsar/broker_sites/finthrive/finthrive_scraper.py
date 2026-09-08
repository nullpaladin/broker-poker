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
# type), which submit regardless of the user's actual state. Followed the
# same established convention here rather than introducing a new exception.
#
# Request type is single-select (one submission per right): Know - Specific
# Pieces, Know - Categories & Sources, Correct, Opt-Out unconditionally;
# Delete gated on REMOVE_INFORMATION. Country/State (personal, separate from
# the initial State Selection gate) are vt-autocomplete comboboxes. captchaCode
# is a BotDetect image CAPTCHA requiring manual entry in live mode.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/e2abd578-6539-47f6-9895-b18d23b76ac4/c3d22390-d038-4464-83d3-3f0c91c76a01"

RIGHT_MAP = {
    "access": [
        "Request to Know - Specific Pieces of Personal Information",
        "Request to Know - Categories of Personal Information & Sources",
    ],
    "correct": ["Request to Correct Inaccurate Personal Information"],
    "opt_out_sale_share": ["Request to Opt-Out (Do Not Sell or Share My Personal Information)"],
    "delete": ["Request to Delete Personal Information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    await _fill_autocomplete(tab, "formField81DSARElement", SuperScraper.STATE)

    visitor_btn = await tab.find(**{"aria-label": "Website Visitor"}, raise_exc=False)
    if visitor_btn:
        await visitor_btn.click_using_js()
        await asyncio.sleep(1)

    req_btn = await tab.find(**{"aria-label": right}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request type button '{right}' not found")
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
        await request_details.type_text(
            f"I am exercising my '{right}' rights under the {SuperScraper.LAW_FULL_NAME or 'applicable state and federal privacy law'}."
        )

    label = "".join(c if c.isalnum() else "_" for c in right.lower())[:40].strip("_")

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/finthrive_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{right}'. Enter the CAPTCHA code, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{right}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{right}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    rights = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, super_scraper)


asyncio.run(main())

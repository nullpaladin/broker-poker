# nexxen.com — OneTrust Angular portal (privacyportal.onetrust.com) embedded on nexxen.com.
# The form requires one separate submission per request type (stated on the form), so each
# RIGHT_MAP entry is submitted separately. Which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). "Correct your personal information" is offered
# but not automated. Country -> State autocomplete reveals the subject type, request types
# and acknowledgement. reCAPTCHA v2 — manual solve in live mode.
#
# Page elements (keep this list current):
#   #countryDSARElement / #stateDSARElement   Country / State autocompletes (State appears after Country)
#   #formField72DSARElement (SUBJECT_TYPE)    Subject type buttons "Customer"/"Employee"/"Vendor" -> "Customer"
#   aria-label buttons (request types, see RIGHT_MAP):
#       "A copy of your personal information/Right to Data Portability"   -> ACCESS
#       "Do Not Sell/Share your personal information"                     -> OPT_OUT
#       "Opt-out of Processing Sensitive Data"                            -> OPT_OUT
#       "Opt-Out of Automated Decision-Making and Profiling/Opt-out of Targeted Advertising" -> OPT_OUT
#       "Delete your personal information"                                -> DELETE
#       "Correct your personal information"                               -> not automated
#   aria-label "Yes"                    Acknowledgement button (click_using_js)
#   aria-label "Click to submit form"   Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/76394770-3c6c-4d28-a57b-18817b0a8e3f/2bbd01a5-983c-440b-9fd5-fd341c9326a1"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("A copy of your personal information/Right to Data Portability", "access")],
    Right.RIGHT_TO_OPT_OUT: [
        ("Do Not Sell/Share your personal information", "optout"),
        ("Opt-out of Processing Sensitive Data", "sensitive"),
        ("Opt-Out of Automated Decision-Making and Profiling/Opt-out of Targeted Advertising", "profiling"),
    ],
    Right.RIGHT_TO_DELETE: [("Delete your personal information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _autocomplete(tab, field_id, text):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return
    await field.click()
    await field.type_text(text)
    await asyncio.sleep(2)
    opts = await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []
    for opt in opts:
        if await opt.is_visible():
            t = await opt.text
            if t and t.strip() == text:
                await opt.click()
                await asyncio.sleep(1)
                return


async def _submit_request(tab, request_aria, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    # Country
    await _autocomplete(tab, "countryDSARElement", "United States")
    await asyncio.sleep(1)

    # State (appears after country)
    await _autocomplete(tab, "stateDSARElement", SuperScraper.STATE)
    await asyncio.sleep(1)

    # Subject type: Customer (formField72DSARElement)
    customer = await tab.find(**{"aria-label": "Customer"}, raise_exc=False)
    if customer:
        await customer.click_using_js()
        await asyncio.sleep(0.5)
    else:
        print(f"{super_scraper.OOPS} 'Customer' subject button not found for {label}")

    # Request type
    req_btn = await tab.find(**{"aria-label": request_aria}, raise_exc=False)
    if req_btn:
        await req_btn.click_using_js()
        await asyncio.sleep(0.5)
    else:
        print(f"{super_scraper.OOPS} Request button '{request_aria}' not found")
        return

    # Acknowledgement: Yes
    yes_btn = await tab.find(**{"aria-label": "Yes"}, raise_exc=False)
    if yes_btn:
        await yes_btn.click_using_js()
        await asyncio.sleep(0.5)

    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    print(
        f"\nForm filled for '{label}'. "
        f"Solve the reCAPTCHA, then click Submit. "
        f"Press Enter after the confirmation page appears..."
    )
    input()

    print(f"Submitted '{label}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    if SuperScraper.bail_if_not_automatable(globals()):
        return
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_aria, label in requests:
            await _submit_request(tab, request_aria, label, super_scraper)


asyncio.run(main())

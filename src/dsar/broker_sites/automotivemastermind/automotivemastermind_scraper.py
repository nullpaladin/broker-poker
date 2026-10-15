# automotivemastermind.com (S&P Global) — Two OneTrust Angular forms:
# MAIN form (URL): Access, Correct (not automated), Portability, Profiling Opt-Out, Delete.
#   - Requesting Party, subject type ("Customer"), and request type buttons use click_using_js().
#   - Country + State autocomplete: click + keyboard.type_text + find(text=, visible).
#   - State appears after Country is selected; request type buttons appear after Subject Type selected.
#   - reCAPTCHA v2 — manual solve required.
# DNS form (DNS_URL): Do Not Sell / Opt-Out of Targeted Advertising.
#   - Country pre-set to "United States"; State is the only autocomplete.
#   - No CAPTCHA — fully automated.
# Which rights run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). RIGHT_TO_OPT_OUT
# goes to BOTH forms (the DNS form, plus the profiling button on the main form); access
# (incl. portability) + opt-out share one main-form submission; delete is its own submission.
#
# Page elements (both OneTrust Angular forms; keep this list current):
#   role=button aria-label="I am making a request for myself"   Requesting party (main)
#   role=button aria-label="Customer"                           Subject type (main)
#   role=button aria-label=<request type>                       Request-type buttons (see RIGHT_MAP)
#   #countryDSARElement         Country autocomplete -> "United States" (main)
#   #stateDSARElement           State autocomplete
#   #emailDSARElement           Email
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #addressDSARElement         Address (DNS form)
#   #formField49DSARElement     Address (main)
#   #formField50DSARElement     City (main)
#   #formField51DSARElement     Zip code (main)
#   #formField29DSARElement     autocomplete answered "Not Sure" (main; label not recorded)
#   #requestDetailsDSARElement  Request details textarea (main)
#   aria-label "Click to submit form"   Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/5cb57702-8ef7-437e-a62b-408fe78cd310/93391c3d-d6c8-45b1-a169-39a0b7f9fb74"
DNS_URL = "https://privacyportal.onetrust.com/webform/5cb57702-8ef7-437e-a62b-408fe78cd310/e5f5cb47-9b36-4ba9-920b-fe50ef4dc0c5"

# Right -> main-form request-type buttons. "Correction" is also offered but is not automatable.
# RIGHT_TO_OPT_OUT additionally submits the separate DNS form (see submit_dns).
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Confirm processing/Access", "Obtain a copy of my Data (Portability)"],
    Right.RIGHT_TO_OPT_OUT: [
        "Opt-Out of profiling in furtherance of decisions that produce legal / similarly significant effects",
    ],
    Right.RIGHT_TO_DELETE: ["Delete my data"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _select_autocomplete(tab, field_id, search_text):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return
    await field.click()
    await asyncio.sleep(0.5)
    await tab.keyboard.type_text(search_text)
    await asyncio.sleep(2)
    opts = await tab.find(text=search_text, find_all=True, raise_exc=False) or []
    for opt in opts:
        if await opt.is_visible():
            await opt.click()
            break
    await asyncio.sleep(1)


async def submit_dns(tab, super_scraper):
    """Submit Do Not Sell / Opt-Out via the dedicated DNS form (no CAPTCHA)."""
    await tab.go_to(DNS_URL)
    await asyncio.sleep(7)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    address = await tab.find(id="addressDSARElement", raise_exc=False)
    if address:
        await address.type_text(SuperScraper.ADDRESS)

    await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)

    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{Right.RIGHT_TO_OPT_OUT.name}' (DNS form) for {SuperScraper.EMAIL}"
        )
        submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
        if not submit_btn:
            submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, "dry_run_dns")
        return

    submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
    if not submit_btn:
        submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(3)

    print(f"Submitted '{Right.RIGHT_TO_OPT_OUT.name}' (DNS form) for {SuperScraper.EMAIL} — confirm in the browser.")


async def submit_main(tab, rights, super_scraper):
    """Submit one main-form request selecting the request type buttons of the given rights."""
    request_types = [rt for right in rights for rt in RIGHT_MAP[right]]
    label = "_".join(right.value for right in rights)
    details_text = SuperScraper.request_statement(rights, broker="Automotive Mastermind")
    await tab.go_to(URL)
    await asyncio.sleep(7)

    myself = await tab.find(**{"aria-label": "I am making a request for myself"}, raise_exc=False)
    if myself:
        await myself.click_using_js()
        await asyncio.sleep(1)

    await _select_autocomplete(tab, "countryDSARElement", "United States")
    await asyncio.sleep(1)
    await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)

    customer = await tab.find(**{"aria-label": "Customer"}, raise_exc=False)
    if customer:
        await customer.click_using_js()
        await asyncio.sleep(1)

    for req_type in request_types:
        btn = await tab.find(**{"aria-label": req_type}, raise_exc=False)
        if btn:
            await btn.click_using_js()
            await asyncio.sleep(0.3)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    address = await tab.find(id="formField49DSARElement", raise_exc=False)
    if address:
        await address.type_text(SuperScraper.ADDRESS)

    city = await tab.find(id="formField50DSARElement", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    zipcode = await tab.find(id="formField51DSARElement", raise_exc=False)
    if zipcode:
        await zipcode.type_text(SuperScraper.ZIP_CODE)

    await _select_autocomplete(tab, "formField29DSARElement", "Not Sure")

    details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if details:
        await details.type_text(details_text)

    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}"
        )
        submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
        if not submit_btn:
            submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    print(f"\nForm filled for {[r.name for r in rights]}.")
    print("Solve the reCAPTCHA in the browser, then click Submit.")
    print("Press Enter after submission completes...")
    input()

    print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


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

        if Right.RIGHT_TO_OPT_OUT in rights:
            await submit_dns(tab, super_scraper)
        shared = [r for r in rights if r != Right.RIGHT_TO_DELETE]
        if shared:
            await submit_main(tab, shared, super_scraper)
        if Right.RIGHT_TO_DELETE in rights:
            await submit_main(tab, [Right.RIGHT_TO_DELETE], super_scraper)


asyncio.run(main())

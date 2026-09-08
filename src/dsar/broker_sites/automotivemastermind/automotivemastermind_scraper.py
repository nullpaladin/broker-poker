# automotivemastermind.com (S&P Global) — Two OneTrust Angular forms:
# MAIN form (URL): Access, Correct, Portability, Profiling Opt-Out, Delete (gated).
#   - Requesting Party, subject type ("Customer"), and request type buttons use click_using_js().
#   - Country + State autocomplete: click + keyboard.type_text + find(text=, visible).
#   - State appears after Country is selected; request type buttons appear after Subject Type selected.
#   - reCAPTCHA v2 — manual solve required.
# DNS form (DNS_URL): Do Not Sell / Opt-Out of Targeted Advertising.
#   - Country pre-set to "United States"; State is the only autocomplete.
#   - No CAPTCHA — fully automated.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/5cb57702-8ef7-437e-a62b-408fe78cd310/93391c3d-d6c8-45b1-a169-39a0b7f9fb74"
DNS_URL = "https://privacyportal.onetrust.com/webform/5cb57702-8ef7-437e-a62b-408fe78cd310/e5f5cb47-9b36-4ba9-920b-fe50ef4dc0c5"

MAIN_REQUEST_TYPES = [
    "Confirm processing/Access",
    "Correction",
    "Obtain a copy of my Data (Portability)",
    "Opt-Out of profiling in furtherance of decisions that produce legal / similarly significant effects",
]
MAIN_REQUEST_DETAILS = (
    "I am exercising my rights under applicable state privacy law: "
    "Right to Know/Access, Right to Correct inaccurate information, "
    "Right to Data Portability, and Right to Opt-Out of Profiling."
)
DELETE_REQUEST_TYPE = "Delete my data"
DELETE_REQUEST_DETAILS = (
    "I am exercising my Right to Delete all personal information under applicable state privacy law."
)


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
            f"DRY RUN: would submit DNS/Opt-Out for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
        if not submit_btn:
            submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, "resources/screenshots/automotivemastermind_dry_run_dns.png")
        return

    submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
    if not submit_btn:
        submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(3)

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted DNS/Opt-Out for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} DNS confirmation unclear — verify in browser")


async def submit_main(tab, request_types, label, details_text, super_scraper):
    """Submit a main-form request selecting the given request type buttons."""
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
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
        if not submit_btn:
            submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"resources/screenshots/automotivemastermind_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{label}'.")
    print("Solve the reCAPTCHA in the browser, then click Submit.")
    print("Press Enter after submission completes...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        await submit_dns(tab, super_scraper)
        await submit_main(tab, MAIN_REQUEST_TYPES, "access_correct_portability", MAIN_REQUEST_DETAILS, super_scraper)
        if SuperScraper.wants("delete"):
            await submit_main(tab, [DELETE_REQUEST_TYPE], "delete", DELETE_REQUEST_DETAILS, super_scraper)


asyncio.run(main())

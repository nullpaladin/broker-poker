# qualcomm.com — OneTrust portal. Subject type "Other" (closest to consumer).
# Despite the "(s)" label, request type buttons are SINGLE-SELECT per submission
# — one form fill per right (same approach as nexxen.com).
# After clicking "Other", formField21DSARElement appears (required: relationship
# explanation). Requires 2s wait after "Other" click for Angular re-render.
# Rights exercised: Access, Data Portability, Opt out, Object to Processing,
# Update Data (Correct), Review Automated Decision.
# Data Deletion gated on REMOVE_INFORMATION.
# Country and State are independent autocompletes (countryDSARElement,
# stateDSARElement). No image CAPTCHA — reCAPTCHA v2 requires manual solve.
# Email verification required after submission (30-day window).
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/b0a5f2cc-0b29-4907-89bf-3f6b380a03c8/7ab89abb-0d42-492a-a324-0570883e2c11"

ALWAYS_REQUESTS = [
    ("Access",                      "access"),
    ("Data Portability",            "portability"),
    ("Opt out",                     "optout"),
    ("Object to Processing",        "object"),
    ("Update Data",                 "correct"),
    ("Review Automated Decision",   "autodecision"),
]
DELETE_REQUEST = ("Data Deletion", "delete")


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


async def _submit_request(tab, req_aria, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    # Subject type — wait 2s after click for Angular re-render
    other_btn = await tab.find(**{"aria-label": "Other"}, raise_exc=False)
    if other_btn:
        await other_btn.click_using_js()
    else:
        print(f"{super_scraper.OOPS} 'Other' subject button not found for {label}")
        return
    await asyncio.sleep(2)

    # Required relationship explanation (appears after "Other" is selected)
    relationship_field = await tab.find(id="formField21DSARElement", raise_exc=False)
    if relationship_field:
        await relationship_field.type_text("Consumer / member of the public")

    # Request type (single-select)
    req_btn = await tab.find(**{"aria-label": req_aria}, raise_exc=False)
    if req_btn:
        await req_btn.click_using_js()
    else:
        print(f"{super_scraper.OOPS} Request button '{req_aria}' not found")
        return
    await asyncio.sleep(0.5)

    # Personal info
    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    # Country and State autocompletes
    await _autocomplete(tab, "countryDSARElement", "United States")
    await asyncio.sleep(1)
    await _autocomplete(tab, "stateDSARElement", SuperScraper.STATE)
    await asyncio.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        submit_btn = await tab.find(**{"aria-label": "Click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/qualcomm_dry_run_{label}.png")
        return

    print(
        f"\nForm filled for '{label}'. "
        f"Solve the reCAPTCHA, then click Submit. "
        f"Press Enter after confirmation..."
    )
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

    requests = list(ALWAYS_REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for req_aria, label in requests:
            await _submit_request(tab, req_aria, label, super_scraper)


asyncio.run(main())

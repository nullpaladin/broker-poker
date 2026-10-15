# atdata.com — rights the form exposes: Access, Do Not Sell, Delete. Which run is decided
# ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# OneTrust CDN Angular DSAR form. Subject type ("Myself") and request type
# buttons are Angular role="button" divs — click via click_using_js().
# State uses formField17DSARElement (text input, full state name).
# reCAPTCHA v2 requires manual solve before submit.
# Submits once per right type.
#
# Page elements (keep this list current):
#   role=button aria-label="Myself"        Subject type
#   role=button aria-label=<request type>  Request-type buttons (see RIGHT_MAP)
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #emailDSARElement           Email
#   #addressDSARElement         Address
#   #cityDSARElement            City
#   #formField17DSARElement     State (text input, full state name)
#   #zipDSARElement             Zip code
#   aria-label "click to submit form"   Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/b38ccfa3-c14a-451e-bf1d-974d1e278b7c/6214ac53-9059-474d-a847-800250556e9d.html"

# (aria-label, screenshot label)
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Access My Information", "access")],
    Right.RIGHT_TO_OPT_OUT: [("Do Not Sell My Information", "optout")],
    Right.RIGHT_TO_DELETE: [("Delete My Information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, aria_label, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    # Subject type — "Myself"
    myself_btn = await tab.find(**{"aria-label": "Myself"}, raise_exc=False)
    if myself_btn:
        await myself_btn.click_using_js()
    await asyncio.sleep(1)

    # Request type button
    req_btn = await tab.find(**{"aria-label": aria_label}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request button '{aria_label}' not found")
        return
    await req_btn.click_using_js()
    await asyncio.sleep(1)

    # Personal info fields
    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    address = await tab.find(id="addressDSARElement", raise_exc=False)
    if address:
        await address.type_text(SuperScraper.ADDRESS)

    city = await tab.find(id="cityDSARElement", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    state_field = await tab.find(id="formField17DSARElement", raise_exc=False)
    if state_field:
        await state_field.type_text(SuperScraper.STATE)

    zip_field = await tab.find(id="zipDSARElement", raise_exc=False)
    if zip_field:
        await zip_field.type_text(SuperScraper.ZIP_CODE)

    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' ('{aria_label}') for {SuperScraper.EMAIL}"
        )
        submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    print(f"\nForm filled for '{right.name}' ('{aria_label}').")
    print("Solve the reCAPTCHA checkbox in the browser, then click Submit.")
    print("Press Enter after the confirmation page appears...")
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
    requests = [(right, aria_label, label) for right in rights for aria_label, label in RIGHT_MAP[right]]

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right, aria_label, label in requests:
            await submit_request(tab, right, aria_label, label, super_scraper)


asyncio.run(main())

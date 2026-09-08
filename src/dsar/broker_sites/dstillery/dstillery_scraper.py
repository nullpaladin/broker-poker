# dstillery.com — exercises Right to Access, Opt-Out of Sale/Targeting, and
# Right to Delete (gated on REMOVE_INFORMATION). OneTrust EU CDN Angular form.
# Subject type "A Consumer". formField18DSARElement is the Authorized Agent email
# (not required when submitting as consumer — left empty). reCAPTCHA v2 checkbox
# requires manual solve before submit. No country/state/phone/address fields.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-eu-cdn.onetrust.com/dsarwebform/246426b7-49c6-4bf5-879b-d3fdd4cbc15d/35502283-7b19-4b67-b3e0-ede06d3820c5.html"

# (aria-label, screenshot label)
RIGHT_MAP = {
    "access": [("Access request", "access")],
    "opt_out_sale_share": [("Opt-out request", "optout")],
    "delete": [("Deletion request", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, aria_label, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    consumer_btn = await tab.find(**{"aria-label": "A Consumer"}, raise_exc=False)
    if consumer_btn:
        await consumer_btn.click_using_js()
    await asyncio.sleep(1)

    req_btn = await tab.find(**{"aria-label": aria_label}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request button '{aria_label}' not found")
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

    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{aria_label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/dstillery_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{aria_label}'.")
    print("Solve the reCAPTCHA in the browser, then click Submit.")
    print("Press Enter after the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{aria_label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{aria_label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for aria_label, label in requests:
            await submit_request(tab, aria_label, label, super_scraper)


asyncio.run(main())

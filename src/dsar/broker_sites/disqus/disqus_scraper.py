# disqus.com — exercises Right to Access, Do Not Sell/Share, Opt-Out of Sensitive
# Data Processing, and Right to Delete (gated on REMOVE_INFORMATION).
# OneTrust CDN Angular DSAR form. Subject type "Disqus User" and request type
# buttons are Angular role="button" divs — click via click_using_js().
# Country and State are autocomplete comboboxes (type then click first visible
# role=option). reCAPTCHA v2 requires manual solve before submit.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/bc2d3301-11a5-4de5-b15e-ce796187a352/9a049fa1-37af-4598-a87a-d0df2e2d904b.html"

# (aria-label, screenshot label)
REQUESTS = [
    ("Request a copy of personal information", "access"),
    ("Do not sell or share my information", "optout"),
    ("Opt out of use of my sensitive personal information", "sensitive"),
]
DELETE_REQUEST = ("Delete my personal information", "delete")


async def submit_request(tab, aria_label, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    subject_btn = await tab.find(**{"aria-label": "Disqus User"}, raise_exc=False)
    if subject_btn:
        await subject_btn.click_using_js()
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

    country_field = await tab.find(id="countryDSARElement", raise_exc=False)
    if country_field:
        await country_field.click()
        await tab.keyboard.type_text("United States")
        await asyncio.sleep(2)
        country_opt = await tab.find(text="United States", raise_exc=False)
        if country_opt:
            await country_opt.click()
    await asyncio.sleep(1)

    # State field only appears after country is selected
    state_field = await tab.find(id="stateDSARElement", raise_exc=False)
    if state_field:
        await state_field.click()
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(2)
        state_opt = await tab.find(text=SuperScraper.STATE, raise_exc=False)
        if state_opt:
            await state_opt.click()
    await asyncio.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{aria_label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(1)
        await tab.take_screenshot(f"resources/screenshots/disqus_dry_run_{label}.png")
        print(f"Screenshot saved to resources/screenshots/disqus_dry_run_{label}.png")
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

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for aria_label, label in requests:
            await submit_request(tab, aria_label, label, super_scraper)


asyncio.run(main())

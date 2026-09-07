# billtrust.com — standard OneTrust webform (privacyportal.onetrust.com/webform/,
# distinct from the Angular *DSARElement CDN forms elsewhere in this repo,
# though it reuses the same *DSARElement id convention). Country/State are
# vt-autocomplete comboboxes (type then click the matching vt-option).
# "I am a(n)" and "Select request type(s)" are already-visible option boxes
# (role="option" divs inside a role="listbox", no dropdown to open first) —
# click_using_js() on the one matching aria-label. "I am a(n)" defaults to
# "Customer" (no generic "Individual"/"Consumer" choice offered), which in
# turn reveals a required "Products" picker (which Billtrust product the
# request relates to) — defaulted to "Billtrust Collections" (the product
# this specific webform's footer is branded for), since there's no way to
# know which product a given data subject actually used. Despite the
# plural "type(s)" label, request type is actually single-select — clicking
# a second option deselects the first (confirmed via aria-selected) — so
# this is one submission per right: Info Request (Access) and Do Not Sell My
# Information unconditionally; Data Deletion gated on REMOVE_INFORMATION.
# "Request Details" is a required free-text field describing the request.
# reCAPTCHA v2 requires a manual solve in live mode.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacyportal.onetrust.com/webform/82a6a736-b3a7-4e87-a2fd-04a39b7d2b19/2f5dc7b8-7698-4623-82d2-b2b969ef901e"

RIGHTS = ["Info Request", "Do Not Sell My Information"]
DELETE_RIGHT = "Data Deletion"


async def _click_option(tab, aria_label, super_scraper, description):
    opt = await tab.find(
        xpath=f"//div[@role='option' and @aria-label='{aria_label}']", raise_exc=False
    )
    if not opt:
        print(f"{super_scraper.OOPS} {description} option '{aria_label}' not found")
        return
    await opt.click_using_js()
    await asyncio.sleep(0.3)


async def _fill_autocomplete(tab, field_id, text, super_scraper, description):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} {description} field not found")
        return
    await field.click()
    await tab.keyboard.type_text(text)
    await asyncio.sleep(1.5)
    opt = await tab.find(xpath=f"//*[contains(@class,'vt-option') and contains(text(),'{text}')]", raise_exc=False)
    if opt:
        await opt.click()
        await asyncio.sleep(0.5)


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    await _fill_autocomplete(tab, "countryDSARElement", "United States", super_scraper, "Country")
    await _click_option(tab, "Customer", super_scraper, "'I am a(n)'")
    await asyncio.sleep(0.5)
    # Selecting "Customer" reveals a required "Products" picker (which
    # Billtrust product the request relates to) — no way to know which
    # product a given data subject actually used, so this defaults to
    # "Billtrust Collections" (the product this specific webform is
    # branded/hosted for, per its footer).
    await _click_option(tab, "Billtrust Collections", super_scraper, "Products")
    await _fill_autocomplete(tab, "stateDSARElement", SuperScraper.STATE, super_scraper, "State")

    await _click_option(tab, right, super_scraper, "request type")

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    email = await tab.find(id="emailDSARElement", raise_exc=False)
    details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)

    if first:
        await first.type_text(SuperScraper.FIRST_NAME)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)
    if email:
        await email.type_text(SuperScraper.EMAIL)
    if details:
        await details.type_text(f"I am {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}. Please process my '{right}' request.")

    label = right.lower().replace(" ", "_")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/billtrust_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{right}'. Solve the reCAPTCHA v2, then click Submit.")
    print("Press Enter after the confirmation page appears...")
    input()
    print(f"Submitted '{right}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, super_scraper)


asyncio.run(main())

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
# this is one submission per right: Info Request (Access), Do Not Sell My
# Information (Opt-out) and Data Deletion (Delete). Which of them run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
# "Request Details" is a required free-text field describing the request.
# reCAPTCHA v2 requires a manual solve in live mode.
#
# Page elements:
#   #countryDSARElement          Country (vt-autocomplete; type, click vt-option)
#   div[role=option][aria-label="Customer"]  "I am a(n)" choice
#   div[role=option][aria-label="Billtrust Collections"]  "Products" choice
#   #stateDSARElement            State (vt-autocomplete)
#   div[role=option][aria-label=<entry>]  "Select request type(s)" choice (single-select)
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #emailDSARElement            Email
#   #requestDetailsDSARElement   "Request Details" free-text
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://privacyportal.onetrust.com/webform/82a6a736-b3a7-4e87-a2fd-04a39b7d2b19/2f5dc7b8-7698-4623-82d2-b2b969ef901e"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Info Request"],
    Right.RIGHT_TO_OPT_OUT: ["Do Not Sell My Information"],
    Right.RIGHT_TO_DELETE: ["Data Deletion"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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


async def submit_request(tab, right, entry, super_scraper):
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

    await _click_option(tab, entry, super_scraper, "request type")

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
        await details.type_text(SuperScraper.request_statement([right], broker="Billtrust"))

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        return

    print(f"\nForm filled for '{right.name}'. Solve the reCAPTCHA v2, then click Submit.")
    print("Press Enter after the confirmation page appears...")
    input()
    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for entry in RIGHT_MAP[right]:
                await submit_request(tab, right, entry, super_scraper)


asyncio.run(main())

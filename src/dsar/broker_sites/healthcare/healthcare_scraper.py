# healthcare.com — server-rendered form, no captcha. "Inquiry" select is
# single-select (one submission per right): "Right to know what information
# is collected" (Access) and "Right to opt-out of sales" unconditionally;
# "Right to delete personal information" gated on REMOVE_INFORMATION. Per the
# form's own note, identification requires the *exact* email and phone number
# previously provided to healthcare.com — this only works for an existing
# customer, not an arbitrary consumer. A cookie consent banner covers part of
# the form on load and must be dismissed first.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.healthcare.com/data-request/request-form/"

RIGHTS = [("ccpa-info-req", "access"), ("ccpa-opt-out-sales-req", "opt_out")]
DELETE_RIGHT = ("ccpa-delete-req", "delete")


async def submit_request(tab, case_type, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(4)

    deny_cookies = await tab.find(text="Deny Non-Essential", raise_exc=False)
    if deny_cookies:
        await deny_cookies.click()
        await asyncio.sleep(1)

    await tab.execute_script(
        f'var s = document.querySelector("select#case_type"); s.value = "{case_type}"; s.dispatchEvent(new Event("change"));'
    )

    for name, value in [
        ("first_name", SuperScraper.FIRST_NAME),
        ("last_name", SuperScraper.LAST_NAME),
        ("email", SuperScraper.EMAIL),
        ("zip_code", SuperScraper.ZIP_CODE),
        ("phone_number", SuperScraper.PHONE_NUMBER),
    ]:
        field = await tab.find(name=name, raise_exc=False)
        if field:
            await field.type_text(value)
            await asyncio.sleep(0.2)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{case_type}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/healthcare_dry_run_{label}.png")
        return

    await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
    await asyncio.sleep(2)
    print(f"Submitted '{case_type}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


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
        for case_type, label in rights:
            await submit_request(tab, case_type, label, super_scraper)


asyncio.run(main())

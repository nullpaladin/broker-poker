# slashdotmedia.com — custom OneTrust Angular portal. "I am a (an)" toggle
# (Customer/Employee/Prospective Employee, no generic-visitor option) —
# "Customer" used as the closest fit. "Select request type" is
# single-select (confirmed: picking a second option deselects the first)
# — one submission per right: Info Request (Access) unconditionally;
# Data Deletion gated on REMOVE_INFORMATION. No Opt-Out option exists on
# this form. Data Correction skipped (no concrete inaccuracy to describe).
# Selecting Data Deletion reveals a required cascading confirmation
# ("...you will lose all account information. Do you wish to proceed?")
# answered "Yes". State is ALSO a cascading vt-autocomplete field, not
# present in the DOM until Country is filled in.
# Country is a vt-autocomplete combobox. Optional free-text "Request
# Details". BotDetect image CAPTCHA — **CAPTCHA solution required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacyportal.onetrust.com/webform/611e70e2-1994-43ff-b07b-646df870db4b/f4165d65-f39c-4ea5-8628-163090b74137"

RIGHT_MAP = {
    "access": ["Info Request"],
    "delete": ["Data Deletion"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    customer_option = await tab.find(xpath="//*[@role='option' and normalize-space()='Customer']", raise_exc=False)
    if customer_option:
        await customer_option.click()
        await asyncio.sleep(0.5)
    else:
        print(f"{super_scraper.OOPS} 'Customer' option not found")

    right_option = await tab.find(xpath=f"//*[@role='option' and normalize-space()='{right}']", raise_exc=False)
    if right_option:
        await right_option.click()
        await asyncio.sleep(0.5)
    else:
        print(f"{super_scraper.OOPS} request type '{right}' not found")

    if right == DELETE_RIGHT:
        # Cascading confirmation only revealed after picking Data Deletion.
        proceed_option = await tab.find(xpath="//*[@role='option' and normalize-space()='Yes']", raise_exc=False)
        if proceed_option:
            await proceed_option.click()
            await asyncio.sleep(0.5)
        else:
            print(f"{super_scraper.OOPS} deletion confirmation 'Yes' option not found")

    first_field = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first_field:
        await first_field.type_text(SuperScraper.FIRST_NAME)
    last_field = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last_field:
        await last_field.type_text(SuperScraper.LAST_NAME)
    email_field = await tab.find(id="emailDSARElement", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    country_field = await tab.find(id="countryDSARElement", raise_exc=False)
    if country_field:
        await country_field.click()
        await asyncio.sleep(0.3)
        await tab.keyboard.type_text("United States")
        await asyncio.sleep(1.2)
        option = await tab.find(xpath="//*[@role='option' and normalize-space()='United States']", raise_exc=False)
        if option:
            await option.click()
            await asyncio.sleep(0.7)
        else:
            print(f"{super_scraper.OOPS} country option 'United States' not found")

    # State only renders in the DOM after Country is set above.
    state_field = await tab.find(id="stateDSARElement", raise_exc=False)
    if state_field:
        await state_field.click()
        await asyncio.sleep(0.3)
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(1.2)
        option = await tab.find(
            xpath=f"//*[@role='option' and normalize-space()='{SuperScraper.STATE}']", raise_exc=False
        )
        if option:
            await option.click()
            await asyncio.sleep(0.7)
        else:
            print(f"{super_scraper.OOPS} state option '{SuperScraper.STATE}' not found")
    else:
        print(f"{super_scraper.OOPS} State field not found")

    label = "".join(c if c.isalnum() else "_" for c in right.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/slashdotmedia_dry_run_{label}.png")
    print(
        f"\n'{right}' request filled but NOT submitted — a BotDetect image CAPTCHA "
        "requires manual entry before submitting."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    rights = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, super_scraper)


asyncio.run(main())

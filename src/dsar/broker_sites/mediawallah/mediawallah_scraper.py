# mediawallah.com — /donotsell/ embeds a OneTrust dsarwebform Angular
# iframe (privacyportal-eu-cdn.onetrust.com/dsarwebform/...), navigated to
# directly since it doesn't frame-bust. "I am a (an)" (Customer/Partner/
# Employee) and "Select request type(s)" (Info Request/Data Deletion/Do
# Not Sell My Information) are both `<div role="option">` toggle groups,
# not native inputs — despite the plural "type(s)" label, empirically
# confirmed SINGLE-select (clicking a second option clears aria-selected
# on the first), same as billtrust.com elsewhere in this repo — one
# submission per right. "Customer" used for "I am a (an)" (closest generic
# fit). Name/email fields use stable DSARElement ids and are plain text;
# Country/State (also DSARElement ids) are custom autocompletes with a
# role="option" dropdown — typing alone lets the widget auto-complete to
# the wrong entry and steal the next field's focus, so the matching
# dropdown option is clicked instead of just typing and moving on.
# reCAPTCHA v2 present — **CAPTCHA solution required**. Exercises Info
# Request (Access) and Do Not Sell unconditionally; Data Deletion gated on
# REMOVE_INFORMATION.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacyportal-eu-cdn.onetrust.com/dsarwebform/e3df3040-c675-462f-99c4-15c05ac3bf5c/545897d5-7793-4317-921b-4efe187a2c02.html"

RIGHT_MAP = {
    "access": ["Info Request"],
    "opt_out_sale_share": ["Do Not Sell My Information"],
    "delete": ["Data Deletion"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    i_am_a = await tab.find(text="Customer", raise_exc=False)
    if i_am_a:
        await i_am_a.click()
    else:
        print(f"{super_scraper.OOPS} 'Customer' option not found")

    right_opt = await tab.find(text=right, raise_exc=False)
    if right_opt:
        await right_opt.click()
    else:
        print(f"{super_scraper.OOPS} '{right}' option not found")

    fields = {
        "firstNameDSARElement": SuperScraper.FIRST_NAME,
        "lastNameDSARElement": SuperScraper.LAST_NAME,
        "emailDSARElement": SuperScraper.EMAIL,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    # Country/State are custom autocompletes (role="option" dropdown, not
    # plain text inputs) — typing alone lets the widget auto-complete to
    # the wrong entry (e.g. "United States Minor Outlying Islands") and
    # steal focus, so the matching dropdown option must be clicked instead.
    country_field = await tab.find(id="countryDSARElement", raise_exc=False)
    if country_field:
        await country_field.click()
        await asyncio.sleep(0.3)
        await tab.keyboard.type_text("United States")
        await asyncio.sleep(1.2)
        country_opt = await tab.find(xpath="//*[@role='option' and normalize-space()='United States']", raise_exc=False)
        if country_opt:
            await country_opt.click()
            await asyncio.sleep(0.5)

    state_field = await tab.find(id="stateDSARElement", raise_exc=False)
    if state_field:
        await state_field.click()
        await asyncio.sleep(0.3)
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(1.2)
        state_opt = await tab.find(
            xpath=f"//*[@role='option' and normalize-space()='{SuperScraper.STATE}']", raise_exc=False
        )
        if state_opt:
            await state_opt.click()
            await asyncio.sleep(0.5)

    label = right.lower().replace(" ", "_")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/mediawallah_dry_run_{label}.png")
    print(
        f"\n'{right}' request filled but NOT submitted — a reCAPTCHA v2 checkbox is present "
        "and requires a manual solve before submitting."
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

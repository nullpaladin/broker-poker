# quad.com (Quad/Graphics Inc.) — custom OneTrust Angular portal. There is
# NO request-type picker of any kind on this form — the page's own copy
# explains that submitting the form covers both "Right to Opt Out of Sale,
# Sharing, and Targeted Advertising" and "Right to Limit the Use of
# Sensitive Personal Information" simultaneously; no Access or Delete
# option is offered at all. So this is a single, always-submitted
# combined request — no REMOVE_INFORMATION gating applies (there's no
# Delete right to gate). State is a vt-autocomplete combobox (type then
# click the matching role="option"); Address/Address Line 2/City/Zip are
# optional. captchaCode is a BotDetect image CAPTCHA — **CAPTCHA solution
# required**. Optional file upload for supporting documentation, left
# unfilled.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacyportal.onetrust.com/webform/9bbdeb31-9ca4-4397-b421-b165438ad177/1ca01042-21a7-4307-8b42-a6c7439c9685"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

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

        fields = {
            "firstNameDSARElement": SuperScraper.FIRST_NAME,
            "lastNameDSARElement": SuperScraper.LAST_NAME,
            "emailDSARElement": SuperScraper.EMAIL,
            "addressDSARElement": SuperScraper.ADDRESS,
            "address2DSARElement": SuperScraper.ADDRESS_LINE_TWO,
            "cityDSARElement": SuperScraper.CITY,
            "zipDSARElement": SuperScraper.ZIP_CODE,
        }
        for field_id, value in fields.items():
            if not value:
                continue
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/quad_dry_run.png")
        print("Screenshot saved to resources/screenshots/quad_dry_run.png")
        print(
            "\nCombined Opt-Out of Sale/Sharing/Targeted Advertising + Limit Use of "
            "Sensitive PI request filled but NOT submitted — a BotDetect image CAPTCHA "
            "requires manual entry before submitting."
        )


asyncio.run(main())

# bbdirect.com — Cognito Forms opt-out compliance form. BB Direct is a
# service provider that doesn't retain data itself, so this form only offers
# Right to Opt-Out (adds the record to their suppression database) — no
# Access/Delete available, so RIGHT_MAP has the single opt-out entry. State is
# an Element-UI-style combobox (click, type, click matching option from the
# popper list). reCAPTCHA Enterprise is invisible (badge hidden via CSS) and
# auto-resolves — no manual solve needed.
#
# Page elements (keep this list current):
#   #cog-input-auto-0 / #cog-input-auto-1   First / Last name
#   #cog-1-line1                Address line 1
#   #cog-1-city                 City
#   #cog-1-state                State combobox (el-select dropdown items)
#   #cog-1-zip-code             Zip code
#   #cog-2                      Email
#   button[type=submit]         Submit button
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.bbdirect.com/resources/privacy-compliance.html"

RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "opt-out"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

FIRST_NAME_XPATH = "//input[@id='cog-input-auto-0']"
LAST_NAME_XPATH = "//input[@id='cog-input-auto-1']"
ADDRESS_ONE_XPATH = "//input[@id='cog-1-line1']"
CITY_XPATH = "//input[@id='cog-1-city']"
STATE_XPATH = "//input[@id='cog-1-state']"
ZIP_XPATH = "//input[@id='cog-1-zip-code']"
EMAIL_XPATH = "//input[@id='cog-2']"
SUBMIT_XPATH = "//button[@type='submit']"


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        await super_scraper.input_text_field(tab=tab, xpath=FIRST_NAME_XPATH, text=SuperScraper.FIRST_NAME, sleep=0.5)
        await super_scraper.input_text_field(tab=tab, xpath=LAST_NAME_XPATH, text=SuperScraper.LAST_NAME, sleep=0.5)
        await super_scraper.input_text_field(tab=tab, xpath=ADDRESS_ONE_XPATH, text=SuperScraper.ADDRESS, sleep=0.5)
        await super_scraper.input_text_field(tab=tab, xpath=CITY_XPATH, text=SuperScraper.CITY, sleep=0.5)

        state_field = await tab.find(xpath=STATE_XPATH, raise_exc=False)
        if state_field:
            await state_field.click()
            await tab.keyboard.type_text(SuperScraper.STATE)
            await asyncio.sleep(1)
            option = await tab.find(
                xpath=f"//li[contains(@class,'el-select-dropdown__item') and contains(., '{SuperScraper.STATE}')]",
                raise_exc=False,
            )
            if option:
                await option.click()

        await super_scraper.input_text_field(tab=tab, xpath=ZIP_XPATH, text=SuperScraper.ZIP_CODE, sleep=0.5)
        await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL, sleep=0.5)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit '{Right.RIGHT_TO_OPT_OUT.name}' for {SuperScraper.EMAIL}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath=SUBMIT_XPATH, sleep=2)
        await asyncio.sleep(3)
        print(f"Submitted '{Right.RIGHT_TO_OPT_OUT.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())

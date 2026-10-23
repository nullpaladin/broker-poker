# recordsfinder.com — people-search opt-out ("data removal") form at /optout/ (InfoPay platform).
# One submission; no separate access/delete flow, so RIGHT_MAP has a single opt-out entry
# (mapped to RIGHT_TO_OPT_OUT because the page is the site's opt-out page; the form itself
# is a record-removal request). Which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements (all ids share the prefix InfoPay_Core_Components_OptOuts_DataRemovalServiceModel_):
#   <prefix>fname   "First name" input
#   <prefix>lname   "Last name" input
#   <prefix>state   State <select> (set by value = state abbreviation)
#   <prefix>city    "City" input
#   button[type=submit]  Submit button
import asyncio
import time

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://recordsfinder.com/optout/"

RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "removal request"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

_PREFIX = "InfoPay_Core_Components_OptOuts_DataRemovalServiceModel"
FIRST_NAME_XPATH = f'//input[@id="{_PREFIX}_fname"]'
LAST_NAME_XPATH = f'//input[@id="{_PREFIX}_lname"]'
STATE_SELECT_ID = f"{_PREFIX}_state"
CITY_XPATH = f'//input[@id="{_PREFIX}_city"]'
SUBMIT_XPATH = '//button[@type="submit"]'
STATE_XPATH = f'//select[@id="{STATE_SELECT_ID}"]'


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    state_abbrev = SuperScraper.STATE_ABBREVIATED

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        time.sleep(2)

        await super_scraper.input_text_field(tab=tab, xpath=FIRST_NAME_XPATH, text=SuperScraper.FIRST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=LAST_NAME_XPATH, text=SuperScraper.LAST_NAME)

        await tab.execute_script(
            f'var s = document.getElementById("{STATE_SELECT_ID}"); s.value = "{state_abbrev}"; s.dispatchEvent(new Event("change"));'
        )

        await super_scraper.input_text_field(tab=tab, xpath=CITY_XPATH, text=SuperScraper.CITY)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, {
                "First name": FIRST_NAME_XPATH,
                "Last name": LAST_NAME_XPATH,
                "State": STATE_XPATH,
                "City": CITY_XPATH,
            })

        if SuperScraper.DRY_RUN:
            await SuperScraper.screenshot(tab, "dry_run_opt_out")
            print(f"DRY RUN: would submit removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(3)
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath=SUBMIT_XPATH)
        time.sleep(3)
        print(f"Submitted removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} — confirm in the browser.")

        await asyncio.sleep(3)


asyncio.run(main())

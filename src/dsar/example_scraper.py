import asyncio
import time

from src.broker_sites.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.achcoop.com/do-not-sell-my-personal-info"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)

        # Site tends to erase input when it fully loads, should handle this in a better way but oh well
        time.sleep(3)

        await super_scraper.input_text_field(tab=tab, xpath='//*[@id="form-field-input-5858d39a-427c-455d-56b0-fc7bec83fd9d-comp-mhuo5c7k-"]', text=SuperScraper.FIRST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath='//*[@id="form-field-input-201e217e-9a38-4058-d1bd-6e4d601bfc60-comp-mhuo5c7k-"]', text=SuperScraper.LAST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath='//*[@id="form-field-input-3bf1bced-9e0f-4f9f-0a88-6d3a2a043ef1-comp-mhuo5c7k-"]', text=SuperScraper.ADDRESS)
        await super_scraper.input_text_field(tab=tab, xpath='//*[@id="form-field-input-57b8968e-f5e4-4f12-09e3-db9f625a7a15-comp-mhuo5c7k-"]', text=SuperScraper.CITY)
        await choose_dropdown_option_by_xpath(
            tab=tab,
            input_css_selector='#label-for-id_-1530 > span:nth-child(1)',  # FIXME: Broken
            dropdown_item_xpath='//*[@id="dropdown-options-container_-13_option-0f3fac48-d114-4fb9-3b8b-3c3cc56340b7-opt-23-text"]',  # Minnesota
        )
        await super_scraper.input_text_field(tab=tab, xpath='//*[@id="form-field-input-641bda48-c9a3-4499-9f8e-eea0047b582c-comp-mhuo5c7k-"]', text=SuperScraper.ZIP_CODE)
        await super_scraper.click_item_by_text(tab=tab, text='Request Access To My Personal Information')
        await super_scraper.click_item_by_text(tab=tab, text='Do Not Share My Personal Information')
        await super_scraper.click_item_by_text(tab=tab, text='Opt-Out of Cross-Context Behavioral or Targeted Advertising')
        await super_scraper.click_item_by_text(tab=tab, text='Opt-Out of Profiling/Automated Decision-Making')
        if SuperScraper.REMOVE_INFORMATION:
            await super_scraper.click_item_by_text(tab=tab, text='Remove Me From Your Database')

        # TODO: Submit button -- /html/body/div/div/div[3]/div/main/div/div/div/div[2]/div/div/div/section/div[2]/div/div[1]/div/div/div/div/div/form/fieldset/div/div[1]/div[9]/div/div[2]/div/button

        await asyncio.sleep(3)


async def choose_dropdown_option_by_xpath(tab, input_css_selector, dropdown_item_xpath, sleep=0):
    input_field = await tab.find(
        css=input_css_selector,
        timeout=2,
        raise_exc=False
    )
    if not input_field:
        print(f"The input field with css selector {input_css_selector} was not found.")
        return

    if sleep:
        time.sleep(sleep)

    await input_field.click()
    dropdown_option = await tab.find(
        xpath=dropdown_item_xpath,
        timeout=2,
        raise_exc=False
    )
    if not dropdown_option:
        print(f"The dropdown option with xpath {dropdown_item_xpath} was not found.")
        return

    if sleep:
        time.sleep(sleep)

    await dropdown_option.click()

asyncio.run(main())

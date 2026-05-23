import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = ""


async def main():
    options = ChromiumOptions()
    options.binary_location = "/snap/bin/chromium"
    options.add_argument("--no-sandbox")
    super_scraper = SuperScraper()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)

        await super_scraper.choose_dropdown_option_by_xpath(tab=tab, input_xpath='', dropdown_item_xpath='')
        await super_scraper.choose_dropdown_option_by_text(tab=tab, input_xpath='', dropdown_option_text='')
        await super_scraper.click_item_by_text(tab=tab, text='')
        await super_scraper.click_item_by_xpath(tab=tab, xpath='')
        await super_scraper.input_text_field(tab=tab, xpath='', text='')
        await super_scraper.solve_captcha(tab=tab, image_xpath='', input_field_xpath='')



        await asyncio.sleep(3)

asyncio.run(main())

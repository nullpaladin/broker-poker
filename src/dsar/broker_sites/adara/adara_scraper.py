# adara.com — merged into sojern.com; the DSAR form now lives at privacy.sojern.com
# (embedded via iframe on adara's own /privacy/opt-out-data page). Server-rendered POST
# form. id_type is single-select (cookie/mobile/email/ip) — email is used since it is
# always available. Exercises Export (Access) and Opt Out unconditionally; Delete
# gated on REMOVE_INFORMATION. Cloudflare Turnstile checkbox widget present and does
# NOT auto-resolve here (unlike jmr-media.com) — requires a manual solve in live mode
# before the submit buttons will actually succeed server-side.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacy.sojern.com/"

EMAIL_ID_TYPE_RADIO_XPATH = "//input[@name='id_type' and @value='email']"
EMAIL_ADDRESS_XPATH = "//input[@id='email-address']"

RIGHTS = [
    ("Export", "access"),
    ("Opt Out", "opt_out"),
]
DELETE_RIGHT = ("Delete", "delete")


async def submit_request(tab, op_value, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(3)

    await super_scraper.click_item_by_xpath(tab=tab, xpath=EMAIL_ID_TYPE_RADIO_XPATH, sleep=1)
    await super_scraper.input_text_field(tab=tab, xpath=EMAIL_ADDRESS_XPATH, text=SuperScraper.EMAIL, sleep=1)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{op_value}' for {SuperScraper.EMAIL}")
        await asyncio.sleep(2)
        await tab.take_screenshot(path=f"resources/screenshots/adara_dry_run_{label}.png")
        print(f"Screenshot saved to resources/screenshots/adara_dry_run_{label}.png")
        return

    await super_scraper.click_item_by_xpath(tab=tab, xpath=f"//input[@type='submit' and @value='{op_value}']", sleep=2)
    await asyncio.sleep(3)
    print(f"Submitted '{op_value}' for {SuperScraper.EMAIL}")


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
        for op_value, label in rights:
            await submit_request(tab, op_value, label, super_scraper)


asyncio.run(main())

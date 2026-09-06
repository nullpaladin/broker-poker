# monitorbase.com — MonitorBase CCPA/privacy request form on my.monitorbase.com/privacypolicy.
# Plain Laravel Livewire page, but the final submit is a native form POST to
# my.monitorbase.com/ccpa/remove, so typing into the wire:model inputs is enough.
# "Request Type" is a native <select id="type">: 1 = What Information Do You Have (access),
# 2 = Opt Me Out Of Having My Data Sold (opt-out), 3 = Delete My Information.
# Single-select — one submission per right. Access and Opt-Out unconditional;
# Delete gated on REMOVE_INFORMATION.
# A dynamic image CAPTCHA (name="captcha") gates submission — form is filled
# completely and left for a manual solve.  **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://my.monitorbase.com/privacypolicy"

# (visible option text, screenshot label)
REQUESTS = [
    ("What Information of Mine Do You Have?", "access"),
    ("Opt Me Out Of Having My Data Sold", "optout"),
]
DELETE_REQUEST = ("Delete My Information", "delete")


async def submit_request(tab, option_text, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    fields = {
        "//input[@id='first_name']": SuperScraper.FIRST_NAME,
        "//input[@id='last_name']": SuperScraper.LAST_NAME,
        "//input[@id='email']": SuperScraper.EMAIL,
        "//input[@id='phone_number']": SuperScraper.PHONE_NUMBER,
        "//input[@id='address']": SuperScraper.ADDRESS,
        "//input[@id='city']": SuperScraper.CITY,
        "//input[@id='state']": SuperScraper.STATE,
        "//input[@id='zip']": SuperScraper.ZIP_CODE,
    }
    for xpath, value in fields.items():
        await super_scraper.input_text_field(tab=tab, xpath=xpath, text=value, sleep=0.3)

    await super_scraper.choose_dropdown_option_by_text(
        tab=tab, input_xpath="//select[@id='type']", dropdown_option_text=option_text, sleep=0.5
    )

    agreement = await tab.find(id="agreement", raise_exc=False)
    if agreement:
        await agreement.execute_script("if (!this.checked) this.click();")

    time.sleep(0.5)
    await tab.take_screenshot(f"resources/screenshots/monitorbase_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/monitorbase_dry_run_{label}.png")

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{option_text}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    print(f"\nForm filled for '{option_text}'. Type the CAPTCHA shown in the browser")
    print("into the 'Please Insert Captcha' field, click Submit Request, then press Enter...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{option_text}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{option_text}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,2400")

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for option_text, label in requests:
            await submit_request(tab, option_text, label, super_scraper)


asyncio.run(main())

# 360mediadirect.com — Saymine.io privacy center (single-select request-type radios,
# one submission per right). Exercises Access ("Get a copy of my data"), Opt-Out of Sale
# ("Do not sell"), Correct ("Right to edit"), and Opt-Out of Mail ("Do not mail")
# unconditionally; Delete ("Delete my data") gated on REMOVE_INFORMATION.
# Country is preset to United States. State is a custom checkbox-driven dropdown —
# click the visible label to open the panel, then click the <li data-label="..."> option.
# A required "brand you are contacting us about" question is answered with
# "360 Media Direct" (the operating entity itself) since there is no way to infer
# which of its sub-brands (bPerx, Subco, ClicknRead, WRSS, AdSmith) applies.
# A required perjury declaration ("YES") must also be selected before submitting.
# reCAPTCHA is invisible v3 (badge only, no checkbox) — auto-resolves, no manual solve needed.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://360-media-direct.privacy.saymine.io/360_Media_Direct"

STATE_DROPDOWN_LABEL_XPATH = "//label[@for='dropdown-state-field']"
STATE_OPTION_XPATH = "//li[@class[contains(., 'dropdown__option')] and normalize-space(@data-label)='{state}']"

FIRST_NAME_XPATH = "//input[@id='fname-field']"
LAST_NAME_XPATH = "//input[@id='lname-field']"
EMAIL_XPATH = "//input[@id='email-field']"
ADDRESS_XPATH = "//input[@id='address-field']"
ZIP_XPATH = "//label[contains(., 'Zip Code')]/following-sibling::div//input"

BRAND_LABEL_XPATH = "//input[@id='778c1709-5809-418f-81cd-879f529e6ebb-4']/parent::label"
PERJURY_LABEL_XPATH = "//input[@id='173a9331-c185-43e2-910e-10f0231a48dd-0']/parent::label"
SUBMIT_XPATH = "//button[@id='btn-primary']"

RIGHTS = [
    ("getcopy", "access"),
    ("donotsell", "opt_out_of_sale"),
    ("righttoedit", "correct"),
    ("donotmail", "opt_out_of_mail"),
]
DELETE_RIGHT = ("delete", "delete")


async def submit_request(tab, right_id, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    await super_scraper.click_item_by_xpath(tab=tab, xpath=STATE_DROPDOWN_LABEL_XPATH, sleep=1)
    await super_scraper.click_item_by_xpath(
        tab=tab,
        xpath=STATE_OPTION_XPATH.format(state=SuperScraper.STATE),
        sleep=1,
    )

    await super_scraper.click_item_by_xpath(tab=tab, xpath=f"//label[@for='{right_id}']", sleep=1)

    await super_scraper.input_text_field(tab=tab, xpath=FIRST_NAME_XPATH, text=SuperScraper.FIRST_NAME, sleep=1)
    await super_scraper.input_text_field(tab=tab, xpath=LAST_NAME_XPATH, text=SuperScraper.LAST_NAME, sleep=1)
    await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL, sleep=1)
    await super_scraper.input_text_field(tab=tab, xpath=ADDRESS_XPATH, text=SuperScraper.ADDRESS, sleep=1)
    await super_scraper.input_text_field(tab=tab, xpath=ZIP_XPATH, text=SuperScraper.ZIP_CODE, sleep=1)

    await super_scraper.click_item_by_xpath(tab=tab, xpath=BRAND_LABEL_XPATH, sleep=1)
    await super_scraper.click_item_by_xpath(tab=tab, xpath=PERJURY_LABEL_XPATH, sleep=1)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right_id}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(2)
        await tab.take_screenshot(path=f"resources/screenshots/360mediadirect_dry_run_{label}.png")
        print(f"Screenshot saved to resources/screenshots/360mediadirect_dry_run_{label}.png")
        return

    await super_scraper.click_item_by_xpath(tab=tab, xpath=SUBMIT_XPATH, sleep=2)
    await asyncio.sleep(3)
    print(f"Submitted '{right_id}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


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
        for right_id, label in rights:
            await submit_request(tab, right_id, label, super_scraper)


asyncio.run(main())

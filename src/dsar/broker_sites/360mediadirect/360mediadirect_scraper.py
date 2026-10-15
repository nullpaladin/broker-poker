# 360mediadirect.com — Saymine.io privacy center (single-select request-type radios,
# one submission per right). Offers Access ("Get a copy of my data"), Opt-Out of Sale
# ("Do not sell"), Correct ("Right to edit"), Opt-Out of Mail ("Do not mail") and
# Delete ("Delete my data"); which run is decided only by rights_to_exercise.
# "Right to edit" (correct) is not automatable and is deliberately not in RIGHT_MAP.
# Country is preset to United States. State is a custom checkbox-driven dropdown —
# click the visible label to open the panel, then click the <li data-label="..."> option.
# A required "brand you are contacting us about" question is answered with
# "360 Media Direct" (the operating entity itself) since there is no way to infer
# which of its sub-brands (bPerx, Subco, ClicknRead, WRSS, AdSmith) applies.
# A required perjury declaration ("YES") must also be selected before submitting.
# reCAPTCHA is invisible v3 (badge only, no checkbox) — auto-resolves, no manual solve needed.
#
# Page elements:
#   label[for=dropdown-state-field]            State dropdown (opens the panel)
#   li.dropdown__option[data-label=<state>]    State option
#   label[for=<request-type id>]               Request-type radio: getcopy ("Get a copy of my data"),
#                                              righttoedit ("Right to edit"), donotsell ("Do not sell"),
#                                              donotmail ("Do not mail"), delete ("Delete my data")
#   #fname-field / #lname-field                First / Last name
#   #email-field                               Email
#   #address-field                             Address
#   label "Zip Code" -> sibling input          Zip Code
#   BRAND_LABEL_XPATH                          "brand you are contacting us about" option "360 Media Direct"
#   PERJURY_LABEL_XPATH                        Perjury declaration "YES"
#   #btn-primary                               Submit button
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

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

# "Do not mail" is an opt-out flavour, so it is a second RIGHT_TO_OPT_OUT entry.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("getcopy", "access")],
    Right.RIGHT_TO_OPT_OUT: [("donotsell", "opt_out_of_sale"), ("donotmail", "opt_out_of_mail")],
    Right.RIGHT_TO_DELETE: [("delete", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, right_id, label, super_scraper):
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
        print(f"DRY RUN: would submit '{right.name}' ({right_id}) for {SuperScraper.EMAIL}")
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    await super_scraper.click_item_by_xpath(tab=tab, xpath=SUBMIT_XPATH, sleep=2)
    await asyncio.sleep(3)
    print(f"Submitted '{right.name}' ({right_id}) for {SuperScraper.EMAIL} — confirm in the browser.")


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
        for right in rights:
            for right_id, label in RIGHT_MAP[right]:
                await submit_request(tab, right, right_id, label, super_scraper)


asyncio.run(main())

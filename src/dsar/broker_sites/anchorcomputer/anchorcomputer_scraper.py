# anchorcomputer.com — server-rendered ASP.NET POST form, no captcha. Single
# submission covers all selected rights via checkboxes. Rights the form exposes:
# access (RequestReport — labeled "CA residents only" but not enforced client-side),
# opt-out (RequestDoNotSell), delete (RequestDelete). Which are ticked is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
# DateOfBirth is an HTML5 date input — set via JS native setter as YYYY-MM-DD
# (converted from the DD/MM/YYYY in DATE_OF_BIRTH). SsnLastFour is optional — filled only
# if LAST_FOUR_SSN is set in .env.
#
# Page elements (keep this list current):
#   #FirstName / #LastName   First / Last name
#   #Address1                Address
#   #City                    City
#   select#State             State (abbreviation)
#   #Zip                     Zip code
#   #SsnLastFour             Last four of SSN (optional)
#   #DateOfBirth             Date of birth (HTML5 date input)
#   #PhoneNumber             Phone number
#   #Email                   Email
#   #RequestReport           Access checkbox
#   #RequestDoNotSell        Opt-out (do not sell) checkbox
#   #RequestDelete           Delete checkbox
#   input[type=submit]       Submit button
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://ecom2.anchorcomputer.com/privacyrequest"

FIRST_NAME_XPATH = "//input[@id='FirstName']"
LAST_NAME_XPATH = "//input[@id='LastName']"
ADDRESS_ONE_XPATH = "//input[@id='Address1']"
CITY_XPATH = "//input[@id='City']"
ZIP_XPATH = "//input[@id='Zip']"
SSN_XPATH = "//input[@id='SsnLastFour']"
PHONE_XPATH = "//input[@id='PhoneNumber']"
EMAIL_XPATH = "//input[@id='Email']"
SUBMIT_XPATH = "//input[@type='submit']"

# Right -> this form's checkbox id.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "RequestReport",
    Right.RIGHT_TO_OPT_OUT: "RequestDoNotSell",
    Right.RIGHT_TO_DELETE: "RequestDelete",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    state_abbrev = SuperScraper.STATE_ABBREVIATED

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(3)

        await super_scraper.input_text_field(tab=tab, xpath=FIRST_NAME_XPATH, text=SuperScraper.FIRST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=LAST_NAME_XPATH, text=SuperScraper.LAST_NAME)
        await super_scraper.input_text_field(tab=tab, xpath=ADDRESS_ONE_XPATH, text=SuperScraper.ADDRESS)
        await super_scraper.input_text_field(tab=tab, xpath=CITY_XPATH, text=SuperScraper.CITY)

        state_select = await tab.find(xpath="//select[@id='State']", raise_exc=False)
        if state_select:
            await js_utils.select_native_option(state_select, value=state_abbrev, dispatch=("change",))

        await super_scraper.input_text_field(tab=tab, xpath=ZIP_XPATH, text=SuperScraper.ZIP_CODE)

        if SuperScraper.LAST_FOUR_SSN:
            await super_scraper.input_text_field(tab=tab, xpath=SSN_XPATH, text=SuperScraper.LAST_FOUR_SSN)

        if SuperScraper.DATE_OF_BIRTH:
            # .env stores DATE_OF_BIRTH as DD/MM/YYYY; the native <input type="date">
            # here silently rejects anything but YYYY-MM-DD, so convert first.
            day, month, year = SuperScraper.DATE_OF_BIRTH.split("/")
            iso_dob = f"{year}-{month}-{day}"
            dob = await tab.find(xpath="//input[@id='DateOfBirth']", raise_exc=False)
            if dob:
                await js_utils.js_set_value(dob, iso_dob)

        await super_scraper.input_text_field(tab=tab, xpath=PHONE_XPATH, text=SuperScraper.PHONE_NUMBER)
        await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL)

        for right in rights:
            await super_scraper.click_item_by_xpath(tab=tab, xpath=f"//input[@id='{RIGHT_MAP[right]}']", sleep=0.3)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}")
            await asyncio.sleep(2)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath=SUBMIT_XPATH)
        await asyncio.sleep(3)
        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())

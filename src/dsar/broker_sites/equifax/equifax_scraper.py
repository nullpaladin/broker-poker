# equifax.com — Angular 2-step wizard ("1. Info" -> "2. Verify") covering
# Right to Limit the Use of sensitive PI, Right to Opt-Out of sharing/sale,
# and Right to Opt-In. A "Your Privacy Choices" cookie banner (Ketch) covers
# the form on load/scroll — dismissed via aria-label="close banner". The
# State <select> uses Angular-generated composite option values (e.g.
# "0: AK") rather than plain state codes, so the matching option must be
# found by visible text and its .value read back, not guessed. SSN/ITIN is
# skipped (only LAST_FOUR_SSN is available, not the full number this field
# wants). DOB and mobile number are optional and left blank along with SSN.
#
# NOTE: this scraper only fills the "Info" step and clicks "Go to next step".
# Equifax performs a real-time identity check against actual credit-bureau
# records before proceeding to "Verify" — placeholder/test data (as used for
# this DRY_RUN) gets rejected with a "Please give us a call" page rather than
# advancing, so the Verify step (and whichever specific right-selection UI
# lives beyond it) could not be observed or automated. A real user with their
# genuine details should get through to Verify; that step onward requires
# manual completion.
#
# Page elements (Info step):
#   aria-label="close banner"                       "Your Privacy Choices" (Ketch) banner close button
#   #firstname / #lastname                          First / Last name
#   #address1 / #city / #zipCode                    Address / City / Zip code
#   #email                                          Email
#   #dateOfBirth / #mobileNumber                    Date of birth / Mobile number (optional)
#   select#state                                    State (composite option values; matched by visible text)
#   #touCheckbox-input                              terms-of-use checkbox (clicked via its label)
#   "Go to next step" button
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://myprivacy.equifax.com/opt-in-opt-out/personal-info"

# The Info step is shared by every choice on the portal and the right-selection UI beyond
# Verify was never observed, so only the opt-out entry point is mapped.
RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "Info step of the opt-in/opt-out wizard"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Only the Info step was observed; the right-selection UI beyond Verify is unknown.)

FIELD_XPATHS = {
    "First name": "//*[@id='firstname']",
    "Last name": "//*[@id='lastname']",
    "Address": "//*[@id='address1']",
    "City": "//*[@id='city']",
    "Zip": "//*[@id='zipCode']",
    "Email": "//*[@id='email']",
    "State": "//select[@id='state']",
}


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
        await asyncio.sleep(6)

        close_banner = await tab.find(**{"aria-label": "close banner"}, raise_exc=False)
        if close_banner:
            await close_banner.click()
            await asyncio.sleep(1)

        for field_id, value in [
            ("firstname", SuperScraper.FIRST_NAME),
            ("lastname", SuperScraper.LAST_NAME),
            ("address1", SuperScraper.ADDRESS),
            ("city", SuperScraper.CITY),
            ("zipCode", SuperScraper.ZIP_CODE),
            ("email", SuperScraper.EMAIL),
        ]:
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)

        if SuperScraper.DATE_OF_BIRTH:
            day, month, year = SuperScraper.DATE_OF_BIRTH.split("/")
            dob_field = await tab.find(id="dateOfBirth", raise_exc=False)
            if dob_field:
                await dob_field.type_text(f"{month}/{day}/{year}")

        if SuperScraper.PHONE_NUMBER:
            mobile_field = await tab.find(id="mobileNumber", raise_exc=False)
            if mobile_field:
                await mobile_field.type_text(SuperScraper.PHONE_NUMBER)

        await tab.execute_script(
            'var s = document.querySelector("select#state"); '
            f'var opt = Array.from(s.options).find(o => o.textContent.trim() === "{SuperScraper.STATE}"); '
            'if(opt){ s.value = opt.value; s.dispatchEvent(new Event("change")); }'
        )

        tou_label = await tab.find(xpath="//input[@id='touCheckbox-input']/ancestor::label", raise_exc=False)
        if tou_label:
            await tou_label.click()
        await asyncio.sleep(1)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would advance to Verify step for {SuperScraper.EMAIL}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        clicked = await tab.execute_script(
            "var btns = Array.from(document.querySelectorAll('button')); "
            "var b = btns.find(x=>x.textContent.trim().toLowerCase().includes('next step')); "
            "if(b){ b.click(); return true;} return false;"
        )
        if not clicked:
            print(f"{super_scraper.OOPS} 'Go to next step' button not found")
            return

        await asyncio.sleep(3)
        print(
            "\nAdvanced past the Info step (if identity verification passed). "
            "Complete the Verify step and any subsequent right-selection manually — "
            "not automated past this point."
        )


asyncio.run(main())

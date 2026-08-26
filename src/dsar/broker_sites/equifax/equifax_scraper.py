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
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://myprivacy.equifax.com/opt-in-opt-out/personal-info"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

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

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would advance to Verify step for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(1)
            await tab.take_screenshot(path="resources/screenshots/equifax_dry_run.png")
            print("Screenshot saved to resources/screenshots/equifax_dry_run.png")
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

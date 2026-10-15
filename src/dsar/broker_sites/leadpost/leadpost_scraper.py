# leadpost.com — Opt-Out, Access (copy of data + list of recipients), Delete.
# Server-rendered POST form, single submission with the checkboxes of every selected right.
# State requires 2-letter abbreviation. Which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
# reCAPTCHA v2 (sitekey: 6Ld5uAArAAAAAKz5Az1SZwbWB3ZtLWtTMBjo-jDV) requires manual solve.
#
# Page elements:
#   #Email / #FirstName / #LastName          Email, First / Last name
#   #Address / #Address2 / #City / #State / #Zip / #Phone   Address fields (State = 2-letter abbreviation)
#   #OptOutOfFutureDataCollection   checkbox: opt out of future data collection
#   #ShareCopyOfMyData              checkbox: access, copy of my data
#   #ShareRecipientsOfMyData        checkbox: access, list of data recipients
#   #DeleteMyData                   checkbox: delete my data
#   reCAPTCHA v2 checkbox + Submit
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://client.leadpost.com/PrivacyRequest"

# Right -> checkbox ids to tick (Access ticks both the data-copy and the recipients box).
RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: ["OptOutOfFutureDataCollection"],
    Right.RIGHT_TO_ACCESS: ["ShareCopyOfMyData", "ShareRecipientsOfMyData"],
    Right.RIGHT_TO_DELETE: ["DeleteMyData"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        email = await tab.find(id="Email", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)

        first = await tab.find(id="FirstName", raise_exc=False)
        if first:
            await first.type_text(SuperScraper.FIRST_NAME)

        last = await tab.find(id="LastName", raise_exc=False)
        if last:
            await last.type_text(SuperScraper.LAST_NAME)

        address = await tab.find(id="Address", raise_exc=False)
        if address:
            await address.type_text(SuperScraper.ADDRESS)

        if SuperScraper.ADDRESS_LINE_TWO:
            address2 = await tab.find(id="Address2", raise_exc=False)
            if address2:
                await address2.type_text(SuperScraper.ADDRESS_LINE_TWO)

        city = await tab.find(id="City", raise_exc=False)
        if city:
            await city.type_text(SuperScraper.CITY)

        state_field = await tab.find(id="State", raise_exc=False)
        if state_field:
            state_abbrev = SuperScraper.STATE_ABBREVIATED
            await state_field.type_text(state_abbrev)

        zip_field = await tab.find(id="Zip", raise_exc=False)
        if zip_field:
            await zip_field.type_text(SuperScraper.ZIP_CODE)

        if SuperScraper.PHONE_NUMBER:
            phone = await tab.find(id="Phone", raise_exc=False)
            if phone:
                await phone.type_text(SuperScraper.PHONE_NUMBER)

        for right in rights:
            for checkbox_id in RIGHT_MAP[right]:
                checkbox = await tab.find(id=checkbox_id, raise_exc=False)
                if checkbox:
                    await checkbox.click()
                else:
                    print(f"{super_scraper.OOPS} checkbox '{checkbox_id}' not found")

        time.sleep(0.5)

        if SuperScraper.DRY_RUN:
            await SuperScraper.screenshot(tab, "dry_run")
            print(
                f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}"
            )
            return

        print("\nForm filled. Solve the reCAPTCHA v2 checkbox, then click Submit.")
        print("Press Enter after the confirmation page appears...")
        input()
        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())

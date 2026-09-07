# leadpost.com — exercises Opt-Out, Access (copy of data + list of recipients), Delete (gated).
# Server-rendered POST form, single submission for all rights. State requires 2-letter abbreviation.
# reCAPTCHA v2 (sitekey: 6Ld5uAArAAAAAKz5Az1SZwbWB3ZtLWtTMBjo-jDV) requires manual solve.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://client.leadpost.com/PrivacyRequest"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

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

        # Opt-Out of future data collection
        optout = await tab.find(id="OptOutOfFutureDataCollection", raise_exc=False)
        if optout:
            await optout.click()

        # Access: copy of data
        copy = await tab.find(id="ShareCopyOfMyData", raise_exc=False)
        if copy:
            await copy.click()

        # Access: list of data recipients
        recipients = await tab.find(id="ShareRecipientsOfMyData", raise_exc=False)
        if recipients:
            await recipients.click()

        if SuperScraper.REMOVE_INFORMATION:
            delete = await tab.find(id="DeleteMyData", raise_exc=False)
            if delete:
                await delete.click()

        time.sleep(0.5)

        if SuperScraper.DRY_RUN:
            await tab.take_screenshot("resources/screenshots/leadpost_dry_run.png")
            print(
                f"DRY RUN: would submit for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            return

        print("\nForm filled. Solve the reCAPTCHA v2 checkbox, then click Submit.")
        print("Press Enter after the confirmation page appears...")
        input()
        print(f"Submitted for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


asyncio.run(main())

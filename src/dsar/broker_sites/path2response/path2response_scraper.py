# path2response.com — OneTrust CDN Angular DSAR form. Exercises Do Not Sell or
# Share / Opt-Out, Access My Data, and Delete My Data (gated on
# REMOVE_INFORMATION). No subject type step. formField17DSARElement is
# "Are you submitting this request for yourself?" (autocomplete Yes/No).
# Affirmation "Yes" button required at bottom. Country and state are autocomplete
# comboboxes (ArrowDown+Enter). Phone country code vt-input-5. reCAPTCHA v2
# requires manual solve before submit.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/2de26f06-de6f-45a7-8e1d-7d1148a3f301/draft/7a5dc7d1-cc7e-43a8-9f24-702807deb65b.html"


async def main():
    options = ChromiumOptions()
    options.binary_location = "/snap/bin/chromium"
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3000")
    super_scraper = SuperScraper()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        # Select request types
        optout_btn = await tab.find(
            **{"aria-label": "Do Not Sell or Share My Personal Information / Opt-Out"},
            raise_exc=False,
        )
        if optout_btn:
            await optout_btn.click_using_js()
        await asyncio.sleep(0.3)

        access_btn = await tab.find(**{"aria-label": "Access My Data"}, raise_exc=False)
        if access_btn:
            await access_btn.click_using_js()
        await asyncio.sleep(0.3)

        if SuperScraper.REMOVE_INFORMATION:
            delete_btn = await tab.find(**{"aria-label": "Delete My Data"}, raise_exc=False)
            if delete_btn:
                await delete_btn.click_using_js()
            await asyncio.sleep(0.3)

        email = await tab.find(id="emailDSARElement", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)

        # "Are you submitting this request for yourself?" — autocomplete Yes/No
        self_field = await tab.find(id="formField17DSARElement", raise_exc=False)
        if self_field:
            await self_field.click()
            await tab.keyboard.type_text("Yes")
            await asyncio.sleep(1)
            await tab.keyboard.press(Key.ARROWDOWN)
            await asyncio.sleep(0.3)
            await tab.keyboard.press(Key.ENTER)
        await asyncio.sleep(0.5)

        first = await tab.find(id="firstNameDSARElement", raise_exc=False)
        if first:
            await first.type_text(SuperScraper.FIRST_NAME)

        last = await tab.find(id="lastNameDSARElement", raise_exc=False)
        if last:
            await last.type_text(SuperScraper.LAST_NAME)

        phone_cc = await tab.find(id="vt-input-5", raise_exc=False)
        if phone_cc:
            await phone_cc.click()
            await tab.keyboard.type_text("1")
        await asyncio.sleep(0.5)

        phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
        if phone:
            await phone.type_text(SuperScraper.PHONE_NUMBER)

        address = await tab.find(id="addressDSARElement", raise_exc=False)
        if address:
            await address.type_text(SuperScraper.ADDRESS)

        city = await tab.find(id="cityDSARElement", raise_exc=False)
        if city:
            await city.type_text(SuperScraper.CITY)

        state_field = await tab.find(id="stateDSARElement", raise_exc=False)
        if state_field:
            await state_field.click()
            await tab.keyboard.type_text(SuperScraper.STATE)
            await asyncio.sleep(2)
            await tab.keyboard.press(Key.ARROWDOWN)
            await asyncio.sleep(0.3)
            await tab.keyboard.press(Key.ENTER)
        await asyncio.sleep(0.5)

        zip_field = await tab.find(id="zipDSARElement", raise_exc=False)
        if zip_field:
            await zip_field.type_text(SuperScraper.ZIP_CODE)

        country_field = await tab.find(id="countryDSARElement", raise_exc=False)
        if country_field:
            await country_field.click()
            await tab.keyboard.type_text("United States")
            await asyncio.sleep(2)
            await tab.keyboard.press(Key.ARROWDOWN)
            await asyncio.sleep(0.3)
            await tab.keyboard.press(Key.TAB)
        await asyncio.sleep(0.5)

        # Affirmation: click "Yes" to confirm this is your own data
        yes_btn = await tab.find(**{"aria-label": "Yes"}, raise_exc=False)
        if yes_btn:
            await yes_btn.click_using_js()
        await asyncio.sleep(0.5)

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
            if submit_btn:
                await submit_btn.scroll_into_view()
            await asyncio.sleep(1)
            await tab.take_screenshot("path2response_dry_run.png")
            print("Screenshot saved to path2response_dry_run.png")
            return

        print("\nForm filled. Solve the reCAPTCHA in the browser, then click Submit.")
        print("Press Enter after the confirmation page appears...")
        input()

        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted DSAR for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())

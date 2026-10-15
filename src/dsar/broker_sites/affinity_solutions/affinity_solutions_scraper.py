# affinity.solutions — Custom OneTrust Angular DSAR portal ("Affinity Solutions Data
# Privacy Options"). Affinity does not collect data directly from consumers — the
# entire form's stated purpose is "delete and/or stop using data currently associated
# with specific identifiers", with no separate non-destructive Access alternative.
# Because deletion is inherent to the only right this form offers, the whole
# submission is gated on REMOVE_INFORMATION (DRY_RUN preview still works either way).
# Subject-type step: click "Myself". Country/State are vt-autocomplete comboboxes
# (type then ArrowDown+Enter). captchaCode is a BotDetect image CAPTCHA — requires
# manual entry in live mode.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://affinitysolutions-privacy.my.onetrust.com/webform/a564cfa1-53bf-4c10-bf95-cd907432d7e8/7e4e6bf3-6562-454e-8c73-6a7bd1f4b336"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        myself_btn = await tab.find(**{"aria-label": "Myself"}, raise_exc=False)
        if not myself_btn:
            print(f"{super_scraper.OOPS} 'Myself' subject button not found")
            return
        await myself_btn.click_using_js()
        await asyncio.sleep(1)

        first = await tab.find(id="firstNameDSARElement", raise_exc=False)
        if first:
            await first.type_text(SuperScraper.FIRST_NAME)

        last = await tab.find(id="lastNameDSARElement", raise_exc=False)
        if last:
            await last.type_text(SuperScraper.LAST_NAME)

        email = await tab.find(id="emailDSARElement", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)

        country_field = await tab.find(id="countryDSARElement", raise_exc=False)
        if country_field:
            await country_field.click()
            await tab.keyboard.type_text("United States")
            await asyncio.sleep(2)
            await tab.keyboard.press(Key.ARROWDOWN)
            await asyncio.sleep(0.3)
            await tab.keyboard.press(Key.ENTER)
        await asyncio.sleep(0.5)

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

        phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
        if phone:
            await phone.type_text(SuperScraper.PHONE_NUMBER)

        request_details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
        if request_details:
            await request_details.type_text(
                "Please delete and stop using any data you have associated with my identifiers."
            )

        if not SuperScraper.wants("delete") and not SuperScraper.DRY_RUN:
            print(
                f"{super_scraper.OOPS} affinity.solutions' only form is a deletion "
                "request — skipping real submission because REMOVE_INFORMATION is False."
            )
            return

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit deletion/opt-out request for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            captcha_field = await tab.find(id="captchaCode", raise_exc=False)
            if captcha_field:
                await captcha_field.scroll_into_view()
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "resources/screenshots/affinity_solutions_dry_run.png")
            return

        print("\nForm filled. Enter the CAPTCHA code shown in the image into the")
        print("captchaCode field, then click Submit. Press Enter after the")
        print("confirmation page appears...")
        input()

        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())

# emailindustries.com (branded "Kickbox") — Custom OneTrust Angular DSAR
# portal. Single generic submission, no request-type picker — the specific
# right is expressed via the free-text Request Details textarea. Gated on
# REMOVE_INFORMATION since a deletion ask is only included in that text when
# the user has opted into removal. Country/State are optional vt-autocomplete
# comboboxes (type then ArrowDown+Enter). captchaCode is a BotDetect image
# CAPTCHA requiring manual entry in live mode.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/f73513a8-7a10-4a9d-939a-703f8d994839/262761ab-edc4-440a-8e56-e6348b131382"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        first = await tab.find(id="firstNameDSARElement", raise_exc=False)
        if first:
            await first.type_text(SuperScraper.FIRST_NAME)
        last = await tab.find(id="lastNameDSARElement", raise_exc=False)
        if last:
            await last.type_text(SuperScraper.LAST_NAME)
        email = await tab.find(id="email", raise_exc=False)
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

        state_field = await tab.find(id="stateDSARElement", raise_exc=False)
        if state_field:
            await state_field.click()
            await tab.keyboard.type_text(SuperScraper.STATE)
            await asyncio.sleep(2)
            await tab.keyboard.press(Key.ARROWDOWN)
            await asyncio.sleep(0.3)
            await tab.keyboard.press(Key.ENTER)
        await asyncio.sleep(0.5)

        if SuperScraper.REMOVE_INFORMATION:
            request_text = (
                "I am requesting access to and deletion of my personal information "
                "under applicable privacy law."
            )
        else:
            request_text = "I am requesting access to my personal information under applicable privacy law."
        request_details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
        if request_details:
            await request_details.type_text(request_text)

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit request for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            captcha_field = await tab.find(id="captchaCode", raise_exc=False)
            if captcha_field:
                await captcha_field.scroll_into_view()
            await asyncio.sleep(1)
            await tab.take_screenshot(path="resources/screenshots/emailindustries_dry_run.png")
            print("Screenshot saved to resources/screenshots/emailindustries_dry_run.png")
            return

        print("\nForm filled. Enter the CAPTCHA code, click Submit,")
        print("then press Enter once the confirmation page appears...")
        input()

        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())

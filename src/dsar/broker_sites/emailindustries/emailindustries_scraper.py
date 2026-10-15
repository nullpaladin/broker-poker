# emailindustries.com (branded "Kickbox") — Custom OneTrust Angular DSAR
# portal. Single generic submission, no request-type picker — the specific
# rights are expressed via the free-text Request Details textarea. Country/State are optional vt-autocomplete
# comboboxes (type then ArrowDown+Enter). captchaCode is a BotDetect image
# CAPTCHA requiring manual entry in live mode.
#
# Page elements:
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #email                                          Email
#   #countryDSARElement / #stateDSARElement         Country / State comboboxes (optional)
#   #requestDetailsDSARElement                      Request Details textarea
#   #captchaCode                                    image CAPTCHA text input
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/f73513a8-7a10-4a9d-939a-703f8d994839/262761ab-edc4-440a-8e56-e6348b131382"

# No request-type picker: every right is expressed in the free-text details box.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Request Details text",
    Right.RIGHT_TO_DELETE: "Request Details text",
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

        request_text = SuperScraper.request_statement(rights, broker="Kickbox")
        request_details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
        if request_details:
            await request_details.type_text(request_text)

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}"
            )
            captcha_field = await tab.find(id="captchaCode", raise_exc=False)
            if captcha_field:
                await captcha_field.scroll_into_view()
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        print("\nForm filled. Enter the CAPTCHA code, click Submit,")
        print("then press Enter once the confirmation page appears...")
        input()

        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())

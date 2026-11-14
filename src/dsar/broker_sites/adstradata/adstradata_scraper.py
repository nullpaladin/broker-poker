# adstradata.com — Custom OneTrust Angular DSAR portal (single combined form titled
# "Data Subject Access Do Not Sell or Share My Personal Information Request" —
# Access and Opt-Out of Sale/Share in one submission, no separate request-type
# picker). No Delete option offered on this form. No subject-type step.
# NOTE: the URL originally recorded for this broker (…/f4d95cf7-…) is actually
# Adstra's "Authorized Agent Portal" — a dead end with no fields for a consumer
# submitting their own request. The correct self-service URL below was found via
# the footer's "Do Not Sell My Personal Information" link on the privacy policy page.
# Country/State are vt-autocomplete comboboxes (type then ArrowDown+Enter).
# Phone country code field id="vt-input-8"-style (id varies — resolved via
# preceding-sibling structure below). captchaCode is a BotDetect image CAPTCHA —
# requires manual entry in live mode.
# The one combined form covers RIGHT_TO_ACCESS and RIGHT_TO_OPT_OUT, so it is submitted once
# if either is requested (decided only by SuperScraper.rights_to_exercise).
#
# Page elements:
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #emailDSARElement                              Email
#   #countryDSARElement                            Country combobox -> "United States"
#   #addressDSARElement                            Address
#   #cityDSARElement                               City
#   #stateDSARElement                              State combobox (full state name)
#   #zipDSARElement                                Zip code
#   #phoneNumberDSARElement                        Phone number
#   #captchaCode                                   BotDetect image CAPTCHA code (manual entry)
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/3d2d5e0c-bd98-46b8-906c-ede68a6f6a80/f54a1b10-bb5d-4c99-9521-3e08dc527583"

# Both rights are served by the same combined form (one submission).
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "combined access / do-not-sell form",
    Right.RIGHT_TO_OPT_OUT: "combined access / do-not-sell form",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIELD_XPATHS = {
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Country": "//*[@id='countryDSARElement']",
    "Address": "//*[@id='addressDSARElement']",
    "City": "//*[@id='cityDSARElement']",
    "State": "//*[@id='stateDSARElement']",
    "Zip": "//*[@id='zipDSARElement']",
    "Phone": "//*[@id='phoneNumberDSARElement']",
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

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit {[r.name for r in rights]} (combined form) "
                f"for {SuperScraper.EMAIL}"
            )
            captcha_field = await tab.find(id="captchaCode", raise_exc=False)
            if captcha_field:
                await captcha_field.scroll_into_view()
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
            return

        print("\nForm filled. Enter the CAPTCHA code shown in the image into the")
        print("captchaCode field, then click Submit. Press Enter after the")
        print("confirmation page appears...")
        input()

        print(f"Submitted {[r.name for r in rights]} (combined form) for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())

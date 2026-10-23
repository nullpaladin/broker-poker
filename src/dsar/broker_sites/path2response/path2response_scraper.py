# path2response.com — OneTrust CDN Angular DSAR form. Rights the form exposes: Do Not Sell or
# Share / Opt-Out, Access My Data, Delete My Data (no Correct). The request-type cards are
# multi-selected in ONE submission; which of them are clicked is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). No subject type step. reCAPTCHA v2 requires a
# manual solve before submit.
#
# Page elements (keep this list current):
#   aria-label "Do Not Sell or Share My Personal Information / Opt-Out"   -> RIGHT_TO_OPT_OUT
#   aria-label "Access My Data"                                           -> RIGHT_TO_ACCESS
#   aria-label "Delete My Data"                                           -> RIGHT_TO_DELETE
#   #emailDSARElement / #firstNameDSARElement / #lastNameDSARElement      Email / First / Last name
#   #formField17DSARElement   "Are you submitting this request for yourself?" autocomplete (Yes/No) -> "Yes"
#   vt-input-5 (PHONE_COUNTRY_CODE)   Phone country code (type "1")
#   #phoneNumberDSARElement   Phone number
#   #addressDSARElement / #cityDSARElement / #zipDSARElement   Street address / City / ZIP
#   #stateDSARElement / #countryDSARElement   State / Country autocomplete comboboxes (ArrowDown+Enter/Tab)
#   aria-label "Yes"          Affirmation button at the bottom (click_using_js)
#   aria-label "click to submit form"   Submit button
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/2de26f06-de6f-45a7-8e1d-7d1148a3f301/draft/7a5dc7d1-cc7e-43a8-9f24-702807deb65b.html"

RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: "Do Not Sell or Share My Personal Information / Opt-Out",
    Right.RIGHT_TO_ACCESS: "Access My Data",
    Right.RIGHT_TO_DELETE: "Delete My Data",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Recorded request types are aria-labels; the visible text may differ, so they are not copied in.)

FIELD_XPATHS = {
    "Email": "//*[@id='emailDSARElement']",
    "Submitting for yourself": "//*[@id='formField17DSARElement']",
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Phone": "//*[@id='phoneNumberDSARElement']",
    "Address": "//*[@id='addressDSARElement']",
    "City": "//*[@id='cityDSARElement']",
    "State": "//*[@id='stateDSARElement']",
    "Zip": "//*[@id='zipDSARElement']",
    "Country": "//*[@id='countryDSARElement']",
}
PHONE_COUNTRY_CODE = "vt-input-5"


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        # Select request types
        for right in rights:
            btn = await tab.find(**{"aria-label": RIGHT_MAP[right]}, raise_exc=False)
            if btn:
                await btn.click_using_js()
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

        phone_cc = await tab.find(id=PHONE_COUNTRY_CODE, raise_exc=False)
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

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
            if submit_btn:
                await submit_btn.scroll_into_view()
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
            return

        print("\nForm filled. Solve the reCAPTCHA in the browser, then click Submit.")
        print("Press Enter after the confirmation page appears...")
        input()

        print(f"Submitted [{', '.join(r.name for r in rights)}] for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())

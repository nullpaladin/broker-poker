# growinglibraries.com — Opt-Out/Delete only, no Access request offered.
# A HubSpot form (g-recaptcha-response/hs_context field names) embedded
# directly in the page (not an iframe). Field `name`s are stable HubSpot
# labels (firstname, lastname, address, street_address_2, city, state_,
# country, zip, email) but the DOM `id`s all carry a random per-load UUID
# suffix (e.g. "firstname-9adf795f-...-9895_6134"), so fields are targeted by
# `name` via xpath rather than by id. Phone number/extension select have NO
# `name` attribute at all (only the id-with-UUID) — targeted by an
# `id^="phone-"` / `id^="phone_ext-"` starts-with CSS selector instead.
# Country/Region is a plain free-text field, not a select. Shipping State
# *is* a real <select> with full state names as option text. A cookie
# consent modal ("Accept"/"Decline") covers the page on first load and must
# be dismissed before the form is interactable. reCAPTCHA v2 checkbox
# present — **CAPTCHA solution required** in live mode.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://growinglibraries.com/do-not-sell"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        decline_cookies = await tab.find(text="Decline", raise_exc=False)
        if decline_cookies:
            await decline_cookies.click()
            await asyncio.sleep(1)

        fields = {
            "firstname": SuperScraper.FIRST_NAME,
            "lastname": SuperScraper.LAST_NAME,
            "address": SuperScraper.ADDRESS,
            "street_address_2": SuperScraper.ADDRESS_LINE_TWO,
            "city": SuperScraper.CITY,
            "country": "United States",
            "zip": SuperScraper.ZIP_CODE,
            "email": SuperScraper.EMAIL,
        }
        for field_name, value in fields.items():
            if not value:
                continue
            field = await tab.find(xpath=f"//input[@name='{field_name}']", raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_name}' not found")

        state_select = await tab.find(xpath="//select[@name='state_']", raise_exc=False)
        if state_select:
            await state_select.execute_script(
                "for (var i=0;i<this.options.length;i++){"
                f"  if(this.options[i].text==={SuperScraper.STATE!r}){{ this.selectedIndex=i; }}"
                "}"
                "this.dispatchEvent(new Event('change', {bubbles:true}));"
            )

        phone_field = await tab.find(xpath="//input[starts-with(@id,'phone-')]", raise_exc=False)
        if phone_field and SuperScraper.PHONE_NUMBER:
            await phone_field.type_text(SuperScraper.PHONE_NUMBER)

        checkbox = await tab.find(
            xpath="//input[@type='checkbox' and starts-with(@name,'i_am_requesting')]",
            raise_exc=False,
        )
        if checkbox:
            await checkbox.click()
        else:
            print(f"{super_scraper.OOPS} attestation checkbox not found")

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/growinglibraries_dry_run.png")
        print("Screenshot saved to resources/screenshots/growinglibraries_dry_run.png")
        print(
            "\nForm filled but NOT submitted — a reCAPTCHA v2 checkbox is present and requires "
            "a manual solve before clicking SUBMIT."
        )


asyncio.run(main())

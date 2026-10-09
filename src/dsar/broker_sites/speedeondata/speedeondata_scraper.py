# speedeondata.com — optout.speedeondata.com is a simple custom form. Only
# Opt-Out/Delete/Sensitive-Data exist (no Right to Access anywhere on the
# site — confirmed by prior manual investigation). "Opt-out" and "Sensitive
# Data" (limit use of religious-affiliation/ethnicity/ailment data) checkboxes
# are exercised unconditionally; "Deletion" gated on REMOVE_INFORMATION — at
# least one of the three is required by the form. State is a Bootstrap
# dropdown of `<button role="menuitem" title="<Full Name>" value="<Abbrev>">`
# items rather than a native <select> — matched by `title` and clicked
# directly (items exist in the DOM whether or not the toggle button has been
# opened). reCAPTCHA v2 checkbox present — **CAPTCHA solution required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://optout.speedeondata.com/"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        opt_out_checkbox = await tab.find(id="optOut", raise_exc=False)
        if opt_out_checkbox:
            await opt_out_checkbox.click()
        else:
            print(f"{super_scraper.OOPS} 'Opt-out' checkbox not found")

        sensitive_checkbox = await tab.find(id="sensitiveData", raise_exc=False)
        if sensitive_checkbox:
            await sensitive_checkbox.click()
        else:
            print(f"{super_scraper.OOPS} 'Sensitive Data' checkbox not found")

        if SuperScraper.wants("delete"):
            deletion_checkbox = await tab.find(id="deletion", raise_exc=False)
            if deletion_checkbox:
                await deletion_checkbox.click()
            else:
                print(f"{super_scraper.OOPS} 'Deletion' checkbox not found")

        fields = {
            "firstName": SuperScraper.FIRST_NAME,
            "lastName": SuperScraper.LAST_NAME,
            "email": SuperScraper.EMAIL,
            "phone": SuperScraper.PHONE_NUMBER,
            "address1": SuperScraper.ADDRESS,
            "address2": SuperScraper.ADDRESS_LINE_TWO,
            "city": SuperScraper.CITY,
            "zip": SuperScraper.ZIP_CODE,
        }
        for name, value in fields.items():
            if not value:
                continue
            field = await tab.find(name=name, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{name}' not found")

        state_toggle = await tab.find(xpath="//button[contains(@class,'dropdown-toggle')]", raise_exc=False)
        if state_toggle:
            await state_toggle.click()
            await asyncio.sleep(0.5)
        else:
            print(f"{super_scraper.OOPS} State dropdown toggle not found")

        state_button = await tab.find(
            xpath=f"//button[@role='menuitem' and @title={SuperScraper.STATE!r}]", raise_exc=False
        )
        if state_button:
            await state_button.click()
        else:
            print(f"{super_scraper.OOPS} State option '{SuperScraper.STATE}' not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/speedeondata_dry_run.png")
        print(
            "\nRequest filled but NOT submitted — a reCAPTCHA v2 checkbox requires a manual "
            "solve before submitting."
        )


asyncio.run(main())

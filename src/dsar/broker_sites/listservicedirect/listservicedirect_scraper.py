# listservicedirect.com — /opt-out/ Contact Form 7, server-rendered, AJAX POST
# in place. The request-type <select name="Please"> offers only "Opt-Out", so
# this form is opt-out only (the site never answered an emailed Right to Access
# request — see README). Single submission.
# Fields: your-name, your-email, telephone-number, Company, Address, City,
# State, Zip, your-message (left blank). The text input name="yes" is NOT a
# honeypot despite its name — its label reads "By typing 'YES' in the box
# provided below you certify you are the individual noted above ... (required)",
# so it is filled with "YES". The page hosts a second, unrelated CF7 form
# (count-requests, _wpcf7=1473) that shares field names; every lookup is scoped
# to the form that contains <select name="Please"> to avoid it. Ends in a
# reCAPTCHA v2 — filled to that point and left for a manual solve + Send.
# **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://listservicedirect.com/opt-out/"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    full_name = " ".join(p for p in (SuperScraper.FIRST_NAME, SuperScraper.LAST_NAME) if p)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        form_xp = "//form[.//select[@name='Please']]"

        please = await tab.find(xpath=f"{form_xp}//select[@name='Please']", raise_exc=False)
        if please:
            await SuperScraper.select_native_option(please, text="Opt-Out")

        fields = {
            "your-name": full_name,
            "your-email": SuperScraper.EMAIL,
            "telephone-number": SuperScraper.PHONE_NUMBER,
            "Company": SuperScraper.COMPANY_NAME,
            "Address": SuperScraper.ADDRESS,
            "City": SuperScraper.CITY,
            "State": SuperScraper.STATE,
            "Zip": SuperScraper.ZIP_CODE,
            "yes": "YES",
        }
        for name, val in fields.items():
            if not val:
                continue
            el = await tab.find(xpath=f"{form_xp}//input[@name={name!r}]", raise_exc=False)
            if el:
                await el.type_text(val)
                await asyncio.sleep(0.15)
            else:
                print(f"{super_scraper.OOPS} field '{name}' not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/listservicedirect_dry_run.png")
        print(
            "Opt-Out request filled but NOT submitted — solve the reCAPTCHA "
            "manually, then click Send."
        )


asyncio.run(main())

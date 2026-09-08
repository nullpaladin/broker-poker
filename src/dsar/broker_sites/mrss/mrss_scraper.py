# mrss.com (M+R) — /my-personal-information/ is a simple opt-out-of-sale form;
# no Right to Access exists on the site (confirmed by prior manual
# investigation). A cookie-consent banner (CookieYes) covers the page on
# first load and must be dismissed via "Accept All" before the form is
# interactable. Only Email (required) and Phone are collected — "emailProxy"
# ("If you are submitting this request on behalf of someone else") is left
# blank since this repo only ever requests on behalf of the account holder.
# reCAPTCHA Enterprise is invisible (badge only, no challenge widget renders)
# — auto-resolves, no manual solve needed, so DRY_RUN is respected and a real
# submission goes through when DRY_RUN is False. A separate footer newsletter
# signup form (footer_first_name/footer_last_name/footer_email/footer_org)
# exists on the same page and is unrelated — not touched.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.mrss.com/my-personal-information/"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        accept_cookies = await tab.find(class_name="cky-btn-accept", raise_exc=False)
        if accept_cookies:
            await accept_cookies.click_using_js()
            await asyncio.sleep(1.5)

        email_field = await tab.find(id="emailMain", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)
        else:
            print(f"{super_scraper.OOPS} Email field not found")

        phone_field = await tab.find(id="phone", raise_exc=False)
        if phone_field:
            await phone_field.type_text(SuperScraper.PHONE_NUMBER)
        else:
            print(f"{super_scraper.OOPS} Phone field not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/mrss_dry_run.png")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit opt-out-of-sale request for {SuperScraper.EMAIL}")
            return

        send_button = await tab.find(text="Send", raise_exc=False)
        if send_button:
            await send_button.click()
            await asyncio.sleep(3)
            print(f"Submitted opt-out-of-sale request for {SuperScraper.EMAIL}")
        else:
            print(f"{super_scraper.OOPS} Send button not found")


asyncio.run(main())

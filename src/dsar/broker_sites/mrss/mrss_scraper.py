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
# exists on the same page and is unrelated — not touched. Whether the opt-out runs is
# decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements (keep this list current):
#   .cky-btn-accept           CookieYes "Accept All" button
#   #emailMain                Email (required)
#   #phone                    Phone
#   "Send" button             found by its text
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.mrss.com/my-personal-information/"

COOKIE_ACCEPT_CLASS = "cky-btn-accept"  # CookieYes "Accept All"
EMAIL_ID = "emailMain"  # Email
PHONE_ID = "phone"  # Phone

RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: "opt-out of sale",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIELD_XPATHS = {
    "Email": f"//*[@id='{EMAIL_ID}']",
    "Phone": f"//*[@id='{PHONE_ID}']",
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
        await asyncio.sleep(5)

        accept_cookies = await tab.find(class_name=COOKIE_ACCEPT_CLASS, raise_exc=False)
        if accept_cookies:
            await accept_cookies.click_using_js()
            await asyncio.sleep(1.5)

        email_field = await tab.find(id=EMAIL_ID, raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)
        else:
            print(f"{super_scraper.OOPS} Email field not found")

        phone_field = await tab.find(id=PHONE_ID, raise_exc=False)
        if phone_field:
            await phone_field.type_text(SuperScraper.PHONE_NUMBER)
        else:
            print(f"{super_scraper.OOPS} Phone field not found")

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_opt_out")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit 'RIGHT_TO_OPT_OUT' for {SuperScraper.EMAIL}")
            return

        send_button = await tab.find(text="Send", raise_exc=False)
        if send_button:
            await send_button.click()
            await asyncio.sleep(3)
            print(f"Submitted 'RIGHT_TO_OPT_OUT' for {SuperScraper.EMAIL} — confirm in the browser.")
        else:
            print(f"{super_scraper.OOPS} Send button not found")


asyncio.run(main())

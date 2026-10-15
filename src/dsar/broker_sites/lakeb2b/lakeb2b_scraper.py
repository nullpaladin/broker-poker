# lakeb2b.com — /do-not-sell-my-data "Data Alteration Request" form (a
# Contact Form 7 form whose submit button still reads "Get a Quote Now!" from
# the template it was cloned from). Server-rendered, AJAX POST in place.
#
# The two CF7 "acceptance" checkboxes act as the request selector:
#   acceptance1 = "Alter frequency of news notifications ..." (left unchecked)
#   acceptance2 = "Opt-out of the mailing list ..."          (checked)
# There is no Access/Delete option on this form — the site says those go by
# email (privacy@lakeb2b.com) — so this exercises Opt-Out only; the free-text
# "message" field additionally states the request in words. Whether it runs is
# decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). No CAPTCHA seen.
#
# Page elements:
#   input[name=acceptance1]  "Alter frequency of news notifications ..." (left unchecked)
#   input[name=acceptance2]  "Opt-out of the mailing list ..."           (checked)
#   first-name / last-name   First / Last name
#   your-email / phone       Email / Phone
#   address / city / state / zip   Address fields
#   message                  Free-text message
#   input[type=submit]       Submit (labelled "Get a Quote Now!")
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.lakeb2b.com/do-not-sell-my-data"

RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "opt-out"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        optout = await tab.find(xpath="//input[@name='acceptance2']", raise_exc=False)
        if optout:
            await optout.click()
        else:
            print(f"{super_scraper.OOPS} opt-out acceptance checkbox not found")

        fields = {
            "first-name": SuperScraper.FIRST_NAME,
            "last-name": SuperScraper.LAST_NAME,
            "your-email": SuperScraper.EMAIL,
            "phone": SuperScraper.PHONE_NUMBER,
            "address": SuperScraper.ADDRESS,
            "city": SuperScraper.CITY,
            "state": SuperScraper.STATE,
            "zip": SuperScraper.ZIP_CODE,
            "message": SuperScraper.request_statement(rights, broker="LakeB2B"),
        }
        for name, val in fields.items():
            if not val:
                continue
            el = await tab.find(xpath=f"//*[@name={name!r}]", raise_exc=False)
            if el:
                await el.type_text(val)
                await asyncio.sleep(0.15)
            else:
                print(f"{super_scraper.OOPS} field '{name}' not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit opt-out for {SuperScraper.EMAIL}")
            return

        submit = await tab.find(xpath="//input[@type='submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(f"Submitted 'RIGHT_TO_OPT_OUT' for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())

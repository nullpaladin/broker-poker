# salutarydata.com — /privacy-opt-out-and-disclosure-form/ . Right to Opt-Out
# of Sale/Sharing only (their Access email is broken and Delete does not exist
# per the site — see README). The page embeds three HubSpot forms via the newer
# `js.hsforms.net/ui-forms-embed-components-app/frame.html` iframe; the opt-out
# form is the one containing a "work email" / "Current Employer" field. Despite
# the marketforcecorp.com note that this embed "renders no fields standalone",
# pydoll's `.find()` on the iframe WebElement DOES resolve into it here.
#
# Fields (frame 0): 0-1/firstname, 0-1/lastname, 0-1/work_email, 0-1/company
# (current employer name), 0-2/address / 0-2/city / 0-2/state / 0-2/zip
# (employer address — filled from the persona's address, the best available).
# Element notes: iframe[src*=ui-forms-embed-components-app] holding the opt-out form;
#   0-1/firstname First name, 0-1/lastname Last name, 0-1/work_email Work email,
#   0-1/company Current Employer, 0-2/address Address, 0-2/city City, 0-2/state State, 0-2/zip Zip.
# Invisible reCAPTCHA Enterprise gates submit.  **CAPTCHA solution required**
# Not submitted by the scraper (manual reCAPTCHA solve, then Submit).
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "opt-out"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIELD_NAMES = {
    "First name": "0-1/firstname",
    "Last name": "0-1/lastname",
    "Work email": "0-1/work_email",
    "Address": "0-2/address",
    "City": "0-2/city",
    "State": "0-2/state",
    "Zip": "0-2/zip",
}

URL = "https://salutarydata.com/privacy-opt-out-and-disclosure-form/"


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
        await asyncio.sleep(10)

        iframes = await tab.find(
            xpath="//iframe[contains(@src,'ui-forms-embed-components-app')]",
            find_all=True,
            raise_exc=False,
        ) or []
        target = None
        for ifr in iframes:
            probe = await ifr.find(xpath="//input[@name='0-1/work_email']", raise_exc=False)
            if probe:
                target = ifr
                break
        if not target:
            print(f"{super_scraper.OOPS} opt-out HubSpot form iframe not found")
            return

        fields = {
            "0-1/firstname": SuperScraper.FIRST_NAME,
            "0-1/lastname": SuperScraper.LAST_NAME,
            "0-1/work_email": SuperScraper.EMAIL,
            "0-1/company": SuperScraper.COMPANY_NAME,
            "0-2/address": SuperScraper.ADDRESS,
            "0-2/city": SuperScraper.CITY,
            "0-2/state": SuperScraper.STATE,
            "0-2/zip": SuperScraper.ZIP_CODE,
        }
        for name, value in fields.items():
            if not value:
                continue
            el = await target.find(xpath=f"//input[@name={name!r}]", raise_exc=False)
            if el:
                await el.type_text(value)
                await asyncio.sleep(0.2)
            else:
                print(f"{super_scraper.OOPS} field name={name!r} not found in frame")

        if SuperScraper.HEALTH_CHECK:
            # `target` (the iframe element) stands in for `tab`: target.find() resolves into the frame's document.
            await SuperScraper.assert_fields_filled(
                target, {label: f"//input[@name={name!r}]" for label, name in FIELD_NAMES.items()}
            )

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_opt_out")
        print("Opt-out request filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


asyncio.run(main())

# homeownersmarketingservices.com — /list-removal-request-new/ Elementor Pro
# form ("DNM-NEW"), server-rendered, AJAX POST in place. The site leans on the
# public-records carve-out to decline CCPA-style Access/Delete, but offers this
# mailing-list removal (opt-out) request. Single submission, opt-out only; run only
# when SuperScraper.rights_to_exercise(RIGHT_MAP) includes Opt-out.
# Fields:
#   form_fields[name]              -> id form-field-name   (full name)
#   form_fields[email]             -> id form-field-email
#   form_fields[field_6d53f74]     -> id form-field-field_6d53f74 (home address,
#                                     "123 Main St, City ST 00000" style)
#   form_fields[message]           -> id form-field-message (optional, left blank)
#   form_fields[privtrue]          -> hidden honeypot (display:none) — left blank
# A reCAPTCHA is present on the page; fill everything and leave the solve +
# submit for a human.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://homeownersmarketingservices.com/list-removal-request-new/"

# The form is a single mailing-list removal request (no choice to make).
RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "list removal"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIELD_XPATHS = {
    "Name": "//*[@id='form-field-name']",
    "Email": "//*[@id='form-field-email']",
    "Home address": "//*[@id='form-field-field_6d53f74']",
}


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    if not SuperScraper.rights_to_exercise(RIGHT_MAP):
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    full_name = " ".join(p for p in (SuperScraper.FIRST_NAME, SuperScraper.LAST_NAME) if p)
    address_bits = [SuperScraper.ADDRESS, SuperScraper.CITY,
                    f"{SuperScraper.STATE_ABBREVIATED} {SuperScraper.ZIP_CODE}".strip()]
    home_address = ", ".join(b for b in address_bits if b and b.strip())

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        fields = {
            "form-field-name": full_name,
            "form-field-email": SuperScraper.EMAIL,
            "form-field-field_6d53f74": home_address,
        }
        for field_id, val in fields.items():
            if not val:
                continue
            el = await tab.find(id=field_id, raise_exc=False)
            if el:
                await el.type_text(val)
                await asyncio.sleep(0.2)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            "List-removal request filled but NOT submitted — solve the reCAPTCHA "
            "manually, then click the submit button."
        )


asyncio.run(main())

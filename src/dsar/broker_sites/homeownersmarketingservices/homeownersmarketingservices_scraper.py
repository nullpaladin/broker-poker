# homeownersmarketingservices.com — /list-removal-request-new/ Elementor Pro
# form ("DNM-NEW"), server-rendered, AJAX POST in place. The site leans on the
# public-records carve-out to decline CCPA-style Access/Delete, but offers this
# mailing-list removal (opt-out) request. Single submission, opt-out only.
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
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://homeownersmarketingservices.com/list-removal-request-new/"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,2600")

    full_name = " ".join(p for p in (SuperScraper.FIRST_NAME, SuperScraper.LAST_NAME) if p)
    address_bits = [SuperScraper.ADDRESS, SuperScraper.CITY,
                    f"{await SuperScraper.state_full_name_to_abbreviated(SuperScraper.STATE)} {SuperScraper.ZIP_CODE}".strip()]
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

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/homeownersmarketingservices_dry_run.png")
        print("Screenshot saved to resources/screenshots/homeownersmarketingservices_dry_run.png")
        print(
            "List-removal request filled but NOT submitted — solve the reCAPTCHA "
            "manually, then click the submit button."
        )


asyncio.run(main())

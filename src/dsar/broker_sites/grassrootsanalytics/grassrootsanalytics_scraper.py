# grassrootsanalytics.com — Wix site, single submission. Rights via checkbox
# group; which boxes get ticked is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). Wix checkboxes are visually hidden (opacity:0) —
# clicked via their wrapping <label> ancestor, not the input directly. The
# "Do Not Sell" label text is truncated on the live site (missing its final
# "n" — "...Informatio") so the match string below is deliberately a shorter
# substring that survives either spelling. Wix's own CAPTCHA widget requires
# manual solve in live mode.
#
# Page elements (inputs located by name):
#   first-name / last-name   First / Last name
#   email                    Email
#   phone-number             Phone number
#   street-address / city / state   Street address / City / State
#   Checkbox "Access My Personal Information"
#   Checkbox "Do Not Sell My Personal Information" (matched on "...Informat")
#   Checkbox "Delete My Personal Information"
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.grassrootsanalytics.com/california-consumer-privacy-act-ccpa"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Access My Personal Information",
    Right.RIGHT_TO_OPT_OUT: "Do Not Sell My Personal Informat",
    Right.RIGHT_TO_DELETE: "Delete My Personal Information",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The "Do Not Sell" label is truncated on the live site, so no exact inventory is built.)

FIELD_XPATHS = {
    "First name": "//*[@name='first-name']",
    "Last name": "//*[@name='last-name']",
    "Email": "//*[@name='email']",
    "Phone": "//*[@name='phone-number']",
    "Street address": "//*[@name='street-address']",
    "City": "//*[@name='city']",
    "State": "//*[@name='state']",
}


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        for name, value in [
            ("first-name", SuperScraper.FIRST_NAME),
            ("last-name", SuperScraper.LAST_NAME),
            ("email", SuperScraper.EMAIL),
            ("phone-number", SuperScraper.PHONE_NUMBER),
            ("city", SuperScraper.CITY),
            ("street-address", SuperScraper.ADDRESS),
            ("state", SuperScraper.STATE),
        ]:
            field = await tab.find(name=name, raise_exc=False)
            if field:
                await field.type_text(value)
                await asyncio.sleep(0.2)

        for right in rights:
            text = RIGHT_MAP[right]
            label = await tab.find(xpath=f"//label[.//span[contains(text(),'{text}')]]", raise_exc=False)
            if label:
                await label.click()
                await asyncio.sleep(0.2)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.EMAIL}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        print("\nForm filled. Solve the CAPTCHA, click Submit,")
        print("then press Enter once the confirmation appears...")
        input()

        print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())

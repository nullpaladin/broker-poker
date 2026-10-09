# aspire-north.com — the DSAR mechanism is the "California - Right to Deletion"
# form on the related domain americanspiritcorp.com. Formsite-hosted, server-
# rendered, POSTs in place. Right to Delete / Opt-Out (the button reads
# "Submit Request/Opt-Out"). The right email (per README) has gone unanswered.
# Fields (Formsite `fieldNNNNNNNNN-...` names):
#   field103068929-first / -last
#   field103068930-address / -address2 / -city / -state (<select>, full names)
#     / -zip
#   field103068931_1  a required checkbox (declaration) -> checked
#   field103068933    email
# An invisible reCAPTCHA v3 badge is present; no manual solve for a dry run,
# though Google may still score the automated submit.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.americanspiritcorp.com/ca-right-to-deletion.html"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        fields = {
            "field103068929-first": SuperScraper.FIRST_NAME,
            "field103068929-last": SuperScraper.LAST_NAME,
            "field103068930-address": SuperScraper.ADDRESS,
            "field103068930-address2": SuperScraper.ADDRESS_LINE_TWO,
            "field103068930-city": SuperScraper.CITY,
            "field103068930-zip": SuperScraper.ZIP_CODE,
            "field103068933": SuperScraper.EMAIL,
        }
        for field_id, val in fields.items():
            if not val:
                continue
            el = await tab.find(id=field_id, raise_exc=False)
            if el:
                await el.type_text(val)
                await asyncio.sleep(0.15)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        state = await tab.find(id="field103068930-state", raise_exc=False)
        if state:
            await SuperScraper.select_native_option(state, text=SuperScraper.STATE)

        checkbox = await tab.find(id="field103068931_1", raise_exc=False)
        if checkbox:
            await checkbox.click()
        else:
            print(f"{super_scraper.OOPS} declaration checkbox not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/aspirenorth_dry_run.png", beyond_viewport=True)
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit deletion/opt-out for {SuperScraper.EMAIL}")
            return

        submit = await tab.find(
            xpath="//*[normalize-space()='Submit Request/Opt-Out' or @type='submit']", raise_exc=False
        )
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(f"Submitted deletion/opt-out for {SuperScraper.EMAIL}")


asyncio.run(main())

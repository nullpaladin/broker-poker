# resonate.com — the marketing page (submit-consumer-privacy-request/)
# only lazy-loads an iframe pointing at the real form host,
# https://optout-form.reson8.com/ — navigate there directly (the marketing
# page's own raw HTML has no form fields at all until the iframe loads,
# same "navigate to the iframe src" pattern as media.net/preqin.com
# elsewhere in this repo). Simple custom (non-OneTrust) form, no CAPTCHA
# observed. Fields have no id/name on the plain inputs — targeted by CSS
# class (first_name/last_name/email/state). "Requested Action(s)" is a
# genuinely multi-select checkbox group (all applicable rights checked in
# ONE combined submission): Access to Information and Opt Out of Sale
# unconditionally; Deletion of My Data gated on REMOVE_INFORMATION. Limit
# Use of Sensitive Info/Correct My Data/Port My Data left unchecked (no
# concrete correction/portability need for a generic request).
# "Designated Agent" checkbox left unchecked. "Resonate Identifier" is a
# disabled, auto-populated-only field (shows "Resonate Identifier not
# found" for a fresh session with no Resonate cookie) — left as-is, not
# fillable.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://optout-form.reson8.com/"

CHECKBOX_VALUES = ["aboutInfoRequested", "optOutRequested"]
DELETE_CHECKBOX_VALUE = "deleteDataRequested"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        fields = {
            "first_name": SuperScraper.FIRST_NAME,
            "last_name": SuperScraper.LAST_NAME,
            "email": SuperScraper.EMAIL,
        }
        for class_name, value in fields.items():
            field = await tab.find(xpath=f"//input[@class='{class_name}']", raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{class_name}' not found")

        state_select = await tab.find(xpath="//select[@class='state']", raise_exc=False)
        if state_select:
            state_abbrev = await SuperScraper.state_full_name_to_abbreviated(SuperScraper.STATE)
            await state_select.execute_script(
                "for (var i=0;i<this.options.length;i++){"
                f"  if(this.options[i].value==={state_abbrev!r}){{ this.selectedIndex=i; }}"
                "}"
                "this.dispatchEvent(new Event('change', {bubbles:true}));"
            )
        else:
            print(f"{super_scraper.OOPS} State select not found")

        checkbox_values = list(CHECKBOX_VALUES)
        if SuperScraper.REMOVE_INFORMATION:
            checkbox_values.append(DELETE_CHECKBOX_VALUE)
        for value in checkbox_values:
            checkbox = await tab.find(xpath=f"//input[@name='{value}']", raise_exc=False)
            if checkbox:
                await checkbox.click()
            else:
                print(f"{super_scraper.OOPS} checkbox '{value}' not found")

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/resonate_dry_run.png")
        print("Screenshot saved to resources/screenshots/resonate_dry_run.png")

        if SuperScraper.DRY_RUN:
            print("DRY RUN: would submit consumer privacy request")
            return

        submit_btn = await tab.find(id="submit-btn", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(2)
            print("Submitted consumer privacy request")
        else:
            print(f"{super_scraper.OOPS} Submit button not found")


asyncio.run(main())

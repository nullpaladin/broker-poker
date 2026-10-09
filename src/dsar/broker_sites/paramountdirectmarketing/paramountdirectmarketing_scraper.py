# paramountdirectmarketing.com — /do-not-sell-non-ca (the CA-resident
# variant at /do-not-sell-ca is a separate, near-identical form; non-CA
# used here since the persona is Minnesota). Right to Access is CALIFORNIA
# ONLY per the README and not covered by either form — only "Right to Opt
# Out" and "Right to Delete" checkboxes (select-all-that-apply, one
# combined submission), no Access option exists at all on this flow.
# First choose "I am submitting this request for myself" (vs. authorized
# agent) to reveal the form. State is a plain 2-letter-abbreviation
# `<select>`. The page notes "the state you select is compared against
# the general location of your connection" for fraud prevention — worth
# knowing if a submission is unexpectedly rejected, doesn't change what
# gets filled here. reCAPTCHA v2 present — **CAPTCHA solution required**.
# Exercises Opt-Out unconditionally; Delete checkbox gated on
# REMOVE_INFORMATION.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://paramountdirectmarketing.com/do-not-sell-non-ca"

RIGHT_MAP = {"opt_out_sale_share": ["optOut"], "delete": ["deleteInfo"]}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        myself_btn = await tab.find(text="I am submitting this request for myself", raise_exc=False)
        if myself_btn:
            await myself_btn.click()
            await asyncio.sleep(2)
        else:
            print(f"{super_scraper.OOPS} 'I am submitting this request for myself' option not found")

        codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
        if not codes:
            print("No requested privacy rights apply to this form — nothing to do.")
            return
        checkbox_ids = [cb for code in codes for cb in RIGHT_MAP[code]]
        for checkbox_id in checkbox_ids:
            checkbox = await tab.find(id=checkbox_id, raise_exc=False)
            if checkbox:
                await checkbox.click()
            else:
                print(f"{super_scraper.OOPS} checkbox '{checkbox_id}' not found")

        fields = {
            "firstName": SuperScraper.FIRST_NAME,
            "lastName": SuperScraper.LAST_NAME,
            "email": SuperScraper.EMAIL,
            "address1": SuperScraper.ADDRESS,
            "address2": SuperScraper.ADDRESS_LINE_TWO,
            "city": SuperScraper.CITY,
            "zip": SuperScraper.ZIP_CODE,
        }
        for field_id, value in fields.items():
            if not value:
                continue
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        state_select = await tab.find(id="state", raise_exc=False)
        if state_select:
            state_abbrev = SuperScraper.STATE_ABBREVIATED
            await state_select.execute_script(
                "for (var i=0;i<this.options.length;i++){"
                f"  if(this.options[i].text==={state_abbrev!r}){{ this.selectedIndex=i; }}"
                "}"
                "this.dispatchEvent(new Event('change', {bubbles:true}));"
            )

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/paramountdirectmarketing_dry_run.png")
        print(
            "\nForm filled but NOT submitted — a reCAPTCHA v2 checkbox is present and "
            "requires a manual solve before submitting."
        )


asyncio.run(main())

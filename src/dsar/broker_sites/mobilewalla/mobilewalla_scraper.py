# mobilewalla.com — the recorded URL is just a Privacy Notices page with
# links to per-right policy text and a "Personal Information Requests
# Form" link, which resolves to /global-opt-out-request — the actual form.
# Select-all-that-apply checkboxes (all `name="info-request"`, no ids,
# targeted positionally in DOM order: 0=Deletion, 1=Opt-out of sale/
# share, 2=Access/port a copy, 3=Limit sensitive PI) — ONE combined
# submission covers everything checked, unlike most other sites in this
# repo. The page itself states "regardless of my specific request... all
# requests will be treated as a request for deletion" since Mobilewalla
# can't otherwise verify identity — documented for completeness, doesn't
# change what gets checked here. Email + MAID (ADVERTISING_ID) are both
# required (no id, targeted by placeholder). Country/State are plain
# `<select>` elements. "verify-resident" radio (2 options, no ids,
# targeted positionally: 0=individual consumer, 1=agent) — "individual
# consumer" selected. reCAPTCHA v2 present — **CAPTCHA solution required**.
# Exercises Access/Port and Opt-Out unconditionally; Deletion checkbox
# gated on REMOVE_INFORMATION.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.mobilewalla.com/global-opt-out-request"

CHECKBOX_INDEXES = {"deletion": 0, "opt_out": 1, "access": 2, "limit_sensitive": 3}
RIGHT_MAP = {
    "access": ["access"],
    "opt_out_sale_share": ["opt_out"],
    "delete": ["deletion"],
}
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

        decline_cookies = await tab.find(text="Decline", raise_exc=False)
        if decline_cookies:
            await decline_cookies.click()
            await asyncio.sleep(1)

        codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
        if not codes:
            print("No requested privacy rights apply to this form — nothing to do.")
            return
        rights = [entry for code in codes for entry in RIGHT_MAP[code]]

        checkboxes = await tab.find(xpath="//input[@name='info-request']", find_all=True, raise_exc=False) or []
        for right in rights:
            idx = CHECKBOX_INDEXES[right]
            if idx < len(checkboxes):
                await checkboxes[idx].click()
            else:
                print(f"{super_scraper.OOPS} checkbox index {idx} for '{right}' not found")

        email_field = await tab.find(xpath="//input[@placeholder='Enter Email (Required)']", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)

        maid_field = await tab.find(xpath="//input[@placeholder='Enter MAID (Required)']", raise_exc=False)
        if maid_field and SuperScraper.ADVERTISING_ID:
            await maid_field.type_text(SuperScraper.ADVERTISING_ID)

        country_select = await tab.find(id="countryDropdown", raise_exc=False)
        if country_select:
            await country_select.execute_script(
                "for (var i=0;i<this.options.length;i++){"
                "  if(this.options[i].text==='United States'){ this.selectedIndex=i; }"
                "}"
                "this.dispatchEvent(new Event('change', {bubbles:true}));"
            )
            await asyncio.sleep(1)

        state_select = await tab.find(id="stateDropdown", raise_exc=False)
        if state_select:
            await state_select.execute_script(
                "for (var i=0;i<this.options.length;i++){"
                f"  if(this.options[i].text==={SuperScraper.STATE!r}){{ this.selectedIndex=i; }}"
                "}"
                "this.dispatchEvent(new Event('change', {bubbles:true}));"
            )

        resident_radios = await tab.find(xpath="//input[@name='verify-resident']", find_all=True, raise_exc=False) or []
        if resident_radios:
            await resident_radios[0].click()
        else:
            print(f"{super_scraper.OOPS} verify-resident radios not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/mobilewalla_dry_run.png")
        print(
            "\nForm filled but NOT submitted — a reCAPTCHA v2 checkbox is present and "
            "requires a manual solve before submitting."
        )


asyncio.run(main())

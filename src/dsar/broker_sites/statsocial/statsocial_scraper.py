# statsocial.com — two separate forms. The "Right to Access" form
# (statsocial.com/datarequest) is only a bare email field gated behind an
# email-verification link before any actual request details can be filled
# in (Step 2 is never reachable without reading a real inbox) — not
# automatable end-to-end, so this scraper only covers the Opt-Out/Delete
# form (statsocial.com/optout/), which is a standard Formidable Forms
# WordPress form with no email-verification step.
#
# Fields are stable HTML ids: field_optout_name_first/_last,
# field_optout_email, field_optout_country (native <select>, value="United
# States"), field_optout_state (native <select>, but starts EMPTY — its
# option list is populated by a JS listener only after Country changes, so
# Country must be set and given time to populate before State is set).
# "Preferences" checkboxes (values "delete_personal_data" /
# "optout_personal_data") require at least one checked. Cloudflare
# Turnstile — **CAPTCHA solution required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.statsocial.com/optout/"


async def _select_native_option(select_element, option_value):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].value==={option_value!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        fields = {
            "field_optout_name_first": SuperScraper.FIRST_NAME,
            "field_optout_name_last": SuperScraper.LAST_NAME,
            "field_optout_email": SuperScraper.EMAIL,
        }
        for field_id, value in fields.items():
            if not value:
                continue
            field = await tab.find(id=field_id, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        country_select = await tab.find(id="field_optout_country", raise_exc=False)
        if country_select:
            await _select_native_option(country_select, "United States")
            await asyncio.sleep(1.5)
        else:
            print(f"{super_scraper.OOPS} Country select not found")

        # State options are only populated after Country's change event fires above,
        # and their values are full state names, not abbreviations.
        state_select = await tab.find(id="field_optout_state", raise_exc=False)
        if state_select:
            await _select_native_option(state_select, SuperScraper.STATE)
        else:
            print(f"{super_scraper.OOPS} State select not found")

        preference_values = ["optout_personal_data"]
        if SuperScraper.REMOVE_INFORMATION:
            preference_values.append("delete_personal_data")
        for value in preference_values:
            checkbox = await tab.find(xpath=f"//input[@value='{value}']", raise_exc=False)
            if checkbox:
                await checkbox.click()
            else:
                print(f"{super_scraper.OOPS} preference checkbox '{value}' not found")

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/statsocial_dry_run.png")
        print("Screenshot saved to resources/screenshots/statsocial_dry_run.png")
        print(
            "\nOptout Form filled but NOT submitted — a Cloudflare Turnstile checkbox "
            "requires a manual solve before submitting. Note: statsocial.com's separate "
            "Right to Access form (datarequest) requires an email-verification link "
            "before any request details can be entered, so is not automated here."
        )


asyncio.run(main())

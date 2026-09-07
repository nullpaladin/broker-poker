# locatesmarter.com — two separate Gravity Forms (WordPress), one per URL.
# "Request to Know or Delete" form has checkboxes for "know" (access) and
# "delete" (gated on REMOVE_INFORMATION) that can both be ticked in the same
# submission — filled together in one pass. Separate "Request to Opt Out of
# Do Not Sell" form only has the self/minor/third-party toggles; "own
# personal information" (self) is used. Both forms also have minor/
# third-party sections that are skipped (this repo only ever requests on
# behalf of the account holder). Both use an invisible reCAPTCHA v2
# (size=invisible sitekey) that auto-resolves without a visible challenge —
# no manual solve needed, so DRY_RUN is respected and a real submission goes
# through when DRY_RUN is False.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

KNOW_DELETE_URL = "https://locatesmarter.com/request-to-know-or-delete-my-personal-information/"
OPT_OUT_URL = "https://locatesmarter.com/request-to-opt-out-do-not-sell-my-personal-information/"


async def _fill_common_fields(tab, name_id, email_id, street_id, city_id, state_id, zip_id, super_scraper):
    fields = {
        name_id: f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}",
        email_id: SuperScraper.EMAIL,
        street_id: SuperScraper.ADDRESS,
        city_id: SuperScraper.CITY,
        zip_id: SuperScraper.ZIP_CODE,
    }
    for field_id, value in fields.items():
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    state_select = await tab.find(id=state_id, raise_exc=False)
    if state_select:
        await state_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            f"  if(this.options[i].value==={SuperScraper.STATE!r}){{ this.selectedIndex=i; }}"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )
    else:
        print(f"{super_scraper.OOPS} State select '{state_id}' not found")


async def _check(tab, checkbox_id, super_scraper):
    checkbox = await tab.find(id=checkbox_id, raise_exc=False)
    if checkbox:
        await checkbox.click()
        await asyncio.sleep(0.3)
    else:
        print(f"{super_scraper.OOPS} checkbox '{checkbox_id}' not found")


async def _submit_or_dry_run(tab, submit_button_id, label, super_scraper):
    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/locatesmarter_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/locatesmarter_dry_run_{label}.png")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{label}' request for {SuperScraper.EMAIL}")
        return

    submit_button = await tab.find(id=submit_button_id, raise_exc=False)
    if submit_button:
        await submit_button.click()
        await asyncio.sleep(3)
        print(f"Submitted '{label}' request for {SuperScraper.EMAIL}")
    else:
        print(f"{super_scraper.OOPS} submit button '{submit_button_id}' not found")


async def submit_know_delete(tab, super_scraper):
    await tab.go_to(KNOW_DELETE_URL)
    await asyncio.sleep(4)

    await _fill_common_fields(
        tab, "input_2_2", "input_2_3", "input_2_5_1", "input_2_5_3", "input_2_5_4", "input_2_5_5", super_scraper
    )
    await _check(tab, "choice_2_14_1", super_scraper)  # own personal information
    await _check(tab, "choice_2_29_1", super_scraper)  # know for past 12 months
    await _check(tab, "choice_2_20_1", super_scraper)  # receive copy of personal information (access)
    if SuperScraper.REMOVE_INFORMATION:
        await _check(tab, "choice_2_32_1", super_scraper)  # delete personal information

    await _submit_or_dry_run(tab, "gform_submit_button_2", "know_delete", super_scraper)


async def submit_opt_out(tab, super_scraper):
    await tab.go_to(OPT_OUT_URL)
    await asyncio.sleep(4)

    await _fill_common_fields(
        tab, "input_1_2", "input_1_3", "input_1_5_1", "input_1_5_3", "input_1_5_4", "input_1_5_5", super_scraper
    )
    await _check(tab, "choice_1_14_1", super_scraper)  # stop selling my personal information

    await _submit_or_dry_run(tab, "gform_submit_button_1", "opt_out", super_scraper)


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await submit_know_delete(tab, super_scraper)
        await submit_opt_out(tab, super_scraper)


asyncio.run(main())

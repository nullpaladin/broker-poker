# choreograph.com — two separate pages under amer-cpp.choreograph.com, both
# gated by the same two react-select comboboxes: "select your country of
# residence" (class react-select-region-country__control) reveals, for
# United States, a second "select your state" combobox (class
# na-dropdown-state__control) — both are plain click-then-click-the-option
# widgets (no typing needed, full option list renders immediately). Only
# after both are set does the actual form appear.
#
# /data-points (Right to Access): after country+state, reveals First/Last/
# Email/Apartment/Address/City/Zip/Phone fields — but ALSO a required
# "upload a copy of a valid ID" file input to verify identity before
# Choreograph will return any data. There's no legitimate document to
# upload here, so this scraper fills every other field and stops there,
# leaving the ID upload + Submit for manual completion.
#
# /manage-your-data/opt-out-delete: after country+state, reveals three
# buttons — "do not sell my personal information" (id=offoptoutforsale),
# "opt out" (id=offlineoptout), "delete and opt out" (id=offlineoptoutdelete)
# — each reveals the *same* simple field set (no ID upload requirement,
# since these are device-level opt-outs, not an access request). Do Not Sell
# and Opt Out are exercised unconditionally; Delete gated on
# REMOVE_INFORMATION. reCAPTCHA is present on both pages — may require a
# manual solve in live mode.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

ACCESS_URL = "https://amer-cpp.choreograph.com/data-points"
MANAGE_URL = "https://amer-cpp.choreograph.com/manage-your-data/opt-out-delete"

DELETE_BUTTON_ID = "offlineoptoutdelete"


async def _select_country_and_state(tab, super_scraper):
    country_combo = await tab.find(
        xpath="//div[contains(@class,'react-select-region-country__control')]", raise_exc=False
    )
    if not country_combo:
        print(f"{super_scraper.OOPS} country combobox not found")
        return False
    await country_combo.click()
    await asyncio.sleep(1)
    us_option = await tab.find(
        xpath="//div[@role='option' and normalize-space(text())='United States']", raise_exc=False
    )
    if not us_option:
        print(f"{super_scraper.OOPS} 'United States' option not found")
        return False
    await us_option.click()
    await asyncio.sleep(2)

    state_combo = await tab.find(xpath="//div[contains(@class,'na-dropdown-state__control')]", raise_exc=False)
    if not state_combo:
        print(f"{super_scraper.OOPS} state combobox not found")
        return False
    await state_combo.click()
    await asyncio.sleep(1)
    state_option = await tab.find(
        xpath=f"//div[@role='option' and normalize-space(text())='{SuperScraper.STATE}']", raise_exc=False
    )
    if not state_option:
        print(f"{super_scraper.OOPS} state option '{SuperScraper.STATE}' not found")
        return False
    await state_option.click()
    await asyncio.sleep(2)
    return True


async def _fill_contact_fields(tab):
    fields = {
        "firstname": SuperScraper.FIRST_NAME,
        "lastname": SuperScraper.LAST_NAME,
        "email": SuperScraper.EMAIL,
        "address": SuperScraper.ADDRESS,
        "city": SuperScraper.CITY,
        "zipcode": SuperScraper.ZIP_CODE,
        "pnumber": "".join(c for c in SuperScraper.PHONE_NUMBER if c.isdigit()),
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)


async def submit_access(tab, super_scraper):
    await tab.go_to(ACCESS_URL)
    await asyncio.sleep(5)

    if not await _select_country_and_state(tab, super_scraper):
        return
    await _fill_contact_fields(tab)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "resources/screenshots/choreograph_dry_run_access.png")
    print(
        "\nAccess request form filled but a valid government ID upload is required to "
        "verify identity before this can be submitted — there is no legitimate document "
        "for this scraper to provide, so uploading the ID and clicking Submit must be done "
        "manually."
    )


async def submit_manage(tab, button_id, label, super_scraper):
    await tab.go_to(MANAGE_URL)
    await asyncio.sleep(5)

    if not await _select_country_and_state(tab, super_scraper):
        return

    btn = await tab.find(id=button_id, raise_exc=False)
    if not btn:
        print(f"{super_scraper.OOPS} '{label}' button not found")
        return
    await btn.click()
    await asyncio.sleep(2)

    await _fill_contact_fields(tab)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/choreograph_dry_run_{button_id}.png")
        return

    print(f"\n'{label}' form filled. Solve the reCAPTCHA if prompted, click Submit,")
    print("then press Enter once the confirmation appears...")
    input()
    print(f"Submitted '{label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await submit_access(tab, super_scraper)
        await submit_manage(tab, "offoptoutforsale", "do not sell my personal information", super_scraper)
        await submit_manage(tab, "offlineoptout", "opt out", super_scraper)
        if SuperScraper.wants("delete"):
            await submit_manage(tab, DELETE_BUTTON_ID, "delete and opt out", super_scraper)


asyncio.run(main())

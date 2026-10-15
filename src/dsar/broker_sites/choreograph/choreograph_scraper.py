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
# and Opt Out map to Opt-out; "delete and opt out" maps to Delete. Which rights
# run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). reCAPTCHA is
# present on both pages — may require a manual solve in live mode.
#
# Page elements:
#   .react-select-region-country__control   "select your country of residence" combobox
#   .na-dropdown-state__control             "select your state" combobox
#   #firstname / #lastname                  First / Last name
#   #email                                  Email
#   #address / #city / #zipcode             Address / City / ZIP
#   #pnumber                                Phone (digits only)
#   #offoptoutforsale                       "do not sell my personal information" button
#   #offlineoptout                          "opt out" button
#   #offlineoptoutdelete                    "delete and opt out" button
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

ACCESS_URL = "https://amer-cpp.choreograph.com/data-points"
MANAGE_URL = "https://amer-cpp.choreograph.com/manage-your-data/opt-out-delete"

# Right -> entries. ACCESS is the /data-points page (filled, never submitted — it needs an ID
# upload); the others are (button id, button label) on the manage page.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [ACCESS_URL],
    Right.RIGHT_TO_OPT_OUT: [
        ("offoptoutforsale", "do not sell my personal information"),
        ("offlineoptout", "opt out"),
    ],
    Right.RIGHT_TO_DELETE: [("offlineoptoutdelete", "delete and opt out")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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
    await SuperScraper.screenshot(tab, "dry_run_access")
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
        await SuperScraper.screenshot(tab, f"dry_run_{button_id}")
        return

    print(f"\n'{label}' form filled. Solve the reCAPTCHA if prompted, click Submit,")
    print("then press Enter once the confirmation appears...")
    input()
    print(f"Submitted '{label}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            if right is Right.RIGHT_TO_ACCESS:
                await submit_access(tab, super_scraper)
                continue
            for button_id, label in RIGHT_MAP[right]:
                await submit_manage(tab, button_id, label, super_scraper)


asyncio.run(main())

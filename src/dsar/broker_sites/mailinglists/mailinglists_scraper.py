# mailinglists.com — HubSpot form (share-na2.hsforms.com). The page itself
# states Access/Correct aren't applicable ("Mailinglists.com is a data
# reseller and does not store or control consumer personal data") — only
# Opt-Out and Delete are offered, as a single-select
# `consumer_privacy_request_type` radio (index 0 = Do Not Sell or Share,
# index 1 = Delete) — one submission per right. Field ids are long random
# hashes with no stable pattern, but `name` attributes are stable/semantic
# (e.g. "0-1/firstname") — targeted by `name` via xpath. A required
# confirmation checkbox and reCAPTCHA v2 (standard hs-recaptcha-response
# hidden-field pattern, same as other HubSpot forms elsewhere in this
# repo) are present. Exercises Opt-Out unconditionally; Delete gated on
# REMOVE_INFORMATION.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://41b1vr.share-na2.hsforms.com/2mF48cI-GSjaSTP9FG8gkjA"

OPT_OUT_INDEX = 0
DELETE_INDEX = 1

RIGHT_MAP = {
    "opt_out_sale_share": [(OPT_OUT_INDEX, "opt_out")],
    "delete": [(DELETE_INDEX, "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, radio_index, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    fields = {
        "0-1/firstname": SuperScraper.FIRST_NAME,
        "0-1/lastname": SuperScraper.LAST_NAME,
        "0-1/email": SuperScraper.EMAIL,
        "0-1/address": SuperScraper.ADDRESS,
        "0-1/city": SuperScraper.CITY,
        "0-1/state": SuperScraper.STATE,
        "0-1/country": "United States",
    }
    for field_name, value in fields.items():
        if not value:
            continue
        field = await tab.find(xpath=f"//input[@name='{field_name}']", raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_name}' not found")

    radios = await tab.find(
        xpath="//input[@name='0-1/consumer_privacy_request_type']", find_all=True, raise_exc=False
    )
    if radios and len(radios) > radio_index:
        await radios[radio_index].click()
    else:
        print(f"{super_scraper.OOPS} request-type radio index {radio_index} not found")

    confirm = await tab.find(
        xpath="//input[@name='0-1/consumer_privacy_request_confirmation']", raise_exc=False
    )
    if confirm:
        await confirm.click()

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/mailinglists_dry_run_{label}.png")
    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{label}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        return

    submit_btn = await tab.find(text="Submit", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{label}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Submit button not found for '{label}'")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for radio_index, label in requests:
            await submit_request(tab, radio_index, label, super_scraper)


asyncio.run(main())

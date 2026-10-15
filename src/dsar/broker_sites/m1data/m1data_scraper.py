# m1data.com — m1-data.com/unsubscribe/. Plain server-rendered form,
# single-select "Please Select Request Type" radios: RequestType1=Request
# to Know (Access), RequestType2=Request to Delete, RequestType3=Do Not
# Sell My Information (Opt-Out) — one submission per right. State is plain
# free text, not a select. A `name="website"` field (no id) has
# `getBoundingClientRect().height === 0` — a honeypot despite the generic
# label, deliberately left BLANK (same pattern as leadloft.com/lsmapps.com
# elsewhere in this repo). reCAPTCHA v2 present via standard hidden
# g-recaptcha-response field. Exercises Access and Opt-Out unconditionally;
# Delete gated on REMOVE_INFORMATION.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://m1-data.com/unsubscribe/"

# Opaque RequestTypeN values — verify against the live form.
RIGHT_MAP = {
    "access": ["RequestType1"],
    "opt_out_sale_share": ["RequestType3"],
    "delete": ["RequestType2"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

LABELS = {
    "RequestType1": "know",
    "RequestType2": "delete",
    "RequestType3": "do_not_sell",
}


async def submit_request(tab, request_type_id, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    fields = {
        "FName": SuperScraper.FIRST_NAME,
        "LName": SuperScraper.LAST_NAME,
        "Address": SuperScraper.ADDRESS,
        "Apartment": SuperScraper.ADDRESS_LINE_TWO,
        "City": SuperScraper.CITY,
        "State": SuperScraper.STATE,
        "Zip": SuperScraper.ZIP_CODE,
        "EmailId": SuperScraper.EMAIL,
        "Phone": SuperScraper.PHONE_NUMBER,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    radio = await tab.find(id=request_type_id, raise_exc=False)
    if radio:
        await radio.click()
    else:
        print(f"{super_scraper.OOPS} radio '{request_type_id}' not found")

    label = LABELS[request_type_id]

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/m1data_dry_run_{label}.png")
    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{label}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        return

    submit_btn = await tab.find(text="SUBMIT UNSUBSCRIBE", raise_exc=False)
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
    request_types = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type_id in request_types:
            await submit_request(tab, request_type_id, super_scraper)


asyncio.run(main())

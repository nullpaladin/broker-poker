# m1data.com — m1-data.com/unsubscribe/. Plain server-rendered form,
# single-select "Please Select Request Type" radios: RequestType1=Request
# to Know (Access), RequestType2=Request to Delete, RequestType3=Do Not
# Sell My Information (Opt-Out) — one submission per right. State is plain
# free text, not a select. A `name="website"` field (no id) has
# `getBoundingClientRect().height === 0` — a honeypot despite the generic
# label, deliberately left BLANK (same pattern as leadloft.com/lsmapps.com
# elsewhere in this repo). reCAPTCHA v2 present via standard hidden
# g-recaptcha-response field. Which rights run is decided only by
# rights_to_exercise(RIGHT_MAP).
#
# Page elements:
#   #FName / #LName      First / Last name
#   #Address / #Apartment / #City / #State / #Zip   Address / Apartment / City / State (free text) / ZIP
#   #EmailId / #Phone    Email / Phone
#   #RequestType1        "Request to Know" radio
#   #RequestType2        "Request to Delete" radio
#   #RequestType3        "Do Not Sell My Information" radio
#   "SUBMIT UNSUBSCRIBE" button (found by text)
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://m1-data.com/unsubscribe/"

# Opaque RequestTypeN values — verify against the live form.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "RequestType1",
    Right.RIGHT_TO_OPT_OUT: "RequestType3",
    Right.RIGHT_TO_DELETE: "RequestType2",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every request-type radio, as displayed -> the Right it maps to.
PAGE_RIGHTS = {
    "Request to Know": Right.RIGHT_TO_ACCESS,
    "Request to Delete": Right.RIGHT_TO_DELETE,
    "Do Not Sell My Information": Right.RIGHT_TO_OPT_OUT,
}
RIGHTS_OPTIONS_CSS = (
    "label:has(#RequestType1), label:has(#RequestType2), label:has(#RequestType3), "
    "label[for='RequestType1'], label[for='RequestType2'], label[for='RequestType3']"
)  # built from the three recorded radio ids

FIELD_XPATHS = {
    "First name": "//*[@id='FName']",
    "Last name": "//*[@id='LName']",
    "Address": "//*[@id='Address']",
    "City": "//*[@id='City']",
    "State": "//*[@id='State']",
    "Zip": "//*[@id='Zip']",
    "Email": "//*[@id='EmailId']",
}

LABELS = {
    "RequestType1": "know",
    "RequestType2": "delete",
    "RequestType3": "do_not_sell",
}


async def submit_request(tab, request_type_id, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

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

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{label}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        return

    submit_btn = await tab.find(text="SUBMIT UNSUBSCRIBE", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{label}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} — confirm in the browser.")
    else:
        print(f"{super_scraper.OOPS} Submit button not found for '{label}'")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, RIGHT_MAP[right], super_scraper)


asyncio.run(main())

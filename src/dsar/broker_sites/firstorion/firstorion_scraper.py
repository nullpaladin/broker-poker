# firstorion.com — no privacy-request URL exists on the main site at all;
# the actual portal is linked only from the footer of an otherwise-unrelated
# 404 page ("Do Not Sell My Info" -> https://privacy.firstorion.com/).
# "GET STARTED ONLINE" leads to a single-page form: First/Last/Email/Phone
# Number (the phone number being opted out — First Orion sells phone/name/
# address/carrier/line-type data, so this *is* the identifying record, not
# just a contact method), "What right do you want to exercise?" (single-
# select radio: "opt-out" bundles opt-out-of-sale with deletion — no way to
# separate them, so both RIGHT_TO_OPT_OUT and RIGHT_TO_DELETE map to it; "data" is
# Access), and a required attestation checkbox. The submit button
# is literally labeled "Send Confirmation" — clicking it sends a real
# verification email/SMS/call to the phone number and address provided, so
# this scraper fills the form and stops there regardless of DRY_RUN.
#
# Page elements:
#   "GET STARTED ONLINE" button
#   #firstName / #lastName / #email / #phone   First / Last name / Email / Phone Number
#   input[name=opt-out] radios                 "What right do you want to exercise?" (values below)
#   input[type=checkbox]                       required attestation checkbox
#   "Send Confirmation" button                 never clicked (sends a real verification message)
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://privacy.firstorion.com/"

DATA_RADIO = "data"        # Access
OPT_OUT_RADIO = "opt-out"  # bundled opt-out of sale + deletion

# "opt-out" is a bundled opt-out + delete request on this form.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [DATA_RADIO],
    Right.RIGHT_TO_OPT_OUT: [OPT_OUT_RADIO],
    Right.RIGHT_TO_DELETE: [OPT_OUT_RADIO],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    start_btn = await tab.find(text="GET STARTED ONLINE", raise_exc=False)
    if not start_btn:
        print(f"{super_scraper.OOPS} 'GET STARTED ONLINE' button not found")
        return
    await start_btn.click()
    await asyncio.sleep(3)

    fields = {
        "firstName": SuperScraper.FIRST_NAME,
        "lastName": SuperScraper.LAST_NAME,
        "email": SuperScraper.EMAIL,
        "phone": SuperScraper.PHONE_NUMBER,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)

    radio = await tab.find(xpath=f"//input[@name='opt-out' and @value='{request_type}']", raise_exc=False)
    if radio:
        await radio.click()

    checkbox = await tab.find(xpath="//input[@type='checkbox']", raise_exc=False)
    if checkbox:
        await checkbox.click()

    label = request_type.replace("-", "_")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(
        f"\n'{request_type}' request filled but NOT sent — click 'Send Confirmation' yourself, "
        "complete the phone/email verification, and confirm the request. This sends a real "
        "verification message regardless of DRY_RUN, so it is never done automatically."
    )


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    request_types = list(dict.fromkeys(rt for r in rights for rt in RIGHT_MAP[r]))

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type in request_types:
            await submit_request(tab, request_type, super_scraper)


asyncio.run(main())

# tunnldata.com — Ethyca/Fides privacy portal.
# Two cards: "Access your data" (access) and "Delete your data and Opt Out of Data Sale"
# (one combined card; mapped to delete only, since it is destructive). Which run is decided
# ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Correct is email-only (privacy_correction@tunnldata.com) — not automated.
# Fields: email, first_name, last_name, addr1, city, state (text), zip; phone optional.
# Phone ID: phone_num (Access), phone (Delete).
# After clicking Continue: email verification code sent → id="code" → "Submit code" button.
# No CAPTCHA.
#
# Page elements:
#   card "Access your data" / card "Delete your data and Opt Out of Data Sale"   request-type cards
#   #email / #first_name / #last_name   Email, First / Last name
#   #addr1 / #city / #state / #zip      Address, City, State (text), Zip
#   #phone_num (Access card) / #phone (Delete card)   Phone (optional)
#   "Continue" button                   submits the form
#   #code + "Submit code" button        emailed verification code step
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacy.tunnldata.com/"

# Right -> (card text, phone field id on that card).
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ("Access your data", "phone_num"),
    Right.RIGHT_TO_DELETE: ("Delete your data and Opt Out of Data Sale", "phone"),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Landing-page cards, as displayed -> the Right they map to. No running path (NOT_AUTOMATABLE); the card
# selector has not been captured yet.
PAGE_RIGHTS = {
    "Access your data": Right.RIGHT_TO_ACCESS,
    "Delete your data and Opt Out of Data Sale": Right.RIGHT_TO_DELETE,
}
RIGHTS_OPTIONS_CSS = ""  # TODO(health-check): capture the card-title selector on a live run

NOT_AUTOMATABLE = True
NOT_AUTOMATABLE_REASON = (
    "the form emails a verification code that must be entered mid-run to proceed"
)


async def _fill_form(tab, phone_field_id="phone_num"):
    for fid, val in [
        ("email", SuperScraper.EMAIL),
        ("first_name", SuperScraper.FIRST_NAME),
        ("last_name", SuperScraper.LAST_NAME),
        ("addr1", SuperScraper.ADDRESS),
        ("city", SuperScraper.CITY),
        ("state", SuperScraper.STATE),
        ("zip", SuperScraper.ZIP_CODE),
    ]:
        field = await tab.find(id=fid, raise_exc=False)
        if field:
            await field.type_text(val)
    phone = await tab.find(id=phone_field_id, raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)


async def _submit_request(tab, right, entry, super_scraper):
    card_text, phone_field_id = entry
    await tab.go_to(URL)
    await asyncio.sleep(6)

    cards = await tab.find(text=card_text, find_all=True, raise_exc=False) or []
    for card in cards:
        if await card.is_visible():
            await card.click()
            await asyncio.sleep(3)
            break
    else:
        print(f"{super_scraper.OOPS} Card '{card_text}' not found")
        return

    await _fill_form(tab, phone_field_id)
    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        continue_btn = await tab.find(text="Continue", raise_exc=False)
        if continue_btn and await continue_btn.is_visible():
            await continue_btn.scroll_into_view()
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        return

    continue_btn = await tab.find(text="Continue", raise_exc=False)
    if continue_btn and await continue_btn.is_visible():
        await continue_btn.click()
        await asyncio.sleep(5)

    print(f"\nForm submitted for {right.name}.")
    print("Check your email for a verification code, then enter it here.")
    code = input("Verification code: ").strip()

    code_field = await tab.find(id="code", raise_exc=False)
    if code_field:
        await code_field.type_text(code)
        await asyncio.sleep(0.5)

    submit_code_btn = await tab.find(text="Submit code", raise_exc=False)
    if submit_code_btn and await submit_code_btn.is_visible():
        await submit_code_btn.click()
        await asyncio.sleep(4)

    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await _submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())

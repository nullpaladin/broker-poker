# deeprootanalytics.com — Ethyca/Fides privacy portal.
# Three cards on landing page: "Access your data", "Delete your data", "Opt out of data sales and sharing".
# Opt-out card shows "Consent management is unavailable in your area." — skipped.
# Rights the form exposes (and we map): access, delete. Which run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
# After clicking Continue: email verification code sent to inbox; the user must enter it
# mid-run, hence NOT_AUTOMATABLE. No CAPTCHA.
#
# Page elements:
#   "Access your data" / "Delete your data" cards    Landing-page cards (see RIGHT_MAP)
#   #email / #first_name / #last_name                Email / First / Last name (required)
#   #addr1 / #city / #state (text) / #zip            Address (required)
#   #phone_num (Access) / #phone (Delete)            Phone (optional)
#   "Continue" button                                Sends the verification code
#   #code + "Submit code" button                     Email verification code
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacy.deeprootanalytics.com/"

# Right -> (landing-page card text, phone field id on that form)
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ("Access your data", "phone_num"),
    Right.RIGHT_TO_DELETE: ("Delete your data", "phone"),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Landing-page cards, as displayed -> the Right they map to (None = not automated). No running path
# (NOT_AUTOMATABLE); the card selector has not been captured yet.
PAGE_RIGHTS = {
    "Access your data": Right.RIGHT_TO_ACCESS,
    "Delete your data": Right.RIGHT_TO_DELETE,
    "Opt out of data sales and sharing": None,
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

    await _fill_form(tab, phone_field_id)
    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        continue_btn = await tab.find(text="Continue", raise_exc=False)
        if continue_btn and await continue_btn.is_visible():
            await continue_btn.scroll_into_view()
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
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

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await _submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())

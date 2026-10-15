# matchbookdata.com — /your-privacy-choices/. Matchbook Data identifies
# consumers only by mobile Device ID (Advertising ID or Installation ID),
# not by name/address — the entire form is just two fields.
# Rights the form exposes: the surrounding page text describes opt-out, deletion
# and limit-sensitive-PI, but there is no separate control for them — every
# request goes through this same single Device-ID-based form, so it is ONE
# submission whenever any mapped right is selected. Which rights apply is decided
# ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). No access / list-of-third-
# parties option exists. No CAPTCHA observed.
#
# Page elements (keep this list current):
#   #CybotCookiebotDialogBodyButtonDecline   Cookiebot banner "Decline" button (banner covers page on first load)
#   #form-field-device_ID      Device ID (Advertising ID / Installation ID)   (form_fields[device_ID])
#   #form-field-email          Email                                          (form_fields[email])
#   "Submit" button            found by its text
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.matchbookdata.com/your-privacy-choices/"

COOKIE_DECLINE_ID = "CybotCookiebotDialogBodyButtonDecline"  # Cookiebot "Decline"
DEVICE_ID_FIELD = "form-field-device_ID"  # Device ID
EMAIL_FIELD = "form-field-email"  # Email
SUBMIT_TEXT = "Submit"  # Submit button

# One form covers every right (see header) — the entry is just a label.
RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: "device ID form",
    Right.RIGHT_TO_DELETE: "device ID form",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    names = "/".join(right.name for right in rights)

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        deny_btn = await tab.find(id=COOKIE_DECLINE_ID, raise_exc=False)
        if deny_btn:
            await deny_btn.click()
            await asyncio.sleep(1)

        device_id_field = await tab.find(id=DEVICE_ID_FIELD, raise_exc=False)
        if device_id_field and SuperScraper.ADVERTISING_ID:
            await device_id_field.type_text(SuperScraper.ADVERTISING_ID)
        else:
            print(f"{super_scraper.OOPS} device_ID field not found or ADVERTISING_ID not set")

        email_field = await tab.find(id=EMAIL_FIELD, raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit '{names}' for {SuperScraper.EMAIL} (device ID: {SuperScraper.ADVERTISING_ID})")
            return

        submit_btn = await tab.find(text=SUBMIT_TEXT, raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(2)
            print(f"Submitted '{names}' for {SuperScraper.EMAIL} — confirm in the browser.")
        else:
            print(f"{super_scraper.OOPS} Submit button not found")


asyncio.run(main())

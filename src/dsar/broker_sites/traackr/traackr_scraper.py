# traackr.com — /data-opt-out embeds a Formsite form via an iframe with a
# real, populated `src` (reachable via `tab.get_frame()`, same technique as
# realsourcedata.com's Tally.so embed elsewhere in this repo). "Type of data
# request" is a native single-select (Access/Deletion/Rectification) — one
# submission per right: Access unconditionally, Deletion gated on
# REMOVE_INFORMATION; Rectification skipped (no concrete inaccuracy). No
# CAPTCHA. The form requires "at least one Twitter, Instagram, or Facebook
# Handle/URL" to validate identity — Traackr identifies people by social media
# presence, not name/email alone. This is now filled from .env
# (TWITTER_URL / INSTAGRAM_URL / FACEBOOK_URL, first available); if none are set
# the field is left blank and the form will likely reject the submission.
# The social field id (SOCIAL_FIELD_ID) is a best guess — verify on a live run.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.traackr.com/data-opt-out"

# Canonical right code -> ("Type of data request" native-select value, screenshot label).
# Rectification is skipped (no concrete inaccuracy to describe).
RIGHT_MAP = {
    "access": ("Radio-0", "access"),
    "delete": ("Radio-1", "delete"),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Best-guess Formsite id for the social handle/URL field (after name/email/confirm).
SOCIAL_FIELD_ID = "RESULT_TextField-4"


async def submit_request(tab, request_type_value, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    iframe_element = await tab.find(tag_name="iframe", raise_exc=False)
    if not iframe_element:
        print(f"{super_scraper.OOPS} Formsite iframe not found")
        return
    frame = await tab.get_frame(iframe_element)
    await asyncio.sleep(2)

    request_type_select = await frame.find(id="RESULT_RadioButton-0", raise_exc=False)
    if request_type_select:
        await SuperScraper.select_native_option(request_type_select, value=request_type_value)
    else:
        print(f"{super_scraper.OOPS} Request type select not found")

    fields = {
        "RESULT_TextField-1": SuperScraper.FIRST_NAME,
        "RESULT_TextField-2": SuperScraper.LAST_NAME,
        "RESULT_TextField-3": SuperScraper.EMAIL,
        "CONFIRM_TextField-3": SuperScraper.EMAIL,
    }
    for field_id, value in fields.items():
        field = await frame.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    socials = SuperScraper.social_urls()
    social_url = socials.get("twitter") or socials.get("instagram") or socials.get("facebook")
    if social_url:
        social_field = await frame.find(id=SOCIAL_FIELD_ID, raise_exc=False)
        if social_field:
            await social_field.type_text(social_url)
        else:
            print(f"{super_scraper.OOPS} social handle field '{SOCIAL_FIELD_ID}' not found (verify id)")
    else:
        print(
            f"{super_scraper.OOPS} no TWITTER_URL / INSTAGRAM_URL / FACEBOOK_URL set in .env — "
            "Traackr requires one to validate identity, so submission will likely be rejected."
        )

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/traackr_dry_run_{label}.png")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would attempt to submit '{label}' request for {SuperScraper.EMAIL}")
        return

    submit_button = await frame.find(id="FSsubmit", raise_exc=False)
    if submit_button:
        await submit_button.click()
        await asyncio.sleep(3)
        print(f"Attempted to submit '{label}' request for {SuperScraper.EMAIL}")
    else:
        print(f"{super_scraper.OOPS} submit button not found")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for code in codes:
            request_type_value, label = RIGHT_MAP[code]
            await submit_request(tab, request_type_value, label, super_scraper)


asyncio.run(main())

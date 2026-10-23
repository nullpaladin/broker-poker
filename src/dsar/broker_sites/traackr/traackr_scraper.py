# traackr.com — /data-opt-out embeds a Formsite form via an iframe with a
# real, populated `src` (reachable via `tab.get_frame()`, same technique as
# realsourcedata.com's Tally.so embed elsewhere in this repo). "Type of data
# request" is a native single-select (Access/Deletion/Rectification) — one
# submission per right (access, delete); which run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). Rectification skipped (no concrete
# inaccuracy). No CAPTCHA. The form requires "at least one Twitter, Instagram, or Facebook
# Handle/URL" to validate identity — Traackr identifies people by social media
# presence, not name/email alone. This is now filled from .env
# (TWITTER_URL / INSTAGRAM_URL / FACEBOOK_URL, first available); if none are set
# the field is left blank and the form will likely reject the submission.
# The social field id (SOCIAL_FIELD_ID) is a best guess — verify on a live run.
#
# Page elements (inside the Formsite iframe):
#   #RESULT_RadioButton-0     "Type of data request" <select> (Radio-0 = Access, Radio-1 = Deletion)
#   #RESULT_TextField-1       First name
#   #RESULT_TextField-2       Last name
#   #RESULT_TextField-3 / #CONFIRM_TextField-3   Email / confirm email
#   #RESULT_TextField-4       Twitter / Instagram / Facebook handle or URL (id unverified, see above)
#   #FSsubmit                 Submit button
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.traackr.com/data-opt-out"

# Right -> "Type of data request" native-select value.
# Rectification is skipped (no concrete inaccuracy to describe).
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Radio-0",
    Right.RIGHT_TO_DELETE: "Radio-1",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The request-type <select> lives inside the Formsite iframe, which read_option_labels cannot read.)

FRAME_FIELD_XPATHS = {
    "Request type": "//*[@id='RESULT_RadioButton-0']",
    "First name": "//*[@id='RESULT_TextField-1']",
    "Last name": "//*[@id='RESULT_TextField-2']",
    "Email": "//*[@id='RESULT_TextField-3']",
    "Confirm email": "//*[@id='CONFIRM_TextField-3']",
}

# Best-guess Formsite id for the social handle/URL field (after name/email/confirm).
SOCIAL_FIELD_ID = "RESULT_TextField-4"


async def submit_request(tab, right, request_type_value, super_scraper):
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
        await js_utils.select_native_option(request_type_select, value=request_type_value)
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

    if SuperScraper.HEALTH_CHECK:
        # `frame` stands in for `tab`: its find() resolves into the Formsite iframe's document.
        await SuperScraper.assert_fields_filled(frame, FRAME_FIELD_XPATHS)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        return

    submit_button = await frame.find(id="FSsubmit", raise_exc=False)
    if submit_button:
        await submit_button.click()
        await asyncio.sleep(3)
        print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")
    else:
        print(f"{super_scraper.OOPS} submit button not found")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())

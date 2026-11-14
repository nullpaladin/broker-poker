# fourthwall.tv — "Do Not Sell or Share" opt-out form (Wix form) at
# fourthwall.tv/donotsellorshare-fourthwall.
# Right to Opt-Out ONLY — the site offers no Access/Delete/Correct mechanism
# even though its privacy policy says those rights exist (privacypolicy@
# fourthwall.tv never responded; a complaint may be the only escalation).
# Server-rendered; field `name` attributes contain spaces/slashes so are matched
# verbatim: first-name, last-name, email, phone, street-address,
# "street-address line 2", city, "region/state/province", "postal-/ zip code".
# The optional "Country" field is a Wix dropdown component (not a native
# <select>) and is left blank — it has no required marker. reCAPTCHA v2 gates
# submission — the form is filled and left for a manual solve.
# **CAPTCHA solution required**
#
# Page elements (inputs by name): first-name / last-name / email / phone / street-address /
#   city / region/state/province / postal-/ zip code; reCAPTCHA v2 checkbox, Submit button.
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.fourthwall.tv/donotsellorshare-fourthwall"

RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "opt-out"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIELDS = [
    ("first-name", "FIRST_NAME"),
    ("last-name", "LAST_NAME"),
    ("email", "EMAIL"),
    ("phone", "PHONE_NUMBER"),
    ("street-address", "ADDRESS"),
    ("city", "CITY"),
    ("region/state/province", "STATE"),
    ("postal-/ zip code", "ZIP_CODE"),
]


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        for name, attr in FIELDS:
            value = getattr(SuperScraper, attr, None)
            if not value:
                continue
            # first matching input — the opt-out form is the first form on the page
            field = await tab.find(xpath=f"(//input[@name={name!r}])[1]", timeout=5, raise_exc=False)
            if field:
                await field.type_text(value)
                await asyncio.sleep(0.2)
            else:
                print(f"{super_scraper.OOPS} field '{name}' not found")

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, {
                name: f"(//input[@name={name!r}])[1]"
                for name, _attr in FIELDS
                if name != "phone"  # optional
            })

        time.sleep(0.5)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            "Opt-out request filled but NOT submitted — a reCAPTCHA v2 checkbox "
            "must be solved manually before submitting."
        )

        if not SuperScraper.DRY_RUN:
            print("Solve the reCAPTCHA, click Submit, then press Enter once confirmed...")
            input()
            print(f"Submitted opt-out for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())

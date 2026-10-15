# civicelement.com — exercises Right to Access, Right to Opt-Out (sales/sharing),
# Right to Opt-Out (sensitive data), and Right to Delete. Which of them run is decided
# ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Single Webflow GET form with no captcha; submit once per request type.
# First/last name both use name="name" in HTML; phone/email both use name="email" —
# target by class (.text-field-7/.text-field-8 and .text-field-6/.text-field-5).
# Phone is required by the form.
#
# Page elements:
#   .text-field-7 / .text-field-8   First / Last name
#   #State-or-Province              State or province
#   .text-field-6                   Phone (required)
#   .text-field-5                   Email
#   #Request-Types                  Request type (see RIGHT_MAP)
#   .light-button-cta               Submit button
import asyncio
import json

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.civicelement.com/privacy-policy-request"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Request a copy of personal information", "access")],
    Right.RIGHT_TO_OPT_OUT: [
        ("Opt-out of sales and/or sharing of personal information", "opt_out_sales_sharing"),
        ("Opt-Out of Sensitive Information Processing", "opt_out_sensitive"),
    ],
    Right.RIGHT_TO_DELETE: [("Request data deletion", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


def _js_set(selector, value):
    sel = json.dumps(selector)
    val = json.dumps(str(value))
    return (
        f"(function(){{"
        f"var el=document.querySelector({sel});"
        f"if(!el)return;"
        f"el.value={val};"
        f"el.dispatchEvent(new Event('input',{{bubbles:true}}));"
        f"el.dispatchEvent(new Event('change',{{bubbles:true}}));"
        f"}})();"
    )


async def submit_request(tab, right, request_type, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    if not SuperScraper.PHONE_NUMBER:
        print(f"{super_scraper.OOPS} PHONE_NUMBER not set — civicelement requires phone; skipping '{request_type}'")
        return

    await tab.execute_script(_js_set(".text-field-7", SuperScraper.FIRST_NAME))
    await tab.execute_script(_js_set(".text-field-8", SuperScraper.LAST_NAME))
    await tab.execute_script(_js_set("#State-or-Province", SuperScraper.STATE))
    await tab.execute_script(_js_set(".text-field-6", SuperScraper.PHONE_NUMBER))
    await tab.execute_script(_js_set(".text-field-5", SuperScraper.EMAIL))
    await tab.execute_script(_js_set("#Request-Types", request_type))

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' ({request_type}) for {SuperScraper.EMAIL}"
        )
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    await tab.execute_script("document.querySelector('.light-button-cta').click();")
    await asyncio.sleep(4)

    print(f"Submitted '{right.name}' ({request_type}) for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for request_type, label in RIGHT_MAP[right]:
                await submit_request(tab, right, request_type, label, super_scraper)


asyncio.run(main())

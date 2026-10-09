# civicelement.com — exercises Right to Access, Right to Opt-Out (sales/sharing),
# Right to Opt-Out (sensitive data), and Right to Delete (gated on REMOVE_INFORMATION).
# Single Webflow GET form with no captcha; submit once per request type.
# First/last name both use name="name" in HTML; phone/email both use name="email" —
# target by class (.text-field-7/.text-field-8 and .text-field-6/.text-field-5).
# Phone is required by the form.
import asyncio
import json

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.civicelement.com/privacy-policy-request"

RIGHT_MAP = {
    "access": [("Request a copy of personal information", "access")],
    "opt_out_sale_share": [("Opt-out of sales and/or sharing of personal information", "optout")],
    "limit_sensitive_pi": [("Opt-Out of Sensitive Information Processing", "optout_sensitive")],
    "delete": [("Request data deletion", "delete")],
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


async def submit_request(tab, request_type, label, super_scraper):
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
            f"DRY RUN: would submit '{request_type}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"resources/screenshots/civicelement_dry_run_{label}.png")
        return

    await tab.execute_script("document.querySelector('.light-button-cta').click();")
    await asyncio.sleep(4)

    result = await SuperScraper.page_text(tab) or ""
    if any(word in result.lower() for word in ("thank", "success", "received", "submitted")):
        print(f"Submitted '{request_type}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{request_type}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type, label in requests:
            await submit_request(tab, request_type, label, super_scraper)


asyncio.run(main())

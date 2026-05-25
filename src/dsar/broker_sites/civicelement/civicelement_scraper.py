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

REQUESTS = [
    ("Request a copy of personal information", "access"),
    ("Opt-out of sales and/or sharing of personal information", "optout"),
    ("Opt-Out of Sensitive Information Processing", "optout_sensitive"),
]
DELETE_REQUEST = ("Request data deletion", "delete")


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
        await tab.take_screenshot(f"resources/screenshots/civicelement_dry_run_{label}.png")
        print(f"Screenshot saved to resources/screenshots/civicelement_dry_run_{label}.png")
        return

    await tab.execute_script("document.querySelector('.light-button-cta').click();")
    await asyncio.sleep(4)

    result = await tab.execute_script("return document.body.innerText") or ""
    if any(word in result.lower() for word in ("thank", "success", "received", "submitted")):
        print(f"Submitted '{request_type}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{request_type}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type, label in requests:
            await submit_request(tab, request_type, label, super_scraper)


asyncio.run(main())

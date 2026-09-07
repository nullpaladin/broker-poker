# inboundinsight.com — Trust Superset DSR platform
# Request Type is a single-select dropdown (one submission per
# right): Right to Rectification (Correct), Right to Restrict Processing,
# Right to Data Portability, Right to Not be Subject to Automated
# Decision-Making, Right to Opt-out of Sales, Right to Limit Sensitive
# Personal Information unconditionally; Right to Erasure (Delete) gated on
# REMOVE_INFORMATION. No dedicated "Access" option is offered by this form.
# Cloudflare Turnstile ("Please verify you're human") requires manual solve
# in live mode. Selecting Rectification reveals an additional required
# "Information to Rectify" textarea (name="rectification_info") — no other
# right adds a conditional field.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://dsr.trustsuperset.com/?orgId=2183d64e-c307-4322-938f-5711d839719e"

RIGHTS = [
    "Right to Rectification",
    "Right to Restrict Processing",
    "Right to Data Portability",
    "Right to Not be Subject to Automated Decision-Making",
    "Right to Opt-out of Sales",
    "Right to Limit Sensitive Personal Information",
]
DELETE_RIGHT = "Right to Erasure"


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    request_type = await tab.find(text="Select request type", raise_exc=False)
    if request_type:
        await request_type.click()
        await asyncio.sleep(1)
        option = await tab.find(text=right, raise_exc=False)
        if option:
            await option.click()
    await asyncio.sleep(1)

    if right == "Right to Rectification":
        rectify_field = await tab.find(name="rectification_info", raise_exc=False)
        if rectify_field:
            await rectify_field.type_text(
                "Please correct any inaccurate personal information you hold about me "
                "to match the details provided in this request."
            )

    for name, value in [
        ("first_name", SuperScraper.FIRST_NAME),
        ("last_name", SuperScraper.LAST_NAME),
        ("email", SuperScraper.EMAIL),
        ("phone", SuperScraper.PHONE_NUMBER),
        ("country", "United States"),
        ("address_1", SuperScraper.ADDRESS),
        ("city", SuperScraper.CITY),
        ("region", SuperScraper.STATE),
        ("zip_code", SuperScraper.ZIP_CODE),
    ]:
        field = await tab.find(name=name, raise_exc=False)
        if field:
            await field.type_text(value)
            await asyncio.sleep(0.2)

    label = right.lower().replace(" ", "_")

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/inboundinsight_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{right}'. Solve the Cloudflare Turnstile challenge,")
    print("click Submit Request, then press Enter once the confirmation appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{right}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{right}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, super_scraper)


asyncio.run(main())

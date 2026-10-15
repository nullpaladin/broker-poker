# datadelivers.com — Trust Superset DSR platform
# Request Type is a single-select dropdown (one submission per request type).
# No dedicated "Access" option is offered by this form; "Right to Data Portability" is
# the closest and is used for Right.RIGHT_TO_ACCESS. "Right to Rectification" is offered
# but not automated (it reveals an extra required "Information to Rectify" textarea,
# name="rectification_info"); no other option adds a conditional field.
# Cloudflare Turnstile ("Please verify you're human") requires manual solve in live mode.
#
# Page elements:
#   "Select request type" dropdown  Request Type (options in PAGE_RIGHTS)
#   first_name / last_name          First / Last name (by name=)
#   email / phone                   Email / Phone
#   country                         Country -> "United States"
#   address_1 / city / region / zip_code   Address / City / State(region) / ZIP
#   "Submit Request" button         Submit (manual, after Turnstile)
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://dsr.trustsuperset.com/?orgId=275d6c62-eb0f-4f8a-80c2-b72573902714"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Right to Data Portability",
    Right.RIGHT_TO_OPT_OUT: [
        "Right to Opt-out of Sales",
        "Right to Restrict Processing",
        "Right to Not be Subject to Automated Decision-Making",
        "Right to Limit Sensitive Personal Information",
    ],
    Right.RIGHT_TO_DELETE: "Right to Erasure",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every request type the dropdown lists -> Right (None = offered but not automated).
PAGE_RIGHTS = {
    "Right to Rectification": None,
    "Right to Restrict Processing": Right.RIGHT_TO_OPT_OUT,
    "Right to Data Portability": Right.RIGHT_TO_ACCESS,
    "Right to Not be Subject to Automated Decision-Making": Right.RIGHT_TO_OPT_OUT,
    "Right to Opt-out of Sales": Right.RIGHT_TO_OPT_OUT,
    "Right to Limit Sensitive Personal Information": Right.RIGHT_TO_OPT_OUT,
    "Right to Erasure": Right.RIGHT_TO_DELETE,
}


async def submit_request(tab, right, entry, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    request_type = await tab.find(text="Select request type", raise_exc=False)
    if request_type:
        await request_type.click()
        await asyncio.sleep(1)
        option = await tab.find(text=entry, raise_exc=False)
        if option:
            await option.click()
    await asyncio.sleep(1)

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

    if SuperScraper.DRY_RUN:
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(f"DRY RUN: would submit '{right.name}' ({entry}) for {SuperScraper.EMAIL}")
        return

    print(f"\nForm filled for '{right.name}' ({entry}). Solve the Cloudflare Turnstile challenge,")
    print("click Submit Request, then press Enter once the confirmation appears...")
    input()

    print(f"Submitted '{right.name}' ({entry}) for {SuperScraper.EMAIL} — confirm in the browser.")


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
            entries = RIGHT_MAP[right]
            for entry in (entries if isinstance(entries, list) else [entries]):
                await submit_request(tab, right, entry, super_scraper)


asyncio.run(main())

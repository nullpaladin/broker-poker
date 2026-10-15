# inboundinsight.com — Trust Superset DSR platform
# Request Type is a single-select dropdown (one submission per right): Right to
# Rectification (Correct, not automated), Right to Restrict Processing, Right to Data
# Portability, Right to Not be Subject to Automated Decision-Making, Right to Opt-out
# of Sales, Right to Limit Sensitive Personal Information, Right to Erasure (Delete).
# No dedicated "Access" option is offered by this form (portability is the nearest).
# Which run is decided only by SuperScraper.rights_to_exercise.
# Cloudflare Turnstile ("Please verify you're human") requires manual solve
# in live mode.
#
# Page elements:
#   "Select request type" dropdown   Request Type (options as in RIGHT_MAP)
#   name=first_name / last_name      First / Last name
#   name=email / phone               Email / Phone
#   name=country / region            Country / State (region)
#   name=address_1 / city / zip_code Address / City / ZIP
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://dsr.trustsuperset.com/?orgId=2183d64e-c307-4322-938f-5711d839719e"

# Trust Superset dropdown; GDPR "Restrict Processing" rides with opt-out, portability
# with access. "Right to Rectification" (correct) is not automated.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Right to Data Portability"],
    Right.RIGHT_TO_OPT_OUT: [
        "Right to Opt-out of Sales",
        "Right to Restrict Processing",
        "Right to Not be Subject to Automated Decision-Making",
        "Right to Limit Sensitive Personal Information",
    ],
    Right.RIGHT_TO_DELETE: ["Right to Erasure"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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

    label = entry.lower().replace(" ", "_")

    if SuperScraper.DRY_RUN:
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}_{label}")
        print(f"DRY RUN: would submit '{right.name}' ({entry}) for {SuperScraper.EMAIL}")
        return

    print(f"\nForm filled for '{entry}'. Solve the Cloudflare Turnstile challenge,")
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
            for entry in RIGHT_MAP[right]:
                await submit_request(tab, right, entry, super_scraper)


asyncio.run(main())

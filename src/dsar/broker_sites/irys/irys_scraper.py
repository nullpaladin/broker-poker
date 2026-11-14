# irys.us — Trust Superset DSR platform (dsr.trustsuperset.com), same platform
# as brooksim.com / datadelivers.com / inboundinsight.com elsewhere in this
# repo. Navigate directly to the underlying form URL.
# Rights the form exposes (single-select "Request Type" dropdown, one submission per
# option): Right to Rectification (Correct — NOT automated, not in RIGHT_MAP), Right to
# Restrict Processing, Right to Data Portability (used as this form's Access),
# Right to Not be Subject to Automated Decision-Making, Right to Opt-out of Sales,
# Right to Limit Sensitive Personal Information, Right to Erasure (Delete).
# No dedicated "Access" option is offered by this form. Which rights run is decided
# ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Cloudflare Turnstile ("Please verify you're human") requires a manual solve in
# live mode.  **CAPTCHA solution required**
#
# Page elements:
#   "Select request type" dropdown   Request Type (options chosen by text, see RIGHT_MAP)
#   name=first_name / last_name      First / Last name
#   name=email / phone               Email / Phone
#   name=country / region            Country / State
#   name=address_1 / city / zip_code Address / City / Zip
#   name=maid                        Advertising ID (required)
#   name=rectification_info          "Information to Rectify" textarea (Rectification only; unused)
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://dsr.trustsuperset.com/?orgId=0d0512a8-9337-4cb5-9369-acf2ef40a077"

# Trust Superset 7-option dropdown; GDPR "Restrict Processing" rides with opt-out.
# "Right to Rectification" (Correct) is deliberately not automated.
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

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The request-type dropdown is a custom widget with no recorded option selector.)

FIELD_XPATHS = {
    "First name": "//*[@name='first_name']",
    "Last name": "//*[@name='last_name']",
    "Email": "//*[@name='email']",
    "Country": "//*[@name='country']",
    "State": "//*[@name='region']",
    "Advertising ID": "//*[@name='maid']",
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

    # This deployment's fields: first_name, last_name, email, country, region,
    # and a REQUIRED "maid" (Advertising ID). No address/city/zip/phone here.
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
        ("maid", SuperScraper.ADVERTISING_ID),
    ]:
        if not value:
            continue
        field = await tab.find(name=name, timeout=4, raise_exc=False)
        if field:
            await field.type_text(value)
            await asyncio.sleep(0.2)

    label = entry.lower().replace(" ", "_")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' ({entry}) for {SuperScraper.EMAIL}"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
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

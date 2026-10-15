# persistent.id — Trust Superset DSR platform (dsr.trustsuperset.com), same platform
# as brooksim.com / datadelivers.com / inboundinsight.com elsewhere in this
# repo. Navigate directly to the underlying form URL.
# Request Type is a single-select dropdown (one submission per entry): Right to
# Rectification (Correct), Right to Restrict Processing, Right to Data
# Portability, Right to Not be Subject to Automated Decision-Making, Right to
# Opt-out of Sales, Right to Limit Sensitive Personal Information, Right to
# Erasure (Delete). Which of them run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). No dedicated "Access" option is
# offered by this form (Data Portability is the closest and is mapped to Access).
# "Right to Rectification" (Correct) is not automated (PAGE_RIGHTS -> None).
# Cloudflare Turnstile ("Please verify you're human") requires a manual solve
# in live mode.
# **CAPTCHA solution required**
#
# Page elements:
#   "Select request type" dropdown   Request type (options listed in RIGHT_MAP / PAGE_RIGHTS)
#   first_name / last_name           First / Last name
#   email / phone                    Email / Phone
#   country / region                 Country ("United States") / State
#   address_1 / city / zip_code      Street address / City / ZIP
#   maid                             Advertising ID (required on this deployment)
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://dsr.trustsuperset.com/?orgId=7b774bc1-608f-8c4c-bb90-453b1540f48b"

# Trust Superset 7-option dropdown; GDPR "Restrict Processing" rides with opt-out.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Right to Data Portability"],
    Right.RIGHT_TO_OPT_OUT: [
        "Right to Not be Subject to Automated Decision-Making",
        "Right to Opt-out of Sales",
        "Right to Restrict Processing",
        "Right to Limit Sensitive Personal Information",
    ],
    Right.RIGHT_TO_DELETE: ["Right to Erasure"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every request type the dropdown offers -> the Right it maps to (None = not automated).
PAGE_RIGHTS = {
    "Right to Rectification": None,
    "Right to Data Portability": Right.RIGHT_TO_ACCESS,
    "Right to Not be Subject to Automated Decision-Making": Right.RIGHT_TO_OPT_OUT,
    "Right to Opt-out of Sales": Right.RIGHT_TO_OPT_OUT,
    "Right to Restrict Processing": Right.RIGHT_TO_OPT_OUT,
    "Right to Limit Sensitive Personal Information": Right.RIGHT_TO_OPT_OUT,
    "Right to Erasure": Right.RIGHT_TO_DELETE,
}


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

    label = right.lower().replace(" ", "_")

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    print(f"\nForm filled for '{right}'. Solve the Cloudflare Turnstile challenge,")
    print("click Submit Request, then press Enter once the confirmation appears...")
    input()

    print(f"Submitted '{right}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    entries = [entry for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for entry in entries:
            await submit_request(tab, entry, super_scraper)


asyncio.run(main())

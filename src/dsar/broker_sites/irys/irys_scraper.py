# irys.us — Trust Superset DSR platform (dsr.trustsuperset.com), same platform
# as brooksim.com / datadelivers.com / inboundinsight.com elsewhere in this
# repo. Navigate directly to the underlying form URL.
# Request Type is a single-select dropdown (one submission per right): Right to
# Rectification (Correct), Right to Restrict Processing, Right to Data
# Portability, Right to Not be Subject to Automated Decision-Making, Right to
# Opt-out of Sales, Right to Limit Sensitive Personal Information
# unconditionally; Right to Erasure (Delete) gated on REMOVE_INFORMATION.
# No dedicated "Access" option is offered by this form.
# Selecting Rectification reveals an additional required "Information to
# Rectify" textarea (name="rectification_info"). Cloudflare Turnstile
# ("Please verify you're human") requires a manual solve in live mode.
# **CAPTCHA solution required**
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://dsr.trustsuperset.com/?orgId=0d0512a8-9337-4cb5-9369-acf2ef40a077"

# Trust Superset 7-option dropdown; GDPR "Restrict Processing" rides with opt-out.
RIGHT_MAP = {
    "correct": ["Right to Rectification"],
    "portability": ["Right to Data Portability"],
    "opt_out_profiling": ["Right to Not be Subject to Automated Decision-Making"],
    "opt_out_sale_share": ["Right to Opt-out of Sales", "Right to Restrict Processing"],
    "limit_sensitive_pi": ["Right to Limit Sensitive Personal Information"],
    "delete": ["Right to Erasure"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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
        await SuperScraper.screenshot(tab, f"resources/screenshots/irys_dry_run_{label}.png")
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

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    rights = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, super_scraper)


asyncio.run(main())

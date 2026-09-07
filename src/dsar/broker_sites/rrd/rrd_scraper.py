# rrd.com (Valassis, an RRD Company) — OneTrust portal. One submission covers
# all rights. Subject type "Consumer". Request types multi-selected.
# emailDSARElement is communication email (reply-to); formField87DSARElement is
# the consumer's own email used for data lookup — fill both with EMAIL.
# State (stateDSARElement) appears after Country is selected.
# Phone country code vt-input-12 (type "1"). Image CAPTCHA (captchaCode).
# Rights exercised: Opt-Out (Do Not Sell/Share, Targeted Advertising, Profiling,
# Sensitive), Correct, Know (Categories + Specific Pieces), Copy/Access.
# Delete gated on REMOVE_INFORMATION.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/45e4be25-919b-483f-9f95-12809576a2b3/6e633594-9a81-48bb-97ab-6fb29bf46019"

RIGHT_MAP = {
    "access": [
        "Request a Copy of Personal Information",
        "Request to Know (Specific Pieces of Personal Information)",
        "Request to Know (Categories of Personal Information & 3rd Parties Shared)",
    ],
    "know_third_parties": ["Request to Know (Categories of Personal Information & 3rd Parties Shared)"],
    "correct": ["Request to Correct Inaccurate Personal Information"],
    "opt_out_sale_share": ["Request to Opt-Out (Do Not Sell or Share My Personal Information)"],
    "opt_out_targeted_ads": ["Request to Opt-Out (Targeted Advertising)"],
    "opt_out_profiling": ["Request to Opt-Out (Profiling)"],
    "limit_sensitive_pi": ["Request to Opt-Out (Use of My Sensitive Information)"],
    "delete": ["Request to Delete Personal Information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _autocomplete(tab, field_id, text):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return
    await field.click()
    await field.type_text(text)
    await asyncio.sleep(2)
    opts = await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []
    for opt in opts:
        if await opt.is_visible():
            t = await opt.text
            if t and t.strip() == text:
                await opt.click()
                await asyncio.sleep(1)
                return


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(7)

        # Subject type
        consumer_btn = await tab.find(**{"aria-label": "Consumer"}, raise_exc=False)
        if consumer_btn:
            await consumer_btn.click_using_js()
        await asyncio.sleep(0.5)

        # Request types
        codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
        if not codes:
            print("No requested privacy rights apply to this form — nothing to do.")
            return
        requests = [entry for code in codes for entry in RIGHT_MAP[code]]

        for req_label in requests:
            btn = await tab.find(**{"aria-label": req_label}, raise_exc=False)
            if btn:
                await btn.click_using_js()
            else:
                print(f"{super_scraper.OOPS} Request button not found: {req_label}")
            await asyncio.sleep(0.3)

        # Communication email
        comm_email = await tab.find(id="emailDSARElement", raise_exc=False)
        if comm_email:
            await comm_email.type_text(SuperScraper.EMAIL)

        # Country (state appears after)
        await _autocomplete(tab, "countryDSARElement", "United States")
        await asyncio.sleep(1)

        # First/Last name
        first = await tab.find(id="firstNameDSARElement", raise_exc=False)
        if first:
            await first.type_text(SuperScraper.FIRST_NAME)

        last = await tab.find(id="lastNameDSARElement", raise_exc=False)
        if last:
            await last.type_text(SuperScraper.LAST_NAME)

        # Address
        address = await tab.find(id="addressDSARElement", raise_exc=False)
        if address:
            await address.type_text(SuperScraper.ADDRESS)

        # City
        city = await tab.find(id="cityDSARElement", raise_exc=False)
        if city:
            await city.type_text(SuperScraper.CITY)

        # State (autocomplete, appears after country)
        await _autocomplete(tab, "stateDSARElement", SuperScraper.STATE)
        await asyncio.sleep(0.5)

        # ZIP
        zip_field = await tab.find(id="zipDSARElement", raise_exc=False)
        if zip_field:
            await zip_field.type_text(SuperScraper.ZIP_CODE)

        # Consumer email (data lookup email)
        consumer_email = await tab.find(id="formField87DSARElement", raise_exc=False)
        if consumer_email:
            await consumer_email.type_text(SuperScraper.EMAIL)

        # Phone country code
        phone_cc = await tab.find(id="vt-input-12", raise_exc=False)
        if phone_cc:
            await phone_cc.click()
            await phone_cc.type_text("1")
        await asyncio.sleep(0.5)

        # Phone
        phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
        if phone:
            await phone.type_text(SuperScraper.PHONE_NUMBER)

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            captcha_field = await tab.find(id="captchaCode", raise_exc=False)
            if captcha_field:
                await captcha_field.scroll_into_view()
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "resources/screenshots/rrd_dry_run.png")
            return

        print(
            f"\nForm filled. "
            f"Enter the CAPTCHA code, then click Submit. "
            f"Press Enter after confirmation..."
        )
        input()

        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())

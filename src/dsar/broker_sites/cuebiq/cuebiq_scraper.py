# cuebiq.com — Gravity Forms MAID-based privacy request (location/mobile-ad
# data company; no name/address fields, everything keys off the Mobile
# Advertising ID). "I wish to:" radio is single-select (one submission per
# right): opt-out and access unconditionally; erase/delete gated on
# REMOVE_INFORMATION. Type of ID defaults to GAID (Android) since ADVERTISING_ID
# format is ambiguous for iOS per the .env comment; change to IDFA manually if
# submitting an Apple identifier. "Authorized Agent on behalf of a CA resident"
# checkbox answered "No". To submit multiple MAIDs, use the browser's back
# button then refresh rather than resubmitting from scratch (per prior research
# notes) — not automated here since SuperScraper only holds one ADVERTISING_ID.
# reCAPTCHA requires manual solve in live mode.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://cuebiq.com/privacy-request/"

RIGHT_MAP = {
    "access": [("get access to or a copy of my personal information", "access")],
    "opt_out_sale_share": [("opt-out/do not sell or share my personal information", "opt_out")],
    "delete": [("erase/delete my personal information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, radio_value, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(4)

    radio = await tab.find(xpath=f"//input[@name='input_3' and @value=\"{radio_value}\"]", raise_exc=False)
    if radio:
        await radio.click()

    email = await tab.find(id="input_5_4", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    await tab.execute_script(
        'var s = document.querySelector("select#input_5_7"); s.value = "GAID"; s.dispatchEvent(new Event("change"));'
    )

    if SuperScraper.ADVERTISING_ID:
        maid = await tab.find(id="input_5_8", raise_exc=False)
        if maid:
            await maid.type_text(SuperScraper.ADVERTISING_ID)

    no_agent = await tab.find(xpath="//input[@name='input_9.1']", raise_exc=False)
    if no_agent:
        await no_agent.click()

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{radio_value}' for <{SuperScraper.EMAIL}>")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/cuebiq_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{radio_value}'. Solve the reCAPTCHA, click Submit My Request,")
    print("then press Enter once the confirmation appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{radio_value}' for <{SuperScraper.EMAIL}>")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{radio_value}' — verify in browser")


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
        for radio_value, label in rights:
            await submit_request(tab, radio_value, label, super_scraper)


asyncio.run(main())

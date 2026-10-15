# cuebiq.com — Gravity Forms MAID-based privacy request (location/mobile-ad
# data company; no name/address fields, everything keys off the Mobile
# Advertising ID). "I wish to:" radio is single-select (one submission per
# right). Type of ID defaults to GAID (Android) since ADVERTISING_ID
# format is ambiguous for iOS per the .env comment; change to IDFA manually if
# submitting an Apple identifier. To submit multiple MAIDs, use the browser's back
# button then refresh rather than resubmitting from scratch (per prior research
# notes) — not automated here since SuperScraper only holds one ADVERTISING_ID.
# reCAPTCHA requires manual solve in live mode.
#
# Page elements:
#   input[name=input_3] (radio, by value)   "I wish to:" request choice (see RIGHT_MAP)
#   #input_5_4                              Email
#   select#input_5_7                        "Type of ID" -> "GAID"
#   #input_5_8                              Mobile Advertising ID (ADVERTISING_ID)
#   input[name="input_9.1"]                 Authorized-agent checkbox, clicked as the "No" answer
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://cuebiq.com/privacy-request/"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "get access to or a copy of my personal information",
    Right.RIGHT_TO_OPT_OUT: "opt-out/do not sell or share my personal information",
    Right.RIGHT_TO_DELETE: "erase/delete my personal information",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, radio_value, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(4)

    radio = await tab.find(xpath=f"//input[@name='input_3' and @value=\"{radio_value}\"]", raise_exc=False)
    if radio:
        await radio.click()

    email = await tab.find(id="input_5_4", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    id_type = await tab.find(id="input_5_7", raise_exc=False)
    if id_type:
        await js_utils.select_native_option(id_type, value="GAID")

    if SuperScraper.ADVERTISING_ID:
        maid = await tab.find(id="input_5_8", raise_exc=False)
        if maid:
            await maid.type_text(SuperScraper.ADVERTISING_ID)

    no_agent = await tab.find(xpath="//input[@name='input_9.1']", raise_exc=False)
    if no_agent:
        await no_agent.click()

    if SuperScraper.DRY_RUN:
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        return

    print(f"\nForm filled for '{right.name}'. Solve the reCAPTCHA, click Submit My Request,")
    print("then press Enter once the confirmation appears...")
    input()

    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


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
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())

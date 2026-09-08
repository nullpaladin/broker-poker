# pulsepoint.com — custom OneTrust Angular portal (mynt-test-privacy.my.
# onetrust.com), MAID-based. "I am a (an)" role="option" toggle answered
# "Consumer" — this reveals a "Select request type(s)" toggle group
# (Request to Delete Personal Information / Request to Access or Know /
# Request to Correct Inaccurate Personal Information). Despite the plural
# "(s)" wording it is SINGLE-select (confirmed: selecting a second option
# deselects the first) — same misleading-plural pattern as qualcomm.com
# elsewhere in this repo — so this is one submission per right. No
# Opt-Out option exists on this form. Country/State are vt-autocomplete
# comboboxes (type then click the matching role="option"). "Mobile
# Advertiser ID or Cookie" (formField78DSARElement) required. captchaCode
# is a BotDetect image CAPTCHA — **CAPTCHA solution required**. Exercises
# "Request to Access or Know" unconditionally; "Request to Delete Personal
# Information" gated on REMOVE_INFORMATION. ("Request to Correct
# Inaccurate Personal Information" skipped — no concrete inaccuracy to
# describe.)
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://mynt-test-privacy.my.onetrust.com/webform/ebe19500-bc8d-487f-9d89-98fde8b270e2/bac5d2a2-fd3e-4830-99b6-bd2a69fec1c9"

RIGHT_MAP = {
    "access": ["Request to Access or Know"],
    "delete": ["Request to Delete Personal Information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _autocomplete_select(tab, field_id, text, super_scraper, description):
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} {description} field not found")
        return
    await field.click()
    await asyncio.sleep(0.3)
    await tab.keyboard.type_text(text)
    await asyncio.sleep(1.2)
    option = await tab.find(xpath=f"//*[@role='option' and normalize-space()='{text}']", raise_exc=False)
    if option:
        await option.click()
        await asyncio.sleep(0.7)
    else:
        print(f"{super_scraper.OOPS} {description} option '{text}' not found")


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    consumer_option = await tab.find(
        xpath="//*[@role='option' and @aria-label='Consumer']", raise_exc=False
    )
    if consumer_option:
        await consumer_option.click()
        await asyncio.sleep(1)
    else:
        print(f"{super_scraper.OOPS} 'Consumer' option not found")

    right_option = await tab.find(
        xpath=f"//*[@role='option' and normalize-space()='{right}']", raise_exc=False
    )
    if right_option:
        await right_option.click()
        await asyncio.sleep(0.7)
    else:
        print(f"{super_scraper.OOPS} request type '{right}' not found")

    await _autocomplete_select(tab, "countryDSARElement", "United States", super_scraper, "country")
    await _autocomplete_select(tab, "stateDSARElement", SuperScraper.STATE, super_scraper, "state")

    email_field = await tab.find(id="emailDSARElement", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    maid_field = await tab.find(id="formField78DSARElement", raise_exc=False)
    if maid_field:
        await maid_field.type_text(SuperScraper.ADVERTISING_ID)

    label = "".join(c if c.isalnum() else "_" for c in right.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/pulsepoint_dry_run_{label}.png")
    print(
        f"\n'{right}' request filled but NOT submitted — a BotDetect image CAPTCHA "
        "requires manual entry before submitting."
    )


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

# audigent.com — a SixFifty "Request Easy" multi-step wizard (app.sixfifty.com).
# Every question is a custom-styled radio group: the real <input> is visually
# hidden (opacity-0) and not click()-able directly (raises ElementNotVisible),
# but its enclosing <label> (data-testid="-someOptionKey", no "-input" suffix)
# is a normal clickable element — click the label, not the input.
#
# Flow: (1) state/region radio -> (2) request-type radio, single-select (one
# submission per right): Right to Know - Specific (Access) and Do Not Sell My
# Data (Opt-Out) unconditionally; Delete My Data gated on REMOVE_INFORMATION
# (other options — Correct/Port/Profiling/Targeted-Advertising/Question-
# Profiling/Appeal — are additional granular rights not exercised here) ->
# (2b) some rights (observed on Opt-Out, not on Access) insert an extra
# "yourself or an authorized agent" question here — answered "myself" only
# when it's actually present, since Access skips straight past it -> (3) "Do
# you know your online identifier?" (the ad.gt cookie ID / MAID
# Audigent uses to look up records, since most of what they hold isn't tied
# to a clear-text name) — answered "I do not have this information at this
# time" since ADVERTISING_ID is a placeholder value, not a real per-device
# identifier, and supplying a fake one would misrepresent the request -> (4)
# Full Name + Email, the only point personal identity is collected at all.
# Ends in a reCAPTCHA requiring a manual solve in live mode.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://app.sixfifty.com/request-easy/653b-4813/questions/5359740"

STATE_TO_KEY = {
    "california": "californiaUsa",
    "colorado": "coloradoUsa",
    "connecticut": "connecticutUsa",
    "indiana": "indianaUsa",
    "kentucky": "kentuckyUsa",
    "maryland": "marylandUsa",
    "minnesota": "minnesotaUsa",
    "oregon": "oregonUsa",
    "rhode island": "rhodeIslandUsa",
    "tennessee": "tennesseeUsa",
    "texas": "texasUsa",
    "utah": "utahUsa",
    "virginia": "virginiaUsa",
}
FALLBACK_STATE_KEY = "otherStateOrRegion"

RIGHTS = ["rightToKnowSpecific", "doNotSellMyData"]
DELETE_RIGHT = "deleteMyData"


async def _click_label(tab, key, super_scraper, description):
    label = await tab.find(xpath=f"//label[@data-testid='-{key}']", raise_exc=False)
    if not label:
        print(f"{super_scraper.OOPS} {description} option '{key}' not found")
        return False
    await label.click()
    await asyncio.sleep(1)
    return True


async def _next(tab):
    next_btn = await tab.find(xpath="//*[@data-testid='navFooterNext']", raise_exc=False)
    if next_btn:
        await next_btn.click()
        await asyncio.sleep(2)


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    state_key = STATE_TO_KEY.get(SuperScraper.STATE.strip().lower(), FALLBACK_STATE_KEY)
    if not await _click_label(tab, state_key, super_scraper, "state"):
        return
    await _next(tab)

    if not await _click_label(tab, right, super_scraper, "request type"):
        return
    await _next(tab)

    # Some rights (e.g. Opt-Out) insert an extra "yourself or an authorized
    # agent" question before the online-identifier step; Access does not.
    # Only click it (and advance) if it's actually present.
    myself_label = await tab.find(xpath="//label[@data-testid='-myself']", raise_exc=False)
    if myself_label:
        await myself_label.click()
        await asyncio.sleep(1)
        await _next(tab)

    if not await _click_label(
        tab, "iDoNotHaveThisInformationAtThisTime", super_scraper, "online identifier"
    ):
        return
    await _next(tab)

    name_field = await tab.find(id="requestEasyNameInput", raise_exc=False)
    email_field = await tab.find(id="requestEasyEmailInput", raise_exc=False)
    if name_field:
        await name_field.click()
        await name_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    if email_field:
        await email_field.click()
        await email_field.type_text(SuperScraper.EMAIL)

    label = right.lower()

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/audigent_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{right}'. Solve the reCAPTCHA, click Submit,")
    print("then press Enter once the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{right}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
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

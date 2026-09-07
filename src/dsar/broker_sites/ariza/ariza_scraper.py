# ariza.com (branded "Azira") — TrustArc IRM privacy request form. Custom
# react-select comboboxes for "I am" (Individual/Agent), "Resident of"
# (state/country full names), and "Type of Request" (single-select — one
# submission per right; the request-type options only populate after
# "Resident of" is chosen). Click the .select__control div, type the target
# text, then click the matching .select__option. Exercises Access, Opt-Out/
# Unsubscribe, Do Not Sell or Share, Withdraw Consent, Limit Sensitive PI Use,
# and Correct unconditionally; Delete gated on REMOVE_INFORMATION. MAID
# (Mobile Ad ID) is optional — filled from ADVERTISING_ID when set. The
# consent checkbox is a standard accuracy/TrustArc-role attestation (not an
# anti-automation notice) — safe to check. reCAPTCHA v2 requires manual solve.
#
# CAUTION: earlier in development this TrustArc-hosted form threw a
# PerimeterX-style "Let's confirm you are human" interstitial after ~8 rapid
# requests, blocking further automated access for the rest of that session
# (same pattern documented for oracle.com and liveramp.com elsewhere in this
# repo). On a later, separate session the form loaded cleanly again with no
# interstitial — it was rapid repeated testing traffic, not a permanent
# block. Confirmed end-to-end with a clean DRY_RUN screenshot.
#
# NOTE: First/Last Name, Email, MAID, and the consent checkbox all have ids
# starting with a digit (e.g. "00000000-0000-0000-0000-000000001002fn").
# `tab.find(id=...)` builds an unescaped `#{id}` CSS selector, which is
# invalid syntax for an id starting with a digit — it silently resolves to
# the wrong (invisible) element instead of raising, so `.type_text()` then
# fails with ElementNotVisible even though the real field is on-screen and
# fillable. Every one of these fields is targeted by xpath instead, same
# workaround as the colon-id bug documented elsewhere in this repo.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://submit-irm.trustarc.com/services/validation/0a80503b-1d56-4d50-a898-4377a0227dab"

IAM_CONTAINER = "00000000-0000-0000-0000-000000001001-select-container"
RESIDENT_CONTAINER = "00000000-0000-0000-0000-000000001004-select-container"
REQUEST_TYPE_CONTAINER = "00000000-0000-0000-0000-000000001005-select-container"

RIGHTS = [
    "Access My Information",
    "Opt-out or Unsubscribe",
    "Do not Sell or Share My Personal Information",
    "Withdraw My Consent",
    "Limit the Use of My Sensitive Personal Information",
    "Correct or Update My Information",
]
DELETE_RIGHT = "Delete My Information"


async def _select_option(tab, container_id, text):
    ctrl = await tab.find(
        xpath=f"//div[@id='{container_id}']//div[contains(@class,'select__control')]",
        raise_exc=False,
    )
    if not ctrl:
        return False
    await ctrl.click()
    await asyncio.sleep(0.5)
    await tab.keyboard.type_text(text)
    await asyncio.sleep(1)
    opt = await tab.find(
        xpath=f"//div[contains(@class,'select__option') and contains(text(),'{text}')]",
        raise_exc=False,
    )
    if opt:
        await opt.click()
        await asyncio.sleep(0.5)
        return True
    return False


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    await _select_option(tab, IAM_CONTAINER, "Individual")

    first = await tab.find(xpath="//input[@id='00000000-0000-0000-0000-000000001002fn']", raise_exc=False)
    if first:
        await first.scroll_into_view()
        await first.type_text(SuperScraper.FIRST_NAME)
    last = await tab.find(xpath="//input[@id='00000000-0000-0000-0000-000000001002ln']", raise_exc=False)
    if last:
        await last.scroll_into_view()
        await last.type_text(SuperScraper.LAST_NAME)
    email = await tab.find(xpath="//input[@id='00000000-0000-0000-0000-000000001003']", raise_exc=False)
    if email:
        await email.scroll_into_view()
        await email.type_text(SuperScraper.EMAIL)

    if SuperScraper.ADVERTISING_ID:
        maid = await tab.find(xpath="//input[@id='77916532-b470-4337-8bc5-269104f7eaf9']", raise_exc=False)
        if maid:
            await maid.scroll_into_view()
            await maid.type_text(SuperScraper.ADVERTISING_ID)

    await _select_option(tab, RESIDENT_CONTAINER, SuperScraper.STATE)
    await _select_option(tab, REQUEST_TYPE_CONTAINER, right)

    consent = await tab.find(xpath="//input[@id='00000000-0000-0000-0000-000000001007']", raise_exc=False)
    if consent:
        # custom-styled hidden checkbox (ta-custom-hidden-checkbox) — not
        # click()-able directly, set + dispatch events instead
        await consent.execute_script(
            "this.checked=true;"
            "this.dispatchEvent(new Event('click', {bubbles:true}));"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )

    label = right.lower().replace(" ", "_").replace("/", "_")

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/ariza_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{right}'. Solve the reCAPTCHA, click Submit Request,")
    print("then press Enter once the confirmation page appears...")
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

    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, super_scraper)


asyncio.run(main())

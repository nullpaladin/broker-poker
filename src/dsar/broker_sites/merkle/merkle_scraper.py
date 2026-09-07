# merkle.com — Custom OneTrust "webform" portal (privacyportal-de.onetrust.com),
# embedded in an iframe on control-your-personal-information.html, navigated
# to directly. "Select Request Type" (Access/Delete/Do Not Share or Sell/
# Correct/Limit Sensitive/Opt-Out Targeted Advertising/Opt-Out Profiling),
# "Are you submitting this request for yourself?" (Yes, myself), and "Which
# dentsu brands relate to your request" (only "Merkle") are all
# `role="option"`-style toggle-button groups, single-select — one
# submission per request type. Name/address/city/zip/email use stable
# DSARElement ids and are plain text; State (formField41DSARElement) is a
# custom autocomplete combobox — typing alone leaves it empty/invalid, so
# the matching role="option" dropdown entry is clicked instead (same trap
# as mediawallah.com's OneTrust dsarwebform elsewhere in this repo).
# BotDetect image CAPTCHA (`captchaCode`) requires manual entry. The
# page also states email confirmation is required within 3 days before any
# request is actually processed. Exercises Access and Do Not Share or Sell
# unconditionally; Delete gated on REMOVE_INFORMATION. Correct/Limit
# Sensitive/Opt-Out Targeted Advertising/Opt-Out Profiling skipped as
# auxiliary.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacyportal-de.onetrust.com/webform/79bad1a6-7964-4224-be55-bb1da49b8d2d/3e467ef9-b66a-49d8-bc62-40943a80745c"

RIGHTS = ["Access My Information", "Do Not Share or Sell My Information"]
DELETE_RIGHT = "Delete My Information"


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    right_opt = await tab.find(text=right, raise_exc=False)
    if right_opt:
        await right_opt.click()
    else:
        print(f"{super_scraper.OOPS} '{right}' option not found")

    myself_opt = await tab.find(text="Yes, myself", raise_exc=False)
    if myself_opt:
        await myself_opt.click()

    # NOT tab.find(text="Merkle") — that substring-matches the intro
    # paragraph ("...Merkle's US data products") before ever reaching the
    # actual button, since pydoll's text search isn't exact-match. Target
    # the role="option" button precisely instead.
    brand_opt = await tab.find(xpath="//*[@role='option' and @aria-label='Merkle']", raise_exc=False)
    if brand_opt:
        await brand_opt.click()

    fields = {
        "firstNameDSARElement": SuperScraper.FIRST_NAME,
        "lastNameDSARElement": SuperScraper.LAST_NAME,
        "addressDSARElement": SuperScraper.ADDRESS,
        "address2DSARElement": SuperScraper.ADDRESS_LINE_TWO,
        "cityDSARElement": SuperScraper.CITY,
        "zipDSARElement": SuperScraper.ZIP_CODE,
        "emailDSARElement": SuperScraper.EMAIL,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    # State (formField41DSARElement) is a custom autocomplete combobox, not
    # a plain text field — same trap as mediawallah.com's OneTrust
    # dsarwebform elsewhere in this repo. Click the matching dropdown
    # option instead of trusting type_text to land correctly.
    state_field = await tab.find(id="formField41DSARElement", raise_exc=False)
    if state_field:
        await state_field.click()
        await asyncio.sleep(0.3)
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(1.2)
        state_opt = await tab.find(
            xpath=f"//*[@role='option' and normalize-space()='{SuperScraper.STATE}']", raise_exc=False
        )
        if state_opt:
            await state_opt.click()
            await asyncio.sleep(0.5)
        else:
            print(f"{super_scraper.OOPS} state option '{SuperScraper.STATE}' not found")

    label = right.lower().replace(" ", "_")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/merkle_dry_run_{label}.png")
    print(
        f"\n'{right}' request filled but NOT submitted — a BotDetect image CAPTCHA is "
        "present and requires manual entry. Submitting also sends a confirmation email "
        "that must be clicked within 3 days before the request is processed."
    )


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

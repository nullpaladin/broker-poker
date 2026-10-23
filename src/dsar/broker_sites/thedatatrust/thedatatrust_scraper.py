# thedatatrust.com — the marketing page (thedatatrust.com/your-privacy-choices/)
# only embeds an Osano DSAR portal via a JS-injected iframe; navigate
# directly to the underlying portal: https://my.datasubject.com/dvx9xrLka0/68954
# (same Osano platform as spycloud.com, but this instance also asks for
# full address + a required free-text "Request Description").
#
# Step 1: click the request-type card (find by visible card title text).
# Step 2 fields: email (id="email"), given-name/family-name (id="given-name"
# /"family-name"), address line 1/2 and city (name="o-addressLine1"
# /"o-addressLine2"/"o-city" — no id, must match by name), State
# (name="o-requestState", native <select> keyed by 2-letter abbreviation),
# Zip (name="o-zipCode"), Phone Number (id="phone-number"), Request
# Description (id="request-description", required free-text -> request_statement). "I am submitting this request on behalf of
# someone other than myself" checkbox (id="representative-type") left
# unchecked. Jurisdiction auto-detected from IP; no location picker.
# Cloudflare Turnstile — auto-verifies invisibly in testing but may prompt
# a manual solve in production, so still flagged as CAPTCHA-required.
#
# One submission per request-type card (separate page navigation each time). Cards:
#   "Summarize my personal information", "Transfer my personal information"   -> access
#   "Do Not Sell or Share to a Third Party", "Don't use my personal information
#   for advertising"                                                           -> opt-out
#   "Third parties your data was sold or shared with"                          -> list of third parties
#   "Delete my personal information"                                           -> delete
# Which run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). Correct is
# skipped (no concrete inaccuracy to describe).
#
# Page elements: request-type cards (matched by title text), #email, #given-name,
# #family-name, #phone-number, [name=o-addressLine1] / [name=o-addressLine2] / [name=o-city] /
# [name=o-zipCode], [name=o-requestState] (State <select>), #request-description,
# #representative-type (left unchecked).
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://my.datasubject.com/dvx9xrLka0/68954"

# Right -> request-type card title(s).
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Summarize my personal information", "Transfer my personal information"],
    Right.RIGHT_TO_OPT_OUT: [
        "Do Not Sell or Share to a Third Party",
        "Don't use my personal information for advertising",
    ],
    Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: ["Third parties your data was sold or shared with"],
    Right.RIGHT_TO_DELETE: ["Delete my personal information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = "h4[data-testid='card-title']"  # datasubject.com card titles (selector not recorded for this site)

FIELD_XPATHS = {
    "Email": "//*[@id='email']",
    "First name": "//*[@id='given-name']",
    "Last name": "//*[@id='family-name']",
    "Address": "//*[@name='o-addressLine1']",
    "City": "//*[@name='o-city']",
    "State": "//*[@name='o-requestState']",
    "Zip": "//*[@name='o-zipCode']",
    "Request description": "//*[@id='request-description']",
}


async def _fill_step2(tab, super_scraper):
    email_field = await tab.find(id="email", raise_exc=False)
    if not email_field:
        print(f"{super_scraper.OOPS} email field not found")
        return False
    await email_field.type_text(SuperScraper.EMAIL)

    text_fields = {
        "given-name": SuperScraper.FIRST_NAME,
        "family-name": SuperScraper.LAST_NAME,
        "phone-number": SuperScraper.PHONE_NUMBER,
    }
    for field_id, value in text_fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    name_fields = {
        "o-addressLine1": SuperScraper.ADDRESS,
        "o-addressLine2": SuperScraper.ADDRESS_LINE_TWO,
        "o-city": SuperScraper.CITY,
        "o-zipCode": SuperScraper.ZIP_CODE,
    }
    for field_name, value in name_fields.items():
        if not value:
            continue
        field = await tab.find(name=field_name, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{field_name}' not found")

    state_select = await tab.find(name="o-requestState", raise_exc=False)
    if state_select:
        state_abbrev = SuperScraper.STATE_ABBREVIATED
        await js_utils.select_native_option(state_select, value=state_abbrev)
    else:
        print(f"{super_scraper.OOPS} State select not found")

    return True


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        requests = [(right, entry) for right in rights for entry in RIGHT_MAP[right]]
        for right, card_title in requests:
            await tab.go_to(URL)
            await asyncio.sleep(6)

            if SuperScraper.HEALTH_CHECK:
                offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
                SuperScraper.audit_rights(offered, PAGE_RIGHTS)

            card = await tab.find(text=card_title, raise_exc=False)
            if not card:
                print(f"{super_scraper.OOPS} Card not found: '{card_title}'")
                continue
            await card.click()
            await asyncio.sleep(2)

            if not await _fill_step2(tab, super_scraper):
                continue

            description_field = await tab.find(id="request-description", raise_exc=False)
            if description_field:
                await description_field.type_text(
                    SuperScraper.request_statement([right], broker="The Data Trust")
                )
            else:
                print(f"{super_scraper.OOPS} Request Description field not found")

            if SuperScraper.HEALTH_CHECK:
                await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

            safe_name = "".join(c if c.isalnum() else "_" for c in card_title.lower())[:40].strip("_")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, f"dry_run_{safe_name}")
            print(
                f"\n'{card_title}' request filled but NOT submitted — a Cloudflare Turnstile "
                "checkbox may require a manual solve before submitting."
            )


asyncio.run(main())

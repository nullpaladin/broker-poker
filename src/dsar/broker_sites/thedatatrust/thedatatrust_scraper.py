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
# Description (id="request-description", required free-text — filled
# generically per right). "I am submitting this request on behalf of
# someone other than myself" checkbox (id="representative-type") left
# unchecked. Jurisdiction auto-detected from IP; no location picker.
# Cloudflare Turnstile — auto-verifies invisibly in testing but may prompt
# a manual solve in production, so still flagged as CAPTCHA-required.
#
# One submission per right (separate page navigation each time). Exercises
# Summarize/Access, Do Not Sell or Share, Don't use for advertising, Transfer
# (portability), and Third parties data was sold or shared with
# unconditionally; Delete gated on REMOVE_INFORMATION. Correct is skipped
# (no concrete inaccuracy to describe).
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://my.datasubject.com/dvx9xrLka0/68954"

ALWAYS_RIGHTS = [
    "Summarize my personal information",
    "Do Not Sell or Share to a Third Party",
    "Don't use my personal information for advertising",
    "Transfer my personal information",
    "Third parties your data was sold or shared with",
]
DELETE_RIGHT = "Delete my personal information"


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
        await state_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            f"  if(this.options[i].value==={state_abbrev!r}){{ this.selectedIndex=i; }}"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )
    else:
        print(f"{super_scraper.OOPS} State select not found")

    return True


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    rights = list(ALWAYS_RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        for right in rights:
            await tab.go_to(URL)
            await asyncio.sleep(6)

            card = await tab.find(text=right, raise_exc=False)
            if not card:
                print(f"{super_scraper.OOPS} Card not found: '{right}'")
                continue
            await card.click()
            await asyncio.sleep(2)

            if not await _fill_step2(tab, super_scraper):
                continue

            description_field = await tab.find(id="request-description", raise_exc=False)
            if description_field:
                await description_field.type_text(
                    f"I am submitting a '{right}' request under applicable state privacy law."
                )
            else:
                print(f"{super_scraper.OOPS} Request Description field not found")

            safe_name = "".join(c if c.isalnum() else "_" for c in right.lower())[:40].strip("_")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, f"resources/screenshots/thedatatrust_dry_run_{safe_name}.png")
            print(
                f"\n'{right}' request filled but NOT submitted — a Cloudflare Turnstile "
                "checkbox may require a manual solve before submitting."
            )


asyncio.run(main())

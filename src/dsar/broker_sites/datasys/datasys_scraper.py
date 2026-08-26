# datasys.com — /privacy/my-privacy-choices is just a marketing/FAQ page;
# its "Make a Privacy Request" button links out to the real wizard at
# privacy.datasys.com. A 4-step React wizard: (1) request type radio
# (opt_out/deletion/access_know, single-select — one submission per right:
# Opt-Out and Access/Know My Data unconditionally; Delete My Data gated on
# REMOVE_INFORMATION), (2) submitter type radio (self/authorized_agent/
# parent_guardian — "self" used here), (3) contact info (First/Last/Email/
# Phone/Address/City/State/Zip), (4) a Review & Submit page listing
# everything back plus a required attestation checkbox, then Submit Request.
# Every radio's real <input> is visually hidden (class "sr-only") inside a
# clickable <label> wrapper — click the label, not the input, same pattern
# as audigent.com elsewhere in this repo. No captcha observed anywhere in
# the flow.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacy.datasys.com"

RIGHTS = ["opt_out", "access_know"]
DELETE_RIGHT = "deletion"


async def _click_radio_label(tab, name, value, super_scraper, description):
    label = await tab.find(
        xpath=f"//input[@name='{name}' and @value='{value}']/ancestor::label", raise_exc=False
    )
    if not label:
        print(f"{super_scraper.OOPS} {description} option '{value}' not found")
        return False
    await label.click()
    await asyncio.sleep(0.5)
    return True


async def _click_next(tab):
    next_btn = await tab.find(text="Next", raise_exc=False)
    if next_btn:
        await next_btn.click()
        await asyncio.sleep(1.5)


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    if not await _click_radio_label(tab, "requestType", right, super_scraper, "request type"):
        return
    await _click_next(tab)

    if not await _click_radio_label(tab, "submitterType", "self", super_scraper, "submitter type"):
        return
    await _click_next(tab)

    fields = {
        "firstName": SuperScraper.FIRST_NAME,
        "lastName": SuperScraper.LAST_NAME,
        "email": SuperScraper.EMAIL,
        "phone": SuperScraper.PHONE_NUMBER,
        "addressLine1": SuperScraper.ADDRESS,
        "city": SuperScraper.CITY,
        "postalCode": SuperScraper.ZIP_CODE,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)

    state_select = await tab.find(id="state", raise_exc=False)
    if state_select:
        state_abbr = await SuperScraper.state_full_name_to_abbreviated(SuperScraper.STATE)
        await state_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            f"  if(this.options[i].value==={state_abbr!r}){{ this.selectedIndex=i; }}"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )
    await _click_next(tab)

    checkbox = await tab.find(xpath="//input[@type='checkbox']", raise_exc=False)
    if checkbox:
        await checkbox.click()

    label = right

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await tab.take_screenshot(path=f"resources/screenshots/datasys_dry_run_{label}.png")
        print(f"Screenshot saved to resources/screenshots/datasys_dry_run_{label}.png")
        return

    submit_btn = await tab.find(text="Submit Request", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{right}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Submit Request button not found for '{right}'")


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

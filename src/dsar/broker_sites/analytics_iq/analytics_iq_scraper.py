# analytics-iq.com — OneTrust portal DSAR form.
# Angular role="button" request type divs — click via click_using_js().
# Country and state use autocomplete comboboxes — type text, then click
# the first visible role="option" element.
# captchaCode is a plain text CAPTCHA input — manual entry required in live mode.
# Rights the form exposes: access, correct (not automated), do-not-sell/share, targeted-ads
# opt-out, limit sensitive PI (all three are RIGHT_TO_OPT_OUT, one submission each), delete.
# Which of them run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements (keep this list current):
#   role=button aria-label=<request type>   Request-type buttons (see RIGHT_MAP)
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #emailDSARElement           Email
#   #addressDSARElement         Address
#   #cityDSARElement            City
#   #countryDSARElement         Country combobox (autocomplete) -> "United States"
#   #stateDSARElement           State combobox (autocomplete)
#   #zipDSARElement             Zip code
#   #phoneNumberDSARElement     Phone number
#   captchaCode                 Text CAPTCHA input (manual entry)
#   aria-label "click to submit form"   Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal.onetrust.com/webform/f6a59500-f900-4652-b030-0cd51afe15a5/87ca07e4-e06c-4ad8-9aa6-ccbbaa8750c1"

# Right -> list of (request-type aria-label, short name). "Correct Inaccurate Data" is
# also offered on the page but is not automatable, so it is not mapped.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Data Access and Information Request CA, CO, CT, OR, TX, UT, VA, MT, NJ, NH, NE, IA, DE, MN, MD Residents Only", "access")],
    Right.RIGHT_TO_OPT_OUT: [
        ("Do Not Sell or Share My Information", "optout"),
        ("Opt-Out of Targeted Advertising", "optout_ads"),
        ("Limit the Use of My Sensitive Personal Information", "sensitive"),
    ],
    Right.RIGHT_TO_DELETE: [("Data Deletion Request Non-California Residents Only", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Recorded request types are aria-labels; the visible text may differ, so they are not copied in.)

FIELD_XPATHS = {
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Address": "//*[@id='addressDSARElement']",
    "City": "//*[@id='cityDSARElement']",
    "Country": "//*[@id='countryDSARElement']",
    "State": "//*[@id='stateDSARElement']",
    "Zip": "//*[@id='zipDSARElement']",
    "Phone": "//*[@id='phoneNumberDSARElement']",
}


async def _select_autocomplete(tab, field_id, search_text):
    """Type into an autocomplete combobox and click the first visible option."""
    field = await tab.find(id=field_id, raise_exc=False)
    if not field:
        return
    await field.type_text(search_text)
    await asyncio.sleep(1.5)
    opts = await tab.find(**{"role": "option"}, find_all=True, raise_exc=False) or []
    for opt in opts:
        if await opt.is_visible():
            await opt.click()
            await asyncio.sleep(0.5)
            return


async def submit_request(tab, right, aria_label, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(7)

    # Request type button (Angular role="button" div)
    req_btn = await tab.find(**{"aria-label": aria_label}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request button '{aria_label}' not found")
        return
    await req_btn.click_using_js()
    await asyncio.sleep(1)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    address = await tab.find(id="addressDSARElement", raise_exc=False)
    if address:
        await address.type_text(SuperScraper.ADDRESS)

    city = await tab.find(id="cityDSARElement", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    await _select_autocomplete(tab, "countryDSARElement", "United States")
    await _select_autocomplete(tab, "stateDSARElement", SuperScraper.STATE)

    zip_field = await tab.find(id="zipDSARElement", raise_exc=False)
    if zip_field:
        await zip_field.type_text(SuperScraper.ZIP_CODE)

    phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)

    time.sleep(0.5)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{right.name}' ('{aria_label}') for {SuperScraper.EMAIL}"
        )
        submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    print(f"\nForm filled for '{aria_label}'.")
    print("Enter the CAPTCHA value shown in the browser into the captchaCode field,")
    print("then click Submit. Press Enter after the confirmation page appears...")
    input()

    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [(right, aria_label, label) for right in rights for aria_label, label in RIGHT_MAP[right]]

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right, aria_label, label in requests:
            await submit_request(tab, right, aria_label, label, super_scraper)


asyncio.run(main())

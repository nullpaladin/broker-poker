# ventiveiq.com — PrivacyPillar-hosted DSAR portal (new platform for this
# repo). The Angular form has NO stable id/name on most text inputs — only
# a preceding <label> distinguishes them — so fields are matched by xpath
# via the nearest ancestor .form-group containing that label text.
#
# "I am a (an)" (radio, name="subjecttype") answered "User" (Customer/
# Employee/User — VentiveIQ is a mobile ad SDK company, "User" is the
# closest generic fit). "Select request type(s)" is, DESPITE the plural
# wording, actual radio inputs sharing name="requesttype" — single-select,
# confirmed by markup (not just by testing) — one submission per right:
# Data Processing, Data Portability, Opt out, Info Request unconditionally;
# Data Deletion gated on REMOVE_INFORMATION. Update Data skipped (no
# concrete correction to describe). Country/State DO have stable
# name="country"/"state" attributes and are ngx-bootstrap typeahead
# comboboxes — click, type, then click the matching typeahead option.
# State is disabled until Country is set. MAID/Mobile ID/IP-address fields
# left blank (optional, no equivalent persona data). Captcha is a 6-digit
# distorted-text code requiring manual entry — **CAPTCHA solution
# required**.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = (
    "https://privacyportal.privacypillar.com/dsar/form?"
    "orgid=0c31c814-ea86-461f-8ccb-294f05bc74c3&propid=cc95835d-7719-4336-b0c4-18146e5d000a"
    "&formid=4348f332-6917-4566-8c56-6fc9eb57097f&status=publish"
)

REQUEST_TYPES = ["Data Processing", "Data Portability", "Opt out", "Info Request"]
DELETE_REQUEST_TYPE = "Data Deletion"


def _field_by_label_xpath(label_text, tag="input"):
    return (
        f"//div[contains(@class,'form-group')]"
        f"[.//label[contains(normalize-space(),{label_text!r})]]//{tag}"
    )


async def _fill_labeled_field(tab, super_scraper, label_text, value, tag="input"):
    if not value:
        return
    field = await tab.find(xpath=_field_by_label_xpath(label_text, tag), raise_exc=False)
    if field:
        await field.type_text(value)
    else:
        print(f"{super_scraper.OOPS} '{label_text}' field not found")


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    user_type_radio = await tab.find(id="User", raise_exc=False)
    if user_type_radio:
        await user_type_radio.click()
    else:
        print(f"{super_scraper.OOPS} 'User' 'I am a (an)' radio not found")

    request_type_radio = await tab.find(xpath=f"//input[@id={request_type!r}]", raise_exc=False)
    if request_type_radio:
        await request_type_radio.click()
    else:
        print(f"{super_scraper.OOPS} request type '{request_type}' radio not found")

    await _fill_labeled_field(tab, super_scraper, "Email", SuperScraper.EMAIL)
    await _fill_labeled_field(tab, super_scraper, "First Name", SuperScraper.FIRST_NAME)
    await _fill_labeled_field(tab, super_scraper, "Last Name", SuperScraper.LAST_NAME)
    await _fill_labeled_field(tab, super_scraper, "Address1", SuperScraper.ADDRESS)
    await _fill_labeled_field(tab, super_scraper, "Address2", SuperScraper.ADDRESS_LINE_TWO)

    country_field = await tab.find(name="country", raise_exc=False)
    if country_field:
        await country_field.click()
        await asyncio.sleep(0.3)
        await tab.keyboard.type_text("United States")
        await asyncio.sleep(1.2)
        option = await tab.find(xpath="//button[contains(normalize-space(),'United States')]", raise_exc=False)
        if option:
            await option.click()
            await asyncio.sleep(0.7)
        else:
            print(f"{super_scraper.OOPS} Country option 'United States' not found")
    else:
        print(f"{super_scraper.OOPS} Country field not found")

    state_field = await tab.find(name="state", raise_exc=False)
    if state_field:
        await state_field.click()
        await asyncio.sleep(0.3)
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(1.2)
        option = await tab.find(
            xpath=f"//button[contains(normalize-space(),{SuperScraper.STATE!r})]", raise_exc=False
        )
        if option:
            await option.click()
            await asyncio.sleep(0.7)
        else:
            print(f"{super_scraper.OOPS} State option '{SuperScraper.STATE}' not found")
    else:
        print(f"{super_scraper.OOPS} State field not found")

    await _fill_labeled_field(tab, super_scraper, "City", SuperScraper.CITY)
    await _fill_labeled_field(tab, super_scraper, "Zipcode", SuperScraper.ZIP_CODE)
    await _fill_labeled_field(
        tab,
        super_scraper,
        "Request Details",
        f"I am submitting a '{request_type}' request under applicable state privacy law.",
        tag="textarea",
    )

    label = "".join(c if c.isalnum() else "_" for c in request_type.lower())[:40].strip("_")
    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/ventiveiq_dry_run_{label}.png")
    print(
        f"\n'{request_type}' request filled but NOT submitted — a 6-digit distorted-text "
        "CAPTCHA requires manual entry before submitting."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    request_types = list(REQUEST_TYPES)
    if SuperScraper.REMOVE_INFORMATION:
        request_types.append(DELETE_REQUEST_TYPE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type in request_types:
            await submit_request(tab, request_type, super_scraper)


asyncio.run(main())

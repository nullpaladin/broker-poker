# thebridgecorp.com — /opt-out/ . Same HubSpot form template as
# withrealcustomers.com ("Connect"), but here it renders inline with `bcf_<hash>_`
# prefixed field ids (not a src-less iframe), so it is driven directly.
#   bcf_*_i_am_a  <select> "State of Residency" — options only "California
#       Resident" / "Non-California Resident"; "California Resident" is selected
#       (the form offers no non-CA path; chosen per this repo's approach for a
#       persona with an equivalent state privacy law — see README).
#   bcf_*_email  (required)
#   bcf_*_enter_advertising_id_  textarea (optional) -> MAID
#   please_select_the_type_of_request_or_requests_you_wish_to_submit_  checkbox
#       group (multi-select, one combined submission): "Request Information"
#       (Access) + "Opt Out" unconditionally; "Delete My Record" gated on
#       REMOVE_INFORMATION.
#   bcf_*_by_checking_off_the_box_...  declaration checkbox -> checked
#   bcf_*_write_your_name_below  (required) -> full name
# reCAPTCHA gates submit — filled to that point.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.thebridgecorp.com/opt-out/"

REQUEST_TYPES = ["Request Information", "Opt Out"]
DELETE_TYPE = "Delete My Record"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    full_name = " ".join(p for p in (SuperScraper.FIRST_NAME, SuperScraper.LAST_NAME) if p)
    request_types = list(REQUEST_TYPES)
    if SuperScraper.REMOVE_INFORMATION:
        request_types.append(DELETE_TYPE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(7)

        residency = await tab.find(xpath="//select[contains(@id,'_i_am_a')]", raise_exc=False)
        if residency:
            await residency.execute_script(
                "this.value='California Resident';"
                "this.dispatchEvent(new Event('change',{bubbles:true}));"
            )
        else:
            print(f"{super_scraper.OOPS} 'State of Residency' select not found")

        email = await tab.find(xpath="//input[contains(@id,'_email') and @type='email']", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)

        ad_id = await tab.find(xpath="//textarea[contains(@id,'_enter_advertising_id_')]", raise_exc=False)
        if ad_id and SuperScraper.ADVERTISING_ID:
            await ad_id.type_text(SuperScraper.ADVERTISING_ID)

        for value in request_types:
            box = await tab.find(
                xpath=f"//input[@type='checkbox' and @value={value!r}]", raise_exc=False
            )
            if box:
                await box.click()
                await asyncio.sleep(0.2)
            else:
                print(f"{super_scraper.OOPS} request-type checkbox {value!r} not found")

        declaration = await tab.find(
            xpath="//input[@type='checkbox' and contains(@id,'_by_checking_off')]", raise_exc=False
        )
        if declaration:
            await declaration.click()
        else:
            print(f"{super_scraper.OOPS} declaration checkbox not found")

        name_field = await tab.find(xpath="//input[contains(@id,'_write_your_name_below')]", raise_exc=False)
        if name_field:
            await name_field.type_text(full_name)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/thebridgecorp_dry_run.png", beyond_viewport=True)
        print(f"{request_types} filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


asyncio.run(main())

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
#       (Access), "Opt Out", "Delete My Record" — only the ones chosen
#       by SuperScraper.rights_to_exercise(RIGHT_MAP) are ticked.
#   bcf_*_by_checking_off_the_box_...  declaration checkbox -> checked
#   bcf_*_write_your_name_below  (required) -> full name
# reCAPTCHA gates submit — filled to that point.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.thebridgecorp.com/opt-out/"

# Right -> checkbox value of the "type of request" group (one combined submission).
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Request Information",
    Right.RIGHT_TO_OPT_OUT: "Opt Out",
    Right.RIGHT_TO_DELETE: "Delete My Record",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    full_name = " ".join(p for p in (SuperScraper.FIRST_NAME, SuperScraper.LAST_NAME) if p)
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    request_types = [RIGHT_MAP[right] for right in rights]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(7)

        residency = await tab.find(xpath="//select[contains(@id,'_i_am_a')]", raise_exc=False)
        if residency:
            # CCPA-oriented "I am a" select on this shared HubSpot template.
            # "California Resident" is selected for any privacy-law state (whose
            # law grants CCPA-equivalent rights); a no-law state keeps the default.
            if SuperScraper.state_has_privacy_law(SuperScraper.STATE):
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
        await SuperScraper.screenshot(tab, "dry_run")
        print(f"{request_types} filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


asyncio.run(main())

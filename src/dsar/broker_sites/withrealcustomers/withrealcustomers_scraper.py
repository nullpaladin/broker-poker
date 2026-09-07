# withrealcustomers.com ("Connect") — /index.php/opt-out/ embeds a HubSpot form
# via the standard src-less `<iframe class="hs-form-iframe">`. pydoll drives it
# by calling `.find()` on the iframe *WebElement* (tab.find / get_frame both
# fail on a src-less HubSpot frame).
#
# Fields (all inside the iframe):
#   i_am_a  <select>  "State of Residency" — options are only "California
#           Resident" / "Non-California Resident". Per the README note for this
#           site ("use 'California Resident' as long as you have state-level
#           CDPA laws"), and because the .env persona's state (Minnesota) has an
#           equivalent consumer-privacy statute, "California Resident" is
#           selected so the form does not route the request into its lesser
#           non-CA path.
#   email (required)
#   enter_advertising_id_  textarea (optional) — filled with the MAID
#   please_select_the_type_of_request_..._  checkbox group (multi-select, one
#           combined submission): "Request Information" (Access) + "Opt Out"
#           unconditionally; "Delete My Record" gated on REMOVE_INFORMATION.
#   Checking a request type reveals an optional identity block — firstname,
#           middle_name, lastname, 0-2/city, 0-2/state, 0-2/zip, birth_month,
#           birth_year — all filled from the persona. Two file-upload fields
#           (license front/back, selfie) are also revealed but are OPTIONAL
#           (only email + the name declaration are `required`) and are skipped:
#           a synthetic persona has no ID document or selfie to upload.
#   by_checking_off_the_box_...  perjury declaration checkbox — checked per this
#           repo's precedent on attestation boxes.
#   write_your_name_below (required) — full name
# No CAPTCHA (HubSpot's spam protection is invisible).
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://support.withrealcustomers.com/index.php/opt-out/"

RIGHT_MAP = {
    "access": ["Request Information"],
    "opt_out_sale_share": ["Opt Out"],
    "delete": ["Delete My Record"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    full_name = " ".join(p for p in (SuperScraper.FIRST_NAME, SuperScraper.LAST_NAME) if p)
    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    request_types = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(9)

        iframe = await tab.find(class_name="hs-form-iframe", raise_exc=False)
        if not iframe:
            print(f"{super_scraper.OOPS} HubSpot form iframe not found")
            return

        residency = await iframe.find(xpath="//select[@name='i_am_a']", raise_exc=False)
        if residency:
            await residency.execute_script(
                "this.value='California Resident';"
                "this.dispatchEvent(new Event('change',{bubbles:true}));"
            )
        else:
            print(f"{super_scraper.OOPS} 'State of Residency' select not found")

        email = await iframe.find(xpath="//input[@name='email']", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)

        ad_id = await iframe.find(xpath="//textarea[@name='enter_advertising_id_']", raise_exc=False)
        if ad_id and SuperScraper.ADVERTISING_ID:
            await ad_id.type_text(SuperScraper.ADVERTISING_ID)

        for value in request_types:
            box = await iframe.find(
                xpath=f"//input[@type='checkbox' and @value={value!r}]", raise_exc=False
            )
            if box:
                await box.click()
                await asyncio.sleep(0.3)
            else:
                print(f"{super_scraper.OOPS} request-type checkbox {value!r} not found")

        # Checking a request type reveals an optional identity block.
        await asyncio.sleep(1.5)
        dob = (SuperScraper.DATE_OF_BIRTH or "").split("/")  # DD/MM/YYYY
        identity = {
            "firstname": SuperScraper.FIRST_NAME,
            "lastname": SuperScraper.LAST_NAME,
            "0-2/city": SuperScraper.CITY,
            "0-2/state": SuperScraper.STATE,
            "0-2/zip": SuperScraper.ZIP_CODE,
            "birth_month": dob[1] if len(dob) == 3 else "",
            "birth_year": dob[2] if len(dob) == 3 else "",
        }
        for fname, val in identity.items():
            if not val:
                continue
            el = await iframe.find(xpath=f"//input[@name={fname!r}]", raise_exc=False)
            if el:
                await el.type_text(val)
                await asyncio.sleep(0.15)

        declaration = await iframe.find(
            xpath="//input[@type='checkbox' and starts-with(@name,'by_checking_off')]", raise_exc=False
        )
        if declaration:
            await declaration.click()
        else:
            print(f"{super_scraper.OOPS} declaration checkbox not found")

        name_field = await iframe.find(xpath="//input[@name='write_your_name_below']", raise_exc=False)
        if name_field:
            await name_field.type_text(full_name)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/withrealcustomers_dry_run.png", beyond_viewport=True)
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {request_types} for {full_name} <{SuperScraper.EMAIL}>")
            return

        submit = await iframe.find(xpath="//input[@type='submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(f"Submitted {request_types} for {full_name}")


asyncio.run(main())

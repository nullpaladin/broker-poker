# postpilot.com — /rights-request-form embeds a ClickUp form
# (forms.clickup.com/14183078/f/dgun6-8690/XIZIQMFCDPWFOG8PKO); this navigates
# straight to it. ClickUp Forms is a new platform for this repo — fields use
# stable `cu-form-control-N` ids and `cu3-checkbox-N-input` ids.
#
#   cu3-checkbox-1  "Right to Access / Portability"          -> Access
#   cu3-checkbox-2  "Right to Know"                          -> (with Access)
#   cu3-checkbox-3  "Right to Correction"                    -> skipped
#   cu3-checkbox-4  "Right to Deletion"                      -> gated on REMOVE_INFORMATION
#   cu3-checkbox-5  "Right to Opt Out of Sales"              -> Opt-Out
#   cu-form-control-6  First and Last Name (required)
#   cu-form-control-7  Company Name (required) -> COMPANY_NAME
#   cu-form-control-8  Job Title -> JOB_TITLE
#   cu-form-control-9  Email (required)
#   cu-form-control-10 Phone Number -> PHONE_NUMBER
#   cu-form-control-11 Street Address (required)
#   cu-form-control-12 Apartment/Suite -> ADDRESS_LINE_TWO
#   cu-form-control-13 City (required)
#   cu-form-control-14 State (required)
#   cu-form-control-15 Zip Code (required)
#   "Please identify your relationship with PostPilot" — a required ClickUp
#       dropdown -> "Consumer".
#   file upload left blank. No CAPTCHA observed.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://forms.clickup.com/14183078/f/dgun6-8690/XIZIQMFCDPWFOG8PKO"

RIGHT_CHECKBOXES = ["cu3-checkbox-1-input", "cu3-checkbox-2-input", "cu3-checkbox-5-input"]
DELETE_CHECKBOX = "cu3-checkbox-4-input"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    full_name = " ".join(p for p in (SuperScraper.FIRST_NAME, SuperScraper.LAST_NAME) if p)
    boxes = list(RIGHT_CHECKBOXES)
    if SuperScraper.REMOVE_INFORMATION:
        boxes.append(DELETE_CHECKBOX)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(8)

        # Required "relationship with PostPilot" ClickUp dropdown -> Consumer
        toggle = await tab.find(
            xpath="//div[@data-test='select__dropdown__toggle']", raise_exc=False
        )
        if toggle:
            await toggle.click()
            await asyncio.sleep(0.8)
            opt = await tab.find(
                xpath="//*[(@role='option' or contains(@class,'option') or self::li)"
                " and normalize-space()='Consumer']",
                raise_exc=False,
            )
            if opt:
                await opt.click()
            else:
                print(f"{super_scraper.OOPS} relationship option 'Consumer' not found")
            await asyncio.sleep(0.4)
        else:
            print(f"{super_scraper.OOPS} relationship dropdown toggle not found")

        for box_id in boxes:
            el = await tab.find(id=box_id, raise_exc=False)
            if not el:
                el = await tab.find(xpath=f"//label[@for={box_id!r}]", raise_exc=False)
            if el:
                await el.click()
                await asyncio.sleep(0.2)
            else:
                print(f"{super_scraper.OOPS} checkbox '{box_id}' not found")

        fields = {
            "cu-form-control-6": full_name,
            "cu-form-control-7": SuperScraper.COMPANY_NAME,
            "cu-form-control-8": SuperScraper.JOB_TITLE,
            "cu-form-control-9": SuperScraper.EMAIL,
            "cu-form-control-10": SuperScraper.PHONE_NUMBER,
            "cu-form-control-11": SuperScraper.ADDRESS,
            "cu-form-control-12": SuperScraper.ADDRESS_LINE_TWO,
            "cu-form-control-13": SuperScraper.CITY,
            "cu-form-control-14": SuperScraper.STATE,
            "cu-form-control-15": SuperScraper.ZIP_CODE,
        }
        for field_id, val in fields.items():
            if not val:
                continue
            el = await tab.find(id=field_id, raise_exc=False)
            if el:
                await el.type_text(val)
                await asyncio.sleep(0.15)
            else:
                print(f"{super_scraper.OOPS} field '{field_id}' not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/postpilot_dry_run.png", beyond_viewport=True)
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit rights request for {full_name} <{SuperScraper.EMAIL}>")
            return

        submit = await tab.find(xpath="//button[normalize-space()='Submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(f"Submitted rights request for {full_name}")


asyncio.run(main())

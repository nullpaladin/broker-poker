# postpilot.com — /rights-request-form embeds a ClickUp form
# (forms.clickup.com/14183078/f/dgun6-8690/XIZIQMFCDPWFOG8PKO); this navigates
# straight to it. ClickUp Forms is a new platform for this repo — fields use
# stable `cu-form-control-N` ids and `cu3-checkbox-N-input` ids.
#
# Which rights run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP);
# all selected rights go in ONE submission.
#
# Page elements:
#   cu3-checkbox-1  "Right to Access / Portability"          -> Access
#   cu3-checkbox-2  "Right to Know"
#   cu3-checkbox-3  "Right to Correction"                    -> not automated
#   cu3-checkbox-4  "Right to Deletion"                      -> Delete
#   cu3-checkbox-5  "Right to Opt Out of Sales"
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

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://forms.clickup.com/14183078/f/dgun6-8690/XIZIQMFCDPWFOG8PKO"

CHECK_ACCESS_PORTABILITY = "cu3-checkbox-1-input"  # "Right to Access / Portability"
CHECK_KNOW = "cu3-checkbox-2-input"  # "Right to Know"
CHECK_DELETION = "cu3-checkbox-4-input"  # "Right to Deletion"

# MANUAL REVIEW: the old code clicked checkbox-2 ("Right to Know") for opt-out and
# checkbox-5 ("Right to Opt Out of Sales") only under the dropped "correct" right.
# Kept as-is; verify against the live form.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [CHECK_ACCESS_PORTABILITY],
    Right.RIGHT_TO_OPT_OUT: [CHECK_KNOW],
    Right.RIGHT_TO_DELETE: [CHECK_DELETION],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every checkbox in the rights group, as displayed -> the Right it maps to (None = not automated). "Right to Know" is
# mapped to RIGHT_TO_OPT_OUT because RIGHT_MAP currently does so (see its MANUAL REVIEW note); "Right to Opt Out of
# Sales" is not used by RIGHT_MAP.
PAGE_RIGHTS = {
    "Right to Access / Portability": Right.RIGHT_TO_ACCESS,
    "Right to Know": Right.RIGHT_TO_OPT_OUT,
    "Right to Correction": None,
    "Right to Deletion": Right.RIGHT_TO_DELETE,
    "Right to Opt Out of Sales": None,
}
RIGHTS_OPTIONS_CSS = "label[for^='cu3-checkbox-']"

FIELD_XPATHS = {
    "Full name": "//*[@id='cu-form-control-6']",
    "Company name": "//*[@id='cu-form-control-7']",
    "Email": "//*[@id='cu-form-control-9']",
    "Street address": "//*[@id='cu-form-control-11']",
    "City": "//*[@id='cu-form-control-13']",
    "State": "//*[@id='cu-form-control-14']",
    "Zip": "//*[@id='cu-form-control-15']",
}


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    options = SuperScraper.build_chromium_options()

    full_name = " ".join(p for p in (SuperScraper.FIRST_NAME, SuperScraper.LAST_NAME) if p)
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    boxes = [entry for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(8)

        if SuperScraper.HEALTH_CHECK:
            offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
            SuperScraper.audit_rights(offered, PAGE_RIGHTS)

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

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit rights request for {full_name} <{SuperScraper.EMAIL}>")
            return

        submit = await tab.find(xpath="//button[normalize-space()='Submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(f"Submitted rights request for {SuperScraper.EMAIL} — confirm in the browser.")
        else:
            print(f"{super_scraper.OOPS} Submit button not found")


asyncio.run(main())

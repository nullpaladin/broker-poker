# speedeondata.com — optout.speedeondata.com is a simple custom form. Only
# Opt-Out/Delete/Sensitive-Data exist (no Right to Access anywhere on the
# site — confirmed by prior manual investigation). The "Opt-out" and "Sensitive
# Data" (limit use of religious-affiliation/ethnicity/ailment data) checkboxes
# both belong to RIGHT_TO_OPT_OUT; "Deletion" is RIGHT_TO_DELETE. At least one
# of the three is required by the form. Which run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP); all ticked boxes go in one form.
# Page elements:
#   #optOut / #sensitiveData / #deletion   request-type checkboxes
#   firstName, lastName, email, phone, address1, address2, city, zip   text inputs (by name)
#   button.dropdown-toggle                 State dropdown toggle
#   button[role=menuitem][title=<State>]   State option
# State is a Bootstrap
# dropdown of `<button role="menuitem" title="<Full Name>" value="<Abbrev>">`
# items rather than a native <select> — matched by `title` and clicked
# directly (items exist in the DOM whether or not the toggle button has been
# opened). reCAPTCHA v2 checkbox present — **CAPTCHA solution required**.
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://optout.speedeondata.com/"

# Right -> ids of the checkbox(es) the form uses for it.
OPT_OUT_CHECKBOX = "optOut"  # "Opt-out"
SENSITIVE_DATA_CHECKBOX = "sensitiveData"  # "Sensitive Data"
DELETION_CHECKBOX = "deletion"  # "Deletion"
RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: [OPT_OUT_CHECKBOX, SENSITIVE_DATA_CHECKBOX],
    Right.RIGHT_TO_DELETE: [DELETION_CHECKBOX],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every checkbox on the form, as displayed -> the Right it maps to.
PAGE_RIGHTS = {
    "Opt-out": Right.RIGHT_TO_OPT_OUT,
    "Sensitive Data": Right.RIGHT_TO_OPT_OUT,
    "Deletion": Right.RIGHT_TO_DELETE,
}
RIGHTS_OPTIONS_CSS = (
    "label:has(#optOut), label:has(#sensitiveData), label:has(#deletion), "
    "label[for='optOut'], label[for='sensitiveData'], label[for='deletion']"
)  # built from the three recorded checkbox ids

FIELD_XPATHS = {
    "First name": "//*[@name='firstName']",
    "Last name": "//*[@name='lastName']",
    "Email": "//*[@name='email']",
    "Phone": "//*[@name='phone']",
    "Address": "//*[@name='address1']",
    "City": "//*[@name='city']",
    "Zip": "//*[@name='zip']",
}


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        if SuperScraper.HEALTH_CHECK:
            offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
            SuperScraper.audit_rights(offered, PAGE_RIGHTS)

        for right in rights:
            for checkbox_id in RIGHT_MAP[right]:
                checkbox = await tab.find(id=checkbox_id, raise_exc=False)
                if checkbox:
                    await checkbox.click()
                else:
                    print(f"{super_scraper.OOPS} checkbox '{checkbox_id}' not found")

        fields = {
            "firstName": SuperScraper.FIRST_NAME,
            "lastName": SuperScraper.LAST_NAME,
            "email": SuperScraper.EMAIL,
            "phone": SuperScraper.PHONE_NUMBER,
            "address1": SuperScraper.ADDRESS,
            "address2": SuperScraper.ADDRESS_LINE_TWO,
            "city": SuperScraper.CITY,
            "zip": SuperScraper.ZIP_CODE,
        }
        for name, value in fields.items():
            if not value:
                continue
            field = await tab.find(name=name, raise_exc=False)
            if field:
                await field.type_text(value)
            else:
                print(f"{super_scraper.OOPS} field '{name}' not found")

        state_toggle = await tab.find(xpath="//button[contains(@class,'dropdown-toggle')]", raise_exc=False)
        if state_toggle:
            await state_toggle.click()
            await asyncio.sleep(0.5)
        else:
            print(f"{super_scraper.OOPS} State dropdown toggle not found")

        state_button = await tab.find(
            xpath=f"//button[@role='menuitem' and @title={SuperScraper.STATE!r}]", raise_exc=False
        )
        if state_button:
            await state_button.click()
        else:
            print(f"{super_scraper.OOPS} State option '{SuperScraper.STATE}' not found")

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
        print(
            "\nRequest filled but NOT submitted — a reCAPTCHA v2 checkbox requires a manual "
            "solve before submitting."
        )


asyncio.run(main())

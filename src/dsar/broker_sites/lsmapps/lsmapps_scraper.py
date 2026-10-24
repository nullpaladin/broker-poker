# lsmapps.com — /opt-out. Territory (US/EU/Other) gates the available
# "Which right do you wish to exercise?" options — for US: Know/Access,
# Deletion, Portability, Non-Discrimination, Rectification, Limit Sensitive
# PI Use, Opt-Out of Sale. Single-select, one submission per right;
# Portability/Non-Discrimination/Rectification/Limit Sensitive skipped as
# auxiliary. "Are you a user of our App?" answered "No" (generic consumer
# persona, not an LSM Apps user). There's a `name="website"` text field
# with `tabIndex="-1"` (removed from the natural tab order — a classic
# honeypot signal despite the generic-sounding label) — deliberately left
# BLANK. A custom text/image CAPTCHA ("Security check — enter the code
# shown below") gates submission — **CAPTCHA solution required**; the form
# is filled completely and left there regardless. Which rights run is decided only
# by rights_to_exercise(RIGHT_MAP).
#
# Page elements:
#   #fullName / #email / #phoneNumber   Full name / Email / Phone (sent as "+1 <number>")
#   #appUser        "Are you a user of our App?" <select> -> "No"
#   #territory      Territory <select> -> "US"
#   #privacyRight   "Which right do you wish to exercise?" <select> -> see RIGHT_MAP
#   #confirmation   Confirmation checkbox
#   name=website    honeypot (tabIndex=-1) -> left blank
#   security check code input (text/image CAPTCHA) -> manual entry
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://lsmapps.com/opt-out"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Right to Know or Access the Personal Information",
    Right.RIGHT_TO_OPT_OUT: "Right to Opt-Out of Sale of Personal Information",
    Right.RIGHT_TO_DELETE: "Right to Deletion of the Personal Information",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = "#privacyRight option"  # options depend on the Territory chosen first

FIELD_XPATHS = {
    "Full name": "//*[@id='fullName']",
    "Email": "//*[@id='email']",
    "Phone": "//*[@id='phoneNumber']",
    "App user": "//*[@id='appUser']",
    "Territory": "//*[@id='territory']",
    "Right": "//*[@id='privacyRight']",
}


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    name_field = await tab.find(id="fullName", raise_exc=False)
    if name_field:
        await name_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")

    email_field = await tab.find(id="email", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    phone_field = await tab.find(id="phoneNumber", raise_exc=False)
    if phone_field and SuperScraper.PHONE_NUMBER:
        await phone_field.type_text(f"+1 {SuperScraper.PHONE_NUMBER}")

    app_user_select = await tab.find(id="appUser", raise_exc=False)
    if app_user_select:
        await js_utils.select_native_option(app_user_select, text="No")

    territory_select = await tab.find(id="territory", raise_exc=False)
    if territory_select:
        await js_utils.select_native_option(territory_select, text="US")
        await asyncio.sleep(0.5)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    right_select = await tab.find(id="privacyRight", raise_exc=False)
    if right_select:
        await js_utils.select_native_option(right_select, text=right)

    confirmation = await tab.find(id="confirmation", raise_exc=False)
    if confirmation:
        await confirmation.click()

    label = "".join(c if c.isalnum() else "_" for c in right.lower())[:40].strip("_")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(
        f"\n'{right}' request filled but NOT submitted — a text/image security check "
        "code is required and requires manual entry."
    )


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, RIGHT_MAP[right], super_scraper)


asyncio.run(main())

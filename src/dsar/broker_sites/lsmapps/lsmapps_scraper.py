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
# is filled completely and left there regardless. Exercises Access and
# Opt-Out of Sale unconditionally; Deletion gated on REMOVE_INFORMATION.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://lsmapps.com/opt-out"

RIGHT_MAP = {
    "access": ["Right to Know or Access the Personal Information"],
    "opt_out_sale_share": ["Right to Opt-Out of Sale of Personal Information"],
    "delete": ["Right to Deletion of the Personal Information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


def _select_by_text(text):
    return (
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].text==={text!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


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
        await app_user_select.execute_script(_select_by_text("No"))

    territory_select = await tab.find(id="territory", raise_exc=False)
    if territory_select:
        await territory_select.execute_script(_select_by_text("US"))
        await asyncio.sleep(0.5)

    right_select = await tab.find(id="privacyRight", raise_exc=False)
    if right_select:
        await right_select.execute_script(_select_by_text(right))

    confirmation = await tab.find(id="confirmation", raise_exc=False)
    if confirmation:
        await confirmation.click()

    label = "".join(c if c.isalnum() else "_" for c in right.lower())[:40].strip("_")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/lsmapps_dry_run_{label}.png")
    print(
        f"\n'{right}' request filled but NOT submitted — a text/image security check "
        "code is required and requires manual entry."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    rights = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, super_scraper)


asyncio.run(main())

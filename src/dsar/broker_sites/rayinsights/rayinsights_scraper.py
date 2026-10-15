# rayinsights.com — "RayCDP Consumer Choice Portal" links out to separate
# Ninja Forms (WordPress) pages per right: Opt-out/Delete/Correct share a
# single combined multi-select checkbox form (one submission covers
# whichever boxes are checked); Data Request (Access) is its own separate
# form. A third "Consumer Appeal Request" (appealing a prior denial) and a
# "Canadian Resident Delete Request" (not applicable — US persona) exist
# but aren't in scope here.
#
# Ninja Forms quirk: each field's numeric `nf-field-N` id is different per
# form instance/page load, but the plain-text fields keep a stable `name`
# attribute (email/fname/lname/address/city/zip/phone) — targeted by name,
# not id. The State `<select>` and the "I affirm..." attestation checkbox
# have no descriptive name (just `nf-field-<N>`), so they're targeted
# structurally: the page's only `<select>`, and the checkbox whose sibling
# label contains the attestation text. A honeypot text input named
# `nf-field-hp` is present on both forms — left untouched. Required
# attestation checkbox ("I affirm I am the consumer...") is checked, since
# it's true for a matching persona. reCAPTCHA v2 — **CAPTCHA solution
# required**. Which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP): Opt out of marketing and Delete my
# data are checked in the same combined submission; Access (Data Request) is
# its own form. Correct my data is left unchecked (not automated).
#
# Page elements:
#   checkbox value="optout" / value="delete"   Opt out / Delete my data (combined form)
#   input[name=email|fname|lname|address|city|zip|phone]   Email / First / Last name /
#                                              Address / City / ZIP / Phone
#   the page's only <select>                   State
#   checkbox "I affirm I am the consumer..."  Attestation (required)
#   reCAPTCHA v2 checkbox (manual)
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

OPT_OUT_URL = "https://www.rayinsights.com/ray-cdp-opt-out-and-delete-request/"
DATA_REQUEST_URL = "https://www.rayinsights.com/raycdp-data-request/"

# Right -> checkbox values on the combined opt-out/delete form; access is the separate
# Data Request form (DATA_REQUEST_URL), so it has no checkbox.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [],
    Right.RIGHT_TO_OPT_OUT: ["optout"],
    Right.RIGHT_TO_DELETE: ["delete"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _fill_common_fields(tab, super_scraper):
    fields = {
        "email": SuperScraper.EMAIL,
        "fname": SuperScraper.FIRST_NAME,
        "lname": SuperScraper.LAST_NAME,
        "address": SuperScraper.ADDRESS,
        "city": SuperScraper.CITY,
        "zip": SuperScraper.ZIP_CODE,
        "phone": SuperScraper.PHONE_NUMBER,
    }
    for name, value in fields.items():
        if not value:
            continue
        field = await tab.find(name=name, raise_exc=False)
        if field:
            await field.type_text(value)
        else:
            print(f"{super_scraper.OOPS} field '{name}' not found")

    state_select = await tab.find(tag_name="select", raise_exc=False)
    if state_select:
        await js_utils.select_native_option(state_select, text=SuperScraper.STATE, dispatch=("change",))
    else:
        print(f"{super_scraper.OOPS} State select not found")

    affirm_checkbox = await tab.find(
        xpath="//label[contains(normalize-space(),'I affirm I am the consumer')]/preceding-sibling::input[@type='checkbox'] | "
        "//input[@type='checkbox']/following-sibling::label[contains(normalize-space(),'I affirm I am the consumer')]/parent::*/input[@type='checkbox']",
        raise_exc=False,
    )
    if not affirm_checkbox:
        affirm_checkbox = await tab.find(
            xpath="//*[contains(normalize-space(),'I affirm I am the consumer')]/ancestor::div[contains(@class,'nf-field-container')]//input[@type='checkbox']",
            raise_exc=False,
        )
    if affirm_checkbox:
        await affirm_checkbox.click()
    else:
        print(f"{super_scraper.OOPS} affirmation checkbox not found")


async def submit_opt_out_delete(super_scraper, tab, checkbox_values):
    await tab.go_to(OPT_OUT_URL)
    await asyncio.sleep(5)

    for value in checkbox_values:
        checkbox = await tab.find(xpath=f"//input[@type='checkbox' and @value='{value}']", raise_exc=False)
        if checkbox:
            await checkbox.click()
        else:
            print(f"{super_scraper.OOPS} '{value}' checkbox not found")

    await _fill_common_fields(tab, super_scraper)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "dry_run_opt_out_delete")


async def submit_data_request(super_scraper, tab):
    await tab.go_to(DATA_REQUEST_URL)
    await asyncio.sleep(5)

    await _fill_common_fields(tab, super_scraper)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "dry_run_data_request")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    checkbox_values = [cb for right in rights for cb in RIGHT_MAP[right]]

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        if checkbox_values:
            await submit_opt_out_delete(super_scraper, tab, checkbox_values)
        if Right.RIGHT_TO_ACCESS in rights:
            await submit_data_request(super_scraper, tab)
        print(
            "\nRequests filled but NOT submitted — a reCAPTCHA v2 checkbox is present "
            "on each form and requires a manual solve."
        )


asyncio.run(main())

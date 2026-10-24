# 01advertising.com — the /legal/dsar/ page is just a static landing page
# ("Submit a Privacy Request" link) that hands off to a generic Termly DSAR
# form at app.termly.io/dsar/<uuid>, prefilled with the "Website" field
# ("01Advertising Inc."). This is Termly's standard template (single
# react-select combobox for law, then a single-select radio group of
# specific actions revealed after picking a law) — likely reused verbatim by
# other Termly customers, so the same field names (name, email, identity_type,
# action, detail.content, __doNotSubmit__.*) should transfer if this pattern
# is seen again. Law defaulted to CCPA. Action is single-select (one
# submission per right): request_to_know (Access), request_to_opt_out and
# request_to_delete; which run is decided only by rights_to_exercise. All three
# "I confirm that" checkboxes (perjury declaration, understand deletion is
# irreversible, understand email validation is required) are checked
# regardless of action — the form doesn't conditionally require them per
# action, and this repo's precedent is to just check attestation boxes. No
# captcha observed. Submission requires clicking an emailed validation link
# afterward (not a pre-submission magic-link gate) — that's a normal
# post-submission step, not one this scraper needs to wait on.
#
# Page elements:
#   input[name=name]                 Full name (first + last typed together)
#   input[name=email]                Email
#   input[role=combobox]             Law selector (react-select) -> "CCPA"
#   input[name=action][value=...]    Action radio group (request_to_know /
#                                    request_to_opt_out / request_to_delete)
#   input[name^=__doNotSubmit__]     "I confirm that" attestation checkboxes
#   "SUBMIT" button                  Submit
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://app.termly.io/dsar/d1321341-0e82-4d8c-afaf-c4940d46c171"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "request_to_know",
    Right.RIGHT_TO_OPT_OUT: "request_to_opt_out",
    Right.RIGHT_TO_DELETE: "request_to_delete",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = "label:has(input[name='action'])"  # action radios, revealed after the law is picked

NAME_XPATH = "//input[@name='name']"
EMAIL_XPATH = "//input[@name='email']"


async def submit_request(tab, right, action, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(4)

    name_field = await tab.find(xpath="//input[@name='name']", raise_exc=False)
    email_field = await tab.find(xpath="//input[@name='email']", raise_exc=False)
    if name_field:
        await name_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    combo = await tab.find(xpath="//input[@role='combobox']", raise_exc=False)
    if combo:
        await combo.click()
        await asyncio.sleep(0.5)
        option = await tab.find(text="CCPA", raise_exc=False)
        if option:
            await option.click()
            await asyncio.sleep(0.5)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    radio = await tab.find(xpath=f"//input[@name='action' and @value='{action}']", raise_exc=False)
    if radio:
        await radio.click()

    await js_utils.check_termly_attestations(tab)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, {"Full name": NAME_XPATH, "Email": EMAIL_XPATH})

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        return

    submit = await tab.find(text="SUBMIT", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(2)
        print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")
    else:
        print(f"{super_scraper.OOPS} SUBMIT button not found for {right.name}")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())

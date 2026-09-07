# 01advertising.com — the /legal/dsar/ page is just a static landing page
# ("Submit a Privacy Request" link) that hands off to a generic Termly DSAR
# form at app.termly.io/dsar/<uuid>, prefilled with the "Website" field
# ("01Advertising Inc."). This is Termly's standard template (single
# react-select combobox for law, then a single-select radio group of
# specific actions revealed after picking a law) — likely reused verbatim by
# other Termly customers, so the same field names (name, email, identity_type,
# action, detail.content, __doNotSubmit__.*) should transfer if this pattern
# is seen again. Law defaulted to CCPA. Action is single-select (one
# submission per right): request_to_know (Access) and request_to_opt_out
# unconditionally; request_to_delete gated on REMOVE_INFORMATION. All three
# "I confirm that" checkboxes (perjury declaration, understand deletion is
# irreversible, understand email validation is required) are checked
# regardless of action — the form doesn't conditionally require them per
# action, and this repo's precedent is to just check attestation boxes. No
# captcha observed. Submission requires clicking an emailed validation link
# afterward (not a pre-submission magic-link gate) — that's a normal
# post-submission step, not one this scraper needs to wait on.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://app.termly.io/dsar/d1321341-0e82-4d8c-afaf-c4940d46c171"

ACTIONS = ["request_to_know", "request_to_opt_out"]
DELETE_ACTION = "request_to_delete"


async def _check_confirm_boxes(tab):
    await tab.execute_script(
        "document.querySelectorAll('input[name^=\"__doNotSubmit__\"]').forEach(function(cb){"
        "  cb.checked=true; cb.dispatchEvent(new Event('click', {bubbles:true}));"
        "  cb.dispatchEvent(new Event('change', {bubbles:true}));"
        "});"
    )


async def submit_request(tab, action, super_scraper):
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

    radio = await tab.find(xpath=f"//input[@name='action' and @value='{action}']", raise_exc=False)
    if radio:
        await radio.click()

    await _check_confirm_boxes(tab)

    label = action.replace("request_to_", "")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit {label} request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/01advertising_dry_run_{label}.png")
        return

    submit = await tab.find(text="SUBMIT", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(2)
        print(f"Submitted {label} request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} SUBMIT button not found for {label}")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    actions = list(ACTIONS)
    if SuperScraper.REMOVE_INFORMATION:
        actions.append(DELETE_ACTION)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for action in actions:
            await submit_request(tab, action, super_scraper)


asyncio.run(main())

# atom.com — generic Termly DSAR form (app.termly.io), the same template
# documented in more detail at 01advertising.com's scraper: Name/Email, an
# identity_type radio (left at its "personal" default), a law combobox
# (defaulted CCPA), then a single-select `action` radio group that is only
# added to the DOM after a law is picked (an earlier version of this
# scraper, written while app.termly.io was showing a Cloudflare bot-check
# during dev testing, missed this and fell back to a free-text detail.content
# description instead — rewritten now that the block cleared and the actual
# action radios could be confirmed). Rights the form exposes:
# request_to_know (Access), request_to_opt_out (Opt-out), request_to_delete (Delete);
# which run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). All three "I confirm that" attestation checkboxes are
# checked regardless of action. No captcha observed on a clean load.
#
# Page elements (keep this list current):
#   input[name=name]            Full name (First + Last)
#   input[name=email]           Email
#   input[role=combobox]        Law chooser -> "CCPA"
#   input[name=action]          Action radio group (value = request_to_know / _opt_out / _delete)
#   "I confirm that" checkboxes  Termly attestations (checked via js_utils.check_termly_attestations)
#   "SUBMIT" button
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://app.termly.io/dsar/62c9d984-30c8-4068-ad84-749ed5ecb452"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["request_to_know"],
    Right.RIGHT_TO_OPT_OUT: ["request_to_opt_out"],
    Right.RIGHT_TO_DELETE: ["request_to_delete"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, action, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

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

    await js_utils.check_termly_attestations(tab)

    label = action.replace("request_to_", "")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    submit = await tab.find(text="SUBMIT", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(2)
        print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")
    else:
        print(f"{super_scraper.OOPS} SUBMIT button not found for {label}")


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
            for action in RIGHT_MAP[right]:
                await submit_request(tab, right, action, super_scraper)


asyncio.run(main())

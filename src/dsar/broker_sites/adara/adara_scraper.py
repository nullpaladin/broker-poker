# adara.com — merged into sojern.com; the DSAR form now lives at privacy.sojern.com
# (embedded via iframe on adara's own /privacy/opt-out-data page). Server-rendered POST
# form. id_type is single-select (cookie/mobile/email/ip) — email is used since it is
# always available. Rights the form exposes: Export (Access), Opt Out and Delete; which
# run is decided only by rights_to_exercise. Cloudflare Turnstile checkbox widget present and does
# NOT auto-resolve here (unlike jmr-media.com) — requires a manual solve in live mode
# before the submit buttons will actually succeed server-side.
#
# Page elements:
#   input[name=id_type][value=email]    ID type radio -> "email"
#   #email-address                      Email address
#   input[type=submit][value=Export]    Export (Access) button
#   input[type=submit][value="Opt Out"] Opt Out button
#   input[type=submit][value=Delete]    Delete button
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://privacy.sojern.com/"

EMAIL_ID_TYPE_RADIO_XPATH = "//input[@name='id_type' and @value='email']"
EMAIL_ADDRESS_XPATH = "//input[@id='email-address']"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Export", "access")],
    Right.RIGHT_TO_OPT_OUT: [("Opt Out", "opt_out")],
    Right.RIGHT_TO_DELETE: [("Delete", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# No audit wired: the options are <input type=submit value=...> buttons, which read_option_labels
# (innerText/textContent) cannot read.


async def submit_request(tab, right, op_value, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(3)

    await super_scraper.click_item_by_xpath(tab=tab, xpath=EMAIL_ID_TYPE_RADIO_XPATH, sleep=1)
    await super_scraper.input_text_field(tab=tab, xpath=EMAIL_ADDRESS_XPATH, text=SuperScraper.EMAIL, sleep=1)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, {"Email address": EMAIL_ADDRESS_XPATH})

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' ({op_value}) for {SuperScraper.EMAIL}")
        await asyncio.sleep(2)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    await super_scraper.click_item_by_xpath(tab=tab, xpath=f"//input[@type='submit' and @value='{op_value}']", sleep=2)
    await asyncio.sleep(3)
    print(f"Submitted '{right.name}' ({op_value}) for {SuperScraper.EMAIL} — confirm in the browser.")


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
            for op_value, label in RIGHT_MAP[right]:
                await submit_request(tab, right, op_value, label, super_scraper)


asyncio.run(main())

# intentsify.io — app.intentsify.io/opt-out, a SayMine-style "data rights" SPA
# SPA form (identical template to 5x5coop.com elsewhere in this repo).
# Fields (ids are React-generated `field-_r_N_`, so target by name / position):
#   email (name="email"), proxyEmail (authorized-agent email — left blank),
#   firstName, lastName, a "Select country" <select>, and a single-select
#   "Select a reason" <select>.
# Reason options: "Do not sell or share my personal information", "Do not process
# my information for purposes of targeted advertising", "Request to delete/erase
# my personal information", "Request to correct/rectify my personal information",
# "Request to know/access my personal information". One submission per reason; which
# run is decided only by SuperScraper.rights_to_exercise (know/access -> ACCESS,
# do-not-sell + do-not-process-for-ads -> OPT_OUT, delete/erase -> DELETE);
# correct/rectify is not automated.
# Cloudflare Turnstile gates submission — form filled and left for a manual
# solve.  **CAPTCHA solution required**
#
# Page elements:
#   input[name=email]                 Email
#   input[name=firstName] / [name=lastName]   First / Last name
#   <select> with first option "Select country"   Country -> United States
#   <select> with first option "Select state"     Residence - State (2-letter value)
#   <select> with first option "Select a reason"  Reason (options in RIGHT_MAP)
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://app.intentsify.io/opt-out"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Request to know/access my personal information", "access")],
    Right.RIGHT_TO_OPT_OUT: [
        ("Do not sell or share my personal information", "opt_out_sale"),
        ("Do not process my information for purposes of targeted advertising", "opt_out_ads"),
    ],
    Right.RIGHT_TO_DELETE: [("Request to delete/erase my personal information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option in the "Select a reason" <select>, as displayed -> the Right it maps to (None = not automated).
PAGE_RIGHTS = {
    "Do not sell or share my personal information": Right.RIGHT_TO_OPT_OUT,
    "Do not process my information for purposes of targeted advertising": Right.RIGHT_TO_OPT_OUT,
    "Request to delete/erase my personal information": Right.RIGHT_TO_DELETE,
    "Request to correct/rectify my personal information": None,
    "Request to know/access my personal information": Right.RIGHT_TO_ACCESS,
}
RIGHTS_OPTIONS_CSS = ""  # TODO(health-check): the reason <select> has no name/id; capture a selector on a live run (no audit wired until then)

FIELD_XPATHS = {
    "Email": "//input[@name='email']",
    "First name": "//input[@name='firstName']",
    "Last name": "//input[@name='lastName']",
    "Country": "//select[option[normalize-space()='Select country']]",
    "State": "//select[option[normalize-space()='Select state']]",
    "Reason": "//select[option[normalize-space()='Select a reason']]",
}


async def _select_by_text(tab, select_xpath, text):
    el = await tab.find(xpath=select_xpath, raise_exc=False)
    if el:
        await js_utils.select_native_option(el, text=text, ci=True)


async def submit_request(tab, right, reason_text, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    for name, value in [
        ("email", SuperScraper.EMAIL),
        ("firstName", SuperScraper.FIRST_NAME),
        ("lastName", SuperScraper.LAST_NAME),
    ]:
        await super_scraper.input_text_field(
            tab=tab, xpath=f"//input[@name={name!r}]", text=value, sleep=0.2
        )

    # country <select> (no name attr — keyed by its first option's text)
    await _select_by_text(tab, "//select[option[normalize-space()='Select country']]", "United States")
    await asyncio.sleep(1)
    # "Residence - State" <select> only renders after Country is set; its options
    # are 2-letter abbreviations, so convert "Minnesota" -> "MN".
    state_abbr = SuperScraper.STATE_ABBREVIATED
    await _select_by_text(tab, "//select[option[normalize-space()='Select state']]", state_abbr)
    await _select_by_text(tab, "//select[option[normalize-space()='Select a reason']]", reason_text)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    time.sleep(0.5)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(
        f"'{reason_text}' filled but NOT submitted — a Cloudflare Turnstile must be "
        f"solved manually before submitting."
    )

    if not SuperScraper.DRY_RUN:
        print("Solve the Turnstile, click Submit, then press Enter once confirmed...")
        input()
        print(f"Submitted '{right.name}' ({reason_text}) for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for reason_text, label in RIGHT_MAP[right]:
                await submit_request(tab, right, reason_text, label, super_scraper)


asyncio.run(main())

# 5x5coop.com — privacy.5x5data.com/5x5/opt-out, a SayMine-style "data rights"
# SPA form (identical template to intentsify.io elsewhere in this repo).
# Fields (ids are React-generated `field-_r_N_`, so target by name / position):
#   email (name="email"), proxyEmail (authorized-agent email — left blank),
#   firstName, lastName, a "Select country" <select>, and a single-select
#   "Select a reason" <select>.
# Reason options: "Do not sell or share my personal information", "Do not process
# my information for purposes of targeted advertising", "Request to delete/erase
# my personal information", "Request to correct/rectify my personal information",
# "Request to know/access my personal information". One submission per reason; which
# run is decided only by SuperScraper.rights_to_exercise. correct/rectify is not
# automatable (None in PAGE_RIGHTS).
# Cloudflare Turnstile gates submission — form filled and left for a manual
# solve.  **CAPTCHA solution required**
#
# Page elements:
#   input[name=email]                     Email
#   input[name=firstName]                 First name
#   input[name=lastName]                  Last name
#   input[name=proxyEmail]                Authorized-agent email (left blank)
#   <select> with first option "Select country"  Country -> "United States"
#   <select> with first option "Select state"    "Residence - State" (2-letter abbreviation;
#                                         only renders after Country is set)
#   <select> with first option "Select a reason" Reason (see PAGE_RIGHTS)
#   Cloudflare Turnstile                  Manual solve, then the page's Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacy.5x5data.com/5x5/opt-out"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Request to know/access my personal information", "access")],
    Right.RIGHT_TO_OPT_OUT: [
        ("Do not sell or share my personal information", "opt_out_sale"),
        ("Do not process my information for purposes of targeted advertising", "opt_out_ads"),
    ],
    Right.RIGHT_TO_DELETE: [("Request to delete/erase my personal information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option in the "Select a reason" <select> -> Right (None = not automated).
PAGE_RIGHTS = {
    "Request to know/access my personal information": Right.RIGHT_TO_ACCESS,
    "Do not sell or share my personal information": Right.RIGHT_TO_OPT_OUT,
    "Do not process my information for purposes of targeted advertising": Right.RIGHT_TO_OPT_OUT,
    "Request to delete/erase my personal information": Right.RIGHT_TO_DELETE,
    "Request to correct/rectify my personal information": None,
}


async def _select_by_text(tab, select_xpath, text):
    el = await tab.find(xpath=select_xpath, raise_exc=False)
    if not el:
        return
    await el.execute_script(
        f"const w={text.lower()!r};"
        "const o=[...this.options].find(x=>x.text.trim().toLowerCase()===w);"
        "if(o){const s=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;"
        "s.call(this,o.value);"
        "this.dispatchEvent(new Event('input',{bubbles:true}));"
        "this.dispatchEvent(new Event('change',{bubbles:true}));}"
    )


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

    time.sleep(0.5)
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}_{label}")
    print(
        f"'{right.name}' ('{reason_text}') filled but NOT submitted — a Cloudflare Turnstile must be "
        f"solved manually before submitting."
    )

    if not SuperScraper.DRY_RUN:
        print("Solve the Turnstile, click Submit, then press Enter once confirmed...")
        input()


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
            for reason_text, label in RIGHT_MAP[right]:
                await submit_request(tab, right, reason_text, label, super_scraper)


asyncio.run(main())

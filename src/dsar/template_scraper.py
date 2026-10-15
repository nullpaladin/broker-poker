# <broker>.com — <one-line description of the form: platform, URL, quirks>.
# Rights the form exposes: <list>. Which of them run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP) (user's RIGHTS_TO_EXERCISE + their state's
# law); never read env flags or call SuperScraper directly to decide what to submit.
# <note anything the form does NOT support and why.>
#
# Page elements (keep this list current — it is what you fix first when the site changes):
#   #first_name / #last_name   First / Last name          (required)
#   #email                     Email                       (required)
#   #request_type              "Request type" <select>     -> options below
#   #details                   Free-text details textarea
#   #submit                    Submit button
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = ""

# Right -> this form's entry (label string / value / (value, label) tuple), or a LIST of
# entries when the form splits one right into several choices (e.g. RIGHT_TO_OPT_OUT ->
# "Do not sell" + "Targeted advertising"). Only rights the form actually offers; omit others.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "",
    # Right.RIGHT_TO_OPT_OUT: ["", ""],
    # Right.RIGHT_TO_DELETE: "",
    # Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: "",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every option the page lists in its rights chooser, exactly as displayed -> the Right it
# maps to, or None for options we deliberately do not automate (e.g. "Correct my data").
# HEALTH_CHECK compares this to the live page and fails on any new or vanished option.
PAGE_RIGHTS = {
    # "Access my data": Right.RIGHT_TO_ACCESS,
    # "Correct my data": None,
}
RIGHTS_OPTIONS_CSS = "#request_type option"  # elements whose text lists PAGE_RIGHTS

# Set only if the form genuinely cannot run unattended (mid-run SMS/email OTP).
# A manual reCAPTCHA input() pause does NOT count. Such scrapers are skipped entirely.
# NOT_AUTOMATABLE = True
# NOT_AUTOMATABLE_REASON = ""


async def submit_request(tab, right, entry, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

    # ... fill fields (SuperScraper.input_text_field / js_utils.js_set_value / js_utils.select_native_option) ...
    # ... select the request type from `entry` ...

    message = SuperScraper.request_statement([right], broker="<Broker Name>")
    # ... type `message` into the details/message textarea if the form has one ...

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, {
            # "First name": "//input[@name='first_name']",
        })

    if SuperScraper.DRY_RUN:  # also true under HEALTH_CHECK
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        return

    # ... click submit / pause for a manual CAPTCHA solve ...
    # Never guess what the post-submit page says. Only assert on confirmation text that a
    # real submission was OBSERVED to show (and note where it was observed); otherwise:
    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    # If the form only takes residents of states WITH a privacy law, set
    # SERVES_NO_LAW_STATES = False at module level and uncomment:
    # if SuperScraper.bail_if_state_unsupported(globals()):
    #     return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            entries = RIGHT_MAP[right]
            for entry in (entries if isinstance(entries, list) else [entries]):
                await submit_request(tab, right, entry, super_scraper)


asyncio.run(main())

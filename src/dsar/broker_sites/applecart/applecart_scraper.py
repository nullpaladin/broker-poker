# applecart.co — /privacyrights is the "someone else"/agent-on-behalf-of
# form; the self-submission form for exercising your own rights lives at
# /privacyrights2 instead (linked from the first page as "this form"). Both
# render as a HubSpot form embedded in a same-origin-permissive iframe
# (`id="hs-form-iframe-0"`) — iframe.find(...) resolves into the frame's
# document directly, no frame-busting observed (unlike acxiom.com's portal).
# Only residents of the states HubSpot lists in the State dropdown are
# accepted (CA/CO/CT/UT/VA/OR/TX/MT/DE/IA/NE/NH/NJ/MD/MN/TN) — the scraper
# aborts if SuperScraper.STATE isn't one of them. Selecting a State reveals a
# second select (name="TICKET.request_v2", conditional on State via HubSpot
# form logic — invisible in the DOM before that) with the actual single-select
# request type: exercises "Request a copy of the personal information..."
# (Access), "Opt out of the sale of my personal information" and "Delete my
# personal information" — one submission per right, and which of them run is decided
# ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). (Two state-specific extra options exist — a Virginia targeted-ads
# opt-out and a California categories-list request — left unexercised since
# they're bonus asks rather than a distinct DSAR right.) The one visible text
# field ("attestation", labeled with the full perjury-declaration paragraph
# as its HubSpot field label) is where you type your full legal name to sign
# the declaration; the page's own copy notes opt-out-only requests aren't
# required to complete it, but this scraper fills it on every pass anyway
# regardless of request type. Ends in an invisible reCAPTCHA v2 —
# may require a manual challenge in live mode if flagged.
#
# Page elements (keep this list current):
#   #hs-form-iframe-0                 HubSpot form iframe
#   select[name=state2]               "State" <select> (abbreviation values)
#   select[name=TICKET.request_v2]    Request type <select> (appears after State is chosen)
#   input[name=attestation]           Perjury-declaration signature (full legal name)
#   input[type=submit]                Submit button
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.applecart.co/privacyrights2"

SUPPORTED_STATE_ABBREVIATIONS = {
    "CA", "CO", "CT", "UT", "VA", "OR", "TX", "MT", "DE", "IA", "NE", "NH", "NJ", "MD", "MN", "TN",
}

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Request a copy of the personal information that Applecart has about me"],
    Right.RIGHT_TO_OPT_OUT: ["Opt out of the sale of my personal information"],
    Right.RIGHT_TO_DELETE: ["Delete my personal information"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# No audit wired: the request <select> lives inside the HubSpot iframe and only appears (with
# state-specific options) after a State is chosen, which read_option_labels cannot read.

STATE_XPATH = "//select[@name='state2']"
REQUEST_TYPE_XPATH = "//select[@name='TICKET.request_v2']"
ATTESTATION_XPATH = "//input[@name='attestation']"


async def submit_request(tab, right, request_type, state_abbr, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    iframe = await tab.find(id="hs-form-iframe-0", raise_exc=False)
    if not iframe:
        print(f"{super_scraper.OOPS} HubSpot form iframe not found")
        return

    state_select = await iframe.find(xpath="//select[@name='state2']", raise_exc=False)
    if not state_select:
        print(f"{super_scraper.OOPS} State dropdown not found")
        return
    await js_utils.select_native_option(state_select, value=state_abbr, dispatch=("change",))
    await asyncio.sleep(1.5)

    request_select = await iframe.find(xpath="//select[@name='TICKET.request_v2']", raise_exc=False)
    if not request_select:
        print(f"{super_scraper.OOPS} Request Type dropdown not found")
        return
    await js_utils.select_native_option(request_select, value=request_type, dispatch=("change",))
    await asyncio.sleep(0.5)

    attestation_field = await iframe.find(xpath="//input[@name='attestation']", raise_exc=False)
    if attestation_field:
        await attestation_field.click()
        await attestation_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")

    if SuperScraper.HEALTH_CHECK:
        # `iframe` stands in for `tab`: iframe.find() resolves into the frame's document.
        await SuperScraper.assert_fields_filled(iframe, {
            "State": STATE_XPATH,
            "Request type": REQUEST_TYPE_XPATH,
            "Attestation (full legal name)": ATTESTATION_XPATH,
        })

    label = "".join(c if c.isalnum() else "_" for c in request_type.lower())[:40].strip("_")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        return

    submit_btn = await iframe.find(xpath="//input[@type='submit']", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")
    else:
        print(f"{super_scraper.OOPS} Submit button not found")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    state_abbr = SuperScraper.STATE_ABBREVIATED
    if state_abbr not in SUPPORTED_STATE_ABBREVIATIONS:
        print(
            f"{SuperScraper.OOPS} applecart.co only accepts requests from "
            f"{sorted(SUPPORTED_STATE_ABBREVIATIONS)} — configured STATE '{SuperScraper.STATE}' "
            f"('{state_abbr}') is not supported. Skipping."
        )
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for request_type in RIGHT_MAP[right]:
                await submit_request(tab, right, request_type, state_abbr, super_scraper)


asyncio.run(main())

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
# (Access) and "Opt out of the sale of my personal information"
# unconditionally; "Delete my personal information" gated on
# REMOVE_INFORMATION — one submission per right, per this repo's usual
# pattern. (Two state-specific extra options exist — a Virginia targeted-ads
# opt-out and a California categories-list request — left unexercised since
# they're bonus asks rather than a distinct DSAR right.) The one visible text
# field ("attestation", labeled with the full perjury-declaration paragraph
# as its HubSpot field label) is where you type your full legal name to sign
# the declaration; the page's own copy notes opt-out-only requests aren't
# required to complete it, but this scraper fills it on every pass anyway
# since Access is always also requested. Ends in an invisible reCAPTCHA v2 —
# may require a manual challenge in live mode if flagged.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.applecart.co/privacyrights2"

SUPPORTED_STATE_ABBREVIATIONS = {
    "CA", "CO", "CT", "UT", "VA", "OR", "TX", "MT", "DE", "IA", "NE", "NH", "NJ", "MD", "MN", "TN",
}

REQUEST_TYPES = [
    "Request a copy of the personal information that Applecart has about me",
    "Opt out of the sale of my personal information",
]
DELETE_REQUEST_TYPE = "Delete my personal information"


async def submit_request(tab, request_type, state_abbr, super_scraper):
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
    await state_select.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].value==={state_abbr!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )
    await asyncio.sleep(1.5)

    request_select = await iframe.find(xpath="//select[@name='TICKET.request_v2']", raise_exc=False)
    if not request_select:
        print(f"{super_scraper.OOPS} Request Type dropdown not found")
        return
    await request_select.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].value==={request_type!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )
    await asyncio.sleep(0.5)

    attestation_field = await iframe.find(xpath="//input[@name='attestation']", raise_exc=False)
    if attestation_field:
        await attestation_field.click()
        await attestation_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")

    label = "".join(c if c.isalnum() else "_" for c in request_type.lower())[:40].strip("_")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{request_type}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await tab.take_screenshot(path=f"resources/screenshots/applecart_dry_run_{label}.png")
        print(f"Screenshot saved to resources/screenshots/applecart_dry_run_{label}.png")
        return

    submit_btn = await iframe.find(xpath="//input[@type='submit']", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{request_type}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Submit button not found")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    state_abbr = SuperScraper.STATE_ABBREVIATED
    if state_abbr not in SUPPORTED_STATE_ABBREVIATIONS:
        print(
            f"{SuperScraper.OOPS} applecart.co only accepts requests from "
            f"{sorted(SUPPORTED_STATE_ABBREVIATIONS)} — configured STATE '{SuperScraper.STATE}' "
            f"('{state_abbr}') is not supported. Skipping."
        )
        return

    request_types = list(REQUEST_TYPES)
    if SuperScraper.REMOVE_INFORMATION:
        request_types.append(DELETE_REQUEST_TYPE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type in request_types:
            await submit_request(tab, request_type, state_abbr, super_scraper)


asyncio.run(main())

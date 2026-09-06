# civisanalytics.com — Google Form ("Civis Analytics, Inc. - Data Subject
# Request"). First question is residency, single-select radio, one option
# per covered state (CA/CO/CT/DE/IN/IA/KY/MD/MT/NH/NJ/OR/RI/TN/UT/VA) plus
# "I am a non-U.S. resident." and "None of the above." — a typical .env
# STATE (e.g. Minnesota) isn't one of the covered states, so "None of the
# above." is the accurate answer.
#
# Selecting a covered state reveals a fuller flow (self/agent, then presumably
# name/email/request-type) — NOT built here, since it doesn't apply to an
# uncovered STATE and this scraper should reflect the requester's actual
# residency rather than picking a covered state just to unlock more fields
# (same principle as catalist.us's "Any other state" case elsewhere in this
# repo). Selecting "None of the above." instead skips straight to a single
# "Attestation" checkbox and Submit — no name, email, or request-type field
# is collected at all for non-covered residents. This is a genuine
# limitation of the form (it doesn't functionally solicit an actionable
# request from residents of uncovered states), not something this scraper
# works around. Google Forms radios/checkboxes carry aria-label directly.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://docs.google.com/forms/d/e/1FAIpQLSfvUYww9wEK9Y4F6VY3nQtm0bBS8QTdcDthet6WAKDYqnnwHA/viewform"

ATTESTATION_LABEL = (
    "I declare, under the penalty of perjury, that I am submitting this request (i) for "
    "myself (or on behalf someone for whom I am authorized to act) and the information "
    "I’ve provided is truthful and accurate and (ii) for a purpose that is not "
    "fraudulent, deceptive, malicious, illegal, or otherwise unauthorized."
)


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        residency_radio = await tab.find(**{"aria-label": "None of the above."}, raise_exc=False)
        if not residency_radio:
            print(f"{super_scraper.OOPS} 'None of the above.' residency option not found")
            return
        await residency_radio.click()
        await asyncio.sleep(1)

        next_btn = await tab.find(text="Next", raise_exc=False)
        if not next_btn:
            print(f"{super_scraper.OOPS} 'Next' button not found")
            return
        await next_btn.click()
        await asyncio.sleep(2)

        attestation = await tab.find(**{"aria-label": ATTESTATION_LABEL}, raise_exc=False)
        if attestation:
            await attestation.click()
        else:
            print(f"{super_scraper.OOPS} attestation checkbox not found")

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit attestation-only request for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} (no identifying fields "
                "are collected for non-covered-state residents)"
            )
            await asyncio.sleep(1)
            await tab.take_screenshot(path="resources/screenshots/civisanalytics_dry_run.png")
            print("Screenshot saved to resources/screenshots/civisanalytics_dry_run.png")
            return

        await super_scraper.click_item_by_text(tab=tab, text="Submit", sleep=2)
        await asyncio.sleep(2)
        print(f"Submitted attestation-only request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


asyncio.run(main())

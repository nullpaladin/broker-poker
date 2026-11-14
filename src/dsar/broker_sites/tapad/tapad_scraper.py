# tapad.com — Tapad consumer rights portal (Angular, crportal.tapad.com/#/email).
# Rights the form exposes (see RIGHT_MAP): "Data Access", "Opt Out", "Deletion". Which of them
# run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP). One submission per right.
# reCAPTCHA v2 requires a manual solve. Data Access and Deletion additionally require a
# mouse-drawn signature in a canvas element, which is not automated.
#
# Page elements:
#   ta-select[formcontrolname=requestType]   "Request type" dropdown (see RIGHT_MAP)
#   ta-select[formcontrolname=country]       Country dropdown -> "United States"
#   ta-input[formcontrolname=email] input    Email
#   "Submit" button
import asyncio
import time

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://crportal.tapad.com/#/email"

# Right -> "Request type" dropdown option.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Data Access",
    Right.RIGHT_TO_OPT_OUT: "Opt Out",
    Right.RIGHT_TO_DELETE: "Deletion",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

REQUEST_TYPE_XPATH = '//ta-select[@formcontrolname="requestType"]'
COUNTRY_XPATH = '//ta-select[@formcontrolname="country"]'
EMAIL_XPATH = '//ta-input[@formcontrolname="email"]//input'

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list


async def submit_request(tab, super_scraper, right, request_type: str):
    await tab.go_to(URL)
    time.sleep(5)

    await super_scraper.choose_dropdown_option_by_text(
        tab=tab,
        input_xpath=REQUEST_TYPE_XPATH,
        dropdown_option_text=request_type,
        sleep=1,
    )

    await super_scraper.choose_dropdown_option_by_text(
        tab=tab,
        input_xpath=COUNTRY_XPATH,
        dropdown_option_text="United States",
        sleep=1,
    )

    await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, {"Email": EMAIL_XPATH})

    if SuperScraper.DRY_RUN:
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        return

    # reCAPTCHA v2 is required — pause for manual solve or 2captcha integration
    # TODO: integrate 2captcha reCAPTCHA solver (site key: 6Lc59qEcAAAAAPUJ01XooqhDt_0rEa4IaAgDinAP)
    print(f"Please solve the reCAPTCHA for the {right.name} request, then press Enter...")
    input()

    # TODO: Data Access and Deletion require a mouse-drawn signature in a canvas element before
    # submission. This step is not automated. The form will reject those submissions without it.
    # Opt Out does not require a signature and submits cleanly.

    await super_scraper.click_item_by_text(tab=tab, text="Submit")
    time.sleep(3)
    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


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
            await submit_request(tab, super_scraper, right, RIGHT_MAP[right])

        await asyncio.sleep(3)


asyncio.run(main())

import asyncio
import json
import time

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

# Rights exercised: Right to Access, Do Not Sell/Share, Right to Delete (gated on REMOVE_INFORMATION).
# Server-rendered POST form. No captcha. Only requires email.
BASE_URL = "https://udp.33across.com/udp_opt_out/submit_request?type={}"

RIGHT_MAP = {
    "access":              ("access",    "Right to Access"),
    "opt_out_sale_share":  ("donotsell", "Do Not Sell / Share"),
    "delete":              ("delete",    "Right to Delete"),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

EMAIL_XPATH = '//input[@id="email"]'


async def submit_request(tab, request_type, label, super_scraper):
    await tab.go_to(BASE_URL.format(request_type))
    time.sleep(3)

    # Page JS (selectedType) pre-selects the right option from the URL param; set it explicitly too.
    await tab.execute_script(
        f"var s = document.getElementById('request_type');"
        f"s.value = {json.dumps(request_type)};"
        f"s.dispatchEvent(new Event('change'));"
    )

    await super_scraper.input_text_field(tab=tab, xpath=EMAIL_XPATH, text=SuperScraper.EMAIL, sleep=1)

    # Checking the terms box calls toggleSubmit() which removes the disabled attribute from submit.
    await tab.execute_script("document.getElementById('terms').click()")
    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        await SuperScraper.screenshot(tab, f"resources/screenshots/33across_{request_type}_dry_run.png")
        print(f"DRY RUN: would submit '{label}' for {SuperScraper.EMAIL}")
        await asyncio.sleep(2)
        return

    await tab.execute_script("document.getElementById('submit').click()")
    await asyncio.sleep(4)
    result = await SuperScraper.page_text(tab)
    print(result[:500])
    print(f"Submitted '{label}' for {SuperScraper.EMAIL}")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for code in codes:
            request_type, label = RIGHT_MAP[code]
            await submit_request(tab, request_type, label, super_scraper)


asyncio.run(main())

import asyncio
import json
import time

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

# 33across.com — server-rendered POST form at udp.33across.com. No captcha. Only requires email.
# Rights the form exposes: Right to Access, Do Not Sell / Share, Right to Delete. Which of them
# run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements:
#   ?type=<access|donotsell|delete>  URL parameter that pre-selects the request type
#   #request_type                    Request type <select> (also set explicitly)
#   #email                           Email                       (required)
#   #terms                           Terms checkbox (enables the submit button via toggleSubmit())
#   #submit                          Submit button
BASE_URL = "https://udp.33across.com/udp_opt_out/submit_request?type={}"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ("access",    "Right to Access"),
    Right.RIGHT_TO_OPT_OUT: ("donotsell", "Do Not Sell / Share"),
    Right.RIGHT_TO_DELETE: ("delete",    "Right to Delete"),
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

EMAIL_XPATH = '//input[@id="email"]'


async def submit_request(tab, right, request_type, label, super_scraper):
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

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, {"Email": EMAIL_XPATH})

    if SuperScraper.DRY_RUN:
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        await asyncio.sleep(2)
        return

    await tab.execute_script("document.getElementById('submit').click()")
    await asyncio.sleep(4)
    result = await js_utils.page_text(tab)
    print(result[:500])
    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


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
            request_type, label = RIGHT_MAP[right]
            await submit_request(tab, right, request_type, label, super_scraper)


asyncio.run(main())

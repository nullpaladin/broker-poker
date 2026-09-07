# alphonso.tv — two React "Customer Choice" forms, each just an email field
# (the request's current IP address is transmitted with it; no advertising IDs
# needed):
#   Opt-Out:  https://choice.alphonso.tv/donotsell            -> email + Submit
#   Other:    https://choice.alphonso.tv/otherconsumerrequests-> a free-text
#             "Write your Request Here" textarea + email + Submit
# The Opt-Out form is submitted unconditionally. The "other requests" form is
# used to state the Access request (and Delete when REMOVE_INFORMATION is set).
# Fields have no id/name — targeted by placeholder. No CAPTCHA.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

OPT_OUT_URL = "https://choice.alphonso.tv/donotsell"
OTHER_URL = "https://choice.alphonso.tv/otherconsumerrequests"


async def _fill_and_shot(tab, super_scraper, url, tag, message=None):
    await tab.go_to(url)
    await asyncio.sleep(6)

    if message:
        area = await tab.find(xpath="//textarea[@placeholder='Write your Request Here']", raise_exc=False)
        if area:
            await area.type_text(message)
            await asyncio.sleep(0.3)
        else:
            print(f"{super_scraper.OOPS} [{tag}] request textarea not found")

    email = await tab.find(xpath="//input[@placeholder='Enter Your Email']", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)
    else:
        print(f"{super_scraper.OOPS} [{tag}] email field not found")

    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/alphonso_dry_run_{tag}.png", beyond_viewport=True)
    print(f"Screenshot saved to resources/screenshots/alphonso_dry_run_{tag}.png")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN [{tag}]: would submit for {SuperScraper.EMAIL}")
        return

    submit = await tab.find(xpath="//button[normalize-space()='Submit']", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(3)
        print(f"Submitted [{tag}] for {SuperScraper.EMAIL}")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,1800")

    other_msg = (
        "I request access to the personal information Alphonso holds about me "
        "(including the specific pieces and categories, its sources, and the "
        "third parties it has been sold or shared with)."
    )
    if SuperScraper.REMOVE_INFORMATION:
        other_msg += " I also request deletion of my personal information."

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await _fill_and_shot(tab, super_scraper, OPT_OUT_URL, "opt_out")
        await _fill_and_shot(tab, super_scraper, OTHER_URL, "other", message=other_msg)


asyncio.run(main())

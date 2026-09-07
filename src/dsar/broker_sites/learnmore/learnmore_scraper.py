# learnmore.com — LearnMore "Privacy Rights" page (learnmore.com/privacy-rights/).
# Inline forms revealed by their own buttons. No CAPTCHA.
#   - "Request a Copy of My Data" (Access): requestDataFirstName /
#     requestDataLastName / requestDataEmail, then "Submit Request".
#   - "Delete My User Data" (Delete, gated on REMOVE_INFORMATION): a single
#     "requestorEmail" field, then submit.
#   - "Exert Right to Opt-out" is NOT automated: clicking it leaves this page
#     for the "Suppression Center", an email-verification-gated record-search
#     tool (enter email -> verification link -> then search for and suppress
#     your own listing). Nothing to fill end-to-end without a real inbox.
# Each form is filled in place and screenshotted BEFORE any navigation.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://learnmore.com/privacy-rights/"


async def _click(tab, text):
    el = await tab.find(text=text, raise_exc=False)
    if el:
        await el.click()
        await asyncio.sleep(1.5)
        return True
    return False


async def _fill_visible(tab, name, value):
    for el in await tab.find(xpath=f"//input[@name={name!r}]", find_all=True, raise_exc=False) or []:
        if await el.is_visible():
            await el.type_text(value)
            await asyncio.sleep(0.2)
            return True
    return False


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        # --- Access ---
        await tab.go_to(URL)
        await asyncio.sleep(5)
        await _click(tab, "Request a Copy of My Data")
        await _fill_visible(tab, "requestDataFirstName", SuperScraper.FIRST_NAME)
        await _fill_visible(tab, "requestDataLastName", SuperScraper.LAST_NAME)
        await _fill_visible(tab, "requestDataEmail", SuperScraper.EMAIL)
        time.sleep(0.5)
        await tab.take_screenshot("resources/screenshots/learnmore_dry_run_access.png")
        print("Screenshot saved to resources/screenshots/learnmore_dry_run_access.png")
        if not SuperScraper.DRY_RUN:
            btn = await tab.find(text="Submit Request", raise_exc=False)
            if btn:
                await btn.click()
                await asyncio.sleep(3)

        # --- Delete (gated) ---
        if SuperScraper.REMOVE_INFORMATION:
            await tab.go_to(URL)
            await asyncio.sleep(4)
            await _click(tab, "Delete My User Data")
            await _fill_visible(tab, "requestorEmail", SuperScraper.EMAIL)
            time.sleep(0.5)
            await tab.take_screenshot("resources/screenshots/learnmore_dry_run_delete.png")
            print("Screenshot saved to resources/screenshots/learnmore_dry_run_delete.png")

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: Access{' + Delete' if SuperScraper.REMOVE_INFORMATION else ''} "
                f"form(s) filled for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} "
                f"<{SuperScraper.EMAIL}>. Opt-out (Suppression Center) is email-verification "
                f"gated and not automated."
            )


asyncio.run(main())

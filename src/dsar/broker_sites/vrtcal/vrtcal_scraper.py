# vrtcal.com — vrtcal.com/opt-out/ is a pure browser-cookie-based opt-out
# toggle, no name/email/identity fields at all (tracking is device/browser-
# level, not account-level, so there's nothing to verify identity against).
# No Access/Delete/Correct mechanism exists anywhere on the site — this is
# the ONLY privacy mechanism vrtcal.com offers. The page shows "YOU ARE
# CURRENTLY: Not Opted Out" / "Opted Out" and a single "CHANGE OPT-OUT
# STATUS" link that flips the state (confirmed via before/after screenshot
# — text changes from "Not Opted Out" to "Opted Out"). No CAPTCHA. This is
# gated on REMOVE_INFORMATION as an opt-out-style action even though this
# repo's other REMOVE_INFORMATION-gated actions are usually deletions —
# treated as "opt out of tracking" being the closest fit to that flag's
# intent, since there is no separate unconditional right offered here to
# exercise instead.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.vrtcal.com/opt-out/"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,2000")

    if not SuperScraper.REMOVE_INFORMATION:
        print(
            "vrtcal.com only offers a browser-cookie opt-out toggle (no Access/Delete/Correct "
            "mechanism exists) — skipping since REMOVE_INFORMATION is not set."
        )
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        status_before = await tab.find(text="Not Opted Out", raise_exc=False)
        if not status_before:
            print("Status is already 'Opted Out' — nothing to change.")
            await tab.take_screenshot(path="resources/screenshots/vrtcal_dry_run.png")
            print("Screenshot saved to resources/screenshots/vrtcal_dry_run.png")
            return

        if SuperScraper.DRY_RUN:
            await tab.take_screenshot(path="resources/screenshots/vrtcal_dry_run.png")
            print("Screenshot saved to resources/screenshots/vrtcal_dry_run.png")
            print("DRY RUN: would click 'CHANGE OPT-OUT STATUS' to flip cookie state to Opted Out")
            return

        link = await tab.find(text="CHANGE OPT-OUT STATUS", raise_exc=False)
        if link:
            await link.click()
            await asyncio.sleep(2)
        else:
            print(f"{super_scraper.OOPS} 'CHANGE OPT-OUT STATUS' link not found")
            return

        await tab.take_screenshot(path="resources/screenshots/vrtcal_dry_run.png")
        print("Screenshot saved to resources/screenshots/vrtcal_dry_run.png")

        status_after = await tab.find(text="Opted Out", raise_exc=False)
        if status_after:
            print("Successfully opted out of vrtcal.com tracking.")
        else:
            print(f"{super_scraper.OOPS} Opt-out status unclear — verify in browser")


asyncio.run(main())

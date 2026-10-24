# vrtcal.com — vrtcal.com/opt-out/ is a pure browser-cookie-based opt-out
# toggle, no name/email/identity fields at all (tracking is device/browser-
# level, not account-level, so there's nothing to verify identity against).
# No Access/Delete/Correct mechanism exists anywhere on the site — this is
# the ONLY privacy mechanism vrtcal.com offers. The page shows "YOU ARE
# CURRENTLY: Not Opted Out" / "Opted Out" and a single "CHANGE OPT-OUT
# STATUS" link that flips the state (confirmed via before/after screenshot
# — text changes from "Not Opted Out" to "Opted Out"). No CAPTCHA. The toggle is
# Right.RIGHT_TO_OPT_OUT; it runs only when SuperScraper.rights_to_exercise(RIGHT_MAP)
# includes it.
#
# Page elements:
#   "Not Opted Out" / "Opted Out"   Current-status text ("YOU ARE CURRENTLY: ...")
#   "CHANGE OPT-OUT STATUS"         Link that flips the cookie opt-out state
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://www.vrtcal.com/opt-out/"

RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: "CHANGE OPT-OUT STATUS",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# The page's only control, as displayed -> the Right it maps to. No selector is recorded for it, so no audit is wired.
PAGE_RIGHTS = {"CHANGE OPT-OUT STATUS": Right.RIGHT_TO_OPT_OUT}
RIGHTS_OPTIONS_CSS = ""  # TODO(health-check): capture the link selector on a live run


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    if SuperScraper.bail_if_not_automatable(globals()):
        return
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print(
            "vrtcal.com only offers a browser-cookie opt-out toggle (no Access/Delete/Correct "
            "mechanism exists) — opt-out not requested, nothing to do."
        )
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        status_before = await tab.find(text="Not Opted Out", raise_exc=False)
        if not status_before:
            print("Status is already 'Opted Out' — nothing to change.")
            await SuperScraper.screenshot(tab, "dry_run")
            return

        if SuperScraper.DRY_RUN:
            await SuperScraper.screenshot(tab, "dry_run")
            print("DRY RUN: would click 'CHANGE OPT-OUT STATUS' to flip cookie state to Opted Out")
            return

        link = await tab.find(text=RIGHT_MAP[Right.RIGHT_TO_OPT_OUT], raise_exc=False)
        if link:
            await link.click()
            await asyncio.sleep(2)
        else:
            print(f"{super_scraper.OOPS} 'CHANGE OPT-OUT STATUS' link not found")
            return

        await SuperScraper.screenshot(tab, "dry_run")
        status_after = await tab.find(text="Opted Out", raise_exc=False)
        if status_after:
            print("Successfully opted out of vrtcal.com tracking.")
        else:
            print(f"{super_scraper.OOPS} Opt-out status unclear — verify in browser")


asyncio.run(main())

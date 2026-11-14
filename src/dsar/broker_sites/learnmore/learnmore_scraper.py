# learnmore.com — LearnMore "Privacy Rights" page (learnmore.com/privacy-rights/).
# Inline forms revealed by their own buttons. No CAPTCHA.
#   - "Request a Copy of My Data" (Access): requestDataFirstName /
#     requestDataLastName / requestDataEmail, then "Submit Request".
#   - "Delete My User Data" (Delete): a single "requestorEmail" field, then submit.
#   - "Exert Right to Opt-out" is NOT automated: clicking it leaves this page
#     for the "Suppression Center", an email-verification-gated record-search
#     tool (enter email -> verification link -> then search for and suppress
#     your own listing). Nothing to fill end-to-end without a real inbox.
# Each form is filled in place and screenshotted BEFORE any navigation.
# Which rights run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements:
#   "Request a Copy of My Data" button   reveals the Access form
#   requestDataFirstName / requestDataLastName / requestDataEmail   Access form fields
#   "Submit Request" button              Access form submit
#   "Delete My User Data" button         reveals the Delete form
#   requestorEmail                       Delete form email field
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://learnmore.com/privacy-rights/"

# Right -> text of the button that reveals that right's inline form.
# (Opt-out goes through the email-verified Suppression Center and is not automated.)
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Request a Copy of My Data",
    Right.RIGHT_TO_DELETE: "Delete My User Data",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every button on the page that starts a request, as displayed -> the Right it maps to (None = not automated).
PAGE_RIGHTS = {
    "Request a Copy of My Data": Right.RIGHT_TO_ACCESS,
    "Delete My User Data": Right.RIGHT_TO_DELETE,
    "Exert Right to Opt-out": None,
}
RIGHTS_OPTIONS_CSS = ""  # TODO(health-check): capture the card-button selector on a live run (no audit wired until then)
# No field assertions: the form inputs share names with hidden twins on the page, so only the visible one may be read.


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
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        for right in rights:
            await tab.go_to(URL)
            await asyncio.sleep(5)
            await _click(tab, RIGHT_MAP[right])

            if right == Right.RIGHT_TO_ACCESS:
                await _fill_visible(tab, "requestDataFirstName", SuperScraper.FIRST_NAME)
                await _fill_visible(tab, "requestDataLastName", SuperScraper.LAST_NAME)
                await _fill_visible(tab, "requestDataEmail", SuperScraper.EMAIL)
            else:
                await _fill_visible(tab, "requestorEmail", SuperScraper.EMAIL)
            time.sleep(0.5)
            await SuperScraper.screenshot(tab, f"dry_run_{right.value}")

            if SuperScraper.DRY_RUN:
                print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
            elif right == Right.RIGHT_TO_ACCESS:
                btn = await tab.find(text="Submit Request", raise_exc=False)
                if btn:
                    await btn.click()
                    await asyncio.sleep(3)
                    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")
            else:
                # The Delete form is filled but this scraper has never clicked its submit.
                print(f"'{right.name}' form filled but NOT submitted — submit it manually.")


asyncio.run(main())

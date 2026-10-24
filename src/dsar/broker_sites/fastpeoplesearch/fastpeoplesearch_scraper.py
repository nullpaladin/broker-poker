# fastpeoplesearch.com — Opt-Out/Right to Opt-Out only (Do Not Sell).
# Two-step removal: step 1 submits name+email+captcha → confirmation email with link.
# Step 2: user clicks email link → fills record details on the site to confirm removal.
# Fields: am=subject, firstname, middlename (optional), lastname, email, legal checkbox.
# reCAPTCHA v2 requires manual solve in live mode.
# Cookie popup dismissed via "Accept" button before form interaction.
#
# Page elements:
#   "Accept" button                 cookie popup
#   #firstname / #lastname / #email First / Last name / Email
#   input[name=legal]               legal checkbox
#   select[name=am]                 subject select (option index 1 chosen, set last)
#   .g-recaptcha                    reCAPTCHA v2
#   button[type=submit]             Submit
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.fastpeoplesearch.com/removal"

RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "removal"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

FIELD_XPATHS = {
    "First name": "//*[@id='firstname']",
    "Last name": "//*[@id='lastname']",
    "Email": "//*[@id='email']",
}


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    opts = SuperScraper.build_chromium_options()

    async with Chrome(options=opts) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(8)

        accept = await tab.find(text="Accept", raise_exc=False)
        if accept and await accept.is_visible():
            await accept.click()
            await asyncio.sleep(0.5)

        fn = await tab.find(id="firstname", raise_exc=False)
        if fn:
            await fn.type_text(SuperScraper.FIRST_NAME)
        time.sleep(0.3)

        ln = await tab.find(id="lastname", raise_exc=False)
        if ln:
            await ln.type_text(SuperScraper.LAST_NAME)
        time.sleep(0.3)

        em = await tab.find(id="email", raise_exc=False)
        if em:
            await em.type_text(SuperScraper.EMAIL)
        time.sleep(0.3)

        legal = await tab.find(name="legal", raise_exc=False)
        if legal:
            await legal.click_using_js()
            await asyncio.sleep(0.3)

        # Set am select last — the framework resets it if set before other inputs fire
        am_select = await tab.find(tag_name="select", name="am", raise_exc=False)
        if am_select:
            await js_utils.select_native_option(am_select, index=1)
        await asyncio.sleep(0.3)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit opt-out for {SuperScraper.EMAIL}")
            captcha_area = await tab.find(**{"class": "g-recaptcha"}, raise_exc=False)
            if captcha_area:
                await captcha_area.scroll_into_view()
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run_optout")
            return

        captcha_area = await tab.find(**{"class": "g-recaptcha"}, raise_exc=False)
        if captcha_area:
            await captcha_area.scroll_into_view()
        print("\nForm filled. Solve the reCAPTCHA and press Enter to submit.")
        input("Press Enter after solving reCAPTCHA: ")

        submit_btn = await tab.find(tag_name="button", type="submit", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(5)

        print(f"Step 1 submitted for {SuperScraper.EMAIL} — confirm in the browser.")
        print(f"  Check {SuperScraper.EMAIL} for a removal link — click it to complete removal.")


asyncio.run(main())

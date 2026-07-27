# fastpeoplesearch.com — Opt-Out/Right to Opt-Out only (Do Not Sell).
# Two-step removal: step 1 submits name+email+captcha → confirmation email with link.
# Step 2: user clicks email link → fills record details on the site to confirm removal.
# Fields: am=subject, firstname, middlename (optional), lastname, email, legal checkbox.
# reCAPTCHA v2 requires manual solve in live mode.
# Cookie popup dismissed via "Accept" button before form interaction.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.fastpeoplesearch.com/removal"


async def main():
    opts = ChromiumOptions()
    opts.binary_location = "/snap/bin/chromium"
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,900")
    super_scraper = SuperScraper()

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
        await tab.execute_script(
            "var s = document.querySelector('select[name=\"am\"]');"
            "s.selectedIndex = 1;"
            "s.dispatchEvent(new Event('change', {bubbles:true}));"
        )
        await asyncio.sleep(0.3)

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit opt-out for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            captcha_area = await tab.find(**{"class": "g-recaptcha"}, raise_exc=False)
            if captcha_area:
                await captcha_area.scroll_into_view()
            await asyncio.sleep(1)
            await tab.take_screenshot("fastpeoplesearch_dry_run_optout.png")
            print("Screenshot saved to fastpeoplesearch_dry_run_optout.png")
            return

        captcha_area = await tab.find(**{"class": "g-recaptcha"}, raise_exc=False)
        if captcha_area:
            await captcha_area.scroll_into_view()
        print(f"\nForm filled. Solve the reCAPTCHA and press Enter to submit.")
        input("Press Enter after solving reCAPTCHA: ")

        submit_btn = await tab.find(tag_name="button", type="submit", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(5)

        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "email", "sent", "check")):
            print(f"Step 1 submitted for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            print(f"  Check {SuperScraper.EMAIL} for a removal link — click it to complete removal.")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())

# popacta.com (optout.popacta.com) — general DSAR contact form.
# No request-type picker; rights are expressed in the free-text message.
# Exercises Access, Opt-Out, and Delete (gated on REMOVE_INFORMATION).
# reCAPTCHA v3 invisible — token auto-injected by the page JS before submit.
# Message field is required with a 250-character limit.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://optout.popacta.com/contact-us"

_MSG_BASE = (
    "I am submitting a DSAR to exercise my right to access "
    "and opt out of the processing and sale of my personal data."
)
_MSG_DELETE = (
    "I am submitting a DSAR to exercise my right to access, "
    "opt out, and delete my personal data."
)


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,2000")

    message = _MSG_DELETE if SuperScraper.REMOVE_INFORMATION else _MSG_BASE

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        email_field = await tab.find(tag_name="input", name="email", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)

        fname_field = await tab.find(tag_name="input", name="fname", raise_exc=False)
        if fname_field:
            await fname_field.type_text(SuperScraper.FIRST_NAME)

        lname_field = await tab.find(tag_name="input", name="lname", raise_exc=False)
        if lname_field:
            await lname_field.type_text(SuperScraper.LAST_NAME)

        msg_field = await tab.find(tag_name="textarea", name="form_message", raise_exc=False)
        if msg_field:
            await msg_field.type_text(message[:250])

        time.sleep(1)

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            await tab.take_screenshot("resources/screenshots/popacta_dry_run.png")
            print("Screenshot saved to resources/screenshots/popacta_dry_run.png")
            return

        submit_btn = await tab.find(id="submit-btn", raise_exc=False)
        if not submit_btn:
            print(f"{super_scraper.OOPS} Submit button not found")
            return
        await submit_btn.click()
        await asyncio.sleep(5)

        source = await tab.page_source
        if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
            print(f"Submitted DSAR for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())

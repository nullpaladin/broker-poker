# bi2technologies.com — plain Contact Form 7 (WordPress) contact form, no
# dedicated DSAR portal. No right-type picker — the specific ask (Access,
# Do Not Sell/Share, and Delete gated on REMOVE_INFORMATION) is stated in
# the free-text "How can we help?" message. reCAPTCHA is invisible
# (_wpcf7_recaptcha_response hidden field auto-populates) — no manual solve
# observed.
#
# NOTE: any of these fields, once given a value that triggers an 'input' or
# 'change' event (whether via type_text() or a native-setter dispatch), gets
# silently reset back to empty by some page-level JS roughly 750ms later —
# reproduced in isolation on a single untouched field with no other
# interaction. Setting the value via the native setter with NO event
# dispatch at all avoids whatever is watching for those events, and the
# value persists (confirmed over several seconds) — a plain HTML form reads
# .value directly at submit time regardless, so no dispatched event is
# actually needed for real submission to work.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://bi2technologies.com/contact-us/"


def _set_value_script(value):
    return (
        "var proto = Object.getPrototypeOf(this);"
        "var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;"
        f"setter.call(this, {value!r});"
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        first = await tab.find(xpath="//input[@name='your-name1']", raise_exc=False)
        last = await tab.find(xpath="//input[@name='your-name2']", raise_exc=False)
        email = await tab.find(xpath="//input[@name='your-email']", raise_exc=False)
        phone = await tab.find(xpath="//input[@name='your-phone']", raise_exc=False)
        message = await tab.find(xpath="//textarea[@name='your-message']", raise_exc=False)

        if first:
            await first.execute_script(_set_value_script(SuperScraper.FIRST_NAME))
        if last:
            await last.execute_script(_set_value_script(SuperScraper.LAST_NAME))
        if email:
            await email.execute_script(_set_value_script(SuperScraper.EMAIL))
        if phone:
            await phone.execute_script(_set_value_script(SuperScraper.PHONE_NUMBER))

        if SuperScraper.wants("delete"):
            request_text = (
                f"I am {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}. I am requesting access to "
                "the personal information you have collected about me, that you do not sell/share it, "
                "and that you delete my personal information."
            )
        else:
            request_text = (
                f"I am {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}. I am requesting access to "
                "the personal information you have collected about me, and that you do not sell/share it."
            )
        if message:
            await message.execute_script(_set_value_script(request_text))

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "resources/screenshots/bi2technologies_dry_run.png")
            return

        submit_btn = await tab.find(text="SEND MESSAGE", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(2)
            print(f"Submitted removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} SEND MESSAGE button not found")


asyncio.run(main())

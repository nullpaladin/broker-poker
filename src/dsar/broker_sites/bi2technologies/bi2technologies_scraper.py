# bi2technologies.com — plain Contact Form 7 (WordPress) contact form, no
# dedicated DSAR portal. No right-type picker — all the requested rights go in ONE
# submission, stated in the free-text "How can we help?" message
# (SuperScraper.request_statement). Which rights are asked for is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). reCAPTCHA is invisible
# (_wpcf7_recaptcha_response hidden field auto-populates) — no manual solve
# observed.
#
# Page elements:
#   input[name=your-name1]     First name
#   input[name=your-name2]     Last name
#   input[name=your-email]     Email
#   input[name=your-phone]     Phone
#   textarea[name=your-message]  Message ("How can we help?")
#   "SEND MESSAGE" button      Submit
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

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://bi2technologies.com/contact-us/"

# Right -> how the right is asked for (all go in the one message; the form has no picker).
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "message",
    Right.RIGHT_TO_OPT_OUT: "message",
    Right.RIGHT_TO_DELETE: "message",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (A plain contact form: there is no rights chooser to inventory.)

FIELD_XPATHS = {
    "First name": "//input[@name='your-name1']",
    "Last name": "//input[@name='your-name2']",
    "Email": "//input[@name='your-email']",
    "Phone": "//input[@name='your-phone']",
    "Message": "//textarea[@name='your-message']",
}


def _set_value_script(value):
    return (
        "var proto = Object.getPrototypeOf(this);"
        "var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;"
        f"setter.call(this, {value!r});"
    )


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

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

        request_text = (
            f"I am {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}. "
            + SuperScraper.request_statement(rights, broker="BI2 Technologies")
        )
        if message:
            await message.execute_script(_set_value_script(request_text))

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit {[r.name for r in rights]} for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run")
            return

        submit_btn = await tab.find(text="SEND MESSAGE", raise_exc=False)
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(2)
            print(f"Submitted {[r.name for r in rights]} for {SuperScraper.EMAIL} — confirm in the browser.")
        else:
            print(f"{super_scraper.OOPS} SEND MESSAGE button not found")


asyncio.run(main())

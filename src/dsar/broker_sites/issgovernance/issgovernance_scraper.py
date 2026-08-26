# issgovernance.com — server-rendered CCPA form (iss-stoxx.com). Required
# "cal_resident" checkbox attests California residency — same CA-only
# framing already used elsewhere in this repo (e.g. reonomy.com, finthrive.com),
# followed here rather than introduced as a new exception. No discrete right
# picker — a free-text "right_to_limit" textarea states which right(s) to
# exercise; deletion is only mentioned when REMOVE_INFORMATION is set.
# ria_broker_dealer/licenced_insurance_agent are optional and left blank
# (not applicable). "trap" is a honeypot field — left untouched. reCAPTCHA
# v3 is invisible and auto-resolves.
#
# NOTE: click()-then-type_text() silently fails on first_name/last_name on
# this page (click never focuses the field — document.activeElement stays
# BODY, likely something on the page intercepting the click), even though
# the identical approach works fine on email_address. Every field here is
# instead set via the native input-value setter + input/change event
# dispatch, which is reliable regardless of focus behavior.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions


URL = "https://www.iss-stoxx.com/legal/ccpa/"


def _js_set(field_id, value):
    return (
        f"var el=document.getElementById('{field_id}');"
        f"var proto = Object.getPrototypeOf(el);"
        f"var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;"
        f"setter.call(el, {value!r});"
        f"el.dispatchEvent(new Event('input', {{bubbles:true}}));"
        f"el.dispatchEvent(new Event('change', {{bubbles:true}}));"
        f"return el.value;"
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(3)

        await tab.execute_script(
            "var cb=document.getElementById('cal_resident'); cb.checked=true; "
            "cb.dispatchEvent(new Event('change', {bubbles:true}));"
        )

        await tab.execute_script(_js_set("first_name", SuperScraper.FIRST_NAME))
        await tab.execute_script(_js_set("last_name", SuperScraper.LAST_NAME))
        await tab.execute_script(_js_set("email_address", SuperScraper.EMAIL))

        if SuperScraper.REMOVE_INFORMATION:
            request_text = "I am requesting to know, correct, opt-out of sale/sharing, and delete my personal information."
        else:
            request_text = "I am requesting to know, correct, and opt-out of sale/sharing of my personal information."
        await tab.execute_script(_js_set("right_to_limit", request_text))

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(1)
            await tab.take_screenshot(path="resources/screenshots/issgovernance_dry_run.png")
            print("Screenshot saved to resources/screenshots/issgovernance_dry_run.png")
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath="//form[@id='ccpa-form']//button[@type='submit']", sleep=2)
        await asyncio.sleep(2)
        print(f"Submitted removal request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


asyncio.run(main())

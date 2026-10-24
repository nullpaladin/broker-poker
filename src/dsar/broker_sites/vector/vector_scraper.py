# vector.co — Vector "opt-out" form at vector.co/opt-out.
# Tiny server-rendered form wired to HubSpot (data-hs-do-not-collect): a single
# "name" field, "email", and a free-text "purpose" field ("What action would
# you like us to take on your data?"). No request-type picker and no CAPTCHA
# observed — one submission. The purpose text states the rights being
# exercised. Which rights are stated is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements:
#   input[name=name]                         Full name (first + last)
#   input[name=email]                        Email
#   input[name=purpose]                      "What action would you like us to take on your data?"
#   form#opt-out-form button[type=submit]    Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.vector.co/opt-out"

# The form is a single free-text box, so every right is expressed in that text.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "access",
    Right.RIGHT_TO_OPT_OUT: "opt_out",
    Right.RIGHT_TO_DELETE: "delete",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (A free-text opt-out form with no rights chooser.)

FIELD_XPATHS = {
    "Name": "//input[@name='name']",
    "Email": "//input[@name='email']",
    "Purpose": "//input[@name='purpose']",
}


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    if SuperScraper.bail_if_not_automatable(globals()):
        return
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    purpose = SuperScraper.request_statement(rights, broker="Vector")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        await super_scraper.input_text_field(
            tab=tab, xpath="//input[@name='name']",
            text=f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}", sleep=0.3,
        )
        await super_scraper.input_text_field(
            tab=tab, xpath="//input[@name='email']", text=SuperScraper.EMAIL, sleep=0.3,
        )
        await super_scraper.input_text_field(
            tab=tab, xpath="//input[@name='purpose']", text=purpose, sleep=0.3,
        )

        time.sleep(0.5)
        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        submit = await tab.find(xpath="//form[@id='opt-out-form']//button[@type='submit']", raise_exc=False)
        if submit:
            await submit.scroll_into_view()
        await SuperScraper.screenshot(tab, "dry_run")
        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit {', '.join(r.name for r in rights)} for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            return

        if submit:
            await submit.click()
            await asyncio.sleep(3)
        print(f"Submitted '{', '.join(r.name for r in rights)}' for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())

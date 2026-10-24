# popacta.com (optout.popacta.com) — general DSAR contact form.
# No request-type picker; rights are expressed in the free-text message.
# Exercises Access, Opt-Out, and Delete as decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP); one submission covers all of them.
# reCAPTCHA v3 invisible — token auto-injected by the page JS before submit.
# Message field is required with a 250-character limit, so a short fixed phrase is
# used instead of SuperScraper.request_statement (which would be truncated).
#
# Page elements:
#   input[name=email]            Email
#   input[name=fname]            First name
#   input[name=lname]            Last name
#   textarea[name=form_message]  Message (required, max 250 chars)
#   #submit-btn                  Submit button
import asyncio
import time

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://optout.popacta.com/contact-us"

# No request-type picker: rights are expressed only in the free-text message.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "access to my personal data",
    Right.RIGHT_TO_OPT_OUT: "opt-out of the processing and sale of my personal data",
    Right.RIGHT_TO_DELETE: "deletion of my personal data",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (A general contact form with no rights chooser.)

FIELD_XPATHS = {
    "Email": "//input[@name='email']",
    "First name": "//input[@name='fname']",
    "Last name": "//input[@name='lname']",
    "Message": "//textarea[@name='form_message']",
}


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    message = "I am submitting a DSAR to exercise my rights: " + "; ".join(RIGHT_MAP[r] for r in rights) + "."

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

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            await SuperScraper.screenshot(tab, "dry_run")
            return

        submit_btn = await tab.find(id="submit-btn", raise_exc=False)
        if not submit_btn:
            print(f"{super_scraper.OOPS} Submit button not found")
            return
        await submit_btn.click()
        await asyncio.sleep(5)

        print(f"Submitted DSAR for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())

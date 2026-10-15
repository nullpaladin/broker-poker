# optimalfusion.com — /do-not-sell-my-personal-information/ custom server-rendered
# form (id="ccpa-form", POSTs in place). One submission per right, chosen via the
# "reason" radio group. Which rights run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
# The required "accept" attestation checkbox is worded as a California perjury
# declaration; it is checked per this repo's precedent of completing attestation boxes.
# reCAPTCHA v3 is invisible (a token is injected into #recaptcha_token by the page's own
# grecaptcha.execute call), so no manual solve is needed for a dry run; a live submit still
# depends on Google scoring the automated session, which it may reject.
#
# Page elements (keep this list current):
#   input[name=reason] value "Request to know"             -> RIGHT_TO_ACCESS
#   input[name=reason] value "Do not sell my information"  -> RIGHT_TO_OPT_OUT
#   input[name=reason] value "Delete my information"       -> RIGHT_TO_DELETE
#   #firstName / #lastName   First / Last name
#   #postalCode              ZIP code
#   #email                   Email
#   input[name=accept]       Required attestation checkbox (California perjury declaration wording)
#   #recaptcha_token         Invisible reCAPTCHA v3 token (filled by the page)
#   form#ccpa-form button[type=submit]   Submit button
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://optimalfusion.com/do-not-sell-my-personal-information/"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Request to know", "access")],
    Right.RIGHT_TO_OPT_OUT: [("Do not sell my information", "opt_out")],
    Right.RIGHT_TO_DELETE: [("Delete my information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, reason_value, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(4)

    reason_radio = await tab.find(
        xpath=f"//input[@name='reason' and @value={reason_value!r}]", raise_exc=False
    )
    if not reason_radio:
        print(f"{super_scraper.OOPS} reason radio {reason_value!r} not found")
        return
    await reason_radio.click()
    await asyncio.sleep(0.5)

    fields = {
        "firstName": SuperScraper.FIRST_NAME,
        "lastName": SuperScraper.LAST_NAME,
        "postalCode": SuperScraper.ZIP_CODE,
        "email": SuperScraper.EMAIL,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)
            await asyncio.sleep(0.2)
        else:
            print(f"{super_scraper.OOPS} field '{field_id}' not found")

    accept = await tab.find(xpath="//input[@name='accept']", raise_exc=False)
    if accept:
        await accept.click()
    else:
        print(f"{super_scraper.OOPS} 'accept' attestation checkbox not found")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{reason_value}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        return

    submit = await tab.find(xpath="//form[@id='ccpa-form']//button[@type='submit']", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(3)
        print(f"Submitted '{reason_value}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    if SuperScraper.bail_if_not_automatable(globals()):
        return
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for right in rights for entry in RIGHT_MAP[right]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for reason_value, label in requests:
            await submit_request(tab, reason_value, label, super_scraper)


asyncio.run(main())

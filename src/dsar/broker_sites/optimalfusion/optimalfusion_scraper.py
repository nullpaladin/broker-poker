# optimalfusion.com — /do-not-sell-my-personal-information/ custom server-rendered
# form (id="ccpa-form", POSTs in place). One submission per right, chosen via the
# "reason" radio group:
#   - "Request to know"            -> Access        (unconditional)
#   - "Do not sell my information" -> Opt-Out        (unconditional)
#   - "Delete my information"      -> Delete          (gated on REMOVE_INFORMATION)
# Fields: firstName, lastName, postalCode, email, and a required "accept"
# attestation checkbox (worded as a California perjury declaration — checked per
# this repo's precedent of completing attestation boxes; the requester exercises
# equivalent rights under the MCDPA). reCAPTCHA v3 is invisible (a token is
# injected into #recaptcha_token by the page's own grecaptcha.execute call), so
# no manual solve is needed for a dry run; a live submit still depends on Google
# scoring the automated session, which it may reject.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://optimalfusion.com/do-not-sell-my-personal-information/"

RIGHTS = [
    ("Request to know", "access"),
    ("Do not sell my information", "opt_out"),
]
DELETE_RIGHT = ("Delete my information", "delete")


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
    await tab.take_screenshot(path=f"resources/screenshots/optimalfusion_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/optimalfusion_dry_run_{label}.png")

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
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,2200")

    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for reason_value, label in rights:
            await submit_request(tab, reason_value, label, super_scraper)


asyncio.run(main())

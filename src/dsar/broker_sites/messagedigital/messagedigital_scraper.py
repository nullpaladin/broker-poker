# messagedigital.com — /my-data embeds a OneTrust "webform" iframe
# (privacyportal.onetrust.com/webform/...), navigated to directly. Country
# defaults to United States; State is a custom autocomplete combobox
# (click, type, click the matching role="option" dropdown entry — same
# trap as mediawallah.com/merkle.com elsewhere in this repo). CAUTION: the
# "Select request type" group and everything below it (I am a (an),
# First/Last Name, perjury declaration) DOES NOT EXIST IN THE DOM until
# State has been selected — a fresh page load has only Country/State/
# Phone/Email, so inspecting the form before filling State will miss the
# entire request-type section. "Select request type" is a `role="option"`
# toggle group (Opt Out/Know-Access-Portability/Correct/Delete/Appeal),
# single-select despite looking like it could be otherwise — one
# submission per right. "I am a (an)" only offers "Consumer". A perjury-
# declaration "Yes" button (also role="option") must be clicked to
# proceed. BotDetect image CAPTCHA (`captchaCode`) — **CAPTCHA solution
# required**. Exercises Know/Access/Data Portability and Opt Out
# unconditionally; Delete gated on REMOVE_INFORMATION. Correct/Appeal
# skipped as auxiliary.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacyportal.onetrust.com/webform/dad2d808-afe9-4335-9217-e650f906ee17/f3f3d5e6-bc82-4d21-ab04-f733117d11d2"

RIGHTS = ["Request to Know/Access/Data Portability", "Request to Opt Out of Selling/Sharing or Targeted Advertising"]
DELETE_RIGHT = "Request to Delete"


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    state_field = await tab.find(id="stateDSARElement", raise_exc=False)
    if state_field:
        await state_field.click()
        await asyncio.sleep(0.3)
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(1.2)
        state_opt = await tab.find(
            xpath=f"//*[@role='option' and normalize-space()='{SuperScraper.STATE}']", raise_exc=False
        )
        if state_opt:
            await state_opt.click()
            await asyncio.sleep(1.5)
        else:
            print(f"{super_scraper.OOPS} state option '{SuperScraper.STATE}' not found")
    else:
        print(f"{super_scraper.OOPS} state field not found")

    right_opt = await tab.find(xpath=f"//*[@role='option' and @aria-label='{right}']", raise_exc=False)
    if right_opt:
        await right_opt.click()
        await asyncio.sleep(1.5)
    else:
        print(f"{super_scraper.OOPS} '{right}' option not found")

    consumer_opt = await tab.find(xpath="//*[@role='option' and @aria-label='Consumer']", raise_exc=False)
    if consumer_opt:
        await consumer_opt.click()

    # First/Last Name and the perjury declaration only render for some
    # request types (e.g. Access) — not others (e.g. Opt-Out), which only
    # ask for Phone/Email. Their absence for a given right is expected, not
    # an error, so these are filled silently when present.
    fields = {
        "firstNameDSARElement": SuperScraper.FIRST_NAME,
        "lastNameDSARElement": SuperScraper.LAST_NAME,
        "emailDSARElement": SuperScraper.EMAIL,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)

    phone_field = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
    if phone_field and SuperScraper.PHONE_NUMBER:
        digits = "".join(c for c in SuperScraper.PHONE_NUMBER if c.isdigit())
        await phone_field.type_text(digits)

    perjury_opt = await tab.find(xpath="//*[@role='option' and @aria-label='Yes']", raise_exc=False)
    if perjury_opt:
        await perjury_opt.click()

    label = "".join(c if c.isalnum() else "_" for c in right.lower())[:40].strip("_")

    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/messagedigital_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/messagedigital_dry_run_{label}.png")
    print(
        f"\n'{right}' request filled but NOT submitted — a BotDetect image CAPTCHA is "
        "present and requires manual entry."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, super_scraper)


asyncio.run(main())

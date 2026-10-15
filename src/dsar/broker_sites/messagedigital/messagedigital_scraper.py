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
# proceed. BotDetect image CAPTCHA (`captchaCode`) — **CAPTCHA solution required**; the
# form is filled and left unsubmitted. Rights the form exposes: "Request to
# Know/Access/Data Portability" (access), "Request to Opt Out of Selling/Sharing or
# Targeted Advertising" (opt-out), "Request to Delete"; Correct/Appeal skipped as
# auxiliary. Which rights run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements (keep this list current):
#   #stateDSARElement          State autocomplete combobox (click the matching role=option)
#   role=option aria-label=<request>   "Select request type" (see RIGHT_MAP)
#   role=option aria-label="Consumer"  "I am a (an)"
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name (only for some request types)
#   #emailDSARElement          Email
#   #phoneNumberDSARElement    Phone (digits only)
#   role=option aria-label="Yes"       perjury declaration
#   BotDetect image CAPTCHA    manual (captchaCode)
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://privacyportal.onetrust.com/webform/dad2d808-afe9-4335-9217-e650f906ee17/f3f3d5e6-bc82-4d21-ab04-f733117d11d2"

STATE_FIELD = "stateDSARElement"  # State autocomplete combobox
FIRST_NAME_FIELD = "firstNameDSARElement"  # First name
LAST_NAME_FIELD = "lastNameDSARElement"  # Last name
EMAIL_FIELD = "emailDSARElement"  # Email
PHONE_FIELD = "phoneNumberDSARElement"  # Phone

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Request to Know/Access/Data Portability",
    Right.RIGHT_TO_OPT_OUT: "Request to Opt Out of Selling/Sharing or Targeted Advertising",
    Right.RIGHT_TO_DELETE: "Request to Delete",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, option, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    state_field = await tab.find(id=STATE_FIELD, raise_exc=False)
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

    right_opt = await tab.find(xpath=f"//*[@role='option' and @aria-label='{option}']", raise_exc=False)
    if right_opt:
        await right_opt.click()
        await asyncio.sleep(1.5)
    else:
        print(f"{super_scraper.OOPS} '{option}' option not found")

    consumer_opt = await tab.find(xpath="//*[@role='option' and @aria-label='Consumer']", raise_exc=False)
    if consumer_opt:
        await consumer_opt.click()

    # First/Last Name and the perjury declaration only render for some
    # request types (e.g. Access) — not others (e.g. Opt-Out), which only
    # ask for Phone/Email. Their absence for a given right is expected, not
    # an error, so these are filled silently when present.
    fields = {
        FIRST_NAME_FIELD: SuperScraper.FIRST_NAME,
        LAST_NAME_FIELD: SuperScraper.LAST_NAME,
        EMAIL_FIELD: SuperScraper.EMAIL,
    }
    for field_id, value in fields.items():
        if not value:
            continue
        field = await tab.find(id=field_id, raise_exc=False)
        if field:
            await field.type_text(value)

    phone_field = await tab.find(id=PHONE_FIELD, raise_exc=False)
    if phone_field and SuperScraper.PHONE_NUMBER:
        digits = "".join(c for c in SuperScraper.PHONE_NUMBER if c.isdigit())
        await phone_field.type_text(digits)

    perjury_opt = await tab.find(xpath="//*[@role='option' and @aria-label='Yes']", raise_exc=False)
    if perjury_opt:
        await perjury_opt.click()

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
    print(
        f"\n'{right.name}' request filled but NOT submitted — a BotDetect image CAPTCHA is "
        "present and requires manual entry."
    )


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())

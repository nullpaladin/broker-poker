# inmar.com — OneTrust CDN Angular DSAR form (same URL as owneriq.com). Offers
# Access My Information and Delete My Information; which run is decided only by
# SuperScraper.rights_to_exercise. No Opt-Out. Subject: "Consumer located in CA, CO, CT, DE, IN, IA, KY, MD, MN,
# MT, NE, NH, NJ, OR, RI, TN, TX, UT, or VA". Delivery method: Online. formField20
# = "I am submitting this request as:" (type "Consumer", no autocomplete confirm
# needed). formField21DSARElement = phone number. Country: type + find(text=) click
# or ArrowDown+TAB fallback. State: ArrowDown+Enter. After state: "Is this request
# based on services provided to you by Inmar on behalf of another organization?" →
# click "No". Delete path additionally requires "Are you sure you want to delete
# your data?" → click "Yes". reCAPTCHA v2 in live mode. Two-step email verification.
# The only subject type offered is "Consumer located in <list of states with a privacy law>",
# so the form is for residents of those states (SERVES_NO_LAW_STATES = False).
#
# Page elements (aria-label buttons / ids):
#   [aria-label=<SUBJECT_TYPE>]             subject type "Consumer located in ..."
#   [aria-label="Access My Information"] / ["Delete My Information"]   request type
#   [aria-label=Online]                     delivery method
#   #formField20DSARElement                 "I am submitting this request as:" -> "Consumer"
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #emailDSARElement                       Email
#   #formField21DSARElement                 Phone number
#   #countryDSARElement / #stateDSARElement Country / State
#   [aria-label=No]                         "services provided by Inmar on behalf of another organization?"
#   [aria-label=Yes] (last one)             Delete only: "Are you sure you want to delete your data?"
#   [aria-label="click to submit form"]     Submit button
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/fa9f2f77-33ff-473b-ae55-579e2e693a91/ea2fadbb-3208-459b-8ed6-c975b6a9901c.html"

SUBJECT_TYPE = "Consumer located in CA, CO, CT, DE, IN, IA, KY, MD, MN, MT, NE, NH, NJ, OR, RI, TN, TX, UT, or VA"

SERVES_NO_LAW_STATES = False

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Access My Information", "access")],
    Right.RIGHT_TO_DELETE: [("Delete My Information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Recorded request types are aria-labels; the visible text may differ, so they are not copied in.)

FIELD_XPATHS = {
    "Submitting as": "//*[@id='formField20DSARElement']",
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Phone": "//*[@id='formField21DSARElement']",
    "Country": "//*[@id='countryDSARElement']",
    "State": "//*[@id='stateDSARElement']",
}


async def submit_request(tab, right, aria_label, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    subject_btn = await tab.find(**{"aria-label": SUBJECT_TYPE}, raise_exc=False)
    if subject_btn:
        await subject_btn.click_using_js()
    await asyncio.sleep(1)

    req_btn = await tab.find(**{"aria-label": aria_label}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request button '{aria_label}' not found")
        return
    await req_btn.click_using_js()
    await asyncio.sleep(1)

    delivery_btn = await tab.find(**{"aria-label": "Online"}, raise_exc=False)
    if delivery_btn:
        await delivery_btn.click_using_js()
    await asyncio.sleep(0.5)

    # "I am submitting this request as:" — type "Consumer" (free-text, no confirm needed)
    ff20 = await tab.find(id="formField20DSARElement", raise_exc=False)
    if ff20:
        await ff20.click()
        await tab.keyboard.type_text("Consumer")
    await asyncio.sleep(0.5)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    phone = await tab.find(id="formField21DSARElement", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)

    country_field = await tab.find(id="countryDSARElement", raise_exc=False)
    if country_field:
        await country_field.click()
        await tab.keyboard.type_text("United States")
        await asyncio.sleep(2)
        country_opt = await tab.find(text="United States", raise_exc=False)
        if country_opt:
            await country_opt.click()
        else:
            await tab.keyboard.press(Key.ARROWDOWN)
            await asyncio.sleep(0.3)
            await tab.keyboard.press(Key.TAB)
    await asyncio.sleep(1)

    state_field = await tab.find(id="stateDSARElement", raise_exc=False)
    if state_field:
        await state_field.click()
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(3)
        await tab.keyboard.press(Key.ARROWDOWN)
        await asyncio.sleep(0.3)
        await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(0.5)

    # "Is this request based on services provided to you by Inmar on behalf of
    # another organization?" — click No
    no_btn = await tab.find(**{"aria-label": "No"}, raise_exc=False)
    if no_btn:
        await no_btn.click_using_js()
    await asyncio.sleep(0.5)

    # Delete path only: "Are you sure you want to delete your data?" — click Yes.
    # Use find_all to get the last Yes button (delete confirmation), not the first
    # (on-behalf-of Yes), which would override the No click above.
    if label == "delete":
        yes_btns = await tab.find(**{"aria-label": "Yes"}, find_all=True, raise_exc=False) or []
        if yes_btns:
            await yes_btns[-1].click_using_js()
        await asyncio.sleep(0.5)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(f"DRY RUN: would submit '{right.name}' ({aria_label}) for {SuperScraper.EMAIL}")
        return

    print(f"\nForm filled for '{aria_label}'.")
    print("Solve the reCAPTCHA in the browser, then click Submit.")
    print("Check your email for the verification link, then press Enter...")
    input()
    print(f"Submitted '{right.name}' ({aria_label}) for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    if SuperScraper.bail_if_state_unsupported(globals()):
        return
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for aria_label, label in RIGHT_MAP[right]:
                await submit_request(tab, right, aria_label, label, super_scraper)


asyncio.run(main())

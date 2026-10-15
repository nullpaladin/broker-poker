# owneriq.com — OneTrust Angular DSAR portal. Rights the form exposes: Access, Delete (no Opt-Out
# or Correct). One submission per right; which run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). inmar.com uses the same form URL.
# Subject type is a "Consumer located in CA, CO, CT, DE, IN, IA, KY, MD, MN, MT, NE, NH, NJ, OR,
# RI, TN, TX, UT, or VA" card — the form is for residents of those states, so
# SERVES_NO_LAW_STATES = False. No captcha observed.
#
# Page elements (keep this list current):
#   aria-label SUBJECT_TYPE             Subject type card (click_using_js)
#   aria-label "Access My Information"  Request type card -> RIGHT_TO_ACCESS
#   aria-label "Delete My Information"  Request type card -> RIGHT_TO_DELETE
#   aria-label "Online"                 Delivery method (click_using_js)
#   #formField20DSARElement             "I am submitting this request as:" autocomplete -> type "Consumer"
#   #firstNameDSARElement / #lastNameDSARElement / #emailDSARElement   First / Last name, Email
#   #formField21DSARElement             Phone number (required)
#   #countryDSARElement / #stateDSARElement   Country / State autocomplete comboboxes (State appears after Country)
#   aria-label "click to submit form"   Submit button
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/fa9f2f77-33ff-473b-ae55-579e2e693a91/ea2fadbb-3208-459b-8ed6-c975b6a9901c.html"

SUBJECT_TYPE = "Consumer located in CA, CO, CT, DE, IN, IA, KY, MD, MN, MT, NE, NH, NJ, OR, RI, TN, TX, UT, or VA"

SERVES_NO_LAW_STATES = False

# Right -> request-type card aria-label
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Access My Information",
    Right.RIGHT_TO_DELETE: "Delete My Information",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, aria_label, super_scraper):
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

    # Delivery method — "Online" preferred
    delivery_btn = await tab.find(**{"aria-label": "Online"}, raise_exc=False)
    if delivery_btn:
        await delivery_btn.click_using_js()
    await asyncio.sleep(0.5)

    # "I am submitting this request as:" — Angular autocomplete; click then keyboard type
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
    await asyncio.sleep(1)

    # State field only appears after country is selected
    state_field = await tab.find(id="stateDSARElement", raise_exc=False)
    if state_field:
        await state_field.click()
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(2)
        state_opt = await tab.find(text=SuperScraper.STATE, raise_exc=False)
        if state_opt:
            await state_opt.click()
    await asyncio.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{aria_label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        return

    print(f"\nForm filled for '{aria_label}'.")
    print("If a captcha appears, solve it, then click Submit.")
    print("Press Enter after the confirmation page appears...")
    input()

    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    if SuperScraper.bail_if_not_automatable(globals()):
        return
    if SuperScraper.bail_if_state_unsupported(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, RIGHT_MAP[right], super_scraper)


asyncio.run(main())

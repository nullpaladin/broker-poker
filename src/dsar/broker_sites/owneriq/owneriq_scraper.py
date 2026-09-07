# owneriq.com — exercises Right to Access and Right to Delete (gated on
# REMOVE_INFORMATION). No Opt-Out or Correct form available on the OneTrust
# portal. Subject type "Consumer located in CA, CO, CT, DE, IN, IA, KY, MD,
# MN, MT, NE, NH, NJ, OR, RI, TN, TX, UT, or VA". Country and State are
# autocomplete comboboxes (click then tab.keyboard.type_text then tab.find(text=)).
# Delivery method: Online (click_using_js). "I am submitting this request as:"
# (formField20DSARElement) autocomplete → type "Consumer", select if option appears.
# Phone number required (formField21DSARElement). No captcha.
# inmar.com uses the same form URL.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/fa9f2f77-33ff-473b-ae55-579e2e693a91/ea2fadbb-3208-459b-8ed6-c975b6a9901c.html"

SUBJECT_TYPE = "Consumer located in CA, CO, CT, DE, IN, IA, KY, MD, MN, MT, NE, NH, NJ, OR, RI, TN, TX, UT, or VA"

# (aria-label, screenshot label)
REQUESTS = [
    ("Access My Information", "access"),
]
DELETE_REQUEST = ("Delete My Information", "delete")


async def submit_request(tab, aria_label, label, super_scraper):
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
        await tab.take_screenshot(f"resources/screenshots/owneriq_dry_run_{label}.png")
        print(f"Screenshot saved to resources/screenshots/owneriq_dry_run_{label}.png")
        return

    print(f"\nForm filled for '{aria_label}'.")
    print("If a captcha appears, solve it, then click Submit.")
    print("Press Enter after the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{aria_label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{aria_label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for aria_label, label in requests:
            await submit_request(tab, aria_label, label, super_scraper)


asyncio.run(main())

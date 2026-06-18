# reonomy.com — California-focused DSAR form. Exercises Access My Information,
# Do Not Sell My Information, and Delete My Information (gated on
# REMOVE_INFORMATION). Subject "California Consumer". Delivery "Online". One
# submission per right (form accepts one at a time). State field has non-standard
# ID formField16DSARElement (autocomplete: ArrowDown+Enter). Phone country code
# vt-input-8 (type "1" for US +1). captchaCode image CAPTCHA requires manual
# entry in live mode.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/ed2a4eae-cadd-4d40-9f21-cf27556d3a21/49fbe5ce-5ee2-487b-9b4f-bfdab733819b.html"

# (aria-label, screenshot label) — trailing spaces are part of the actual labels
REQUESTS = [
    ("Access My Information ", "access"),
    ("Do Not Sell My Information ", "optout"),
]
DELETE_REQUEST = ("Delete My Information ", "delete")


async def fill_and_submit(tab, req_aria_label, screenshot_label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    consumer_btn = await tab.find(**{"aria-label": "California Consumer"}, raise_exc=False)
    if not consumer_btn:
        print(f"{super_scraper.OOPS} 'California Consumer' subject button not found")
        return
    await consumer_btn.click_using_js()
    await asyncio.sleep(0.5)

    req_btn = await tab.find(**{"aria-label": req_aria_label}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request button '{req_aria_label}' not found")
        return
    await req_btn.click_using_js()
    await asyncio.sleep(0.5)

    online_btn = await tab.find(**{"aria-label": "Online"}, raise_exc=False)
    if online_btn:
        await online_btn.click_using_js()
    await asyncio.sleep(0.5)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    address = await tab.find(id="addressDSARElement", raise_exc=False)
    if address:
        await address.type_text(SuperScraper.ADDRESS)

    city = await tab.find(id="cityDSARElement", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    # State field uses non-standard ID formField16DSARElement
    state_field = await tab.find(id="formField16DSARElement", raise_exc=False)
    if state_field:
        await state_field.click()
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(2)
        await tab.keyboard.press(Key.ARROWDOWN)
        await asyncio.sleep(0.3)
        await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(0.5)

    zip_field = await tab.find(id="zipDSARElement", raise_exc=False)
    if zip_field:
        await zip_field.type_text(SuperScraper.ZIP_CODE)

    phone_cc = await tab.find(id="vt-input-8", raise_exc=False)
    if phone_cc:
        await phone_cc.click()
        await tab.keyboard.type_text("1")
    await asyncio.sleep(0.5)

    phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    request_details = await tab.find(**{"aria-label": "Request Details"}, raise_exc=False)
    if request_details:
        label = req_aria_label.strip()
        await request_details.type_text(
            f"I am exercising my right to {label.lower()} under applicable privacy law."
        )
    await asyncio.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{req_aria_label.strip()}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await tab.take_screenshot(f"resources/screenshots/reonomy_dry_run_{screenshot_label}.png")
        print(f"Screenshot saved to resources/screenshots/reonomy_dry_run_{screenshot_label}.png")
        return

    print(f"\nForm filled for '{req_aria_label.strip()}'.")
    print("Enter the CAPTCHA code shown in the image into the captchaCode field,")
    print("then click Submit. Press Enter after the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{req_aria_label.strip()}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{req_aria_label.strip()}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3000")

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for req_label, screenshot_label in requests:
            await fill_and_submit(tab, req_label, screenshot_label, super_scraper)


asyncio.run(main())

# clientcommand.com (Summit Resources, LLC d/b/a Client Command) — OneTrust CDN
# Angular DSAR form. Exercises Know/Access, Opt-Out, and Deletion (gated).
# Subject: "Marketing Recipient". Request type buttons (Know/Access, Deletion,
# Opt-Out) only appear after all personal info fields (including state) are
# filled. One submission per right (form processes only one selection at a time).
# State is an autocomplete combobox (ArrowDown+Enter). Phone country code
# vt-input-9 (type "1" for US +1). captchaCode image CAPTCHA requires manual
# entry in live mode.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/555c3377-7eb2-4e7a-bf30-c408de4ab483/70df6685-8289-4d72-a9d7-9a736b3b837f.html"

RIGHT_MAP = {
    "access": [("Know/Access", "access", "I am requesting access to all personal data you hold about me.")],
    "opt_out_sale_share": [("Opt-Out", "optout", "I am opting out of the sale or sharing of my personal data.")],
    "delete": [("Deletion", "delete", "I am requesting deletion of all personal data you hold about me.")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def fill_and_submit(tab, req_label, screenshot_label, details_text, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    subject_btn = await tab.find(**{"aria-label": "Marketing Recipient"}, raise_exc=False)
    if not subject_btn:
        print(f"{super_scraper.OOPS} 'Marketing Recipient' subject button not found")
        return
    await subject_btn.click_using_js()
    await asyncio.sleep(1)

    from_field = await tab.find(id="formField23DSARElement", raise_exc=False)
    if from_field:
        await from_field.type_text("Client Command marketing lists / data broker services")

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

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

    state_field = await tab.find(id="stateDSARElement", raise_exc=False)
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

    phone_cc = await tab.find(id="vt-input-9", raise_exc=False)
    if phone_cc:
        await phone_cc.click()
        await tab.keyboard.type_text("1")
    await asyncio.sleep(0.5)

    phone = await tab.find(id="phoneNumberDSARElement", raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)
    await asyncio.sleep(1)

    req_btn = await tab.find(**{"aria-label": req_label}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request button '{req_label}' not found")
        return
    await req_btn.click_using_js()
    await asyncio.sleep(0.5)

    details = await tab.find(id="requestDetailsDSARElement", raise_exc=False)
    if details:
        await details.type_text(details_text)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{req_label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"resources/screenshots/clientcommand_dry_run_{screenshot_label}.png")
        return

    print(f"\nForm filled for '{req_label}'.")
    print("Enter the CAPTCHA code shown in the image into the captchaCode field,")
    print("then click Submit. Press Enter after the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{req_label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{req_label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    requests = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for req_label, screenshot_label, details_text in requests:
            await fill_and_submit(tab, req_label, screenshot_label, details_text, super_scraper)


asyncio.run(main())

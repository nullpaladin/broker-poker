# deeprootanalytics.com — Ethyca/Fides privacy portal.
# Three cards on landing page: "Access your data", "Delete your data", "Opt out of data sales and sharing".
# Opt-out card shows "Consent management is unavailable in your area." — skipped.
# Access and Delete each require: email, first_name, last_name, addr1, city, state (text), zip.
# Phone optional: phone_num (Access), phone (Delete).
# After clicking Continue: email verification code sent to inbox.
#   id="code" input + "Submit code" button.
# No CAPTCHA. Live mode requires user to enter the email verification code.
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://privacy.deeprootanalytics.com/"


async def _fill_form(tab, phone_field_id="phone_num"):
    for fid, val in [
        ("email", SuperScraper.EMAIL),
        ("first_name", SuperScraper.FIRST_NAME),
        ("last_name", SuperScraper.LAST_NAME),
        ("addr1", SuperScraper.ADDRESS),
        ("city", SuperScraper.CITY),
        ("state", SuperScraper.STATE),
        ("zip", SuperScraper.ZIP_CODE),
    ]:
        field = await tab.find(id=fid, raise_exc=False)
        if field:
            await field.type_text(val)
    phone = await tab.find(id=phone_field_id, raise_exc=False)
    if phone:
        await phone.type_text(SuperScraper.PHONE_NUMBER)


async def _submit_request(tab, card_text, label, phone_field_id, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    cards = await tab.find(text=card_text, find_all=True, raise_exc=False) or []
    for card in cards:
        if await card.is_visible():
            await card.click()
            await asyncio.sleep(3)
            break

    await _fill_form(tab, phone_field_id)
    time.sleep(0.5)

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit {label} for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        continue_btn = await tab.find(text="Continue", raise_exc=False)
        if continue_btn and await continue_btn.is_visible():
            await continue_btn.scroll_into_view()
        await asyncio.sleep(2)
        await tab.take_screenshot(f"resources/screenshots/deeprootanalytics_dry_run_{label}.png")
        print(f"Screenshot saved to resources/screenshots/deeprootanalytics_dry_run_{label}.png")
        return

    continue_btn = await tab.find(text="Continue", raise_exc=False)
    if continue_btn and await continue_btn.is_visible():
        await continue_btn.click()
        await asyncio.sleep(5)

    print(f"\nForm submitted for {label}.")
    print("Check your email for a verification code, then enter it here.")
    code = input("Verification code: ").strip()

    code_field = await tab.find(id="code", raise_exc=False)
    if code_field:
        await code_field.type_text(code)
        await asyncio.sleep(0.5)

    submit_code_btn = await tab.find(text="Submit code", raise_exc=False)
    if submit_code_btn and await submit_code_btn.is_visible():
        await submit_code_btn.click()
        await asyncio.sleep(4)

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation", "request submitted")):
        print(f"Submitted {label} for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for {label} — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,3000")

    async with Chrome(options=options) as browser:
        tab = await browser.start()

        await _submit_request(tab, "Access your data", "access", "phone_num", super_scraper)
        if SuperScraper.REMOVE_INFORMATION:
            await _submit_request(tab, "Delete your data", "delete", "phone", super_scraper)


asyncio.run(main())

# perion.com — a Monday.com form (forms.monday.com). Perion states its
# product doesn't process direct identifiers (name/email/phone), so it
# needs a MAID (ADVERTISING_ID) or cookie ID to locate records — filled
# into the "Identification" long-text field in addition to name/email.
#
# Both dropdowns ("ARE YOU THE INDIVIDUAL OR A REPRESENTATIVE..." and
# "Request") are Downshift comboboxes whose real `<input>` is not
# independently clickable — pydoll's `.click()`/`.click_using_js()` both
# raise ElementNotVisible on it even though it reports visible CSS
# properties, and dispatching synthetic mousedown/click/focus/ArrowDown
# events directly at the input does nothing either. What actually opens
# the dropdown is clicking the input's own ancestor
# `div.triggerWrapper_...` wrapper instead. "Request" (the actual right
# selector) is single-select despite the plural "RIGHT(S)" wording in its
# label — selecting a second option replaces rather than adds to the
# field's value — so this is one submission per right, matching the
# pattern seen on several OneTrust-hosted sites elsewhere in this repo.
# "I am the individual requesting action" is used for the relationship
# question. Plain text fields (Name/Email/MAID/Country) also silently
# drop their first couple of keystrokes if typed immediately (e.g. "John
# Doe" landed as "n Doe") — a click + ~0.4s pause before typing fixes it.
# Exercises Access ("Right to Know or Access my Personal Data") and
# Opt-out of Sale unconditionally; Delete gated on REMOVE_INFORMATION. No
# CAPTCHA observed.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://forms.monday.com/forms/2e643e95786ac0c2cdf2dca015d20c68?r=use1"

RIGHT_MAP = {
    "access": ["Right to Know or Access my Personal Data"],
    "opt_out_sale_share": ["Right to opt-out of Sale"],
    "delete": ["Right to Delete my Personal Data"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _open_and_select(tab, input_id, option_text, super_scraper, description):
    trigger = await tab.find(
        xpath=f"//input[@id='{input_id}']/ancestor::div[contains(@class,'triggerWrapper')]",
        raise_exc=False,
    )
    if not trigger:
        print(f"{super_scraper.OOPS} {description} trigger not found")
        return
    await trigger.scroll_into_view()
    await asyncio.sleep(0.3)
    await trigger.click()
    await asyncio.sleep(1)
    option = await tab.find(xpath=f"//*[@role='option' and normalize-space()='{option_text}']", raise_exc=False)
    if option:
        await option.click()
        await asyncio.sleep(0.5)
    else:
        print(f"{super_scraper.OOPS} {description} option '{option_text}' not found")


async def _type_with_settle(field, text):
    # This form's fields silently drop the first couple of keystrokes if
    # typed immediately after page load / a fresh click — e.g. "John Doe"
    # landed as "n Doe". A click + brief pause before typing avoids it.
    await field.click()
    await asyncio.sleep(0.4)
    await field.type_text(text)


async def submit_request(tab, right, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    name_field = await tab.find(id="name-input", raise_exc=False)
    if name_field:
        await _type_with_settle(name_field, f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")

    email_field = await tab.find(id="text_mkym7vyt-input", raise_exc=False)
    if email_field:
        await _type_with_settle(email_field, SuperScraper.EMAIL)

    await _open_and_select(
        tab, "downshift-:r0:-input", "I am the individual requesting action", super_scraper, "relationship"
    )

    maid_field = await tab.find(id="long_text9__1-input", raise_exc=False)
    if maid_field and SuperScraper.ADVERTISING_ID:
        await _type_with_settle(maid_field, SuperScraper.ADVERTISING_ID)

    country_field = await tab.find(id="text__1-input", raise_exc=False)
    if country_field:
        await _type_with_settle(country_field, "United States")

    await _open_and_select(tab, "downshift-:r1:-input", right, super_scraper, "request type")

    label = "".join(c if c.isalnum() else "_" for c in right.lower())[:40].strip("_")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/perion_dry_run_{label}.png")
    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        return

    submit_btn = await tab.find(text="Submit", raise_exc=False)
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{right}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Submit button not found for '{right}'")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    rights = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, right, super_scraper)


asyncio.run(main())

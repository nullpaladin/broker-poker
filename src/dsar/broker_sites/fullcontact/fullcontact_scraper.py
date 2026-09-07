# fullcontact.com — three cards (Access My Data / Do Not Sell or Share My
# Data / Delete My Data). "Access My Data" first asks "What country do you
# live in?" (defaults to United States, just click Continue); the other two
# skip straight to the identity-verification step. All three converge on
# the same "We need to verify your identity" screen: "Use My Email" reveals
# an email field and a "Send Me A Code" button — a real OTP email send, so
# this scraper fills the email and stops there regardless of DRY_RUN;
# entering the code and continuing must be done manually. Exercises Access
# and Do Not Sell/Share unconditionally; Delete gated on REMOVE_INFORMATION.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://platform.fullcontact.com/your-privacy-choices"

CARDS = ["Access My Data", "Do Not Sell or Share My Data"]
DELETE_CARD = "Delete My Data"


async def submit_request(tab, card_text, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    card_btn = await tab.find(text=card_text, raise_exc=False)
    if not card_btn:
        print(f"{super_scraper.OOPS} '{card_text}' card not found")
        return
    await card_btn.click()
    await asyncio.sleep(2)

    continue_btn = await tab.find(text="Continue", raise_exc=False)
    if continue_btn:
        await continue_btn.click()
        await asyncio.sleep(2)

    use_email_btn = await tab.find(text="Use My Email", raise_exc=False)
    if not use_email_btn:
        print(f"{super_scraper.OOPS} 'Use My Email' button not found for '{card_text}'")
        return
    await use_email_btn.click()
    await asyncio.sleep(2)

    email_field = await tab.find(
        xpath="//input[@placeholder='Enter Your Email Address']", raise_exc=False
    )
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    label = "".join(c if c.isalnum() else "_" for c in card_text.lower())[:40].strip("_")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/fullcontact_dry_run_{label}.png")
    print(
        f"\n'{card_text}' email entered but NOT sent — click 'Send Me A Code' yourself, "
        "enter the code you receive, and continue. This sends a real verification code "
        "regardless of DRY_RUN, so it is never done automatically."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    cards = list(CARDS)
    if SuperScraper.REMOVE_INFORMATION:
        cards.append(DELETE_CARD)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for card_text in cards:
            await submit_request(tab, card_text, super_scraper)


asyncio.run(main())

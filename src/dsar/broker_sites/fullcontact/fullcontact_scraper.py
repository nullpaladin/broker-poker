# fullcontact.com — three cards (Access My Data / Do Not Sell or Share My
# Data / Delete My Data). "Access My Data" first asks "What country do you
# live in?" (defaults to United States, just click Continue); the other two
# skip straight to the identity-verification step. All three converge on
# the same "We need to verify your identity" screen: "Use My Email" reveals
# an email field and a "Send Me A Code" button — a real OTP email send, so
# this scraper fills the email and stops there regardless of DRY_RUN;
# entering the code and continuing must be done manually. Which cards run is
# decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements:
#   Card "Access My Data" / "Do Not Sell or Share My Data" / "Delete My Data"
#   Button "Continue"            (country step of "Access My Data"; default United States)
#   Button "Use My Email"        reveals the email field
#   input placeholder "Enter Your Email Address"   Email
#   Button "Send Me A Code"      (never clicked by this scraper — sends a real OTP)
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://platform.fullcontact.com/your-privacy-choices"

NOT_AUTOMATABLE = True
NOT_AUTOMATABLE_REASON = (
    "identity verification sends a real email OTP that must be entered to continue"
)

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Access My Data",
    Right.RIGHT_TO_OPT_OUT: "Do Not Sell or Share My Data",
    Right.RIGHT_TO_DELETE: "Delete My Data",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

# Every card on the landing page, as displayed -> the Right it maps to. No running path (NOT_AUTOMATABLE);
# this only documents the page. The card selector has not been captured yet.
PAGE_RIGHTS = {
    "Access My Data": Right.RIGHT_TO_ACCESS,
    "Do Not Sell or Share My Data": Right.RIGHT_TO_OPT_OUT,
    "Delete My Data": Right.RIGHT_TO_DELETE,
}
RIGHTS_OPTIONS_CSS = ""  # TODO(health-check): capture the card-title selector on a live run


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
    await SuperScraper.screenshot(tab, f"dry_run_{label}")
    print(
        f"\n'{card_text}' email entered but NOT sent — click 'Send Me A Code' yourself, "
        "enter the code you receive, and continue. This sends a real verification code "
        "regardless of DRY_RUN, so it is never done automatically."
    )


async def main():
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await submit_request(tab, RIGHT_MAP[right], super_scraper)


asyncio.run(main())

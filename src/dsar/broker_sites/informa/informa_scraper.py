# informa.com — custom Informa privacy portal (not OneTrust, despite the
# privacy.informa.com hostname). The page itself is a very long privacy
# policy with no visible form; a "Privacy Request" button (id="modal-select-
# subject") opens a two-step modal wizard instead. Step 1 asks "I am a" —
# defaults to "Recipient of Marketing Communications" since none of the
# other options (Customer, Prospective Employee, Employee, Contractor) fit a
# generic data subject. Step 2 offers 5 request cards, one per pass: Obtain a
# copy of my data (Access), Update inaccuracies (Correct, not automated),
# Unsubscribe Request (Opt-Out marketing), Do not sell my personal data
# (Opt-Out sale), Delete my data. Which run is decided only by
# SuperScraper.rights_to_exercise.
#
# Selecting a card immediately prompts for an email to send a verification
# link to ("Enter your email here to verify your identity") — clicking "Send
# Email" triggers a real email send, so this scraper types the email in and
# stops there regardless of DRY_RUN. The rest of the form (name/address,
# etc.) only appears after clicking the emailed link, which must be done
# manually.
#
# Page elements:
#   #modal-select-subject                   "Privacy Request" button (opens wizard)
#   "Recipient of Marketing Communications" step 1 "I am a" choice
#   request cards (text in RIGHT_MAP)       step 2 request type
#   [aria-label="Email Address"]            email to send the verification link to
#                                           (fallback: first input[type=email|text])
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://privacy.informa.com/policies/en/"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["Obtain a copy of my data"],
    Right.RIGHT_TO_OPT_OUT: ["Unsubscribe Request", "Do not sell my personal data (CCPA/CPRA)"],
    Right.RIGHT_TO_DELETE: ["Delete my data"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def submit_request(tab, right, card_text, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    modal_btn = await tab.find(id="modal-select-subject", raise_exc=False)
    if not modal_btn:
        print(f"{super_scraper.OOPS} 'Privacy Request' button not found")
        return
    await modal_btn.click()
    await asyncio.sleep(1)

    subject = await tab.find(text="Recipient of Marketing Communications", raise_exc=False)
    if subject:
        await subject.click()
    await asyncio.sleep(2)

    card = await tab.find(text=card_text, raise_exc=False)
    if not card:
        print(f"{super_scraper.OOPS} Request card '{card_text}' not found")
        return
    await card.click()
    await asyncio.sleep(2)

    label = "".join(c if c.isalnum() else "_" for c in card_text.lower())[:40].strip("_")

    email_field = await tab.find(**{"aria-label": "Email Address"}, raise_exc=False)
    if not email_field:
        email_field = await tab.find(xpath="//input[@type='email' or @type='text']", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}_{label}")
    print(
        f"\n'{card_text}' ready but NOT sent — click 'Send Email' yourself, check your "
        "inbox for the verification link, click it, and complete whatever form follows "
        "manually. This sends a real email regardless of DRY_RUN, so it is never done "
        "automatically."
    )


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for card_text in RIGHT_MAP[right]:
                await submit_request(tab, right, card_text, super_scraper)


asyncio.run(main())

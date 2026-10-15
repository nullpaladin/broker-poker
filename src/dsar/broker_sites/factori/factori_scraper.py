# factori.ai — /opt-out/ embeds a Google Form (navigated to directly). Opt-out
# only: no rights selector, just contact + device-ID + message fields, so it
# maps to a Do-Not-Sell / Opt-Out request. Every other right is email-only
# (privacy@factori.ai); a prior emailed request got a receipt but no real
# response — see README.
# Questions (all required, all short-answer text):
#   Name, Email, Country, Mobile Advertising ID, Message.
# Google Form text inputs have no aria-label, so each is reached by an xpath
# scoped to its question's role="listitem" container. No CAPTCHA.
#
# Page elements:
#   Name / Email / Country / Mobile Advertising ID   short-answer inputs (by question text)
#   Message                                           paragraph textarea (by question text)
#   "Submit" button                                   div[role=button] span
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

RIGHT_MAP = {Right.RIGHT_TO_OPT_OUT: "opt-out"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSenQ43-rKbEqNWX8jUhKaXWpxzs4G5NLNFaU1-ML9htK-OmLQ/viewform"
)


async def fill_text(tab, super_scraper, question, value, para=False):
    if not value:
        return
    tag = "textarea" if para else "input"
    xpath = (
        f"//div[@role='listitem'][.//span[contains(normalize-space(.), {question!r})]]//{tag}"
    )
    field = await tab.find(xpath=xpath, raise_exc=False)
    if not field:
        print(f"{super_scraper.OOPS} field for {question!r} not found")
        return
    await field.click()
    await tab.keyboard.type_text(text=value)
    await asyncio.sleep(0.3)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

    full_name = " ".join(p for p in (SuperScraper.FIRST_NAME, SuperScraper.LAST_NAME) if p)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(FORM_URL)
        await asyncio.sleep(5)

        await fill_text(tab, super_scraper, "Name", full_name)
        await fill_text(tab, super_scraper, "Email", SuperScraper.EMAIL)
        await fill_text(tab, super_scraper, "Country", "United States")
        await fill_text(tab, super_scraper, "Mobile Advertising ID", SuperScraper.ADVERTISING_ID)
        await fill_text(
            tab, super_scraper, "Message",
            SuperScraper.request_statement(rights, broker="Factori"),
        )

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit opt-out for {SuperScraper.EMAIL}")
            return

        submit = await tab.find(xpath="//div[@role='button']//span[normalize-space(.)='Submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(f"Submitted opt-out for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())

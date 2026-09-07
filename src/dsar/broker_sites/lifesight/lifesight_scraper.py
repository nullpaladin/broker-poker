# lifesight.io — /opt-out/ embeds a Google Form (navigated to directly). This
# form is opt-out only: it has no rights selector, just contact + device-ID
# fields, so it maps to a Do-Not-Sell / Opt-Out request. Every other right is
# email-only (privacy@lifesight.io) and has gone unanswered — see README.
# Questions (all short-answer text except Message which is a paragraph):
#   Name (required), Email (required), Country, Mobile Advertising ID, Message.
# Google Form text inputs have no aria-label, so each is reached by an xpath
# scoped to its question's role="listitem" container. No CAPTCHA.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSdBAQskPxxBeztX9e2tt8U5kmLDsYIExqIVSiaxyO3QLW6Q7A/viewform"
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
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

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
            "I am exercising my right to opt out of the sale/sharing of my personal "
            "information and to direct you not to process it for targeted advertising.",
            para=True,
        )

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/lifesight_dry_run.png", beyond_viewport=True)
        print("Screenshot saved to resources/screenshots/lifesight_dry_run.png")

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit opt-out for {full_name} <{SuperScraper.EMAIL}>")
            return

        submit = await tab.find(xpath="//div[@role='button']//span[normalize-space(.)='Submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(f"Submitted opt-out for {full_name}")


asyncio.run(main())

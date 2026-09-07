# databaseusa.com — Contact Form 7 "MCDPA Request Page" (Minnesota Consumer
# Data Privacy Act). A single generic request form (no discrete Access/
# Delete/Opt-Out picker) covering all 7 MCDPA rights at once (know/access,
# delete, correct, data portability, opt out of targeted advertising, opt
# out of sale, opt out of profiling) via one Email/Full Name/State
# submission. The CF7 form key is literally "email-authentication" — this is
# an email-verification gate (fill in and a verification link is emailed),
# so this scraper fills the fields and stops there regardless of DRY_RUN;
# clicking Send actually triggers that email and must be done manually.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://privacycompliance.biz/databaseusa-mcdpa/"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        email_field = await tab.find(xpath="//input[@name='email']", raise_exc=False)
        name_field = await tab.find(xpath="//input[@name='fullname']", raise_exc=False)
        state_select = await tab.find(id="state", raise_exc=False)

        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)
        if name_field:
            await name_field.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        if state_select:
            state_abbr = SuperScraper.STATE_ABBREVIATED
            await state_select.execute_script(
                "for (var i=0;i<this.options.length;i++){"
                f"  if(this.options[i].value==={state_abbr!r}){{ this.selectedIndex=i; }}"
                "}"
                "this.dispatchEvent(new Event('change', {bubbles:true}));"
            )

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/databaseusa_dry_run.png")
        print(
            "\nMCDPA request form filled but NOT sent — click 'Send' yourself, check your "
            "inbox for the verification link, and click it to complete the request. This "
            "sends a real verification email regardless of DRY_RUN, so it is never done "
            "automatically."
        )


asyncio.run(main())

# liveintent.com — https://privacy.liveintent.com/ . The entire portal is a
# single email field: "provide an email address. We will then email you a
# personalized link to login to our secure privacy portal." The specific rights
# (access / delete / opt-out) are then chosen inside that emailed portal, which
# a human must complete.
#
# Submitting this form sends a real verification email, so the scraper fills the
# email field and stops there regardless of DRY_RUN — it never clicks Submit.
# No CAPTCHA.
#
# Page elements:
#   input[type=email] / input[name=email]   The portal's only field: email address
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.super_scraper import SuperScraper

URL = "https://privacy.liveintent.com/"


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        email = await tab.find(xpath="//input[@type='email' or @name='email']", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)
        else:
            print(f"{super_scraper.OOPS} email field not found")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run")
        print(
            f"Email {SuperScraper.EMAIL} entered but NOT submitted — clicking Submit sends a "
            "real verification email. Do that yourself, then follow the personalized link to "
            "the privacy portal and select the right(s) to exercise."
        )


asyncio.run(main())

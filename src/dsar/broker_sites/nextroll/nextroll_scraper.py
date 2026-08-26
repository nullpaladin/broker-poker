# nextroll.com — the nextroll.com landing page links out to two other
# domains rather than hosting its own form:
# (1) app.adroll.com/optout — the primary consumer opt-out mechanism, with
#     a "Web Browser Opt-Out" Allow/Opt-Out toggle (sets a local
#     "opt_out" cookie, no PII/network submission involved — clicked
#     unconditionally regardless of DRY_RUN since it has no server-side
#     effect on personal data) plus a secondary "Email Opt-Out" for
#     NextRoll's B2B "Contact Data" product (business email + reCAPTCHA,
#     no visible Submit button — appears to submit via the reCAPTCHA
#     callback itself, so filled and left for manual solve).
# (2) nextroll-privacy.relyance.ai (Relyance AI portal) — offers a formal
#     "Verify Identity to Make Request(s)" flow, but requires an AdRoll
#     "Advertiser Identifier" that only existing AdRoll/RollWorks account
#     holders have (the last 22 characters of their dashboard URL) — not
#     something a generic consumer persona can provide, so this flow is
#     not exercised.
# There is no Access or Delete mechanism anywhere in this flow — NextRoll
# only offers opt-out here.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://app.adroll.com/optout"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        # NOT tab.find(text="Opt-Out") — the page heading is also literally
        # "Opt-Out" and matches first, which isn't clickable/visible in the
        # way pydoll expects. Target the actual <button> tag.
        opt_out_btn = await tab.find(xpath="//button[normalize-space()='Opt-Out']", raise_exc=False)
        if opt_out_btn:
            await opt_out_btn.click()
            print("Clicked the Web Browser Opt-Out toggle (sets a local opt_out cookie).")
        else:
            print(f"{super_scraper.OOPS} Web Browser Opt-Out toggle not found")

        email_field = await tab.find(xpath="//input[@name='email']", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/nextroll_dry_run.png")
        print("Screenshot saved to resources/screenshots/nextroll_dry_run.png")
        print(
            "\nBusiness-email opt-out field filled but NOT submitted — a reCAPTCHA v2 "
            "checkbox is present with no separate Submit button (submission appears to be "
            "triggered by the reCAPTCHA callback itself), and requires a manual solve."
        )


asyncio.run(main())

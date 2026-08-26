# audisense.com (Audiense) — form is actually hosted/operated by Buxton
# (posts to privacy.buxtonco.com/privacy). Server-rendered, single submission
# with checkboxes selecting which rights apply: IsRightToKnow, IsRightToAccess,
# IsOptOutRequest unconditionally; IsDeleteRequest gated on REMOVE_INFORMATION.
# reCAPTCHA Enterprise is invisible (badge only) and auto-resolves before submit.
# Cookie consent (WP Consent Wall) renders inside a shadow root on
# #wpconsent-container — not reachable via normal DOM queries, so it's
# dismissed via a direct shadowRoot script instead of tab.find().
#
# BLOCKER: the form requires uploading "two forms of identification... at
# least one being a copy of a government issued ID" (File1 is a required file
# input) to verify identity. This tool has no access to — and should not be
# storing — photo ID documents, so this scraper fills every other field and
# stops there; a human must attach their own ID photos, pick the correct
# "Company" (Buxton vs Elevar — unclear which applies without more research),
# and submit manually.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.audiense.com/legal/consumer-personal-information-requests/"

RIGHT_CHECKBOXES = ["IsRightToKnow", "IsRightToAccess", "IsOptOutRequest"]
DELETE_CHECKBOX = "IsDeleteRequest"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(4)

        # Cookie consent (WP Consent Wall) renders inside a shadow root — not
        # reachable via normal DOM queries/pydoll find().
        await tab.execute_script(
            "var host = document.getElementById('wpconsent-container'); "
            "if(host && host.shadowRoot){ "
            "  var btns = Array.from(host.shadowRoot.querySelectorAll('button')); "
            "  var b = btns.find(x=>x.textContent.trim().toLowerCase()==='accept all'); "
            "  if(b) b.click(); "
            "}"
        )
        await asyncio.sleep(1)

        checkboxes = list(RIGHT_CHECKBOXES)
        if SuperScraper.REMOVE_INFORMATION:
            checkboxes.append(DELETE_CHECKBOX)
        for name in checkboxes:
            box = await tab.find(name=name, raise_exc=False)
            if box:
                await box.click()
                await asyncio.sleep(0.3)

        text_fields = [
            ("FirstName", SuperScraper.FIRST_NAME),
            ("LastName", SuperScraper.LAST_NAME),
            ("PrimaryEmail", SuperScraper.EMAIL),
            ("PrimaryPhone", SuperScraper.PHONE_NUMBER),
            ("HomeAddress", SuperScraper.ADDRESS),
            ("City", SuperScraper.CITY),
            ("Zip", SuperScraper.ZIP_CODE),
            ("JurisdictionOfResidence", SuperScraper.STATE),
        ]
        for name, value in text_fields:
            field = await tab.find(name=name, raise_exc=False)
            if field:
                await field.type_text(value)
                await asyncio.sleep(0.2)

        state_abbrev = await SuperScraper.state_full_name_to_abbreviated(SuperScraper.STATE)
        await tab.execute_script(
            f'var s = document.querySelector("select[name=PersonalState]"); '
            f's.value = "{state_abbrev}"; s.dispatchEvent(new Event("change"));'
        )

        if SuperScraper.ADVERTISING_ID:
            maid = await tab.find(name="MobileAdvertisingId", raise_exc=False)
            if maid:
                await maid.type_text(SuperScraper.ADVERTISING_ID)

        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/audisense_prefilled.png")
        print("Screenshot saved to resources/screenshots/audisense_prefilled.png")
        print(
            "\nForm pre-filled but NOT submitted. audisense.com's DSAR form (hosted by "
            "Buxton) requires uploading photo ID to verify identity, which this tool "
            "cannot supply. Review the form, select the correct Company (Buxton/Elevar), "
            "attach your own ID photos, and submit manually."
        )


asyncio.run(main())

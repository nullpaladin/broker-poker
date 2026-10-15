# audisense.com (Audiense) — form is actually hosted/operated by Buxton
# (posts to privacy.buxtonco.com/privacy). Server-rendered, single submission
# with checkboxes selecting which rights apply: IsRightToKnow + IsRightToAccess (Access),
# IsOptOutRequest (Opt-out), IsDeleteRequest (Delete); which are ticked is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
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
#
# Page elements (keep this list current):
#   #wpconsent-container (shadow root)  Cookie consent -> "Accept all" button
#   name=IsRightToKnow / IsRightToAccess  Access checkboxes
#   name=IsOptOutRequest        Opt-out checkbox
#   name=IsDeleteRequest        Delete checkbox
#   name=FirstName / LastName   First / Last name
#   name=PrimaryEmail           Email
#   name=PrimaryPhone           Phone
#   name=HomeAddress / City / Zip   Address, City, Zip code
#   name=JurisdictionOfResidence  Jurisdiction of residence (state)
#   select[name=PersonalState]  State (abbreviation)
#   name=MobileAdvertisingId    Mobile advertising ID (optional)
#   File1                       Required ID upload (NOT filled — see BLOCKER)
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.audiense.com/legal/consumer-personal-information-requests/"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: ["IsRightToKnow", "IsRightToAccess"],
    Right.RIGHT_TO_OPT_OUT: ["IsOptOutRequest"],
    Right.RIGHT_TO_DELETE: ["IsDeleteRequest"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()

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

        checkboxes = [entry for right in rights for entry in RIGHT_MAP[right]]
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

        state_abbrev = SuperScraper.STATE_ABBREVIATED
        state_select = await tab.find(xpath="//select[@name='PersonalState']", raise_exc=False)
        if state_select:
            await js_utils.select_native_option(state_select, value=state_abbrev, dispatch=("change",))

        if SuperScraper.ADVERTISING_ID:
            maid = await tab.find(name="MobileAdvertisingId", raise_exc=False)
            if maid:
                await maid.type_text(SuperScraper.ADVERTISING_ID)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "prefilled")
        print(
            "\nForm pre-filled but NOT submitted. audisense.com's DSAR form (hosted by "
            "Buxton) requires uploading photo ID to verify identity, which this tool "
            "cannot supply. Review the form, select the correct Company (Buxton/Elevar), "
            "attach your own ID photos, and submit manually."
        )


asyncio.run(main())

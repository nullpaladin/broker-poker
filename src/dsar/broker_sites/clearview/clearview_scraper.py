# clearview.ai — /privacy-and-requests lists per-state buttons (Access/
# Delete/Do Not Sell/Correct/Opt-Out of Profiling/Appeal), but for a given
# state every button shares the exact same target="_blank" OneTrust webform
# URL (confirmed by inspecting the underlying <a href> — Minnesota's ACCESS
# and DELETE both point to the identical webform), so this scraper navigates
# straight to that URL instead of clicking through the marketing page.
#
# The form asks for State (vt-autocomplete combobox, same pattern as other
# OneTrust webforms in this repo) and Email — selecting a State reveals a
# "Select request type(s)" grid that's genuinely multi-select (confirmed via
# aria-selected staying true on multiple options after sequential clicks,
# unlike billtrust.com's near-identical-looking but actually single-select
# grid), so all selected rights go into a single pass. Critically, the form ALSO
# requires uploading "a clear image of your face" (a redacted photo of your
# ID if requesting Access) — Clearview identifies people by image, not by
# name/email, so there is no legitimate photo this scraper can supply. This
# scraper fills State, request type(s), Email, and the required
# "I acknowledge" listbox option (same role="option"/role="listbox" pattern
# as billtrust.com), then stops — the photo upload and Submit must be done
# manually.
#
# Page elements:
#   #formField78DSARElement                      State (vt-autocomplete combobox)
#   .vt-option (text = STATE)                    State dropdown option
#   div[role=option][aria-label=...]             "Select request type(s)" grid: "Access",
#                                                "Do not Sell/Share", "Delete/Opt-Out"
#   #emailDSARElement                            Email
#   div[role=option][aria-label="I acknowledge"] Required acknowledgement listbox option
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://privacyportal.onetrust.com/webform/1fdd17ee-bd10-4813-a254-de7d5c09360a/7c79cae5-6e86-4d8d-b409-7a932c09b942"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Access",
    Right.RIGHT_TO_OPT_OUT: "Do not Sell/Share",
    Right.RIGHT_TO_DELETE: "Delete/Opt-Out",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Recorded request types are aria-labels; the visible text may differ, so they are not copied in.)

FIELD_XPATHS = {
    "State": "//*[@id='formField78DSARElement']",
    "Email": "//*[@id='emailDSARElement']",
}


async def main():
    super_scraper = SuperScraper()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(6)

        state_field = await tab.find(id="formField78DSARElement", raise_exc=False)
        if state_field:
            await state_field.click()
            await tab.keyboard.type_text(SuperScraper.STATE)
            await asyncio.sleep(1.5)
            state_opt = await tab.find(
                xpath=f"//*[contains(@class,'vt-option') and contains(text(),'{SuperScraper.STATE}')]",
                raise_exc=False,
            )
            if state_opt:
                await state_opt.click()
                await asyncio.sleep(1)

        request_types = [RIGHT_MAP[right] for right in rights]
        for request_type in request_types:
            opt = await tab.find(
                xpath=f"//div[@role='option' and @aria-label='{request_type}']", raise_exc=False
            )
            if opt:
                await opt.click_using_js()
                await asyncio.sleep(0.3)

        email_field = await tab.find(id="emailDSARElement", raise_exc=False)
        if email_field:
            await email_field.type_text(SuperScraper.EMAIL)

        acknowledge = await tab.find(xpath="//div[@role='option' and @aria-label='I acknowledge']", raise_exc=False)
        if acknowledge:
            await acknowledge.click_using_js()

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_" + "_".join(r.value for r in rights))
        print(
            "\nForm filled but NOT submitted — Clearview identifies people by image, not name/"
            "email, and requires uploading a clear photo of your face (a redacted photo of your "
            "ID if requesting Access) to process any request. There is no legitimate photo for "
            "this scraper to supply, so uploading it and clicking Submit must be done manually."
        )


asyncio.run(main())

# yellowpages.com (Thryv, Inc.) — OneTrust CDN Angular DSAR form. Exercises
# Data Request (Access), Opt-Out (via additional info, no dedicated button),
# and Delete. Which of them run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Opt-out has no request type of its own: it is stated in "Additional Request Information"
# on the Data Request (Access) submission, so it is sent only together with Access.
# Subject: "Myself" + role "Consumer"
# + site picker "I am not a registered user of any of these sites or apps."
# Country and state are autocomplete comboboxes (keyboard nav: ArrowDown+Enter).
# captchaCode image CAPTCHA requires manual entry in live mode.
#
# Page elements:
#   [aria-label="Myself"] / [aria-label="Consumer"]   Subject / role buttons
#   [aria-label="I am not a registered user of any of these sites or apps."]   Site picker
#   #firstNameDSARElement / #lastNameDSARElement   First / Last name
#   #emailDSARElement                              Email
#   #countryDSARElement / #stateDSARElement        Country / State autocomplete comboboxes
#   #cityDSARElement / #zipDSARElement             City / Zip
#   [aria-label="Data Request"] / [aria-label="Delete Data"]   Request-type buttons
#   Data Request sub-options (aria-label): "The categories of your personal information we
#       collected, sold, or shared", "The specific pieces of your personal information we
#       collected", "List of 3rd Parties to Whom Data was Sold/Shared"
#   [aria-label="Additional Request Information (if any)"]   Free-text box (Data Request only)
#   #captchaCode                                   Image CAPTCHA code (manual entry)
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.constants import Key

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/dd6500c7-03cb-45b0-8bed-97ece55a892d/cfcefb69-41db-4aee-bd00-c702df72ee0f.html"

ADDITIONAL_INFO_LABEL = "Additional Request Information (if any)"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "Data Request",
    # No request type of its own: stated in the Data Request form's free-text box.
    Right.RIGHT_TO_OPT_OUT: ADDITIONAL_INFO_LABEL,
    Right.RIGHT_TO_DELETE: "Delete Data",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def fill_and_submit(tab, right, request_type_label, additional_info, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    myself_btn = await tab.find(**{"aria-label": "Myself"}, raise_exc=False)
    if myself_btn:
        await myself_btn.click_using_js()
    await asyncio.sleep(0.5)

    consumer_btn = await tab.find(**{"aria-label": "Consumer"}, raise_exc=False)
    if consumer_btn:
        await consumer_btn.click_using_js()
    await asyncio.sleep(0.5)

    not_registered = await tab.find(
        **{"aria-label": "I am not a registered user of any of these sites or apps."},
        raise_exc=False,
    )
    if not not_registered:
        not_registered = await tab.find(
            **{"aria-label": "I am not a registered user of any of these sites or apps"},
            raise_exc=False,
        )
    if not_registered:
        await not_registered.click_using_js()
    await asyncio.sleep(0.5)

    first = await tab.find(id="firstNameDSARElement", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)

    last = await tab.find(id="lastNameDSARElement", raise_exc=False)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)

    email = await tab.find(id="emailDSARElement", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    country_field = await tab.find(id="countryDSARElement", raise_exc=False)
    if country_field:
        await country_field.click()
        await tab.keyboard.type_text("United States")
        await asyncio.sleep(2)
        await tab.keyboard.press(Key.ARROWDOWN)
        await asyncio.sleep(0.3)
        await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(1)

    state_field = await tab.find(id="stateDSARElement", raise_exc=False)
    if state_field:
        await state_field.click()
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(2)
        await tab.keyboard.press(Key.ARROWDOWN)
        await asyncio.sleep(0.3)
        await tab.keyboard.press(Key.ENTER)
    await asyncio.sleep(0.5)

    city = await tab.find(id="cityDSARElement", raise_exc=False)
    if city:
        await city.type_text(SuperScraper.CITY)

    zip_field = await tab.find(id="zipDSARElement", raise_exc=False)
    if zip_field:
        await zip_field.type_text(SuperScraper.ZIP_CODE)

    req_btn = await tab.find(**{"aria-label": request_type_label}, raise_exc=False)
    if req_btn:
        await req_btn.click_using_js()
    await asyncio.sleep(1)

    if right == Right.RIGHT_TO_ACCESS:
        # Select all data request sub-options
        for sub_label in [
            "The categories of your personal information we collected, sold, or shared",
            "The specific pieces of your personal information we collected",
            "List of 3rd Parties to Whom Data was Sold/Shared",
        ]:
            sub_btn = await tab.find(**{"aria-label": sub_label}, raise_exc=False)
            if sub_btn:
                await sub_btn.click_using_js()
                await asyncio.sleep(0.3)

        if additional_info:
            additional = await tab.find(**{"aria-label": ADDITIONAL_INFO_LABEL}, raise_exc=False)
            if additional:
                await additional.type_text(additional_info)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL}")
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        return

    print(f"\nForm filled for '{request_type_label}'.")
    print("Enter the CAPTCHA code shown in the image into the captchaCode field,")
    print("then click Submit. Press Enter after the confirmation page appears...")
    input()
    print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    if SuperScraper.bail_if_not_automatable(globals()):
        return
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    # Opt-out rides along in the Access submission's free-text box; it is not a submission itself.
    additional_info = (
        SuperScraper.request_statement([Right.RIGHT_TO_OPT_OUT], broker="Yellowpages")
        if Right.RIGHT_TO_OPT_OUT in rights else None
    )
    submit_rights = [r for r in rights if r != Right.RIGHT_TO_OPT_OUT]
    if additional_info and Right.RIGHT_TO_ACCESS not in submit_rights:
        print("Opt-out is only sent together with a Data Request (Access) submission — not requested this run.")
    if not submit_rights:
        print("Nothing to submit.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in submit_rights:
            await fill_and_submit(tab, right, RIGHT_MAP[right], additional_info, super_scraper)


asyncio.run(main())

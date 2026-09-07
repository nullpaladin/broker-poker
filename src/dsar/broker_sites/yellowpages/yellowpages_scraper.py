# yellowpages.com (Thryv, Inc.) — OneTrust CDN Angular DSAR form. Exercises
# Data Request (Access), Opt-Out (via additional info, no dedicated button),
# and Delete (gated on REMOVE_INFORMATION). Subject: "Myself" + role "Consumer"
# + site picker "I am not a registered user of any of these sites or apps."
# Country and state are autocomplete comboboxes (keyboard nav: ArrowDown+Enter).
# captchaCode image CAPTCHA requires manual entry in live mode.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.constants import Key

from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/dd6500c7-03cb-45b0-8bed-97ece55a892d/cfcefb69-41db-4aee-bd00-c702df72ee0f.html"


def _build_additional_info():
    rights = ["Right to Opt-Out of the sale or sharing of my personal data"]
    return (
        "I am also exercising the following rights not listed above: "
        + "; ".join(rights) + "."
    )


async def fill_and_submit(tab, request_type_label, screenshot_label, super_scraper):
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

    if screenshot_label == "access":
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

        additional = await tab.find(
            **{"aria-label": "Additional Request Information (if any)"}, raise_exc=False
        )
        if additional:
            await additional.type_text(_build_additional_info())

    if SuperScraper.DRY_RUN:
        print(
            f"DRY RUN: would submit '{request_type_label}' for "
            f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
        )
        captcha_field = await tab.find(id="captchaCode", raise_exc=False)
        if captcha_field:
            await captcha_field.scroll_into_view()
        await asyncio.sleep(1)
        await tab.take_screenshot(f"resources/screenshots/yellowpages_dry_run_{screenshot_label}.png")
        print(f"Screenshot saved to resources/screenshots/yellowpages_dry_run_{screenshot_label}.png")
        return

    print(f"\nForm filled for '{request_type_label}'.")
    print("Enter the CAPTCHA code shown in the image into the captchaCode field,")
    print("then click Submit. Press Enter after the confirmation page appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted '{request_type_label}' for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for '{request_type_label}' — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    # (aria-label, screenshot label)
    requests = [("Data Request", "access")]
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(("Delete Data", "delete"))

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for req_label, screenshot_label in requests:
            await fill_and_submit(tab, req_label, screenshot_label, super_scraper)


asyncio.run(main())

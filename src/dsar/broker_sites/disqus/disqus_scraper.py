# disqus.com — OneTrust CDN Angular DSAR form. Rights the form exposes (and we map):
# access, do not sell/share, opt-out of sensitive personal information, delete. Which
# of them run is decided ONLY by SuperScraper.rights_to_exercise(RIGHT_MAP).
# Subject type "Disqus User" and request type buttons are Angular role="button" divs —
# click via click_using_js(). Country and State are autocomplete comboboxes (type then
# click the matching option). reCAPTCHA v2 requires manual solve before submit.
#
# Page elements:
#   [aria-label="Disqus User"]       Subject type button
#   [aria-label=<request type>]      Request type buttons (labels in RIGHT_MAP)
#   #firstNameDSARElement / #lastNameDSARElement / #emailDSARElement   First / Last name, Email
#   #countryDSARElement              Country combobox -> "United States"
#   #stateDSARElement                State combobox (appears after country is chosen)
#   [aria-label="click to submit form"]   Submit button
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://privacyportal-cdn.onetrust.com/dsarwebform/bc2d3301-11a5-4de5-b15e-ce796187a352/9a049fa1-37af-4598-a87a-d0df2e2d904b.html"

# (aria-label, screenshot label)
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("Request a copy of personal information", "access")],
    Right.RIGHT_TO_OPT_OUT: [
        ("Do not sell or share my information", "optout"),
        ("Opt out of use of my sensitive personal information", "sensitive"),
    ],
    Right.RIGHT_TO_DELETE: [("Delete my personal information", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (Recorded request types are aria-labels; the visible text may differ, so they are not copied in.)

FIELD_XPATHS = {
    "First name": "//*[@id='firstNameDSARElement']",
    "Last name": "//*[@id='lastNameDSARElement']",
    "Email": "//*[@id='emailDSARElement']",
    "Country": "//*[@id='countryDSARElement']",
    "State": "//*[@id='stateDSARElement']",
}


async def submit_request(tab, right, aria_label, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    subject_btn = await tab.find(**{"aria-label": "Disqus User"}, raise_exc=False)
    if subject_btn:
        await subject_btn.click_using_js()
    await asyncio.sleep(1)

    req_btn = await tab.find(**{"aria-label": aria_label}, raise_exc=False)
    if not req_btn:
        print(f"{super_scraper.OOPS} Request button '{aria_label}' not found")
        return
    await req_btn.click_using_js()
    await asyncio.sleep(1)

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
        country_opt = await tab.find(text="United States", raise_exc=False)
        if country_opt:
            await country_opt.click()
    await asyncio.sleep(1)

    # State field only appears after country is selected
    state_field = await tab.find(id="stateDSARElement", raise_exc=False)
    if state_field:
        await state_field.click()
        await tab.keyboard.type_text(SuperScraper.STATE)
        await asyncio.sleep(2)
        state_opt = await tab.find(text=SuperScraper.STATE, raise_exc=False)
        if state_opt:
            await state_opt.click()
    await asyncio.sleep(0.5)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        submit_btn = await tab.find(**{"aria-label": "click to submit form"}, raise_exc=False)
        if submit_btn:
            await submit_btn.scroll_into_view()
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{label}")
        print(f"DRY RUN: would submit '{right.name}' ({aria_label}) for {SuperScraper.EMAIL}")
        return

    print(f"\nForm filled for '{aria_label}'.")
    print("Solve the reCAPTCHA in the browser, then click Submit.")
    print("Press Enter after the confirmation page appears...")
    input()

    print(f"Submitted '{right.name}' ({aria_label}) for {SuperScraper.EMAIL} — confirm in the browser.")


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
        for right in rights:
            for aria_label, label in RIGHT_MAP[right]:
                await submit_request(tab, right, aria_label, label, super_scraper)


asyncio.run(main())

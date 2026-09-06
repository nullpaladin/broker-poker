# decisionlinks.com — Webflow site with two separate GET forms on one page.
# Both forms reuse the same Webflow template: the checkbox
# `name`/`id` attributes (Agency/Brand/DSP/DMP) are identical across both
# forms but carry different visible labels per form, and one text field's
# `id` ("Contact-Company-Name" on form 1) is mislabeled — its visible label
# reads "State of Residence", not "Company Name". Checkboxes are scoped by
# ancestor::form to disambiguate the duplicated ids.
#
# Form 1 "Opt-Out Request Form": First/Last/Email/State of Residence, plus a
# required opt-out-preference checkbox group — "DMP" is labeled "Opt-Out of
# All the Above", so that single box covers Sale/Sharing, Targeted
# Advertising, and Profiling in one click. Always submitted, ungated.
#
# Form 2 "General Data Rights Request Form": First/Last/Email/State of
# Residence, plus a required rights checkbox group where each right IS
# independently selectable: Agency=Access, DSP=Correct, DMP=Data Portability
# (checked unconditionally), Brand=Delete (checked only when
# REMOVE_INFORMATION is set). Both forms have a reCAPTCHA v2 checkbox
# requiring manual solve in live mode.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.decisionlinks.com/legal-pages/your-privacy-choices"


async def _check(tab, anchor_id, checkbox_name):
    # The real <input type="checkbox"> is visually hidden (opacity:0) — Webflow's
    # custom-checkbox pattern relies on clicking the wrapping <label> instead.
    box = await tab.find(
        xpath=f"//input[@id='{anchor_id}']/ancestor::form//input[@name='{checkbox_name}']/parent::label",
        raise_exc=False,
    )
    if box:
        await box.click()


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(3)

        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='Opt-Out-First-Name']", text=SuperScraper.FIRST_NAME, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='Opt-out-Last-Name']", text=SuperScraper.LAST_NAME, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='Opt-Out-Email']", text=SuperScraper.EMAIL, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='Contact-Company-Name']", text=SuperScraper.STATE, sleep=0.2)
        await _check(tab, "Opt-Out-First-Name", "DMP")  # "Opt-Out of All the Above"

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit opt-out request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(1)
            await tab.take_screenshot(path="resources/screenshots/decisionlinks_dry_run_optout.png")
            print("Screenshot saved to resources/screenshots/decisionlinks_dry_run_optout.png")
        else:
            await super_scraper.click_item_by_xpath(tab=tab, xpath="//input[@id='Opt-Out-First-Name']/ancestor::form//input[@type='submit']", sleep=2)
            print(f"Submitted opt-out request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")

        await tab.go_to(URL)
        await asyncio.sleep(3)

        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='General-Opt-Out-First-Name']", text=SuperScraper.FIRST_NAME, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='General-Opt-out-Last-Name']", text=SuperScraper.LAST_NAME, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='General-Opt-Out-Email']", text=SuperScraper.EMAIL, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='General-Opt-Out-State']", text=SuperScraper.STATE, sleep=0.2)

        await _check(tab, "General-Opt-Out-First-Name", "Agency")  # Access
        await _check(tab, "General-Opt-Out-First-Name", "DSP")  # Correct
        await _check(tab, "General-Opt-Out-First-Name", "DMP")  # Data Portability
        if SuperScraper.REMOVE_INFORMATION:
            await _check(tab, "General-Opt-Out-First-Name", "Brand")  # Delete

        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit Access/Correct/Portability request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
            await asyncio.sleep(1)
            await tab.take_screenshot(path="resources/screenshots/decisionlinks_dry_run_general.png")
            print("Screenshot saved to resources/screenshots/decisionlinks_dry_run_general.png")
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath="//input[@id='General-Opt-Out-First-Name']/ancestor::form//input[@type='submit']", sleep=2)
        print(f"Submitted General Data Rights request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")


asyncio.run(main())

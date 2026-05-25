import asyncio
import time

from src.broker_sites.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

# Target URL for Axciom (OneTrust Privacy Portal)
URL = "https://privacyportal.onetrust.com/webform/342ca6ac-4177-4827-b61e-19070296cbd3/7229a09c-578f-4ac6-a987-e0428a7b877e"


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)

        # Wait for the page to load completely before interacting
        time.sleep(5)

        # --- FORM FILLING START ---
        # NOTE: XPaths/CSS Selectors must be updated based on inspection of the live site.
        # Replicating the structure from example_scraper.py for consistency.

        # Example placeholders for required fields:
        # First Name
        await super_scraper.input_text_field(tab=tab, xpath='//input[@name="firstName"]', text=SuperScraper.FIRST_NAME)
        # Last Name
        await super_scraper.input_text_field(tab=tab, xpath='//input[@name="lastName"]', text=SuperScraper.LAST_NAME)
        # Email (assuming one might be required)
        await super_scraper.input_text_field(tab=tab, xpath='//input[@name="emailAddress"]', text=SuperScraper.EMAIL)

        # Example for a dropdown selection (if present)
        # await choose_dropdown_option_by_xpath(
        #     tab=tab,
        #     input_css_selector='//select[@name="country"]',
        #     dropdown_item_xpath='//option[text()="United States"]', # Placeholder
        # )

        # --- OPT-IN/OUT SELECTIONS (Based on typical privacy portal flow) ---
        
        # Example: Clicking a consent checkbox/button
        # Replace with actual XPath for the primary action button/checkbox
        await super_scraper.click_item_by_text(tab=tab, text='Submit Request') # Placeholder text
        
        # If there are specific consent checkboxes, they would go here:
        # await super_scraper.click_checkbox(tab=tab, selector='//input[@id="consent_marketing"]')

        # --- END FORM FILLING ---

        await asyncio.sleep(5)


async def choose_dropdown_option_by_xpath(tab, input_css_selector, dropdown_item_xpath, sleep=0):
    """Helper function to select an option from a dropdown."""
    input_field = await tab.find(
        css=input_css_selector,
        timeout=3,
        raise_exc=False
    )
    if not input_field:
        print(f"The input field with css selector {input_css_selector} was not found.")
        return

    if sleep:
        time.sleep(sleep)

    await input_field.click()
    dropdown_option = await tab.find(
        xpath=dropdown_item_xpath,
        timeout=3,
        raise_exc=False
    )
    if not dropdown_option:
        print(f"The dropdown option with xpath {dropdown_item_xpath} was not found.")
        return

    if sleep:
        time.sleep(sleep)

    await dropdown_option.click()

asyncio.run(main())
import asyncio
from pydoll.browser.chromium import Chrome


async def save_page_bundle(tab):
    """Saves the current state of the tab as a zip bundle using pydoll's native function."""
    try:
        # Use the native save_bundle method available on the Tab object
        filename = "sabioctv_page_bundle"
        await tab.save_bundle(filename)
        print(f"Successfully saved page content bundle to {filename}.zip")
        return True
    except Exception as e:
        print(f"Error saving page bundle: {e}")
        return False


# Helper to run the async function if needed outside the main scraper flow
async def run_saver(browser, tab):
    await save_page_html(browser, tab)

import asyncio
import os

import dotenv
from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

dotenv.load_dotenv()

URL = "https://preferences.crunchbase.com/?locationCode=US-MN"


async def main():
    options = ChromiumOptions()
    options.binary_location = os.getenv("CHROMIUM_LOCATION")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,900")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(8)

        # Click "Start Access Request"
        start_btn = await tab.find(text="Start Access Request", raise_exc=False)
        if start_btn:
            await start_btn.scroll_into_view()
            await asyncio.sleep(0.5)
            await start_btn.click_using_js()
            await asyncio.sleep(8)

        # Try JS focus then keyboard type
        await tab.execute_script(
            "document.querySelector('input[name=\"first_name\"]').focus();"
        )
        await asyncio.sleep(0.3)

        focused = await tab.execute_script(
            "var e = document.activeElement; return e ? e.tagName+' name='+e.name : 'none';"
        )
        if isinstance(focused, dict):
            focused = focused.get('result', {}).get('result', {}).get('value', str(focused))
        print(f"Focused after JS focus(): {focused}")

        await tab.keyboard.type_text("John")
        await asyncio.sleep(0.5)

        val = await tab.execute_script(
            "return document.querySelector('input[name=\"first_name\"]').value;"
        )
        if isinstance(val, dict):
            val = val.get('result', {}).get('result', {}).get('value', str(val))
        print(f"Value after JS focus+keyboard.type_text: {val}")

        await tab.take_screenshot("inspect_crunchbase5.png")
        print("Screenshot saved.")


asyncio.run(main())

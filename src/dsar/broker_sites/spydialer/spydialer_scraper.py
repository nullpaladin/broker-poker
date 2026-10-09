# spydialer.com — exercises Delete only (removal tool).
# Navigate directly to wizards.aspx (START on /Consumers/ doesn't navigate reliably via CDP).
# Step 1: select state (SttFltrDrpDwnLst, abbreviation via JS); reCAPTCHA v2 manual solve; CONTINUE.
# Step 2: records list — user finds their record; modal exposes name/contact fields (obfuscated IDs).
# Delete: ctl00_ContentPlaceHolder1_DeleteAllBottomButton → confirm ContinueConfirmButton.
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.spydialer.com/Consumers/wizards.aspx"


async def _select_option(tab, select_id, value):
    result = await tab.execute_script(f"""
        var sel = document.getElementById('{select_id}');
        if (!sel) return 'not found';
        for (var i = 0; i < sel.options.length; i++) {{
            if (sel.options[i].value === '{value}') {{
                sel.selectedIndex = i;
                sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                return 'selected: ' + sel.options[i].text;
            }}
        }}
        return 'option not found: {value}';
    """)
    if isinstance(result, dict):
        msg = result.get('result', {}).get('result', {}).get('value', '')
        print(f"  {select_id}: {msg}")
    await asyncio.sleep(0.5)


RIGHT_MAP = {"delete": "Delete All"}
RIGHTS_SUPPORTED = ("delete",)


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    # Removal tool — Delete only. Skip unless the user actually asked for deletion.
    if not SuperScraper.rights_to_exercise(RIGHT_MAP):
        print("spydialer is delete-only; 'delete' not in REQUESTED_RIGHTS / REMOVE_INFORMATION not set — skipping.")
        return

    state_abbr = SuperScraper.STATE_ABBREVIATED

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(8)

        # Dismiss cookie banner if present
        got_it = await tab.find(text="Got it", raise_exc=False)
        if got_it and await got_it.is_visible():
            await got_it.click()
            await asyncio.sleep(1)

        # State filter (narrows displayed records to your state)
        await _select_option(tab, "SttFltrDrpDwnLst", state_abbr)
        await asyncio.sleep(1)

        if SuperScraper.DRY_RUN:
            submit_btn = await tab.find(
                id="ctl00_ContentPlaceHolder1_StateSubmitButton", raise_exc=False
            )
            if submit_btn:
                await submit_btn.scroll_into_view()
            await SuperScraper.screenshot(tab, "resources/screenshots/spydialer_dry_run.png")
            print(
                f"DRY RUN: would submit state filter for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            print("  Next steps (manual): solve reCAPTCHA → search records → Delete All → confirm")
            return

        # Submit state filter → reCAPTCHA gate → records list appears
        submit_btn = await tab.find(
            id="ctl00_ContentPlaceHolder1_StateSubmitButton", raise_exc=False
        )
        if submit_btn:
            await submit_btn.click()
            await asyncio.sleep(3)

        print("\nState filter submitted. Solve the reCAPTCHA v2 if prompted.")
        print("After records appear, find your record — the name/contact fields will appear in a modal.")
        print("Fill in your details, then click Delete All and confirm.")
        print("Press Enter after the confirmation page appears...")
        input()

        # Attempt delete if button is visible (may have been exposed by user interaction)
        confirmed = False
        delete_btn = await tab.find(
            id="ctl00_ContentPlaceHolder1_DeleteAllBottomButton", raise_exc=False
        )
        if delete_btn and await delete_btn.is_visible():
            await delete_btn.click()
            await asyncio.sleep(2)
            confirm_btn = await tab.find(
                id="ctl00_ContentPlaceHolder1_ContinueConfirmButton", raise_exc=False
            )
            if confirm_btn and await confirm_btn.is_visible():
                await confirm_btn.click()
                await asyncio.sleep(3)
                confirmed = True

        if confirmed:
            print(f"Submitted deletion for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(
                f"{super_scraper.OOPS} Delete/confirm button was not clicked automatically — "
                "complete the deletion in the browser and verify the confirmation page."
            )


asyncio.run(main())

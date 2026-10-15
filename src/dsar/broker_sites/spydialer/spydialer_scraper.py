# spydialer.com — exercises Delete only (removal tool).
# Navigate directly to wizards.aspx (START on /Consumers/ doesn't navigate reliably via CDP).
# Step 1: select state (SttFltrDrpDwnLst, abbreviation via JS); reCAPTCHA v2 manual solve; CONTINUE.
# Step 2: records list — user finds their record; modal exposes name/contact fields (obfuscated IDs).
# Delete: ctl00_ContentPlaceHolder1_DeleteAllBottomButton → confirm ContinueConfirmButton
#   (clicked by the USER, never by the scraper: it deletes whatever the record list shows).
# NEEDS MANUAL REVIEW (PR #54): confirm the list can only contain the user's own records.
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
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


RIGHT_MAP = {Right.RIGHT_TO_DELETE: "Delete All"}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    # Removal tool — Delete only. Skip unless the user asked for RIGHT_TO_DELETE.
    if not SuperScraper.rights_to_exercise(RIGHT_MAP):
        print("spydialer is delete-only; RIGHT_TO_DELETE is not in RIGHTS_TO_EXERCISE — skipping.")
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
            await SuperScraper.screenshot(tab, "dry_run")
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
        print("After records appear, find YOUR record — the name/contact fields appear in a modal.")
        print("Fill in your details, review which records the page will remove, then click")
        print("Delete All and confirm yourself. This scraper does not click Delete All: the button")
        print("acts on whatever the list shows, and the list can include other people's records.")
        print("Press Enter once you have finished...")
        input()
        print(f"Handed off to the browser for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} — "
              "verify the confirmation page yourself.")

asyncio.run(main())

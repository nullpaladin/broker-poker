# instantly.ai — two separate React (MUI) forms, no shared field ids between
# them (each page's inputs use React's auto-generated `:rN:` ids, mapped via
# each form's own <label for="..."> — resolved here per page rather than
# hardcoded blindly). Access form (app.instantly.ai/privacy/data-request):
# First/Last/Email/Country, always submitted. Opt-Out form (.../privacy/opt-out)
# combines Opt-Out of Sale/Sharing AND Deletion into a single submission with
# no way to select just one — "requesting to opt out... and to have my
# personal information deleted" — so the whole thing is gated on
# REMOVE_INFORMATION. Selecting Country (react-select-2) reveals a State
# combobox (react-select-3) — both react-select instances, instance numbers
# observed stable across loads. Cloudflare Turnstile requires manual solve
# in live mode.
#
# NOTE: `tab.find(id=...)` fails on any id containing a colon (React's
# default `:rN:` id format) — pydoll builds a raw CSS selector `#{id}` with
# no escaping, and `#:r2:` is invalid/misinterpreted CSS. Every field here is
# targeted by xpath (`//*[@id='...']`) instead, which takes a different code
# path unaffected by this.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

ACCESS_URL = "https://app.instantly.ai/privacy/data-request"
OPT_OUT_DELETE_URL = "https://app.instantly.ai/privacy/opt-out"


async def _select_react_option(tab, instance_id, text):
    combobox = await tab.find(xpath=f"//*[@id='{instance_id}-input']", raise_exc=False)
    if not combobox:
        return
    await combobox.click()
    await tab.keyboard.type_text(text)
    await asyncio.sleep(1)
    option = await tab.find(
        xpath=f"//*[starts-with(@id,'{instance_id}-option') and contains(text(),'{text}')]",
        raise_exc=False,
    )
    if option:
        await option.click()
        await asyncio.sleep(0.5)


async def _select_country_and_state(tab):
    # Selecting Country (react-select-2) reveals a State combobox
    # (react-select-3) — instance numbers observed stable across loads.
    await _select_react_option(tab, "react-select-2", "United States")
    await _select_react_option(tab, "react-select-3", SuperScraper.STATE)


async def submit_access(tab, super_scraper):
    await tab.go_to(ACCESS_URL)
    await asyncio.sleep(5)

    for field_id, value in [(":r2:", SuperScraper.FIRST_NAME), (":r3:", SuperScraper.LAST_NAME), (":r4:", SuperScraper.EMAIL)]:
        field = await tab.find(xpath=f"//*[@id='{field_id}']", raise_exc=False)
        if field:
            await field.scroll_into_view()
            await field.type_text(value)
            await asyncio.sleep(0.2)

    await _select_country_and_state(tab)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit Access request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/instantly_dry_run_access.png")
        print("Screenshot saved to resources/screenshots/instantly_dry_run_access.png")
        return

    print("\nAccess form filled. Solve the Cloudflare Turnstile challenge, click Affirm & Submit,")
    print("then press Enter once the confirmation appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted Access request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for Access request — verify in browser")


async def submit_opt_out_delete(tab, super_scraper):
    await tab.go_to(OPT_OUT_DELETE_URL)
    await asyncio.sleep(5)

    for field_id, value in [
        (":r2:", SuperScraper.FIRST_NAME),
        (":r3:", SuperScraper.LAST_NAME),
        (":r4:", SuperScraper.COMPANY_NAME),
        (":r5:", SuperScraper.EMAIL),
    ]:
        if not value:
            continue
        field = await tab.find(xpath=f"//*[@id='{field_id}']", raise_exc=False)
        if field:
            await field.scroll_into_view()
            await field.type_text(value)
            await asyncio.sleep(0.2)

    await _select_country_and_state(tab)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit Opt-Out/Delete request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await tab.take_screenshot(path="resources/screenshots/instantly_dry_run_opt_out_delete.png")
        print("Screenshot saved to resources/screenshots/instantly_dry_run_opt_out_delete.png")
        return

    print("\nOpt-Out/Delete form filled. Solve the Cloudflare Turnstile challenge, click Affirm & Submit,")
    print("then press Enter once the confirmation appears...")
    input()

    source = await tab.page_source
    if any(w in source.lower() for w in ("thank", "success", "received", "submitted", "confirmation")):
        print(f"Submitted Opt-Out/Delete request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Confirmation unclear for Opt-Out/Delete request — verify in browser")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await submit_access(tab, super_scraper)
        if SuperScraper.REMOVE_INFORMATION:
            await submit_opt_out_delete(tab, super_scraper)
        else:
            print(
                "Skipping Opt-Out/Delete form — it bundles deletion with no way to opt "
                "out of just that part, and REMOVE_INFORMATION is False."
            )


asyncio.run(main())

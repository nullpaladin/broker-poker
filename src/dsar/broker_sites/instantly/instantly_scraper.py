# instantly.ai — two separate React (MUI) forms, no shared field ids between
# them (each page's inputs use React's auto-generated `:rN:` ids, mapped via
# each form's own <label for="..."> — resolved here per page rather than
# hardcoded blindly). Access form (app.instantly.ai/privacy/data-request):
# First/Last/Email/Country -> RIGHT_TO_ACCESS. Opt-Out form (.../privacy/opt-out)
# combines Opt-Out of Sale/Sharing AND Deletion into a single submission with
# no way to select just one — "requesting to opt out... and to have my
# personal information deleted" — so it is mapped to RIGHT_TO_DELETE only (an
# opt-out request alone must not trigger a deletion). Which run is decided only
# by SuperScraper.rights_to_exercise. Selecting Country (react-select-2) reveals a State
# combobox (react-select-3) — both react-select instances, instance numbers
# observed stable across loads. Cloudflare Turnstile requires manual solve
# in live mode.
#
# NOTE: `tab.find(id=...)` fails on any id containing a colon (React's
# default `:rN:` id format) — pydoll builds a raw CSS selector `#{id}` with
# no escaping, and `#:r2:` is invalid/misinterpreted CSS. Every field here is
# targeted by xpath (`//*[@id='...']`) instead, which takes a different code
# path unaffected by this.
#
# Page elements (React ids `:rN:` mapped per page):
#   Access form (ACCESS_URL):
#     :r2: / :r3: / :r4:           First name / Last name / Email
#     react-select-2 (-input)      Country -> United States
#     react-select-3 (-input)      State (revealed by Country)
#   Opt-Out/Delete form (OPT_OUT_DELETE_URL):
#     :r2: / :r3: / :r4: / :r5:    First name / Last name / Company name (optional) / Email
#     react-select-2 / react-select-3   Country / State, as above
#   "Affirm & Submit" button, Cloudflare Turnstile (manual)
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

ACCESS_URL = "https://app.instantly.ai/privacy/data-request"
OPT_OUT_DELETE_URL = "https://app.instantly.ai/privacy/opt-out"

# Right -> which of the two forms handles it (see header for why only DELETE gets the bundled form).
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "access",
    Right.RIGHT_TO_DELETE: "opt_out_delete",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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
        print(f"DRY RUN: would submit '{Right.RIGHT_TO_ACCESS.name}' for {SuperScraper.EMAIL}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_access")
        return

    print("\nAccess form filled. Solve the Cloudflare Turnstile challenge, click Affirm & Submit,")
    print("then press Enter once the confirmation appears...")
    input()

    print(f"Submitted '{Right.RIGHT_TO_ACCESS.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


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
        print(f"DRY RUN: would submit '{Right.RIGHT_TO_DELETE.name}' (bundled opt-out + deletion form) for {SuperScraper.EMAIL}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_delete")
        return

    print("\nOpt-Out/Delete form filled. Solve the Cloudflare Turnstile challenge, click Affirm & Submit,")
    print("then press Enter once the confirmation appears...")
    input()

    print(f"Submitted '{Right.RIGHT_TO_DELETE.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


HANDLERS = {"access": submit_access, "opt_out_delete": submit_opt_out_delete}


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            await HANDLERS[RIGHT_MAP[right]](tab, super_scraper)


asyncio.run(main())

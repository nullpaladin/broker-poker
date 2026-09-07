# intelius.com — app.intelius.com/privacy-center/. Splits rights into
# "User Data Tools" (the actual CCPA-style rights: Know/Opt Out/Correct/
# Delete, all as accordion sections on one page) and "Public Data Tools" (a
# separate background-report "Suppression Tool" for their people-search
# product — a distinct, more involved flow not covered here). "Right to
# Correct" has no form for non-customers at all — it just redirects
# non-customers to Right to Delete instead, so it's skipped entirely.
#
# Right to Know: single `retrievalEmail` field + "Request a Copy of My
# Data" — this emails a download link, a real side-effect trigger, so the
# scraper fills the email and stops there regardless of DRY_RUN.
#
# Right to Opt Out: "Open Cookie Preferences" opens a modal with a single
# "Do Not Sell or Share My Personal Information" checkbox + "Save My
# Preferences" — a plain preference toggle (no email verification
# involved), so it follows the normal DRY_RUN-gated submit pattern used
# elsewhere in this repo. The same accordion section also has a second,
# separate form (name/DOB/city/state/email) to suppress your name from
# appearing as a relative/associate in OTHER people's reports — that's an
# auxiliary feature (not a core Access/Opt-Out/Delete right) and is
# skipped, same as Transfer/Update Inaccuracies cards are skipped on
# DataGrail sites elsewhere in this repo.
#
# Right to Delete: single `deletionEmail` field + "Delete My User Data" —
# this also emails a confirmation link, a real side-effect trigger, so the
# scraper fills the email and stops there regardless of DRY_RUN. Gated on
# REMOVE_INFORMATION.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://app.intelius.com/privacy-center/"


async def _open_accordion(tab, label):
    link = await tab.find(text=label, raise_exc=False)
    if link:
        await link.click()
        await asyncio.sleep(1)
    return link


async def do_access(tab, super_scraper):
    await _open_accordion(tab, "Right to Know")
    email_field = await tab.find(xpath="//input[@name='retrievalEmail']", raise_exc=False)
    if not email_field:
        print(f"{super_scraper.OOPS} retrievalEmail field not found")
        return
    await email_field.type_text(SuperScraper.EMAIL)
    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "resources/screenshots/intelius_dry_run_access.png")
    print(
        "\nAccess request email entered but NOT sent — click 'Request a Copy of My Data' "
        "yourself. This emails a real download link regardless of DRY_RUN, so it is never "
        "done automatically."
    )


async def do_opt_out(tab, super_scraper):
    await _open_accordion(tab, "Right to Opt Out")
    cookie_btn = await tab.find(text="Open Cookie Preferences", raise_exc=False)
    if not cookie_btn:
        print(f"{super_scraper.OOPS} 'Open Cookie Preferences' button not found")
        return
    await cookie_btn.click()
    await asyncio.sleep(2)

    checkbox = await tab.find(id="ckyCCPAOptOut", raise_exc=False)
    if checkbox:
        await checkbox.click()
    else:
        print(f"{super_scraper.OOPS} CCPA opt-out checkbox not found")
        return

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would save opt-out cookie preference for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/intelius_dry_run_opt_out.png")
        # dismiss the modal (leaving it open would block the next
        # accordion section's screenshot) — the checkbox state was already
        # captured above, nothing is lost by cancelling instead of saving
        cancel_btn = await tab.find(text="Cancel", raise_exc=False)
        if cancel_btn:
            await cancel_btn.click()
            await asyncio.sleep(1)
        return

    save_btn = await tab.find(text="Save My Preferences", raise_exc=False)
    if save_btn:
        await save_btn.click()
        await asyncio.sleep(2)
        print(f"Saved opt-out cookie preference for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} 'Save My Preferences' button not found")


async def do_delete(tab, super_scraper):
    await _open_accordion(tab, "Right to Delete")
    email_field = await tab.find(xpath="//input[@name='deletionEmail']", raise_exc=False)
    if not email_field:
        print(f"{super_scraper.OOPS} deletionEmail field not found")
        return
    await email_field.type_text(SuperScraper.EMAIL)
    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "resources/screenshots/intelius_dry_run_delete.png")
    print(
        "\nDeletion request email entered but NOT sent — click 'Delete My User Data' "
        "yourself and confirm via the email you receive. This sends a real confirmation "
        "email regardless of DRY_RUN, so it is never done automatically."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        view_btn = await tab.find(text="View User Data Tools", raise_exc=False)
        if view_btn:
            await view_btn.click()
            await asyncio.sleep(2)

        await do_access(tab, super_scraper)
        await do_opt_out(tab, super_scraper)
        if SuperScraper.wants("delete"):
            await do_delete(tab, super_scraper)


asyncio.run(main())

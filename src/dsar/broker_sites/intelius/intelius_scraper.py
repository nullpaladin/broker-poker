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
# scraper fills the email and stops there regardless of DRY_RUN.
#
# Which of Know / Opt Out / Delete run is decided only by SuperScraper.rights_to_exercise.
#
# Page elements:
#   "View User Data Tools"                       opens the User Data Tools section
#   "Right to Know" / "Right to Opt Out" / "Right to Delete"   accordion sections
#   input[name=retrievalEmail]                   Know: email for the data copy
#   "Request a Copy of My Data"                  Know submit (never clicked)
#   "Open Cookie Preferences"                    Opt Out: opens the preferences modal
#   #ckyCCPAOptOut                               "Do Not Sell or Share My Personal Information" checkbox
#   "Save My Preferences" / "Cancel"             modal buttons
#   input[name=deletionEmail]                    Delete: email for the confirmation link
#   "Delete My User Data"                        Delete submit (never clicked)
import asyncio

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://app.intelius.com/privacy-center/"

# Right -> which accordion section handles it.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "access",
    Right.RIGHT_TO_OPT_OUT: "opt_out",
    Right.RIGHT_TO_DELETE: "delete",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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
    await SuperScraper.screenshot(tab, "dry_run_access")
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
        print(f"DRY RUN: would save opt-out cookie preference ({Right.RIGHT_TO_OPT_OUT.name})")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_opt_out")
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
        print(f"Saved opt-out cookie preference ({Right.RIGHT_TO_OPT_OUT.name}) — confirm in the browser.")
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
    await SuperScraper.screenshot(tab, "dry_run_delete")
    print(
        "\nDeletion request email entered but NOT sent — click 'Delete My User Data' "
        "yourself and confirm via the email you receive. This sends a real confirmation "
        "email regardless of DRY_RUN, so it is never done automatically."
    )


HANDLERS = {"access": do_access, "opt_out": do_opt_out, "delete": do_delete}


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        view_btn = await tab.find(text="View User Data Tools", raise_exc=False)
        if view_btn:
            await view_btn.click()
            await asyncio.sleep(2)

        for right in rights:
            await HANDLERS[RIGHT_MAP[right]](tab, super_scraper)


asyncio.run(main())

# information.com — a single /privacy-rights/ page with three cards, each
# revealing its own distinct-named inline form only after its own button is
# clicked (the other two cards' fields are absent from the DOM until their
# button is clicked, so there's no risk of hitting the wrong form by name).
#
# Right To Know ("REQUEST A COPY"): requestDataFirstName/requestDataLastName/
# requestDataEmail -> RIGHT_TO_ACCESS.
# Right To Delete ("DELETE MY USER DATA"): deleteDataFirstName/
# deleteDataLastName/deleteDataEmail -> RIGHT_TO_DELETE (it cancels subscriptions
# and deletes the account).
# Opt-Out ("EXERT RIGHT TO OPT-OUT", branded "Suppression Center"): only asks
# for an email + an "acknowledge" checkbox, then a "Continue" button that
# sends a verification email with a link to proceed — that send is a real
# side effect, so this scraper fills the email/checkbox and stops there
# regardless of DRY_RUN, same handoff pattern as informa.com. -> RIGHT_TO_OPT_OUT.
# Which of the three run is decided only by SuperScraper.rights_to_exercise.
#
# Page elements:
#   "REQUEST A COPY" / "DELETE MY USER DATA" / "EXERT RIGHT TO OPT-OUT"   card buttons
#   input[name=requestDataFirstName|requestDataLastName|requestDataEmail]   Know form
#   input[name=deleteDataFirstName|deleteDataLastName|deleteDataEmail]      Delete form
#   "SUBMIT REQUEST" button         submits the Know / Delete form
#   #requestorEmail                 Opt-out (Suppression Center) email
#   #acknowledge                    Opt-out "acknowledge" checkbox
#   "Continue" button               sends the verification email (never clicked)
import asyncio

from src.dsar import js_utils
from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome

URL = "https://information.com/privacy-rights/"

# Right -> which card/form on the page handles it.
RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "know",
    Right.RIGHT_TO_DELETE: "delete",
    Right.RIGHT_TO_OPT_OUT: "opt_out",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
# (The three card buttons are the rights; no selector is recorded for reading them back.)

KNOW_FIELD_XPATHS = {
    "First name": "//input[@name='requestDataFirstName']",
    "Last name": "//input[@name='requestDataLastName']",
    "Email": "//input[@name='requestDataEmail']",
}
DELETE_FIELD_XPATHS = {
    "First name": "//input[@name='deleteDataFirstName']",
    "Last name": "//input[@name='deleteDataLastName']",
    "Email": "//input[@name='deleteDataEmail']",
}


async def submit_know(tab, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(4)

    btn = await tab.find(text="REQUEST A COPY", raise_exc=False)
    if not btn:
        print(f"{super_scraper.OOPS} 'REQUEST A COPY' button not found")
        return
    await btn.click()
    await asyncio.sleep(1)

    first = await tab.find(xpath="//input[@name='requestDataFirstName']", raise_exc=False)
    last = await tab.find(xpath="//input[@name='requestDataLastName']", raise_exc=False)
    email = await tab.find(xpath="//input[@name='requestDataEmail']", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, KNOW_FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{Right.RIGHT_TO_ACCESS.name}' for {SuperScraper.EMAIL}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_access")
        return

    submit = await tab.find(text="SUBMIT REQUEST", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(2)
        print(f"Submitted '{Right.RIGHT_TO_ACCESS.name}' for {SuperScraper.EMAIL} — confirm in the browser.")
    else:
        print(f"{super_scraper.OOPS} 'SUBMIT REQUEST' button not found for Right To Know")


async def submit_delete(tab, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(4)

    btn = await tab.find(text="DELETE MY USER DATA", raise_exc=False)
    if not btn:
        print(f"{super_scraper.OOPS} 'DELETE MY USER DATA' button not found")
        return
    await btn.click()
    await asyncio.sleep(1)

    first = await tab.find(xpath="//input[@name='deleteDataFirstName']", raise_exc=False)
    last = await tab.find(xpath="//input[@name='deleteDataLastName']", raise_exc=False)
    email = await tab.find(xpath="//input[@name='deleteDataEmail']", raise_exc=False)
    if first:
        await first.type_text(SuperScraper.FIRST_NAME)
    if last:
        await last.type_text(SuperScraper.LAST_NAME)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, DELETE_FIELD_XPATHS)

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{Right.RIGHT_TO_DELETE.name}' for {SuperScraper.EMAIL}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_delete")
        return

    submit = await tab.find(text="SUBMIT REQUEST", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(2)
        print(f"Submitted '{Right.RIGHT_TO_DELETE.name}' for {SuperScraper.EMAIL} — confirm in the browser.")
    else:
        print(f"{super_scraper.OOPS} 'SUBMIT REQUEST' button not found for Right To Delete")


async def submit_opt_out(tab, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(4)

    btn = await tab.find(text="EXERT RIGHT TO OPT-OUT", raise_exc=False)
    if not btn:
        print(f"{super_scraper.OOPS} 'EXERT RIGHT TO OPT-OUT' button not found")
        return
    await btn.click()
    await asyncio.sleep(1)

    email = await tab.find(id="requestorEmail", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)

    acknowledge = await tab.find(id="acknowledge", raise_exc=False)
    if acknowledge:
        await js_utils.js_check(acknowledge)

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, {"Email": "//*[@id='requestorEmail']"})

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "dry_run_opt_out")
    print(
        "\nOpt-Out (Suppression Center) email entered but NOT sent — click 'Continue' "
        "yourself, check your inbox for the verification link, click it, and complete "
        "whatever step follows manually. This sends a real verification email regardless "
        "of DRY_RUN, so it is never done automatically."
    )


HANDLERS = {"know": submit_know, "delete": submit_delete, "opt_out": submit_opt_out}


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

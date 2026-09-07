# information.com — a single /privacy-rights/ page with three cards, each
# revealing its own distinct-named inline form only after its own button is
# clicked (the other two cards' fields are absent from the DOM until their
# button is clicked, so there's no risk of hitting the wrong form by name).
#
# Right To Know ("REQUEST A COPY"): requestDataFirstName/requestDataLastName/
# requestDataEmail, always submitted.
# Right To Delete ("DELETE MY USER DATA"): deleteDataFirstName/
# deleteDataLastName/deleteDataEmail, gated on REMOVE_INFORMATION since it
# cancels subscriptions and deletes the account.
# Opt-Out ("EXERT RIGHT TO OPT-OUT", branded "Suppression Center"): only asks
# for an email + an "acknowledge" checkbox, then a "Continue" button that
# sends a verification email with a link to proceed — that send is a real
# side effect, so this scraper fills the email/checkbox and stops there
# regardless of DRY_RUN, same handoff pattern as informa.com.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://information.com/privacy-rights/"


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

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit Right To Know request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/information_dry_run_know.png")
        return

    submit = await tab.find(text="SUBMIT REQUEST", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(2)
        print(f"Submitted Right To Know request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
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

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit Right To Delete request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/information_dry_run_delete.png")
        return

    submit = await tab.find(text="SUBMIT REQUEST", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(2)
        print(f"Submitted Right To Delete request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
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

    await tab.execute_script(
        "var cb=document.getElementById('acknowledge'); if(cb){ cb.checked=true; "
        "cb.dispatchEvent(new Event('change', {bubbles:true})); "
        "cb.dispatchEvent(new Event('click', {bubbles:true})); }"
    )

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, "resources/screenshots/information_dry_run_optout.png")
    print(
        "\nOpt-Out (Suppression Center) email entered but NOT sent — click 'Continue' "
        "yourself, check your inbox for the verification link, click it, and complete "
        "whatever step follows manually. This sends a real verification email regardless "
        "of DRY_RUN, so it is never done automatically."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await submit_know(tab, super_scraper)
        if SuperScraper.REMOVE_INFORMATION:
            await submit_delete(tab, super_scraper)
        else:
            print("Skipping Right To Delete — REMOVE_INFORMATION is False.")
        await submit_opt_out(tab, super_scraper)


asyncio.run(main())

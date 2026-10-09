# ip2location.com — /do-not-sell #form-do-not-sell, server-rendered, POSTs in
# place. One submission per requestType <select>:
#   "I want to know what personal data you have about me"                -> Access
#   "I want you to not sell my personal data (California residents)"     -> Opt-Out
#   "I want you to delete the personal data you have about me"           -> Delete
#       (gated on REMOVE_INFORMATION)
#   "change" / "stop using" skipped as non-core.
# Fields: name, emailAddress, ipAddresses (textarea — the requester's public IP,
#   fetched at runtime), scope <select> -> "all of my data", behalf <select> ->
#   "No", file (optional, skipped). No CAPTCHA seen (only a Trustpilot widget).
import asyncio
import urllib.request

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.ip2location.com/do-not-sell"

RIGHT_MAP = {
    "access": [("I want to know what personal data you have about me", "access")],
    "opt_out_sale_share": [("I want you to not sell my personal data (California residents)", "opt_out")],
    "delete": [("I want you to delete the personal data you have about me", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


def _public_ip():
    for svc in ("https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com"):
        try:
            return urllib.request.urlopen(svc, timeout=8).read().decode().strip()
        except Exception:
            continue
    return ""


async def submit_request(tab, right_label, tag, super_scraper, ip):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    form_xp = "//form[@id='form-do-not-sell']"

    name = await tab.find(xpath=f"{form_xp}//input[@name='name']", raise_exc=False)
    if name:
        await name.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}".strip())
    email = await tab.find(xpath=f"{form_xp}//input[@name='emailAddress']", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)
    ips = await tab.find(xpath=f"{form_xp}//textarea[@name='ipAddresses']", raise_exc=False)
    if ips and ip:
        await ips.type_text(ip)
    elif not ip:
        print(f"{super_scraper.OOPS} could not determine public IP for ipAddresses field")

    rt = await tab.find(xpath=f"{form_xp}//select[@name='requestType']", raise_exc=False)
    if rt:
        await SuperScraper.select_native_option(rt, text=right_label)
    else:
        print(f"{super_scraper.OOPS} requestType select not found")

    scope = await tab.find(xpath=f"{form_xp}//select[@name='scope']", raise_exc=False)
    if scope:
        await SuperScraper.select_native_option(scope, text="This request relates to all of my data")
    behalf = await tab.find(xpath=f"{form_xp}//select[@name='behalf']", raise_exc=False)
    if behalf:
        await SuperScraper.select_native_option(behalf, text="No")

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/ip2location_dry_run_{tag}.png", beyond_viewport=True)
    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right_label}' for {SuperScraper.EMAIL} (IP {ip or '?'})")
        return

    submit = await tab.find(xpath=f"{form_xp}//button[@type='submit'] | {form_xp}//input[@type='submit']", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(3)
        print(f"Submitted '{right_label}' for {SuperScraper.EMAIL}")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    ip = _public_ip()
    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    rights = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right_label, tag in rights:
            await submit_request(tab, right_label, tag, super_scraper, ip)


asyncio.run(main())

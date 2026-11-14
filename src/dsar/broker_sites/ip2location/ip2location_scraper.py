# ip2location.com — /do-not-sell #form-do-not-sell, server-rendered, POSTs in
# place. One submission per requestType <select>:
#   "I want to know what personal data you have about me"                -> Access
#   "I want you to not sell my personal data (California residents)"     -> Opt-Out
#   "I want you to delete the personal data you have about me"           -> Delete
#   "change" / "stop using" skipped as non-core.
# Which run is decided only by SuperScraper.rights_to_exercise.
# Fields: name, emailAddress, ipAddresses (textarea — the requester's public IP,
#   fetched at runtime), scope <select> -> "all of my data", behalf <select> ->
#   "No", file (optional, skipped). No CAPTCHA seen (only a Trustpilot widget).
#
# Page elements (all inside form#form-do-not-sell):
#   input[name=name]                  Name
#   input[name=emailAddress]          Email
#   textarea[name=ipAddresses]        IP addresses (requester's public IP)
#   select[name=requestType]          Request type (options in RIGHT_MAP)
#   select[name=scope]                Scope -> "This request relates to all of my data"
#   select[name=behalf]               On behalf of someone else -> "No"
#   button/input[type=submit]         Submit
import asyncio
import urllib.request

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper
from src.dsar import js_utils

URL = "https://www.ip2location.com/do-not-sell"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: [("I want to know what personal data you have about me", "access")],
    Right.RIGHT_TO_OPT_OUT: [("I want you to not sell my personal data (California residents)", "opt_out")],
    Right.RIGHT_TO_DELETE: [("I want you to delete the personal data you have about me", "delete")],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = "form#form-do-not-sell select[name='requestType'] option"  # change / stop-using options are unrecorded


def _public_ip():
    for svc in ("https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com"):
        try:
            return urllib.request.urlopen(svc, timeout=8).read().decode().strip()
        except Exception:
            continue
    return ""


async def submit_request(tab, right, right_label, tag, super_scraper, ip):
    await tab.go_to(URL)
    await asyncio.sleep(6)

    form_xp = "//form[@id='form-do-not-sell']"

    if SuperScraper.HEALTH_CHECK:
        offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
        SuperScraper.audit_rights(offered, PAGE_RIGHTS)

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
        await js_utils.select_native_option(rt, text=right_label)
    else:
        print(f"{super_scraper.OOPS} requestType select not found")

    scope = await tab.find(xpath=f"{form_xp}//select[@name='scope']", raise_exc=False)
    if scope:
        await js_utils.select_native_option(scope, text="This request relates to all of my data")
    behalf = await tab.find(xpath=f"{form_xp}//select[@name='behalf']", raise_exc=False)
    if behalf:
        await js_utils.select_native_option(behalf, text="No")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(tab, {
            "Name": f"{form_xp}//input[@name='name']",
            "Email": f"{form_xp}//input[@name='emailAddress']",
            "IP addresses": f"{form_xp}//textarea[@name='ipAddresses']",
            "Request type": f"{form_xp}//select[@name='requestType']",
            "Scope": f"{form_xp}//select[@name='scope']",
            "On behalf of": f"{form_xp}//select[@name='behalf']",
        })

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{right.name}' for {SuperScraper.EMAIL} (IP {ip or '?'})")
        return

    submit = await tab.find(xpath=f"{form_xp}//button[@type='submit'] | {form_xp}//input[@type='submit']", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(3)
        print(f"Submitted '{right.name}' for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    options = SuperScraper.build_chromium_options()

    ip = _public_ip()
    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right in rights:
            for right_label, tag in RIGHT_MAP[right]:
                await submit_request(tab, right, right_label, tag, super_scraper, ip)


asyncio.run(main())

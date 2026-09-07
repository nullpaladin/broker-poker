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

RIGHTS = [
    ("I want to know what personal data you have about me", "access"),
    ("I want you to not sell my personal data (California residents)", "opt_out"),
]
DELETE_RIGHT = ("I want you to delete the personal data you have about me", "delete")


def _public_ip():
    for svc in ("https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com"):
        try:
            return urllib.request.urlopen(svc, timeout=8).read().decode().strip()
        except Exception:
            continue
    return ""


async def _select_by_text(select_element, text):
    await select_element.execute_script(
        "for (var i=0;i<this.options.length;i++){"
        f"  if(this.options[i].text.trim()==={text!r}){{ this.selectedIndex=i; }}"
        "}"
        "this.dispatchEvent(new Event('change', {bubbles:true}));"
    )


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
        await _select_by_text(rt, right_label)
    else:
        print(f"{super_scraper.OOPS} requestType select not found")

    scope = await tab.find(xpath=f"{form_xp}//select[@name='scope']", raise_exc=False)
    if scope:
        await _select_by_text(scope, "This request relates to all of my data")
    behalf = await tab.find(xpath=f"{form_xp}//select[@name='behalf']", raise_exc=False)
    if behalf:
        await _select_by_text(behalf, "No")

    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/ip2location_dry_run_{tag}.png", beyond_viewport=True)
    print(f"Screenshot saved to resources/screenshots/ip2location_dry_run_{tag}.png")

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
    options.add_argument("--window-size=1280,2400")

    ip = _public_ip()
    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for right_label, tag in rights:
            await submit_request(tab, right_label, tag, super_scraper, ip)


asyncio.run(main())

# socialcatfish.com — Social Catfish privacy request. The same /opt-out/ page
# serves a different form per `?id=` query value: request_access (Right to
# Access), request_optout (Right to Opt-Out), request_delete (Right to Delete).
# One submission per right — Access + Opt-Out unconditional, Delete gated on
# REMOVE_INFORMATION.
# Fields: firstname, lastname, email, ccpa_state (native <select>, full state
# names). The "I am submitting as an authorized agent of a third-party
# organization" checkbox is left UNCHECKED; the STEP 03 "check all that apply"
# scope checkboxes are all ticked. The required "I verify I am a resident of
# <state> and am the person named above" attestation is a React-controlled
# hidden checkbox that does not reliably toggle via script under automation —
# TICK IT MANUALLY before submitting. The repeatable
# "ccpa_url[]" profile-URL field is a manual record-location step (paste links
# to your own Social Catfish result pages, found via the on-page name search)
# and is left blank here.
# A reCAPTCHA / Cloudflare Turnstile gates submission and the whole site sits
# behind PerimeterX — the form is filled and left for a manual solve; if the
# page is fully replaced by a "press & hold" / bot interstitial, retry from a
# fresh, low-frequency session.  **CAPTCHA solution required**
import asyncio
import time

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

BASE = "https://socialcatfish.com/opt-out/?id="
REQUESTS = [
    ("request_access", "access"),
    ("request_optout", "optout"),
]
DELETE_REQUEST = ("request_delete", "delete")


async def submit_request(tab, mode, label, super_scraper):
    await tab.go_to(BASE + mode)
    await asyncio.sleep(6)

    # the page also carries hidden newsletter/login inputs with the same
    # name="email" etc. — target the visible CCPA form by its stable ids
    for xpath, value in [
        ("//input[@id='first-name']", SuperScraper.FIRST_NAME),
        ("//input[@id='last-name']", SuperScraper.LAST_NAME),
        ("//input[@id='email']", SuperScraper.EMAIL),
    ]:
        await super_scraper.input_text_field(tab=tab, xpath=xpath, text=value, sleep=0.2)

    state_select = await tab.find(id="ccpa_state", raise_exc=False)
    if state_select:
        await state_select.execute_script(
            f"const o=[...this.options].find(x=>x.text.trim()=={SuperScraper.STATE!r});"
            "if(o){const s=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;"
            "s.call(this,o.value);this.dispatchEvent(new Event('change',{bubbles:true}));}"
        )

    # STEP 03 "check all that apply" scope checkboxes (skip the agent checkbox
    # and the residency attestation, handled below)
    for box in await tab.find(xpath="//div[contains(@class,'step') or true()]//input[@type='checkbox']", find_all=True, raise_exc=False) or []:
        if not await box.is_visible():
            continue
        name = (box.get_attribute("name") or "").lower()
        if "third_party_opt" in name:
            continue  # "I am an authorized agent" — leave unchecked
        val = (box.get_attribute("value") or "").lower()
        if name == "consent" or box.id == "consent-checkbox" or val in ("on", "1") or "information" in val or "categor" in val:
            await box.execute_script("if (!this.checked) this.click();")
            await asyncio.sleep(0.1)

    # required residency attestation, in case it wasn't caught above
    consent = await tab.find(id="consent-checkbox", raise_exc=False)
    if consent:
        await consent.execute_script("if (!this.checked) this.click();")

    time.sleep(0.5)
    await SuperScraper.screenshot(tab, f"resources/screenshots/socialcatfish_dry_run_{label}.png")
    print(
        f"'{mode}' filled but NOT submitted — paste links to your own Social Catfish "
        f"result pages in the profile-URL field, solve the CAPTCHA, then submit."
    )

    if not SuperScraper.DRY_RUN:
        print("Complete the manual steps, click Submit Now, then press Enter once confirmed...")
        input()


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    requests = list(REQUESTS)
    if SuperScraper.REMOVE_INFORMATION:
        requests.append(DELETE_REQUEST)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for mode, label in requests:
            await submit_request(tab, mode, label, super_scraper)


asyncio.run(main())

# leadloft.com — user-agreements/personal-data. The page itself states
# "We are not CCPA regulated... We do not honor automated requests," so a
# submission here may simply be ignored — documented for completeness
# regardless, consistent with this repo's policy of filling and
# documenting rather than skipping based on a site's own claims. Only
# Delete/Rectify/Restrict Processing are offered — no Access or explicit
# Opt-Out-of-Sale option at all. "Restrict Processing" is used as the
# closest available analog to Opt-Out; "Rectify" (=Correct) is skipped as
# auxiliary. The email field ids are INVERTED from what they suggest:
# `id="Email"` is CSS-hidden (`hide-this-scale`, height:0) and is the
# actual spam trap, while `id="HoneyPot"` is the real, visibly-rendered
# field carrying the "Email Address *" label — filling "Email" instead
# would both miss the real field and trip the trap. Additional Information
# textarea is required, filled with a
# short generic explanation. The form's own submit button uses an
# auto-generated Webflow node id (not a readable one) and there's a
# second, unrelated form on the page with a plain `id="submit"` (a
# newsletter-signup CTA) — targeted via the stable `wf-form-Personal-Data`
# form id instead of guessing either id directly. A `cf-turnstile-response`
# hidden field exists but no visible Turnstile widget renders — appears to
# run in invisible/managed mode with nothing to solve. Exercises Restrict
# Processing unconditionally; Delete gated on REMOVE_INFORMATION.
import asyncio

from src.dsar.super_scraper import SuperScraper

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

URL = "https://www.leadloft.com/user-agreements/personal-data"

REQUEST_TYPES = ["Restrict Processing"]
DELETE_REQUEST_TYPE = "Delete"


async def submit_request(tab, request_type, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    first_field = await tab.find(id="First-Name-2", raise_exc=False)
    if first_field:
        await first_field.type_text(SuperScraper.FIRST_NAME)

    last_field = await tab.find(id="Last-Name-2", raise_exc=False)
    if last_field:
        await last_field.type_text(SuperScraper.LAST_NAME)

    # The field ids are inverted from what they suggest: id="Email" is
    # CSS-hidden (class "hide-this-scale", height:0) and is the actual
    # spam trap, while id="HoneyPot" is the real, visibly-rendered email
    # field (h:48, the one with the "Email Address *" label above it).
    # Filling "Email" instead would both miss the real field and trip the
    # trap.
    email_field = await tab.find(id="HoneyPot", raise_exc=False)
    if email_field:
        await email_field.type_text(SuperScraper.EMAIL)

    request_select = await tab.find(id="Request-2", raise_exc=False)
    if request_select:
        await request_select.execute_script(
            "for (var i=0;i<this.options.length;i++){"
            f"  if(this.options[i].text==={request_type!r}){{ this.selectedIndex=i; }}"
            "}"
            "this.dispatchEvent(new Event('change', {bubbles:true}));"
        )

    details_field = await tab.find(id="field-2", raise_exc=False)
    if details_field:
        await details_field.type_text(
            f"Please {request_type.lower()} my personal data pursuant to applicable privacy law."
        )

    label = request_type.lower().replace(" ", "_")

    if SuperScraper.DRY_RUN:
        print(f"DRY RUN: would submit '{request_type}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        await asyncio.sleep(1)
        await tab.take_screenshot(path=f"resources/screenshots/leadloft_dry_run_{label}.png")
        print(f"Screenshot saved to resources/screenshots/leadloft_dry_run_{label}.png")
        return

    # NOT id="submit" — that belongs to an unrelated newsletter-signup form
    # elsewhere on the page ("Your work email"). This form's own submit
    # button uses an auto-generated Webflow node id instead of a readable
    # one, so it's targeted via the stable form id + its submit input.
    submit_btn = await tab.find(
        xpath="//form[@id='wf-form-Personal-Data']//input[@type='submit']", raise_exc=False
    )
    if submit_btn:
        await submit_btn.click()
        await asyncio.sleep(2)
        print(f"Submitted '{request_type}' request for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
    else:
        print(f"{super_scraper.OOPS} Submit button not found for '{request_type}'")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    request_types = list(REQUEST_TYPES)
    if SuperScraper.REMOVE_INFORMATION:
        request_types.append(DELETE_REQUEST_TYPE)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for request_type in request_types:
            await submit_request(tab, request_type, super_scraper)


asyncio.run(main())

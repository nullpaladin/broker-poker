# swoop.com — the /your-privacy-choices/ page embeds an Osano DataSubject
# portal (my.datasubject.com) in an iframe — navigate straight to it.
# (The page's Gravity Forms are only a cookie/newsletter widget.)
# After a card is clicked the fields are: requestor-type (select — options
# "Healthcare Professional" / "Consumer" / "Agent for Data Subject", set to
# "Consumer"), given-name, family-name, email, and a representative-type
# "on behalf of someone else" checkbox (left UNCHECKED for a self-submission).
# Cards found by their h4[data-testid="card-title"] text. One card/right per
# pass: "Access or Request to Know" (Access), "Opt-Out Request", "Transfer my
# personal information" (portability), "Third parties your data was sold or
# shared with", "Automated Decision-Making" unconditionally; "Delete my
# personal information" gated on REMOVE_INFORMATION. "Correct my personal
# information" and "Employee Request" skipped.
# Cloudflare Turnstile gates the submit — form filled and left for a manual
# solve.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://my.datasubject.com/16A0AaT1hE8CL2xPu/19933"

RIGHTS = [
    ("Access or Request to Know", "access"),
    ("Opt-Out Request", "opt_out"),
    ("Transfer my personal information", "portability"),
    ("Third parties your data was sold or shared with", "third_parties"),
    ("Automated Decision-Making", "adm"),
]
DELETE_RIGHT = ("Delete my personal information", "delete")

FIELDS = {
    "given-name": "FIRST_NAME",
    "family-name": "LAST_NAME",
    "email": "EMAIL",
    "phone-number": "PHONE_NUMBER",
}


async def submit_request(tab, card_text, label, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(5)

    card = await tab.find(
        xpath=f"//h4[@data-testid='card-title' and normalize-space()={card_text!r}]", raise_exc=False
    )
    if not card:
        print(f"{super_scraper.OOPS} Card '{card_text}' not found")
        return
    await card.click()
    await asyncio.sleep(2)

    # requestor-type options: "" / "Healthcare Professional" / "Consumer" /
    # "Agent for Data Subject" — "Consumer" is the right answer for a data
    # subject exercising their own rights.
    rt = await tab.find(name="requestor-type", timeout=4, raise_exc=False)
    if rt:
        await rt.execute_script(
            "const o=[...this.options].find(x=>/^consumer$/i.test(x.text.trim()));"
            "if(o){const s=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;"
            "s.call(this,o.value);this.dispatchEvent(new Event('change',{bubbles:true}));}"
        )

    for name, attr in FIELDS.items():
        value = getattr(SuperScraper, attr, None)
        if not value:
            continue
        field = await tab.find(name=name, timeout=4, raise_exc=False)
        if field:
            await field.type_text(value)
            await asyncio.sleep(0.2)

    # name="representative-type" is the "on behalf of someone else" checkbox —
    # left UNCHECKED for a self-submission.

    await asyncio.sleep(1)
    await tab.take_screenshot(path=f"resources/screenshots/swoop_dry_run_{label}.png")
    print(f"Screenshot saved to resources/screenshots/swoop_dry_run_{label}.png")
    print(
        f"'{card_text}' request filled but NOT submitted — a Cloudflare Turnstile "
        f"checkbox must be solved manually before submitting."
    )


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    rights = list(RIGHTS)
    if SuperScraper.REMOVE_INFORMATION:
        rights.append(DELETE_RIGHT)

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        for card_text, label in rights:
            await submit_request(tab, card_text, label, super_scraper)


asyncio.run(main())

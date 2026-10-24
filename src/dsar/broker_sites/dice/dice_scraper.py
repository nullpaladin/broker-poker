# dice.com — /about/ccpa#ccpa-form-anchor . Server-rendered form
# (id="form-dice-ccpa", posts to a DHI Group forwarder).
#
# The "Please indicate whether you wish to" radio (name="description") is
# single-select, so exercising more than one right needs one submission each.
# This page is heavy (reCAPTCHA Enterprise) and a second full reload inside one
# browser session reliably hangs pydoll's load-event wait, so the scraper does
# ONE pass per run: the first right of PASS_ORDER that SuperScraper.rights_to_exercise(RIGHT_MAP)
# allows. To submit another right, re-run with only that right requested.
#
# Page elements:
#   #radio-description-access / #radio-description-optout / #radio-description-delete
#                                   "Please indicate whether you wish to" radio (see RIGHT_MAP)
#   form#form-dice-ccpa #name       Name (full name)
#   form#form-dice-ccpa #email      Email
# reCAPTCHA Enterprise gates the submit — filled to that point.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.dice.com/about/ccpa#ccpa-form-anchor"

RIGHT_MAP = {
    Right.RIGHT_TO_ACCESS: "radio-description-access",
    Right.RIGHT_TO_OPT_OUT: "radio-description-optout",
    Right.RIGHT_TO_DELETE: "radio-description-delete",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list
RIGHTS_OPTIONS_CSS = "label:has(input[name='description'])"  # "Please indicate whether you wish to" radios

FIELD_XPATHS = {
    "Name": "//form[@id='form-dice-ccpa']//input[@id='name']",
    "Email": "//form[@id='form-dice-ccpa']//input[@id='email']",
}
PASS_ORDER = (Right.RIGHT_TO_DELETE, Right.RIGHT_TO_ACCESS, Right.RIGHT_TO_OPT_OUT)


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    right = next(r for r in PASS_ORDER if r in rights)
    radio_id = RIGHT_MAP[right]

    options = SuperScraper.build_chromium_options()

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        try:
            await tab.go_to(URL)
        except Exception as exc:
            print(f"(dice: go_to reported {exc!r} — continuing once DOM is ready)")
        await asyncio.sleep(8)

        if SuperScraper.HEALTH_CHECK:
            offered = await SuperScraper.read_option_labels(tab, RIGHTS_OPTIONS_CSS)
            SuperScraper.audit_rights(offered, PAGE_RIGHTS)

        radio = await tab.find(id=radio_id, raise_exc=False)
        if radio:
            await radio.click()
            await asyncio.sleep(0.3)
        else:
            print(f"{super_scraper.OOPS} radio '{radio_id}' not found")

        name = await tab.find(xpath="//form[@id='form-dice-ccpa']//input[@id='name']", raise_exc=False)
        if name:
            await name.type_text(f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}".strip())
        email = await tab.find(xpath="//form[@id='form-dice-ccpa']//input[@id='email']", raise_exc=False)
        if email:
            await email.type_text(SuperScraper.EMAIL)

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, FIELD_XPATHS)

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, f"dry_run_{right.value}")
        print(
            f"'{right.name}' request filled but NOT submitted — solve the reCAPTCHA manually, then "
            "Submit. One right per run: re-run to submit another."
        )


asyncio.run(main())

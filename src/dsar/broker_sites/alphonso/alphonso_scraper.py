# alphonso.tv — two React "Customer Choice" forms, each just an email field
# (the request's current IP address is transmitted with it; no advertising IDs
# needed):
#   Opt-Out:  https://choice.alphonso.tv/donotsell            -> email + Submit
#   Other:    https://choice.alphonso.tv/otherconsumerrequests-> a free-text
#             "Write your Request Here" textarea + email + Submit
# RIGHT_TO_OPT_OUT uses the Opt-Out form. The "other requests" form carries
# RIGHT_TO_ACCESS and RIGHT_TO_DELETE together in one free-text request. Which run is
# decided only by SuperScraper.rights_to_exercise.
# Fields have no id/name — targeted by placeholder. No CAPTCHA.
#
# Page elements:
#   input[placeholder="Enter Your Email"]            Email (both forms)
#   textarea[placeholder="Write your Request Here"]  Request text (other-requests form only)
#   button "Submit"                                  Submit
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

OPT_OUT_URL = "https://choice.alphonso.tv/donotsell"
OTHER_URL = "https://choice.alphonso.tv/otherconsumerrequests"

RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: OPT_OUT_URL,
    Right.RIGHT_TO_ACCESS: OTHER_URL,
    Right.RIGHT_TO_DELETE: OTHER_URL,
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

PAGE_RIGHTS = {}  # TODO(health-check): run HEALTH_CHECK once live; it prints the full list

EMAIL_XPATH = "//input[@placeholder='Enter Your Email']"
MESSAGE_XPATH = "//textarea[@placeholder='Write your Request Here']"


async def _fill_and_shot(tab, super_scraper, url, tag, message=None):
    await tab.go_to(url)
    await asyncio.sleep(6)

    if message:
        area = await tab.find(xpath="//textarea[@placeholder='Write your Request Here']", raise_exc=False)
        if area:
            await area.type_text(message)
            await asyncio.sleep(0.3)
        else:
            print(f"{super_scraper.OOPS} [{tag}] request textarea not found")

    email = await tab.find(xpath="//input[@placeholder='Enter Your Email']", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)
    else:
        print(f"{super_scraper.OOPS} [{tag}] email field not found")

    if SuperScraper.HEALTH_CHECK:
        await SuperScraper.assert_fields_filled(
            tab, {"Email": EMAIL_XPATH, **({"Request text": MESSAGE_XPATH} if message else {})}
        )

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"dry_run_{tag}")
    if SuperScraper.DRY_RUN:
        print(f"DRY RUN [{tag}]: would submit for {SuperScraper.EMAIL}")
        return

    submit = await tab.find(xpath="//button[normalize-space()='Submit']", raise_exc=False)
    if submit:
        await submit.click()
        await asyncio.sleep(3)
        print(f"Submitted [{tag}] for {SuperScraper.EMAIL} — confirm in the browser.")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    # Access and Delete share the free-text "other requests" form -> one submission.
    other_rights = [r for r in rights if RIGHT_MAP[r] == OTHER_URL]

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        if Right.RIGHT_TO_OPT_OUT in rights:
            await _fill_and_shot(tab, super_scraper, OPT_OUT_URL, "opt_out")
        if other_rights:
            other_msg = SuperScraper.request_statement(other_rights, broker="Alphonso")
            await _fill_and_shot(tab, super_scraper, OTHER_URL, "other", message=other_msg)


asyncio.run(main())

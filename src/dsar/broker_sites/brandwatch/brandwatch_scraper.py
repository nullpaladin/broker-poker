# brandwatch.com — /legal/data-subject-access-request/ . A small React form
# (#dsr-form, injected a variable delay after page load) with two react-select
# comboboxes:
#   "Relationship to the company" (react-select-4) -> "Other" (none of the
#       options — Customer / Current Employee / Online Author / ... — is a clean
#       fit for a member of the public exercising privacy rights).
#   "Type of request" (react-select-5) — single-select, so one submission per
#       right: "Access" + "Do not Sell/Share Data" + "Portability"
#       unconditionally; "Erasure" gated on REMOVE_INFORMATION. Rectification /
#       Restriction / "No auto decisions" / "Object processing" / "Opt out from
#       commercial communications" / "Limit Use of Personal Data" skipped.
# The form can be slow/flaky to appear on a fresh load — the scraper polls for
# it for ~20s before each pass.
# Plus an email field (#1 / name="email") and a "Reason / Comment" textarea.
# A react-select is opened by clicking its control container
# (//input[@id='react-select-N-input']/ancestor::div[3]), then clicking the
# //*[@id^='react-select-N-option'] whose text matches.
# reCAPTCHA gates submit — filled to that point.  **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = "https://www.brandwatch.com/legal/data-subject-access-request/"

RIGHT_MAP = {
    "access": ["Access"],
    "opt_out_sale_share": ["Do not Sell/Share Data"],
    "portability": ["Portability"],
    "delete": ["Erasure"],
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)

COMMENT = (
    "I am a member of the public exercising my data subject rights. Please "
    "process this request with respect to any personal information Brandwatch "
    "holds about me (including data collected from public online sources)."
)


async def _react_select(tab, super_scraper, index, value):
    control = None
    for _ in range(3):
        control = await tab.find(
            xpath=f"//input[@id='react-select-{index}-input']/ancestor::div[3]", raise_exc=False
        )
        if control:
            break
        await asyncio.sleep(2)
    if not control:
        print(f"{super_scraper.OOPS} react-select-{index} control not found")
        return
    await control.click()
    await asyncio.sleep(1)
    opt = await tab.find(
        xpath=f"//*[starts-with(@id, 'react-select-{index}-option') and normalize-space()={value!r}]",
        raise_exc=False,
    )
    if opt:
        await opt.click()
        await asyncio.sleep(0.5)
    else:
        print(f"{super_scraper.OOPS} option {value!r} not found in react-select-{index}")


async def submit_request(tab, right, tag, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(9)

    accept = await tab.find(id="onetrust-accept-btn-handler", raise_exc=False)
    if accept:
        await accept.click()
        await asyncio.sleep(1)

    # #dsr-form is injected by JS a variable amount of time after load — wait
    # for it (up to ~20s) before touching the react-selects.
    for _ in range(10):
        if await tab.find(xpath="//input[@id='react-select-4-input']", raise_exc=False):
            break
        await asyncio.sleep(2)

    await _react_select(tab, super_scraper, 4, "Other")
    await _react_select(tab, super_scraper, 5, right)

    email = await tab.find(xpath="//form[@id='dsr-form']//input[@type='email' or @name='email']", raise_exc=False)
    if email:
        await email.type_text(SuperScraper.EMAIL)
    else:
        print(f"{super_scraper.OOPS} email field not found")

    comment = await tab.find(
        xpath="//form[@id='dsr-form']//textarea[not(@name='g-recaptcha-response')]", raise_exc=False
    )
    if comment:
        await comment.type_text(COMMENT)

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/brandwatch_dry_run_{tag}.png", beyond_viewport=True)
    print(f"'{right}' filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


async def main():
    options = ChromiumOptions()
    super_scraper = SuperScraper()
    options.binary_location = super_scraper.CHROMIUM_LOCATION
    options.add_argument("--no-sandbox")

    codes = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not codes:
        print("No requested privacy rights apply to this form — nothing to do.")
        return
    rights = [entry for code in codes for entry in RIGHT_MAP[code]]

    async with Chrome(options=options) as browser:
        tab = await browser.start()
        # Warm-up load: on a cold session #dsr-form frequently fails to render;
        # a throwaway first navigation makes subsequent loads reliable.
        try:
            await tab.go_to(URL)
        except Exception:
            pass
        await asyncio.sleep(6)

        for right in rights:
            tag = "".join(c if c.isalnum() else "_" for c in right.lower()).strip("_")[:20]
            await submit_request(tab, right, tag, super_scraper)


asyncio.run(main())

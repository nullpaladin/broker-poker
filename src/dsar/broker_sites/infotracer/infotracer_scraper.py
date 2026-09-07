# infotracer.com — TrustArc IRM "Privacy Rights Form"
# (submit-irm.trustarc.com), the same react-select scaffold as dnb.com /
# ariza.com: container ids 00000000-...-001001 ("on behalf of"), ...-001004
# ("Resident of" — state), ...-001005 ("Type of Request"). The options only
# populate after you TYPE into the control, so each is driven by typing a
# keyword then clicking the matching `.select__option`.
# Name is a single field (...-001002 "Enter Full Name"), email is ...-001003,
# "Request Details" is a textarea. One submission per right — the Type of
# Request options seen are "Right to Know or Access", "Right to Correct", and
# (presumably) "Right to Delete"; matched by keyword. Access + Correct
# unconditionally; Delete gated on REMOVE_INFORMATION. Do Not Sell / Opt-Out is
# a SEPARATE link in the site footer (not this form) and is not handled here.
# A final "By submitting this request, I am confirming ..." accuracy/consent
# checkbox is checked.
# Many other registry sites (affordablebackgroundchecks.com, courtcasefinder.com,
# uswarrants.org, searchquarry.com, ...) are infotracer.com wrappers.
# reCAPTCHA gates submit. This TrustArc host also throws a PerimeterX wall after
# rapid repeated loads — retry from a fresh session if the form won't render.
# **CAPTCHA solution required**
import asyncio

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

from src.dsar.super_scraper import SuperScraper

URL = (
    "https://submit-irm.trustarc.com/services/validation/"
    "8bec428f-079d-421f-8b6b-3ede6c5d5930/?brandId=7e2c71e1-7122-4856-bcaf-60248daf9d46"
)

IAM_CONTAINER = "00000000-0000-0000-0000-000000001001-select-container"
RESIDENT_CONTAINER = "00000000-0000-0000-0000-000000001004-select-container"
REQUEST_TYPE_CONTAINER = "00000000-0000-0000-0000-000000001005-select-container"

# (keyword typed into the request-type control, screenshot label)
RIGHTS = [("Access", "access"), ("Correct", "correct")]
DELETE_RIGHT = ("Delete", "delete")


async def _select_option(tab, super_scraper, container_id, text, label=""):
    ctrl = await tab.find(
        xpath=f"//div[@id='{container_id}']//div[contains(@class,'select__control')]",
        raise_exc=False,
    )
    if not ctrl:
        print(f"{super_scraper.OOPS} select control '{label or container_id}' not found")
        return
    await ctrl.click()
    await asyncio.sleep(0.4)
    await tab.keyboard.type_text(text)
    await asyncio.sleep(1.2)
    opt = await tab.find(
        xpath=f"//div[contains(@class,'select__option') and contains(., {text!r})]",
        raise_exc=False,
    )
    if opt:
        await opt.click()
        await asyncio.sleep(0.4)
    else:
        print(f"{super_scraper.OOPS} no '{label or container_id}' option matched {text!r}")


async def submit_request(tab, keyword, tag, super_scraper):
    await tab.go_to(URL)
    await asyncio.sleep(9)

    await _select_option(tab, super_scraper, IAM_CONTAINER, "Myself", "on behalf of")

    full_name = " ".join(p for p in (SuperScraper.FIRST_NAME, SuperScraper.LAST_NAME) if p)
    # The name/email ids are UUIDs — `tab.find(id=...)` returns an element that
    # fails is_visible(); target by aria-label / the //*[@id] xpath path instead.
    name_field = await tab.find(xpath="//input[@aria-label='Enter Full Name']", raise_exc=False)
    if not name_field:
        name_field = await tab.find(
            xpath="//input[@id='00000000-0000-0000-0000-000000001002']", raise_exc=False
        )
    if name_field:
        await name_field.scroll_into_view()
        await name_field.type_text(full_name)
    email_field = await tab.find(xpath="//input[@aria-label='Enter Email']", raise_exc=False)
    if not email_field:
        email_field = await tab.find(
            xpath="//input[@id='00000000-0000-0000-0000-000000001003']", raise_exc=False
        )
    if email_field:
        await email_field.scroll_into_view()
        await email_field.type_text(SuperScraper.EMAIL)

    await _select_option(tab, super_scraper, RESIDENT_CONTAINER, SuperScraper.STATE, "Resident of")
    await _select_option(tab, super_scraper, REQUEST_TYPE_CONTAINER, keyword, "Type of Request")

    # Final "By submitting this request, I am confirming ..." accuracy checkbox.
    checkboxes = await tab.find(xpath="//input[@type='checkbox']", find_all=True, raise_exc=False) or []
    for cb in checkboxes:
        try:
            await cb.execute_script(
                "if(!this.checked){this.checked=true;"
                "this.dispatchEvent(new Event('click',{bubbles:true}));"
                "this.dispatchEvent(new Event('change',{bubbles:true}));}"
            )
        except Exception:
            pass

    await asyncio.sleep(1)
    await SuperScraper.screenshot(tab, f"resources/screenshots/infotracer_dry_run_{tag}.png", beyond_viewport=True)
    print(f"'{keyword}' request filled but NOT submitted — solve the reCAPTCHA manually, then Submit.")


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
        for keyword, tag in rights:
            await submit_request(tab, keyword, tag, super_scraper)


asyncio.run(main())

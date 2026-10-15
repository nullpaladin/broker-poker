# decisionlinks.com — Webflow site with two separate GET forms on one page.
# Rights the form exposes: opt-out (form 1), access / data portability / correct /
# delete (form 2). Which of them run is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP). "Correct" (DSP) is not automatable and
# is no longer checked.
# Both forms reuse the same Webflow template: the checkbox
# `name`/`id` attributes (Agency/Brand/DSP/DMP) are identical across both
# forms but carry different visible labels per form, and one text field's
# `id` ("Contact-Company-Name" on form 1) is mislabeled — its visible label
# reads "State of Residence", not "Company Name". Checkboxes are scoped by
# ancestor::form to disambiguate the duplicated ids.
# Both forms have a reCAPTCHA v2 checkbox requiring manual solve in live mode.
#
# Form 1 "Opt-Out Request Form" (anchored on OPT_OUT_ANCHOR):
#   #Opt-Out-First-Name / #Opt-out-Last-Name / #Opt-Out-Email   First / Last name, Email
#   #Contact-Company-Name        "State of Residence" (id is mislabeled, see above)
#   checkbox name=DMP            "Opt-Out of All the Above" — one box covers Sale/Sharing,
#                                Targeted Advertising and Profiling (required group)
#   input[type=submit]           Submit (in this form)
# Form 2 "General Data Rights Request Form" (anchored on GENERAL_ANCHOR):
#   #General-Opt-Out-First-Name / #General-Opt-out-Last-Name / #General-Opt-Out-Email
#   #General-Opt-Out-State       "State of Residence"
#   checkbox name=Agency         Access
#   checkbox name=DSP            Correct (not automated)
#   checkbox name=DMP            Data Portability
#   checkbox name=Brand          Delete
#   input[type=submit]           Submit (in this form)
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.decisionlinks.com/legal-pages/your-privacy-choices"

OPT_OUT_ANCHOR = "Opt-Out-First-Name"  # first-name input of form 1
GENERAL_ANCHOR = "General-Opt-Out-First-Name"  # first-name input of form 2

# Right -> checkbox names to tick on the form that carries it. The opt-out form is
# separate from the general data-rights form.
OPT_OUT_BOXES = {Right.RIGHT_TO_OPT_OUT: ["DMP"]}  # "Opt-Out of All the Above"
GENERAL_BOXES = {
    Right.RIGHT_TO_ACCESS: ["Agency", "DMP"],  # Access + Data Portability
    Right.RIGHT_TO_DELETE: ["Brand"],  # Delete
}
RIGHT_MAP = {**OPT_OUT_BOXES, **GENERAL_BOXES}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


async def _check(tab, anchor_id, checkbox_name):
    # The real <input type="checkbox"> is visually hidden (opacity:0) — Webflow's
    # custom-checkbox pattern relies on clicking the wrapping <label> instead.
    box = await tab.find(
        xpath=f"//input[@id='{anchor_id}']/ancestor::form//input[@name='{checkbox_name}']/parent::label",
        raise_exc=False,
    )
    if box:
        await box.click()


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return

    rights = SuperScraper.rights_to_exercise(RIGHT_MAP)
    if not rights:
        print("No requested privacy rights apply to this form — nothing to do.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()

        if Right.RIGHT_TO_OPT_OUT in rights:
            await tab.go_to(URL)
            await asyncio.sleep(3)

            await super_scraper.input_text_field(tab=tab, xpath="//input[@id='Opt-Out-First-Name']", text=SuperScraper.FIRST_NAME, sleep=0.2)
            await super_scraper.input_text_field(tab=tab, xpath="//input[@id='Opt-out-Last-Name']", text=SuperScraper.LAST_NAME, sleep=0.2)
            await super_scraper.input_text_field(tab=tab, xpath="//input[@id='Opt-Out-Email']", text=SuperScraper.EMAIL, sleep=0.2)
            await super_scraper.input_text_field(tab=tab, xpath="//input[@id='Contact-Company-Name']", text=SuperScraper.STATE, sleep=0.2)
            for name in OPT_OUT_BOXES[Right.RIGHT_TO_OPT_OUT]:
                await _check(tab, OPT_OUT_ANCHOR, name)

            if SuperScraper.DRY_RUN:
                await asyncio.sleep(1)
                await SuperScraper.screenshot(tab, "dry_run_opt_out")
                print(f"DRY RUN: would submit '{Right.RIGHT_TO_OPT_OUT.name}' for {SuperScraper.EMAIL}")
            else:
                await super_scraper.click_item_by_xpath(tab=tab, xpath="//input[@id='Opt-Out-First-Name']/ancestor::form//input[@type='submit']", sleep=2)
                print(f"Submitted '{Right.RIGHT_TO_OPT_OUT.name}' for {SuperScraper.EMAIL} — confirm in the browser.")

        general_rights = [r for r in rights if r in GENERAL_BOXES]
        if not general_rights:
            return

        await tab.go_to(URL)
        await asyncio.sleep(3)

        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='General-Opt-Out-First-Name']", text=SuperScraper.FIRST_NAME, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='General-Opt-out-Last-Name']", text=SuperScraper.LAST_NAME, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='General-Opt-Out-Email']", text=SuperScraper.EMAIL, sleep=0.2)
        await super_scraper.input_text_field(tab=tab, xpath="//input[@id='General-Opt-Out-State']", text=SuperScraper.STATE, sleep=0.2)

        for name in dict.fromkeys(n for r in general_rights for n in GENERAL_BOXES[r]):
            await _check(tab, GENERAL_ANCHOR, name)

        names = ", ".join(r.name for r in general_rights)
        if SuperScraper.DRY_RUN:
            await asyncio.sleep(1)
            await SuperScraper.screenshot(tab, "dry_run_general")
            print(f"DRY RUN: would submit '{names}' for {SuperScraper.EMAIL}")
            return

        await super_scraper.click_item_by_xpath(tab=tab, xpath="//input[@id='General-Opt-Out-First-Name']/ancestor::form//input[@type='submit']", sleep=2)
        print(f"Submitted '{names}' for {SuperScraper.EMAIL} — confirm in the browser.")


asyncio.run(main())

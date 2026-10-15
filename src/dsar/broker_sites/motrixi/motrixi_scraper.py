# motrixi.com — /index.php/opt-out/ embeds a HubSpot form via the standard
# src-less `<iframe class="hs-form-iframe">` (hbspt.forms.create). Unlike the
# older note in scraper_dev_discoveries.md, pydoll CAN drive this: calling
# `.find()` on the iframe *WebElement* (not tab.find, not get_frame — both fail)
# resolves into the frame's document.
#
# The opt-out form is a single required textarea, "Enter Advertising ID"
# (name="enter_advertising_id_"), plus Submit — so this exercises Opt-Out only,
# keyed on the mobile advertising ID. Right to Access is email-only
# (privacy@Motrixi.com, never answered) — see README. No CAPTCHA (HubSpot's
# built-in spam protection is invisible). Whether it runs is decided ONLY by
# SuperScraper.rights_to_exercise(RIGHT_MAP).
#
# Page elements (keep this list current):
#   iframe.hs-form-iframe            HubSpot form iframe (find inside via the iframe WebElement)
#   textarea[name=enter_advertising_id_]   "Enter Advertising ID" (required)
#   input[type=submit]               Submit button
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.rights import Right
from src.dsar.super_scraper import SuperScraper

URL = "https://www.motrixi.com/index.php/opt-out/"

IFRAME_CLASS = "hs-form-iframe"  # HubSpot form iframe
AD_ID_NAME = "enter_advertising_id_"  # "Enter Advertising ID" textarea

RIGHT_MAP = {
    Right.RIGHT_TO_OPT_OUT: "opt-out by advertising ID",
}
RIGHTS_SUPPORTED = tuple(RIGHT_MAP)


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
        await tab.go_to(URL)
        await asyncio.sleep(8)

        iframe = await tab.find(class_name=IFRAME_CLASS, raise_exc=False)
        if not iframe:
            print(f"{super_scraper.OOPS} HubSpot form iframe not found")
            return

        ad_id_field = await iframe.find(xpath="//textarea", raise_exc=False)
        if not ad_id_field:
            ad_id_field = await iframe.find(xpath=f"//*[@name='{AD_ID_NAME}']", raise_exc=False)
        if ad_id_field:
            await ad_id_field.type_text(SuperScraper.ADVERTISING_ID)
        else:
            print(f"{super_scraper.OOPS} 'Enter Advertising ID' field not found in iframe")

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "dry_run_opt_out")
        if SuperScraper.DRY_RUN:
            print(f"DRY RUN: would submit 'RIGHT_TO_OPT_OUT' for advertising ID {SuperScraper.ADVERTISING_ID}")
            return

        submit = await iframe.find(xpath="//input[@type='submit']", raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(4)
            print(f"Submitted 'RIGHT_TO_OPT_OUT' for advertising ID {SuperScraper.ADVERTISING_ID} — confirm in the browser.")


asyncio.run(main())

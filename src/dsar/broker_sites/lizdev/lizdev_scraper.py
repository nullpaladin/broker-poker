# lizdev.com — https://lizdev.com/opt-out-form/  (WPForms form id 109).
# A single opt-out submission (no separate access/delete flow), so RIGHT_MAP has
# one entry; the run is skipped unless an opt-out right is requested.
# Fields (ids are WPForms-form-109 specific — reconfirm if the form is rebuilt):
#   field_1 / field_1-last   First / Last name          (required)
#   field_2 / field_2-secondary  Email / confirm email  (required)
#   field_5                  Phone Number               (required)
#   field_16                 "Type of Request" <select> (Personal / Business /
#                            Business on behalf of Individual) -> "Personal"
#   field_3                  "Custom Phone Type" (optional) -> left blank
#   field_20                 "Custom Captcha" Q&A — question like "What is 7+4?"
#                            in #wpforms-109-field_20-question, changes per load
#   field_23                 "Custom Captcha" math — equation rendered by JS into
#                            #wpforms-109-field_23-question ("6 x 3 =" etc.),
#                            covers add / subtract / multiply / divide
# Both custom captchas are solved with SuperScraper.solve_math_captcha. There is
# ALSO a Google reCAPTCHA v2 checkbox -> manual solve required in live mode.
import asyncio

from pydoll.browser.chromium import Chrome

from src.dsar.super_scraper import SuperScraper

URL = "https://lizdev.com/opt-out-form/"

RIGHT_MAP = {"opt_out_sale_share": "opt-out"}
RIGHTS_SUPPORTED = ("opt_out_sale_share",)

FIRST = "//input[@id='wpforms-109-field_1']"
LAST = "//input[@id='wpforms-109-field_1-last']"
EMAIL = "//input[@id='wpforms-109-field_2']"
EMAIL_CONFIRM = "//input[@id='wpforms-109-field_2-secondary']"
PHONE = "//input[@id='wpforms-109-field_5']"
TYPE_SELECT = "//select[@id='wpforms-109-field_16']"
QA_QUESTION = "//*[@id='wpforms-109-field_20-question']"
QA_ANSWER = "//input[@id='wpforms-109-field_20']"
MATH_QUESTION = "//*[@id='wpforms-109-field_23-question']"
MATH_ANSWER = "//input[@id='wpforms-109-field_23']"
SUBMIT = "//button[@id='wpforms-submit-109']"


async def _solve_captcha(tab, super_scraper, question_xpath, answer_xpath, name):
    q = await tab.find(xpath=question_xpath, raise_exc=False)
    if not q:
        print(f"{super_scraper.OOPS} {name} captcha question not found")
        return
    question_text = (await SuperScraper.js_eval(q, "return this.textContent")) or ""
    answer = SuperScraper.solve_math_captcha(question_text)
    if answer is None:
        print(f"{super_scraper.OOPS} could not parse {name} captcha: {question_text!r}")
        return
    field = await tab.find(xpath=answer_xpath, raise_exc=False)
    if field:
        await field.type_text(answer)
    else:
        print(f"{super_scraper.OOPS} {name} captcha answer field not found")


async def main():
    super_scraper = SuperScraper()
    if SuperScraper.bail_if_not_automatable(globals()):
        return
    if not SuperScraper.rights_to_exercise(RIGHT_MAP):
        print("lizdev is opt-out only; no opt-out right requested — skipping.")
        return

    options = SuperScraper.build_chromium_options()
    async with Chrome(options=options) as browser:
        tab = await browser.start()
        await tab.go_to(URL)
        await asyncio.sleep(5)

        await SuperScraper.input_text_field(tab=tab, xpath=FIRST, text=SuperScraper.FIRST_NAME, sleep=0.2)
        await SuperScraper.input_text_field(tab=tab, xpath=LAST, text=SuperScraper.LAST_NAME, sleep=0.2)
        await SuperScraper.input_text_field(tab=tab, xpath=EMAIL, text=SuperScraper.EMAIL, sleep=0.2)
        await SuperScraper.input_text_field(tab=tab, xpath=EMAIL_CONFIRM, text=SuperScraper.EMAIL, sleep=0.2)
        await SuperScraper.input_text_field(tab=tab, xpath=PHONE, text=SuperScraper.PHONE_NUMBER, sleep=0.2)

        type_select = await tab.find(xpath=TYPE_SELECT, raise_exc=False)
        if type_select:
            await SuperScraper.select_native_option(type_select, value="Personal")

        await _solve_captcha(tab, super_scraper, QA_QUESTION, QA_ANSWER, "Q&A")
        await _solve_captcha(tab, super_scraper, MATH_QUESTION, MATH_ANSWER, "math")

        if SuperScraper.HEALTH_CHECK:
            await SuperScraper.assert_fields_filled(tab, {
                "First name": FIRST, "Last name": LAST, "Email": EMAIL,
                "Confirm email": EMAIL_CONFIRM, "Phone": PHONE,
                "Type of Request": TYPE_SELECT,
                "Q&A captcha": QA_ANSWER, "Math captcha": MATH_ANSWER,
            })

        await asyncio.sleep(1)
        await SuperScraper.screenshot(tab, "resources/screenshots/lizdev_dry_run.png")

        if SuperScraper.DRY_RUN:
            print(
                f"DRY RUN: would submit opt-out for "
                f"{SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME} <{SuperScraper.EMAIL}>"
            )
            return

        print("\nForm filled. Solve the reCAPTCHA v2 checkbox, then press Enter to submit...")
        input()
        submit = await tab.find(xpath=SUBMIT, raise_exc=False)
        if submit:
            await submit.click()
            await asyncio.sleep(3)
        source = await SuperScraper.page_text(tab)
        if any(w in source.lower() for w in ("thank you", "success", "received", "submitted", "confirmation")):
            print(f"Submitted opt-out for {SuperScraper.FIRST_NAME} {SuperScraper.LAST_NAME}")
        else:
            print(f"{super_scraper.OOPS} Confirmation unclear — verify in browser")


asyncio.run(main())

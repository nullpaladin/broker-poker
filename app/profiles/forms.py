from django import forms

from app.profiles.env_mapping import FIELD_LABELS, REQUIRED
from src.state_privacy_request_factory.state_name_abbreviation import StateAbbreviation

STATES = sorted({s.name.replace("_", " ").title() for s in StateAbbreviation})


def _char(name):
    return forms.CharField(label=FIELD_LABELS[name], required=name in REQUIRED, max_length=200)


class IdentityForm(forms.Form):
    FIRST_NAME, LAST_NAME = _char("FIRST_NAME"), _char("LAST_NAME")
    DATE_OF_BIRTH = forms.CharField(label=FIELD_LABELS["DATE_OF_BIRTH"], required=False, max_length=10,
                                    help_text="Optional. Only some brokers ask for it.")


class AddressForm(forms.Form):
    ADDRESS, ADDRESS_LINE_TWO, CITY = _char("ADDRESS"), _char("ADDRESS_LINE_TWO"), _char("CITY")
    STATE = forms.ChoiceField(label="State", choices=[("", "Select…")] + [(s, s) for s in STATES])
    ZIP_CODE = _char("ZIP_CODE")


class ContactForm(forms.Form):
    EMAIL = forms.EmailField(label=FIELD_LABELS["EMAIL"])
    PHONE_NUMBER = _char("PHONE_NUMBER")


class OptionalForm(forms.Form):
    LAST_FOUR_SSN = forms.RegexField(r"^\d{4}$", label=FIELD_LABELS["LAST_FOUR_SSN"], required=False,
                                     help_text="Optional. Only 4 digits. Used by the few brokers that require it.")
    ADVERTISING_ID = _char("ADVERTISING_ID")
    LINKEDIN_URL, FACEBOOK_URL = _char("LINKEDIN_URL"), _char("FACEBOOK_URL")
    TWITTER_URL, INSTAGRAM_URL = _char("TWITTER_URL"), _char("INSTAGRAM_URL")
    JOB_TITLE, COMPANY_NAME = _char("JOB_TITLE"), _char("COMPANY_NAME")


class RightsForm(forms.Form):
    delete_enabled = forms.BooleanField(
        required=False, label="Also request deletion of my data",
        help_text="Access, opt-out and 'list of third parties' requests are always included. "
                  "Deletion is optional because it is permanent.")


class CaptchaForm(forms.Form):
    captcha_mode = forms.ChoiceField(
        widget=forms.RadioSelect, label="CAPTCHAs",
        choices=[("solve", "I'll solve CAPTCHAs in the browser window (sites that need this run first)"),
                 ("skip", "Skip every site that needs a human")])


STEPS = [
    ("identity", "About you", IdentityForm), ("address", "Address", AddressForm),
    ("contact", "Contact", ContactForm), ("optional", "Optional details", OptionalForm),
    ("rights", "Rights", RightsForm), ("captcha", "CAPTCHAs", CaptchaForm),
]
STEP_KEYS = [s[0] for s in STEPS]
for _form in (IdentityForm, AddressForm, ContactForm, OptionalForm):
    for _f in _form.base_fields.values():
        _f.widget.attrs.setdefault("autocomplete", "off")

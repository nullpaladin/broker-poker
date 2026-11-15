import json

from cryptography.fernet import Fernet
from django.db import models

from app import paths

CAPTCHA_MODES = [("solve", "Solve CAPTCHAs in the browser window"), ("skip", "Skip sites that need a human")]


def _fernet() -> Fernet:
    return Fernet(paths.fernet_key())


class Profile(models.Model):
    """Single local profile. PII lives in an encrypted blob; only the state is plaintext
    (needed for rights gating and harmless on its own)."""
    encrypted_pii = models.BinaryField(default=b"")
    state = models.CharField(max_length=40, blank=True)
    delete_enabled = models.BooleanField(default=False)
    captcha_mode = models.CharField(max_length=10, choices=CAPTCHA_MODES, default="solve")
    complete = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def data(self) -> dict:
        if not self.encrypted_pii:
            return {}
        return json.loads(_fernet().decrypt(bytes(self.encrypted_pii)))

    @data.setter
    def data(self, value: dict):
        self.encrypted_pii = _fernet().encrypt(json.dumps(value).encode())
        self.state = value.get("STATE", "")

    @classmethod
    def current(cls) -> "Profile":
        return cls.objects.first() or cls.objects.create()

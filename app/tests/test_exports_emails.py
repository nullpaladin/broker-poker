import pytest

from app.emails import helper
from app.exports import bundle

PAYLOAD = {"profile": {"EMAIL": "a@b.c"}, "settings": {"delete_enabled": False}}


def test_roundtrip_encrypted():
    blob = bundle.export_bundle(PAYLOAD, "pw")
    assert b"a@b.c" not in blob and bundle.needs_password(blob)
    assert bundle.import_bundle(blob, "pw") == PAYLOAD


def test_wrong_password_and_missing():
    blob = bundle.export_bundle(PAYLOAD, "pw")
    with pytest.raises(bundle.BundleError, match="Wrong password"):
        bundle.import_bundle(blob, "nope")
    with pytest.raises(bundle.BundleError, match="required"):
        bundle.import_bundle(blob)


def test_plaintext_and_history():
    blob = bundle.export_bundle(PAYLOAD, None, runs=[{"id": 1}])
    out = bundle.import_bundle(blob)
    assert out["runs"] == [{"id": 1}] and out["profile"]["EMAIL"] == "a@b.c"


def test_newer_schema_refused(monkeypatch):
    blob = bundle.export_bundle(PAYLOAD, None)
    monkeypatch.setattr(bundle, "SCHEMA_VERSION", 0)
    with pytest.raises(bundle.BundleError, match="newer"):
        bundle.import_bundle(blob)


def test_garbage():
    with pytest.raises(bundle.BundleError):
        bundle.import_bundle(b"not a zip")


def test_email_batches_and_body():
    bs = helper.batches()
    assert sum(map(len, bs)) == len(helper.recipients()) and all(len(b) <= 50 for b in bs)
    b = helper.body({"FIRST_NAME": "Jo", "LAST_NAME": "Doe", "EMAIL": "a@b.c"}, delete=False)
    assert "Email: a@b.c" in b and "Delete my personal data" not in b and "LAST" not in b
    assert "Delete my personal data" in helper.body({}, delete=True)

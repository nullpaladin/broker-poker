"""Profile export/import bundle (design doc §11): zip{manifest.json, profile.json[.enc]}.
Encrypted by default: PBKDF2-HMAC-SHA256 (600k) -> Fernet. Plaintext needs explicit opt-in."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import zipfile

from cryptography.fernet import Fernet, InvalidToken

SCHEMA_VERSION = 1
KDF_ITERATIONS = 600_000


class BundleError(Exception):
    pass


def _key(password: str, salt: bytes, iterations: int) -> bytes:
    return base64.urlsafe_b64encode(hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations, 32))


def export_bundle(payload: dict, password: str | None, runs: list | None = None) -> bytes:
    """payload: {"profile": {...}, "settings": {...}}. ``password=None`` => plaintext."""
    doc = dict(payload)
    if runs is not None:
        doc["runs"] = runs
    raw = json.dumps(doc, indent=2).encode()
    manifest = {"schema_version": SCHEMA_VERSION, "encrypted": password is not None, "has_run_history": runs is not None}
    if password is not None:
        salt = os.urandom(16)
        manifest["kdf"] = {"name": "pbkdf2-hmac-sha256", "iterations": KDF_ITERATIONS,
                           "salt": base64.b64encode(salt).decode()}
        raw = Fernet(_key(password, salt, KDF_ITERATIONS)).encrypt(raw)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        z.writestr("profile.json.enc" if password is not None else "profile.json", raw)
    return buf.getvalue()


def needs_password(blob: bytes) -> bool:
    return _manifest(blob)["encrypted"]


def _manifest(blob: bytes) -> dict:
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            return json.loads(z.read("manifest.json"))
    except (zipfile.BadZipFile, KeyError, ValueError):
        raise BundleError("This file is not a Broker Poker export.")


def _migrate(doc: dict, version: int) -> dict:
    # Chain of migrate_vN_to_vN+1 functions goes here as the schema evolves.
    return doc


def import_bundle(blob: bytes, password: str | None = None) -> dict:
    m = _manifest(blob)
    version = m.get("schema_version")
    if not isinstance(version, int):
        raise BundleError("This file is not a Broker Poker export.")
    if version > SCHEMA_VERSION:
        raise BundleError("This export was made by a newer version of Broker Poker. Please update the app.")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        try:
            raw = z.read("profile.json.enc" if m["encrypted"] else "profile.json")
        except KeyError:
            raise BundleError("The export is missing its profile data.")
    if m["encrypted"]:
        if not password:
            raise BundleError("This export is encrypted — a password is required.")
        kdf = m["kdf"]
        try:
            raw = Fernet(_key(password, base64.b64decode(kdf["salt"]), int(kdf["iterations"]))).decrypt(raw)
        except InvalidToken:
            raise BundleError("Wrong password (or the file was modified).")
    try:
        return _migrate(json.loads(raw), version)
    except ValueError:
        raise BundleError("The export could not be read.")

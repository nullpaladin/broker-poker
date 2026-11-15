"""Filesystem locations. Data lives outside the repo so profiles are never committed."""
import os
import secrets
from pathlib import Path

from platformdirs import user_data_dir

REPO_ROOT = Path(__file__).resolve().parent.parent
BROKER_SITES = REPO_ROOT / "src" / "dsar" / "broker_sites"
README = REPO_ROOT / "README.md"


def data_dir() -> Path:
    d = Path(os.environ.get("BROKER_POKER_DATA_DIR") or user_data_dir("broker-poker"))
    d.mkdir(parents=True, exist_ok=True)
    try:
        d.chmod(0o700)
    except OSError:
        pass
    return d


def runs_dir() -> Path:
    d = data_dir() / "runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _secret_file(name: str, make) -> bytes:
    p = data_dir() / name
    if not p.exists():
        p.write_bytes(make())
        try:
            p.chmod(0o600)
        except OSError:
            pass
    return p.read_bytes()


def django_secret_key() -> str:
    return _secret_file("django.key", lambda: secrets.token_hex(32).encode()).decode()


def fernet_key() -> bytes:
    from cryptography.fernet import Fernet
    return _secret_file("profile.key", Fernet.generate_key)

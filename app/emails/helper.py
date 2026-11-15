"""Email-broker helper: batches of recipients + the Minnesota template filled from the profile."""
from __future__ import annotations

from urllib.parse import quote

from app import paths

EMAIL_DIR = paths.REPO_ROOT / "src" / "dsar" / "emails"
BATCH_SIZE = 50


def recipients() -> list[str]:
    seen, out = set(), []
    for line in (EMAIL_DIR / "verified_email_list.txt").read_text(encoding="utf-8").splitlines():
        e = line.strip()
        if e and "@" in e and e.lower() not in seen:
            seen.add(e.lower())
            out.append(e)
    return out


def batches(size: int = BATCH_SIZE) -> list[list[str]]:
    r = recipients()
    return [r[i:i + size] for i in range(0, len(r), size)]


def subject() -> str:
    return "Minnesota Consumer Data Privacy Act Request"


def body(data: dict, delete: bool) -> str:
    text = (EMAIL_DIR / "mcdpa_email_template.txt").read_text(encoding="utf-8")
    addr = ", ".join(p for p in [data.get("ADDRESS"), data.get("ADDRESS_LINE_TWO"), data.get("CITY"),
                                 f'{data.get("STATE", "")} {data.get("ZIP_CODE", "")}'.strip()] if p)
    fills = {"Name:": f'{data.get("FIRST_NAME", "")} {data.get("LAST_NAME", "")}'.strip(),
             "Email:": data.get("EMAIL", ""), "Phone Number:": data.get("PHONE_NUMBER", ""),
             "Home Address:": addr, "Mobile Advertising ID:": data.get("ADVERTISING_ID", "")}
    lines = []
    for ln in text.splitlines():
        for k, v in fills.items():
            if ln.strip() == k:
                ln = f"{k} {v}"
        lines.append(ln)
    out = "\n".join(lines)
    if not delete:
        out = out.replace(" (you must delete data LAST)", "")
        out = out.replace("4. Delete my personal data from your systems\n  - Minnesota statute 325M.14(d)\n", "")
    return out.rstrip() + "\n" + f'{data.get("FIRST_NAME", "")} {data.get("LAST_NAME", "")}'.strip() + "\n"


def mailto(batch: list[str]) -> str:
    # Recipients go in BCC so brokers can't see each other. Body is too long for a mailto: URL
    # in many clients, so it is copied separately.
    return f"mailto:?bcc={quote(','.join(batch), safe='@,')}&subject={quote(subject())}"

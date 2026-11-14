"""The four standardized privacy rights every scraper maps its form onto.

Rights beyond these (e.g. right to correct) may exist on a form but cannot be
automated, so they are not enumerated — list them as ``None`` in a scraper's
``PAGE_RIGHTS`` inventory instead (see the health-check audit skill).
Not every site offers every right. ``RIGHT_TO_OPT_OUT`` covers *all* opt-out
flavours (sale/sharing, targeted advertising, profiling, limiting sensitive
data); a scraper whose form splits them lists each form option under that one key.
"""

from __future__ import annotations

from enum import Enum


class Right(str, Enum):
    RIGHT_TO_ACCESS = "access"
    RIGHT_TO_OPT_OUT = "opt_out"
    RIGHT_TO_DELETE = "delete"
    RIGHT_TO_LIST_OF_THIRD_PARTIES = "list_of_third_parties"

    @classmethod
    def parse(cls, token: str) -> "Right | None":
        """``"RIGHT_TO_ACCESS"`` / ``"access"`` / ``"right to access"`` -> member, else None."""
        norm = token.strip().lower().replace("-", "_").replace(" ", "_")
        for member in cls:
            if norm in (member.name.lower(), member.value):
                return member
        return None


RIGHT_DISPLAY = {
    Right.RIGHT_TO_ACCESS: "access to and a copy of my personal data",
    Right.RIGHT_TO_OPT_OUT: "opt-out of the sale or sharing of my personal data, targeted "
    "advertising, profiling, and the use of my sensitive personal information",
    Right.RIGHT_TO_DELETE: "deletion of my personal data",
    Right.RIGHT_TO_LIST_OF_THIRD_PARTIES: "a list of the specific third parties to which my "
    "personal data has been disclosed",
}

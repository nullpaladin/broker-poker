"""Static scraper registry. Scrapers are NEVER imported (each ends in a bare
``asyncio.run(main())``); we parse them with ``ast`` and read the README sections
for each broker's inclusion status."""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app import paths

SECTION_STATUS = {
    "Automated sites": "automated",
    "Sites that cannot be automated": "not_automatable",
    "Sites requiring a manual record lookup first": "manual_lookup",
    "Sites to retry later": "retry_later",
}
STATUS_REASON = {
    "not_automatable": "Cannot be automated (bot wall, dead site, or manual-only process).",
    "manual_lookup": "Requires finding your own record on the site first.",
    "retry_later": "Not reliably automatable yet.",
}


@dataclass(frozen=True)
class ScraperInfo:
    slug: str
    display_name: str
    path: Path
    urls: tuple = ()
    needs_human: bool = False
    status: str = "automated"  # automated | not_automatable | manual_lookup | retry_later
    note: str = ""

    @property
    def runnable(self) -> bool:
        return self.status == "automated"

    @property
    def skip_reason(self) -> str:
        return STATUS_REASON.get(self.status, "")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _domain_key(domain: str) -> str:
    d = domain.lower().removeprefix("www.")
    return _norm(d.rsplit(".", 1)[0] if "." in d else d)


def parse_readme_statuses(readme_text: str) -> dict[str, tuple[str, str]]:
    """{normalized-domain-key: (status, domain)} from the README broker sections."""
    out: dict[str, tuple[str, str]] = {}
    status = None
    for line in readme_text.splitlines():
        if line.startswith("## "):
            status = SECTION_STATUS.get(line[3:].strip())
            continue
        if line.startswith("# "):
            status = None
            continue
        m = re.match(r"- \[[ x]\] (\S+)", line)
        if m and status:
            out[_domain_key(m.group(1))] = (status, m.group(1))
    return out


def analyze_source(source: str) -> tuple[tuple, bool]:
    """(module-level http URL string constants, calls input())."""
    tree = ast.parse(source)
    urls, needs_human = [], False
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str) and node.value.value.startswith("http"):
            urls.append(node.value.value)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "input":
            needs_human = True
            break
    return tuple(urls), needs_human


@lru_cache(maxsize=4)
def _load(broker_sites: Path, readme: Path) -> tuple[ScraperInfo, ...]:
    statuses = parse_readme_statuses(readme.read_text(encoding="utf-8")) if readme.exists() else {}
    infos = []
    for path in sorted(broker_sites.glob("*/*_scraper.py")):
        slug = path.parent.name
        try:
            urls, needs_human = analyze_source(path.read_text(encoding="utf-8"))
        except SyntaxError:
            urls, needs_human = (), False
        status, domain = statuses.get(_norm(slug), ("automated", slug))
        infos.append(ScraperInfo(slug=slug, display_name=domain, path=path, urls=urls,
                                 needs_human=needs_human, status=status))
    return tuple(infos)


def all_scrapers(broker_sites: Path | None = None, readme: Path | None = None) -> list[ScraperInfo]:
    return list(_load(broker_sites or paths.BROKER_SITES, readme or paths.README))


def get(slug: str) -> ScraperInfo | None:
    return next((s for s in all_scrapers() if s.slug == slug), None)

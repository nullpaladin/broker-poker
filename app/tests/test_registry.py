import sys

from app.scrapers import registry


def test_analyze_source():
    urls, human = registry.analyze_source('URL = "https://a.example/x"\nOTHER = "nope"\ndef f():\n    input()\n')
    assert urls == ("https://a.example/x",) and human


def test_analyze_no_input():
    assert registry.analyze_source("X = 1\n") == ((), False)


def test_readme_sections():
    text = "## Sites to retry later\n- [ ] foo-bar.com\n## Automated sites\n- [x] 33across.com\n# Other\n- [x] zzz.com\n"
    st = registry.parse_readme_statuses(text)
    assert st["foobar"][0] == "retry_later" and st["33across"][0] == "automated" and "zzz" not in st


def test_real_repo_scan_does_not_import():
    before = {m for m in sys.modules if "broker_sites" in m}
    infos = registry.all_scrapers()
    assert len(infos) > 200
    assert {m for m in sys.modules if "broker_sites" in m} == before
    assert any(i.needs_human for i in infos) and any(i.runnable for i in infos)
    assert any(not i.runnable for i in infos)

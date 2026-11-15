import pytest


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("BROKER_POKER_DATA_DIR", str(tmp_path_factory.mktemp("bpdata")))

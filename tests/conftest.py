import pytest


@pytest.fixture(autouse=True)
def isolated_logs(tmp_path, monkeypatch):
    """Never write test logs into the real ~/.simplutils folder."""
    monkeypatch.setenv("simplutils_LOG_DIR", str(tmp_path / "logs"))
    yield
    import logging

    for h in list(logging.getLogger("simplutils").handlers):
        if getattr(h, "_simplutils_handler", False):
            logging.getLogger("simplutils").removeHandler(h)
            h.close()

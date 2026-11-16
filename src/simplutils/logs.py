"""Logging setup. Logs go to ~/.simplutils/simplutils.log (override the folder with simplutils_LOG_DIR).

Privacy: only tool names, sizes, timings and non-text option values are logged,
never the content you process.
"""
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List

LOGGER_NAME = "simplutils"
_FORMAT = "%(asctime)s %(levelname)-7s %(message)s"
_MARK = "_simplutils_handler"


def log_dir() -> Path:
    return Path(os.environ.get("simplutils_LOG_DIR") or (Path.home() / ".simplutils"))


def log_path() -> Path:
    return log_dir() / "simplutils.log"


def setup_logging(verbose: bool = False) -> None:
    """Attach a rotating file handler (and a console handler if verbose). Safe to call repeatedly."""
    logger = logging.getLogger(LOGGER_NAME)
    for h in list(logger.handlers):
        if getattr(h, _MARK, False):
            logger.removeHandler(h)
            h.close()
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    try:
        log_dir().mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(log_path(), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(_FORMAT))
        setattr(fh, _MARK, True)
        logger.addHandler(fh)
    except OSError:
        pass  # logging must never break the tool (e.g. read-only home folder)

    if verbose:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        setattr(ch, _MARK, True)
        logger.addHandler(ch)


def tail(n: int = 20) -> List[str]:
    """Return the last n lines of the log file."""
    try:
        with open(log_path(), encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()[-n:]
    except OSError:
        return []

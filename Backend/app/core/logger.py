"""
Structured logger for Spend Analyser
"""
import logging
import sys


def _make_logger() -> logging.Logger:
    log = logging.getLogger("spend_analyser")
    log.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    if not log.handlers:
        log.addHandler(handler)
    return log


logger = _make_logger()

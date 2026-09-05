"""
Application logging setup. Separate from the cleanup audit log
(cleanup_log.jsonl) — this is for general diagnostic/debug output,
not a compliance record of destructive actions.
"""

import logging


def get_logger(name: str = "cloud-auditor") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
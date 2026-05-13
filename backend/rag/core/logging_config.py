"""Structured logging for the RAG service (stdout, suitable for Docker/K8s)."""

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    lvl = getattr(logging, str(level).upper(), logging.INFO)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(lvl)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(lvl)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(fmt)
    root.addHandler(handler)

    # Quieter noisy libraries in production
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

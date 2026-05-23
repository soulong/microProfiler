"""Logging configuration for microProfiler."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    name: str = "microProfiler",
    level: int = logging.INFO,
    log_file: Path | None = None,
    qt_handler: Optional[logging.Handler] = None,
    clear_existing: bool = True,
) -> logging.Logger:
    """Configure and return a logger instance.

    Parameters
    ----------
    name : str
        Logger name.
    level : int
        Logging level (e.g., logging.DEBUG).
    log_file : Path, optional
        If set, also write logs to this file.
    qt_handler : logging.Handler, optional
        If set, add this handler instead of the default StreamHandler.
    clear_existing : bool
        If True, clear all existing handlers before adding new ones.

    Returns
    -------
    logging.Logger
        Configured logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if clear_existing and logger.hasHandlers():
        logger.handlers.clear()

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    if qt_handler:
        qt_handler.setLevel(level)
        qt_handler.setFormatter(fmt)
        logger.addHandler(qt_handler)
    elif clear_existing:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(level)
        console.setFormatter(fmt)
        logger.addHandler(console)

    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file)
        fh.setLevel(level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger

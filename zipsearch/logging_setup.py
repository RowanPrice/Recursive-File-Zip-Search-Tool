"""One logging setup shared by the command line and zipsearch modules."""

import logging
import sys
from pathlib import Path
from typing import Optional, TextIO

from zipsearch.models import Path as FilePath

LOGGER_NAME = "zipsearch"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_path: FilePath = "zipsearch.log", *, console: Optional[TextIO] = None
) -> logging.Logger:
    """Send INFO, WARNING and ERROR messages to the console and a UTF-8 file.

    Append so earlier runs are kept. The parent folder must already exist.
    Configure only our logger, not other libraries or the global root logger.
    Calling this again replaces our handlers rather than doubling messages.
    Open the new file first so a failed change keeps the old setup working.
    """
    logger = logging.getLogger(LOGGER_NAME)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    try:
        # errors="backslashreplace" keeps a filename with odd bytes from
        # breaking the log write; it appears as a readable \xNN-style escape.
        # Open the stream ourselves because FileHandler only gained the
        # errors option in Python 3.9, and this project supports 3.8.
        file_handler = logging.StreamHandler(
            open(Path(log_path), "a", encoding="utf-8", errors="backslashreplace")
        )
    except OSError:
        # The requested file cannot be used, so report to the console instead.
        fallback = logging.StreamHandler(console if console is not None else sys.stderr)
        fallback.setFormatter(formatter)
        fallback.handle(logger.makeRecord(
            LOGGER_NAME, logging.ERROR, __file__, 0,
            "Cannot open log file: %s", (str(log_path),), sys.exc_info(),
        ))
        fallback.close()
        raise
    console_handler = logging.StreamHandler(console if console is not None else sys.stderr)
    for handler in (console_handler, file_handler):
        handler.setFormatter(formatter)
        handler.setLevel(logging.INFO)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


def log_errors(function):
    """Log a helper's failures and re-raise the same exception for its caller.

    Generators need a separate wrapper: their work happens during iteration,
    not when the function is first called. No handlers are added here; calling
    setup_logging once makes all module loggers share the same destinations.
    """
    from functools import wraps
    from inspect import isgeneratorfunction

    logger = logging.getLogger(function.__module__)

    if isgeneratorfunction(function):
        @wraps(function)
        def generator_wrapper(*args, **kwargs):
            try:
                yield from function(*args, **kwargs)
            except Exception:
                logger.exception("%s failed", function.__name__)
                raise
        return generator_wrapper

    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception:
            logger.exception("%s failed", function.__name__)
            raise
    return wrapper

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler


def init_logger(
    name: str = __name__,
    level: int = logging.INFO,
    preinstalled_lib_logs_override: tuple[str] | None = ("BERTopic",),
    width: int = 200,
) -> logging.Logger:
    console = Console(file=sys.stdout, width=width)

    rich_handler = RichHandler(console=console, rich_tracebacks=True, markup=True, show_time=True, show_path=True)

    formatter = logging.Formatter("%(message)s")
    rich_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()

    logger.addHandler(rich_handler)

    for lib in preinstalled_lib_logs_override:
        lib_logger = logging.getLogger(lib)
        lib_logger.setLevel(level)  # Use the same level as the main logger

        # Clear any existing handlers from the lib logger
        if lib_logger.handlers:
            lib_logger.handlers.clear()

        # Add the same Rich handler to the lib logger
        lib_logger.addHandler(rich_handler)

    return logger

import logging
import sys


def get_logger(log_path: str) -> logging.Logger:
    """Configures logger to write to both the console and script-specific logfile"""
    logger = logging.getLogger(log_path)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # write to log
        file_handler = logging.FileHandler(log_path)

        # write to console
        console_handler = logging.StreamHandler(sys.stdout)

        # remove timestamps, log level, etc.
        formatter = logging.Formatter("%(message)s")
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

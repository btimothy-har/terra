import logging

__all__ = ["logger"]


def initialize_logger():
    logger = logging.getLogger("jobs")
    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s [%(asctime)s] %(name)s: %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


logger = initialize_logger()

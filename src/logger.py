# src/logger.py
import logging, sys
def get_logger(name="gmail_to_sheets"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        h = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
        h.setFormatter(fmt)
        logger.addHandler(h)
    return logger

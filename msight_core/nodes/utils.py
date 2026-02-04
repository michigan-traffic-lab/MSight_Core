import logging
from .. import LOGGING_LEVEL, MSIGHT_EDGE_DEVICE_NAME


def create_logger(prefix, logging_level=LOGGING_LEVEL):
    logger = logging.getLogger(prefix)
    logger.propagate = False
    ch = logging.StreamHandler()
    formatter = logging.Formatter(
        f"%(asctime)s - {MSIGHT_EDGE_DEVICE_NAME} - %(name)s - %(levelname)s :: %(message)s"
    )
    ch.setFormatter(formatter)
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(ch)
    logger.setLevel(logging_level)
    return logger

class Counter:
    # a utility class to periodically countdown
    # Counter(1) means always return true
    # Counter(2) will be false-true-false-true sequence...
    def __init__(self, period):
        self.period = period
        self.counter = 0
    
    def countdown(self):
        if self.period < 0:
            return False # Always return False if period is negative
        self.counter += 1
        if self.counter >= self.period:
            self.counter = 0
            return True
        return False


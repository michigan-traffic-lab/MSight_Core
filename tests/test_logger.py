from msight_core.nodes.utils import create_logger

import logging

def test_create_logger():
    # logging.basicConfig(level=logging.DEBUG)
    logger = create_logger("test")
    assert logger.level == logging.INFO
    logger.debug("debug1")
    logger.info("info1")
    logger.warning("warning1")
    logger.error("error1")
    logger.critical("critical1")

    logger.setLevel(logging.ERROR)
    logger.debug("debug2")
    logger.info("info2")
    logger.warning("warning2")
    logger.error("error2")
    logger.critical("critical2")
    assert logger.level == logging.ERROR


    

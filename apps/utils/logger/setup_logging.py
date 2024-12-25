import logging

def setup_logging(module_name=__name__, log_level=logging.DEBUG):
    # Setup logger
    logger = logging.getLogger(module_name)
    logger.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Setup console stream handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

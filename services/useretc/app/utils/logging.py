import logging

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(module)s - %(funcName)s - line:%(lineno)d - %(levelname)s - %(message)s"
    )

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch) #Exporting logs to the screen

    #fh = logging.FileHandler(filename='./server.log')
    #fh.setFormatter(formatter)
    #logger.addHandler(fh) #Exporting logs to a file

    return logger

log = setup_logging()

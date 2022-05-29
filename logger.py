import logging
import logging.handlers
import sys
import os

filename = 'logs/wizard.log'
logger = logging.getLogger('wizard')
logger.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
file_handler = logging.handlers.RotatingFileHandler(filename=filename, mode='w', backupCount=5, delay=True)
file_handler.setFormatter(file_formatter)
if os.path.isfile(filename):
    file_handler.doRollover()
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(stream_handler)

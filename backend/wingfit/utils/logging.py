import logging
from logging.handlers import RotatingFileHandler

from ..config import settings

# app_logger contains the logging from the code, mostly before raises, acting as information
app_logger = logging.getLogger("wingfit.app")
app_logger.setLevel(logging.INFO)

app_console_handler = logging.StreamHandler()
app_console_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
app_logger.addHandler(app_console_handler)

# request_logger contains the logging of every request, from the middleware. JSONL format.
request_logger = logging.getLogger("wingfit.requests")
request_logger.setLevel(logging.DEBUG)

request_file_handler = RotatingFileHandler(settings.LOG_FILE, maxBytes=5000000)
request_file_handler.setFormatter(logging.Formatter("%(message)s"))
request_logger.addHandler(request_file_handler)

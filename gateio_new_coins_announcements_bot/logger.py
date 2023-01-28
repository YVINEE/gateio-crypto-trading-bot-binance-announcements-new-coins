import logging
import os

from gateio_new_coins_announcements_bot.load_config import load_config
from gateio_new_coins_announcements_bot.send_telegram import TelegramHandler
from gateio_new_coins_announcements_bot.send_telegram import TelegramLogFilter
from gateio_new_coins_announcements_bot.sqlite_handler import SQLiteHandler

# loads local configuration
config = load_config("config.yml")

log = logging

# Set default log settings
log_level = "INFO"
cwd = os.getcwd()

db_dir = os.path.join(cwd, "logs")
db_file = "bot.db3"
db_path = os.path.join(db_dir, db_file)
log_table = 'log'

# create logging directory
if not os.path.exists(db_dir):
    os.mkdir(db_dir)

try:
    log_telegram = config["TELEGRAM"]["ENABLED"]
except KeyError:
    pass
    
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

#WARNING: attributes must be choosen from https://docs.python.org/3/library/logging.html#formatter-objects
attributes_list = ['asctime', 'levelname', 'message'] 
DEFAULT_SEPARATOR = '|'
formatter = logging.Formatter('%(' + ((')s' + DEFAULT_SEPARATOR + '%(').join(attributes_list)) + ')s')

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

sql_handler = SQLiteHandler(database = db_path, table = log_table, attributes_list = attributes_list)
sql_handler.setLevel(logging.DEBUG)
sql_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(sql_handler)

if log_telegram:
    telegram_handler = TelegramHandler()
    telegram_handler.addFilter(TelegramLogFilter())  # only handle messages with extra: TELEGRAM
    telegram_handler.setLevel(logging.NOTSET)  # so that telegram can recieve any kind of log message
    logger.addHandler(telegram_handler)

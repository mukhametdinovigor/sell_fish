import logging

from environs import Env
import telegram

env = Env()
env.read_env()


class TelegramLogsHandler(logging.Handler):
    def __init__(self, chat_id):
        super().__init__()
        tg_bot = telegram.Bot(token=env.str('BUG_REPORTING_BOT_TOKEN'))
        self.chat_id = chat_id
        self.tg_bot = tg_bot

    def emit(self, record):
        log_entry = self.format(record)
        self.tg_bot.send_message(chat_id=self.chat_id, text=log_entry)

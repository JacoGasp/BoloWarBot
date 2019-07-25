import os
import logging
import requests

token = os.environ["API_TOKEN"]
chat_id = os.environ["CHAT_ID"]


class TelegramHandler(logging.Handler):
    url = f"https://api.telegram.org/bot{token}/sendMessage?"

    def emit(self, record):
        log_entry = self.format(record)
        json = {
            "chat_id": chat_id,
            "text": log_entry
        }
        return requests.post(self.url, json=json).content

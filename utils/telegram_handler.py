import json
import logging
import requests

from telegram.ext import Updater
from telegram import InputFile, parsemode
from telegram.error import *


class TelegramHandler(object):

    def __init__(self, token, chat_id):
        # ---------------------------------------- #
        # Start the Telegram updater
        self.token = token
        self.chat_id = chat_id
        self.updater = Updater(token=token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        self.bot = self.dispatcher.bot
        self.logger = logging.getLogger(self.__class__.__name__)

        self.last_update_id = 0
        self.get_last_update_id()
        self.__msg_cache_handler = None
        self.__stats_handler = None

    def send_message(self, message):
        try:
            self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode=parsemode.ParseMode.MARKDOWN)
            self.__msg_cache_handler.remove_msg_from_cache()
        except (TelegramError, NetworkError, Unauthorized, TimeoutError) as e:
            self.__msg_cache_handler.add_msg_to_cache(message)
            self.logger.warning("Message not sent; saved on cache: %s", e)

    def send_image(self, path, caption=None, battle_round=None):
        try:
            with open(path, "rb") as img:
                self.bot.send_photo(photo=InputFile(img), chat_id=self.chat_id, caption=caption, parse_mode=parsemode.ParseMode.MARKDOWN)
                self.__msg_cache_handler.remove_msg_from_cache()

        except (TelegramError, NetworkError, Unauthorized, TimeoutError) as e:
            self.__msg_cache_handler.add_photo_to_cache(caption=caption, battle_round=battle_round)
            self.logger.warning("Map not sent saved on cache: %s", e)

    def telegram_api(self, command, **kwargs):
        url = f"https://api.telegram.org/bot{self.token}/{command}?"
        r = requests.post(url, json=kwargs)
        return json.loads(r.content)

    def get_last_update_id(self):
        updates = self.bot.get_updates()
        if len(updates) > 0:
            current_update_id = updates[-1].update_id

            while self.last_update_id < current_update_id:
                self.last_update_id = current_update_id
                current_update_id = self.bot.get_updates()[-1].update_id

    def send_poll(self, attacker_name, defender_name, question):

        poll = dict(
            chat_id=self.chat_id,
            question=question,
            options=[attacker_name, defender_name],
            disable_notification=True,
        )

        r = self.telegram_api("sendPoll", **poll)

        if not r["ok"]:
            self.logger.error("Cannot open poll")
            raise TelegramError("%s: Cannot open poll" % __name__)

        message_id = r["result"]["message_id"]
        poll_id = r["result"]["poll"]["id"]

        self.logger.debug("Poll successfully opened. message_id: %s, poll_id: %s", message_id, poll_id)

        return message_id, poll_id

    def stop_poll(self, message_id):
        self.logger.debug("Closing Poll")
        args = dict(chat_id=self.chat_id, message_id=message_id)
        r = self.telegram_api("stopPoll", **args)
        if not r["ok"]:
            self.logger.error("Cannot stop poll with message id %s", message_id)
            raise RuntimeError("%s: Cannot stop poll with message_id %s" % (__name__, message_id))
        self.logger.debug("Successfully closed poll with message_id %s" % message_id)

    def get_poll(self, poll_id):

        # Recompute last update id
        self.get_last_update_id()

        r = self.telegram_api("getUpdates", **dict(offset=self.last_update_id))

        if not r["ok"]:
            self.logger.error("Cannot get poll with poll_id %s", poll_id)
            raise RuntimeError("%s Cannot get poll with poll_id %s" % (__name__, poll_id))

        results = r["result"]
        self.last_update_id = results[-1]["update_id"]

        poll = filter(lambda x: "poll" in x, results)
        poll = filter(lambda x: x["poll"]["id"] == poll_id, poll)
        poll = list(poll)

        if len(poll) > 0:
            self.logger.debug("Successfully got poll with poll_id %s", poll_id)
        else:
            self.logger.warning("Cannot find poll with poll_id %s", poll_id)

        return poll

    def get_last_poll(self, poll_id):
        poll = self.get_poll(poll_id)

        ids = [x["update_id"] for x in poll]

        for update in poll:
            if update["update_id"] == max(ids):

                # Write poll results to stats
                if self.stats_handler is not None:
                    self.stats_handler.stats.append(update["poll"])

                return update["poll"]

    def get_last_poll_results(self, poll_id):
        poll = self.get_last_poll(poll_id)

        # The poll is empty
        if poll is None:
            self.logger.debug("The poll is empty")
            return None

        if not poll["is_closed"]:
            raise RuntimeError("%s: This poll is not closed" % __name__)

        # Count the results
        results = {}
        total_votes = 0
        for option in poll["options"]:
            results[option["text"]] = option["voter_count"]
            total_votes += option["voter_count"]

        self.logger.debug("%d people voted the poll with poll_id: %s" % (total_votes, poll_id))
        return results

    def send_cached_data(self):

        if self.__msg_cache_handler is not None:
            cached_msgs = self.__msg_cache_handler.get_cached_msgs()
            if cached_msgs is not None:
                self.logger.info("Sending %d cached messages", len(cached_msgs))

                for cached_msg in cached_msgs:
                    if cached_msg["type"] == "text":
                        self.send_message(cached_msg["message"])
                    if cached_msg["type"] == "image":
                        try:
                            self.send_image(path=cached_msg["fname"], caption=cached_msg["caption"])
                        except FileNotFoundError as e:
                            self.logger.warning("Cannot send cached image: %s", e)

                # Clear cache
                self.__msg_cache_handler.remove_photo_cache_files()
                self.__msg_cache_handler.remove_msg_cache_file()

    @property
    def msg_cache_handler(self):
        return self.__msg_cache_handler

    @msg_cache_handler.setter
    def msg_cache_handler(self, obj):
        self.__msg_cache_handler = obj

    @property
    def stats_handler(self):
        return self.__stats_handler

    @stats_handler.setter
    def stats_handler(self, obj):
        self.__stats_handler = obj

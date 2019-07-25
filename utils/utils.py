import yaml
import os
import requests
import json
import logging
import logging.config
token = os.environ["API_TOKEN"]
chat_id = os.environ["CHAT_ID"]

with open("config/logging.yaml", "rt") as f:
    logging_config = yaml.safe_load(f)
    logging.config.dictConfig(logging_config)

logger = logging.getLogger("Utils")


def telegram_api(command, **kwargs):
    url = f"https://api.telegram.org/bot{token}/{command}?"
    r = requests.post(url, json=kwargs)
    return json.loads(r.content)


def send_poll(attacker_name, defender_name):
    poll = dict(
        chat_id=chat_id,
        question=config["poll"]["question_message"],
        options=[attacker_name, defender_name],
        disable_notification=True,
    )
    r = telegram_api("sendPoll", **poll)
    if not r["ok"]:
        logger.error("Cannot open poll")
        raise RuntimeError("%s: Cannot open poll" % __name__)

    message_id = r["result"]["message_id"]
    poll_id = r["result"]["poll"]["id"]

    logger.debug("Poll successfully opened. message_id: %s, poll_id: %s", message_id, poll_id)
    return message_id, poll_id


def get_poll(poll_id):
    r = telegram_api("getUpdates", **dict(chat_id=chat_id))
    if not r["ok"]:
        logger.error("Cannot get poll with poll_id %s", poll_id)
        raise RuntimeError("%s Cannot get poll with poll_id %s" % (__name__, poll_id))

    logger.debug("Successfully got poll with poll_id %s" % poll_id)
    results = r["result"]
    poll = filter(lambda x: "poll" in x, results)
    poll = filter(lambda x: x["poll"]["id"] == poll_id, poll)
    return list(poll)


def get_last_poll(poll_id):
    poll = get_poll(poll_id)

    ids = [x["update_id"] for x in poll]

    for update in poll:
        if update["update_id"] == max(ids):
            return update["poll"]


def get_last_poll_results(poll_id):
    poll = get_last_poll(poll_id)

    # The poll is empty
    if poll is None:
        logger.debug("The poll is empty")
        return None

    if not poll["is_closed"]:
        raise RuntimeError("%s: This poll is not closed" % __name__)

    # Count the results
    results = {}
    total_votes = 0
    for option in poll["options"]:
        results[option["text"]] += option["voter_count"]
        total_votes += option["voter_count"]

    logger.debug("%d people voted the poll with poll_id: %s" % (total_votes, poll_id))
    return results


def stop_poll(message_id):
    logging.debug("Closing Poll")
    args = dict(chat_id=chat_id, message_id=message_id)
    r = telegram_api("stopPoll", **args)
    if not r["ok"]:
        logger.error("Cannot stop poll with message id %s", message_id)
        raise RuntimeError("%s: Cannot stop poll with message_id %s" % (__name__, message_id))
    logger.debug("Successfully closed poll with message_id %s" %message_id)


def load_messages(language):
    with open("config/messages.yaml") as stream:
        return yaml.load(stream, Loader=yaml.FullLoader)[language]


def load_configs():
    with open("config/config.yaml") as stream:
        logger.debug("Configurations successfully loaded")
        return yaml.load(stream, Loader=yaml.FullLoader)


config = load_configs()
messages = load_messages(config["language"])

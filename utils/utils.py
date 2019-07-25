import yaml
import os
import requests
import json
import logging

token = os.environ["API_TOKEN"]
chat_id = os.environ["CHAT_ID"]

logger = logging.getLogger(__name__)


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
        logging.error("Cannot open poll")

    message_id = r["result"]["message_id"]
    poll_id = r["result"]["poll"]["id"]
    return message_id, poll_id


def get_poll(poll_id):
    response = telegram_api("getUpdates", **dict(chat_id=chat_id))
    results = response["result"]
    poll = filter(lambda x: "poll" in x, results)
    # poll = [x["poll"] for x in poll]
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
    # if not poll["is_closed"]:
    #     raise RuntimeError("This poll is not closed")

    results = {}
    for option in poll["options"]:
        if option["text"] in results:
            results[option["text"]] += option["voter_count"]
        else:
            results[option["text"]] = option["voter_count"]
    return results


def stop_poll(message_id):
    logging.debug("Closing Poll")
    args = dict(chat_id=chat_id, message_id=message_id)
    r = telegram_api("stopPoll", **args)
    if not r["ok"]:
        logger.error("Cannot stop poll with message id %s" % message_id)


def load_messages(language):
    with open("config/messages.yaml") as stream:
        return yaml.load(stream, Loader=yaml.FullLoader)[language]


def load_config():
    with open("config/config.yaml") as stream:
        return yaml.load(stream, Loader=yaml.FullLoader)


messages = load_messages("it")
config = load_config()

# message_id, poll_id = send_poll("Bologna", "Modena")
# print(message_id, poll_id)
# # stop_poll(message_id)
# print(get_last_poll_results("1435"))
# print(get_last_poll_results("5892961168976248845"))
# print(get_last_poll("5892961168976248845"))

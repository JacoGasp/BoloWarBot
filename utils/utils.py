import yaml
import os
import logging.config

token = os.environ["API_TOKEN"]
chat_id = os.environ["CHAT_ID"]

with open("config/logging.yaml", "rt") as f:
    logging_config = yaml.safe_load(f)
    logging.config.dictConfig(logging_config)


def load_messages(language):
    with open("config/messages.yaml") as stream:
        return yaml.load(stream, Loader=yaml.FullLoader)[language]


def load_configs():
    with open("config/config.yaml") as stream:
        return yaml.load(stream, Loader=yaml.FullLoader)


config = load_configs()
messages = load_messages(config["language"])

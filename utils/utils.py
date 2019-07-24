import yaml


def load_messages(language):
    with open("config/messages.yaml") as stream:
        return yaml.load(stream, Loader=yaml.FullLoader)[language]
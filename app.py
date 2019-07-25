import os
from reign import Reign
import argparse
from telegram.ext import Updater
from utils.utils import messages, config, token
from utils.telegram_handler import TelegramHandler
import schedule
import logging
import logging.config
import yaml
import pandas as pd
from time import sleep

with open("config/logging.yaml", "rt") as f:
    logging_config = yaml.safe_load(f)
    logging.config.dictConfig(logging_config)

reign_logger = logging.getLogger("Reign")
app_logger = logging.getLogger("App")
reign_logger.addHandler(TelegramHandler())


FLAGS = None
PLAY = True
battle_round = 1


def play_turn(reign):
    global battle_round, PLAY
    app_logger.info(f"Round {battle_round}")
    reign.battle()
    battle_round += 1
    if reign.remaing_territories == 1:
        PLAY = False


def __main__():
    app_logger.info("Start BoloWartBot")

    # Start the Telegram updater
    updater = Updater(token=token)
    dispatcher = updater.dispatcher

    # Load the data
    df = pd.read_pickle(config["db"]["path"])
    reign = Reign(df, should_display_map=FLAGS.map, telegram_dispatcher=dispatcher)

    # Schedule the turns
    schedule.every(config["schedule"]["minutes_per_round"]).minutes.do(play_turn, reign)

    # Start the battle
    reign_logger.info(messages["start"])

    while PLAY:
        schedule.run_pending()
        sleep(1)

    # End of the war
    the_winner = df.groupby("Empire").count().query("color > 1").iloc[0].name
    reign_logger.info(messages["the_winner_is"] % the_winner)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", "-m", action="store_true", help="If present, display the map")
    parser.add_argument("--sleep", "-s", type=int, default=0, help="Time in seconds to wait between each round")
    FLAGS = parser.parse_args()
    __main__()

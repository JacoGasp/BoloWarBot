import argparse
import threading
import signal
import os
import traceback
import logging
import json

import schedule
from time import sleep

import pandas as pd
from reign import Reign
from utils import utils
from utils.functions import get_sig_dict, read_stats
from utils.telegram_handler import TelegramHandler
from utils.cache_handler import MsgCacheHandler

messages, config, token, chat_id = utils.messages, utils.config, utils.token, utils.chat_id

reign_logger = logging.getLogger("Reign")
app_logger = logging.getLogger("App")

# ---------------------------------------- #
# Global Variables

sig_dict = {}
telegram_handler = None

FLAGS = None
PLAY = True
reign = None
stats = None


# ---------------------------------------- #

def exit_app(signum, _):
    app_logger.debug("Terminating with signal %s", sig_dict[signum])
    global PLAY
    PLAY = False
    app_logger.info("Closing the BoloWarBot")
    save_temp()
    for job in schedule.jobs:
        schedule.cancel_job(job)


def save_temp():
    if reign.obj is not None:
        if not os.path.exists(config["saving"]["dir"]):
            os.makedirs(config["saving"]["dir"])

    df_path = os.path.join(config["saving"]["dir"], config["saving"]["db"])
    stats_path = os.path.join(config["saving"]["dir"], config["saving"]["stats"])
    try:
        if stats is not None:
            with open(stats_path, "w") as f:
                json.dump(stats, f)
                app_logger.debug('Stats saved to "%s"' % stats_path)
    except (FileNotFoundError, OSError, Exception):
        app_logger.error("Cannot save statistics to disk")

    try:
        pd.to_pickle(reign.obj, df_path)
        app_logger.debug('Dataframe saved to "%s"' % df_path)
    except (FileNotFoundError, OSError):
        app_logger.error("Cannot save state to pickle")


def init_reign():
    global reign
    df = None
    file_path = os.path.join(config["saving"]["dir"], config["saving"]["db"])
    try:
        df = pd.read_pickle(file_path)
        app_logger.info("Saved state successfully loaded")

    except (FileNotFoundError, OSError):
        df = pd.read_pickle(config["db"]["path"])
        app_logger.info("Saved state file not found. Initializing new game")

    finally:
        if df is not None:
            reign = Reign(df, should_display_map=FLAGS.map)
            app_logger.debug("Alive empires: %d" % reign.remaing_territories)
        else:
            raise RuntimeError("Cannot initialize geopandas dataframe")


def play_turn():
    global stats, PLAY

    if stats is not None:
        stats["battle_round"] = reign.battle_round

    app_logger.info(f"Round {reign.battle_round}")
    try:
        reign.battle()

    except Exception:
        error_message = traceback.format_exc()
        app_logger.error(error_message)
        telegram_handler.bot.send_message(chat_id=config["telegram"]["chat_id_logging"], text=error_message)

    if reign.remaing_territories == 1:
        PLAY = False

    # Save the partial battle state
    save_temp()


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()


def __main__():

    # ---------------------------------------- #
    # Load the data. Try to restore previously partial dataframe.

    init_reign()
    global stats
    stats = read_stats(os.path.join(config["saving"]["dir"], config["saving"]["stats"]), app_logger)

    # ---------------------------------------- #
    # Init data handlers

    global telegram_handler

    telegram_handler = TelegramHandler(token=token, chat_id=chat_id)
    msg_cache_handler = MsgCacheHandler()

    reign.telegram_handler = telegram_handler
    telegram_handler.msg_cache_handler = msg_cache_handler

    telegram_handler.send_cached_data()

    try:
        reign.battle_round = stats["battle_round"] #+ 1
    except TypeError:
        stats = dict()
        stats["battle_round"] = 1
        # Send Start message
        reign_logger.info(messages["start"])
        telegram_handler.send_message(messages["start"])

    # ---------------------------------------- #
    # Schedule the turns

    schedule.every(config["schedule"]["minutes_per_round"]).seconds.do(run_threaded, play_turn)

    # ---------------------------------------- #
    # Start the battle

    while PLAY:
        schedule.run_pending()
        sleep(1)

    # ---------------------------------------- #
    # End of the war
    if reign.remaing_territories == 1:
        the_winner = reign.obj.groupby("Empire").count().query("color > 1").iloc[0].name
        message = messages["the_winner_is"] % the_winner
        telegram_handler.send_message(message)
        reign_logger.info(message)


if __name__ == "__main__":

    app_logger.info("Start BoloWartBot")
    # ---------------------------------------- #
    # Parse arguments

    parser = argparse.ArgumentParser()
    parser.add_argument("--map", "-m", action="store_true", help="If present, display the map")
    FLAGS = parser.parse_args()

    # ---------------------------------------- #
    # Register exit handler

    sig_dict = get_sig_dict()
    signal.signal(signal.SIGINT, exit_app)
    signal.signal(signal.SIGTERM, exit_app)

    # ---------------------------------------- #
    # App
    __main__()

    app_logger.info("Bye bye.")

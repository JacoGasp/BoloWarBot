import argparse
import threading
import signal
import os
import traceback
import logging

import schedule
from time import sleep

import pandas as pd
from reign import Reign
from utils import utils
from utils.functions import get_sig_dict
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
battle_round = 1
reign = None


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
    output_path = os.path.join(config["saving"]["dir"], config["saving"]["db"])
    pd.to_pickle(reign.obj, output_path)
    app_logger.debug('Dataframe saved to "%s"' % output_path)


def play_turn():
    global battle_round, PLAY
    app_logger.info(f"Round {battle_round}")
    try:
        reign.battle()
        battle_round += 1
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

    stored_df_path = os.path.join(config["saving"]["dir"], config["saving"]["db"])
    if os.path.exists(stored_df_path):
        df = pd.read_pickle(stored_df_path)
        app_logger.debug("Dataframe restored from disk.")
    else:
        df = pd.read_pickle(config["db"]["path"])
        reign_logger.info(messages["start"])
        # telegram_handler.bot.send_message()
    global reign

    # ---------------------------------------- #
    # Init data handlers

    global telegram_handler
    reign = Reign(df, should_display_map=FLAGS.map)
    app_logger.debug("Alive empires: %d" % reign.remaing_territories)

    telegram_handler = TelegramHandler(token=token, chat_id=chat_id)
    msg_cache_handler = MsgCacheHandler()

    reign.telegram_handler = telegram_handler
    telegram_handler.msg_cache_handler = msg_cache_handler

    telegram_handler.send_cached_data()

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
        the_winner = df.groupby("Empire").count().query("color > 1").iloc[0].name
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

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
from telegram.ext import Updater

messages, config, token = utils.messages, utils.config, utils.token

reign_logger = logging.getLogger("Reign")
app_logger = logging.getLogger("App")
reign_logger.addHandler(TelegramHandler())

# ---------------------------------------- #
# Global Variables

sig_dict = {}
dispatcher = None
bot = None
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
    app_logger.info("Bye bye.")


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
        bot.send_message(chat_id=config["telegram"]["chat_id_logging"], text=error_message)

    if reign.remaing_territories == 1:
        PLAY = False

    # Save the partial battle state
    save_temp()


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()


def __main__():

    # ---------------------------------------- #
    # Start the Telegram updater

    updater = Updater(token=token)
    global dispatcher
    dispatcher = updater.dispatcher
    global bot
    bot = dispatcher.bot

    # ---------------------------------------- #
    # Load the data. Try to restore previously partial dataframe.

    stored_df_path = os.path.join(config["saving"]["dir"], config["saving"]["db"])
    if os.path.exists(stored_df_path):
        df = pd.read_pickle(stored_df_path)
        app_logger.debug("Dataframe restored from disk.")
    else:
        df = pd.read_pickle(config["db"]["path"])
        reign_logger.info(messages["start"])
    global reign

    reign = Reign(df, should_display_map=FLAGS.map, telegram_dispatcher=dispatcher)
    app_logger.debug("Alive empires: %d" % reign.remaing_territories)

    # ---------------------------------------- #
    # Schedule the turns

    schedule.every(config["schedule"]["minutes_per_round"]).minutes.do(run_threaded, play_turn)

    # ---------------------------------------- #
    # Start the battle

    while PLAY:
        schedule.run_pending()
        sleep(1)

    # ---------------------------------------- #
    # End of the war
    if reign.remaing_territories == 1:
        the_winner = df.groupby("Empire").count().query("color > 1").iloc[0].name
        reign_logger.info(messages["the_winner_is"] % the_winner)


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

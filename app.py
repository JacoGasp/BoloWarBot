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
from utils.functions import get_sig_dict, read_saved_turn
from utils.telegram_handler import TelegramHandler
from utils.cache_handler import MsgCacheHandler
from utils.stats_handler import StatsHandler
from utils.utils import messages, config, schedule_config, token, chat_id

reign_logger = logging.getLogger("Reign")
app_logger = logging.getLogger("App")

# ---------------------------------------- #
# Global Variables

sig_dict = {}
telegram_handler = None

FLAGS = None
PLAY = False
reign = None
saved_turn = None


# ---------------------------------------- #

def cancel_jobs():
    for job in schedule.jobs:
        schedule.cancel_job(job)


def start_main_job():
    for round_time in schedule_config["rounds_at_time"]:
        if config["distribution"] == "production":
            schedule.every().day.at(round_time).do(run_threaded, play_turn).tag("main_job")
        elif config["distribution"] == "develop":
            schedule.every().minute.at(round_time).do(run_threaded, play_turn).tag("main_job")

    next_run = schedule.next_run().strftime("%Y-%m-%d %H:%M:%S")
    app_logger.info("The Battle continues. Next turn will be at %s", next_run)


def cancel_main_job():
    schedule.clear("main_job")
    app_logger.info("Main job canceled.")
    for job in schedule.jobs:
        if "start_job" in job.tags:
            app_logger.info("The battle will continue on %s", job.next_run.strftime("%Y-%m-%d %H:%M:%S"))


def exit_app(signum, _):
    app_logger.debug("Terminating with signal %s", sig_dict[signum])
    global PLAY
    PLAY = False
    app_logger.info("Closing the BoloWarBot")
    save_temp()
    cancel_jobs()


def save_temp():
    if reign.obj is not None:
        if not os.path.exists(config["saving"]["dir"]):
            os.makedirs(config["saving"]["dir"])

    df_path = os.path.join(config["saving"]["dir"], config["saving"]["db"])
    saved_turn_path = os.path.join(config["saving"]["dir"], config["saving"]["saved_turn"])
    try:
        if saved_turn is not None:
            with open(saved_turn_path, "w") as f:
                json.dump(saved_turn, f)
                app_logger.debug('saved_turn saved to "%s"' % saved_turn_path)
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
    threshold = config["balance"]["threshold"]
    low_b = config["balance"]["low_b"]
    try:
        df = pd.read_pickle(file_path)
        app_logger.info("Saved state successfully loaded")

    except (FileNotFoundError, OSError):
        df = pd.read_pickle(config["db"]["path"])
        app_logger.info("Saved state file not found. Initializing new game")

    finally:
        if df is not None:
            reign = Reign(df, threshold, low_b, should_display_map=FLAGS.map)
            app_logger.debug("Alive empires: %d" % reign.remaing_territories)
        else:
            raise RuntimeError("Cannot initialize geopandas dataframe")


def play_turn():
    global saved_turn, PLAY

    # Send cached message
    if telegram_handler is not None:
        telegram_handler.send_cached_data()

    if saved_turn is not None:
        saved_turn["battle_round"] = reign.battle_round

    app_logger.info(f"Round {reign.battle_round}")

    try:
        reign.battle()

    except Exception:
        error_message = traceback.format_exc()
        app_logger.error(error_message)
        telegram_handler.bot.send_message(chat_id=config["telegram"]["chat_id_logging"], text=error_message)

    if reign.remaing_territories == 0:
        PLAY = False

    # Save the partial battle state
    save_temp()

    next_run = schedule.next_run().strftime("%Y-%m-%d %H:%M:%S")
    app_logger.info("Next turn will be at %s", next_run)


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()


def __main__():

    # ---------------------------------------- #
    # Load the data. Try to restore previously partial dataframe.

    init_reign()
    global saved_turn
    saved_turn = read_saved_turn(os.path.join(config["saving"]["dir"], config["saving"]["saved_turn"]), app_logger)

    # ---------------------------------------- #
    # Init data handlers

    global telegram_handler

    telegram_handler = TelegramHandler(token=token, chat_id=chat_id)
    msg_cache_handler = MsgCacheHandler()
    stats_handler = StatsHandler(file_path=os.path.join(config["saving"]["dir"], config["saving"]["stats"]))

    reign.telegram_handler = telegram_handler
    telegram_handler.msg_cache_handler = msg_cache_handler
    telegram_handler.stats_handler = stats_handler

    try:
        reign.battle_round = saved_turn["battle_round"] + 1
    except TypeError:
        saved_turn = dict()
        saved_turn["battle_round"] = 1
        # Send Start message
        reign_logger.info(messages["start"])
        telegram_handler.send_message(messages["start"])

    # ---------------------------------------- #
    # Schedule the turns

    if reign.remaing_territories > 1:
        global PLAY
        PLAY = True
        schedule.every().day.at(schedule_config["start_time"]).do(start_main_job).tag("start_job")
        schedule.every().day.at(schedule_config["stop_time"]).do(cancel_main_job).tag("stop_job")
        start_main_job()

    else:
        app_logger.warning("The war is over")

    # ---------------------------------------- #
    # Start the battle

    while PLAY:
        schedule.run_pending()
        sleep(1)

    # ---------------------------------------- #
    # End of the war

    if reign.remaing_territories <= 1:
        cancel_jobs()
        the_winner = reign.obj.groupby("Empire").count().query("color > 1").iloc[0].name
        message = messages["the_winner_is"] % the_winner
        telegram_handler.send_message(message)
        reign_logger.info(message)



if __name__ == "__main__":

    app_logger.info("Start BoloWartBot")
    app_logger.debug("Distribution: %s", config["distribution"])
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

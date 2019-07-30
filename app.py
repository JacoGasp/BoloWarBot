import threading

from reign import Reign
import argparse
from telegram.ext import Updater
from utils import utils
from utils.telegram_handler import TelegramHandler
import schedule
import logging
import pandas as pd
from time import sleep
import traceback
import os

messages, config, token = utils.messages, utils.config, utils.token

reign_logger = logging.getLogger("Reign")
app_logger = logging.getLogger("App")
reign_logger.addHandler(TelegramHandler())

dispatcher = None
bot = None
FLAGS = None
PLAY = True
battle_round = 1
reign = None


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

    # Start the Telegram updater
    updater = Updater(token=token)
    global dispatcher
    dispatcher = updater.dispatcher
    global bot
    bot = dispatcher.bot

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

    # Schedule the turns
    schedule.every(config["schedule"]["minutes_per_round"]).minutes.do(run_threaded, play_turn)

    # Start the battle
    while PLAY:
        schedule.run_pending()
        sleep(1)

    # End of the war
    the_winner = df.groupby("Empire").count().query("color > 1").iloc[0].name
    reign_logger.info(messages["the_winner_is"] % the_winner)


if __name__ == "__main__":

    app_logger.info("Start BoloWartBot")

    parser = argparse.ArgumentParser()
    parser.add_argument("--map", "-m", action="store_true", help="If present, display the map")
    parser.add_argument("--sleep", "-s", type=int, default=0, help="Time in seconds to wait between each round")
    FLAGS = parser.parse_args()

    try:
        __main__()
    except KeyboardInterrupt:
        app_logger.info("Closing the BoloWarBot")
    finally:
        if PLAY:
            PLAY = False

            # Save the partial battle state
            save_temp()

        app_logger.info("Bye bye.")

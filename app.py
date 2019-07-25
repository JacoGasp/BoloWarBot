import os, sys
from reign import Reign
import argparse
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from utils import utils
from utils.telegram_handler import TelegramHandler
import schedule
import logging
import pandas as pd
from time import sleep

messages, config, token = utils.messages, utils.config, utils.token

reign_logger = logging.getLogger("Reign")
app_logger = logging.getLogger("App")
reign_logger.addHandler(TelegramHandler())

dispatcher = None
FLAGS = None
PLAY = True
battle_round = 1


def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=update.message.text)


def hello(bot, update):
    print(update.message.chat_id)
    bot.send_message(chat_id=update.message.chat_id, text="Ciao")


def send_error_to_telegram_user(chat_id, text):
    dispatcher.bot.send_message(chat_id=chat_id, text=text)


def save_temp():
    pass


def play_turn(reign):
    global battle_round, PLAY
    app_logger.info(f"Round {battle_round}")
    try:
        reign.battle()
        battle_round += 1
    except Exception as e:
        exc_type, _, _ = sys.exc_info()

        text = "Something went wrong with error: %s at line %d of file %s" % (e, line, fname)
        app_logger.error(text)
        send_error_to_telegram_user(chat_id=config["telegram"]["chat_id_logging"], text=text)

    if reign.remaing_territories == 1:
        PLAY = False


def __main__():
    app_logger.info("Start BoloWartBot")

    # Start the Telegram updater
    updater = Updater(token=token)
    global dispatcher
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", hello))
    updater.start_polling()

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

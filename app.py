import os
from Territory import *
import argparse
from telegram.ext import Updater
from utils.utils import messages, config
from utils.telegram_handler import TelegramHandler
import schedule


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

reign_logger = logging.getLogger("Reign")
reign_logger.addHandler(TelegramHandler())
reign_logger.setLevel("INFO")

app_logger = logging.getLogger("App")
app_logger.setLevel("INFO")

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
    updater = Updater(token=os.environ["API_TOKEN"])
    dispatcher = updater.dispatcher

    # Load the data
    df = pd.read_pickle(config["db"]["path"])
    reign = Reign(df, should_display_map=FLAGS.map, telegram_dispatcher=dispatcher)

    # Schedule the turns
    schedule.every(5).minutes.do(play_turn, reign)

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

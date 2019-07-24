import os
from Territory import *
import argparse
from telegram.ext import Updater
from utils.utils import load_messages
from telegram_handler import TelegramHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

reign_logger = logging.getLogger("Reign")
reign_logger.addHandler(TelegramHandler())
reign_logger.setLevel("INFO")

app_logger = logging.getLogger("App")
app_logger.setLevel("INFO")

FLAGS = None

messages = load_messages("it")


def __main__():
    app_logger.info("Start BoloWartBot")

    updater = Updater(token=os.environ["API_TOKEN"])
    dispatcher = updater.dispatcher

    reign_logger.info(messages["start"])

    df = pd.read_pickle("bologna.pickle")
    reign = Reign(df, should_display_map=FLAGS.map, telegram_dispatcher=dispatcher)

    battle_round = 1

    while reign.remaing_territories > 1:
        app_logger.info(f"Round {battle_round}")
        reign.battle()

        battle_round += 1
        if "sleep" in FLAGS:
            sleep(FLAGS.sleep)

    the_winner = df.groupby("Empire").count().query("color > 1").iloc[0].name
    reign_logger.info(messages["the_winner_is"] % the_winner)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", "-m", action="store_true", help="If present, display the map")
    parser.add_argument("--sleep", "-s", type=int, default=0, help="Time in seconds to wait between each round")
    FLAGS = parser.parse_args()
    __main__()

from time import sleep
from Territory import *
import argparse

logger = logging.getLogger("Reign")
logger.setLevel("DEBUG")

FLAGS = None


def __main__():
    df = pd.read_pickle("bologna.pickle")

    reign = Reign(df, should_display_map=FLAGS.map)

    battle_round = 1
    while reign.remaing_territories > 1:
        print("Round", battle_round)
        reign.battle()

        battle_round += 1
        if "sleep" in FLAGS:
            sleep(FLAGS.sleep)

    the_winner = df.groupby("Empire").count().query("color > 1").iloc[0].name
    print(f"🏆🏆🏆 {the_winner} WON THE WAR!!! 🏆🏆🏆")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", "-m", action="store_true", help="If present, display the map")
    parser.add_argument("--sleep", "-s", type=int, default=0, help="Time in seconds to wait between each round")
    FLAGS = parser.parse_args()
    __main__()

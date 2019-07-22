from Territory import *

logger = logging.getLogger("Reign")
logger.setLevel("DEBUG")

df = pd.read_pickle("bologna.pickle")

reign = Reign(df)

battle_round = 1
while reign.remaing_territories > 1:
    print("Round", battle_round)
    reign.battle()

    battle_round += 1
    # sleep(1)

the_winner = df.groupby("Empire").count().query("color > 1").iloc[0].name
print(f"🏆🏆🏆 {the_winner} WON THE WAR!!! 🏆🏆🏆")

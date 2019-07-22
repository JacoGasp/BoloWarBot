from Territory import *

logger = logging.getLogger("Reign")
logger.setLevel("DEBUG")

df = pd.read_pickle("bologna.pickle")
df["empire_geometry"] = df.geometry
df["empire_neighbours"] = df.neighbours
df["empire_color"] = df.color

df = df.rename(columns={"COMUNE": "Territory"})
df["Empire"] = df.Territory
df.set_index("Territory", drop=True, inplace=True)

reign = Reign(df)

battle_round = 1
while reign.remaing_territories > 1:
    print("Round", battle_round)
    reign.battle()

    battle_round += 1
    # sleep(1)

the_winner = df.groupby("Empire").count().query("color > 1").iloc[0].name
print(f"🏆🏆🏆 {the_winner} WON THE WAR!!! 🏆🏆🏆")

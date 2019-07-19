import pandas as pd
from random import choice, seed
from time import sleep
from descartes import PolygonPatch
from matplotlib.collections import PatchCollection
import logging
from Territory import *
import matplotlib.pyplot as plt
from functools import reduce


logger = logging.getLogger("Reign")
logger.setLevel("DEBUG")

df = pd.read_pickle("bologna.pickle")
df["empire_geometry"] = df.geometry
df["empire_neighbours"] = df.neighbours
df = df.rename(columns={"COMUNE": "Territory"})
df["Empire"] = df.Territory
df.set_index("Territory", drop=True, inplace=True)

reign = Reign(df)

while reign.remaing_territories > 1:
    reign.battle()

    # sleep(1)

the_winner = df.groupby("Empire").count().query("color > 1").iloc[0].name
print(f"🏆🏆🏆 {the_winner} WON THE WAR!!! 🏆🏆🏆")

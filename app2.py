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

reign = Reign(df)
reign.obj["extended_geometry"] = reign.obj.geometry
reign.obj["SOVRANO"] = reign.obj.COMUNE
reign.obj.set_index("COMUNE", drop=True, inplace=True)

reign.find_neighbors()

while reign.remaing_territories > 1:
    reign.battle()
    # sleep(1)

the_winner = df.groupby("SOVRANO").count().query("color > 1").iloc[0].name
print(f"🏆🏆🏆 {the_winner} WON THE WAR!!! 🏆🏆🏆")

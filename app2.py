import pandas as pd
from random import choice, seed
from time import sleep
from descartes import PolygonPatch
from matplotlib.collections import PatchCollection

from Territory import *
import matplotlib.pyplot as plt
from functools import reduce

df = pd.read_pickle("bologna.pickle")


reign = Reign(df)
reign.obj["extended_geometry"] = reign.obj.geometry
#reign.obj["SOVRANO"] = reign.obj.geometry
index = pd.MultiIndex.from_arrays([reign.obj.COMUNE, reign.obj.COMUNE], names=["SOVRANO", "COMUNE"])

reign.obj.index = index
reign.obj.drop(columns=["COMUNE"], inplace=True)
reign.find_neighbors()


while len(reign.obj) > 1:
    reign.battle()
    # sleep(1)

print(f"🏆🏆🏆 {reign.obj.iloc[0].COMUNE.upper()} WON THE WAR!!! 🏆🏆🏆")

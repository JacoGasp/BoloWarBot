import pandas as pd
from random import choice, seed
from time import sleep
from descartes import PolygonPatch
from matplotlib.collections import PatchCollection

from Territory import *
import matplotlib.pyplot as plt
from functools import reduce

df = pd.read_pickle("bologna.pickle")


df = Reign(df)
df.find_neighbors()



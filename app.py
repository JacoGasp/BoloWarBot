import pandas as pd
from random import choice, seed
from time import sleep
from descartes import PolygonPatch
from matplotlib.collections import PatchCollection

from Reign import *
import matplotlib.pyplot as plt
from functools import reduce

df = pd.read_pickle("bologna.pickle")

reigns = {k.lower(): Reign(k, df[df.COMUNE == k]) for k in df.COMUNE.values}


def better_name(name):
    words = name.split()
    words = ["S." if x == "San" else x for x in words]
    if len(words) >= 4:
        return " ".join(words[:2]) + "\n" + " ".join(words[2:])
    else:
        return words[0] + "\n" + " ".join(words[1:])


def plot_world():
    _, ax = plt.subplots(figsize=(8, 8))
    patches = []

    for reign in reigns.values():

        color = reign.df.iloc[0].color

        if len(reign.df) > 1:
            reign.df.apply(
                lambda x: patches.append(PolygonPatch(x.geometry, alpha=0.75, fc=color, ec="#555555", ls=(0, (10, 5)))),
                axis=1)
        else:
            reign.df.apply(lambda x: patches.append(PolygonPatch(x.geometry, alpha=0.75, fc=color, ec="#555555", lw=2)),
                           axis=1)

        reign_border = reduce(lambda x, y: x.union(y), reign.df.geometry)
        new_center = reign_border.centroid.coords[0]
        patches.append(PolygonPatch(reign_border, fill=False, ec="#555555"))

        ax.annotate(s=better_name(reign.name), xy=new_center, ha='center', fontsize=8)

    ax.add_collection(PatchCollection(patches, match_original=True))
    ax.set_aspect(1)
    ax.axis('off')
    ax.grid(False)
    plt.axis('equal')
    plt.tight_layout()
    plt.show()


plot_world()


def battle():
    while len(reigns) > 1:

        reign: Reign = choice(list(reigns.values()))

        neighbours = reign.get_neighbours()
        neighbours = list(filter(lambda x: x.lower() in list(reigns.keys()), neighbours))
        if len(neighbours) > 1:
            enemy_name = choice(neighbours)
            enemy = reigns[enemy_name.lower()]

            if reign.attack(enemy):
                plot_world()
                del reigns[enemy_name.lower()]
                print(f"Remaining reigns: {len(reigns)}")

        sleep(2)




battle()

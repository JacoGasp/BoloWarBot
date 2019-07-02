import geopandas as gp
import pandas as pd
import random


class Territory(gp.GeoSeries):
    @property
    def _constructor(self):
        return Territory

    @property
    def _constructor_sliced(self):
        return Territory

    @staticmethod
    def attack():
        return random.random()

    @staticmethod
    def defend():
        return random.random()


class Reign(gp.GeoDataFrame):

    @property
    def _constructor(self):
        return Reign

    @property
    def _constructor_sliced(self):
        return Reign

    def find_neighbors(self):
        neighbours = []
        for i, territory in self.iterrows():
            n = self[~self.geometry.disjoint(territory.geometry)].COMUNE.tolist()
            neighbours.append([name for name in n if territory.COMUNE != name])
        self["neighbours"] = neighbours

    def battle(self):
        attacker: Territory = self.sample(1)[0]
        defender: Territory = self[random.choice(attacker.neighbours)]

        if attacker.attack() > defender.defend():
            self.drop(index=defender.index)
            self.iloc[attacker.index].geometry = self.iloc[attacker.index].geometry.union(defender.geometry)
            print(f"{attacker.COMUNE} won")
            self.find_neighbors()
        else:
            print(f"{defender.COMUNE} resisted")
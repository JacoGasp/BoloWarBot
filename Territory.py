import pandas as pd
import random


class Territory(pd.Series):
    @property
    def _constructor(self):
        return Territory

    @property
    def _constructor_expanddim(self):
        return Territory

    @property
    def SOVRANO(self):
        return self.name[0]

    @property
    def COMUNE(self):
        return self.name[1]

    @staticmethod
    def attack():
        return random.random()

    @staticmethod
    def defend():
        return random.random()


@pd.api.extensions.register_dataframe_accessor('reign')
class Reign(object):

    def __init__(self, pandas_obj):
        self.obj = pandas_obj
        # self.find_neighbors(pandas_obj)

    @property
    def SOVRANI(self):
        return self.obj.index.get_level_values(0).tolist()

    @property
    def COMUNI(self):
        return self.obj.index.get_level_values(1).tolist()

    def find_neighbors(self):
        neighbours = []
        for i, territory in self.obj.iterrows():
            territory = Territory(territory)
            n = self.obj[~self.obj.geometry.disjoint(territory.geometry)].reign.SOVRANI
            neighbours.append([name for name in n if territory.name[0] != name])
        self.obj["extended_neighbours"] = neighbours

    def battle(self):
        attacker = Territory(self.obj.sample(1).iloc[0])
        defender = Territory(self.obj.loc[random.choice(attacker.extended_neighbours)])

        print(f"{attacker.COMUNE} is attacking {defender.COMUNE}... ⚔️")

        if attacker.attack() > defender.defend():

            self.obj.drop(defender.COMUNE, inplace=True)
            self.obj.loc[attacker.COMUNE].geometry = self.obj.loc[attacker.COMUNE].geometry.union(defender.geometry)
            print(f"{attacker.COMUNE} conquered {defender.COMUNE} 🗡")
            print(f"{len(self.obj)} remaining territories.\n")
            self.find_neighbors()
        else:
            print(f"{defender.COMUNE} resisted to the attack of {attacker.COMUNE} 🛡\n")

    @staticmethod
    def attack():
        return random.random()

    @staticmethod
    def defend():
        return random.random()

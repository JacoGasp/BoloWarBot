import pandas as pd
import random
from geopandas import GeoDataFrame
import logging

logging.basicConfig()
logger = logging.getLogger("Reign")


class Territory(pd.Series):
    @property
    def _constructor(self):
        return Territory

    @property
    def _constructor_expanddim(self):
        return Territory

    @property
    def COMUNE(self):
        return self.name

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
        self.remaing_territories = len(self.obj)
        # self.find_neighbors(pandas_obj)

    def find_neighbors(self):
        neighbours = []
        for i, territory in self.obj.iterrows():
            n = self.obj[~self.obj.geometry.disjoint(territory.extended_geometry)].SOVRANO.tolist()
            neighbours.append([name for name in n if territory.name != name])
        self.obj["extended_neighbours"] = neighbours

    def _extend_geometry(self, attacker, defender):
        new_geometry = self.obj[self.obj.SOVRANO == attacker.SOVRANO].loc[attacker.COMUNE].extended_geometry
        logger.debug(f"Old geometry area: {new_geometry.area}")
        new_geometry = new_geometry.union(self.obj.loc[defender.COMUNE].geometry)
        logging.debug(f"new geometry area: {new_geometry.area}")
        self.obj[self.obj.SOVRANO == attacker.SOVRANO].loc[attacker.COMUNE].extended_geometry = new_geometry

    def _reduce_geometry(self, defender):
        new_geometry = self.obj[self.obj.SOVRANO == defender.SOVRANO].loc[defender.COMUNE].extended_geometry
        new_geometry = new_geometry.difference(defender.geometry)
        self.obj[self.obj.SOVRANO == defender.SOVRANO].loc[defender.COMUNE].extended_geometry = new_geometry

    def battle(self):
        attacker = Territory(self.obj.sample(1).iloc[0])
        defender = Territory(self.obj.loc[random.choice(attacker.extended_neighbours)])

        print(
            f"{attacker.COMUNE}, of the {attacker.SOVRANO}'s reign, is attacking {defender.COMUNE} of the {defender.SOVRANO}'s reign... ⚔️")

        if attacker.attack() > defender.defend():
            print(f"{attacker.COMUNE} conquered {defender.COMUNE} 🗡")
            """The sovereign of the attacker must include the defender geometry, and the defender becomes owned by the
            attacker's sovereign"""

            self._extend_geometry(attacker, defender)

            if len(self.obj[self.obj.SOVRANO == defender.SOVRANO]) is GeoDataFrame:
                self._reduce_geometry(defender)
                self.obj.loc[defender.COMUNE].SOVRANO = attacker.SOVRANO
                print()

            else:
                self.remaing_territories -= 1
                print(f"{defender.SOVRANO} has been defeated. ✝️")
                print(f"{self.remaing_territories} remaining territories.\n")

            self.find_neighbors()
        else:
            print(f"{defender.COMUNE} resisted to the attack of {attacker.COMUNE} 🛡\n")

    @staticmethod
    def attack():
        return random.random()

    @staticmethod
    def defend():
        return random.random()

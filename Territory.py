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
    def Territory(self):
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
        self.alive_empires = list(pandas_obj.index.values)
        # self.find_neighbors(pandas_obj)

    def update_empire_neighbours(self):
        neighbours = []
        for i, territory in self.obj.iterrows():
            n = self.obj[~self.obj.geometry.disjoint(territory.empire_geometry)].Empire.tolist()
            neighbours.append([name for name in n if territory.Empire != name])
        self.obj["empire_neighbours"] = neighbours

    def __expand_empire_geometry(self, attacker, defender):
        old_geometry = self.obj.query(f'Empire == "{attacker.Empire}"').loc[attacker.Territory].empire_geometry
        new_geometry = old_geometry.union(defender.geometry)
        empire_territories_index = self.obj.query(f'Empire == "{attacker.Empire}"').index
        self.obj.loc[empire_territories_index].empire_geometry = new_geometry

    def __reduce_empire_geometry(self, defender):
        old_geometry = self.obj.query(f'Empire == "{defender.Empire}"').loc[defender.Territory].empire_geometry
        new_geometry = old_geometry.difference(defender.geometry)

        empire_terriories_index = self.obj.query(f'Empire == "{defender.Empire}"').index
        self.obj.loc[empire_terriories_index].empire_geometry = new_geometry

    def __get_alive_empires(self):
        empires = self.obj.Empire.unique()
        return list(empires)

    def battle(self):
        """
        - Choose a random Empire ∑ (attacker reign)
        - Choose a random Territory from ∑'s neighbours => defender
        - defender's Empire Ω = Territory.sovereign
        - intersection(Ω's territory neighbours, ∑) => attackers
        - random(attackers) => Territory attacker (of ∑)
        - attacker vs defender
        - if attack > defense:
            if len(Ω) > 1:
                remove defender geometry from Ω geometry

            else:
                defender.empire defeated
                remaining_territories => len(Empires with more than one Territory)

            Do always:
            expand ∑ geometry including the defender geometry
            attacker.empire => defender.empire
            recompute neighbours of empires
         else:
            defender, of Ω, resisted
        """

        # Choose ∑
        empire = random.choice(self.__get_alive_empires())
        empire_neighbours = self.obj.query(f'Empire == "{empire}"').iloc[0].empire_neighbours

        # Choose the defender Territory among the empire's neighbours
        defender = random.choice(empire_neighbours)
        defender = Territory(self.obj.loc[defender])

        # Find the attackers as the intersection between ∑'s all territories and Ω's neighbours
        attacker_territories = self.obj.query(f'Empire == "{empire}"').index.values
        attackers = list(set(attacker_territories) & set(defender.neighbours))

        assert len(attackers) > 0, f"{defender} {attacker_territories}"

        # Pick a random attacker Territory from Territories at the border
        attacker = random.choice(attackers)
        attacker = Territory(self.obj.loc[attacker])

        print(
            f"{attacker.Territory}, of the {attacker.Empire}'s reign, is attacking {defender.Territory} of the {defender.Empire}'s reign... ⚔️")

        if attacker.attack() > defender.defend():
            print(f"{attacker.Territory} conquered {defender.Territory} 🗡")

            if len(self.obj.query(f'Empire == "{defender.Empire}"')) > 1:
                self.__reduce_empire_geometry(defender)
                print()

            else:
                self.remaing_territories = len(self.__get_alive_empires()) - 1
                print(f"{defender.Empire} has been defeated. ✝️")
                print(f"{self.remaing_territories} remaining territories.\n")

            self.__expand_empire_geometry(attacker, defender)
            self.obj.loc[defender.Territory].Empire = attacker.Empire  # Change the defender's Empire to the attacker one

            self.update_empire_neighbours()

        else:
            print(f"{defender.Territory} resisted to the attack of {attacker.Territory} 🛡\n")

    @staticmethod
    def attack():
        return random.random()

    @staticmethod
    def defend():
        return random.random()

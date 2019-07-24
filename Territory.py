from time import sleep
from telegram.ext import Dispatcher
from telegram import InputFile
import pandas as pd
import random
import logging
import matplotlib.pyplot as plt
from descartes import PolygonPatch
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
from utils.utils import load_messages

logger = logging.getLogger("Reign")
messages = load_messages("it")


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

    def __init__(self, pandas_obj, should_display_map=False, telegram_dispatcher: Dispatcher = None, language="it"):
        self.obj = pandas_obj
        self.remaing_territories = len(self.obj)
        self.alive_empires = list(pandas_obj.index.values)
        self.should_display_map = should_display_map
        self.telegram_dispatcher = telegram_dispatcher
        random.seed(1)

    def __update_empire_neighbours(self, empire):
        empire_df = self.obj.query(f'Empire == "{empire}"')
        territories_neighbours = empire_df.neighbours.values.tolist()
        territories_neighbours = list(set([item for sublist in territories_neighbours for item in sublist]))

        empire_idx = empire_df.index
        empire_territories = empire_idx.values.tolist()
        empire_neighbours = list(filter(lambda x: x not in empire_territories, territories_neighbours))

        self.obj.loc[empire_idx, "empire_neighbours"] = [empire_neighbours] * len(empire_idx)

    def __expand_empire_geometry(self, attacker, defender):
        old_geometry = self.obj.query(f'Empire == "{attacker.Empire}"').loc[attacker.Territory].empire_geometry
        new_geometry = old_geometry.union(defender.geometry)
        empire_territories_index = self.obj.query(f'Empire == "{attacker.Empire}"').index
        self.obj.loc[empire_territories_index, "empire_geometry"] = [new_geometry] * len(empire_territories_index)

    def __reduce_empire_geometry(self, defender):
        old_geometry = self.obj.query(f'Empire == "{defender.Empire}"').loc[defender.Territory].empire_geometry
        new_geometry = old_geometry.difference(defender.geometry)
        empire_terriories_index = self.obj.query(f'Empire == "{defender.Empire}"').index
        self.obj.loc[empire_terriories_index, "empire_geometry"] = [new_geometry] * len(empire_terriories_index)

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
        empire = random.choice(self.obj.Empire.values.tolist())
        empire_neighbours = self.obj.query(f'Empire == "{empire}"').iloc[0].empire_neighbours

        # Choose the defender Territory among the empire's neighbours
        defender = random.choice(empire_neighbours)
        defender = Territory(self.obj.loc[defender])

        # Find the attackers as the intersection between ∑'s all territories and Ω's neighbours
        attacker_territories = self.obj.query(f'Empire == "{empire}"').index.values.tolist()
        attackers = list(set(attacker_territories) & set(defender.neighbours))

        assert len(attackers) > 0, f"{defender} {attacker_territories}"

        # Pick a random attacker Territory from Territories at the border
        attacker = random.choice(attackers)
        attacker = Territory(self.obj.loc[attacker])

        # Send message
        if attacker.Territory == attacker.Empire and defender.Territory == defender.Empire:
            message = messages["battle_a"] % (attacker.Territory, defender.Territory)
        elif attacker.Territory != attacker.Empire and defender.Territory == defender.Empire:
            message = messages["battle_b"] % (attacker.Territory, attacker.Empire, defender.Territory)
        elif attacker.Territory == attacker.Empire and defender.Territory != defender.Empire:
            message = messages["battle_b"] % (attacker.Territory, defender.Territory, defender.Empire)
        else:
            message = messages["battle"]

        logger.info(message)

        sleep(10)

        # Compute the strength of the attacker and defender
        counts = self.obj.groupby("Empire").count().geometry
        attack = attacker.attack() * counts[attacker.Empire] / len(self.obj)
        defense = defender.defend() * counts[defender.Empire] / len(self.obj)

        # The attacker won
        if attack > defense:
            message = messages["attacker_won"] % (attacker.Territory, defender.Territory)
            # logger.info(message)

            # If the empire has more than one territory, reduce its geometry
            if len(self.obj.query(f'Empire == "{defender.Empire}"')) > 1:
                self.__reduce_empire_geometry(defender)

            # If the empire has only one territory, the empire has been defeated
            else:
                self.remaing_territories = len(self.__get_alive_empires()) - 1

                message += '\n' + messages["defender_defeated"] % defender.Empire
                message += '\n' + messages["remaining_territories"] % self.remaing_territories
                # logger.info(message)

            # Change the defender's Empire to the attacker one
            old_defender = defender
            old_attacker = attacker
            self.obj.loc[defender.Territory, "Empire"] = attacker.Empire

            # Update geometries and neighbours
            self.__update_empire_neighbours(attacker.Empire)
            self.__update_empire_neighbours(old_defender.Empire)
            self.__expand_empire_geometry(attacker, defender)

            if self.should_display_map:
                self.draw_map(old_attacker, defender)
                with open("img.png", "rb") as img:
                    self.telegram_dispatcher.bot.send_photo(chat_id="@BoloWarBot", photo=InputFile(img),
                                                            caption=message)
        # The defender won
        else:
            message = messages["defender_won"] % (defender.Territory, attacker.Territory)
            logger.info(message)

    @staticmethod
    def __better_name(name):
        words = name.split()
        words = ["S." if x == "San" else x for x in words]
        if len(words) >= 4:
            return " ".join(words[:2]) + "\n" + " ".join(words[2:])
        else:
            return words[0] + "\n" + " ".join(words[1:])

    def draw_map(self, attacker: Territory, defender: Territory):

        _, ax = plt.subplots(figsize=(12, 12))
        patches = []
        empires = [e for e in self.obj.Empire.unique() if e != attacker.Empire and e != defender.Territory]

        for i, empire in self.obj.loc[empires].iterrows():
            color = empire.empire_color
            patches.append(
                PolygonPatch(empire.empire_geometry, alpha=0.75, fc=color, ec="#555555"))
            ax.annotate(s=self.__better_name(i),
                        xy=empire.empire_geometry.centroid.coords[0],
                        ha="center", fontsize=12)

        patches.append(PolygonPatch(attacker.empire_geometry, alpha=1, fc=attacker.empire_color, ls=2, ec="#E1025B"))
        patches.append(PolygonPatch(defender.empire_geometry, alpha=1, fc=defender.empire_color, ls=2, ec="#E1025B"))

        ax.add_collection(PatchCollection(patches, match_original=True))

        ax.add_patch(Polygon(defender.geometry.exterior.coords, fc=defender.empire_color, lw=2, ec="#15F505", hatch="/"))
        ax.annotate(s=self.__better_name(attacker.Empire),
                    xy=attacker.empire_geometry.centroid.coords[0],
                    ha="center", fontsize=12)
        ax.annotate(s=self.__better_name(defender.Territory),
                    xy=defender.geometry.centroid.coords[0],
                    ha="center", fontsize=12)

        ax.set_aspect(1)
        ax.axis('off')
        ax.grid(False)
        plt.axis('equal')
        plt.tight_layout()
        img = ax.get_figure()
        img.savefig("img.png")
        # plt.show()

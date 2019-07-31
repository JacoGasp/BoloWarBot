from time import sleep
import random
import logging

import pandas as pd
import matplotlib.pyplot as plt
from descartes import PolygonPatch
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection

from telegram import TelegramError

from utils.utils import messages, config
from territory import Territory


@pd.api.extensions.register_dataframe_accessor('reign')
class Reign(object):

    def __init__(self, pandas_obj, should_display_map=False):
        self.obj = pandas_obj
        self.remaing_territories = len(self.__get_alive_empires())
        self.alive_empires = list(pandas_obj.index.values)
        self.should_display_map = should_display_map

        self.logger = logging.getLogger(self.__class__.__name__)
        self.__telegram_handler = None
        self.__msg_cache_handler = None

        self.battle_round = 1

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
            message = messages["battle_c"] % (attacker.Territory, defender.Territory, defender.Empire)
        else:
            message = messages["battle"] % (attacker.Territory, attacker.Empire, defender.Territory, defender.Empire)

        self.logger.info(message)
        # self.__telegram_handler.send_message(message)

        # Send poll. If cannot open poll skip the turn
        question = message + '\n\n' + messages["poll"]
        try:
            message_id, poll_id = self.__telegram_handler.send_poll(attacker.Territory, defender.Territory, question)
        except TelegramError:
            self.logger.warning("Skip turn")
            return

        # Wait for the vote
        sleep(config["schedule"]["wait_for_poll"])

        # Close the poll and read the results.
        self.__telegram_handler.stop_poll(message_id)
        poll_results = self.__telegram_handler.get_last_poll_results(poll_id)

        if poll_results:
            total_votes = sum(poll_results.values())
        else:
            total_votes = 0

        # Compute the strength of the attacker and defender
        if total_votes > 0:
            attack = attacker.attack() * poll_results[attacker.Territory] / total_votes
            defense = defender.defend() * poll_results[defender.Territory] / total_votes
        else:
            counts = self.obj.groupby("Empire").count().geometry
            attack = attacker.attack() * counts[attacker.Empire] / len(self.obj)
            defense = defender.defend() * counts[defender.Empire] / len(self.obj)

        self.battle_round += 1

        # The attacker won
        if attack > defense:
            message = messages["attacker_won"] % (attacker.Territory, defender.Territory,
                                                  defender.Territory, attacker.Empire)

            # If the empire has more than one territory, reduce its geometry
            if len(self.obj.query(f'Empire == "{defender.Empire}"')) > 1:
                self.__reduce_empire_geometry(defender)

            # If the empire has only one territory, the empire has been defeated
            else:
                self.remaing_territories = len(self.__get_alive_empires()) - 1

                message += '\n' + messages["defender_defeated"] % defender.Empire
                message += '\n' + messages["remaining_territories"] % self.remaing_territories

            # Change the defender's Empire to the attacker one
            old_defender = defender
            old_attacker = attacker
            self.obj.loc[defender.Territory, "Empire"] = attacker.Empire

            # Update geometries and neighbours
            self.__update_empire_neighbours(attacker.Empire)
            self.__update_empire_neighbours(old_defender.Empire)
            self.__expand_empire_geometry(attacker, defender)

            # Send map to Telegram
            self.__send_map_to_bot(old_attacker, defender, caption=message)
            self.logger.info(message)

        # The defender won
        else:
            message = messages["defender_won"] % (defender.Territory, attacker.Territory)
            self.logger.info("Round: %d - %s", self.battle_round, message)
            self.__telegram_handler.send_message(message)

        self.battle_round += 1

    @staticmethod
    def __better_name(name):
        words = name.split()
        words = ["S." if x == "San" else x for x in words]
        if len(words) >= 4:
            return " ".join(words[:2]) + "\n" + " ".join(words[2:])
        else:
            return words[0] + "\n" + " ".join(words[1:])

    def __draw_map(self, attacker: Territory, defender: Territory):

        _, ax = plt.subplots(figsize=(12, 12))
        patches = []
        empires = [e for e in self.obj.Empire.unique() if e != attacker.Empire and e != defender.Territory]

        # Add all empire patches but both attacker and defender territories
        for i, empire in self.obj.loc[empires].iterrows():
            color = empire.empire_color
            patches.append(
                PolygonPatch(empire.empire_geometry, alpha=0.75, fc=color, ec="#555555"))
            ax.annotate(s=self.__better_name(i),
                        xy=empire.empire_geometry.centroid.coords[0],
                        ha="center", fontsize=12)

        # Give to the defender the attacker color and add oblique lines on top the defender area
        patches.append(PolygonPatch(attacker.empire_geometry, alpha=1, fc=attacker.empire_color, lw=4, ec="#15F505", zorder=10))
        ax.add_patch(Polygon(defender.geometry.exterior.coords, fc=defender.empire_color, lw=4, ec="#E1025B", hatch="//", zorder=2))
        # Set the attacker and defender titles
        ax.annotate(s=self.__better_name(attacker.Empire),
                    xy=attacker.geometry.centroid.coords[0],
                    ha="center", fontsize=12)
        ax.annotate(s=self.__better_name(defender.Territory),
                    xy=defender.geometry.centroid.coords[0],
                    ha="center", fontsize=12)

        # Add all patches
        ax.add_collection(PatchCollection(patches, match_original=True))

        ax.set_aspect(1)
        ax.axis('off')
        ax.grid(False)
        plt.axis('equal')
        plt.tight_layout()
        img = ax.get_figure()

        # Save the fig to send later
        img_path = config["saving"]["dir"] + "/img.png"
        img.savefig(img_path)
        # plt.show()

    def __send_map_to_bot(self, attacker, defender, caption):
        img_path = config["saving"]["dir"] + "/img.png"
        self.__draw_map(attacker, defender)
        self.__telegram_handler.send_image(img_path, caption=caption, battle_round=self.battle_round)

    @property
    def telegram_handler(self):
        return self.__telegram_handler

    @telegram_handler.setter
    def telegram_handler(self, obj):
        self.__telegram_handler = obj

    @property
    def msg_cache_handler(self):
        return self.__msg_cache_handler

    @msg_cache_handler.setter
    def msg_cache_handler(self, obj):
        self.__msg_cache_handler = obj

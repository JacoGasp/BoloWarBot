import os
from time import sleep
import random
import logging
from copy import deepcopy

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from descartes import PolygonPatch
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import matplotlib.patheffects as PathEffects
from shapely.geometry.multipolygon import MultiPolygon
from telegram import TelegramError
from utils.utils import messages, config, schedule_config
from territory import Territory


@pd.api.extensions.register_dataframe_accessor('reign')
class Reign(object):

    def __init__(self, pandas_obj, threshold, low_b, should_display_map=False):
        self.obj = pandas_obj
        self.remaing_territories = len(self.__get_alive_empires())
        self.alive_empires = list(pandas_obj.index.values)
        self.should_display_map = should_display_map

        self.logger = logging.getLogger(self.__class__.__name__)
        self.__telegram_handler = None
        self.__msg_cache_handler = None

        self.battle_round = 1

        self.threshold = threshold
        self.low_b = low_b

        # random.seed(10)

    def __update_empire_neighbours(self, empire):
        empire_df = self.obj.query(f'Empire == "{empire}"')
        territories_neighbours = empire_df.neighbours.values.tolist()
        territories_neighbours = list(set([item for sublist in territories_neighbours for item in sublist]))

        empire_idx = empire_df.index
        empire_territories = empire_idx.values.tolist()
        empire_neighbours = list(filter(lambda x: x not in empire_territories, territories_neighbours))

        self.obj.loc[empire_idx, "empire_neighbours"] = [empire_neighbours] * len(empire_idx)

    def __update_defender_attrs(self, attacker, defender, geometry_reducer=None):
        defender_empire_index = self.obj.query(f'Empire == "{defender.Empire}"').index
        self.obj.loc[defender_empire_index, "Empire"] = [attacker.Empire] * len(defender_empire_index)
        self.obj.loc[defender_empire_index, "empire_color"] = [attacker.empire_color] * len(defender_empire_index)

        if geometry_reducer is not None:
            new_geometry = geometry_reducer(attacker, defender)
            self.obj.loc[defender_empire_index, "empire_geometry"] = [new_geometry] * len(defender_empire_index)

    def __expand_empire_geometry(self, attacker, defender):
        new_geometry = attacker.empire_geometry.union(defender.geometry)
        empire_territories_index = self.obj.query(f'Empire == "{attacker.Empire}"').index
        self.obj.loc[empire_territories_index, "empire_geometry"] = [new_geometry] * len(empire_territories_index)

    @staticmethod
    def __reduce_defender_geometry(defender):
        return defender.empire_geometry.difference(defender.geometry)

    def __merge_empires_geometry(self, attacker, defender):
        new_geometry = attacker.empire_geometry.union(defender.empire_geometry)
        empire_territories_index = self.obj.query(f'Empire == "{attacker.Empire}"').index
        defender_territories_index = self.obj.query(f'Empire == "{defender.Empire}"').index
        index = empire_territories_index.union(defender_territories_index)
        self.obj.loc[index, "empire_geometry"] = [new_geometry] * len(index)

    def __get_alive_empires(self):
        empires = self.obj.Empire.unique()
        return list(empires)

    def __send_poll(self, attacker, defender):
        try:
            message_id, poll_id = self.__telegram_handler.send_poll(attacker.Territory, defender.Territory, messages['poll'])
        except TelegramError:
            self.logger.warning("Skip turn")
            return

        # Wait for the vote
        poll_interval = schedule_config["wait_for_poll"]
        if config["distribution"] == "production":
            sleep(poll_interval * 60)
        elif config["distribution"] == "develop":
            sleep(poll_interval)

        # Close the poll and read the results.
        self.__telegram_handler.stop_poll(message_id)
        poll_results = self.__telegram_handler.get_last_poll_results(poll_id)
        return poll_results

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

        empire_list = self.obj.Empire.values.tolist()
        un_empire, empire_weight = np.unique(empire_list, return_counts=True)
        probability_ratio = max(empire_weight)/empire_weight

        if len(un_empire) < self.threshold and any(probability_ratio > self.low_b):
            empire_weight[probability_ratio > self.low_b] = max(empire_weight)/self.low_b
        else:
            pass

        empire=random.choices(un_empire, empire_weight)

        #empire = random.choice(self.obj.Empire.values.tolist())
        empire_neighbours = self.obj.query(f'Empire == "{empire[0]}"').iloc[0].empire_neighbours

        # Choose the defender Territory among the empire's neighbours
        defender = random.choice(empire_neighbours)
        defender = Territory(self.obj.loc[defender])

        # Find the attackers as the intersection between ∑'s all territories and Ω's neighbours
        attacker_territories = self.obj.query(f'Empire == "{empire[0]}"').index.values.tolist()
        attackers = list(set(attacker_territories) & set(defender.neighbours))

        assert len(
            attackers) > 0, f"Defender territory: {defender.Territory}; possible attackers: {attacker_territories}"

        # Pick a random attacker Territory from Territories at the border
        attacker = random.choice(attackers)
        attacker = Territory(self.obj.loc[attacker])

        assert attacker.Territory != defender.Territory, f"Attacker and defender territories are equal: {attacker.Territory}"
        assert attacker.Empire != defender.Empire, f"Attacker and defender empires are equal: {attacker.Empire}"
        assert attacker.Territory not in self.obj.query(
            f'Empire == "{defender.Empire}"').index.tolist(), f"Attacker territory {attacker.Territory} " \
                                                              f"in defender empire {defender.Empire}"

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

        # Send map with caption
        message = "*Round %d:*\n" % self.battle_round + message
        self.__send_map_to_bot(attacker=attacker, defender=defender, caption=message)

        # Send poll. If cannot open poll skip the turn
        poll_results = self.__send_poll(attacker, defender)

        if poll_results:
            total_votes = sum(poll_results.values())
        else:
            total_votes = 0

        # Compute the strength of the attacker and defender
        attacker_votes = poll_results[attacker.Territory]
        defender_votes = poll_results[defender.Territory]

        if total_votes > 0:
            w = 0.66  # users votes weight 2/3 vs 1/3 random
            duel = random.random() * (1 - w) + attacker_votes / (attacker_votes + defender_votes) * w
        else:
            duel = random.random()

        # The attacker won
        if duel > 0.5:
            message = messages["attacker_won"] % (attacker.Territory, defender.Territory,
                                                  defender.Territory, attacker.Empire)

            # Copy the attacker and defender state as it is before the battle
            old_defender = deepcopy(defender)

            # If the capitol city looses, the attacker takes the whole empire
            if defender.Territory == defender.Empire:
                message = messages["capitol_defeated"] % (attacker.Territory, defender.Empire, attacker.Empire)
                message += '\n' + messages["defender_defeated"] % defender.Empire
                message += '\n' + messages["remaining_territories"] % self.remaing_territories

                self.__merge_empires_geometry(attacker=attacker, defender=defender)
                self.__update_defender_attrs(attacker=attacker, defender=defender)
                self.remaing_territories = len(self.__get_alive_empires()) - 1

            else:
                # If the empire has more than one territory, reduce its geometry
                # Change the empire geometry for the whole defender empire
                # Change the sovereign for the whole defender empire
                if len(self.obj.query(f'Empire == "{defender.Empire}"')) > 1:

                    defender_empire_index = self.obj.query(f'Empire == "{defender.Empire}"').index
                    self.obj.loc[defender.Territory, "empire_color"] = attacker.empire_color
                    self.obj.loc[defender_empire_index, "empire_geometry"] = [self.__reduce_defender_geometry(
                        defender)] * len(defender_empire_index)
                    self.obj.loc[defender.Territory]["Empire"] = attacker.Empire
                    self.__expand_empire_geometry(attacker, old_defender)

                # If the empire has only one territory, the empire has been defeated
                # Change the defender's Empire, to the attacker one
                # Change the color for the whole old defender empire
                # Merge the attacker and defender geometries
                else:
                    self.remaing_territories = len(self.__get_alive_empires()) - 1
                    message += '\n' + messages["defender_defeated"] % defender.Empire
                    message += '\n' + messages["remaining_territories"] % self.remaing_territories

                    defender_empire_index = self.obj.query(f'Empire == "{defender.Empire}"').index
                    self.obj.loc[defender_empire_index, "Empire"] = [attacker.Empire] * len(defender_empire_index)
                    self.obj.loc[defender_empire_index, "empire_color"] = [attacker.empire_color] * len(
                        defender_empire_index)
                    self.__merge_empires_geometry(attacker, defender)

            # Update geometries and neighbours
            self.__update_empire_neighbours(attacker.Empire)
            self.__update_empire_neighbours(old_defender.Empire)
            self.__expand_empire_geometry(attacker, defender)

            # Send map to Telegram
            self.__telegram_handler.send_message(message)
            # self.__send_map_to_bot(attacker=old_attacker, defender=old_defender, caption=message)

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
        elif len(words) == 1:
            return words[0]
        else:
            return words[0] + "\n" + " ".join(words[1:])

    def draw_map(self, attacker: Territory, defender: Territory):

        fig, ax = plt.subplots(figsize=(12, 12))
        patches = []
        empires = [e for e in self.obj.Empire.unique() if e != attacker.Empire and e != defender.Empire]

        assert attacker.Empire not in empires, "Attacker's empire in empires"
        assert defender.Empire not in empires, "Defender's empire in empires"

        def annotate(s, xy, fontsize=10):
            ax.annotate(s=self.__better_name(s), xy=list(xy),
                        fontsize=fontsize, ha="center", color="white",
                        path_effects=[PathEffects.withStroke(linewidth=2, foreground="k")]
                        )
        try:
            # Add all empire patches but both attacker and defender territories
            for empire_name, empire in self.obj.loc[empires].iterrows():
                color = empire.empire_color
                patches.append(
                    PolygonPatch(empire.empire_geometry, alpha=0.75, fc=color, ec="#555555"))
                annotate(s=empire_name, xy=empire.empire_geometry.representative_point().coords[0])

            # Give to the defender the attacker color and add oblique lines on top the defender area
            patches.append(
                PolygonPatch(defender.empire_geometry, alpha=1, fc=defender.empire_color, lw=4, ec="#E1025B"))

            # Account for geometries composed by multi-polygons
            if isinstance(defender.geometry, MultiPolygon):
                for polygon in defender.geometry:
                    ax.add_patch(
                        Polygon(polygon.exterior.coords, fc=defender.empire_color, lw=2, ec="#E1025B", hatch="//"))
            else:
                ax.add_patch(
                    Polygon(defender.geometry.exterior.coords, fc=defender.empire_color, lw=2, ec="#E1025B",
                            hatch="//"))

            patches.append(
                PolygonPatch(attacker.empire_geometry, alpha=1, fc=attacker.empire_color, lw=4, ec="#15F505"))

            # Set the attacker and defender titles
            annotate(s=attacker.Empire, xy=attacker.empire_geometry.representative_point().coords[0])
            annotate(s=defender.Empire, xy=defender.empire_geometry.representative_point().coords[0])

            if attacker.Empire != attacker.Territory:
                annotate(s=attacker.Territory, xy=attacker.geometry.representative_point().coords[0])

            if defender.Empire != defender.Territory:
                annotate(s=defender.Territory, xy=defender.geometry.representative_point().coords[0])

            # Add all patches
            ax.add_collection(PatchCollection(patches, match_original=True))

            ax.set_aspect(1)
            ax.axis('off')
            ax.grid(False)
            plt.axis('equal')
            plt.tight_layout()
            img = ax.get_figure()
            # plt.show()

            # Save the fig to send later
            if not os.path.exists(config["saving"]["dir"]):
                os.makedirs(config["saving"]["dir"])
            img_path = os.path.join(config["saving"]["dir"], config["saving"]["map_img"])
            img.savefig(img_path)
            plt.close(fig)
        except (AttributeError, KeyError, ValueError, OSError) as e:
            self.logger.error("Error drawing map for attacker: %s; defender %s with error: %s", attacker.Territory,
                              defender.Territory, e)
            raise e

    def __send_map_to_bot(self, attacker, defender, caption):
        img_path = os.path.join(config["saving"]["dir"], config["saving"]["map_img"])
        self.draw_map(attacker=attacker, defender=defender)
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

from random import random, sample
import pandas as pd


class Reign:

    def __init__(self, name, df):
        self.name = name
        self.df = df

    def get_reign(self):
        return self.df.COMUNE.values.tolist()

    def get_neighbours(self):
        n = [item for sublist in self.df.neighbours.values.tolist() for item in sublist if item not in self.get_reign()]
        return list(set(n))

    def attack(self, enemy):

        # enemy_name = sample(self.get_neighbours(), 1)[0]
        # enemy = reigns[enemy_name.lower()]

        print(f"Attacking: {enemy.name}...\n")

        attack_result = random()

        if attack_result > enemy.defend():
            self.df = pd.concat([self.df, enemy.df], ignore_index=True)

            print(f"{self.name} conquered {enemy.name}.")
            return True
        else:
            print(f"{enemy.name} survived to the attack.")
            return False

    @staticmethod
    def defend():
        result = random()
        return result

# from random import random, seed
# import pandas as pd
# seed(2)
#
# class Reign:
#
#     def __init__(self, name, df):
#         self.name = name
#         self.df = df
#
#     def get_reign(self):
#         """Get all conquered territories"""
#         return self.df.COMUNE.values.tolist()
#
#     def get_neighbours(self):
#         """Get all boundary territories"""
#         # n = [item for sublist in self.df.neighbours.values.tolist() for item in sublist if item not in self.get_reign()]
#
#         n = []
#         for item in self.df.neighbours.values.tolist():
#             for subitem in item:
#                 if subitem not in self.get_reign():
#                     n.append(subitem)
#         return list(set(n))
#
#     def attack(self, enemy):
#
#         # enemy_name = sample(self.get_neighbours(), 1)[0]
#         # enemy = reigns[enemy_name.lower()]
#
#         print(f"{self.name} attacks {enemy.name}... ⚔️")
#
#         attack_result = random()
#
#         if attack_result > enemy.defend():
#             self.df = pd.concat([self.df, enemy.df], ignore_index=True)
#
#             print(f"{self.name} conquered {enemy.name}. 🗡\n")
#             return True
#         else:
#             print(f"{enemy.name} survived to the attack. 🛡\n")
#             return False
#
#     @staticmethod
#     def defend():
#         result = random()
#         return result

import pandas as pd
from random import choice
from Reign import *

df = pd.read_pickle("bologna.pickle")

# Alternative loop version to define reigns dictionary

#reigns={}
#for k in df.COMUNE.values:
#    reignsb[k.lower()]= Reign(k,df[df.COMUNE==k])
    
    
reigns = {k.lower(): Reign(k, df[df.COMUNE == k]) for k in df.COMUNE.values}


def battle():
    while len(reigns) > 1:
        reign: Reign = choice(list(reigns.values()))

        neighbours = reign.get_neighbours()
        enemy_name = choice(neighbours)
        enemy = reigns[enemy_name.lower()]

        if reign.attack(enemy):
            del reigns[enemy_name.lower()]
            print(f"Remaining reigns: {len(reigns)}")


battle()

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
    def Territory(self):
        return self.name

    @staticmethod
    def attack():
        return random.random()

    @staticmethod
    def defend():
        return random.random()

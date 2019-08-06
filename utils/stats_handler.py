import logging
import os
import json


class StatsList(list):

    def __init__(self, ll):
        self.ll = ll
        super().__init__(ll)

    def append(self, item):
        super(StatsList, self).append(item)
        self.on_change()

    def on_change(self):
        pass


class StatsHandler(object):

    def __init__(self, file_path):
        self.file_path = file_path
        self.__stats = StatsList([])
        self.__stats.on_change = self.dump_stats_to_disk

        self.logger = logging.getLogger(self.__class__.__name__)

        stats_dir = "/".join(file_path.split("/")[:-1])
        if not os.path.exists(stats_dir):
            os.makedirs(stats_dir)

    def dump_stats_to_disk(self):
        try:
            with open(self.file_path, "w") as fp:
                json.dump(self.__stats, fp)
                self.logger.debug("Stats saved to file.")
        except (IOError, FileNotFoundError, OSError) as e:
            self.logger.warning("Cannot save stats to disk: %s", e)

    @property
    def stats(self):
        return self.__stats

    @stats.setter
    def stats(self, value):
        if self.__stats != value:
            self.dump_stats_to_disk()
        self.__stats = value

import logging
import os
import pickle
from threading import Lock
import glob

from utils.utils import config


class MsgCacheHandler(object):
    """
    Class used to handle the unsent observations file.
    """
    persist_dir = "cache/"
    msg_file = "messages.cache"

    msg_list = []

    def __init__(self, oc_dir=persist_dir, force_mkdir=False):
        if not os.path.exists(oc_dir) and force_mkdir:
            os.makedirs(oc_dir)
        elif not os.access(oc_dir, os.R_OK | os.W_OK | os.X_OK):
            raise OSError("Folder {} does not exist or is not writable.".format(oc_dir))

        self.logger = logging.getLogger(self.__class__.__name__)
        self.msg_cache_file = os.path.join(oc_dir, self.msg_file)
        self.logger.debug("Observation cache file: %s", self.msg_cache_file)

        self.__lock = Lock()

    def remove_msg_cache_file(self):
        if os.path.exists(self.msg_cache_file):
            try:
                os.remove(self.msg_cache_file)
            except OSError as e:
                self.logger.warning("Error deleting observation cache file '%s': %s", self.msg_cache_file, e)
            else:
                self.logger.debug("Observation cache file '%s' deleted", self.msg_cache_file)

    def get_cached_msgs(self):
        msg_list = None
        if os.path.exists(self.msg_cache_file):
            try:
                with open(self.msg_cache_file, 'rb') as msg_file:
                    msg_list = pickle.load(msg_file)
            except (OSError, EOFError, ValueError, TypeError) as ex:
                self.logger.warning("Can't read observation cache file: %s", ex)
        return msg_list

    def add_msg_to_cache(self, message):
        self.__lock.acquire()
        msg_to_cache = {"type": "text", "message": message}
        self.msg_list.append(msg_to_cache)
        try:
            with open(self.msg_cache_file, 'wb') as msg_file:
                pickle.dump(self.msg_list, msg_file)
        except OSError as ex:
            self.logger.warning("Can't add msg to cache file: %s", ex)
        finally:
            self.__lock.release()

    def remove_msg_from_cache(self):
        self.__lock.acquire()
        try:
            if len(self.msg_list) > 0:
                del self.msg_list[-1]
                with open(self.msg_cache_file, 'wb') as msg_file:
                    pickle.dump(self.msg_list, msg_file)
        except (OSError, KeyError) as ex:
            self.logger.warning("Can't remove msg from cache: %s", ex)
        finally:
            self.__lock.release()

    def add_photo_to_cache(self, caption, battle_round=None):
        self.__lock.acquire()
        if battle_round is not None:
            fname = self.persist_dir + f"img_round{battle_round}.png"
        else:
            fname = config["saving"]["dir"] + "/img.png"

        msg_to_cache = {"type": "image", "fname": fname, "caption": caption}
        self.msg_list.append(msg_to_cache)
        try:
            if battle_round is not None:
                os.rename(config["saving"]["dir"] + "/img.png", fname)
            with open(self.msg_cache_file, 'wb') as msg_file:
                pickle.dump(self.msg_list, msg_file)
        except OSError as ex:
            self.logger.warning("Can't add image to cache file: %s", ex)
        finally:
            self.__lock.release()

    def remove_photo_cache_files(self):
        files = glob.glob(self.persist_dir + "*.png")
        for file in files:
            try:
                os.remove(file)
            except OSError as e:
                self.logger.warning("Error deleting observation cache file '%s': %s", self.msg_cache_file, e)
            else:
                self.logger.debug("Observation cache file '%s' deleted", self.msg_cache_file)
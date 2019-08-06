import json
import signal


def get_sig_dict():
    return dict((k, v) for v, k in reversed(sorted(signal.__dict__.items()))
                if v.startswith('SIG') and not v.startswith('SIG_'))


def read_saved_turn(path, logger):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        logger.error("Cannot read stats file %s", e)
        return None

import logging as log
import sys

DEFAULT_LEVEL_NAME = "DEBUG"
LOGGING_FORMAT = "%(asctime)s - %(message)s"


def set_log_level(level_name):
    if level_name != DEFAULT_LEVEL_NAME:
        level_name = level_name.upper()

    try:
        level = log.getLevelName(level_name)
        log.basicConfig(
            format=LOGGING_FORMAT,
            level=log.getLevelName(level_name),
            datefmt="%H:%M:%S",
            force=True
        )
        return log
    except ValueError:
        print(f"Logging level of {level_name} not recognised, defaulting to DEBUG")
        sys.exit(1)


set_log_level(DEFAULT_LEVEL_NAME)

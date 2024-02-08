# This file is used to read from the config file and return the values of the parameters

import configparser
import os


def get_config():
    config = configparser.ConfigParser()

    if not os.path.exists('config.ini'):
        print("Could not find config.ini")
        print("Please create a config.ini file")
        exit(1)

    config.read('config.ini')

    return config


def get_config_value(section, key):
    config = get_config()

    if config[section][key] is None:
        print(f"Could not find {key} in the config file")
        print(f"Please add {key} to the config file")
        exit(1)

    return config[section][key]
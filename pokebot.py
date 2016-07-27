from pgoapi import PGoApi
from pokeutils import *
from pokelocation import *

import logging

import os
import argparse
import json

log = logging.getLogger(__name__)

def init_config():
    parser = argparse.ArgumentParser()
    config_file = "config.json"

    # If config file exists, load variables from json
    load   = {}
    if os.path.isfile(config_file):
        with open(config_file) as data:
            load.update(json.load(data))

    # Read passed in Arguments
    required = lambda x: not x in load
    parser.add_argument("-a", "--auth_service", help="Auth Service ('ptc' or 'google')",
        required=required("auth_service"))
    parser.add_argument("-u", "--username", help="Username", required=required("username"))
    parser.add_argument("-p", "--password", help="Password", required=required("password"))
    parser.add_argument("-l", "--location", help="Location", required=required("location"))
    parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true')
    parser.add_argument("-t", "--test", help="Only parse the specified location", action='store_true')
    parser.set_defaults(DEBUG=False, TEST=False)
    config = parser.parse_args()

    # Passed in arguments shoud trump
    for key in config.__dict__:
        if key in load and config.__dict__[key] == None:
            config.__dict__[key] = load[key]

    if config.auth_service not in ['ptc', 'google']:
      log.error("Invalid Auth service specified! ('ptc' or 'google')")
      return None
    
    return config

class BotException(Exception):
    pass

class PokeBot():

    def __init__(self, configuration):
        print "Bot initializated"
        self.config = configuration;
        self.api = PGoApi()
        self.location = PokeLocation(self.api)
        

    def start(self):
        print "Getting location.."
        position = get_pos_by_name(self.config.location)
        if (position[0] == 0 or \
            position[1] == 0):
            log.error("Can't get location.")
            raise BotException

        print "Logging in.."
        self.location.set_position(position)

        if not self.api.login(self.config.auth_service, self.config.username, self.config.password):
            print "Can't login!"
            raise BotException

        print "Login successful"


if __name__ == "__main__":
    bot = PokeBot(init_config())
    bot.start()

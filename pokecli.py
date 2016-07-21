import os
import re
import json
import struct
import logging
import requests
import argparse
import time

from pgoapi import PGoApi
from pgoapi.utilities import f2i, h2f

from google.protobuf.internal import encoder
from geopy.geocoders import GoogleV3
from s2sphere import CellId, LatLng

log = logging.getLogger(__name__)

pokestops_filename = "pokestops.json"
pokestops_farms = {}

def pokefarm_load():
    global pokestops_farms
    try:
        print "pokefarm_load == Loading pokestops from file.."
        f = open(pokestops_filename, 'r')
        pokestops_farms = json.loads(f.read())
        pokestops_farms
        f.close()
    except:
        print "pokefarm_load == Can't load pokestops from file."

def pokefarm_save():
    pk_json = json.dumps(pokestops_farms)
    f = open(pokestops_filename, 'wb')
    f.write(pk_json);
    f.close()

def parse_getmapobjects_response(obj):
    pokefarm_load()
    status = obj['responses']['GET_MAP_OBJECTS']['status']

    # yeah, it's orrible, if you want please fix this
    if status == 1:
        cells = obj['responses']['GET_MAP_OBJECTS']['map_cells']
        for i in cells:
            if 'forts' in i:
                for k in i['forts']:
                    if not 'gym_points' in k:
                        if k['id'] in pokestops_farms:
                            print "Pokestop " + k['id'] + " already known"
                            continue
                        
                        print "Pokestop at " + str(k['longitude']) + "," + str(k['latitude']),
                        print " id: " + k['id']

                        poke_id = k['id']
                        
                        del k['last_modified_timestamp_ms']
                        del k['type']
                        del k['enabled']
                        del k['id']
                        pokestops_farms[poke_id] = k
    pokefarm_save()
    


def get_pos_by_name(location_name):
    geolocator = GoogleV3()
    try:
        loc = geolocator.geocode(location_name)        
        log.info('Your given location: %s', loc.address.encode('utf-8'))
        log.info('lat/long/alt: %s %s %s', loc.latitude, loc.longitude, loc.altitude)
        return (loc.latitude, loc.longitude, loc.altitude)
    except:
        log.info("Can't get position, quitting")
        exit()
        

def get_cellid(lat, long):
    origin = CellId.from_lat_lng(LatLng.from_degrees(lat, long)).parent(15)
    walk = [origin.id()]

    # 10 before and 10 after
    next = origin.next()
    prev = origin.prev()
    for i in range(10):
        walk.append(prev.id())
        walk.append(next.id())
        next = next.next()
        prev = prev.prev()
    return ''.join(map(encode, sorted(walk)))

def encode(cellid):
    output = []
    encoder._VarintEncoder()(output.append, cellid)
    return ''.join(output)
    
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

def distance_by_points(lat1, lng1, lat2, lng2):
    coord1 = s2sphere.LatLng.from_degrees(lat1, lng1)
    coord2 = s2sphere.LatLng.from_degrees(lat2, lng2)
    angle = coord1.get_distance(coord2)
    return 6371e3 * angle.radians


def main():
    global pokestops_farms
    running = True
    # log settings
    # log format
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
    # log level for http request class
    logging.getLogger("requests").setLevel(logging.WARNING)
    # log level for main pgoapi class
    logging.getLogger("pgoapi").setLevel(logging.INFO)
    # log level for internal pgoapi class
    logging.getLogger("rpc_api").setLevel(logging.INFO)

    config = init_config()
    if not config:
        return
        
    if config.debug:
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("rpc_api").setLevel(logging.DEBUG)
    
    position = get_pos_by_name(config.location)
    if config.test:
        return
    
    # instantiate pgoapi 
    api = PGoApi()
    
    # provide player position on the earth
    api.set_position(*position)
    
    if not api.login(config.auth_service, config.username, config.password):
        return

    
    # get player profile call
    # ----------------------
    #api.get_player()
    
    
    # get map objects call
    # ----------------------
    #timestamp = "\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000"
    #cellid = get_cellid(position[0], position[1])
    #api.get_map_objects(latitude=f2i(position[0]), longitude=f2i(position[1]), since_timestamp_ms=timestamp, cell_id=cellid)

    #response_dict = api.call()
    #parse_getmapobjects_response(response_dict)

    while running:
        print "\r\n\r\n\r\n - What you want to do?"
        print " 1. Move (current location is:",
        print position,
        print ")"
        print " 2. Show & load pokestop"
        print " 3. Delete loaded pokestop"
        print " 4. Search & save pokestop"
        print " 5. Start pokestop farming"
        print " 0. Quit"

        choice = input(" --> ")
        if (choice == 0): running = False

        # Move
        if (choice == 1):
            lat = int(raw_input(" -- Input new latitude: (0 to cancel): "))
            if (lat == 0): continue
            lng = int(raw_input(" -- Input new longitude: (0 to cancel): "))
            if (lng == 0): continue
            sure = raw_input(" -- Are you sure (y/n)? ")
            if (sure == "y"):
                position = (lat, lng, 0.0)
                api.set_position(*position)

        # Show & Load pokestops
        elif (choice == 2):
            pokefarm_load()
            for pokeid, value in pokestops_farms.iteritems():
                print "Farm " + pokeid + " at " + str(value['latitude']) + "," + str(value['longitude'])
            print "Loaded " + str(len(pokestops_farms)) + " farms!"

        # Delete pokestops
        elif (choice == 3):
            pokestops_farms = {}
            pokefarm_save()
            print "Deleted."

        # Search & save
        elif (choice == 4):
            timestamp = "\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000"
            cellid = get_cellid(position[0], position[1])
            api.get_map_objects(latitude=f2i(position[0]), longitude=f2i(position[1]), since_timestamp_ms=timestamp, cell_id=cellid)
            response_dict = api.call()
            parse_getmapobjects_response(response_dict)
            # print('Response dictionary: \n\r{}'.format(json.dumps(response_dict, indent=2)))

            
            print "Found " + str(len(pokestops_farms)) + " farms!"

        # Start pokestop farming
        elif (choice == 5):
            if (len(pokestops_farms)) < 1:
                print "No pokestops! Load or search for them."
                continue
            print "Starting to farm pokestops"
            old_position = position
            for pokeid, pokestop in pokestops_farms.iteritems():
                lat = pokestop['latitude']
                lng = pokestop['longitude']
                dlat = position[0] - lat
                dlng = position[1] - lng
                api.set_position(*(lat, lng, 0.0))
                api.fort_search(fort_id=pokeid, fort_latitude=lat, fort_longitude=lng, player_latitude=f2i(lat), player_longitude=f2i(lng))
                response = api.call()
                try:
                    fort_search_response = response['responses']['FORT_SEARCH']
                    result = int(fort_search_response['result'])
                    # Pokestop farmed
                    if result == 1:
                        experience = fort_search_response['experience_awarded']
                        cooldown = fort_search_response['cooldown_complete_timestamp_ms']
                        print "Pokestop farmed! +" + str(experience) + " XP - id: " + pokeid
                    # Already farmed
                    elif result == 3:
                        print "Pokestop already farmed, must wait - id: " + pokeid

                    # Unknow error
                    else:
                        print "Pokestop error: " + str(result) + " - id:" + pokeid
                except:
                    print "Pokestop error: \r\n{}\r\n".format(json.dumps(response,indent=2))
                    break
                time.sleep(5)
            api.set_position(*old_position)
    
    # execute the RPC call

if __name__ == '__main__':
    main()

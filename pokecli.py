
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

import threading

from weakpokemons import *


log = logging.getLogger(__name__)

pokestops_filename = "pokestops.json"
pokestops = []

class nabbadict(dict):
    def __hash__(self):
        return hash(tuple(sorted(self.items())))
    

def pokefarm_load():
    global pokestops
    try:
        print "pokefarm_load == Loading pokestops from file.."
        f = open(pokestops_filename, 'r')
        pokestops_dict = json.loads(f.read())
        pokestops = pokestops_dict['pokestops']
        f.close()
    except:
        print "pokefarm_load == Can't load pokestops from file."

def pokefarm_save():
    global pokestops
    print 'Saving pokestops'
    pk_json = json.dumps({"pokestops": pokestops})
    f = open(pokestops_filename, 'wb')
    f.write(pk_json);
    f.close()

def parse_getmapobjects_response(obj):
    global pokestops
    # pokefarm_load()
    # print obj
    status = obj['responses']['GET_MAP_OBJECTS']['status']

    if status == 1:
        cells = obj['responses']['GET_MAP_OBJECTS']['map_cells']
        for i in cells:
            if not 'forts' in i:
                continue
            for k in i['forts']:
                if 'gym_points' in k:
                    continue
                k = nabbadict(k)
                if k in pokestops:
                    continue
                print "Pokestop at " + str(k['longitude']) + "," + str(k['latitude']),
                print " id: " + k['id']
                pokestops.append(k)
    pokefarm_save()
    


def get_pos_by_name(location_name):
    geolocator = GoogleV3()
    try:
        loc = geolocator.geocode(location_name)        
        log.info('Your given location: %s', loc.address.encode('utf-8'))
        log.info('lat/long/alt: %s %s %s', loc.latitude, loc.longitude, loc.altitude)
        return (loc.latitude, loc.longitude, loc.altitude)
    except:
        log.error("Can't get position, quitting")
        return (37.5, 15.0, 0.0)
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
    coord1 = LatLng.from_degrees(lat1, lng1)
    coord2 = LatLng.from_degrees(lat2, lng2)
    angle = coord1.get_distance(coord2)
    return angle.radians
def angle_to_meters(angle):
    return angle * 6371e3

def walk(api, position):
    timestamp = "\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000"
    cellid = get_cellid(position[0], position[1])
    api.get_map_objects(latitude=f2i(position[0]), longitude=f2i(position[1]), since_timestamp_ms=timestamp, cell_id=cellid)
    return api.call()

def pokestop_sort(a, b):
    a_dist = angle_to_meters(distance_by_points(position[0], position[1], a['latitude'], a['longitude']))
    b_dist = angle_to_meters(distance_by_points(position[0], position[1], b['latitude'], b['longitude']))
    return int(a_dist - b_dist)

def pokefarm_thread(api):
    global position
    if (len(pokestops)) < 1:
        print "No pokestops! Load or search for them."
        return
    
    pokestops.sort(pokestop_sort)
    
    print "Starting to farm pokestops"

    first_stop = 0

    for pokestop in pokestops:
        if first_stop > 0:
            now = time.time()
            seconds = int(now-first_stop)
            print "Time passed: " + str(now-first_stop)
        pokestop['visited'] = True
        pokeid = pokestop['id']
        lat = pokestop['latitude']
        lng = pokestop['longitude']
        
        o = distance_by_points(lat, lng, position[0], position[1])
        v = 5
        p = 3
        w = v * p / 6371e3
        nstep = int(o / w)
        dlat = abs(lat-position[0])
        dlng = abs(lng-position[1])
        plat = o / dlat
        plng = o / dlng
        slat = w / plat
        slng = w / plng
        blat = position[0]
        blng = position[1]
        for i in range(1, nstep):
            print "current step: " + str(i) + " / " + str(nstep)
            nlat = blat + (i * slat)
            nlng = blng + (i * slng)
            print "Moved to " + str(nlat) + "," + str(nlng)
            walk(api, (nlat, nlng, 0.0))
            time.sleep(p)

        # final step is pokestop
        position = (lat, lng, 0.0)
        api.set_position(*position)
        
        api.fort_search(fort_id=pokeid, fort_latitude=lat, fort_longitude=lng, player_latitude=f2i(lat), player_longitude=f2i(lng))
        response = api.call()
        try:
            fort_search_response = response['responses']['FORT_SEARCH']
            result = int(fort_search_response['result'])
            # Pokestop farmed
            if result == 1:
                try:
                    experience = fort_search_response['experience_awarded']
                except:
                    experience = "(ERROR)"
                #cooldown = fort_search_response['cooldown_complete_timestamp_ms']
                if first_stop == 0:
                    first_stop = time.time()
                    print "First pokestop at: " + str(first_stop)
                print "Pokestop farmed! +" + str(experience) + " XP - id: " + pokeid
            # Too far
            elif result == 2:
                print "Pokestop too far! - id: " + pokeid
            # Already farmed
            elif result == 3:
                print "Pokestop already farmed, must wait - id: " + pokeid
            # Bag full
            elif result == 4:
                print "Your bag is full! - id: " + pokeid

            # Unknow error
            else:
                print "Pokestop error: " + str(result) + " - id:" + pokeid
        except:
            print "Pokestop error: \r\n{}\r\n".format(json.dumps(response,indent=2))
            continue
        time.sleep(2)

position = ()

def main():
    global position
    global pokestops
    running = True
    
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("pgoapi").setLevel(logging.WARNING)
    logging.getLogger("rpc_api").setLevel(logging.WARNING)

    print "Checking configuration..."
    config = init_config()
    if not config:
        return

    if config.debug:
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("rpc_api").setLevel(logging.DEBUG)

    print "Getting position..."
    position = get_pos_by_name(config.location)

    print "Loading pokedex..."
    fpokedex = open('pokedex.json', 'rb')
    pokedex = json.loads(fpokedex.read())
    fpokedex.close()

    # instantiate pgoapi 
    api = PGoApi()
    
    # provide player position on the earth
    api.set_position(*position)

    print "Logging in..."
    if not api.login(config.auth_service, config.username, config.password):
        return


    while running:
        print "\r\n\r\n\r\n - What you want to do?"
        print " 1. Move (current location is:",
        print position,
        print ")"
        print " 2. Show & load pokestop"
        print " 3. Delete loaded pokestop"
        print " 4. Search & save pokestop"
        print " 5. Start pokestop farming"
        print " 6. Get player info"
        print " 7. Get inventory"
        print " 8. Free weak pokemons"
        print " 0. Quit"

        try:
            choice = input(" --> ")
        except:
            continue
        if (choice == 0): running = False

        # Move
        if (choice == 1):
            lat = float(raw_input(" -- Input new latitude: (0 to cancel): "))
            if (lat == 0): continue
            lng = float(raw_input(" -- Input new longitude: (0 to cancel): "))
            if (lng == 0): continue
            sure = raw_input(" -- Are you sure (y/n)? ")
            if (sure == "y"):
                position = (lat, lng, 0.0)
                api.set_position(*position)

        # Show & Load pokestops
        elif (choice == 2):
            pokefarm_load()
            for pokestop in pokestops:
                print pokestop['id'] + " at " + str(pokestop['latitude']) + "," + str(pokestop['longitude'])
            print "Loaded " + str(len(pokestops)) + " farms!"

        # Delete pokestops
        elif (choice == 3):
            pokestops = []
            pokefarm_save()
            print "Deleted."

        # Search & save
        elif (choice == 4):
            timestamp = "\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000"
            cellid = get_cellid(position[0], position[1])
            api.get_map_objects(latitude=f2i(position[0]), longitude=f2i(position[1]), since_timestamp_ms=timestamp, cell_id=cellid)
            response_dict = api.call()
            parse_getmapobjects_response(response_dict)            
            print "Found " + str(len(pokestops)) + " farms!"

        # Start pokestop farming
        elif (choice == 5):
            #t = threading.Thread(target=pokefarm_thread, args=(api,))
            #t.daemon = True
            #t.start()
            pokefarm_thread(api)


        # Player info
        elif (choice == 6):
            api.get_player()
            response = api.call()
            print response

        # Inventory
        elif (choice == 7):
            api.get_inventory()
            response = api.call()
            file_inventory = open ("inventory.json", 'wb')
            file_inventory.write(json.dumps(response))
            file_inventory.close()
            print "Written to inventory.json"

        elif (choice == 8):
            api.get_inventory()
            inventory = api.call()
            shouldfree = parse_inventory_for_weak_pokemon(inventory)
            print "There are " + str(len(shouldfree)) + " pokemon to release"
            released = 0
            for i in shouldfree:
                name = pokedex[str(i['pid'])]
                print "(" + str(released) + "/" + str(len(shouldfree)) + ") Releasing " + name + " with CP: " + str(i['cp']) + " (" + str(i['id']) + ")",
                api.release_pokemon(pokemon_id=i['id'])
                response = api.call()
                try:
                    candies = response['responses']['RELEASE_POKEMON']['candy_awarded']
                    print "got " + str(candies) + " candies"
                except:
                    print " - unknow error"
                released += 1
                time.sleep(1)

    
if __name__ == '__main__':
    main()

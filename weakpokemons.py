import json

def parse_inventory_for_weak_pokemon(data):
    if not 'responses' in data:
        print "responses not found"
        return -1
    if not 'GET_INVENTORY' in data['responses']:
        print "GET_INVENTORY not found"
        return -1

    item_inventory = data['responses']['GET_INVENTORY']['inventory_delta']['inventory_items']

    pokemon_dict = {}

    should_free_ids = []

    for item in item_inventory:
        if 'pokemon' in item['inventory_item_data']:
            pokemon = item['inventory_item_data']['pokemon']
            if 'is_egg' in pokemon:
                continue
            cp = str(pokemon['cp'])
            #name = pokedex[str(pokemon['pokemon_id'])]
            pid = pokemon['pokemon_id']
            
            if not pid in pokemon_dict:
                #print "first " + name + " with " + cp
                pokemon_dict[pid] = {'id': pokemon['id'], 'cp': cp}
            else:
                old_poke = pokemon_dict[pid]
                old_cp = old_poke['cp']
                if int(cp) <= int(old_cp):
                    #print "should free " + name + " with cp " + cp
                    should_free_ids.append({'id': pokemon['id'], 'cp': cp, 'pid': pid})
                else:
                    #print "should free old " + name + " with " + str(old_cp) + ", new is " + cp
                    should_free_ids.append({'id': old_poke['id'], 'cp': old_cp, 'pid': pid})
                    pokemon_dict[pid] = {'id': pokemon['id'], 'cp': cp}

    return should_free_ids


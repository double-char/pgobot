import json

def load_pokedex():
    fpokedex = open('pokedex.json', 'rb')
    pokedex = json.loads(fpokedex.read())
    fpokedex.close()
    return pokedex

def get_catchable_pokemons(api_result):
    map_objects = api_result['responses']['GET_MAP_OBJECTS']['map_cells']
    res_catchable = []
    pokedex = load_pokedex()

    for cell in map_objects:
        #if 'nearby_pokemons' in cell: print "Cell id",cell['s2_cell_id']
        if 'catchable_pokemons' in cell:
            print "Catchable pokemons: "
            catchable = cell['catchable_pokemons']
            for pokemon in catchable:
                print "\t",pokedex[str(pokemon['pokemon_id'])]
                res_catchable.append(pokemon)
        """
        if 'nearby_pokemons' in cell:
            #print "Nearby pokemons: "
            nearby = cell['nearby_pokemons']
            for pokemon  in nearby:
                pass
                #print "\t",pokedex[str(pokemon['pokemon_id'])]
        """
    return res_catchable


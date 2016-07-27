from geopy.geocoders import GoogleV3
from s2sphere import CellId, LatLng
from google.protobuf.internal import encoder

def get_pos_by_name(location_name):
    return (37.509470, 15.082904, 0.0)
    geolocator = GoogleV3()
    try:
        loc = geolocator.geocode(location_name)        
        print('Your given location: %s', loc.address.encode('utf-8'))
        print('lat/long/alt: %s %s %s', loc.latitude, loc.longitude, loc.altitude)
        return (loc.latitude, loc.longitude, loc.altitude)
    except:
        print("Can't get position, quitting")
        exit()
        
        

def get_cell_ids(lat, long, radius = 10):
    origin = CellId.from_lat_lng(LatLng.from_degrees(lat, long)).parent(15)
    walk = [origin.id()]
    right = origin.next()
    left = origin.prev()

    # Search around provided radius
    for i in range(radius):
        walk.append(right.id())
        walk.append(left.id())
        right = right.next()
        left = left.prev()

    # Return everything
    return sorted(walk)

def encode(cellid):
    output = []
    encoder._VarintEncoder()(output.append, cellid)
    return ''.join(output)

def distance_by_points(lat1, lng1, lat2, lng2):
    coord1 = LatLng.from_degrees(lat1, lng1)
    coord2 = LatLng.from_degrees(lat2, lng2)
    angle = coord1.get_distance(coord2)
    return angle.radians

def angle_to_meters(angle):
    return angle * 6371e3

import osmnx as ox

TAGS = {
    "alcohol": {"shop": ["alcohol"]},
    "bakery": {"shop": ["bakery"]},
    "coffee": {"shop": ["coffee"]},
    "food": {"shop": ["food"]},
    "general": {"shop": ["general"]},
    "supermarket": {"shop": ["supermarket"]},
    "mall": {"shop": ["mall"]},

    "restaurant": {"amenity": ["restaurant"]},
    "cafe": {"amenity": ["cafe"]},
    "bar": {"amenity": ["bar"]},
    "university": {"amenity": ["university"]},
    "library": {"amenity": ["library"]},
    "school": {"amenity": ["school"]},
    "college": {"amenity": ["college"]},
    "cinema": {"amenity": ["cinema"]},
    "nightclub": {"amenity": ["nightclub"]},
    "theatre": {"amenity": ["theatre"]},

    "beach_resort": {"leisure": ["beach_resort"]},
    "dog_park": {"leisure": ["dog_park"]},
    "fitness_centre": {"leisure": ["fitness_centre"]},
    "fitness_station": {"leisure": ["fitness_station"]},
    "garden": {"leisure": ["garden"]},
    "park": {"leisure": ["park"]},
    "playground": {"leisure": ["playground"]},
    "stadium": {"leisure": ["stadium"]},
    "swimming_pool": {"leisure": ["swimming_pool"]},

    "stop_position": {"public_transport": ["stop_position"]},
    "station": {"public_transport": ["station"], "railway": ["station"]},
    "platform": {"public_transport": ["platform"]},
    "halt": {"railway": ["halt"]},
    "tram_stop": {"railway": ["tram_stop"]},
    "subway_entrance": {"railway": ["subway_entrance"]},
}


def osm_api(address, request, radius, *targets):
    if request == 'route':
        graph = ox.graph_from_address(address, dist=radius, network_type='walk')
        return ox.graph_to_gdfs(graph, nodes=False, edges=True)
    elif request == 'start':
        points = ox.features_from_address(address, tags={'building': True}, dist=radius - 250)
        return points
    elif request == 'targets':
        targets_list = []
        for tag in targets:
            try:
                targets_list += [ox.features_from_address(address, tags=TAGS[tag], dist=radius)]
            except ox._errors.InsufficientResponseError:
                continue
        return targets_list

    raise ValueError(f"Invalid request type: {request}")

import osmnx as ox


def osm_api(address, request, radius, *targets):

    if request == 'route':
        graph = ox.graph_from_address(address, dist=radius, network_type='walk')
        return ox.graph_to_gdfs(graph, nodes=False, edges=True)
    elif request == 'start':
        points = ox.features_from_address(address, tags={'building': True}, dist=radius-500)
        return points
    elif request == 'targets':
        tags = {
            "shop": {"shop": ["alcohol", "bakery", "coffee", "food", "general", "supermarket", "mall"]} ,
            "amenity": {"amenity": ["restaurant", "cafe", "bar", "university", "library", "school", "college", "cinema", "nightclub", "theatre"]},
            "leisure": {"leisure": ["beach_resort", "dog_park", "fitness_centre", "fitness_station", "garden", "park", "playground", "stadium", "swimming_pool"]},
            "public_transport": {"public_transport": ["stop_position", "station", "platform"], "railway": ["station", "halt", "tram_stop", "subway_entrance"]},
        }
        return [ox.features_from_address(address, tags=tags[tag], dist=radius) for tag in targets]

    raise ValueError(f"Invalid request type: {request}")


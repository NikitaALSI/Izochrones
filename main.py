import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry.linestring import LineString
from shapely.ops import unary_union, split
import networkx as nx
import osmnx as ox
import momepy
from scipy.spatial import KDTree


def validate_crs(gdf):
    if not gdf.crs:
        gdf = gdf.set_crs(epsg=4326)
        gdf = gdf.to_crs(gdf.estimate_utm_crs())
    else:
        if gdf.crs.is_geographic:
            gdf = gdf.to_crs(epsg=4326)
            gdf = gdf.to_crs(gdf.estimate_utm_crs())

    return gdf.crs


def get_centroids(gdf):
    crs = validate_crs(gdf)

    gdf = gdf.to_crs(crs)

    gdf['shape_centroid'] = gdf.geometry.centroid

    return gdf


def preprocess_route(route):
    crs = validate_crs(route)

    route = route.to_crs(crs)

    segmented = unary_union(route.geometry)
    segmented = shapely.get_parts(segmented)

    segments = []
    for line in segmented:
        coords = list(line.coords)
        for i in range(len(coords) - 1):
            segments.append(shapely.geometry.LineString([coords[i], coords[i + 1]]))

    return gpd.GeoDataFrame(geometry=segments, crs=crs)


def extend_route_to_centroids(route, objects):
    crs = validate_crs(route)

    route = route.to_crs(crs)
    objects = objects.to_crs(crs)

    _ = route.sindex
    _ = objects.sindex

    snapped = gpd.sjoin_nearest(get_centroids(objects),
                                    route,
                                    how='left')[['shape_centroid', 'index_right']].drop_duplicates(subset='shape_centroid')
    snapped = snapped.merge(route[['geometry']], left_on='index_right', right_index=True)
    snapped['start_line'] = snapped['geometry'].interpolate(snapped['geometry'].project(snapped['shape_centroid']))

    new_geometries = [LineString([pt1, pt2]) for pt1, pt2 in zip(snapped['start_line'], snapped['shape_centroid'])]
    new_gdf = gpd.GeoDataFrame(geometry=new_geometries, crs=crs)

    return pd.concat([route, new_gdf], ignore_index=True)


def create_isochrones(graph, starting_point, distance, spatial_index, node_ids):
    _, min_idx = spatial_index.query([starting_point.x, starting_point.y])
    nearest_node = node_ids[min_idx]

    isochrone = nx.ego_graph(graph, nearest_node, radius=distance, distance='length', undirected=True)
    isochrone = ox.graph_to_gdfs(isochrone, nodes=False, edges=True)

    return isochrone


def isochrone_target_intersection(isochrone, start):
    isochrone = isochrone.to_crs(validate_crs(start))
    isochrone_buffered = isochrone.geometry.buffer(10).union_all()
    mask = start.geometry.centroid.within(isochrone_buffered)
    start.loc[mask, 'accessibility'] += 1

    return start


def accessibility_analysis(start, route, distance, *targets):
    crs = validate_crs(route)
    route = route.to_crs(crs)
    route = preprocess_route(route)
    route = extend_route_to_centroids(route, start)
    route = preprocess_route(route)

    for target in targets:
        target = target.to_crs(crs)
        route = extend_route_to_centroids(route, target)
    route = preprocess_route(route)
    start = start.to_crs(crs)
    start = get_centroids(start)
    start['accessibility'] = 0

    route = momepy.gdf_to_nx(route, approach='primal', length='length', directed=True)
    print('Preprocessing route finished!')
    node_ids = list(route.nodes)
    node_coords = [node for node in node_ids]
    spatial_index = KDTree(node_coords)

    for i, target in enumerate(targets):
        target_isochrones = []
        for j, start_point in enumerate(target.centroid):
            target_isochrones.append(create_isochrones(route, start_point, distance, spatial_index, node_ids))
            print(f'Target {i + 1} isochrone {j+1}|{len(target)} created!')
        target_isochrone = gpd.GeoDataFrame(pd.concat(target_isochrones, ignore_index=True), crs=crs)
        start = isochrone_target_intersection(target_isochrone, start)
        print(f'Target {i + 1} finished!')
    print('All targets finished!')
    return start


if __name__ == '__main__':
    route_osm_graph = ox.graph_from_address('Sofia, Bulgaria', dist=1000, network_type='walk')
    points = ox.features_from_address('Sofia, Bulgaria', tags={'building': True}, dist=1000)
    route_osm = ox.graph_to_gdfs(route_osm_graph, nodes=False, edges=True).to_crs(validate_crs(points))

    start = accessibility_analysis(points[points['building'].isin(['apartments'])], route_osm, 800, points[points['building'].isin(['school', 'university', 'kindergarten'])])
    print(start['accessibility'].sum())
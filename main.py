
import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry.linestring import LineString
from shapely.ops import unary_union, split
import networkx as nx
import osmnx as ox
import momepy
import matplotlib.pyplot as plt
import contextily as cx
from scipy.spatial import KDTree


def validate_crs(gdf):
    if gdf.crs.is_geographic:
        gdf = gdf.to_crs(epsg=4326)
        gdf = gdf.to_crs(gdf.estimate_utm_crs())
    if not gdf.crs:
        gdf = gdf.set_crs(epsg=4326)
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

    segmented_lines = unary_union(route.geometry)
    segmented_lines = shapely.get_parts(segmented_lines)
    segments = []
    for line in segmented_lines:
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

    gdf_snapped = gpd.sjoin_nearest(get_centroids(objects), route, how='left')[['shape_centroid', 'index_right']].drop_duplicates(subset='shape_centroid')
    gdf_snapped = gdf_snapped.merge(route[['geometry']], left_on='index_right', right_index=True)
    gdf_snapped['start_line'] = gdf_snapped['geometry'].interpolate(gdf_snapped['geometry'].project(gdf_snapped['shape_centroid']))
    new_geometries = [LineString([pt1, pt2]) for pt1, pt2 in zip(gdf_snapped['start_line'], gdf_snapped['shape_centroid'])]
    new_gdf = gpd.GeoDataFrame(geometry=new_geometries, crs=crs)
    return pd.concat([route, new_gdf], ignore_index=True)


def create_isochrones(graph, starting_point, distance, spatial_index, node_ids):
    _, min_idx = spatial_index.query([starting_point.x, starting_point.y])
    nearest_node = node_ids[min_idx]

    isochrone = nx.ego_graph(graph, nearest_node, radius=distance, distance='length', undirected=True)
    isochrone = ox.graph_to_gdfs(isochrone, nodes=False, edges=True)

    return isochrone


def isochrone_target_intersection(isochrone, *targets):
    crs = validate_crs(isochrone)

    isochrone_buffered = isochrone.buffer(10).union_all()

    count = 0
    for target in targets:
        target = target.to_crs(crs)
        _ = target.sindex
        joined = target[target.geometry.centroid.within(isochrone_buffered)]
        print(joined.shape)
        if joined.shape[0] != 0:
            count += 1

    return count


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
    start = get_centroids(start)
    start = start.to_crs(crs)

    route = momepy.gdf_to_nx(route, approach='primal', length='length', directed=True)

    node_ids = list(route.nodes)
    node_coords = [node for node in node_ids]
    spatial_index = KDTree(node_coords)
    start['accessibility'] = start.apply(lambda row: isochrone_target_intersection(create_isochrones(route, row['shape_centroid'], distance, spatial_index, node_ids), *targets), axis=1)
    return start

import geopandas as gpd
import pandas as pd
import shapely
import networkx as nx
import osmnx as ox
import momepy
from shapely.geometry.linestring import LineString
from shapely.ops import unary_union, split


def validate_crs(gdf):
    if gdf.crs.is_geographic:
        gdf = gdf.to_crs(epsg=4326)
        return gdf.to_crs(gdf.estimate_utm_crs())
    return gdf


def get_centroids(gdf):
    gdf = validate_crs(gdf)
    gdf['shape_centroid'] = gdf.geometry.centroid
    return gdf


def preprocess_route(gdf_polylines):
    gdf_polylines = validate_crs(gdf_polylines)

    segmented_lines = unary_union(gdf_polylines.geometry)
    segmented_lines = shapely.get_parts(segmented_lines)
    segments = []
    for line in segmented_lines:
        coords = list(line.coords)
        for i in range(len(coords) - 1):
            segments.append(shapely.geometry.LineString([coords[i], coords[i + 1]]))

    return gpd.GeoDataFrame(geometry=segments, crs=gdf_polylines.crs)


def extend_route_to_centroids(gdf_polylines, gdf):
    gdf_polylines = validate_crs(gdf_polylines.to_crs(gdf.crs))
    gdf = get_centroids(validate_crs(gdf))

    gdf_snapped = gpd.sjoin_nearest(gdf, gdf_polylines, how='left')[['shape_centroid', 'index_right']]
    gdf_snapped = gdf_snapped.drop_duplicates(subset='shape_centroid')
    gdf_snapped = gdf_snapped.merge(gdf_polylines[['geometry']], left_on='index_right', right_index=True)
    gdf_snapped['start_line'] = gdf_snapped['geometry'].interpolate(
        gdf_snapped['geometry'].project(gdf_snapped['shape_centroid']))

    new_rows = []
    for row in gdf_snapped.iloc:
        new_rows.append({'geometry': LineString([row['start_line'], row['shape_centroid']])})
    new_gdf = gpd.GeoDataFrame(new_rows, crs=gdf_polylines.crs)
    return pd.concat([gdf_polylines, new_gdf], ignore_index=True)


def create_isochrones(network, starting_point, distance):
    if isinstance(network, gpd.GeoDataFrame):
        network = momepy.gdf_to_nx(network, approach='primal', length='length', directed=True)
        nearest_node = min(network.nodes, key=lambda node: starting_point.distance(shapely.geometry.Point(node)))
    else:
        nearest_node = ox.nearest_nodes(G=network, X=[starting_point.x], Y=[starting_point.y])[0]

    isochrone = nx.ego_graph(network, nearest_node, radius=distance, distance='length', undirected=True)
    isochrone = ox.graph_to_gdfs(isochrone, nodes=False, edges=True)
    isochrone = validate_crs(isochrone)
    return isochrone


def isochrone_target_intersection(isochrone, *targets):
    isochrone_buffered = isochrone.buffer(10).union_all()
    count = 0
    for target in targets:
        joined = gpd.sjoin(gpd.GeoDataFrame(geometry=[isochrone_buffered], crs=target.crs), target, how='inner',
                           predicate='intersects')
        if len(joined) > 0:
            count += 1

    return count


def accessibility_analysis(start, route, *targets, distance):
    route = preprocess_route(route)
    route = extend_route_to_centroids(route, start)
    route = preprocess_route(route)
    for target in targets:
        route = extend_route_to_centroids(route, target)

    start = get_centroids(start)
    start['accessibility'] = start.apply(
        lambda row: isochrone_target_intersection(create_isochrones(route, row['shape_centroid'], distance), *targets),
        axis=1)
    return start

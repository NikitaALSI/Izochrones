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


def preprocess_route(gdf):
    gdf = validate_crs(gdf)

    segmented_lines = unary_union(gdf.geometry)
    segmented_lines = shapely.get_parts(segmented_lines)
    segments = []
    for line in segmented_lines:
        coords = list(line.coords)
        for i in range(len(coords) - 1):
            segments.append(shapely.geometry.LineString([coords[i], coords[i + 1]]))

    return gpd.GeoDataFrame(geometry=segments, crs=gdf.crs)


def extend_route_to_centroids(route, gdf):
    route = validate_crs(route.to_crs(gdf.crs))
    gdf = get_centroids(validate_crs(gdf))

    joined = gpd.sjoin_nearest(gdf, route, how='left')[['shape_centroid', 'index_right']]
    joined = joined.drop_duplicates(subset='shape_centroid')
    joined = joined.merge(route[['geometry']], left_on='index_right', right_index=True)
    joined['start_line'] = joined['geometry'].interpolate(joined['geometry'].project(joined['shape_centroid']))

    new_rows = []
    for row in joined.iloc:
        new_rows.append({'geometry': LineString([row['start_line'], row['shape_centroid']])})
    new_gdf = gpd.GeoDataFrame(new_rows, crs=route.crs)
    return pd.concat([route, new_gdf], ignore_index=True)


def create_isochrones(route, start, distance):
    if isinstance(route, gpd.GeoDataFrame):
        route = momepy.gdf_to_nx(route, approach='primal', length='length', directed=True)
        nearest_node = min(route.nodes, key=lambda node: start.distance(shapely.geometry.Point(node)))
    else:
        nearest_node = ox.nearest_nodes(G=route, X=[start.x], Y=[start.y])[0]

    isochrone = nx.ego_graph(route, nearest_node, radius=distance, distance='length', undirected=True)
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

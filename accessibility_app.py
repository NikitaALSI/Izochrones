import streamlit as st
import folium
from streamlit_folium import folium_static
import geopandas as gpd
import matplotlib as mlp
import matplotlib.colors as mcolors
import branca

from main import accessibility_analysis
from osm_api import osm_api, TAGS


def generate_data():
    _route = gpd.read_file(route) if route else osm_api(route_address, 'route', route_address_radius)
    _start = gpd.read_file(start) if start else osm_api(route_address, 'start', route_address_radius)
    _targets = [gpd.read_file(_target) for _target in targets] + osm_api(route_address, 'targets', route_address_radius,
                                                                         *targets_choice)
    return accessibility_analysis(_start,
                                  _route,
                                  minutes * 80,
                                  *_targets)  # gpd.read_file("Generated_Maps/sofia.geojson")


def create_map(data):
    data = data[['geometry', "accessibility"]]
    bins = list(range(max(4, data.accessibility.max() + 1)))
    n = len(bins)

    cmap = mlp.colormaps['YlOrRd'].resampled(n)
    colors = [mcolors.to_hex(cmap(i)) for i in range(n)]
    value_to_color = dict(zip(bins, colors))

    def style_function(feature):
        value = feature['properties']['accessibility']
        return {
            'fillColor': value_to_color.get(value, '#EEEEEE'),
            'color': 'white',
            'weight': 0.3,
            'fillOpacity': 0.75,
        }

    m = folium.Map(tiles="CartoDB.Positron",
                   zoom_start=17)

    ch = folium.GeoJson(data,
                        style_function=style_function,
                        tooltip=folium.GeoJsonTooltip(fields=["accessibility"])
                        ).add_to(m)
    bounds = ch.get_bounds()
    m.fit_bounds(bounds)

    colormap = branca.colormap.linear.YlOrRd_09.scale(0, n)
    colormap = colormap.to_step(index=bins)
    colormap.add_to(m)

    with m_col3:
        st.space("small")
        folium_static(m, width=1040, height=820)
    st.download_button("Download Map", data=data.to_json(), file_name=f"accessibility_map.geojson")


st.set_page_config(layout="wide",
                   page_title="Accessibility Analysis", )

m_col1, m_col2, m_col3 = st.columns([20, 2, 30])

sb = st.sidebar
with sb:
    st.title(":red[Accessibility Analysis]")

    st.markdown(
        """
        This is a comprehensive analysis of the **15-minute city** concept, but extend to any form of network and POI (points of interest)
        The idea behind is that a specialist can use that form of analysis to generate map of accessibility to target object in any 2D space, be it:
        
         * an apartment's floorplan
         * an hospitals's floorplan
         * park
         * public transport schema
         * *and may more*
         """)

    st.header("Pre-loved maps", divider='rainbow')
    st.markdown(
        """
        1. **Sofia, Bulgaria** 
        
        `15 min / All`
        
        2. **London, England** 
        
        `10 min / Schools`
        
        3. **Sofia, Bulgaria** 
        
        `10 min / Malls, Shops, Restaurants`
        """)
    pre_loved_maps = {
        "1": gpd.read_file("Generated_Maps/sofia.geojson"),
        "2": gpd.read_file("Generated_Maps/london.geojson"),
        # "3": gpd.read_file("Generated_Maps/sofia_malls_shops_restaurants.geojson")
    }
    pre_loved_map_choice = st.selectbox(label="Choose Pre-loved map",
                                          options=["None", "1", "2", "3"])
    load_btn = st.button("Load Pre-loved map", disabled=pre_loved_map_choice == "None")
    if load_btn:
        create_map(pre_loved_maps[pre_loved_map_choice])

with m_col1:
    st.header("The network", divider='yellow')
    st.markdown("""*This is the route based on which the accessibility will be calculated.*""")
    st.space()
    col1, col2 = st.columns(2)
    with col1:
        route = st.file_uploader("**Upload polylines**", type=["gpkg", "geojson", "shp"])
        st.write("*\\*the polylines must meet exactly, otherwise the network will not produce valid results*")
    with col2:
        route_address = st.text_input("Write address to use as a network and bound of analysis",
                                      disabled=bool(route),
                                      value=('' if route else ''))
        st.write("*\\*the address will be the boundary of the analysis, if provided*")
        route_address_radius = st.number_input("Specify the distance radius in kilometers for the analysis",
                                               max_value=2500,
                                               value=500,
                                               disabled=bool(route), )

    st.header("Points of interest (POI)", divider='orange')
    st.markdown("""*This are the starting points from which the accessibility will be calculated.*""")
    st.space()
    col1, col2 = st.columns(2)
    with col1:
        start = st.file_uploader("Upload POIs", type=["gpkg", "geojson", "shp"])
    with col2:
        start_address = st.checkbox("Use buildings in the range of network",
                                    disabled=bool(start),
                                    value=not bool(start))

    st.header("Targets", divider='red')
    st.markdown("""*This are the target objects which the accessibility is aimed at.*""")
    st.space()
    col1, col2 = st.columns(2)
    with col1:
        targets = st.file_uploader("Upload target", type=["gpkg", "geojson", "shp"], accept_multiple_files=True)
    with col2:
        targets_choice = st.multiselect(label="Select targets to use as targets",
                                        options=TAGS.keys())
        st.write("*\\*the amenities will be the collected for the boundaries of the network*")

    minutes = st.slider("Select walking distance in minutes for analysis", min_value=5, max_value=30, value=10)


    if "generate_map" not in st.session_state:
        st.session_state.generate_map = False

    if st.button("**Generate map**",
             type="primary",
             width="stretch",
             disabled=not all([bool(route or route_address),
                               bool(start or start_address),
                               bool(targets or targets_choice)])):
        st.session_state.generate_map = True

    if st.session_state.generate_map:
        with st.spinner():
            data = generate_data()
            create_map(data)

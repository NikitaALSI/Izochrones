import streamlit as st

# from main import accessibility_analysis


st.title(":orange[Accessibility Analysis]")

st.markdown(
    """
    This is a comprehensive analysis of the **15-minute city** concept, but extend to any form of network and POI (points of interest)
    The idea behind is that a specialist can use that form of analysis to generate map of accessibility to target object in any 2D space, be it:
    
     * an apartment's floorplan
     * an apartment's floorplan
     * park
     * public transport schema
     * *and may more*
     """)

st.header("The network", divider='orange')
st.markdown("""*This is the route based on which the accessibility will be calculated.*""")
st.space()
col1, col2 = st.columns(2)
with col1:
    route = st.file_uploader("**Upload polylines**", type=["gpkg", "geojson", "shp"])
    st.write("*\*the polylines must meet exactly, otherwise the network will not produce valid results*")
with col2:
    route_address = st.text_input("Write address to use as a network and bound of analysis", disabled=bool(route), value=('' if route else ''))
    st.write("*\*the address will be the boundary of the analysis, if provided*")

st.header("Points of interest (POI)", divider='orange')
st.markdown("""*This are the starting points from which the accessibility will be calculated.*""")
st.space()
col1, col2 = st.columns(2)
with col1:
    start = st.file_uploader("Upload POIs", type=["gpkg", "geojson", "shp"])
with col2:
    start_address = st.checkbox("Use buildings in the range of network", disabled=bool(start), value=not bool(start))

st.header("Targets", divider='orange')
st.markdown("""*This are the target objects which the accessibility is aimed at.*""")
st.space()
col1, col2 = st.columns(2)
with col1:
    targets = st.file_uploader("Upload target", type=["gpkg", "geojson", "shp"], accept_multiple_files=True)
with col2:
    targets_choice = st.multiselect(label="Select amenities to use as targets", options=["school", "hospital", "supermarket", "park", "restaurant"])
    st.write("*\*the amenities will be the collected for the boundaries of the network*")


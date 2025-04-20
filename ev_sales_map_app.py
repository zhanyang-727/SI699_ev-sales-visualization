import geopandas as gpd
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.features import GeoJsonTooltip
import altair as alt
from vega_datasets import data
import warnings

st.set_page_config(layout="wide")

# Suppress deprecation warnings for cleaner output
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- Load your sales data ---
try:
    df = pd.read_csv('final_dataset.csv')
    st.success("Data loaded successfully")
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Clean and convert key columns
df['STATE'] = df['STATE'].str.strip()
df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
df['Gasoline_Price'] = pd.to_numeric(df['Gasoline_Price'], errors='coerce')
df['Electric (EV)'] = pd.to_numeric(df['Electric (EV)'], errors='coerce')
df['Plug-In Hybrid Electric (PHEV)'] = pd.to_numeric(df['Plug-In Hybrid Electric (PHEV)'], errors='coerce')
df['Hybrid Electric (HEV)'] = pd.to_numeric(df['Hybrid Electric (HEV)'], errors='coerce')

# Exclude Alaska, Hawaii, Puerto Rico for the folium map
exclude_states = ['Alaska', 'Hawaii', 'Puerto Rico']
df_continental = df[~df['STATE'].isin(exclude_states)]

# State abbreviations
state_abbrev = {
    'Alabama': 'AL', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL',
    'Georgia': 'GA', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME',
    'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN',
    'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE',
    'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM',
    'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI',
    'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX',
    'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
    'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
    'District of Columbia': 'DC', 'Alaska': 'AK', 'Hawaii': 'HI'
}
df['STATE_ABBR'] = df['STATE'].map(state_abbrev)

# Map state names to FIPS 'id' for Altair map
state_id_map = {
    'Alabama': 1, 'Alaska': 2, 'Arizona': 4, 'Arkansas': 5, 'California': 6, 'Colorado': 8,
    'Connecticut': 9, 'Delaware': 10, 'District of Columbia': 11, 'Florida': 12, 'Georgia': 13,
    'Hawaii': 15, 'Idaho': 16, 'Illinois': 17, 'Indiana': 18, 'Iowa': 19, 'Kansas': 20,
    'Kentucky': 21, 'Louisiana': 22, 'Maine': 23, 'Maryland': 24, 'Massachusetts': 25,
    'Michigan': 26, 'Minnesota': 27, 'Mississippi': 28, 'Missouri': 29, 'Montana': 30,
    'Nebraska': 31, 'Nevada': 32, 'New Hampshire': 33, 'New Jersey': 34, 'New Mexico': 35,
    'New York': 36, 'North Carolina': 37, 'North Dakota': 38, 'Ohio': 39, 'Oklahoma': 40,
    'Oregon': 41, 'Pennsylvania': 42, 'Rhode Island': 44, 'South Carolina': 45, 'South Dakota': 46,
    'Tennessee': 47, 'Texas': 48, 'Utah': 49, 'Vermont': 50, 'Virginia': 51, 'Washington': 53,
    'West Virginia': 54, 'Wisconsin': 55, 'Wyoming': 56
}
df['id'] = df['STATE'].map(state_id_map)

# --- Precompute growth rate (2018 to 2023) ---
try:
    ev_growth = df[df['Year'].isin([2018, 2023])].pivot(index='STATE', columns='Year', values='Electric (EV)').dropna()
    ev_growth['Growth Rate'] = ((ev_growth[2023] - ev_growth[2018]) / ev_growth[2018]) * 100  # in %
    ev_growth = ev_growth.reset_index()
except Exception as e:
    st.error(f"Error calculating growth rate: {e}")
    # Create an empty dataframe with the required structure if calculation fails
    ev_growth = pd.DataFrame(columns=['STATE', 'Growth Rate'])

# --- Load US States Shape ---
try:
    geojson_url = 'https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json'
    states_geo = gpd.read_file(geojson_url)
    st.success("GeoJSON loaded successfully")
except Exception as e:
    st.error(f"Error loading GeoJSON: {e}")
    st.stop()

# --- Streamlit App ---
st.title('EV / PHEV / HEV Sales and Gas Price Visualization')

# Choose visualization type
viz_type = st.radio('Select Visualization Type:', ['Folium Maps', 'Altair Interactive Dashboard'])

if viz_type == 'Folium Maps':
    # Choose mode: Sales vs Growth Rate
    mode = st.radio('Select Map Type:', ['Sales by Year', 'Growth Rate (2018–2023)'])

    if mode == 'Sales by Year':
        # --- Sales by Year Mode ---
        year = st.selectbox('Select Year:', sorted(df['Year'].unique()))

        df_year = df_continental[df_continental['Year'] == year]
        merged = states_geo.merge(df_year, left_on='name', right_on='STATE')

        m = folium.Map(location=[37.8, -96], zoom_start=4, tiles='CartoDB positron')

        folium.Choropleth(
            geo_data=merged,
            name='choropleth',
            data=merged,
            columns=['STATE', 'Electric (EV)'],
            key_on='feature.properties.name',
            fill_color='Blues',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name=f'Electric Vehicle Sales ({year})'
        ).add_to(m)

        folium.GeoJson(
            merged,
            style_function=lambda x: {
                'fillColor': 'transparent',
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0
            },
            tooltip=GeoJsonTooltip(
                fields=['STATE', 'Electric (EV)', 'Plug-In Hybrid Electric (PHEV)', 'Hybrid Electric (HEV)', 'Gasoline_Price'],
                aliases=['State:', 'EV Sales:', 'PHEV Sales:', 'HEV Sales:', 'Gas Price ($):'],
                localize=True
            )
        ).add_to(m)
        
        # Display the Folium map inside this condition
        st_folium(m, width=800, height=600)

    else:
        # --- Growth Rate Mode ---
        merged_growth = states_geo.merge(ev_growth, left_on='name', right_on='STATE')

        m = folium.Map(location=[37.8, -96], zoom_start=4, tiles='CartoDB positron')

        folium.Choropleth(
            geo_data=merged_growth,
            name='choropleth',
            data=merged_growth,
            columns=['STATE', 'Growth Rate'],
            key_on='feature.properties.name',
            fill_color='YlGnBu',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name='EV Growth Rate (%) (2018–2023)'
        ).add_to(m)

        folium.GeoJson(
            merged_growth,
            style_function=lambda x: {
                'fillColor': 'transparent',
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0
            },
            tooltip=GeoJsonTooltip(
                fields=['STATE', 'Growth Rate'],
                aliases=['State:', 'EV Growth Rate (%):'],
                localize=True,
                labels=True
            )
        ).add_to(m)
        
        # Display the Folium map inside this condition
        st_folium(m, width=800, height=600)

else:  # Altair Interactive Dashboard
    # Filter for most recent year data for the map
    latest_year = df['Year'].max()
    st.write(f"Showing Altair dashboard with data for {latest_year}")
    
    # Debug information
    st.write(f"Number of rows in dataset: {len(df)}")
    st.write(f"Years in dataset: {sorted(df['Year'].unique())}")
    
    # Filter and clean data for visualization
    df_latest = df[df['Year'] == latest_year].copy()
    df_latest = df_latest.dropna(subset=['id', 'Gasoline_Price', 'Electric (EV)'])
    df_latest = df_latest.drop_duplicates(subset='id')
    
    # More debug info
    st.write(f"States with complete data for {latest_year}: {len(df_latest)}")
    
    # Show a sample of the data
    if st.checkbox("Show filtered data sample"):
        st.write(df_latest.head())
    
    # Create a simplified version of the Altair visualization first
    try:
        # Create a basic chart to test if Altair is working
        basic_chart = alt.Chart(df_latest).mark_circle().encode(
            x='Gasoline_Price:Q',
            y='Electric (EV):Q',
            tooltip=['STATE', 'Gasoline_Price', 'Electric (EV)']
        ).properties(
            width=400,
            height=300,
            title='Basic Test Chart: Gas Price vs. EV Sales'
        )
        
        # Display the basic chart
        st.altair_chart(basic_chart, use_container_width=True)
        
        # If basic chart works, try the full dashboard
        st.write("Now attempting to render the full dashboard...")
        
        # Create selection mechanism with corrected 'empty' parameter
        state_selection = alt.selection_point(
            name='state_select',
            fields=['STATE'],
            on='mouseover',
            empty=False,  # Changed from 'none' to False
            clear='mouseout'
        )

        # Load TopoJSON for US states
        states = alt.topo_feature(data.us_10m.url, 'states')

        map_chart = alt.Chart(states).mark_geoshape(
            stroke='white',
            strokeWidth=1
        ).encode(
            color=alt.condition(
                state_selection,
                alt.Color('Gasoline_Price:Q', 
                        scale=alt.Scale(scheme='oranges'), 
                        title=f'Gas Price ({latest_year})'),
                alt.value('lightgray')
            ),
            tooltip=['STATE:N', 'Gasoline_Price:Q', 'Electric (EV):Q']
        ).transform_lookup(
            lookup='id',
            from_=alt.LookupData(df_latest, 'id', ['STATE', 'Gasoline_Price', 'Electric (EV)'])
        ).project(
            type='albersUsa'
        ).add_params(
            state_selection
        ).properties(
            width=600,  # Increased size
            height=400,  # Increased size
            title=f'{latest_year} Gas Prices by State (Hover over a state)'
        )

        # Scatter plot showing Gas Price vs EV Sales for the latest year
        scatter_plot = alt.Chart(df_latest).mark_circle(size=80).encode(
            x=alt.X('Gasoline_Price:Q', title=f'Gas Price ({latest_year})'),
            y=alt.Y('Electric (EV):Q', title=f'EV Sales ({latest_year})'),
            color=alt.condition(
                state_selection,
                alt.Color('STATE:N', scale=alt.Scale(scheme='category20')),
                alt.value('lightgray')
            ),
            opacity=alt.condition(
                state_selection,
                alt.value(1.0),
                alt.value(0.3)
            ),
            size=alt.condition(
                state_selection,
                alt.value(200),
                alt.value(80)
            ),
            tooltip=['STATE', 'Gasoline_Price', 'Electric (EV)']
        ).properties(
            width=600,  # Increased size
            height=400,  # Increased size
            title='Gas Price vs. EV Sales'
        )

        # Combine map and scatter into a horizontal layout
        top_row = alt.hconcat(map_chart, scatter_plot).resolve_scale(color='independent')
        
        # Display just the top row first
        st.altair_chart(top_row, use_container_width=True)
        
        # Line chart showing trend over years for selected state
        # Create a multi-line chart for both Gas Price and EV Sales over time
        st.write("Now attempting to render the trend chart...")
        
        # First, prepare a selection of data for the selected state
        line_data = alt.Chart(df).transform_filter(
            state_selection
        ).encode(
            x=alt.X('Year:O', title='Year', axis=alt.Axis(labelAngle=0)),
            tooltip=['STATE', 'Year', 'Gasoline_Price', 'Electric (EV)']
        )

        # Gas price line
        gas_line = line_data.mark_line(
            color='orange',
            strokeWidth=3
        ).encode(
            y=alt.Y('Gasoline_Price:Q', title='Gas Price ($)', axis=alt.Axis(titleColor='orange'))
        )

        # Gas price points
        gas_points = line_data.mark_circle(
            color='orange',
            size=60
        ).encode(
            y=alt.Y('Gasoline_Price:Q')
        )

        # EV sales line on secondary y-axis
        ev_line = line_data.mark_line(
            color='green',
            strokeWidth=3
        ).encode(
            y=alt.Y('Electric (EV):Q', 
                title='EV Sales', 
                axis=alt.Axis(titleColor='green'),
                scale=alt.Scale(zero=True))
        )

        # EV sales points
        ev_points = line_data.mark_circle(
            color='green',
            size=60
        ).encode(
            y=alt.Y('Electric (EV):Q')
        )

        # Combine lines and points
        gas_layer = alt.layer(gas_line, gas_points)
        ev_layer = alt.layer(ev_line, ev_points)

        # Create a layered chart with dual y-axes
        trend_chart = alt.layer(
            gas_layer, ev_layer
        ).resolve_scale(
            y='independent'
        ).properties(
            width=800,  # Reduced from 1200
            height=250,  # Reduced from 300
            title='Gas Price and EV Sales Trend Over Time (Hover over a state on the map)'
        )

        # Display just the trend chart
        st.altair_chart(trend_chart, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error rendering Altair charts: {e}")
        st.write("Please try the Folium Maps option instead.")

# Add some additional analysis
if st.checkbox("Show Data Analysis"):
    st.subheader("Analysis of EV Sales and Gas Prices")
    
    # Correlation between gas prices and EV sales
    years = sorted(df['Year'].unique())
    selected_year = st.selectbox("Select year for correlation analysis:", years, index=len(years)-1)
    
    df_selected = df[df['Year'] == selected_year].dropna(subset=['Gasoline_Price', 'Electric (EV)'])
    correlation = df_selected['Gasoline_Price'].corr(df_selected['Electric (EV)'])
    
    st.write(f"Correlation between Gas Prices and EV Sales in {selected_year}: {correlation:.4f}")
    
    # Top 5 states by EV sales
    st.subheader(f"Top 5 States by EV Sales ({selected_year})")
    top_states = df_selected.sort_values('Electric (EV)', ascending=False).head(5)[['STATE', 'Electric (EV)']]
    st.write(top_states)
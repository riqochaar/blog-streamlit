# Import required packages
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys
from plotly.subplots import make_subplots

# Set page configuration
st.set_page_config(page_title = 'Thomas Rail', page_icon = ':train:', layout = 'wide', initial_sidebar_state = 'expanded')

# Functions
def calculate_percentage(numerator, denominator, decimal_places):
    percentage = (numerator / denominator) * 100
    percentage_round = np.round(percentage, decimal_places)
    return percentage_round

def slicer_options(col):
    return sorted(list(set(col)))

def slicer_setup(title, options, sval = True):
    slicer = st.sidebar.subheader(title)
    select_all = st.sidebar.checkbox("Select all", key = title, value = sval)
    if not select_all and sval == False:
        slicer =  st.sidebar.multiselect("Select values", options, default = options[0])
    elif not select_all:
        slicer =  st.sidebar.multiselect("Select values", options)
    return slicer, select_all

def set_color(lst, color0, color1):
    if lst == 0:
        return color0
    elif lst == 1:
        return color1

def query(string, df):
    if string == '' or pd.isnull(string) == True:
        df_selection = df
    else:
        df_selection = df.query(string)
    return df_selection

class NumberFormatter:

    @staticmethod
    def format_count(count):

        if count >= 10**5:
            return f"{count / 1_000_000:.2f} M"
        elif count >= 10*3:
            return f"{count / 1_000:.2f} K"
        else:
            return count

    @staticmethod
    def format_money(value):
        if value >= 10**5:
                return f"£{value / 1_000_000:.2f} M"
        elif value >= 10*3:
            return f"£{value / 1_000:.2f} K"
        else:
            return value

    @staticmethod
    def format_percentage(percent, decimal_places = 1):
        return f"{percent:.{decimal_places}f} %"

    @staticmethod
    def format_minutes(minutes):
        if pd.isnull(minutes) == True:
            return "No delays"
        else:
            return f"{minutes:.1f} min"

# Styling
with open('style.css')as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)

# Upload the data
df_trips = pd.read_csv('Data/Trips.csv')

# Extract data for filters
cities_end = slicer_options(df_trips['City End'])
cities_start = slicer_options(df_trips['City Start'])
delay_reasons = slicer_options(df_trips['Delay Reason'])

# Set up filter pane
st.sidebar.header('Please filter here')

filter_cities_end, select_all_cities_end = slicer_setup('City of Arrival', cities_end, False)
filter_cities_start, select_all_cities_start = slicer_setup('City of Departure', cities_start)

st.sidebar.markdown('**Notes**')
st.sidebar.markdown('''To make specific selections, untick the appropriate *Select all* box''')
st.sidebar.markdown('''--- 
Created by Riqo Chaar''')

# Generate queries
f1 = "`City End` == @filter_cities_end" if not select_all_cities_end else np.nan
f2 = "`City Start` == @filter_cities_start" if not select_all_cities_start else np.nan
filters = ' & '.join([x for x in [f1, f2] if pd.isnull(x) == False])

# Query the data
df_selection = query(filters, df_trips)
df_selection_cities_end = query(f1, df_trips)
    
# Information message
if len(df_selection['Trip ID']) == 0:
    st.info("Please ensure that all filters have at least one value selected!")
    sys.exit()

# Extract data for cards
number_of_trips = len(df_selection['Trip ID'].unique().tolist())
total_revenue = df_selection[df_selection['Refund'] != 'Yes']['Price'].sum()
total_refunds = df_selection[df_selection['Refund'] == 'Yes']['Price'].sum()
percent_of_trips_delayed = calculate_percentage(len(df_selection[df_selection['Delay Class'] != 'No Delay']['Trip ID']), len(df_selection['Trip ID']), 1)
average_delay = np.mean(df_selection[df_selection['Delay Class'] != 'No Delay']['Delay'])

# Cards
st.markdown('### Metrics')
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Trips", NumberFormatter.format_count(number_of_trips))
col2.metric("Total Revenue", NumberFormatter.format_money(total_revenue))
col3.metric("Total Refunds", NumberFormatter.format_money(total_refunds))
col4.metric("Trips Delayed", NumberFormatter.format_percentage(percent_of_trips_delayed))
col5.metric("Average Delay", NumberFormatter.format_minutes(average_delay))

# Bar chart captions
st.markdown("#### Select a *City of Arrival* to view the routes with the largest amounts of refunds due to delays and the reason for these delays!")

# Bar chart: City of Arrival by % of Trips Delayed
# Calculations
total_trips = df_trips.groupby('City End')[['Trip ID']].size()
delayed_trips = df_trips[df_trips['Delay Class'] != 'No Delay'].groupby('City End')[['Trip ID']].size()
percentage_of_trips_delayed_by_city = pd.DataFrame(calculate_percentage(delayed_trips, total_trips, 1).sort_values(ascending = False))

# Fix df columns
percentage_of_trips_delayed_by_city = percentage_of_trips_delayed_by_city.reset_index()
percentage_of_trips_delayed_by_city.rename(columns={'City End' : 'City', 0 : 'Percent of Trips Delayed'}, inplace=True)
percentage_of_trips_delayed_by_city['Color'] = np.where(percentage_of_trips_delayed_by_city["City"].isin(list(set(df_selection_cities_end['City End']))), 1, 0)

# Bar chart: Route by Total Refunds
# Calculations
total_refunds = df_selection[df_selection['Refund'] == 'Yes'].groupby('Route')[['Price']].sum().sort_values(by = 'Price', ascending = False)[:10].sort_values(by = 'Price')

# Fix df columns
total_refunds = total_refunds.reset_index()
total_refunds.rename(columns={'Price' : 'Total Refunds'}, inplace=True)
total_refunds['Color'] = 0

# Bar chart: Reason for Delay by Number of Trips
# Calculations
number_of_trips_by_delay_reason = df_selection[df_selection['Delay Reason'] != 'No Delay'].groupby('Delay Reason')[['Trip ID']].count().sort_values(by = 'Trip ID')

# Fix df columns
number_of_trips_by_delay_reason = number_of_trips_by_delay_reason.reset_index()
number_of_trips_by_delay_reason.rename(columns={'Trip ID' : 'Number of Trips', 0 : 'Delay Reason'}, inplace=True)
number_of_trips_by_delay_reason['Color'] = 0

# Plot Figures

fig = make_subplots(
    rows=2, cols=2, horizontal_spacing = 0.2,
    specs=[[{"rowspan": 2}, {}],
           [None, {}]],
    subplot_titles=("<b>City of Arrival by % of Trips Delayed</b>","<b>Top 10 Routes by Total Refunds (£)</b>", "<b>Reason for Delay by Number of Trips</b>"))

fig.add_trace(
    go.Bar(
        x=percentage_of_trips_delayed_by_city['City'], 
        y=percentage_of_trips_delayed_by_city['Percent of Trips Delayed'],
        marker=dict(color=list(map(lambda x: set_color(x, '#000000', '#0070C0'), percentage_of_trips_delayed_by_city['Color'])))), 
    row=1, col=1)

fig.add_trace(
    go.Bar(
        x=total_refunds['Total Refunds'], 
        y=total_refunds['Route'],
        orientation='h',
        marker=dict(color=list(map(lambda x: set_color(x, '#0070C0', np.nan), total_refunds['Color'])))),
        row=1, 
        col=2)

fig.add_trace(
    go.Bar(
        x=number_of_trips_by_delay_reason['Number of Trips'], 
        y=number_of_trips_by_delay_reason['Delay Reason'],
        orientation='h',
        marker=dict(color=list(map(lambda x: set_color(x, '#0070C0', np.nan), number_of_trips_by_delay_reason['Color'])))),
    row=2, col=2)

fig.update_layout(
    showlegend=False, 
    height=600
)
fig.update_xaxes(showgrid=False)
fig.update_yaxes(showgrid=False)

st.plotly_chart(fig, use_container_width=True)

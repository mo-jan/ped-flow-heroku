import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
import pickle
from flask import Flask
import os


# Paths
INPUT_PATH = ""

# mapbox needs an access token
mapbox_access_token = "pk.eyJ1IjoicGxvdGx5bWFwYm94IiwiYSI6ImNqdnBvNDMyaTAxYzkzeW5ubWdpZ2VjbmMifQ.TXcBE-xg9BFdV2ocecc_7g"

### DATA WRANGLING ###########################

# load meter data
df = pd.read_pickle(f"{INPUT_PATH}df_corr.pkl")  # df_corr -> correction factors have been applied
"""
# Alternative file loading via compressed csv file
df = pd.read_csv(f"{INPUT_PATH}df_corr.zip", compression='bz2')  # df_corr -> correction factors have been applied
df['datum']=pd.to_datetime(df['datum'])
df = df.set_index('datum', drop=True)
"""

# Load metadata
df_metadata = pd.read_pickle(f"{INPUT_PATH}df_metadata.pkl")

# Create dataframe for latitude and longitude
df_latlon = df_metadata.drop_duplicates(
    subset=['abkuerzung'], keep="first").copy(
    ).loc[:, ['abkuerzung', 'bezeichnung', 'easting_wgs', 'northing_wgs']]


# Select data for one location and mode, based on "abkuerzung" data_id
def sel_data(data_id, df_metadata=df_metadata, df=df):
    mode = df_metadata.loc[df_metadata['abkuerzung'] ==
                            data_id, 'mode'].tolist()[0]
    if mode == "bike":
        meter_cols = ("velo_in", "velo_out")
    elif mode == "ped":
        meter_cols = ("fuss_in", "fuss_out")
    else:
        print("no mode 'bike' or 'ped' found!")

    df_sel_data = df.loc[df['abkuerzung'] == data_id, meter_cols].sort_index()
    return df_sel_data


# create first df_linechart
initial_data_id = df_metadata.abkuerzung.tolist()[15]
df_linechart = sel_data(initial_data_id)


# create first df_heatmap
def make_df_heatmap(df=df_linechart):
    df_hm = df.iloc[:, [0]].copy()
    df_hm = pd.DataFrame(df_hm.resample('H').sum())
    cname = df_hm.columns.tolist()[0]
    df_hm['date'] = df_hm.index.map(lambda t: t.date())
    df_hm['time'] = df_hm.index.map(lambda t: t.time())
    df_piv = pd.pivot_table(df_hm, values=cname, index='date', columns='time')
    return df_piv


# Get lat lon for first marker in map
def get_lat_lon(data_id, df=df_metadata):
    latlon = df_metadata.drop_duplicates(
        subset=['abkuerzung'], keep="first").loc[df['abkuerzung'] == data_id,
                                                 ('easting_wgs',
                                                  'northing_wgs')].values
    return latlon[0, 0], latlon[0, 1]


# dict pairing "abkuerzung" with name of site.
dict_id_to_name = dict(zip(df_metadata.abkuerzung, df_metadata.bezeichnung))

# create dropdown list from 'abkuerzung' data_ids
drpdwn_lst = []
for i in dict_id_to_name:
    #print (i, dict_id_to_name[i])
    drpdwn_lst.append({'label': f"{i} {dict_id_to_name[i]}", "value": i})

















server = Flask(__name__)
#server.secret_key = os.environ.get('secret_key', 'secret')
app = dash.Dash(name = __name__, server = server)
#app.config.supress_callback_exceptions = True

app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),
    html.Div(children='''
        Dash: A web application framework for Python.
    '''),
    dcc.Graph(
        id='example-graph',    
        figure={
            'data': [
                {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
                {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': u'Montréal'},
            ],
            'layout': {
                'title': 'Dash Data Visualization'
            }
        }
    ),
    dcc.Input(id='my-id', value='initial value', type="text"),
    html.Div(id='my-div')
])

@app.callback(
    Output(component_id='my-div', component_property='children'),
    [Input(component_id='my-id', component_property='value')]
)
def update_output_div(input_value):
    return 'You\'ve entered "{}"'.format(input_value)

if __name__ == '__main__':
    app.run_server()
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.graph_objs as go
import pickle
from flask import Flask
import os
import json
import mydcc

# Paths
INPUT_PATH = "data/"

# mapbox needs an access token
mapbox_access_token = "pk.eyJ1IjoicGxvdGx5bWFwYm94IiwiYSI6ImNqdnBvNDMyaTAxYzkzeW5ubWdpZ2VjbmMifQ.TXcBE-xg9BFdV2ocecc_7g"

### DATA WRANGLING ###########################

# load data
df = pd.read_pickle(
    f"{INPUT_PATH}df_corr.pkl"
)  # df_corr -> correction factors have been applied
df_metadata = pd.read_pickle(f"{INPUT_PATH}df_metadata.pkl")

# Create dataframe for latitude and longitude
df_latlon = (
    df_metadata.drop_duplicates(subset=["abkuerzung"], keep="first")
    .copy()
    .loc[:, ["abkuerzung", "bezeichnung", "easting_wgs", "northing_wgs"]]
)


# Select data for one location and mode, based on "abkuerzung" data_id
def sel_data(data_id, df_metadata=df_metadata, df=df):
    mode = df_metadata.loc[df_metadata["abkuerzung"] == data_id, "mode"].tolist()[0]
    if mode == "bike":
        meter_cols = ("velo_in", "velo_out")
    elif mode == "ped":
        meter_cols = ("fuss_in", "fuss_out")
    else:
        print("no mode 'bike' or 'ped' found!")

    df_sel_data = df.loc[df["abkuerzung"] == data_id, meter_cols].sort_index()
    return df_sel_data


# create first df_linechart
initial_data_id = df_metadata.abkuerzung.tolist()[15]
df_linechart = sel_data(initial_data_id)


# create first df_heatmap
def make_df_heatmap(df=df_linechart):
    df_hm = df.iloc[:, [0]].copy()
    df_hm = pd.DataFrame(df_hm.resample("H").sum())
    cname = df_hm.columns.tolist()[0]
    df_hm["date"] = df_hm.index.map(lambda t: t.date())
    df_hm["time"] = df_hm.index.map(lambda t: t.time())
    df_piv = pd.pivot_table(df_hm, values=cname, index="date", columns="time")
    return df_piv


# Get lat lon for first marker in map
def get_lat_lon(data_id, df=df_metadata):
    latlon = (
        df_metadata.drop_duplicates(subset=["abkuerzung"], keep="first")
        .loc[df["abkuerzung"] == data_id, ("easting_wgs", "northing_wgs")]
        .values
    )
    return latlon[0, 0], latlon[0, 1]


# dict pairing "abkuerzung" with name of site.
dict_id_to_name = dict(zip(df_metadata.abkuerzung, df_metadata.bezeichnung))

# create dropdown list from 'abkuerzung' data_ids
drpdwn_lst = []
for i in dict_id_to_name:
    # print (i, dict_id_to_name[i])
    drpdwn_lst.append({"label": f"{i} {dict_id_to_name[i]}", "value": i})

### DASH GLOBAL STYLE PARAMETERS ###########################

margins_top = 20
margins_bottom = 20

font_color = "black"
bg_color = "white"
plotly_template = "plotly_white"

graph_margins = {"l": 10, "r": 10, "t": 10, "b": 10}
legend = {"x": 1, "y": 0.9}

### DASH LAYOUT ###########################

navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Contact", href="email")),
    ],
    brand="Meter readings check",
    brand_href="#",
    sticky="top",
)

body = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1("Meter overview for Alois"),
                        dcc.Markdown(
                            """\
                        Meters accross Zurich, this is a test, running data from Open Data Hub Zurich. 
                        
                        """
                        ),
                    ],
                    lg=4,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                # selectors
                                dcc.Dropdown(
                                    id="drop_down",
                                    options=drpdwn_lst,
                                    # multi=True,
                                    value=initial_data_id,
                                )
                            ]
                        ),
                        dcc.Graph(
                            id="map",
                            style={
                                "marginBottom": margins_bottom,
                                "marginTop": margins_top,
                            },
                            config={'displayModeBar': False},
                        ),
                    ],
                    lg=8,
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Pre(id='relayout-data_ts'),
                        html.Pre(id='relayout-data_hm'),
                        html.H1(id="meter_name", children=["init"]),
                        dcc.Graph(id="ts_plot", config={'displayModeBar': False}),
                        dcc.Graph(id="hm_plot", config={'displayModeBar': False}),
                    ],
                    style={"marginBottom": margins_bottom, "marginTop": margins_top},
                    lg=12,
                )
            ]
        ),
    ],
    className="mt-4",
)


server = Flask(__name__)
# server.secret_key = os.environ.get('secret_key', 'secret')
# app.config.supress_callback_exceptions = True

app = dash.Dash(name=__name__, server=server, external_stylesheets=[dbc.themes.SIMPLEX])
app.layout = html.Div([navbar, body])
app.title = "Meter reading check"

### DASH FUNCTIONS FOR CALLBACKS ###########################


def generate_linechart(df_linechart):
    """
    Generate linechart based on selected data. 
    :param df_linechart: dataframe with trend data. 
    """
    layout = go.Layout(
        xaxis={"title": "time"},
        yaxis={"title": "counts"},
        # uirevision=data_id,
        margin=graph_margins,
        legend=legend,
        height=300,
        hovermode="closest",
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        autosize=True,
        font={"color": font_color},
        template=plotly_template,
        xaxis_rangeslider_visible=True,
        xaxis_rangeslider_thickness=0.075,
    )
    data = []
    for col in df_linechart:
        new_trace = go.Scatter(
            x=df_linechart.index,
            y=df_linechart[col],
            text=df_linechart[col],
            mode="lines",
            opacity=1,
            line={"width": 1},
            name=str(col),
        )
        data.append(new_trace)
    return {"data": data, "layout": layout}


def generate_heatmap(df_heatmap):
    """
    Generate heatmap based on selected data. 
    :param df_heatmap: dataframe with trend data. 
    """
    layout = go.Layout(
        template=plotly_template,
        height=400,
        # ticks='',
        yaxis_nticks=4,
        yaxis={"title": "hour of day"},
    )
    data = []
    new_trace = go.Heatmap(
        z=df_heatmap.T.values,
        x=df_heatmap.index,
        y=list(range(0, len(df_heatmap.columns))),
        colorscale="Greys",  # "Viridis",
    )
    data.append(new_trace)
    return {"data": data, "layout": layout}


### DASH CALLBACKS ###########################


# Update data_id trough map or drop_down
@app.callback(
    [Output("drop_down", "value")],
    [Input("map", "clickData")],
)
def update_data_id(map):
    # when app is loaded
    if map is None:
        data_id = [initial_data_id]
        return data_id
    else:
        click_data = map["points"][0]["text"]
        data_id = [click_data.split(" ")[0]]
        return data_id


# Update line graph
@app.callback(
    Output("ts_plot", "figure"),
    [Input("drop_down", "value")],
)
def update_linechart(drop_down):
    data_id = drop_down
    df_linechart = sel_data(data_id)
    return generate_linechart(df_linechart)


# Update heatmap
@app.callback(
    Output("hm_plot", "figure"),
    [Input("drop_down", "value")],
)
def update_heatmap(drop_down):
    df_heatmap = make_df_heatmap(sel_data(drop_down))
    return generate_heatmap(df_heatmap)


# Update map marker
@app.callback(
    Output("map", "figure"),
    [Input("drop_down", "value")],
)
def update_map(drop_down):
    data_id = drop_down
    label = f"{data_id}, {df_latlon.loc[df_latlon['abkuerzung']==data_id, ('bezeichnung')].tolist()[0]}"

    return {
        "data": [
            go.Scattermapbox(
                lat=df_latlon["northing_wgs"],
                lon=df_latlon["easting_wgs"],
                mode="markers",
                marker_size=15,
                opacity=0.5,
                text=(df_latlon["abkuerzung"] + " " + df_latlon["bezeichnung"]),
            ),
            go.Scattermapbox(
                lat=df_latlon.loc[df_latlon["abkuerzung"] == data_id, "northing_wgs"],
                lon=df_latlon.loc[df_latlon["abkuerzung"] == data_id, "easting_wgs"],
                mode="markers",
                marker_size=20,
                marker_color="red",
                opacity=0.8,
                text=label,
            ),
        ],
        "layout": go.Layout(
            hovermode="closest",
            showlegend=False,
            height=400,
            geo=dict(scope="europe"),
            margin=dict(l=0, r=0, t=0, b=0),
            mapbox=go.layout.Mapbox(
                accesstoken=mapbox_access_token,
                bearing=0,
                center=go.layout.mapbox.Center(
                    lat=47.385, lon=8.5417
                ),  # 47.3769° N, 8.5417° E
                pitch=0,
                zoom=11,
                style="light",
            ),
        ),
    }


# Update title
@app.callback(
    Output("meter_name", "children"),
    [Input("drop_down", "value")],
)
def update_linechart(drop_down):
    data_id = drop_down
    label = f"{df_latlon.loc[df_latlon['abkuerzung']==data_id, ('bezeichnung')].tolist()[0]}"
    return label


if __name__ == "__main__":
    app.run_server(debug=False)

import json
import logging
import math
import os
from datetime import date, datetime
import locale

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_flexbox_grid as dfx
import sd_material_ui as dui
import numpy as np
import pandas as pd
import plotly.express as px
from dash.dependencies import Input, Output,State

from figures import get_regional_map,get_provincial_map, get_tamponi_graph
from utils import (
    calcolo_giorni_da_min_positivi,
    calculate_line,
    exp_viridis,
    get_areas,
    get_dataset,
    get_map_json,
    linear_reg,
    mean_absolute_percentage_error,
    pretty_colors,
    viridis,
    filter_dates,
)

locale.setlocale(locale.LC_ALL, "")
logger = logging.getLogger("dash_application")
logger.setLevel(logging.DEBUG)

# external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css",os.path.join("assets","dashboard.css")]

app = dash.Dash(__name__)  # , external_stylesheets=external_stylesheets)

df, df_regioni, smokers_series, imprese_series = get_dataset(datetime.today())
province_map_json, regions_map_json = get_map_json()
regions, provinces = get_areas(df)
giorni_da_min_positivi = calcolo_giorni_da_min_positivi(df_regioni)
viridis_exp_scale = exp_viridis(giorni_da_min_positivi)

metric_names = {
    "totale_casi": "Totale Contagiati",
    "deceduti": "Deceduti",
    "tamponi": "Tamponi",
    "terapia_intensiva": "Terapia Intensiva",
    "totale_positivi": "Attualmente Positivi",
    "dimessi_guariti": "Guariti",
    "totale_ospedalizzati":"Ospedalizzati",
}
metric_list = [
    "totale_casi",
    "tamponi",
    "totale_positivi",
    "deceduti",
    "dimessi_guariti",
    "terapia_intensiva",
]


def get_big_numbers(metrics_list, area="IT", day=datetime.today):

    top_metrics = []

    for metric in metrics_list:
        top_metrics.append(
            dfx.Row(
                between="xs",
                children=[
                    html.Div(
                        [
                            html.Div(
                                [dui.CircularProgress(mode="indeterminate", size=20)],
                                id=f"daily-{metric}-number",
                                className="big-metric-number",
                            ),
                            html.Div(
                                metric_names[metric],
                                id=f"daily-{metric}-label",
                                className="big-metric-label",
                            ),
                        ],
                        id=f"daily_{metric}",
                        className="big-metric",
                    )
                ],
            )
        )
    return top_metrics


app.layout = dfx.Grid(
    id="grid",
    fluid=True,
    children=[
        dfx.Row(
            middle="xs",
            center="xs",
            children=[
                dfx.Col(
                    xs=12,
                    lg=1,
                    children=[
                        html.Div(
                            html.Img(
                                src="http://neurality.it/images/logo_small_black.png"
                            ),
                            id="logo",
                        )
                    ],
                    className="menuItem",
                ),
                dfx.Col(
                    xs=12,
                    lg=8,
                    children=[html.Div("Menu", id="menu")],
                    className="menuItem",
                ),
                dfx.Col(
                    xs=12,
                    lg=3,
                    children=[html.Div("info-tooltips", id="info-tooltips")],
                    className="menuItem",
                ),
            ],
            id="menu-bar",
        ),
        dfx.Row(
            id="main-content",
            center="xs",
            children=[
                dfx.Col(
                    id="numbers", xs=12, lg=2, children=get_big_numbers(metric_list)
                ),
                dfx.Col(
                    id="map-column",
                    xs=12,
                    lg=7,
                    children=[
                        dfx.Row(
                            dcc.Graph(
                                id="main-map",
                                figure=get_regional_map(
                                    df_regioni,
                                    regions_map_json,
                                    viridis_exp_scale,
                                    "totale_casi",
                                    "Totale Casi",
                                    max_scale_value=math.ceil(
                                        df_regioni["totale_casi"].max() + 1
                                    ),
                                ),
                                # animate=True,
                                # config={"displayModeBar": False}),
                                className="dashboardContainer",
                                # style={"min-width": "100%"}
                            ),
                            center="xs",
                        ),
                        dfx.Row(
                            dcc.Tabs(
                                id="area-map",
                                value="regioni",
                                children=[
                                    dcc.Tab(label="Regioni", value="regioni"),
                                    dcc.Tab(label="Provincie", value="province"),
                                ],
                            )
                        ),
                        dfx.Row(
                            dcc.Tabs(
                                id="data-selected",
                                value="totale_casi",
                                children=[
                                    dcc.Tab(
                                        label="Casi Confermati", value="totale_casi"
                                    ),
                                    dcc.Tab(label="Tamponi", value="tamponi"),
                                    dcc.Tab(label="Deceduti", value="deceduti"),
                                    dcc.Tab(label="Guariti", value="dimessi_guariti"),
                                    dcc.Tab(label="Positivi", value="totale_positivi"),
                                    dcc.Tab(
                                        label="Ospedalizzati",
                                        value="totale_ospedalizzati",
                                    ),
                                    dcc.Tab(
                                        label="Terapia Intensiva",
                                        value="terapia_intensiva",
                                    ),
                                ],
                            )
                        ),
                        dfx.Row(
                            dcc.Slider(
                                min=df["data"].min().toordinal(),
                                max=df["data"].max().toordinal(),
                                value=df["data"].max().toordinal(),
                                marks={
                                    giorno.toordinal(): {
                                        "label": f"{str(giorno.day).zfill(2)}/{str(giorno.month).zfill(2)}/{str(giorno.year)[:2]}",
                                        "style": {
                                            "color": "#444",
                                            # "transform": "rotate(45deg)",
                                        },
                                    }
                                    for giorno in filter_dates(df["data"].unique(), 12)
                                },
                                id="date-slider",
                            ),
                            center="xs",
                        ),
                    ],
                ),
                dfx.Col(
                    id="graphs-column",
                    xs=12,
                    lg=3,
                    children=[
                        dcc.Graph(
                            figure=get_tamponi_graph(df_regioni),
                            id="tamponi-graph",
                            className="dashboardContainer",
                        ),
                        dcc.Graph(
                            figure=get_tamponi_graph(df_regioni),
                            id="other-graph",
                            className="dashboardContainer",
                        ),
                    ],
                ),
            ],
        ),
        html.Div(id="filter", style={"display": "none"}),
    ],
)


@app.callback(
    Output("main-map", component_property="figure"),
    [
        Input("date-slider", "value"),
        Input("data-selected", "value"),
        Input("area-map", "value"),
    ],
)
def update_map(ordinal_date, data_selected, area_map):

    giorno = date.fromordinal(ordinal_date)
    if area_map == "regioni":
        filtered_df = df_regioni[df_regioni["data"].dt.date == giorno]
        geojson = regions_map_json
        figure = get_regional_map(
            filtered_df,
            geojson,
            viridis_exp_scale,
            data_selected,
            metric_names[data_selected],
            math.ceil(df_regioni[data_selected].max() + 1),
        )
    else:
        filtered_df = df[df["data"].dt.date == giorno]
        geojson = province_map_json
        figure = get_provincial_map(
            filtered_df,
            geojson,
            viridis_exp_scale,
            math.ceil(df["totale_casi"].max() + 1),
        )

    # logger.debug()

    return figure


@app.callback(
    [
        Output(f"daily-{metric}-number", component_property="children")
        for metric in metric_list
    ],
    [
        Input("filter", component_property="data-area"),
        Input("filter", component_property="data-date"),
    ],
    [
        State('area-map', 'value'),
    ]
)
def update_big_numbers(area_string, ordinal_date,area_type):
    giorno = date.fromordinal(ordinal_date)
    if area_type =="regioni":
        filtered_df = df_regioni[df_regioni["data"].dt.date == giorno]
        if area_string:
            area_list = area_string.split("|")
            filter_ = filtered_df["denominazione_regione"].isin(area_list)
            filtered_df = filtered_df[filter_]
    else:
        filtered_df = df[df["data"].dt.date == giorno]
        if area_string:
            area_list = area_string.split("|")
            filter_ = filtered_df["NUTS3"].isin(area_list)
            filtered_df = filtered_df[filter_]

    response_number = [f"{filtered_df[metric].sum():n}" for metric in metric_list]

    return response_number


@app.callback(
    Output("tamponi-graph", component_property="figure"),
    [Input("filter", component_property="data-area"),],
)
def update_area_graphs(area_string):
    if area_string:
        area_list = area_string.split("|")
        filter_ = df_regioni["denominazione_regione"].isin(area_list)
        filtered_data = df_regioni[filter_]

        return get_tamponi_graph(filtered_data)
    else:
        return get_tamponi_graph(df_regioni)


@app.callback(
    Output("filter", component_property="data-area"),
    [Input("main-map", component_property="selectedData"),],
)
def set_filter_location(selectedData):

    if selectedData:
        a = [point["customdata"][0] for point in selectedData["points"]]
        return "|".join(a)
    else:
        return ""


@app.callback(
    Output("data-selected", component_property="style"), [Input("area-map", "value"),]
)
def hide_data_type(area_value):
    if area_value == "province":
        return {"display":"None"}
    else:
        return {"display":"block"}


@app.callback(
    Output("filter", component_property="data-date"), [Input("date-slider", "value"),]
)
def set_filter_data(selectedData):

    return selectedData


if __name__ == "__main__":
    app.run_server(debug=True)

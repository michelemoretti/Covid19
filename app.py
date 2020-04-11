import json
import logging
import math
import os
from datetime import date, datetime

import dash
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import pandas as pd
import plotly.express as px
from dash.dependencies import Input, Output

from figures import get_regional_map
from utils import (
    calcolo_giorni_da_min_positivi, calculate_line, exp_viridis, get_areas,
    get_dataset, get_map_json, linear_reg, mean_absolute_percentage_error,
    pretty_colors, viridis)

logger = logging.getLogger('dash_application')
logger.setLevel(logging.DEBUG)

# external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css",os.path.join("assets","dashboard.css")]

app = dash.Dash(__name__)  # , external_stylesheets=external_stylesheets)

df, df_regioni, smokers_series, imprese_series = get_dataset(datetime.today())
province_map_json, regions_map_json = get_map_json()
regions, provinces = get_areas(df)
giorni_da_min_positivi = calcolo_giorni_da_min_positivi(df_regioni)
viridis_exp_scale = exp_viridis(giorni_da_min_positivi)


def get_top_bar(metrics_list, area="IT", day=datetime.today):

    top_metrics = []

    for metric in metrics_list:
        top_metrics.append(
            html.Div(
                [
                    html.Div(
                        1000,
                        id=f"daily-{metric}-number",
                        className="big-metric-number",
                    ),
                    html.Div(
                        metric, id=f"daily-{metric}-label", className="big-metric-label"
                    ),
                ],
                id=f"daily_{metric}",
                className="big-metric",
            )
        )
    return html.Div(top_metrics, id="top-bar", className="dashboardContainer")


app.layout = html.Div(
    [
        get_top_bar(["Contagiati", "Deceduti", "Tamponi", "Terapia Intensiva"]),
        html.Div(
            dcc.Graph(
                id="main-map",
                figure=get_regional_map(
                    df_regioni,
                    regions_map_json,
                    viridis_exp_scale,
                    "totale_casi",
                    "Totale Casi",
                    max_scale_value=math.ceil(df_regioni["totale_casi"].max()+1),
                ),
                # config={"displayModeBar": False}),
                className="dashboardContainer",
            ),
        ),
        html.Div(
            [
                dcc.Slider(
                    min=df["data"].min().toordinal(),
                    max=df["data"].max().toordinal(),
                    value=df["data"].max().toordinal(),
                    marks={
                        giorno.toordinal(): {
                            "label": f"{str(giorno.day).zfill(2)}/{str(giorno.month).zfill(2)}/{str(giorno.year)[:2]}",
                            "style": {"color": "#444",

                                    "transform":"rotate(45deg)"},
                        }
                        for giorno in df["data"].unique()
                    },
                    id="date-slider",
                ),
            ],
        )
    ]
)


@app.callback(Output("main-map", component_property="figure"), [Input("date-slider", "value"),])
def update_map(ordinal_date):
    giorno = date.fromordinal(ordinal_date)    

    figure = get_regional_map(
                    df_regioni[df_regioni["data"].dt.date==giorno],
                    regions_map_json,
                    viridis_exp_scale,
                    "totale_casi",
                    "Totale Casi",
                    math.ceil(df_regioni["totale_casi"].max()+1)
                )
    return figure


if __name__ == "__main__":
    app.run_server(debug=True)

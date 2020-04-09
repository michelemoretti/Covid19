import json
import os
from datetime import datetime

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
                ),
                # config={"displayModeBar": False}),
                className="dashboardContainer",
            ),
        
        ),
        html.Div(id="content"),
    ],
    className="row",
)

@app.callback(
    Output('content', 'children'),
    [Input('main-map', 'hoverData'),]
    )
def update_x_timeseries(hoverData):
    
    return json.dumps(hoverData, indent=2)



if __name__ == "__main__":
    app.run_server(debug=True)

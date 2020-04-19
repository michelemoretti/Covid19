import json
import locale
import logging
import math
import os
from datetime import date, datetime

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_flexbox_grid as dfx
import dash_html_components as html
import markdown
import numpy as np
import pandas as pd
import plotly.express as px
import sd_material_ui as dui
from dash.dependencies import Input, Output, State

from figures import get_provincial_map, get_regional_map, get_tamponi_graph
from utils import (
    calcolo_giorni_da_min_positivi,
    calculate_line,
    exp_viridis,
    filter_dates,
    get_areas,
    get_dataset,
    get_map_json,
    linear_reg,
    mean_absolute_percentage_error,
    pretty_colors,
    viridis,
)

locale.setlocale(locale.LC_ALL, "")
logger = logging.getLogger("dash_application")
logger.setLevel(logging.DEBUG)

# external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css",os.path.join("assets","dashboard.css")]
df, df_regioni, smokers_series, imprese_series = get_dataset(datetime.today())
df_notes = pd.read_csv(
    "https://raw.githubusercontent.com/pcm-dpc/COVID-19/master/note/dpc-covid19-ita-note-it.csv"
)
df_notes["data"] = pd.to_datetime(df_notes["data"],)  # format='%d%b%Y:%H:%M:%S.%f')

license_md = markdown.markdown(open("LICENSE.md").read())

app = dash.Dash(__name__,external_stylesheets=[dbc.themes.BOOTSTRAP])  # , external_stylesheets=external_stylesheets)

logger.error(dbc.themes.BOOTSTRAP)

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
    "totale_ospedalizzati": "Ospedalizzati",
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
                    id="numbers",
                    className="dashboardColumn",
                    xs=12,
                    lg=2,
                    children=get_big_numbers(metric_list),
                ),
                dfx.Col(
                    id="map-column",
                    className="dashboardColumn",
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
                                parent_className="bottom-tabs",
                                className="bottom-tabs-container",
                                children=[
                                    dcc.Tab(
                                        label="Regioni",
                                        value="regioni",
                                        className="bottom-tab",
                                        selected_className="bottom-tab--selected",
                                    ),
                                    dcc.Tab(
                                        label="Province",
                                        value="province",
                                        className="bottom-tab",
                                        selected_className="bottom-tab--selected",
                                    ),
                                ],
                            ),
                            center="xs",
                        ),
                        dfx.Row(
                            dcc.Tabs(
                                id="data-selected",
                                value="totale_casi",
                                parent_className="bottom-tabs",
                                className="bottom-tabs-container",
                                # content_style={"padding":"7px"},
                                children=[
                                    dcc.Tab(
                                        label="Confermati",
                                        value="totale_casi",
                                        className="bottom-tab",
                                        selected_className="bottom-tab--selected",
                                    ),
                                    dcc.Tab(
                                        label="Tamponi",
                                        value="tamponi",
                                        className="bottom-tab",
                                        selected_className="bottom-tab--selected",
                                    ),
                                    dcc.Tab(
                                        label="Deceduti",
                                        value="deceduti",
                                        className="bottom-tab",
                                        selected_className="bottom-tab--selected",
                                    ),
                                    dcc.Tab(
                                        label="Guariti",
                                        value="dimessi_guariti",
                                        className="bottom-tab",
                                        selected_className="bottom-tab--selected",
                                    ),
                                    dcc.Tab(
                                        label="Positivi",
                                        value="totale_positivi",
                                        className="bottom-tab",
                                        selected_className="bottom-tab--selected",
                                    ),
                                    dcc.Tab(
                                        label="Ospedalizzati",
                                        value="totale_ospedalizzati",
                                        className="bottom-tab",
                                        selected_className="bottom-tab--selected",
                                    ),
                                    dcc.Tab(
                                        label="Terapia Int.",
                                        value="terapia_intensiva",
                                        className="bottom-tab",
                                        selected_className="bottom-tab--selected",
                                    ),
                                ],
                            ),
                            center="xs",
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
                    className="dashboardColumn",
                    xs=12,
                    lg=3,
                    children=[
                        dcc.Graph(
                            figure=get_tamponi_graph(df_regioni),
                            id="tamponi-graph",
                            className="dashboardContainer dash-graph",
                        ),
                        dcc.Graph(
                            figure=get_tamponi_graph(df_regioni),
                            id="other-graph",
                            className="dashboardContainer dash-graph",
                        ),
                        dcc.Graph(
                            figure=get_tamponi_graph(df_regioni),
                            id="tamponi-graph2",
                            className="dashboardContainer dash-graph",
                        ),
                    ],
                ),
            ],
        ),
        dfx.Row(
            id="footer",
            center="xs",
            children=[
                dfx.Col(
                    [
                        html.Div(
                            [html.H4("Note"), html.Ul([], id="notes-list",)],
                            id="notes",
                        )
                    ],
                    xs=12,
                    lg=3,
                    id="notes-column",
                    className="dashboardContainer",
                ),
                dfx.Col(
                    [
                        html.Div(
                            children=[
                                html.H4("Licenza d'uso"),
                                dcc.Markdown([license_md], dangerously_allow_html=True),
                            ],
                            id="license",
                        )
                    ],
                    xs=12,
                    lg=9,
                    id="licenseColumn",
                    className="dashboardContainer",
                ),
            ],
        ),
        html.Div(id="filter", style={"display": "none"}),
        html.Div(
            [
                dbc.Tooltip(
                    f"Contiene anche i casi guariti o già deceduti",
                    target=f"daily-totale_casi-number",
                    placement="right",
                )
            ],
            id="tooltips-container",
            style={"display": "none"},
        ),
    ],
)


@app.callback(
    Output("tamponi-graph", component_property="figure"),
    [Input("filter", component_property="data-area"),],
)
def update_area_graphs(area_string):

    ctx = dash.callback_context
    triggerer = [x["prop_id"] for x in ctx.triggered]
    logger.debug(f"update_area_graphs triggered by {triggerer}")

    if area_string:
        area_list = area_string.split("|")
        filter_ = df_regioni["denominazione_regione"].isin(area_list)
        filtered_data = df_regioni[filter_]

        return get_tamponi_graph(filtered_data)
    else:
        return get_tamponi_graph(df_regioni)


@app.callback(
    [
        Output("filter", component_property="data-area"),
        Output("filter", component_property="data-area-index"),
        Output("filter", component_property="data-map-type"),
    ],
    [Input("main-map", component_property="selectedData"), Input("area-map", "value"),],
    [State("main-map", component_property="figure")],
)
def set_filter_location(selectedData, area_tab, figure):

    ctx = dash.callback_context
    triggerer = [x["prop_id"] for x in ctx.triggered]
    logger.debug(f"set_filter_location triggered by {triggerer}")

    ctx = dash.callback_context

    # If the callback was triggered by a tab click reset the selection
    if ctx.triggered[0]["prop_id"] == "area-map.value":
        return "", "", area_tab

    else:
        if selectedData:
            selected_indexes = figure["data"][0]["selectedpoints"]
            area_list = [point["customdata"][0] for point in selectedData["points"]]
            logger.debug(f"selected area in map = {area_list}")
            logger.debug(f"selected area in map with indexes = {selected_indexes}")
            return (
                "|".join(area_list),
                "|".join(str(x) for x in selected_indexes),
                area_tab,
            )
        else:
            return "", "", area_tab


@app.callback(
    Output("data-selected", component_property="style"),
    [Input("filter", component_property="data-map-type")],
)
def hide_data_type(area_value):
    ctx = dash.callback_context
    triggerer = [x["prop_id"] for x in ctx.triggered]
    logger.debug(f"hide_data_type triggered by {triggerer}")
    if area_value == "province":
        return {"display": "None"}
    else:
        return {"display": ""}


@app.callback(
    Output("filter", component_property="data-map-datatype-selected"),
    [
        Input("data-selected", "value"),
        Input("filter", component_property="data-map-type"),
    ],
)
def set_map_datatype(selectedData, map_type):

    ctx = dash.callback_context
    triggerer = [x["prop_id"] for x in ctx.triggered]
    logger.debug(f"set_map_datatype triggered by {triggerer}")

    if map_type == "province":
        return "totale_casi"
    else:
        return selectedData


@app.callback(
    Output("filter", component_property="data-date"), [Input("date-slider", "value"),]
)
def set_filter_date(selectedData):
    ctx = dash.callback_context
    triggerer = [x["prop_id"] for x in ctx.triggered]
    logger.debug(f"set_filter_date triggered by {triggerer}")
    return selectedData


""" @app.callback(
    Output("filter","data-area-type"),
    [Input("area-map", "value"),]
)
def set_map_type_filter(area_type):
    #Sets "regioni" or "province" in the DOM so it can be read by other callbacks
    return area_type, None """


@app.callback(
    Output("main-map", component_property="figure"),
    [
        Input("filter", component_property="data-date"),
        Input("filter", "data-map-datatype-selected"),
        Input("filter", component_property="data-map-type"),
    ],
    [State("filter", "data-area-index")],
)
def update_map(ordinal_date, data_selected, area_map, preselection):

    if not ordinal_date:
        return None
    ctx = dash.callback_context
    triggerer = [x["prop_id"] for x in ctx.triggered]
    logger.debug(f"update_map triggered by {triggerer}")

    giorno = date.fromordinal(ordinal_date)

    # check if region or province map was requested
    if area_map == "regioni":
        filtered_df = df_regioni[df_regioni["data"].dt.date == giorno]
        figure = get_regional_map(
            filtered_df,
            regions_map_json,
            viridis_exp_scale,
            data_selected,
            metric_names[data_selected],
            math.ceil(df_regioni[data_selected].max() + 1),
        )
    else:
        filtered_df = df[df["data"].dt.date == giorno]
        figure = get_provincial_map(
            filtered_df,
            province_map_json,
            viridis_exp_scale,
            math.ceil(df["totale_casi"].max() + 1),
        )

    if (
        preselection
    ):  # and (triggerer in ["filter.data-date", "filter.data-map-datatype-selected"]) :
        preselection_list = [str(x) for x in preselection.split("|")]
        figure.data[0].selectedpoints = preselection_list
        logger.debug(f"new_selection ->{figure.data[0].selectedpoints}")

    logger.debug("\n")
    return figure


@app.callback(
    [
        Output(f"daily-{metric}-number", component_property="children")
        for metric in metric_list
    ],
    [
        Input("filter", component_property="data-area"),
        Input("filter", component_property="data-date"),
        Input("filter", component_property="data-map-type"),
    ],
)
def update_big_numbers(area_string, ordinal_date, area_type):

    if not ordinal_date:
        return [None for metric in metric_list]

    ctx = dash.callback_context
    logger.debug(f"update_big_numbers triggered by {ctx.triggered[0]['prop_id']}")

    giorno = date.fromordinal(ordinal_date)

    if area_type == "regioni":
        filtered_df = df_regioni[df_regioni["data"].dt.date == giorno]
        if area_string:
            area_list = area_string.split("|")
            filter_ = filtered_df["denominazione_regione"].isin(area_list)
            filtered_df = filtered_df[filter_]
        response_number = [f"{filtered_df[metric].sum():n}" for metric in metric_list]

    else:
        filtered_df = df[df["data"].dt.date == giorno]
        if area_string:
            area_list = area_string.split("|")
            filter_ = filtered_df["NUTS3"].isin(area_list)
            filtered_df = filtered_df[filter_]
        response_number = [
            f"{filtered_df[metric].sum():n}" if metric in filtered_df.columns else "N/A"
            for metric in metric_list
        ]

    return response_number


@app.callback(
    Output("notes-list", component_property="children"),
    [Input("filter", component_property="data-map-type")],
)
def set_notes(map_type):

    if map_type == None:
        # Page Loading
        return []
    if map_type == "regioni":
        filtered_notes = df_notes[df_notes["dataset"] == "dati-regioni"]
        filter_area = "regione"
    elif map_type == "province":
        filtered_notes = df_notes[df_notes["dataset"] == "dati-province"]
        filter_area = "provincia"
    else:
        raise Exception(f"maptype {map_type} not in ['regioni','province']")

    return [
        html.Li(f"{day} | {region} - {warning} ")
        for day, warning, region in zip(
            filtered_notes["data"].dt.date,
            filtered_notes["avviso"],
            filtered_notes[filter_area],
        )
    ]


if __name__ == "__main__":
    app.run_server(debug=True)

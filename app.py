import base64
import importlib
import json
import locale
import logging
import math
import os
from datetime import date, datetime

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_daq as daq
import dash_flexbox_grid as dfx
import dash_html_components as html
import markdown
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sd_material_ui as dui
from dash.dependencies import Input, Output, State
from flask import request
from flask_caching import Cache

from figures import (
    get_growth_rate_graph,
    get_PM10_graph,
    get_positive_tests_ratio_graph,
    get_provincial_map,
    get_regional_map,
    get_removed_graph,
    get_respiratory_deaths_graph,
    get_smokers_graph,
    get_tamponi_graph,
    get_variable_graph,
)
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

locale.setlocale(locale.LC_ALL, "it_IT.UTF-8")
logger = logging.getLogger("dash_application")
logger.setLevel(logging.INFO)

# external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css",os.path.join("assets","dashboard.css")]
df, df_regioni, smokers_series, imprese_series, _ = get_dataset(datetime.today())

df_regioni_map_index = {
    "Abruzzo": "0",
    "Basilicata": "1",
    "Calabria": "3",
    "Campania": "4",
    "Emilia-Romagna": "5",
    "Friuli Venezia Giulia": "6",
    "Lazio": "7",
    "Liguria": "8",
    "Lombardia": "9",
    "Marche": "10",
    "Molise": "11",
    "Piemonte": "12",
    "Puglia": "13",
    "Sardegna": "14",
    "Sicilia": "15",
    "Trentino Alto Adige": "17",
    "Toscana": "16",
    "Umbria": "18",
    "Valle d'Aosta": "19",
    "Veneto": "20",
}

region_names = df_regioni["denominazione_regione"].unique().tolist()
region_names.remove("P.A. Bolzano")
region_names = [
    "Trentino Alto Adige" if x == "P.A. Trento" else x for x in region_names
]
region_dropdown_options = [
    {"label": regione, "value": codice_regione}
    for regione, codice_regione in zip(region_names, region_names,)
]

provinces_dropdown_options = [
    {
        "label": provincia,
        "value": df[df["denominazione_provincia"] == provincia]["NUTS3"].tolist()[0],
    }
    for provincia in df["denominazione_provincia"].unique().tolist()
]


with open("provinces_map_indexes.json", "r") as f:
    provinces_datapoint_json = json.load(f)


df_province_map_index = {
    x["customdata"][0]: str(x["pointNumber"]) for x in provinces_datapoint_json
}


air_series = pd.read_csv(
    os.path.join("ISTAT_DATA", "air_pollution_2018.csv"), encoding="utf-8"
).set_index("NUTS3")

df_notes = pd.read_csv(
    "https://raw.githubusercontent.com/pcm-dpc/COVID-19/master/note/dpc-covid19-ita-note-it.csv"
)
df_notes["data"] = pd.to_datetime(df_notes["data"],)  # format='%d%b%Y:%H:%M:%S.%f')

license_md = markdown.markdown(open("LICENSE.md").read())

df_regioni_today = df_regioni.set_index("NUTS3")
df_regioni_today = df_regioni_today[
    df_regioni_today["data"] == df_regioni_today["data"].max()
]
morti_resp_path = os.path.join(
    "ISTAT_DATA", "Deaths(#), Diseases of the respiratory system, Total.csv"
)
morti_resp = pd.read_csv(morti_resp_path).set_index("index")
morti_resp.at[0, "Covid"] = df_regioni_today["deceduti"].sum()


app = dash.Dash(
    __name__, external_stylesheets=[dbc.themes.BOOTSTRAP]
)  # , external_stylesheets=external_stylesheets)

server = app.server

province_map_json, regions_map_json = get_map_json()
regions, provinces = get_areas(df)
giorni_da_min_positivi = calcolo_giorni_da_min_positivi(df_regioni)
viridis_exp_scale = exp_viridis(giorni_da_min_positivi)

TIMEOUT = 6*60*60

metric_names = {
    "totale_casi": "Contagiati",
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

fullscreen_icon = os.path.join(
    "imgs", "fullscreen-enter-2x.png"
)  # replace with your own image
fullscreen_icon_encoded = base64.b64encode(open(fullscreen_icon, "rb").read())
fullscreen_img_tag = html.Img(
    src="data:image/png;base64,{}".format(fullscreen_icon_encoded.decode())
)

redis_found = importlib.util.find_spec("redis_connection")

if redis_found:
    from redis_connection import config as cache_config
else:
    cache_config = {
        "CACHE_TYPE": "filesystem",
        "CACHE_DIR": "cache-directory",
    }
cache = Cache(app.server, config=cache_config)

app.index_string = """<!DOCTYPE html>
<html>
    <head>
        <!-- Global site tag (gtag.js) - Google Analytics -->
        <script async src="https://www.googletagmanager.com/gtag/js?id=UA-162843377-2"></script>
        <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', 'UA-162843377-2');
        gtag('config', 'GA_TRACKING_ID', { 'anonymize_ip': true });

        </script>

        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""


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
                        id=f"daily-{metric}",
                        className="big-metric rounded_boxes",
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
                            html.A(
                                html.Img(
                                    src="http://neurality.it/images/logo_small_black.png"
                                ),
                                id="logo",
                                href="https://neurality.it",
                                target="_blank",
                            ),
                        ),
                    ],
                    className="menuItem",
                ),
                dfx.Col(
                    xs=12,
                    lg=8,
                    children=[
                        html.Div(
                            html.A(
                                "Dashboard Neurality COVID-19",
                                href="https://neurality.it",
                                target="_blank",
                            ),
                            id="menu",
                        )
                    ],
                    className="menuItem",
                ),
                dfx.Col(
                    xs=12,
                    lg=3,
                    children=[
                        html.Div(
                            [
                                daq.BooleanSwitch(
                                    id="istat-button",
                                    on=False,
                                    label="ISTAT Data",
                                    labelPosition="bottom",
                                    className="toggle",
                                ),
                                daq.BooleanSwitch(
                                    id="aggregation-toggle",
                                    label="Aggrega grafici",
                                    labelPosition="bottom",
                                    on=False,
                                    className="toggle",
                                ),
                                daq.BooleanSwitch(
                                    id="logarithmic-toggle",
                                    label="Asse-y Log",
                                    labelPosition="bottom",
                                    on=False,
                                    className="toggle",
                                ),
                            ],
                            id="info-tooltips",
                        )
                    ],
                    className="menuItem",
                ),
            ],
            id="menu-bar",
        ),
        dfx.Row(
            id="main-content",
            center="xs",
            middle="xs",
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
                    lg=5,
                    children=[
                        dfx.Row([html.H2("Mappa Contagio"),], id="area-selection-row",),
                        dfx.Row(
                            [
                                html.Div(
                                    [
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
                                        dbc.Button(
                                            "Confronta le aree di interesse",
                                            id="map-info-button",
                                            className="floating-button mapButton",
                                            size="sm",
                                            color="info",
                                        ),
                                    ],
                                    style={"position": "relative", "width": "100%"},
                                )
                            ],
                            center="xs",
                        ),
                        dfx.Row(
                            dcc.Dropdown(
                                id="dropdown-select",
                                options=[
                                    {"label": regione, "value": codice_regione}
                                    for regione, codice_regione in zip(
                                        df_regioni["denominazione_regione"].unique(),
                                        df_regioni["denominazione_regione"].unique(),
                                    )
                                ],
                                value=[],
                                multi=True,
                                placeholder="Scegli le regioni",
                                searchable=False,
                                optionHeight=50,
                                style={"text-align": "center"},
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
                                        "label": f"{str(giorno.day).zfill(2)}/{str(giorno.month).zfill(2)}",  # /{str(giorno.year)[:2]}",
                                        "style": {
                                            "color": "#444",
                                            # "transform": "rotate(45deg)",
                                        },
                                    }
                                    for giorno in filter_dates(df["data"].unique(), 12)
                                },
                                id="date-slider",
                                # tooltip={"always_visible": True, "placement": "bottom"},
                            ),
                            center="xs",
                        ),
                    ],
                ),
                dfx.Col(
                    id="graphs-column",
                    className="dashboardColumn",
                    xs=12,
                    lg=5,
                    children=[
                        html.Div(
                            [
                                dcc.Graph(
                                    figure=get_variable_graph(
                                        df_regioni, True, False, "totale_casi"
                                    ),
                                    id="graph1",
                                    className="dashboardContainer dash-graph",
                                ),
                                dbc.Button(
                                    fullscreen_img_tag,
                                    id="graph1-fullscreen-button",
                                    n_clicks=0,
                                    className="floating-button",
                                    size="sm",
                                    outline=True,
                                ),
                                dbc.Button(
                                    "?",
                                    id="graph1-tooltip-button",
                                    n_clicks=0,
                                    className="graph-tooltip-button floating-button",
                                    size="sm",
                                    color="info",
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                dcc.Graph(
                                    figure=get_removed_graph(df_regioni, True),
                                    id="graph2",
                                    className="dashboardContainer dash-graph",
                                ),
                                dbc.Button(
                                    fullscreen_img_tag,
                                    id="graph2-fullscreen-button",
                                    n_clicks=0,
                                    className="floating-button",
                                    size="sm",
                                    outline=True,
                                ),
                                dbc.Button(
                                    "?",
                                    id="graph2-tooltip-button",
                                    n_clicks=0,
                                    className="graph-tooltip-button floating-button",
                                    size="sm",
                                    color="info",
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                dcc.Graph(
                                    figure=get_growth_rate_graph(df_regioni, True),
                                    id="graph3",
                                    className="dashboardContainer dash-graph",
                                ),
                                dbc.Button(
                                    fullscreen_img_tag,
                                    id="graph3-fullscreen-button",
                                    n_clicks=0,
                                    className="floating-button",
                                    size="sm",
                                    outline=True,
                                ),
                                dbc.Button(
                                    "?",
                                    id="graph3-tooltip-button",
                                    n_clicks=0,
                                    className="graph-tooltip-button floating-button",
                                    size="sm",
                                    color="info",
                                ),
                            ]
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
                    target=f"daily-totale_casi",
                    placement="right",
                ),
                dbc.Tooltip(
                    f"Non coincide con il numero di persone sottoposte a test, alcune persone sono state testate più volte",
                    target=f"daily-tamponi",
                    placement="right",
                ),
                dbc.Tooltip(
                    f"Visualizza correlazioni con dati storici sulla popolazione",
                    target=f"istat-button",
                    placement="bottom",
                ),
                dbc.Tooltip(
                    f"Modifica l'asse y di alcuni grafici rendendolo logaritmico. In questo modo gli andamenti esponenziali vengono visualizzati da una linea retta ",
                    target=f"logarithmic-toggle",
                    placement="bottom",
                ),
                dbc.Tooltip(
                    f"Aggrega i dati delle aree selezionate, escludendo quelle non selezionate",
                    target=f"aggregation-toggle",
                    placement="bottom",
                ),
                dbc.Tooltip(
                    [
                        html.P(
                            "Click su una regione per selezionarla",
                            className="tooltip-map-p",
                        ),
                        html.P(
                            "Shift+Click su più regioni per selezionarle",
                            className="tooltip-map-p",
                        ),
                        html.P(
                            "Doppio click su una regione pre riassunto nazionale",
                            className="tooltip-map-p",
                        ),
                        html.P("OPPURE"),
                        html.P(
                            "Usa la tendina in basso per scegliere le aree da confrontare o aggregare (In questo caso le regioni non saranno più selezionabili sulla mappa)",
                            className="tooltip-map-p",
                        ),
                    ],
                    target=f"map-info-button",
                    placement="top",
                    className="tooltip-map",
                ),
                dbc.Tooltip(
                    [
                        html.P("Clicca e trascina per zoommare"),
                        html.P("Doppio click per tornare alla vista di default"),
                    ],
                    target=f"graph1-tooltip-button",
                    placement="top",
                ),
                dbc.Tooltip(
                    [
                        html.P("Clicca e trascina per zoommare"),
                        html.P("Doppio click per tornare alla vista di default"),
                    ],
                    target=f"graph2-tooltip-button",
                    placement="top",
                ),
                dbc.Tooltip(
                    [
                        html.P("Clicca e trascina per zoommare"),
                        html.P("Doppio click per tornare alla vista di default"),
                    ],
                    target=f"graph3-tooltip-button",
                    placement="top",
                ),
                dbc.Tooltip(
                    [
                        "Persone ricoverate in terapia intensiva"
                    ],
                    target=f"daily-terapia_intensiva",
                    placement="right",
                ),
            ],
            id="tooltips-container",
            style={"display": "none"},
        ),
        dcc.Interval(
            id='interval-datapull',
            interval=2*1000, # in milliseconds
            n_intervals=0,
        ),
        dbc.Modal(
            [
                dbc.ModalBody(dcc.Graph(id="modal-graph")),
                dbc.ModalFooter(
                    dbc.Button("Chiudi", id="modal-close", className="ml-auto")
                ),
            ],
            id="fullscreen-modal",
            is_open=False,
            size="xl",
        ),
    ],
)


#######################################################################################
##################################CALLBACKS############################################
#######################################################################################


@app.callback(
    [
        Output("graph1", component_property="figure"),
        Output("graph2", component_property="figure"),
        Output("graph3", component_property="figure"),
    ],
    [
        Input("filter", component_property="data-area"),
        Input("filter", component_property="data-aggregation"),
        Input("logarithmic-toggle", component_property="on"),
        Input("filter", component_property="data-map-datatype-selected"),
        Input("istat-button", component_property="on"),
    ],
    [State("filter", component_property="data-map-type"),],
)
@cache.memoize(timeout=TIMEOUT)
def update_area_graphs(
    area_string, aggregation, logy, map_datatype_selected, istat_flag, map_type
):

    ctx = dash.callback_context
    triggerer = [x["prop_id"] for x in ctx.triggered]
    logger.debug(f"update_area_graphs triggered by {triggerer}")

    if istat_flag:
        return (
            get_respiratory_deaths_graph(morti_resp),
            get_PM10_graph(df, air_series),
            get_smokers_graph(df_regioni),
        )

    if map_type == "regioni":

        if area_string:

            area_list = area_string.split("|")
            if "Trentino Alto Adige" in area_list:
                area_list = [
                    x if x != "Trentino Alto Adige" else "P.A. Trento"
                    for x in area_list
                ]
            filter_ = df_regioni["denominazione_regione"].isin(area_list)
            filtered_data = df_regioni[filter_]

            return (
                get_variable_graph(
                    filtered_data, aggregation, logy, map_datatype_selected
                ),
                get_removed_graph(filtered_data, aggregation),
                get_growth_rate_graph(filtered_data, aggregation),
            )

        else:

            return (
                get_variable_graph(
                    df_regioni,
                    aggregate=True,
                    logy=logy,
                    datatype=map_datatype_selected,
                ),
                get_removed_graph(df_regioni, aggregate=True),
                get_growth_rate_graph(df_regioni, aggregate=True),
            )

    elif map_type == "province":
        if area_string:

            area_list = area_string.split("|")
            filter_ = df["NUTS3"].isin(area_list)
            filtered_data = df[filter_]

            return (
                get_variable_graph(filtered_data, aggregation, logy=logy),
                get_variable_graph(
                    filtered_data, aggregation, logy=logy, datatype="increased_cases"
                ),
                get_growth_rate_graph(filtered_data, aggregation),
            )

        else:

            return (
                get_variable_graph(df_regioni, aggregate=True, logy=logy),
                get_variable_graph(
                    df_regioni, aggregate=True, logy=logy, datatype="increased_cases"
                ),
                get_growth_rate_graph(df_regioni, aggregate=True),
            )
    elif map_type == None:
        return go.Figure(), go.Figure(), go.Figure()
    else:
        raise Exception(f"incorrect map-type provided (received '{map_type}')")


@app.callback(
    [
        Output("filter", component_property="data-area"),
        Output("filter", component_property="data-area-index"),
        Output("filter", component_property="data-map-type"),
    ],
    [
        Input("main-map", component_property="selectedData"),
        Input("area-map", "value"),
        Input("dropdown-select", "value"),
    ],
    [State("main-map", component_property="figure")],
)
def set_filter_location(selectedData, area_tab, dropdown_values, figure):

    ctx = dash.callback_context
    triggerer = [x["prop_id"] for x in ctx.triggered]
    logger.debug(f"set_filter_location triggered by {triggerer}")

    print(f"set_filter_location triggered by {triggerer}")
    print(selectedData)

    # If the callback was triggered by a tab click reset the selection
    if ctx.triggered[0]["prop_id"] == "area-map.value":
        return "", "", area_tab

    if "dropdown-select.value" in triggerer:
        if area_tab == "regioni":
            return (
                "|".join(dropdown_values),
                "|".join([df_regioni_map_index[x] for x in dropdown_values]),
                area_tab,
            )
        else:
            return (
                "|".join(dropdown_values),
                "|".join([df_province_map_index[x] for x in dropdown_values]),
                area_tab,
            )

    if selectedData:

        if (area_tab == "regioni") and (len(selectedData["points"]) == 20):
            return "", "", area_tab
        if (area_tab == "province") and (len(selectedData["points"]) == 107):
            return "", "", area_tab

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
@cache.memoize(timeout=TIMEOUT)
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
    [State("filter", "data-area-index"), State("dropdown-select", "value")],
)
@cache.memoize(timeout=TIMEOUT)
def update_map(ordinal_date, data_selected, area_map, preselection, dropdown_select):

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

    if dropdown_select:
        figure.update_layout(clickmode="event",)

    return figure


@app.callback(
    [Output(f"daily-{metric}", component_property="hidden") for metric in metric_list],
    [Input("filter", component_property="data-map-type")],
)
def hide_numbers(data_map_type):

    if data_map_type == "province":
        return [
            True if metric not in ["totale_casi"] else False for metric in metric_list
        ]
    else:
        return [False for metric in metric_list]


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
@cache.memoize(timeout=TIMEOUT)
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
        filtered_notes = df_notes[df_notes["dataset"] == "dati-regioni"].iloc[::-1]
        filter_area = "regione"
    elif map_type == "province":
        filtered_notes = df_notes[df_notes["dataset"] == "dati-province"].iloc[::-1]
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


@app.callback(
    Output("filter", component_property="data-aggregation"),
    [Input("aggregation-toggle", component_property="on")],
)
def set_aggregation(value):
    return value


@app.callback(
    [
        Output("aggregation-toggle", component_property="style"),
        Output("aggregation-toggle", component_property="on"),
        Output("aggregation-toggle", component_property="disabled"),
    ],
    [Input("filter", "data-area")],
)
def enable_aggregation(areas_string):

    if areas_string:
        area_list = areas_string.split("|")
        if len(area_list) > 1:

            if len(area_list) > 3:
                return {"display": ""}, True, True

            else:
                return {"display": ""}, False, False

    return {"display": "None"}, False, False


@app.callback(
    [
        Output("modal-graph", component_property="figure"),
        Output("fullscreen-modal", component_property="is_open"),
    ],
    [
        Input("graph1-fullscreen-button", "n_clicks"),
        Input("graph2-fullscreen-button", "n_clicks"),
        Input("graph3-fullscreen-button", "n_clicks"),
        Input("modal-close", "n_clicks"),
    ],
    [State("graph1", "figure"), State("graph2", "figure"), State("graph3", "figure")],
)
def open_fullscreen_graph(btn1, btn2, btn3, close_btn, fig1, fig2, fig3):

    changed_id = [p["prop_id"] for p in dash.callback_context.triggered][
        0
    ]  # returns the id of the clicked button

    if not btn1 and not btn2 and not btn3:
        return go.Figure(), False

    if "1" in changed_id:
        return fig1, True
    if "2" in changed_id:
        return fig2, True
    if "3" in changed_id:
        return fig3, True

    return go.Figure(), False


@app.callback(
    [
        Output("dropdown-select", component_property="options"),
        Output("dropdown-select", component_property="placeholder"),
    ],
    [Input("filter", component_property="data-map-type")],
)
def update_dropdown(area_type):

    if not area_type:
        return [], ""
    if area_type == "regioni":
        return region_dropdown_options, "Scegli le regioni da confrontare"
    else:
        return provinces_dropdown_options, "Scegli le province da confrontare"

@app.callback(
    Output("filter", component_property="data-refresh-intervals"),
    [Input("interval-datapull", component_property="interval")],
)
@cache.memoize(timeout=TIMEOUT)
def interval_datapull(n_intervals):
    print("#"*30)
    print("UPDATING DATAFRAME FROM GITHUB")
    print("#"*30)
    global df
    global df_regioni
    df, df_regioni, _, _, _ = get_dataset(datetime.today())
    return n_intervals

if __name__ == "__main__":
    app.run_server(debug=True)

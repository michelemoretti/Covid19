
import os
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
import math
import logging

logger = logging.getLogger('__main__')

temporal_graph_layout={
        "margin":dict(l=10, r=10, t=40, b=10),
        "title_text":'Totale Tamponi/Totale Casi Positivi',
        "xaxis" : {"calendar":"gregorian",
                "nticks":15},
        "yaxis" : {"tickformat":",d"},
        "legend" : {"xanchor":"left","yanchor":"top","x":0,"y":1,"bgcolor":"rgba(255,255,255,0.2)"},
        "title" :{"xanchor":"center", "x":0.5}        
}

def get_regional_map(df_regioni,regions_map_json,cmap,data_selected,data_selected_label,max_scale_value):

    fig = px.choropleth_mapbox(
        data_frame=df_regioni, 
        geojson=regions_map_json, 
        locations='codice_regione', 
        featureidkey='properties.reg_istat_code_num',
        color=data_selected,
        color_continuous_scale=cmap,
        range_color=(0, max_scale_value),
        hover_data=[data_selected],
        custom_data=["denominazione_regione","codice_regione"],
        mapbox_style="carto-positron",
        zoom=4.8, center = {"lat": 42.00107394, "lon": 10.3283498},
        #opacity=1,
        #animation_frame="giorno",
        labels={ data_selected:data_selected_label, 
                "giorno":"Giorno",
                'data': 'Data', "growth_rate": "Growth Rate", 
                "increased_cases": "Nuovi Casi",
                "increased_tamponi":"Nuovi Tamponi Effettuati",
                "denominazione_regione":"Regione",
                "codice_regione":"Codice Regione"},
        #height=600,
        )
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        clickmode="select+event",
        autosize=True
        #paper_bgcolor="LightSteelBlue",
    )
    return fig

def get_provincial_map(df_province,province_map_json,cmap,max_scale_value):
    fig = px.choropleth_mapbox(
        data_frame=df_province, 
        geojson=province_map_json, 
        locations='sigla_provincia', 
        featureidkey='properties.prov_acr',
        color="totale_casi",
        color_continuous_scale=cmap,
        range_color=(0, max_scale_value),
        hover_data=["denominazione_provincia"],
        custom_data=["NUTS3"],
        mapbox_style="carto-positron",
        zoom=4.8, center = {"lat": 42.00107394, "lon": 10.3283498},
        #opacity=1,
        #animation_frame="giorno",
        labels={"giorno":"Giorno",
                "totale_casi":"Totale Casi",
                'data': 'Data', "growth_rate": "Growth Rate", 
                "increased_cases": "Nuovi Casi",
                "denominazione_provincia":"Provincia",
                "sigla_provincia":"Sigla Provincia"},
        #height=600,
        )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        clickmode="select+event",
        autosize=True
        #paper_bgcolor="LightSteelBlue",
    )
    return fig

def get_tamponi_graph(filtered_data):
    fig = go.Figure()

    summed_data_by_date = filtered_data.sort_values("data").groupby("data").sum()
    
    fig.add_trace(go.Scatter(x=filtered_data.sort_values("data")["data"].dt.date.unique(), 
                            y=summed_data_by_date["totale_casi"], 
                            fill='tozeroy',
                            mode='lines+markers',
                            name="Totale Casi Positivi",
                            hovertemplate = "<b>%{x}</b><br>Totale casi positivi: %{y}<br>Percentuale casi positivi: %{text:.2f}%<extra></extra>",
                            text=(summed_data_by_date["totale_casi"]/summed_data_by_date["tamponi"]) * 100
                            ))
    fig.add_trace(go.Scatter(x=filtered_data.sort_values("data")["data"].dt.date.unique(), 
                            y=summed_data_by_date["tamponi"], 
                            fill='tonexty',
                            mode='lines+markers',
                            name="Totale Tamponi",
                            hovertemplate = "<b>%{x}</b><br>Totale tamponi effettuati: %{y}<br>Percentuale casi positivi: %{text:.2f}%<extra></extra>",
                            text=(summed_data_by_date["totale_casi"]/summed_data_by_date["tamponi"]) * 100
                            ))
    fig.update_layout(temporal_graph_layout)
    return fig
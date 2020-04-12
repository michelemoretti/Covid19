
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



def get_regional_map(df_regioni,regions_map_json,cmap,data_selected,data_selected_label,max_scale_value):
    fig = px.choropleth_mapbox(
        data_frame=df_regioni, 
        geojson=regions_map_json, 
        locations='codice_regione', 
        featureidkey='properties.reg_istat_code_num',
        color=data_selected,
        color_continuous_scale=cmap,
        range_color=(0, max_scale_value),
        hover_data=["increased_cases", "increased_tamponi",data_selected],
        custom_data=["denominazione_regione","codice_regione"],
        mapbox_style="carto-positron",
        zoom=4, center = {"lat": 42.00107394, "lon": 10.3283498},
        #opacity=1,
        #animation_frame="giorno",
        labels={ data_selected:data_selected_label, 
                "giorno":"Giorno",
                'data': 'Data', "growth_rate": "Growth Rate", 
                "increased_cases": "Nuovi Casi",
                "increased_tamponi":"Nuovi Tamponi Effettuati",
                "codice_regione":"Codice Regione"},
        height=600,
        )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        clickmode="select"
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
    fig.update_layout(
        title_text='Totale Tamponi/Totale Casi Positivi',
        xaxis = {"calendar":"gregorian",
                "nticks":15},
        yaxis = {"tickformat":",d"}
        
    )
    return fig
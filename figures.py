
import importlib
import logging
import math
import os
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats

from utils import linear_reg

logger = logging.getLogger('__main__')

temporal_graph_layout={
        "margin":dict(l=10, r=10, t=40, b=10),
        "xaxis" : {"calendar":"gregorian",
                "nticks":15},
        "legend" : {"xanchor":"left","yanchor":"top","x":0,"y":1,"bgcolor":"rgba(255,255,255,0.2)","title":None},
        "title" :{"xanchor":"center", "x":0.5},
}

colors = px.colors.qualitative.Plotly

def get_regional_map(df_regioni,regions_map_json,cmap,data_selected,data_selected_label,max_scale_value):

    fig = px.choropleth_mapbox(
        data_frame=df_regioni, 
        geojson=regions_map_json, 
        locations='codice_regione', 
        featureidkey='properties.reg_istat_code_num',
        color=data_selected,
        color_continuous_scale=cmap,
        range_color=(0, max_scale_value),
        hover_data=["denominazione_regione"],
        custom_data=["denominazione_regione","codice_regione"],
        mapbox_style="carto-positron",
        zoom=4.5, center = {"lat": 42.00107394, "lon": 10.3283498},
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
        zoom=4.5, center = {"lat": 42.00107394, "lon": 10.3283498},
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

def get_tamponi_graph(filtered_data,aggregate=True,logy=True):
    fig = go.Figure()

    if aggregate:
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
    else:
        for regione in filtered_data["denominazione_regione"].unique():
            regional_data = filtered_data[filtered_data["denominazione_regione"] == regione]
            fig.add_trace(go.Scatter(x=filtered_data.sort_values("data")["data"].dt.date.unique(), 
                                y=regional_data["tamponi"], 
                                #fill='tonexty',
                                mode='lines',
                                name=regione,
                                hovertemplate = "<b>"+regione+"</b><br><b>%{x}</b><br>Totale tamponi effettuati : %{y}<br>Percentuale casi positivi: %{text:.2f}%<extra></extra>",
                                text=(regional_data["totale_casi"]/regional_data["tamponi"]) * 100
                                ))
    fig.update_layout(temporal_graph_layout)
    fig.update_layout({"title_text":'Totale Tamponi/Totale Casi Positivi',"yaxis" : {"tickformat":",d"},})
    if logy:
        fig.update_layout({"yaxis":{"type":"log"}})
    else:
        fig.update_layout({"yaxis":{"type":"linear"}})
    return fig

def get_positive_tests_ratio_graph(filtered_data,aggregate=True):
    fig = go.Figure()

    if aggregate:

        aggregated_data = filtered_data.sort_values("data").groupby("data").sum()
        y = aggregated_data["totale_casi"]/aggregated_data["tamponi"]
        
        fig.add_trace(go.Scatter(x=aggregated_data.index.date, 
                                y=y,
                                mode='lines',
                                name="\% Tamponi Positivi",
                                
                                fill='tozeroy',
                                hovertemplate = "<b>%{x}</b><br><b>Percentuale tamponi positivi: %{text:.2f}%</b><extra></extra>",
                                text=y*100))

    else:

        for region_name in filtered_data['denominazione_regione'].unique():
            region = filtered_data[filtered_data["denominazione_regione"] == region_name]
            fig.add_trace(go.Scatter(x=region["data"].dt.date, 
                                    y=region["totale_casi/tamponi"],
                                    mode='lines',
                                    name=region_name,
                                    
                                    #fill='tozeroy',
                                    hovertemplate = "<b>"+region_name+"</b><br>"+"%{x}</b><br><b>Percentuale tamponi positivi: %{text:.2f}%<extra></extra>",
                                    text=region["totale_casi/tamponi"]*100))
    
    fig.update_layout(temporal_graph_layout)
    fig.update_layout(
        title_text='Rapporto del Totale Casi Positivi sul Totale Tamponi',
        yaxis={
            "tickformat": '%',}
    )
    return fig

def get_variable_graph(filtered_data,aggregate,logy=False,datatype="totale_casi"):

    fig = go.Figure()
    comparison_column = "denominazione_provincia" if "codice_provincia" in filtered_data.columns else "denominazione_regione"

    titles = {
    "totale_casi": "Totale Casi Confermati",
    "deceduti": "Deceduti",
    "tamponi": "Tamponi effettuati",
    "terapia_intensiva": "Terapia Intensiva",
    "totale_positivi": "Attualmente Positivi",
    "dimessi_guariti": "Guariti",
    "totale_ospedalizzati": "Ospedalizzati",
    'data': 'Data',
    'denominazione_provincia': 'Provincia',
    'denominazione_regione': 'Regione',
    "increased_cases" : "Nuovi Casi Giornalieri",
    }

    if aggregate:
        aggregated_data = filtered_data.sort_values("data").groupby("data").sum()


        fig.add_trace(
            go.Scatter(
                x=aggregated_data.index.date, 
                y=aggregated_data[datatype],
                mode='lines',
                name=titles[datatype],
                
                fill='tozeroy',
                hovertemplate = "<b>%{x}</b><br><b>"+titles[datatype]+": %{y}</b><br><b>Percentuale "+titles[datatype]+" sulla popolazione: %{text:.3f}%</b><extra></extra>",
                text=100*aggregated_data[datatype]/aggregated_data["Popolazione_Sesso_totale"],
            )
        )
        fig.update_layout(title=titles[datatype])

    else:
        fig = px.line(  
            data_frame=filtered_data,
            x="data",
            y=datatype,
            log_y=logy,
            #hover_data=[datatype],
            color=comparison_column,
            title=titles[datatype], 
            labels=titles
        )
    
    log_type = "log" if logy else "linear"
    fig.update_layout(temporal_graph_layout)
    fig.update_layout(
        yaxis={"title":None,"type":log_type},
        xaxis={"title":None},
    )

    return fig

def get_growth_rate_graph(filtered_data,aggregate):

    fig = go.Figure()

    comparison_column = "denominazione_provincia" if "codice_provincia" in filtered_data.columns else "denominazione_regione"

    if aggregate:
        
        filtered_data = filtered_data[filtered_data["data"] > datetime(2020,2,29)]
        aggregated_data = filtered_data.groupby("data").sum()
        aggregated_data['growth_rate'] = aggregated_data["increased_cases"] / aggregated_data["increased_cases"].shift(1)
        aggregated_data['smooth_growth_rate'] = aggregated_data['growth_rate'].rolling(min_periods=1,window=3).mean()
        aggregated_data = aggregated_data.reset_index()

        fig.add_trace(go.Scatter(
            x=filtered_data["data"].dt.date.unique(), 
            y=[1 for x in filtered_data["data"].unique()],
            mode='lines',
            name="Limite crescita esponenziale",
            #fill='tozeroy',
            line = dict(dash='dot'),
            hovertemplate = "Limite Crescita Esponenziale (Fattore di Crescita = 1)</b><extra></extra>",
            marker=go.scatter.Marker(color=colors[1]),
            )
        )
        fig.add_trace(go.Scatter(
            x=aggregated_data["data"].dt.date, 
            y=aggregated_data["smooth_growth_rate"],
            mode='lines',
            name="Fattore di Crescita",
            fill='tonexty',
            hovertemplate = "<b>Fattore di crescita: %{text:.2f}</b><extra></extra>",
            text=aggregated_data["smooth_growth_rate"],
            marker=go.scatter.Marker(color=colors[0]),
            )
        )
        

    else:

        fig = px.line(data_frame=filtered_data,#filtered_data[filtered_data["data"] > datetime(2020,3,4)],
                    x="data",
                    y="smooth_growth_rate",
                    hover_data=["increased_cases","denominazione_regione"],
                    log_y=False,
                    color=comparison_column,
                    title="Fattore di Crescita medio ultimi 3gg", 
                    labels={'increased_cases':'Nuovi casi positivi', 'data': 'Data', 'denominazione_regione': 'Regione',"smooth_growth_rate":"Fattore di Crescita"})

        fig.update_traces(mode='lines',hovertemplate = "<b>Fattore di crescita: %{y:.2f}</b><extra></extra>")
    
    
    
    fig.update_layout(temporal_graph_layout)
    fig.update_layout(
        title_text='Fattore di Crescita medio ultimi 3gg',
        yaxis={"title":None},
        xaxis={"title":None},
    )
    return fig

def get_respiratory_deaths_graph(morti_resp):

    morti_2017 = int(morti_resp[morti_resp["Year"]==2017]["Value"].tolist()[0])

    #Non essendoci dati 2020 proiettiamo ad oggi quelli del 2017
    proiezione_morti_2020 = (morti_2017 * int(datetime.now().timetuple().tm_yday))/365

    fig = go.Figure(data=[
        go.Bar(name='Decessi Malattie Respiratorie', x=morti_resp['Year'], y=morti_resp['Value'],),
        go.Bar(name='Decessi Malattie Respiratorie (proiezione ad oggi)', x=[2020], y=[proiezione_morti_2020],marker_color=colors[2]),
        go.Bar(name='Decessi COVID-19', x=morti_resp['Year'], y=morti_resp['Covid'],marker_color=colors[1])
    ])
    fig.update_layout(temporal_graph_layout)
    fig.update_layout(barmode='stack', legend={"xanchor":"center","yanchor":"top","x":0.5,"y":1,"bgcolor":"rgba(255,255,255,0.5)"},)
    fig.update_layout({"title_text":'Decessi per malattie respiratorie'})
    return fig

def get_removed_graph(filtered_data,aggregate=True,logy=True):
    
    fig = go.Figure()

    if aggregate:
        summed_data_by_date = filtered_data.sort_values("data").groupby("data").sum()
        
        fig.add_trace(go.Scatter(x=filtered_data.sort_values("data")["data"].dt.date.unique(), 
                                y=summed_data_by_date["deceduti"]/summed_data_by_date["totale_casi"], 
                                fill='tozeroy',
                                mode='lines',
                                name="Deceduti/Contagi",
                                hovertemplate = "<b>%{x}</b><br>Deceduti: %{y}<extra></extra>",
                                #text=,
                                line = dict(dash='dot'),
                                marker=go.scatter.Marker(color=colors[1]),
                                ))
        fig.add_trace(go.Scatter(x=filtered_data.sort_values("data")["data"].dt.date.unique(), 
                                y=summed_data_by_date["dimessi_guariti"]/summed_data_by_date["totale_casi"], 
                                fill='tonexty',
                                mode='lines',
                                name="Guariti/Contagi",
                                hovertemplate = "<b>%{x}</b><br>Guariti: %{y}<extra></extra>",
                                marker=go.scatter.Marker(color=colors[0]),
                                #text=,
                                ))
    else:

        for idx,regione in enumerate(filtered_data["denominazione_regione"].unique()):
            regional_data = filtered_data[filtered_data["denominazione_regione"] == regione]
            fig.add_trace(go.Scatter(x=filtered_data.sort_values("data")["data"].dt.date.unique(), 
                                y=regional_data["dimessi_guariti"]/regional_data["totale_casi"], 
                                #fill='tonexty',
                                mode='lines',
                                name=regione,
                                hovertemplate = "<b>"+regione+"</b><br>%{x}<br>Guariti: %{y}<extra></extra>",
                                #text=,
                                marker=go.scatter.Marker(color=colors[idx]),
                                ))
            fig.add_trace(go.Scatter(x=filtered_data.sort_values("data")["data"].dt.date.unique(), 
                                y=regional_data["deceduti"]/regional_data["totale_casi"], 
                                #fill='tonexty',
                                mode='lines',
                                name=regione,
                                hovertemplate = "<b>"+regione+"</b><br>%{x}<br>Guariti: %{y}<extra></extra>",
                                #text=,
                                line = dict(dash='dot'),
                                showlegend =False,
                                marker=go.scatter.Marker(color=colors[idx]),
                                ))
    fig.update_layout(temporal_graph_layout)
    fig.update_layout({"title_text":'Guariti/Deceduti per contagiato',"yaxis" : {"tickformat":"%"},})
   
    return fig

def traces_punti_e_trend(x_data, y_data, idx, hovertemplate, text, name='data'):

    line_x, line_y, r_value, mape = linear_reg(x_data, y_data)

    trace_line = go.Scatter(
                        x=line_x,
                        y=line_y,
                        mode='lines',
                        hovertemplate = f"Trend:<br><b>R^2</b> : {str(round((r_value**2)*100, 2))}% <br><b>MAPE</b> : {str(round(mape, 2))}%  <extra></extra>",
                        legendgroup='group'+str(idx),
                        showlegend =False,
                        marker=go.scatter.Marker(color=colors[idx]))

    trace_markers = go.Scatter(
                        x=x_data, 
                        y=y_data,
                        mode='markers',
                        hovertemplate = hovertemplate,
                        text=text,
                        name=name,
                        showlegend =False,
                        legendgroup='group'+str(idx),
                        marker=go.scatter.Marker(color=colors[idx]))
    return trace_line, trace_markers

def get_PM10_graph(df_province, air_series):

    fig = go.Figure()
    filtered_province_today = df_province[df_province["data"] == df_province["data"].max()].set_index('NUTS3')
    filtered_province_today = filtered_province_today.drop(columns=[x for x in filtered_province_today.columns if not x in ["totale_casi", "Popolazione_ETA1_Total", "denominazione_provincia"]]).join(air_series, rsuffix='_other').drop(columns=['denominazione_regione', "COMUNI", "NUTS3_regione", "CODICE PROVINCIA"])
    all_columns = [x for x in filtered_province_today.columns if "PM10" in x ]
    prov_data = (filtered_province_today["totale_casi"]/filtered_province_today["Popolazione_ETA1_Total"]).rename('totale_casi_procapite')*100

    prov_data = pd.concat([filtered_province_today.denominazione_provincia, prov_data, filtered_province_today[all_columns[0]], filtered_province_today[all_columns[1]]], axis=1)

    prov_data_zero = prov_data.drop(prov_data[all_columns[0]][prov_data[all_columns[0]] == 0].index)

    line, markers = traces_punti_e_trend(prov_data_zero.totale_casi_procapite, prov_data_zero[all_columns[0]], 0, "<b>%{text}</b><br>Casi Positivi procapite confermati: %{x:.3f}%<br>Giorni sopra il limite consigliato: %{y}<extra></extra>", prov_data_zero.denominazione_provincia)
    fig.add_trace(line)
    fig.add_trace(markers)

    fig.add_trace(go.Scatter(
                x=np.arange(start=0, stop=2, step=0.1),
                y=[35,]*20,
                mode='lines',
                line = dict(dash='dot'),
                showlegend =False,
                hovertemplate='Limite di giorni sopra limite consigliati<extra></extra>')
    )
    fig.update_layout(
        title = "Inquinamento Aria (Giorni PM10 > limite consigliato) / Casi positivi",
        )
    fig.update_layout({
        "margin":dict(l=10, r=10, t=40, b=10),
        "legend" : {"xanchor":"left","yanchor":"top","x":0,"y":1,"bgcolor":"rgba(255,255,255,0.2)"},
        "title" :{"xanchor":"center", "x":0.5},
    })
    return fig

def get_smokers_graph(df_regioni):
    
    fig = go.Figure()
    filtered_regioni_today = df_regioni[df_regioni["data"] == df_regioni["data"].max()].set_index('NUTS3')

    filtered_regioni_today['Popolazione_ETA1_61-100+'] = filtered_regioni_today['Popolazione_ETA1_61-70']  + filtered_regioni_today['Popolazione_ETA1_71-80'] + filtered_regioni_today['Popolazione_ETA1_81-90'] + filtered_regioni_today['Popolazione_ETA1_91-100+']
    filtered_regioni_today = filtered_regioni_today.drop(columns=[x for x in filtered_regioni_today.columns if not x in ["deceduti", "totale_casi", "Popolazione_ETA1_61-100+", "Popolazione_ETA1_Total", "denominazione_regione"]])
    prov_data = (filtered_regioni_today["deceduti"]/filtered_regioni_today["totale_casi"]).rename('decessi_su_totale_casi')*100

    prov_data = pd.concat([filtered_regioni_today.denominazione_regione, prov_data, filtered_regioni_today["Popolazione_ETA1_61-100+"].div(filtered_regioni_today["Popolazione_ETA1_Total"],axis=0).rename("pop_rischio")*100], axis=1)

    line, markers = traces_punti_e_trend(prov_data.decessi_su_totale_casi, prov_data["pop_rischio"], 0, "<b>%{text}</b><br>Decessi su casi positivi confermati: %{x:.2f}%<br>Percentuale popolazione a rischio: %{y:.2f}%<extra></extra>", prov_data.denominazione_regione)
    fig.add_trace(line)
    fig.add_trace(markers)

    fig.update_layout(
        title = "Correlazione tra Tasso di letalità e popolazione in età avanzata",
        )

    fig.update_layout({
        "margin":dict(l=10, r=10, t=40, b=10),
        "legend" : {"xanchor":"left","yanchor":"top","x":0,"y":1,"bgcolor":"rgba(255,255,255,0.2)"},
        "title" :{"xanchor":"center", "x":0.5},
    }
    )
    return fig
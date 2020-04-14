import csv
import json
import math
import os
import random
from datetime import date, datetime, timedelta

import analytics
import geojson
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import scipy
import streamlit as st

import st_state_patch
from utils import (calculate_line, exp_viridis, get_dataset, get_map_json,
                   linear_reg, mean_absolute_percentage_error, pretty_colors,
                   viridis)

analytics_token = open(".analytics_token").read()
analytics.write_key = analytics_token

session_state = st.SessionState()
if not session_state:
    session_state.user = random.randint(1,9999999999)

USER_UNIQUE_ID = session_state.user



hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        </style>
        """
styling = """
        <style>
        .reportview-container .main .block-container {padding-top: 1rem !important; padding-bottom: 0 !important;}
        .reportview-container .element-container {margin-bottom:0.5rem !important;}
        .footer  {margin-top:0.3rem;}
        .footer p {font-size:0.8rem !important; margin-bottom:0 !important;}
        .smallText {font-size: 0.8rem !important; text-align:justify !important;}
        .marginTop {margin-top: 0.5rem !important;}
        .portraitAlert{
                display:None !important;
            }
        @media only screen and (max-width:600px) and (orientation: portrait) {
            hr.portraitAlert{
                display:block !important;
            }
            p.portraitAlert{
                font-weight: 900 !important;
                display: block !important;
                background-color: #ffffb1 !important;
                border: 1px solid #ccc !important;
                text-align: center !important;
                padding: 5px !important;
                border-radius: 20px !important;
                margin-top: 5px !important;
            }
        }
        </style>

"""

intro_text = """
        Questa pagina è nata dalla volontà di integrare i dati forniti dalla [Protezione Civile](https://github.com/pcm-dpc/COVID-19) con i database pubblici [ISTAT](http://dati.istat.it). L’obiettivo è quello di trovare possibili correlazioni tra indicatori ambientali, geografici e demografici e i dati sulla diffusione del virus.
        \n**Qui sopra** è possibile visualizzare l’andamento dei dati principali in una mappa animata. Premere play per ripercorrere l’andamento nazionale dal 24 Febbraio ad oggi
        \nNel **menu a sinistra** è possibile visualizzare molte altre metriche tra cui la comparazione diretta tra Regioni o Province italiane o la correlazione tra gli indicatori ISTAT e i dati sul COVID-19.
"""

logo_html = "<p style='text-align: center;'><a target='_blank' href='https://www.neurality.it' target='_blank' rel='noopener noreferrer'><img width='100px'alt='Neurality Logo' src='http://neurality.it/images/logo_small_black.png'></a></p>"
subtitle_html = "<h2 style='text-align: center;color: rgb(246, 51, 102);'><a target='_blank' href='https://github.com/pcm-dpc/COVID-19' target='_blank' rel='noopener noreferrer' style='color: rgb(246, 51, 102);'>Covid19 Data Analysis</a></h2>"
#st.markdown(hide_menu_style, unsafe_allow_html=True)
st.markdown(styling, unsafe_allow_html=True)
st.write('<style>div.Widget.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)


@st.cache(show_spinner=False)
def get_areas(df):
    regions = df["denominazione_regione"].unique()
    provinces = df["denominazione_provincia"].unique()
    return regions,provinces

def calcolo_giorni_da_min_positivi(df_regioni, min_positivi=100):
    regione_piu_colpita = df_regioni[df_regioni["data"] == df_regioni["data"].max()][df_regioni["totale_casi"] == df_regioni["totale_casi"].max()]["denominazione_regione"].tolist()[0]
    temp = df_regioni[df_regioni["totale_casi"] > min_positivi]
    temp = temp[temp["denominazione_regione"] == regione_piu_colpita]
    return len(temp['data'].tolist())

@st.cache(suppress_st_warning=True,show_spinner=False)
def get_regional_map(df_regioni,regions_map_json,cmap,data_selected,data_selected_label):
    fig = px.choropleth_mapbox(
                            data_frame=df_regioni, 
                            geojson=regions_map_json, 
                            locations='codice_regione', 
                            featureidkey='properties.reg_istat_code_num',
                            color=data_selected,
                            color_continuous_scale=cmap,
                            range_color=(0, math.ceil(df_regioni[data_selected].max()+1)),
                            hover_data=["increased_cases", "increased_tamponi",data_selected],
                            mapbox_style="carto-positron",
                            zoom=4, center = {"lat": 42.00107394, "lon": 10.3283498},
                            #opacity=1,
                            animation_frame="giorno",
                            labels={ data_selected:data_selected_label, 
                                    "giorno":"Giorno",
                                    'data': 'Data', "growth_rate": "Growth Rate", 
                                    "increased_cases": "Nuovi Casi",
                                    "increased_tamponi":"Nuovi Tamponi Effettuati",
                                    "codice_regione":"Codice Regione"},
                            height=600,
                          )
    return fig
@st.cache(suppress_st_warning=True,show_spinner=False)
def get_provincial_map(df_province,province_map_json,cmap):
    fig = px.choropleth_mapbox(
                            data_frame=df_province, 
                            geojson=province_map_json, 
                            locations='sigla_provincia', 
                            featureidkey='properties.prov_acr',
                            color='totale_casi',
                            color_continuous_scale=cmap,
                            range_color=(0, math.ceil(df_province['totale_casi'].max()+1)),
                            hover_data=["growth_rate","increased_cases"],
                            mapbox_style="carto-positron",
                            zoom=4, center = {"lat": 42.00107394, "lon": 10.3283498},
                            #opacity=1,
                            animation_frame="giorno",
                            labels={"giorno":"Giorno",
                                    "totale_casi":"Totale Casi",
                                    'data': 'Data', "growth_rate": "Growth Rate", 
                                    "increased_cases": "Nuovi Casi",
                                    "increased_tamponi":"Nuovi Tamponi Effettuati",
                                    "sigla_provincia":"Sigla Provincia"},
                            height=600,
                          )
    return fig

@st.cache(allow_output_mutation=True,show_spinner=False)
def fig_tamponi_vs_positivi(filtered_data):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=filtered_data["data"], 
                            y=filtered_data["totale_casi"], 
                            fill='tozeroy',
                            #mode='lines+markers',
                            name="Totale Casi Positivi",
                            hovertemplate = "<b>%{x}</b><br><b>Totale casi positivi: %{y}</b><br><b>Percentuale tamponi per casi positivi: %{text:.2f}%</b><extra></extra>",
                            text=filtered_data["totale_casi/tamponi"] * 100
                            ))
    fig.add_trace(go.Scatter(x=filtered_data["data"], 
                            y=filtered_data["tamponi"], 
                            fill='tonexty',
                            #mode='lines+markers',
                            name="Totale Tamponi",
                            hovertemplate = "<b>%{x}</b><br><b>Totale tamponi effettuati: %{y}</b><extra></extra>",
                            text=filtered_data["totale_casi/tamponi"] * 100
                            ))
    fig.update_layout(
        title_text='Totale Tamponi comparato con Totale Casi Positivi'
    )
    return fig

@st.cache(allow_output_mutation=True,show_spinner=False)
def fig_totale_casi_regione(filtered_data,log_y):
    fig = px.line(  data_frame=filtered_data,x="data",
                    y="totale_casi",
                    hover_data=["increased_cases"],
                    log_y=log_y,
                    color='denominazione_regione',
                    title="Totale Casi per giorno", 
                    labels={'totale_casi':'Casi confermati', 'data': 'Data', 'denominazione_regione': 'Regione', "increased_cases": "Nuovi Casi"})
    return fig.update_traces(mode='lines+markers')

@st.cache(allow_output_mutation=True,show_spinner=False)
def fig_totale_casi_provincia(filtered_data,log_y):
    fig = px.line(  data_frame=filtered_data,
                    x="data",
                    y="totale_casi",
                    log_y=log_y,
                    hover_data=["increased_cases"],
                    color='denominazione_provincia',
                    title="Totale Casi per giorno", 
                    labels={'totale_casi':'Casi confermati', 'data': 'Data', 'denominazione_provincia': 'Provincia', "increased_cases": "Nuovi Casi"})
    return fig.update_traces(mode='lines+markers')


@st.cache(allow_output_mutation=True,show_spinner=False)
def fig_totale_casi_su_tamponi(filtered_data):
    fig = go.Figure()
           
    for region_name in filtered_data['denominazione_regione'].unique():
        region = df_regioni[df_regioni["denominazione_regione"].isin([region_name])].reset_index()
        fig.add_trace(go.Scatter(x=region["data"], 
                                y=region["totale_casi/tamponi"]*100,
                                #mode='lines+markers',
                                name=region_name,
                                line_shape='vh',
                                fill='tozeroy',
                                hovertemplate = "<b>%{x}</b><br><b>Percentuale tamponi per casi positivi: %{text:.2f}%</b><extra></extra>",
                                text=region["totale_casi/tamponi"]*100))
    fig.update_layout(
        title_text='Rapporto del Totale Casi Positivi sul Totale Tamponi'
    )
    return fig

@st.cache(allow_output_mutation=True,show_spinner=False)
def fig_nuovi_casi_giornalieri(filtered_data):
    fig = px.line(
        data_frame=filtered_data,
        x="data",
        y="increased_cases",
        color='denominazione_provincia',
        title="Nuovi Casi al giorno", 
        labels={'increased_cases':'Nuovi Casi', 'data': 'Data', 'denominazione_provincia': 'Provincia'})
    return fig.update_traces(mode='lines+markers')

@st.cache(allow_output_mutation=True,show_spinner=False)
def traces_punti_e_trend(x_data, y_data, idx, hovertemplate, text, name='data'):
           
    line_x, line_y, r_value, mape = linear_reg(x_data, y_data)

    trace_line = go.Scatter(
                        x=line_x,
                        y=line_y,
                        mode='lines',
                        hovertemplate = f"Trend:<br><b>R^2</b> : {str(round((r_value**2)*100, 2))}% <br><b>MAPE</b> : {str(round(mape, 2))}%  <extra></extra>",
                        legendgroup='group'+str(idx),
                        showlegend =False,
                        marker=go.scatter.Marker(color=pretty_colors[idx]))
    
    trace_markers = go.Scatter(
                        x=x_data, 
                        y=y_data,
                        mode='markers',
                        hovertemplate = hovertemplate,
                        text=text,
                        name=name,
                        legendgroup='group'+str(idx),
                        marker=go.scatter.Marker(color=pretty_colors[idx]))
    return trace_line, trace_markers

mapbox_token = open(".mapbox_token").read()
px.set_mapbox_access_token(mapbox_token)

ISTAT_layout = go.Layout(
            {"hoverlabel_align" : 'left',
            "title" : "Analisi Correlazione Imprese/COVID",
            "autosize":False,
                    "height":600,
                    "legend":{"tracegroupgap":1,
                            "y":-0.2,
                            "xanchor":"left",
                            "x":0,
                            "yanchor":"top",
                            }})

st.sidebar.image("http://neurality.it/images/logo_small_black.png", width = 100)
st.sidebar.markdown("<hr/>",unsafe_allow_html=True)
#st.markdown("[![Foo](http://neurality.it/images/logo_new_small.png)](https://www.neurality.it)")
#st.markdown("## [Covid19 Data Analysis](https://github.com/pcm-dpc/COVID-19)")
st.markdown(logo_html, unsafe_allow_html=True)
st.markdown(subtitle_html, unsafe_allow_html=True)
        
df, df_regioni, smokers_series, imprese_series, air_series  = get_dataset(date.today())

province_map_json,regions_map_json = get_map_json()
regions,provinces = get_areas(df)

#area_filter = st.sidebar.selectbox("Seleziona il raggio di interesse",["Nazione","Regione","Provincia"])
area_filter = st.sidebar.radio("Seleziona il raggio di interesse",["Nazione","Regione","Provincia"])
st.markdown("<hr class='portraitAlert'/><p class='portraitAlert'>Per visualizzare i grafici si consiglia di orientare il telefono in orizzontale</p>",unsafe_allow_html=True)

if area_filter == "Nazione":
    
    st.markdown("---")
    analytics.page(session_state.user,"Main_category",'Nazionale',{
    'path': '/',
    'name': "Nazionale",
    'title': "Neurality - Streamlit",
    "url": "http://neurality.it/covid/Nazionale"
    })


    cmap = st.sidebar.radio("Scelta Color Map", ("Lineare", "Esponenziale"),index=1)
    st.sidebar.markdown("<p class='smallText marginTop'>Per un approfondimento sull'utilizzo di scale esponenziali per visualizzare l'andamento del virus clicca <a target='_blank' href=https://www.neodemos.info/articoli/la-curva-dei-contagiati-da-covid-19-la-ricerca-del-punto-di-svolta/>qui</a></p>",unsafe_allow_html=True)

    if cmap == "Lineare":
        cmap = viridis
    else:
        analytics.track(USER_UNIQUE_ID, "Exponential Map Scale", {
                'category':'Values_Scale',
            })
        giorni_da_min_positivi = calcolo_giorni_da_min_positivi(df_regioni)
        viridis_exp_scale = exp_viridis(giorni_da_min_positivi)
        cmap = viridis_exp_scale
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Incrocia i Dati ISTAT con i dati del Ministero della Salute**")
    fumatori_switch = st.sidebar.checkbox("Fumatori",False)
    air_switch = st.sidebar.checkbox("Inquinamento Aria",False)
    imprese_switch = st.sidebar.checkbox("Imprese",False)
    ISTAT_switches = [fumatori_switch,imprese_switch]
    ISTAT_switches_labels = ["Fumatori","Imprese"]
    df_province = df

    nation_view = st.radio("Vista per ", ("Regioni", "Province"))

    if nation_view == "Regioni":
        def format_func_select(input_option):
            data = {'totale_casi':'Casi Confermati', 'data': 'Data',"terapia_intensiva": "Ricoverati in terapia intensiva",
            "totale_ospedalizzati": "Totale ospedalizzati", "isolamento_domiciliare": "Persone in isolamento domiciliare", "totale_positivi": "Totale attualmente positivi (ospedalizzati + isolamento domiciliare)", 
            "dimessi_guariti": "Persone dimesse guarite", "deceduti": "Persone decedute", "tamponi": "Totale tamponi effettuati"}
            return data[input_option]


        data_selected = st.selectbox("Seleziona il dato da visualizzare",["totale_casi","terapia_intensiva","totale_ospedalizzati", "isolamento_domiciliare", "totale_positivi", "dimessi_guariti", "deceduti", "tamponi"], format_func=format_func_select)
        
        if data_selected != "totale_casi":
            analytics.track(USER_UNIQUE_ID, format_func_select(data_selected), {
                    'category':'Map Data Category',
                })
        fig = get_regional_map(df_regioni,regions_map_json,cmap,data_selected,format_func_select(data_selected))
    else:
        analytics.track(USER_UNIQUE_ID, "Provincie", {
                    'category':'Map Data Category',
                })
        fig = get_provincial_map(df_province,province_map_json,cmap)
    st.plotly_chart(fig,use_container_width=True)

    st.markdown("---")
    st.markdown(intro_text)

    if True in ISTAT_switches:
        st.markdown("---")

        st.markdown("## Visualizzazione indicatori ISTAT")
        st.markdown("""
        Qui puoi visualizzare le correlazioni tra gli indicatori regionali forniti dall'[ISTAT](http://dati.istat.it)\n 
        I punti nei grafici qui sotto rappresentano gli indicatori per regione, mentre la linea rappresenta la migliore approssimazione lineare dell'andamento dei punti.\n
        Ad ogni distribuzione di punti corrisponde una linea che ne approssima l'andamento per facilitarne la lettura.\n
        Muovendo il mouse su questa linea è possibile visualizzare **quanto si distacca l'approssimazione dai dati reali** ([*MAPE*](https://it.qwe.wiki/wiki/Mean_absolute_percentage_error)) e **quanto gli indicatori sono correlati ai dati di diffusione del COVID-19** ([*R^2*](https://it.wikipedia.org/wiki/Coefficiente_di_determinazione))
        """)
        

    if fumatori_switch:

        st.markdown("---")
        st.markdown("### Analisi Indicatori Fumo")
        analytics.track(USER_UNIQUE_ID, "Fumatori", {
                'category':'ISTAT Selected',
            })
        
        df_regioni_today = df_regioni.set_index("NUTS3")
        df_regioni_today = df_regioni_today[df_regioni_today["data"] == df_regioni_today["data"].max()]

        df_regioni_today = df_regioni_today.join(smokers_series)

        scelta_dati_fumatori = [x for x in df_regioni_today.columns if "Fumatori" in x]
        
        selected_columns = st.multiselect(
                        label="Scegli dati sul fumo da visualizzare per regione",
                        options=scelta_dati_fumatori,
                        format_func=lambda x:x.split("_")[-1],
                        default=[scelta_dati_fumatori[4],scelta_dati_fumatori[7]])
        #selected_columns = st.selectbox(label="Scegli dati sul fumo da visualizzare per regione",options=scelta_dati_fumatori)
        fig = go.Figure(layout=ISTAT_layout)
                                
        for idx, column in enumerate(selected_columns):

            line_x, line_y, r_value, mape = linear_reg(df_regioni_today["deceduti"]/df_regioni_today["totale_casi"], df_regioni_today[column])

            fig.add_trace(go.Scatter(
                                x=line_x,
                                y=line_y,
                                mode='lines',
                                hovertemplate = f"<b>R^2</b> : {str(round((r_value**2)*100, 2))}% <br><b>MAPE</b> : {str(round(mape, 2))}%  <extra></extra>",
                                legendgroup=column,
                                showlegend =False,
                                marker=go.scatter.Marker(color=pretty_colors[idx]))
            )


            fig.add_trace(go.Scatter(
                                x=df_regioni_today["deceduti"]/df_regioni_today["totale_casi"], 
                                y=df_regioni_today[column],
                                mode='markers',
                                hovertemplate = "<b>%{text}</b><br>Deceduti per contagiati confermati: %{x:.2f}%<br>"+column.split("_")[-1]+": %{y:.2f}%<extra></extra>",
                                text=df_regioni_today["denominazione_regione"],
                                name=column.split("_")[-1][:34],
                                legendgroup=column,
                                marker=go.scatter.Marker(color=pretty_colors[idx]))
            )
        fig.update_layout(
            title = "Analisi Correlazione Fumatori/COVID",
            )
        fig.update_xaxes(title_text='% popolazione deceduta per casi confermati')
        fig.update_yaxes(title_text='Metrica selezionata')
        st.plotly_chart(fig,use_container_width=True)

    if air_switch:

        st.markdown("---")
        st.markdown("### Analisi Indicatori Qualità dell'Aria")

        air_reg_series = air_series.drop(columns=["CODICE PROVINCIA", "COMUNI"]).pivot_table(index='NUTS3_regione')

        analytics.track(USER_UNIQUE_ID, "Aria", {
                'category':'ISTAT Selected',
            })
        
        df_regioni_today = df_regioni.set_index("NUTS3")
        df_regioni_today = df_regioni_today[df_regioni_today["data"] == df_regioni_today["data"].max()]

        df_regioni_today = df_regioni_today.join(air_reg_series)

        scelta_dati_aria = ["PM10", "PM2.5"]
        
        selected_cat = st.radio(
                        label="Scegli quali dati sul inquinamento dell'aria da visualizzare per regione ",
                        options=scelta_dati_aria)        

        all_columns = [x for x in air_reg_series.columns if selected_cat in x ]
        if selected_cat == 'PM10':
            idx = 0
            df_regioni_today = df_regioni_today.drop(df_regioni_today[all_columns[idx]][df_regioni_today[all_columns[idx]] == 0].index)
            fig = go.Figure()
            line, markers = traces_punti_e_trend(df_regioni_today["totale_casi"]/df_regioni_today["Popolazione_ETA1_Total"], df_regioni_today[all_columns[idx]], idx, "<b>%{text}</b><br>Casi Positivi procapite confermati: %{x:.3f}%<br>Giorni sopra il limite consigliato %{y}<extra></extra>", df_regioni_today['denominazione_regione'])
            fig.add_trace(line)
            fig.add_trace(markers)
            fig.update_layout(
                title = "Inquinamento Aria (giorni con PM10 superiore al limite consigliato) / COVID",
                )
            fig.update_xaxes(title_text='Contagi Procapite')
            fig.update_yaxes(title_text='Giorni al di sopra del limite consigliato - 50 μg/m^3')
            fig.add_trace(go.Scatter(
                        x=np.arange(0,0.009, 0.001),
                        y=[35,]*9,
                        mode='lines',
                        showlegend =False,
                        hovertemplate='Limite di giorni sopra limite consigliati<extra></extra>')
            )
            st.plotly_chart(fig,use_container_width=True)

            idx = 1
            df_regioni_today = df_regioni_today.drop(df_regioni_today[all_columns[idx]][df_regioni_today[all_columns[idx]] == 0].index)
            fig = go.Figure()
            line, markers = traces_punti_e_trend(df_regioni_today["totale_casi"]/df_regioni_today["Popolazione_ETA1_Total"], df_regioni_today[all_columns[idx]], idx, "<b>%{text}</b><br>Casi Positivi procapite confermati: %{x:.3f}%<br>Media Annuale PM10 %{y}<extra></extra>", df_regioni_today['denominazione_regione'])
            fig.add_trace(line)
            fig.add_trace(markers)
            fig.update_layout(
                title = "Inquinamento Aria (valore annuale medio) PM10 / COVID",
                )
            fig.update_xaxes(title_text='Contagi Procapite')
            fig.update_yaxes(title_text='Valore medio annuale [μg/m^3]')

            fig.add_trace(go.Scatter(
                        x=np.arange(0,0.009, 0.001),
                        y=[40,]*9,
                        mode='lines',
                        showlegend =False,
                        hovertemplate='Limite di emissioni consigliato<extra></extra>')
            )
            st.plotly_chart(fig,use_container_width=True)
        else:
            idx = 0
            df_regioni_today = df_regioni_today.drop(df_regioni_today[all_columns[idx]][df_regioni_today[all_columns[idx]] == 0].index)
            fig = go.Figure()
            line, markers = traces_punti_e_trend(df_regioni_today["totale_casi"]/df_regioni_today["Popolazione_ETA1_Total"], df_regioni_today[all_columns[idx]], idx, "<b>%{text}</b><br>Casi Positivi procapite confermati: %{x:.3f}%<br>Media Annuale PM10 %{y}<extra></extra>", df_regioni_today['denominazione_regione'])
            fig.add_trace(line)
            fig.add_trace(markers)
            fig.update_layout(
                title = "Analisi Correlazione Inquinamento Aria (valore annuale medio) PM2.5 / COVID",
                )
            fig.add_trace(go.Scatter(
                        x=np.arange(0,0.009, 0.001),
                        y=[25,]*9,
                        mode='lines',
                        showlegend =False,
                        hovertemplate='Limite di emissioni consigliato<extra></extra>')
            )
            fig.update_xaxes(title_text='Contagi Procapite')
            fig.update_yaxes(title_text='Valore medio annuale')
            st.plotly_chart(fig,use_container_width=True)
    
    if imprese_switch:

        st.markdown("---")
        st.markdown("### Analisi Indicatori Imprese")

        analytics.track(USER_UNIQUE_ID, "Imprese", {
                'category':'ISTAT Selected',
            })
        df_regioni_today = df_regioni.set_index("NUTS3")
        df_regioni_today = df_regioni_today[df_regioni_today["data"] == df_regioni_today["data"].max()]

        df_regioni_today = df_regioni_today.join(imprese_series)

        with open(os.path.join("ISTAT_DATA","Imprese_metadata.json"), encoding="utf-8") as json_file:
            json_dict = json.load(json_file)
        with open(os.path.join("ISTAT_DATA","DICA_ASIAUE1P_02042020145705482_metadata.json")) as json_file:
            procapite_data = json.load(json_file)["data_type_pro_capite"]

        scelta_dati_imprese = list(json_dict.keys())
        
        selected_column = st.selectbox(
                        label="Scegli dati sulle imprese per regione",
                        options=scelta_dati_imprese,
                        index=1)

        all_segments = st.multiselect(
                        label="Scegli dati sulle imprese da visualizzare per regione",
                        options= json_dict[selected_column],
                        format_func=lambda x:x.split("_")[-1],
                        default=[ json_dict[selected_column][0], json_dict[selected_column][1]])

        selected_data_type = st.radio("Scegli l'indicatore da visualizzare",('numero imprese attive', 'numero addetti delle imprese attive (valori medi annui)'))

        #all_segments = json_dict[selected_column]

        fig = go.Figure(layout=ISTAT_layout)
        pro_capite_text = ""

        for idx, segment in enumerate(all_segments):
            pro_capite = procapite_data[selected_data_type] #<- sempre True per ora

            if pro_capite:
                y = df_regioni_today[f"{selected_data_type}_{selected_column}_{segment}"]/df_regioni_today["Popolazione_Sesso_totale"]
                pro_capite_text = "pro capite "
            else:
                y = df_regioni_today[f"{selected_data_type}_{selected_column}_{segment}"]

            line_x, line_y, r_value, mape = linear_reg(df_regioni_today["totale_casi"]/df_regioni_today["Popolazione_Sesso_totale"], y)

            fig.add_trace(go.Scatter(
                                x=100*line_x,
                                y=line_y,
                                mode='lines',
                                hovertemplate = f"<b>R^2</b> : {str(round((r_value**2)*100, 2))}% <br><b>MAPE</b> : {str(round(mape, 2))}%  <extra></extra>",
                                legendgroup=segment,
                                showlegend=False,
                                marker=go.scatter.Marker(color=pretty_colors[idx]),
                                name='Trend '+segment)
            )

            fig.add_trace(go.Scatter(
                                x=100*(df_regioni_today["totale_casi"]/df_regioni_today["Popolazione_Sesso_totale"]), 
                                y=y,
                                mode='markers',
                                hovertemplate = "<b>%{text}</b><br>Contagiati pro capite : %{x:.2f}%<br>"+selected_data_type+" | "+selected_column+"-> "+segment+": %{y:.2f}%<extra></extra>",
                                text=df_regioni_today["denominazione_regione"],
                                legendgroup=segment,
                                marker=go.scatter.Marker(color=pretty_colors[idx]),
                                name=segment)
            )
            
        fig.update_layout(
            title = "Analisi Correlazione Imprese/COVID",
            )
        fig.update_xaxes(title_text='% di popolazione contagiata')
        fig.update_yaxes(title_text=f"{selected_data_type} {pro_capite_text}")
        st.plotly_chart(fig,use_container_width=True)
    
    ####### Correlation Analysis #########
    #smokers_series = ISTAT_return_filtered_series(df_istat_smokers,selected_column="Tipo dato")
        
    #df_regioni_today = df_regioni.set_index("NUTS3")
    #df_regioni_today = df_regioni_today[df_regioni_today["data"] == df_regioni_today["data"].max()]
    #df_regioni_today = df_regioni_today.join(smokers_series)

    #scelta_dati_imprese = [x for x in df_istat_imprese.metadata["multiindex"] if x != df_istat_imprese.metadata["data_type_column"]]
    #for data_type in df_istat_imprese[df_istat_imprese.metadata["data_type_column"]].unique():
    #    for division in scelta_dati_imprese:
    #        imprese_series = ISTAT_return_filtered_series(df_istat_imprese,selected_column=division,selected_data_type=data_type)
    #        df_regioni_today = df_regioni_today.join(imprese_series)

    #st.write(df_regioni_today.corr()["growth_rate"])
    

elif area_filter == "Regione":

    st.markdown("---")

    analytics.page(USER_UNIQUE_ID,"Main_category",'Regione',{
    'path': '/',
    'name': "Regione",
    'title': "Neurality - Streamlit",
    "url": "http://neurality.it/covid/Regione"
    })

    #region_name = st.sidebar.selectbox("Seleziona la regione di interesse",sorted(regions))
    region_name = st.sidebar.multiselect("Seleziona una o più regioni di interesse",sorted(regions),default=["Emilia-Romagna","Lombardia"])

    cmap_radio = st.sidebar.radio("Scelta Color Map ed andamento asse y", ("Lineare", "Esponenziale"),index=1)

    st.sidebar.markdown("<p class='smallText marginTop'>Per un approfondimento sull'utilizzo di scale esponenziali per visualizzare l'andamento del virus clicca <a target='_blank' href=https://www.neodemos.info/articoli/la-curva-dei-contagiati-da-covid-19-la-ricerca-del-punto-di-svolta/>qui</a></p>",unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Incrocia i Dati ISTAT con i dati del Ministero della Salute**")
    air_switch = st.sidebar.checkbox("Inquinamento Aria",False)

    regional_data = df_regioni[df_regioni["denominazione_regione"].isin(region_name)].reset_index()
    
    if region_name:
        for region in region_name:
            analytics.track(USER_UNIQUE_ID, region, {
                'category':"Region Selected"
            })
        if len(region_name) > 1:
            analytics.track(USER_UNIQUE_ID, str(sorted(region_name)), {
                    'category':'Regions combined'
                })

    filtered_province_data = df[df["denominazione_regione"].isin(region_name)]

    if not filtered_province_data.empty:

        st.markdown("### Mappa totale casi COVID19 confermati")

        lat_sum = 0
        lon_sum = 0
        lats = regional_data.lat.unique()
        lons = regional_data.long.unique()

        for idx in range(len(lats)):
            lat_sum+=lats[idx]
            lon_sum+=lons[idx]

        lat_sum/=len(lats)
        lon_sum/=len(lons)

        lat_max = regional_data.lat.max()
        lat_min = regional_data.lat.min()
        lon_max = regional_data.long.max()
        lon_min = regional_data.long.min()

        if (lat_max-lat_min)>6 or (lon_max-lon_min)>7:
            
            #@TODO FIX ZOOM
            
            zoom = 6

        else:
            zoom = 6

        if cmap_radio == "Lineare":
            cmap = viridis
        else:
            giorni_da_min_positivi = calcolo_giorni_da_min_positivi(regional_data)
            viridis_exp_scale = exp_viridis(giorni_da_min_positivi)
            cmap = viridis_exp_scale
            analytics.track(USER_UNIQUE_ID, "Exponential Map Scale", {
                'category':'Values_Scale',
            })

        fig = px.choropleth_mapbox(
                            data_frame=filtered_province_data, 
                            geojson=province_map_json, 
                            locations='sigla_provincia', 
                            featureidkey='properties.prov_acr',
                            color='totale_casi',
                            color_continuous_scale=cmap,
                            range_color=(0, math.ceil(filtered_province_data['totale_casi'].max()+1)),
                            hover_data=["increased_cases"],
                            mapbox_style="carto-positron",
                            zoom=zoom, center = {"lat": lat_sum, "lon": lon_sum},
                            #opacity=1,
                            animation_frame="giorno",
                            labels={"giorno":"Giorno",
                                    "totale_casi":"Totale Casi",
                                    'data': 'Data', "growth_rate": "Growth Rate", 
                                    "increased_cases": "Nuovi Casi",
                                    "increased_tamponi":"Nuovi Tamponi Effettuati",
                                    "sigla_provincia":"Sigla Provincia"},
                            height=600,
                          )
        st.plotly_chart(fig,use_container_width=True)

        filtered_data = regional_data

        st.markdown("---")

        st.markdown("""
        Il grafico sottostante mostra il tasso di crescita dei casi positivi [(growth rate)](https://www.complexityeducation.com/2020/03/10/crescita-esponenziale-ed-epidemie/). \nValori inferiori ad 1 indicano che i contagi [non avvengono più su una curva esponenziale ma su una logaritmica](https://www.neodemos.info/articoli/la-curva-dei-contagiati-da-covid-19-la-ricerca-del-punto-di-svolta/), stanno quindi aumentando più lentamente ogni giorno.\n
        """)
        
        fig = px.line(data_frame=filtered_data[filtered_data["data"] > datetime(2020,3,4)],x="data",
                    y="smooth_growth_rate",
                    hover_data=["increased_cases","denominazione_regione"],
                    log_y=False,
                    color='denominazione_regione',
                    title="Growth rate media ultimi 3gg", 
                    labels={'increased_cases':'Nuovi Casi', 'data': 'Data', 'denominazione_regione': 'Regione',"smooth_growth_rate":"Growth Rate"})
        fig.update_traces(mode='lines+markers',hovertemplate = "<b>Growth Rate: %{y}</b><extra></extra>")
        st.plotly_chart(fig,use_container_width=True)

        st.markdown("---")

        if len(filtered_data['denominazione_regione'].unique() ) == 1:
            fig = fig_tamponi_vs_positivi(filtered_data)
            st.plotly_chart(fig,use_container_width=True)
        
        else:
            
            fig = fig_totale_casi_regione(filtered_data,cmap_radio=="Esponenziale")

            st.plotly_chart(fig,use_container_width=True)
            st.markdown("---")

            fig = fig_totale_casi_su_tamponi(filtered_data)
            st.plotly_chart(fig,use_container_width=True)

        if air_switch:

            st.markdown("---")
            st.markdown("### Analisi Indicatori Qualità dell'Aria")

            #air_reg_series = air_series.drop(columns=["CODICE PROVINCIA", "COMUNI"]).pivot_table(index='NUTS3_regione')

            analytics.track(USER_UNIQUE_ID, "Aria", {
                    'category':'ISTAT Selected',
                })
            
            filtered_province_today = filtered_province_data.set_index("NUTS3")
            
            filtered_province_today = filtered_province_today[filtered_province_today["data"] == filtered_province_today["data"].max()]

            filtered_air_data = air_series[air_series["denominazione_regione"].isin(region_name)]

            filtered_province_today = filtered_province_today.join(filtered_air_data, rsuffix='_other').drop(columns=['denominazione_regione_other', "COMUNI", "NUTS3_regione"])

            scelta_dati_aria = ["PM10", "PM2.5"]
            
            selected_cat = st.radio(
                            label="Scegli quali dati sul inquinamento dell'aria da visualizzare per regione ",
                            options=scelta_dati_aria)        

            all_columns = [x for x in filtered_province_today.columns if selected_cat in x ]
            if selected_cat == 'PM10':
                
                fig = go.Figure()
                fig2 = go.Figure()
                for idx, region in enumerate(filtered_province_today.denominazione_regione.unique()):
                    filtered_province_today_reg = filtered_province_today[filtered_province_today['denominazione_regione'] == region]

                    prov_data = (filtered_province_today_reg["totale_casi"]/filtered_province_today_reg["Popolazione_ETA1_Total"]).rename('totale_casi_procapite')
                
                    prov_data = pd.concat([filtered_province_today_reg.denominazione_provincia, prov_data, filtered_province_today_reg[all_columns[0]], filtered_province_today_reg[all_columns[1]]], axis=1)

                    prov_data_zero = prov_data.drop(prov_data[all_columns[0]][prov_data[all_columns[0]] == 0].index)
                    if prov_data_zero.empty:
                        st.write("Nessun dato PM10 giornaliero disponibile per la regione "+region)
                    else:

                        line, markers = traces_punti_e_trend(prov_data_zero.totale_casi_procapite, prov_data_zero[all_columns[0]], idx, "<b>%{text}</b><br>Casi Positivi procapite confermati: %{x:.3f}%<br>Giorni sopra il limite consigliato: %{y}<extra></extra>", prov_data_zero.denominazione_provincia, name=region)
                        fig.add_trace(line)
                        fig.add_trace(markers)

                    prov_data_one = prov_data.drop(prov_data[all_columns[1]][prov_data[all_columns[1]] == 0].index)
                    if prov_data_one.empty:
                        st.write("Nessun dato PM10 annuale disponibile per la regione "+region)
                    else:
                        line, markers = traces_punti_e_trend(prov_data_one.totale_casi_procapite, prov_data_one[all_columns[1]], idx, "<b>%{text}</b><br>Casi Positivi procapite confermati: %{x:.3f}%<br>Media Annuale PM10: %{y}<extra></extra>", prov_data_one.denominazione_provincia, name=region)
                        fig2.add_trace(line)
                        fig2.add_trace(markers)
                
                fig.add_trace(go.Scatter(
                            x=np.arange(start=0, stop=0.018, step=0.001),
                            y=[35,]*16,
                            mode='lines',
                            showlegend =False,
                            hovertemplate='Limite di giorni sopra limite consigliati<extra></extra>')
                )
                fig.update_layout(
                    title = "Inquinamento Aria (giorni con PM10 superiore al limite consigliato) / COVID",
                    )
                fig.update_xaxes(title_text='Contagi Procapite')
                fig.update_yaxes(title_text='Giorni al di sopra del limite consigliato - 50 μg/m^3')
                st.plotly_chart(fig,use_container_width=True)

                fig2.add_trace(go.Scatter(
                            x=np.arange(start=0, stop=0.018, step=0.001),
                            y=[40,]*16,
                            mode='lines',
                            showlegend =False,
                            hovertemplate='Limite di emissioni annuali consigliato<extra></extra>')
                )
                fig2.update_layout(
                    title = "Analisi Correlazione Inquinamento Aria (valore annuale medio) PM10 / COVID",
                    )
                fig2.update_xaxes(title_text='Contagi Procapite')
                fig2.update_yaxes(title_text='Valore medio annuale [μg/m^3]')
                st.plotly_chart(fig2,use_container_width=True)

            else:
                fig = go.Figure()
                fig2 = go.Figure()
                for idx, region in enumerate(filtered_province_today.denominazione_regione.unique()):
                    filtered_province_today_reg = filtered_province_today[filtered_province_today['denominazione_regione'] == region]

                    prov_data = (filtered_province_today_reg["totale_casi"]/filtered_province_today_reg["Popolazione_ETA1_Total"]).rename('totale_casi_procapite')

                    prov_data = pd.concat([filtered_province_today_reg.denominazione_provincia, prov_data, filtered_province_today_reg[all_columns[0]]], axis=1)

                    prov_data = prov_data.drop(prov_data[all_columns[0]][prov_data[all_columns[0]] == 0].index)
                    if prov_data.empty:
                        st.write("Nessun dato PM2.5 annuale disponibile per la regione "+region)
                    else:
                        line, markers = traces_punti_e_trend(prov_data.totale_casi_procapite, prov_data[all_columns[0]], idx, "<b>%{text}</b><br>Casi Positivi procapite confermati: %{x:.3f}%<br>Media Annuale PM2.5: %{y}<extra></extra>", prov_data.denominazione_provincia, name=region)
                        fig.add_trace(line)
                        fig.add_trace(markers)

                
                fig.add_trace(go.Scatter(
                            x=np.arange(start=0, stop=0.018, step=0.001),
                            y=[25,]*16,
                            mode='lines',
                            showlegend =False,
                            hovertemplate='Limite di emissioni annuali consigliato<extra></extra>')
                )
                fig.update_layout(
                    title = "Analisi Correlazione Inquinamento Aria (valore annuale medio) PM2.5 / COVID",
                    )
                fig.update_xaxes(title_text='Contagi Procapite')
                fig.update_yaxes(title_text='Valore medio annuale')
                st.plotly_chart(fig,use_container_width=True)

    else:
        st.markdown("--- \n ### Seleziona una o più Regioni")

    

elif area_filter == "Provincia":
    st.markdown("---")

    analytics.page(USER_UNIQUE_ID,"Main_category",'Provincia',{
    'path': '/',
    'name': "Provincia",
    'title': "Neurality - Streamlit",
    "url": "http://neurality.it/covid/Provincia"
    })
    province_name = st.sidebar.multiselect("Seleziona una o più province di interesse",sorted(provinces),default=["Milano","Bergamo","Lodi"])
    
    if province_name:
        for province in province_name:
            analytics.track(USER_UNIQUE_ID, province, {
                'category':'Province Selected',
            })
        if len(province_name) > 1:
            analytics.track(USER_UNIQUE_ID, str(sorted(province_name)), {
                    'category': 'Provinces combined'
                })
        

    _filter = df["denominazione_provincia"].isin(province_name)

    filtered_data = df[_filter]
    if not filtered_data.empty:
        log_y = st.sidebar.radio("Scegli andamento asse y", (False, True), format_func=lambda x:"Esponenziale" if x else "Lineare",index=1)
        st.sidebar.markdown("<p class='smallText marginTop'>Per un approfondimento sull'utilizzo di scale esponenziali per visualizzare l'andamento del virus clicca <a target='_blank' href=https://www.neodemos.info/articoli/la-curva-dei-contagiati-da-covid-19-la-ricerca-del-punto-di-svolta/>qui</a></p>",unsafe_allow_html=True)
        
        fig = fig_totale_casi_provincia(filtered_data,log_y)
        st.plotly_chart(fig,use_container_width=True)
        fig = fig_nuovi_casi_giornalieri(filtered_data)
        st.plotly_chart(fig,use_container_width=True)
    else:
        st.markdown("--- \n ### Seleziona una provincia")

st.markdown("---")
st.markdown("""
    <div class='footer'>
    <p>I dati visualizzati in questa pagina sono forniti dal Ministero della Salute ed elaborati dal <a target='_blank' href='https://github.com/pcm-dpc/COVID-19'>Dipartimento della Protezione Civile</a> e dall' <a target='_blank' href='http://dati.istat.it'>Istituto Nazionale di Statistica</a>.</p>
    <p>I dati forniti dal Ministero della Salute sono soggetti a licenza <a target='_blank' href='https://github.com/pcm-dpc/COVID-19/blob/master/LICENSE'>CC-BY-4.0</a> - <a target='_blank' href='https://creativecommons.org/licenses/by/4.0/deed.en'>Visualizza licenza</a></p>
    <p>I dati Istat sono soggetti a licenza <a target='_blank' href='https://www.istat.it/it/note-legali'>CC-BY-3.0</a> - <a target='_blank' href='https://creativecommons.org/licenses/by/3.0/it/'>Visualizza licenza</a></p>
    <p>Puoi trovare il nostro source code su <a target='_blank' href='http://github.com/neurality/covid19'>Github</a></p>
    </div>
""",unsafe_allow_html=True)

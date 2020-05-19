import difflib
import json
import math
import os
from datetime import date, datetime, timedelta
from typing import Dict, List
from zipfile import ZipFile

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

viridis = ((0.0, '#440154'), (0.1111111111, '#482878'), (0.2222222222, '#3e4989'), (0.3333333333, '#31688e'), (0.4444444444, '#26828e'), (0.5555555555, '#1f9e89'), (0.6666666666, '#35b779'), (0.7777777777, '#6ece58'), (0.8888888888, '#b5de2b'), (1.0, '#fde725'))

pretty_colors = ["#ff0000","#00ff00","#0000ff","#ffff00","#00ffff","#ffffff",
                 "#000000","#ffff00","#ff0000","#009900","#0099ff","#00cc00",
                 "#0000ff","#996600","#006600","#cc0033","#cc6600","#6600ff",
                 "#00ccff","#00ff33","#00ffff","#3300ff","#336600","#663399",
                 "#EF233C","#18FF6D","#916953","#FFF07C","#80FF72","#7EE8FA",
                 "#285238","#977AB5","#A0E4DD","#8C8344","#468C3F","#457F89"]

def format_df(df):
    df = df.fillna(0).replace(np.inf, 0).replace(-np.inf, 0)
    df = df[(df.T != 0).any()]
    return df
    

def calculate_line(x,slope,intercept):
    y= x*slope + intercept
    return y

def mean_absolute_percentage_error(y_true, y_pred): 
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    return mape

def linear_reg(xi:np.array,y:list):
    slope, intercept, r_value, p_value, std_err = stats.linregress(xi,y)
    line = slope*xi+intercept
    mape = mean_absolute_percentage_error(y, line)
    line_x = np.arange(xi.min(),xi.max(),(xi.max() - xi.min())/30) if len(xi)>2 else []
    line_y = calculate_line(line_x,slope,intercept) if line_x != [] else []
    return line_x, line_y, r_value, mape

def exponential_growth(x:float, d:float, r:float=0.16):
    '''
        Input parameters: 
            r: Growth factor - 1
            d: Giorni passati dal rilevamento di X casi positivi (per esempio 100)
            x: valore lineare da convertire
    '''

    eg = (np.power(1+r, d*x)-1)/(np.power(1+r, d)-1)
    return eg


def exp_viridis(d:float, r:float=0.16):
    exp_viridis = ()
    for itup in viridis:
        exp_viridis += ((exponential_growth(itup[0], d, r), itup[1]),)
    return exp_viridis

def convert_datetime(string_from,format_to:str="%m/%d"):
    if type(string_from) == "str":
        date = datetime.strptime(string_from, "%Y-%m-%dT%H:%M:%S")
        return date
    else:
        dates = [datetime.strptime(x, "%Y-%m-%dT%H:%M:%S") for x in string_from]
        return np.array(dates)

def calcolo_giorni_da_min_positivi(df_regioni, min_positivi=100):
    regione_piu_colpita = df_regioni[df_regioni["data"] == df_regioni["data"].max()][df_regioni["totale_casi"] == df_regioni["totale_casi"].max()]["denominazione_regione"].tolist()[0]
    temp = df_regioni[df_regioni["totale_casi"] > min_positivi]
    temp = temp[temp["denominazione_regione"] == regione_piu_colpita]
    return len(temp['data'].tolist())



def get_map_json():
    #st.write("Cache miss: Getting the geoJSON")
    province_map_path = os.path.join("map","GeoJSON","limits_IT_provinces_simple.json")
    regions_map_path = os.path.join("map","GeoJSON","limits_IT_regions_simplified.json")
    with open(province_map_path) as map_file:
        province_map_json = json.load(map_file)
    
    with open(regions_map_path) as map_file:
        regions_map_json = json.load(map_file)
    return province_map_json,regions_map_json

def group_trentino(df):
    trentino = df[df["codice_regione"] >=21]
    trentino = trentino.groupby("data").apply(aggregate_trentino)
    trentino["codice_regione"] = 4
    trentino["denominazione_regione"] = "Trentino Alto Adige"
    trentino = trentino.reset_index(drop=True)
    df = df.append(trentino).sort_values(["data","denominazione_regione"])
    df = df.reset_index(drop=True)
    df = df.infer_objects()
    return df
    
def aggregate_trentino(x):
    #st.write("prima",type(x))
    x = x.agg(
        {"data":"max",
        "stato":"max",
        "codice_regione":"max",
        "denominazione_regione":"max",
        "lat":"mean",
        "long":"mean",
        "ricoverati_con_sintomi":"sum",
        "terapia_intensiva":"sum",
        "totale_ospedalizzati":"sum",
        "isolamento_domiciliare":"sum",
        "totale_positivi":"sum",
        "variazione_totale_positivi":"sum",
        "nuovi_positivi":"sum",
        "dimessi_guariti":"sum",
        "deceduti":"sum",
        "totale_casi":"sum",
        "tamponi":"sum",
        "casi_testati":"sum",

        }
    )
    x = x.to_frame().transpose()
    x["denominazione_regione"] = "Trentino Alto Adige"
    
    return x

def check_ds_istat():
    if (not os.path.exists(os.path.join("ISTAT_DATA","DCCV_AVQ_FAMIGLIE_01042020194245399.csv")) or
        not os.path.exists(os.path.join("ISTAT_DATA","DCCV_AVQ_PERSONE_01042020202759289.csv")) or
        not os.path.exists(os.path.join("ISTAT_DATA","DCIS_POPRES1_29032020143754329.csv")) or
        not os.path.exists(os.path.join("ISTAT_DATA","DICA_ASIAUE1P_02042020145705482.csv"))):
        with ZipFile(os.path.join("ISTAT_DATA","istat.zip"), 'r') as zipObj:
            # Extract all the contents of zip file in current directory
            zipObj.extractall("ISTAT_DATA")

def get_population_df():
    return import_ISTAT_dataset("DCIS_POPRES1_29032020143754329",sep=",")

def get_dataset(current_date: datetime.date):
    df = pd.read_csv("https://raw.githubusercontent.com/pcm-dpc/COVID-19/master/dati-province/dpc-covid19-ita-province.csv", keep_default_na=False, na_values=[''])
    df_regioni = pd.read_csv("https://raw.githubusercontent.com/pcm-dpc/COVID-19/master/dati-regioni/dpc-covid19-ita-regioni.csv")
    df_nazione = pd.read_csv("https://raw.githubusercontent.com/pcm-dpc/COVID-19/master/dati-andamento-nazionale/dpc-covid19-ita-andamento-nazionale.csv")

    check_ds_istat()

    df_regioni = group_trentino(df_regioni)

    conversioni_province, conversioni_regioni = read_conversion_tables()
    
    conversioni_regioni = conversioni_regioni.set_index("denominazione_regione")
    conversioni_province = conversioni_province.set_index("codice_provincia")
    df_regioni = df_regioni.join(conversioni_regioni, on="denominazione_regione")
    df_nazione['NUTS3'] = 'IT'
    
    df = df.join(conversioni_province.drop(columns="denominazione_provincia"), on="codice_provincia")

    df.dropna(subset = ["data"], inplace=True)
    df = df.round({"growth_rate":2}) 
    #streamlit vuole "lon" per la longitudine invece di "long"
    df.columns = ["lon" if x=="long" else x for x in df.columns]
    df = df.apply(lambda x: convert_datetime(x) if x.name == 'data' else x)
    df_regioni = df_regioni.apply(lambda x: convert_datetime(x) if x.name == 'data' else x)
    df_nazione = df_nazione.apply(lambda x: convert_datetime(x) if x.name == 'data' else x)

    #aggiungere una data formattata come colonna per le mappe
    df_nazione["giorno"] = df_nazione["data"].apply(lambda x: x.strftime("%d/%m"))
    df_regioni["giorno"] = df_regioni["data"].apply(lambda x: x.strftime("%d/%m"))
    df["giorno"] = df["data"].apply(lambda x: x.strftime("%d/%m"))

    pop_path = os.path.join("ISTAT_DATA", "Popolazione.csv")
    if os.path.exists(pop_path):
        pop = pd.read_csv(pop_path).pivot_table(index="ITTER107")
    else:
        df_istat = get_population_df()
        pop = ISTAT_return_filtered_series(df_istat,"ETA1","10_anni")
        pop = pd.concat([pop, ISTAT_return_filtered_series(df_istat,"Stato civile")], axis=1)
        pop = pd.concat([pop, ISTAT_return_filtered_series(df_istat,"Sesso")], axis=1)
        pop.to_csv(os.path.join("ISTAT_DATA", df_istat.metadata['main_data_type']+".csv"))

    df_regioni = df_regioni.join(pop, on="NUTS3")
    df = df.join(pop, on="NUTS3")

    smokers_path = os.path.join("ISTAT_DATA", "Fumatori.csv")
    if os.path.exists(smokers_path):
        smokers = pd.read_csv(smokers_path).pivot_table(index="ITTER107")
    else:
        df_istat_smokers = import_ISTAT_dataset("DCCV_AVQ_PERSONE_01042020202759289",sep=",")
        smokers = ISTAT_return_filtered_series(df_istat_smokers,selected_column="Tipo dato")
        smokers.to_csv(os.path.join("ISTAT_DATA", df_istat_smokers.metadata['main_data_type']+".csv"))

    air_path = os.path.join("ISTAT_DATA", "air_pollution_2018.csv")
    df_istat_air = pd.read_csv(air_path, encoding='utf-8').set_index('NUTS3')
    
    imprese_path = os.path.join("ISTAT_DATA", "Imprese.csv")
    if os.path.exists(imprese_path):
        imprese = pd.read_csv(imprese_path).pivot_table(index="D1")
    else:
        df_istat_imprese = import_ISTAT_dataset("DICA_ASIAUE1P_02042020145705482",sep=",")
        scelta_dati_imprese = [x for x in df_istat_imprese.metadata["multiindex"] if x != df_istat_imprese.metadata["data_type_column"]]
        data_types = df_istat_imprese[df_istat_imprese.metadata["data_type_column"]].unique()

        imprese = 0
        imprese_metadata = {}
        for selected_column in scelta_dati_imprese:
            for selected_data_type in data_types: 
                if type(imprese) == int:
                    imprese = ISTAT_return_filtered_series(df_istat_imprese,selected_column=selected_column,selected_data_type=selected_data_type)
                else:
                    imprese = pd.concat([imprese,ISTAT_return_filtered_series(df_istat_imprese,selected_column=selected_column,selected_data_type=selected_data_type)], axis=1)
        imprese_metadata[str(imprese.columns[0].split("_")[1])] = [str(imprese.columns[0].split("_")[2]),]
        for col in imprese.columns:
            col = col.split("_")
            multiindex = col[1]
            multinindex_data = col[2]
            if multiindex in imprese_metadata:
                if not str(multinindex_data) in imprese_metadata[str(multiindex)]:
                    imprese_metadata[str(multiindex)].append(str(multinindex_data))
            else:
                imprese_metadata[str(multiindex)] = [str(multinindex_data,)]
        imprese.to_csv(os.path.join("ISTAT_DATA", df_istat_imprese.metadata['main_data_type']+".csv"))
        json_dict = json.dumps(imprese_metadata)
        with open(os.path.join("ISTAT_DATA", df_istat_imprese.metadata['main_data_type']+"_metadata.json"),mode="w", encoding="utf-8") as f:
            f.write(json_dict)

    df = df.groupby('sigla_provincia').apply(add_statistics)
    df = format_df(df)
    df_regioni = df_regioni.groupby('denominazione_regione').apply(add_statistics)
    df_regioni = format_df(df_regioni)

    return df, df_regioni, smokers, imprese, df_istat_air


def read_conversion_tables():
    conversioni_province = pd.read_csv("codici_province.CSV",encoding = "ISO-8859-1",sep=";")
    conversioni_regioni = pd.read_csv("codici_regioni.CSV",encoding = "ISO-8859-1",sep=";")
    
    return conversioni_province, conversioni_regioni

def get_areas(df):
    regions = df["denominazione_regione"].unique()
    provinces = df["denominazione_provincia"].unique()
    return regions,provinces

def add_statistics(df):
    df['increased_cases'] = df.totale_casi - df.totale_casi.shift(1)
    df['growth_rate'] = df.increased_cases / df.increased_cases.shift(1)
    df['smooth_growth_rate'] = df['growth_rate'].rolling(min_periods=1,window=3).mean() #Growth rate mediata sugli ultimi 3 giorni
    if "tamponi" in df:
        df['totale_casi/tamponi'] = df.totale_casi / df.tamponi
        df['increased_tamponi'] = df.tamponi - df.tamponi.shift(1)
    if "deceduti" in df:
        df['suscettibili'] = df["Popolazione_ETA1_Total"]-df["totale_positivi"]-df["deceduti"]-df["dimessi_guariti"]
    return df


def import_ISTAT_dataset(filename_without_extension:str,sep=","):
    df = pd.read_csv(os.path.join("ISTAT_DATA",f"{filename_without_extension}.csv"),sep=sep)
    path = os.path.join("ISTAT_DATA",f"{filename_without_extension}_metadata.json")
    df.metadata = property()
    with open(path) as json_file:
        json_dict = json.load(json_file)
    
    df.metadata = json_dict
    return df


def group_labels(x,prefix,ranges):
    
    for group in ranges.keys():
        
        if x in [f"{prefix}{x}" for x in ranges[group]]:
            return f"{prefix}{group}"
    raise Exception(f"Problem in aggregating column {x}")

def ISTAT_return_filtered_series(df,selected_column:str,aggregate=None,selected_data_type=None):
    metadata = df.metadata

    if "data_type_column" in metadata.keys():
        if selected_data_type not in df[metadata['data_type_column']].unique():
            raise Exception(f"please select data type between {df[metadata['data_type_column']].unique()}")
        else:
            #Filtering data Frame based on data type
            df = df[df[metadata['data_type_column']] == selected_data_type]
            
    
    df = df.pivot_table(index=metadata["index_name"],columns=metadata["multiindex"], values=[metadata["main_data_column_name"]])

    multiindex_level_names = df.columns.names
    selected_column_level = multiindex_level_names.index(selected_column)
    indexer = [metadata["columns_info"][column]["total"] if column in metadata["columns_info"] else slice(None) for column in df.columns.names]

    indexer[selected_column_level] = slice(None)

    a = df.loc[(slice(None),tuple(indexer))]

    if "data_type_column" in metadata.keys():
        prefix = selected_data_type
    else:
        prefix = metadata['main_data_type']
    
    a.columns = [f"{prefix}_{selected_column}_{x}" for x in a.columns.get_level_values(selected_column_level)]
    
    if aggregate:
        aggregate_method = metadata["columns_info"][selected_column]["aggregate"]["method"]
        if aggregate not in metadata["columns_info"][selected_column]["aggregate"]["ranges"]:
            raise Exception(f"Aggregate range {aggregate} not in metadata")
        
        a = a.groupby(axis=1,by=lambda x: group_labels(x,f"{metadata['main_data_type']}_{selected_column}_",metadata["columns_info"][selected_column]["aggregate"]["ranges"][aggregate]))
    
        if aggregate_method == "sum":
            a = a.sum()
        elif aggregate_method == "mean":
            a = a.mean()
        else:
            raise Exception(f"Unknown method of aggregation {aggregate_method}")
    
    #st.write(a)
    return a

def filter_dates(dates,n):
    return np.append(dates[:-math.ceil(len(dates)/n-1):math.ceil(len(dates)/n)],dates[-1])

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 14:12:45 2024

@author: statistics
"""

import os
import pandas as pd
import parselmouth
from collections import defaultdict
from praatio import tgio

# Nombres en español para las columnas de intensidad en los CSV generados
INTENSIDAD_LABELS = {
    'mean':    'Promedio (intensidad)',
    'maximum': 'Máximo (intensidad)',
    'minimum': 'Mínimo (intensidad)',
}

# Nombres en español de la métrica de extracción (pitch/formantes)
PITCH_LABELS = {
    'mean':    'Promedio',
    'median':  'Punto medio',
    'maximum': 'Máximo',
    'minimun': 'Mínimo',
}

# Vocales válidas: evita capturar diptongos (ai, ue...) ni la 's'
VOCALES_VALIDAS = {'a', 'e', 'i', 'o', 'u'}

'''
funcion que encuentra el nivel mas bajo de analisis del text grid dado su ubicacion
El parametro file_path tiene que tener el siguiente formato file_path="/content/audios/1MMFS"
'''
def last_tier(file_path):
    textgrid_path=file_path+ ".TextGrid"
    tg = tgio.openTextgrid(textgrid_path)
    tier_names = list(tg.tierDict.keys())
    if tier_names:
        last_tier = tier_names[-1]
        return last_tier
    else:
        return None



# REVISAR: La modificación de éste incide en el otro método de abajo.
'''
Función para el análisis por INTERVALO .
los parametros pitch y formant son objetos de ese tipo (tipo pratt) y start y stop son los limites del intervalo de interes
'''
def extract_interval_features_vocal(pitch, pitch_mode, formant, formant_mode, start, stop, incluir_pitch=True):

    # Puede elegir distintos formantes (F1-F4), el pitch (F0) y una sola media/mediana/min/max.

    if (pitch_mode == "mean"):
        pitch_values = parselmouth.praat.call(pitch, "Get mean", start, stop, "Hertz")
        formant_values = [parselmouth.praat.call(formant, "Get mean", i, start, stop, "Hertz") for i in formant_mode]
    elif (pitch_mode == "maximum"):
        pitch_values = parselmouth.praat.call(pitch, "Get maximum", start, stop, "Hertz", "Parabolic")
        formant_values = [parselmouth.praat.call(formant, "Get maximum", i, start, stop, "Hertz", "Parabolic") for i in formant_mode]
    elif (pitch_mode == "minimun"):
        pitch_values = parselmouth.praat.call(pitch, "Get minimum", start, stop, "Hertz", "Parabolic")
        formant_values = [parselmouth.praat.call(formant, "Get minimum", i, start, stop, "Hertz", "Parabolic") for i in formant_mode]
    elif (pitch_mode == "median"):
        pitch_values = parselmouth.praat.call(pitch, "Get quantile", start, stop, 0.5, "Hertz")
        formant_values = [parselmouth.praat.call(formant, "Get quantile", i, start, stop, "Hertz", 0.5) for i in formant_mode]
    else:
        print("Error: pitch no reconocido")
        return None
    
    base = [start, stop, stop-start]
    if incluir_pitch:
        base.append(pitch_values)   # F0
    return (base + formant_values)


def extract_interval_features_s(sound, intensity, intensity_modes, start, stop, center_b, sd_b, sk_b, kur_b, alt_b):

    valores_s = []

    #intensidad (multiselección: promedio, máximo y/o mínimo)
    for modo in intensity_modes:
        if (modo == "mean"):
            valores_s.append(parselmouth.praat.call(intensity, "Get mean", start, stop, 'energy'))
        elif (modo == "maximum"):
            valores_s.append(parselmouth.praat.call(intensity, "Get maximum", start, stop, "Parabolic"))
        elif (modo == "minimum"):
            valores_s.append(parselmouth.praat.call(intensity, "Get minimum", start, stop, "Parabolic"))

    #ESPECTRO
    if any([center_b, sd_b, sk_b, kur_b, alt_b]): #...evitamos que se calcule el espectro si no hay ninguna opcion
        s1=sound.extract_part(from_time=start, to_time=stop)#extraccion de audio del intervalo
        sp1=s1.to_spectrum() # Este valor sólo se utiliza para sacar center, sd, sk, kur
        center = None
        sk = None
        if center_b:
            center= parselmouth.praat.call(sp1, "Get centre of gravity",2)
            valores_s.append(center)
        if sd_b:
            sd= parselmouth.praat.call(sp1, "Get standard deviation",2)
            valores_s.append(sd)
        if sk_b:
            sk= parselmouth.praat.call(sp1, "Get skewness",2)
            valores_s.append(sk)
        if kur_b:
            kur= parselmouth.praat.call(sp1, "Get kurtosis",2)
            valores_s.append(kur)
        if alt_b:
            # Altura de la fricción = Centro de gravedad - (Asimetría / 2).
            # Se calcula aunque no se hayan pedido center/sk como columnas propias.
            center_alt = center if center is not None else parselmouth.praat.call(sp1, "Get centre of gravity", 2)
            sk_alt = sk if sk is not None else parselmouth.praat.call(sp1, "Get skewness", 2)
            valores_s.append(center_alt - (sk_alt / 2))

        # Regresa una lista que varía según los valores extraídos
    return ([start, stop, stop-start] + valores_s)




'''
Función para el análisis por observación (archivo) dadan su ubicacion .
'''
# Revisar si quiero generar dos archivos (uno vocálico y otro de S) o si quiero generar uno solo con ambas cosas
def process_file(file_path, genero, pitch_mode, formant_mode, intensity_modes, center_b, sd_b, sk_b, kur_b, alt_b):
    base_name = os.path.basename(file_path)
    name = os.path.splitext(base_name)[0]
    tg = tgio.openTextgrid(file_path + ".TextGrid")
    sound = parselmouth.Sound(file_path + ".wav")
    intensity = sound.to_intensity(minimum_pitch=75, time_step=None, subtract_mean=True)

    if (genero == 'F'):
        # Mujeres
        pitch = sound.to_pitch(pitch_floor=100, pitch_ceiling=500)
        formant = parselmouth.praat.call(sound, "To Formant (burg)", 0.005, 5, 5500, 0.025, 50)
    elif (genero == 'M'):
        # Hombres
        pitch = sound.to_pitch(pitch_floor=75, pitch_ceiling=300)
        formant = parselmouth.praat.call(sound, "To Formant (burg)", 0.005, 5, 5000, 0.025, 50)
    else:
        # Sin distinción de género
        pitch = sound.to_pitch(pitch_floor=75, pitch_ceiling=600)
        # Consulté https://www.fon.hum.uva.nl/praat/manual/Sound__To_Formant__burg____.html
        formant = parselmouth.praat.call(sound, "To Formant (burg)", 0.005, 5, 5000, 0.025, 50)

    metrica_es = PITCH_LABELS.get(pitch_mode, pitch_mode)
    formantes = [f'F{i} ({metrica_es})' for i in formant_mode] #...nombres en español que coinciden con los botones

    # Definir los nombres de columna para el DataFrame
    column_names = ['name','Label','Start', 'Stop','Duration', f'F0 ({metrica_es})'] + formantes + [INTENSIDAD_LABELS.get(m, m) for m in intensity_modes]
    if center_b:
        column_names.append('Centro de gravedad')
    if sd_b:
        column_names.append('Desviación estándar')
    if sk_b:
        column_names.append('Asimetría')
    if kur_b:
        column_names.append('Curtosis')
    if alt_b:
        column_names.append('Altura de la fricción')

    word_tier = tg.tierDict[last_tier(file_path)]

    #Análisis por intervalo
    interval_features = []
    for start, stop, label in word_tier.entryList:
        interval_features.append([name, label]+ extract_interval_features_vocal(pitch, pitch_mode, formant, formant_mode, start, stop) +  extract_interval_features_s(sound, intensity, intensity_modes, start, stop, center_b, sd_b, sk_b, kur_b, alt_b))

    return pd.DataFrame(interval_features, columns=column_names)


''' Procesamiento sólo de las vocales para la generación de un data frame'''
def process_file_vocal(file_path, vocales , genero, pitch_mode, formant_mode, incluir_pitch=True):
    base_name = os.path.basename(file_path)
    name = os.path.splitext(base_name)[0]
    tg = tgio.openTextgrid(file_path + ".TextGrid")
    sound = parselmouth.Sound(file_path + ".wav")

    if (genero == 'F'):
        # Mujeres
        pitch = sound.to_pitch(pitch_floor=100, pitch_ceiling=500)
        formant = parselmouth.praat.call(sound, "To Formant (burg)", 0.005, 5, 5500, 0.025, 50)
    elif (genero == 'M'):
        # Hombres
        pitch = sound.to_pitch(pitch_floor=75, pitch_ceiling=300)
        formant = parselmouth.praat.call(sound, "To Formant (burg)", 0.005, 5, 5000, 0.025, 50)
    else:
        # Sin distinción de género
        pitch = sound.to_pitch(pitch_floor=75, pitch_ceiling=600)
        # Consulté https://www.fon.hum.uva.nl/praat/manual/Sound__To_Formant__burg____.html
        formant = parselmouth.praat.call(sound, "To Formant (burg)", 0.005, 5, 5000, 0.025, 50)

    metrica_es = PITCH_LABELS.get(pitch_mode, pitch_mode)
    formantes = [f'F{i} ({metrica_es})' for i in formant_mode] #...nombres en español que coinciden con los botones

    # Definir los nombres de columna para el DataFrame (F0 solo si se seleccionó)
    column_names = ['name','Label','Start', 'Stop','Duration']
    if incluir_pitch:
        column_names.append(f'F0 ({metrica_es})')
    column_names += formantes

    # Solo vocales puras seleccionadas (a, e, i, o, u): excluye diptongos y la 's'
    vocales_puras = [v for v in vocales if v in VOCALES_VALIDAS]

    word_tier = tg.tierDict[last_tier(file_path)]

    #Análisis por intervalo
    interval_features = []
    for start, stop, label in word_tier.entryList:
        if label.strip() in vocales_puras:  #...coincidencia exacta: sin diptongos ni 's'
                interval_features.append([name, label]+ extract_interval_features_vocal(pitch, pitch_mode, formant, formant_mode, start, stop, incluir_pitch))

    return pd.DataFrame(interval_features, columns=column_names)

'''Procesamiento sólo de las s para generar un data frame'''
def process_file_s(file_path, intensity_modes, center_b, sd_b, sk_b, kur_b, alt_b):
    base_name = os.path.basename(file_path)
    name = os.path.splitext(base_name)[0]
    tg = tgio.openTextgrid(file_path + ".TextGrid")
    sound = parselmouth.Sound(file_path + ".wav")
    intensity = sound.to_intensity(minimum_pitch=75, time_step=None, subtract_mean=True)

    # Definir los nombres de columna para el DataFrame
    column_names = ['name','Label','Start', 'Stop','Duration'] + [INTENSIDAD_LABELS.get(m, m) for m in intensity_modes]
    if center_b:
        column_names.append('Centro de gravedad')
    if sd_b:
        column_names.append('Desviación estándar')
    if sk_b:
        column_names.append('Asimetría')
    if kur_b:
        column_names.append('Curtosis')
    if alt_b:
        column_names.append('Altura de la fricción')

    word_tier = tg.tierDict[last_tier(file_path)]

    #Análisis por intervalo
    interval_features = []
    for start, stop, label in word_tier.entryList:
        if ('s' == label):
            interval_features.append([name, label] +  extract_interval_features_s(sound, intensity, intensity_modes, start, stop, center_b, sd_b, sk_b, kur_b, alt_b))

    return pd.DataFrame(interval_features, columns=column_names)


'''
Función para el análisis por muestra (archivo) dada su ubicacion (directorio de la carpeta de audios) .
'''
# Revisar cómo definir el comportamiento cuando no queremos que haga las cosas de forma genérica
def process_sample(directory,genero='X',pitch_mode="mean", formant_mode = [0,1,2,3,4],intensity_modes=("mean",),center_b=False,sd_b = False, sk_b = False, kur_b = False, alt_b = False):
    EXTENSIONS = {'.wav', '.TextGrid'}
    # Diccionario para contar archivos por observacion
    #... Hice un cambio debidio a que el diccionario inicial contaba cuantas veces aparecia el path de un archivo, pero al final solo va a utilizar el path existente no el conteo.
    files = set()
    for f in os.listdir(directory):
        nombre, ext = os.path.splitext(os.path.join(directory, f))
        if ext in EXTENSIONS:
            files.add(nombre)
    files = list(files)  #lista que contiene el path base (sin extension) de todas las observaciones. ej: /content/audios/1MMFS
                        #este path tiene el formato de imput para la funcion "last_tier" y "process_file"

    general = []

    # Generar un archivo CSV por observación (archivo)
    for file_path in files:
        df = process_file(file_path,genero,pitch_mode, formant_mode, intensity_modes, center_b, sd_b, sk_b, kur_b, alt_b)
        general.append(df)
        df.to_csv(file_path + "_data.csv", index=False)

    # Generar un CSV general
    # Este DataFrame contendrá la información de todos
    df_general = pd.concat(general, ignore_index=True) #...Cambio evitamos hacer un loop

    df_general.to_csv(os.path.join(directory, "General.csv"), index=False)


#Función para el análisis por muestra (archivo) dada su ubicacion (directorio de la carpeta de audios) .

def process_sample_separado(directory,vocales = ['a','e','i','o','u'],genero='X',pitch_mode="mean", formant_mode = [1,2,3,4],incluir_pitch=True,intensity_modes=("mean",),center_b=False,sd_b = False, sk_b = False, kur_b = False, alt_b = False, gen_vocal=True, gen_s=True):

    EXTENSIONS = {'.wav', '.TextGrid'}
    # Diccionario para contar archivos por observacion
    #directory = os.path.join(directory,"..","temporal_file_storage")
    #... Mismo cambio que en process_sample
    files = set()

    for f in os.listdir(directory):
        nombre, ext = os.path.splitext(os.path.join(directory, f))
        if ext in EXTENSIONS:
            files.add(nombre)
    files = list(files)  #lista que contiene el path base (sin extension) de todas las observaciones. ej: /content/audios/1MMFS
                        #este path tiene el formato de imput para la funcion "last_tier" y "process_file"

    general_s = []
    general_vocal = []

    # Generar un archivo CSV por observación (archivo).
    # Solo se genera el bloque que corresponde a lo seleccionado (vocales y/o /s/).
    for file_path in files:
        if gen_vocal:
            df_vocal = process_file_vocal(file_path, vocales, genero, pitch_mode, formant_mode, incluir_pitch)
            general_vocal.append(df_vocal)
            df_vocal.to_csv(file_path + "_data_VOCAL.csv", index=False)

        if gen_s:
            df_s = process_file_s(file_path, intensity_modes, center_b, sd_b, sk_b, kur_b, alt_b)
            general_s.append(df_s)
            df_s.to_csv(file_path + "_data_S.csv", index=False)

    # Generar el CSV general vocal (solo si se pidieron vocales)
    if gen_vocal:
        df_general_vocal = pd.concat(general_vocal, ignore_index = True)
        df_general_vocal.to_csv(os.path.join(directory, "General_Vocal.csv"), index=False)

    # Generar el CSV general de /s/ (solo si se pidió la s)
    if gen_s:
        df_general_s = pd.concat(general_s, ignore_index = True)
        df_general_s.to_csv(os.path.join(directory, "General_S.csv"), index=False)

    # Generar un CSV general COMPLETO con ambas voces (dubitada e indubitada) y
    # ambos tipos de fonema (vocales y /s/) en una sola tabla. Las columnas que no
    # aplican a una fila quedan vacías: en las filas de /s/ los formantes F0-F4
    # salen en blanco (no se pueden calcular), y en las vocales las columnas
    # espectrales/intensidad también.
    partes = []
    if gen_vocal:
        partes.extend(general_vocal)
    if gen_s:
        partes.extend(general_s)
    if partes:
        df_completo = pd.concat(partes, ignore_index=True)
        # Ordenar columnas: metadata, vocales (F0-F4), espectrales y al final las
        # de intensidad.
        meta = ['name', 'Label', 'Start', 'Stop', 'Duration']
        espectral_orden = ['Centro de gravedad', 'Desviación estándar', 'Asimetría', 'Curtosis', 'Altura de la fricción']
        intensidad_orden = list(INTENSIDAD_LABELS.values())
        cols = list(df_completo.columns)
        vocal_cols = [c for c in cols if c not in meta and c not in espectral_orden and c not in intensidad_orden]
        orden = (meta
                 + vocal_cols
                 + [c for c in espectral_orden if c in cols]
                 + [c for c in intensidad_orden if c in cols])
        df_completo = df_completo[orden]
        # Ordenar filas por archivo y tiempo para que ambas voces queden legibles
        df_completo = df_completo.sort_values(['name', 'Start']).reset_index(drop=True)
        df_completo.to_csv(os.path.join(directory, "General_Completo.csv"), index=False)


'''
reset a archivos originales en la carpeta base (elimina los archivos producto de la extracccion)
'''
def reset_archivos(path):
    EXTENSIONS = {'.wav', '.TextGrid','.csv'}
    if not os.path.isdir(path):
        print("La ruta proporcionada no es un directorio válido.")
        return
        
    archivos = os.listdir(path)
    for archivo in archivos:
        archivo_path = os.path.join(path, archivo)
        if os.path.isfile(archivo_path) and os.path.splitext(archivo)[1] in EXTENSIONS:
            os.remove(archivo_path)

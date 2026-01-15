#utils/funciones_importar.py
import os
import json
import re
from datetime import datetime
from dash import html
import xml.etree.ElementTree as ET



from utils.funciones_comunes import valores_calc_directos



#funciones que sólo se usan en el módulo importar
# importadores de diferentes marcas
def import_RST(files, index_0, cota):
    # importador para archivos de RST de inclinómetros verticales, con sonda de 0.5 m
    # index_0 marca dónde comienza el inclinómetro, 1000 si no hay cambios en la boca
    # cota es la cota original de index_0=1000

    # Contante del instrumento para dar mm de desplazamiento por paso
    cte_instrument = 1000
    paso = 0.5

    data = {}

    for file in files:
        # Para cada archivo se genera una estructura de datos compatible con el json tipo
        filename = file['filename']
        lines = file['lines']
        index = index_0 - 1 # inicializo en índice en cada pasada

        # Inicializar la estructura de datos para la fecha y hora
        campaign_data = {}
        date_time = None

        # Variables para almacenar los datos
        index_values = []
        abs_depth_values = []
        depth_values = []
        a0_values = []
        a180_values = []
        b0_values = []
        b180_values = []

        # info asociada a la campaña. Por defecto
        campaign_info = {
            "index_0": index_0,
            "importador": "RST",
            "instrument_constant": cte_instrument, # valor en mm para RST
            #"reference": False,
            "active": True,
            "quarentine": False,
            "alarm": "por definir"
        }
        # Paso 1. Busca dónde comienzan las líneas de lecturas
        # Parsear las líneas del archivo (mantener la lógica existente)
        reading_lines_start = 0
        # busca la línea donde empiezan los datos - reading_lines_start
        for i, line in enumerate(lines):
            if line.strip() == "" and "Depth,Face" in lines[i + 1]:
                reading_lines_start = i + 2
                break
        # Paso 2. Recorre del inicio hasta las lecturas y rellena la información de la campaña
        for line in lines[:reading_lines_start]:
            if ',' in line:
                try:
                    key, value = line.strip().split(',', 1)
                except ValueError:
                    print(f"Error al dividir la línea en {filename}: {line.strip()}")
                    continue
                if key in ["Reading Date(m/d/y)", "Reading Date(m/d/y,h:m:s)"]:
                    try:
                        # Intentar varios formatos posibles de fecha
                        date_time = datetime.strptime(value.strip(), "%m/%d/%Y,%H:%M:%S").isoformat()
                    except ValueError:
                        try:
                            date_time = datetime.strptime(value.strip(), "%m/%d/%Y").isoformat()
                        except ValueError:
                            print(f"Error al parsear la fecha en {filename}: {value.strip()}")
                elif key == "Borehole":
                    campaign_data["nom_campo"] = value
                elif key == "Reading Date(m/d/y)":
                    campaign_date = value
                elif key == "Interval":
                    depth_interval = float(value)
                    campaign_data["interval"] = depth_interval
                elif key == "Probe Serial#":
                    campaign_data["probe_serial"] = value
                elif key == "Reel Serial#":
                    campaign_data["reel_serial"] = value
                elif key == "Reading Units":
                    campaign_data["reading_units"] = value
                elif key == "Depth Units":
                    campaign_data["depth_units"] = value
                elif key == "Operator":
                    campaign_data["operator"] = value
                elif key == "Offset Correction":
                    campaign_data["offset_correction"] = float(value.split(",")[0])
                elif key == "Incline Angle":
                    campaign_data["incline_angle"] = float(value.split(",")[1])
                else:
                    campaign_data[key] = value.strip()
        campaign_data["fecha_campo"] = date_time

        # Paso 3. Recorre las líneas con lecturas y separa las variables. Se guarda una lista con cada una
        for line in lines[reading_lines_start:]:
            if ',' in line:
                try:
                    values = line.split(',')
                    depth = float(values[0])
                    a0 = float(values[1])
                    a180 = float(values[2])
                    b0 = float(values[3])
                    b180 = float(values[4])

                    # index y abs_depth
                    index += 1 # añado una posición por línea
                    abs_depth = cota - (index - index_0 + 1) * paso
                except ValueError:
                    print(f"Error al dividir la línea en {filename}: {line.strip()}")
                    continue

                index_values.append(index)
                abs_depth_values. append(abs_depth)
                depth_values.append(depth)
                a0_values.append(a0)
                a180_values.append(a180)
                b0_values.append(b0)
                b180_values.append(b180)

        # añado la última fila, para que parta el cálculo de cero
        index_values.append(index_values[-1] + 1) # posición absoluta en el índice del tubo "index"
        abs_depth_values.append(cota - (index_values[-1] - index_0 + 1) * paso)
        depth_values.append(depth_values[-1] - paso)
        a0_values.append(0)
        a180_values.append(0)
        b0_values.append(0)
        b180_values.append(0)

        # Paso 4. Generar la estructura de salida compatible con JSON
        raw_entries = [] # valores raw
        calc_entries = [] # convertidos en mm
        # Paso 4.a. Primero inserto los valores raw
        for i in range(len(depth_values)):
            entry = {
                "index": index_values[i], # posición absoluta en el índice del tubo
                "cota_abs": abs_depth_values[i], # cota absoluta
                "depth": -depth_values[i], # considero las profundidades positivas
                "a0": a0_values[i],
                "a180": a180_values[i],
                "b0": b0_values[i],
                "b180": b180_values[i]
            }
            raw_entries.append(entry)

        # Paso 4.b. Calcula los valores raw normalizados
        # Se crea el bloque "normalizados", sólo es el paso a mm del raw.
        # Es por unificar debido a como da los datos Sisgeo
        # En resumen, habrá dos bloques además del raw:
        #  - normalizados, en mm. Es un raw en mm, nunca va a cambiar
        #  - calc, en mm. En este paso del importador serán iguales, luego puede cambiar con las correcciones
        for i in range(len(depth_values)):
            entry = valores_calc_directos(
                index_values[i], abs_depth_values[i],
                -depth_values[i], a0_values[i], a180_values[i],
                b0_values[i], b180_values[i], cte_instrument)
            calc_entries.append(entry)
        # Nota: el bloque que depende de los cáculos con referencias y profundidades, se calcula fuera del importador

        # Paso 4.c. Añadir la información al diccionario final
        if date_time:
            data[date_time] = {
                "campaign_info": campaign_info,
                "info_readout": campaign_data,
                "raw": raw_entries,
                #"normalizados": calc_entries,
                "calc": calc_entries # en la importación no hay cambios en calculado, a tener en cuenta en caso de spira
            }
        else:
            print(f"Fecha no encontrada en {filename}")

    return data

def import_Sisgeo(files, index_0, cota):
    # importador para archivos de Sisgeo de inclinómetros verticales, con sonda de 0.5 m
    # index_0 marca dónde comienza el inclinómetro, 1000 si no hay cambios en la boca
    # cota es la cota original de index_0=1000
    # el archivo de sisgeo es un .xml


    # Contante del instrumento para dar mm de desplazamiento por paso
    cte_instrument = 0.025 # =(1/20000)*0.5*1000
    paso = 0.5

    data = {}

    for file in files:
        # Convertir el contenido del archivo (lista de líneas) en un solo string
        content = "\n".join(file['lines'])

        # Parsear el contenido XML desde el string
        root = ET.fromstring(content)

        # Para cada archivo se genera una estructura de datos compatible con el json tipo
        filename = file['filename']
        index = index_0 - 1  # inicializo en índice en cada pasada

        # Inicializar la estructura de datos para la fecha y hora
        campaign_data = {}
        date_time = None

        # hay que formatear la fecha
        # Convertir la fecha original a un objeto datetime
        fecha_obj = datetime.fromisoformat(root.find('test').attrib.get('date'))

        # Convertir el objeto datetime a un string sin fracción de segundos
        date_time = fecha_obj.strftime("%Y-%m-%dT%H:%M:%S") # fecha_sin_fraccion

        # Listas de variables para almacenar los datos
        index_values = []
        abs_depth_values = []
        depth_values = []
        a0_values = []
        a180_values = []
        b0_values = []
        b180_values = []

        # info asociada a la campaña. Por defecto
        campaign_info = {
            "index_0": index_0,
            "importador": "Sisgeo",
            "instrument_constant": cte_instrument,  # valor en mm para Sisgeo
            #"reference": False,
            "active": True,
            "quarentine": False,
            "alarm": "por definir"
        }

        # Paso 1. Rellena los datos de la campaña
        campaign_data = {
            "xml_version": root.attrib.get('version'),
            "encoding": root.attrib.get('encoding'),
            "inclinometric_format_version": root.attrib.get('format_version'),
            "Site": root.attrib.get('site'),
            "nom_campo": root.attrib.get('casing'),
            "type": root.attrib.get('type'),
            "direction": root.attrib.get('direction'),
            "mode": root.attrib.get('mode'),
            "Interval": root.attrib.get('step'),
            "runs": root.attrib.get('runs'),
            "length": root.attrib.get('length'),
            "azimuth": root.attrib.get('azimuth'),
            "site_description": root.findtext('site_description'),
            "tube_description": root.findtext('tube_description'),
            "application_version": root.find('application').attrib.get('version') if root.find('application') is not None else None,
            "master_type": root.find('master').attrib.get('type') if root.find('master') is not None else None,
            "serial": root.find('master').attrib.get('serial') if root.find('master') is not None else None,
            "firmware": root.find('master').attrib.get('firmware') if root.find('master') is not None else None,
            "probe_serial": root.find('instrument').attrib.get('serial') if root.find('instrument') is not None else None,
            "hardware": root.find('instrument').attrib.get('hardware') if root.find('instrument') is not None else None,
            "reading_units": root.find('instrument').attrib.get('unit') if root.find('instrument') is not None else None,
            "factor": root.find('instrument').attrib.get('factor') if root.find('instrument') is not None else None,
            "calibration": root.find('instrument').attrib.get('calibration') if root.find('instrument') is not None else None,
            "fecha_campo": date_time,
        }

        # Paso 2. Recorre las líneas con lecturas y separa las variables
        for test in root.findall('test'):
            #date_time = test.get('date') # esto no está muy pulido
            for run in test.findall('run'):
                run_type = run.get('type')

                for step in run.findall('step'):
                    depth = float(step.get('depth'))
                    a_value = float(step.get('A'))
                    b_value = float(step.get('B'))

                    # Add depth value only once (to avoid duplication)
                    if depth not in depth_values:
                        index += 1
                        abs_depth = cota - (index - index_0 + 1) * paso

                        index_values.append(index)
                        abs_depth_values.append(abs_depth)
                        depth_values.append(depth)

                    if run_type == 'A1B1':
                        a0_values.append(a_value)
                        b0_values.append(b_value)
                    elif run_type == 'A3B3':
                        a180_values.append(a_value)
                        b180_values.append(b_value)

        # Paso 3. Añado la última fila, para que parta el cálculo de cero
        index_values.append(index_values[-1] + 1)  # posición absoluta en el índice del tubo
        abs_depth_values.append(cota - (index_values[-1] - index_0 + 1) * paso)
        depth_values.append(depth_values[-1] + paso)
        a0_values.append(0)
        a180_values.append(0)
        b0_values.append(0)
        b180_values.append(0)

        # Paso 4. Generar la estructura de salida compatible con JSON
        raw_entries = []  # valores raw
        calc_entries = []  # convertidos en mm

        # Paso 4.a. Primero inserto los valores raw
        for i in range(len(depth_values)):
            entry = {
                "index": index_values[i],  # posición absoluta en el índice del tubo
                "cota_abs": abs_depth_values[i],  # cota absoluta
                "depth": depth_values[i],  # considero las profundidades positivas
                "a0": a0_values[i],
                "a180": a180_values[i],
                "b0": b0_values[i],
                "b180": b180_values[i]
            }
            raw_entries.append(entry)

        # Paso 4.b. Calcula los valores raw normalizados
        # Se crea el bloque "normalizados", sólo es el paso a mm del raw.
        # Es por unificar debido a como da los datos Sisgeo
        # En resumen, habrá dos bloques además del raw:
        #  - normalizados, en mm. Es un raw en mm, nunca va a cambiar
        #  - calc, en mm. En este paso del importador serán iguales, luego puede cambiar con las correcciones
        for i in range(len(depth_values)):
            entry = valores_calc_directos(
                index_values[i], abs_depth_values[i],
                depth_values[i], a0_values[i], a180_values[i],
                b0_values[i], b180_values[i], cte_instrument)
            calc_entries.append(entry)
        # Nota: el bloque que depende de los cáculos con referncias y profundidades, se calcula fuera del importador

        # Paso 4.c. Añadir la información al diccionario final
        if date_time:
            data[date_time] = {
                "campaign_info": campaign_info,
                "info_readout": campaign_data,
                "raw": raw_entries,
                #"normalizados": calc_entries,
                "calc": calc_entries  # en la importación no hay cambios en calculado, a tener en cuenta en caso de spira
            }
        else:
            print(f"Fecha no encontrada en {filename}")
    return data


def import_soil_dux(files, index_0, cota):
    # Constantes del instrumento
    cte_instrument = 0.005  # La salida es en 100.000*sen -> 100.000*sen = R -> sen = delta/L -> R/100.000 = delta / L
    # L=0.5m = 0.5*1000 -> delta = R * 0.005
    paso = 0.5  # Intervalo de medición en metros

    data = {}

    for file in files:
        filename = file['filename']
        lines = file['lines']

        index = index_0 - 1
        campaign_data = {}
        campaign_info = {}
        raw_entries = []
        calc_entries = []

        # Extraer información de instalación
        for line in lines:
            if line.startswith("Installation v1"):
                install_params = line.strip().split(',')
                campaign_info = {
                    "index_0": index_0,
                    "importador": "Soil (dux)",
                    "instrument_constant": cte_instrument,
                    "reference": False,
                    "active": True,
                    "quarentine": False,
                    "alarm": "por definir"
                }
            elif line.startswith("Survey v1"):
                survey_params = line.strip().split(',')
                date_str = survey_params[1]  # Fecha en formato YYYY/MM/DD HH:MM:SS
                date_time = datetime.strptime(date_str, "%Y/%m/%d %H:%M:%S").isoformat()
                campaign_data = {
                    "probe_serial": survey_params[4],
                    "factor": float(survey_params[5]),
                    "fecha_campo": date_time
                }
                break  # Ya tenemos la información necesaria del encabezado

        # Extraer los datos de medición
        for line in lines:
            if re.match(r"^\d+\.\d+,-?\d+,-?\d+,-?\d+,-?\d+$", line.strip()):
                values = list(map(float, line.strip().split(',')))
                depth, a0, a180, b0, b180 = values

                index += 1
                abs_depth = cota - (index - index_0 + 1) * paso

                entry = {
                    "index": index,
                    "cota_abs": abs_depth,
                    "depth": depth,
                    "a0": a0,
                    "a180": a180,
                    "b0": b0,
                    "b180": b180
                }
                raw_entries.append(entry)
                calc_entries.append(valores_calc_directos(index, abs_depth, depth, a0, a180, b0, b180, cte_instrument))

        # Agregar una última fila para cierre
        index += 1
        abs_depth -= paso
        raw_entries.append(
            {"index": index, "cota_abs": abs_depth, "depth": depth + paso, "a0": 0, "a180": 0, "b0": 0, "b180": 0})
        calc_entries.append(valores_calc_directos(index, abs_depth, depth + paso, 0, 0, 0, 0, cte_instrument))

        # Guardar en la estructura final
        if date_time:
            data[date_time] = {
                "campaign_info": campaign_info,
                "info_readout": campaign_data,
                "raw": raw_entries,
                #"normalizados": calc_entries,
                "calc": calc_entries
            }
        else:
            print(f"Fecha no encontrada en {filename}")

    return data

# Funciones auxiliares   +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
def insertar_camp(data, fechas_agg, selected_filename, data_path):
   # inserta las campañas seleccionadasa

    try:
         # Guardar los cambios en el archivo JSON original
        if not selected_filename:
            raise ValueError("No se ha seleccionado ningún archivo para guardar.")

        file_path = os.path.join(data_path, selected_filename)

        # Cargar el contenido actual del archivo JSON
        # realmente se puede optimizar porque el archivo json ya esta en memoria, pero esto penaliza poco
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                existing_data = json.load(json_file)
        else:
            existing_data = {}

        # Filtrar selected_file_data para incluir solo las fechas en fechas_agg
        filtered_data = {key: value for key, value in data.items() if key in fechas_agg}

        # Actualizar el contenido existente con los nuevos datos
        existing_data.update(filtered_data)

        # Guardar el archivo actualizado
        with open(file_path, 'w') as json_file:
            json.dump(existing_data, json_file, indent=4)

        return "campañas añadidas"
    except Exception as e:
        print(f"Error al actualizar el archivo JSON 1: {e}")
        return "Error"

def es_fecha_isoformat(clave):
    # Expresión regular para fechas ISO: 'YYYY-MM-DD' o 'YYYY-MM-DDTHH:MM:SS'
    patron_fecha = r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?$"
    return bool(re.match(patron_fecha, clave))

def default_value(data):

    try:
        for date_str, content in data.items():
            # Si la clave es "info", extraer la información general
            if date_str == "info":
                extracted_data = {
                    "cota_1000": content.get("cota_1000", 0),
                    "adquisicion": content.get("adquisicion", "manual"),
                    "disposicion": content.get("disposicion", "vertical"),
                    "sentido_calculo": content.get("sentido_calculo", "abajo-arriba"),
                    "umbrales": content.get("umbrales", "por_definir")
                }

        # Obtener todas las claves del diccionario que parezcan fechas
        fechas = sorted([clave for clave in data.keys() if isinstance(clave, str) and "T" in clave])

        # Obtener las últimas campañas
        latest_date = None
        camp_anterior_referencia = None
        latest_reference = None

        # Recorre la lista en orden inverso para encontrar la última campaña activa
        for fecha in reversed(fechas):
            if data[fecha]["campaign_info"]["active"]:
                latest_date = fecha
                break

        # Última referencia activa
        for fecha in reversed(fechas):
            if data[fecha]["campaign_info"]["reference"] and data[fecha]["campaign_info"]["active"]:
                latest_reference = fecha
                break

        # Campaña activa anterior a la última referencia
        if latest_reference:
            try:
                idx_latest = fechas.index(latest_reference)
                for fecha in reversed(fechas[:idx_latest]):
                    if data[fecha]["campaign_info"]["active"]:
                        camp_anterior_referencia = fecha
                        break
            except ValueError:
                print("Error: latest_reference no se encuentra en la lista de fechas")

        # Obtener información de la última campaña activa
        latest_importador = data[latest_date].get("campaign_info", {}).get("importador") if latest_date else None
        latest_index_0 = data[latest_date].get("campaign_info", {}).get("index_0") if latest_date else None

        # Completar el diccionario con los valores obtenidos
        extracted_data.update({
            "latest_campaign": latest_date,
            "latest_reference": latest_reference,
            "camp_anterior_referencia": camp_anterior_referencia,
            "importador": latest_importador,
            "index_0": latest_index_0
        })
        return extracted_data

    except Exception as e:
        print(f"Error al leer el archivo JSON: {e}")

    # Retornar un diccionario vacío en caso de error
    return {}

def parse_alarm_val(raw_alarm):
    """
    raw_alarm puede ser:
     - lista de strings (e.g. ['Supera umbral "Red_a", nivel: 12', ...])
     - string
     - None
    Devuelve un int (el primer nivel detectado) o None.
    """
    # normaliza a string único o None
    if isinstance(raw_alarm, list):
        raw = raw_alarm[0] if raw_alarm else ""
    elif isinstance(raw_alarm, str):
        raw = raw_alarm
    else:
        raw = ""
    # busca 'nivel: número'
    m = re.search(r'nivel:\s*(\d+)', raw)
    return int(m.group(1)) if m else None
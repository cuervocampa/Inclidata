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

    data = {}

    for file in files:
        filename = file['filename']
        lines = file['lines']
        
        # --- DETECCIÓN DE FORMATO ---
        # AQUI se identifica qué formato tiene el archivo leyendo las cabeceras.
        format_type = None
        header_row_idx = -1
        
        # Escaneamos las primeras líneas para encontrar la cabecera
        for i, line in enumerate(lines[:50]):
            line_upper = line.strip().upper()
            
            # FORMATO B: Nuevo formato CSV
            # Busca cabecera: ID, DEPTH_METRES (o METERS), ...
            # Confirma si contiene columnas clave
            if "ID," in line_upper and ("DEPTH_METRES" in line_upper or "DEPTH_METERS" in line_upper) and "A_POSITIVE_MM" in line_upper:
                format_type = "B"
                header_row_idx = i
                break
            
            # FORMATO A: Formato original RST
            # Busca cabeceras tipo: Depth,Face A+,Face A-,Face B+,Face B-
            # O la versión reducida: Depth,Face
            elif "DEPTH,FACE" in line_upper or ("DEPTH" in line_upper and "FACE A+" in line_upper):
                format_type = "A"
                header_row_idx = i
                break
        
        if format_type is None:
            print(f"No se pudo identificar un formato válido para {filename}. Se requiere cabecera RST conocida.")
            continue

        # --- PARÁMETROS SEGÚN FORMATO ---
        if format_type == "B":
            # Formato B (Nuevo): Los datos vienen en MM -> Cte = 1
            cte_instrument = 1.0
            paso_defecto = 0.5 # Se intentará leer del archivo
        else: # Format A
            # Formato A (Original): Los datos suelen venir en Metros -> Cte = 1000
            cte_instrument = 1000.0
            paso_defecto = 0.5
            
        # Variables comunes
        campaign_info = {
            "index_0": index_0,
            "importador": "RST",
            "instrument_constant": cte_instrument,
            "active": True,
            "quarentine": False,
            "alarm": "por definir"
        }
        campaign_data = {}
        date_time = None
        index_values = []
        abs_depth_values = []
        depth_values = []
        a0_values = []
        a180_values = []
        b0_values = []
        b180_values = []
        
        # --- PARSING DE METADATA (Común y específico) ---
        # Leemos líneas anteriores a la cabecera para metadatos
        meta_lines = lines[:header_row_idx] if header_row_idx > 0 else lines[:20]
        
        for line in meta_lines:
            # Limpieza básica
            if ':' not in line and ',' not in line: continue
            
            parts = []
            # Intentar separar clave-valor dependiendo del formato
            # En Format A (legacy), se usa comma. En Format B (nuevo), se usa colon.
            if format_type == "B":
                if ':' in line:
                    parts = line.split(':', 1)
            else: # Format A
                if ',' in line:
                    parts = line.split(',', 1)
            
            if not parts: continue
                
            key = parts[0].strip()
            value = parts[1].strip()
            key_upper = key.upper()
             
            # Intervalo (Paso)
            if "INTERVAL" in key_upper:
                try:
                    val_clean = value.lower().replace('m', '').replace('ft', '').strip()
                    paso_defecto = float(val_clean)
                    campaign_data["interval"] = paso_defecto
                except: pass
            
            # Fecha (Survey Date / Reading Date)
            elif "SURVEY DATE" in key_upper or "READING DATE" in key_upper:
                # Formatos posibles: 20250828_103102 (B) o m/d/y (A)
                try:
                    if "_" in value and len(value) >= 15: # Tipo 20250828_103102
                        date_time = datetime.strptime(value.strip(), "%Y%m%d_%H%M%S").isoformat()
                    elif "," in value: # Tipo m/d/y,h:m:s
                        date_time = datetime.strptime(value.strip(), "%m/%d/%Y,%H:%M:%S").isoformat()
                    else: # Tipo m/d/y
                        date_time = datetime.strptime(value.strip(), "%m/%d/%Y").isoformat()
                except ValueError:
                    pass
            
            # Otros metadatos
            elif "BOREHOLE" in key_upper:
                campaign_data["nom_campo"] = value
            elif "SERIAL" in key_upper:
                campaign_data["probe_serial"] = value
            elif "OPERATOR" in key_upper:
                campaign_data["operator"] = value
            elif "SITE" in key_upper:
                campaign_data["Site"] = value
        
        campaign_data["fecha_campo"] = date_time
        
        # --- PARSING DE DATOS ---
        header_line = lines[header_row_idx]
        headers = [h.upper().strip() for h in header_line.split(',')]
        
        # Mapeo de columnas
        col_map = {}
        try:
            if format_type == "B":
                # Buscar columnas específicas del formato B
                # DEPTH_METRES puede ser DEPTH_METERS
                if "DEPTH_METRES" in headers:
                    col_map['depth'] = headers.index("DEPTH_METRES")
                elif "DEPTH_METERS" in headers:
                    col_map['depth'] = headers.index("DEPTH_METERS")
                else:
                     # Si no encuentra Depth exacto, puede haber un error en el archivo
                     # pero si detectó el formato, asumimos que existe depth
                     raise ValueError("Columna DEPTH no encontrada")

                col_map['a0'] = headers.index("A_POSITIVE_MM")
                col_map['a180'] = headers.index("A_NEGATIVE_MM")
                col_map['b0'] = headers.index("B_POSITIVE_MM")
                col_map['b180'] = headers.index("B_NEGATIVE_MM")
                
            else: # Format A
                # Formato original posicional si no se encuentran nombres exactos de columnas
                # Cabecera esperada: Depth,Face A+,Face A-,Face B+,Face B-
                if "DEPTH" in headers:
                     col_map['depth'] = headers.index("DEPTH")
                else:
                     col_map['depth'] = 0
                     
                if "FACE A+" in headers:
                    col_map['a0'] = headers.index("FACE A+")
                    col_map['a180'] = headers.index("FACE A-")
                    col_map['b0'] = headers.index("FACE B+")
                    col_map['b180'] = headers.index("FACE B-")
                else:
                    # Fallback posicional estricto para formato antiguo 'Depth,Face'
                    col_map['a0'] = 1
                    col_map['a180'] = 2
                    col_map['b0'] = 3
                    col_map['b180'] = 4

        except ValueError as e:
            print(f"Error mapeando columnas en {filename}: {e}")
            continue

        # Lectura fila a fila
        index = index_0 - 1
        
        for line in lines[header_row_idx+1:]:
            if not line.strip(): continue
            
            # --- SANITIZACIÓN DE DATOS ---
            # Reemplazar 'null' por '0' para evitar errores de conversión a float
            # Esto corrige archivos antiguos que tienen 'null' en columnas no usadas (ej. TEMP)
            # o permite recuperar filas con datos parciales.
            line = re.sub(r'(?i)\bnull\b', '0', line)
            
            parts = line.split(',')
            
            # Verificar longitud suficiente
            req_len = max(col_map.values()) + 1
            if len(parts) < req_len: continue
            
            try:
                # Extraer valores raw
                d_val = float(parts[col_map['depth']])
                a0_val = float(parts[col_map['a0']])
                a180_val = float(parts[col_map['a180']])
                b0_val = float(parts[col_map['b0']])
                b180_val = float(parts[col_map['b180']])
                
                # Procesar Depth: SIEMPRE valor absoluto según requerimiento
                depth = abs(d_val)
                
                index += 1
                # Abs Depth (Cota): Se asume orden descendente (top-down)
                abs_depth = cota - (index - index_0 + 1) * paso_defecto
                
                index_values.append(index)
                abs_depth_values.append(abs_depth)
                depth_values.append(depth)
                a0_values.append(a0_val)
                a180_values.append(a180_val)
                b0_values.append(b0_val)
                b180_values.append(b180_val)
                
            except ValueError:
                continue

        # Fila de cierre (Bottom)
        if index_values:
            index_values.append(index_values[-1] + 1)
            abs_depth_values.append(cota - (index_values[-1] - index_0 + 1) * paso_defecto)
            # Profundidad final = profundidad anterior + paso
            depth_values.append(depth_values[-1] + paso_defecto) 
            a0_values.append(0)
            a180_values.append(0)
            b0_values.append(0)
            b180_values.append(0)

        # Generar JSON Output
        raw_entries = []
        calc_entries = []
        
        for i in range(len(depth_values)):
            # RAW
            entry = {
                "index": index_values[i],
                "cota_abs": abs_depth_values[i],
                "depth": depth_values[i], # Almacenar positivo (módulo)
                "a0": a0_values[i],
                "a180": a180_values[i],
                "b0": b0_values[i],
                "b180": b180_values[i]
            }
            raw_entries.append(entry)
            
            # CALC (Normalizado a mm)
            # Pasamos cte_instrument que será 1 o 1000 según formato
            # depth se pasa tal cual (positivo)
            entry_calc = valores_calc_directos(
                index_values[i], abs_depth_values[i],
                depth_values[i], 
                a0_values[i], a180_values[i],
                b0_values[i], b180_values[i], 
                cte_instrument)
            calc_entries.append(entry_calc)

        if date_time:
            data[date_time] = {
                "campaign_info": campaign_info,
                "info_readout": campaign_data,
                "raw": raw_entries,
                "calc": calc_entries
            }
        else:
            print(f"Fecha no encontrada en {filename}. Cabecera a línea {header_row_idx}")

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
def insertar_camp(data, fechas_agg, selected_filename, data_path, fallback_data=None):
    # inserta las campañas seleccionadas

    try:
         # Guardar los cambios en el archivo JSON original
        if not selected_filename:
            raise ValueError("No se ha seleccionado ningún archivo para guardar.")

        # Buscar el archivo: primero directo en data_path, luego recursivamente
        file_path = os.path.join(data_path, selected_filename)

        if not os.path.exists(file_path):
            # Buscar recursivamente en data_path por nombre de archivo
            for root, dirs, files in os.walk(data_path):
                if selected_filename in files:
                    file_path = os.path.join(root, selected_filename)
                    print(f"Archivo encontrado en: {file_path}")
                    break

        # Cargar el contenido actual del archivo JSON
        # Si el archivo no existe en disco (ej. subido por drag-and-drop desde fuera de data/),
        # usar fallback_data (tubo en memoria) como base
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                existing_data = json.load(json_file)
        elif fallback_data is not None:
            existing_data = dict(fallback_data)
        else:
            existing_data = {}

        # Filtrar selected_file_data para incluir solo las fechas en fechas_agg
        filtered_data = {key: value for key, value in data.items() if key in fechas_agg}

        # Actualizar el contenido existente con los nuevos datos
        existing_data.update(filtered_data)

        # --- ORDENAR CRONOLÓGICAMENTE ---
        # Separar claves especiales y fechas
        special_keys = ['info', 'umbrales']
        # Identificar claves de fecha (asumimos formato ISO o contienen 'T', y no son especiales)
        date_keys = [k for k in existing_data.keys() if k not in special_keys]
        
        # Ordenar las fechas
        # Es robusto ordenarlas como string ISO 8601
        date_keys.sort()
        
        # Reconstruir el diccionario ordenado
        sorted_data = {}
        
        # 1. Insertar 'info' y 'umbrales' al principio si existen
        for k in special_keys:
            if k in existing_data:
                sorted_data[k] = existing_data[k]
        
        # 2. Insertar las campañas ordenadas
        for k in date_keys:
            sorted_data[k] = existing_data[k]

        # Guardar el archivo actualizado
        print(f"Guardando archivo en: {file_path}")
        with open(file_path, 'w') as json_file:
            json.dump(sorted_data, json_file, indent=4)

        return "campañas añadidas"
    except Exception as e:
        print(f"Error al actualizar el archivo JSON 1: {e}")
        import traceback
        traceback.print_exc()
        return "Error"

def es_fecha_isoformat(clave):
    # Expresión regular para fechas ISO: 'YYYY-MM-DD' o 'YYYY-MM-DDTHH:MM:SS'
    patron_fecha = r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?$"
    return bool(re.match(patron_fecha, clave))

def default_value(data):
    """
    Extrae valores por defecto del archivo JSON.
    Maneja correctamente archivos sin campañas (solo con 'info' y 'umbrales').
    """
    # Inicializar extracted_data con valores por defecto
    extracted_data = {
        "cota_1000": 0,
        "adquisicion": "manual",
        "disposicion": "vertical",
        "sentido_calculo": "abajo-arriba",
        "umbrales": "por_definir",
        "latest_campaign": None,
        "latest_reference": None,
        "camp_anterior_referencia": None,
        "importador": None,
        "index_0": None
    }

    try:
        # Extraer información de la clave "info" si existe
        if "info" in data:
            content = data["info"]
            extracted_data.update({
                "cota_1000": content.get("cota_1000", 0),
                "adquisicion": content.get("adquisicion", "manual"),
                "disposicion": content.get("disposicion", "vertical"),
                "sentido_calculo": content.get("sentido_calculo", "abajo-arriba"),
                "umbrales": content.get("umbrales", "por_definir")
            })

        # Obtener todas las claves del diccionario que parezcan fechas (campañas)
        fechas = sorted([clave for clave in data.keys() if isinstance(clave, str) and "T" in clave])

        # Si no hay fechas (campañas), retornar los valores por defecto
        if not fechas:
            return extracted_data

        # Obtener las últimas campañas
        latest_date = None
        camp_anterior_referencia = None
        latest_reference = None

        # Recorre la lista en orden inverso para encontrar la última campaña activa
        for fecha in reversed(fechas):
            if data[fecha].get("campaign_info", {}).get("active", False):
                latest_date = fecha
                break

        # Última referencia activa
        for fecha in reversed(fechas):
            campaign_info = data[fecha].get("campaign_info", {})
            if campaign_info.get("reference", False) and campaign_info.get("active", False):
                latest_reference = fecha
                break

        # Campaña activa anterior a la última referencia
        if latest_reference:
            try:
                idx_latest = fechas.index(latest_reference)
                for fecha in reversed(fechas[:idx_latest]):
                    if data[fecha].get("campaign_info", {}).get("active", False):
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
        import traceback
        traceback.print_exc()

    # Retornar el diccionario con valores por defecto en caso de error
    return extracted_data

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
# utils/funciones_comunes.py

import json
from datetime import datetime
import plotly.colors as pcolors
import os
import random

#from Descompuesto_L8_unsolouso.camp_a_lista import fechas


# función para los calculados directos de cada profundidad
def debug_funcion(texto):
    # Obtener la hora actual
    hora_actual = datetime.now()

    # Imprimir la hora en el formato deseado
    return print(texto, hora_actual.strftime("%Y-%m-%d %H:%M:%S"))

def valores_calc_directos(index, cota_abs, depth, a0, a180, b0, b180, cte):
    # Los valores de a0c-b180c vienen en mm para el desplazamiento absoluto de ese escalón
    # en la cte ya viene incluido el paso a mm y la consideración de longitud del torpedo

    a0c = round(a0 * cte, 2)
    a180c = round(a180 * cte, 2)
    b0c = round(b0 * cte, 2)
    b180c = round(b180 * cte, 2)
    checksum_a = round(a0c + a180c, 4)
    checksum_b = round(b0c + b180c, 4)
    dev_a = round((a0c - a180c) / 2, 2)  # dev media para cada profundidad
    dev_b = round((b0c - b180c) / 2, 2)

    # monto el diccionario en la función
    entry = {
        "index": index,
        "cota_abs": cota_abs,
        "depth": depth,
        "a0": a0c,
        "a180": a180c,
        "b0": b0c,
        "b180": b180c,
        "checksum_a": checksum_a,
        "checksum_b": checksum_b,
        "dev_a": dev_a,
        "dev_b": dev_b
    }
    return entry
######################################################################################################################
######################################################################################################################
# cálculos acumulados y en función de la lectura cero
def buscar_referencia(data, fecha_calc):
    #fechas = sorted([datetime.fromisoformat(fecha) for fecha in data.keys() if fecha != 'info'])

    fechas = sorted([
        datetime.fromisoformat(fecha)
        for fecha in data.keys()
        if isinstance(fecha, str)  # Asegurar que es una cadena
           and fecha.count('-') >= 2  # Un filtro rápido para evitar textos claramente no relacionados con fechas
           and fecha.count('T') <= 1  # Para evitar entradas con múltiples "T" que no sean ISO
           and all(c.isdigit() or c in "-T:." for c in fecha)  # Solo caracteres esperados en una fecha ISO
           and fecha[0].isdigit()  # Asegurar que empieza con un número (año)
           and '-' in fecha  # Asegurar que tiene guiones como parte del formato de fecha
           and ':' in fecha  # Asegurar que tiene dos puntos (para la parte de la hora)
           and (  # Intentar convertir la fecha para validarla
               lambda f: datetime.fromisoformat(f) if f else False
           )(fecha)
    ])

    fecha_calc_dt = datetime.fromisoformat(fecha_calc)

    fecha_referencia = None
    for fecha in reversed(fechas):
        if fecha <= fecha_calc_dt and data[fecha.isoformat()]['campaign_info']['reference']:
            fecha_referencia = fecha.isoformat()
            break

    return fecha_referencia


def buscar_ant_referencia(data, fecha_referencia):
    fechas = sorted([datetime.fromisoformat(fecha) for fecha in data.keys() if fecha != 'info'])
    fecha_ref_dt = datetime.fromisoformat(fecha_referencia)

    fecha_ant_referencia = None
    for fecha in reversed(fechas):
        if fecha < fecha_ref_dt and data[fecha.isoformat()]['campaign_info']['active']:
            fecha_ant_referencia = fecha.isoformat()
            break

    return fecha_ant_referencia


def extraer_fechas_activas(diccionario):
    # Lista para almacenar las fechas activas
    fechas_activas = []

    # Iterar a través de todas las claves del diccionario
    for clave in diccionario.keys():
        # Ignorar las claves especiales que no son fechas
        if clave in ["info", "umbrales"]:
            continue

        # Verificar si es una fecha con campaña activa
        try:
            if diccionario[clave].get('campaign_info', {}).get('active', False) == True:
                fechas_activas.append(clave)
        except (KeyError, AttributeError):
            # Si hay errores al acceder a las claves anidadas, ignorar esta entrada
            continue

    # Ordenar las fechas de más antigua a más reciente
    # Asumiendo que las fechas están en formato ISO (como '2024-11-20T12:39:22')
    fechas_activas.sort()

    return fechas_activas

def calcular_incrementos(data, fecha_calc,fecha_referencia):
    # Parámetros:
    # data: tubo + campañas añadidas
    # fecha_calc: fecha a calcular
    # fecha_referencia: referencia para fecha_calc
    # fecha_ant_referencia: fecha anterior active=true
    # es_referencia, si es referencia
    # salida:
    #                 "incr_dev_a": cambio de pendiente respecto a la referencia,
    #                 "incr_dev_b": ,
    #                 "incr_dev_abs_a": cambio de pendiente respecto a la campaña origen,
    #                 "incr_dev_abs_b": ,
    #                 "abs_dev_a": Forma del tubo,
    #                 "abs_dev_b": ,
    #                 "desp_a": diferencia absoluta,
    #                 "desp_b":

    calc_fecha_calc = data[fecha_calc]['calc'] # del json considero sólo 'calc' de la campaña seleccionada
    calc_fecha_referencia = data[fecha_referencia]['calc'] # del jason considero 'calc' de la campaña referencia anterior

    # datos anterior
    if fecha_calc == fecha_referencia or fecha_calc == fechas_activas[0]:
        # Verificar si hay una fecha anterior
        if indice_actual > 0:
            # Devolver la fecha anterior
            fecha_anterior = fechas_activas[indice_actual - 1]
        else:
            # No hay fecha anterior (es la primera fecha de la lista)
            fecha_anterior = fechas_activas[0]
        calc_fecha_anterior = data[fecha_anterior]['calc']  # del json considero 'calc' de la campaña activa anterior

    fechas_activas = extraer_fechas_activas(data) # lista de fechas con active = true

    # Añadir valores iniciales de incr_dev_abs_a y incr_dev_abs_b a todos los índices para evitar el error inicial
    for index_info in calc_fecha_calc:
        index_info['incr_dev_abs_a'] = 0
        index_info['incr_dev_abs_b'] = 0



    # Calcular incr_dev_a y incr_dev_b
    for index_info in calc_fecha_calc:
        index = index_info['index']
        referencia_info = next((item for item in calc_fecha_referencia if item['index'] == index), None) # valores de la camp referencia para esa profundidad


        if referencia_info:
            index_info['incr_dev_a'] = round(index_info['dev_a'] - referencia_info['dev_a'], 2)
            index_info['incr_dev_b'] = round(index_info['dev_b'] - referencia_info['dev_b'], 2)
            index_info['incr_dev_abs_a'] = index_info['incr_dev_a'] + referencia_info['incr_dev_abs_a']
            index_info['incr_dev_abs_b'] = index_info['incr_dev_b'] + referencia_info['incr_dev_abs_b']

            if fecha_calc == fecha_referencia or fecha_calc == fechas_activas[0]:
                # se debe sumar el valor anterior
                anterior_info = next((item for item in calc_fecha_anterior if item['index'] == index), None)  # valores de la camp anterior para esa profundidad
                for index_info in calc_fecha_calc:
                    index_info['incr_dev_abs_a'] = anterior_info['incr_dev_abs_a']
                    index_info['incr_dev_abs_b'] = anterior_info['incr_dev_abs_b']
                #print ('datos fecha anterior')
                #print(calc_fecha_anterior[0]["incr_dev_abs_a"])

                #print ('datos fecha actual')
                #print(calc_fecha_calc[0]["incr_dev_abs_a"])


    # Insertar parámetros calculados en el diccionario data, preservando los campos existentes excepto incr_dev_a y incr_dev_b
    for index_info in calc_fecha_calc:
        existing_info = next((item for item in data[fecha_calc]['calc'] if item['index'] == index_info['index']), None)
        if existing_info:
            for key, value in index_info.items():
                if key not in ['incr_dev_a', 'incr_dev_b']:
                    existing_info[key] = value
        else:
            data[fecha_calc]['calc'].append(depth_info) # sobra?
    # Calcular abs_dev_a y abs_dev_b
    for i, index_info in enumerate(calc_fecha_calc):
        # envolvente del tubo
        index_info['abs_dev_a'] = round(sum(item['dev_a'] for item in calc_fecha_calc[i:]), 2)
        index_info['abs_dev_b'] = round(sum(item['dev_b'] for item in calc_fecha_calc[i:]), 2)

    # Calcular desp_a y desp_b
    # desplazamientos respecto a la campaña origen
    for i, index_info in enumerate(calc_fecha_calc):
        index_info['desp_a'] = round(sum(item.get('incr_dev_a', 0) for item in calc_fecha_calc[i:]), 2)
        index_info['desp_b'] = round(sum(item.get('incr_dev_b', 0) for item in calc_fecha_calc[i:]), 2)

    # Sumo el offset de desplazamiento que tenga en la referencia, o en la campaña anterior activa
    # busco la campaña anterior 'Activa', extraigo todas las fechas 'active'
    # Asumiendo que tienes un diccionario llamado 'datos'

    fecha_activa_anterior = obtener_fecha_activa_anterior(data, fecha_calc)#['calc']

    # evito el error en caso de que sea la primera lectura del tubo
    if fecha_activa_anterior:
        # el diccionario NO está vacío
        fecha_activa_anterior = obtener_fecha_activa_anterior(data, fecha_calc)['calc']


    # da error en caso de ser la primera fecha
    if fecha_activa_anterior is None:
        # es la primera fecha para todo
        fecha_activa_anterior = fecha_calc


    for index_info in calc_fecha_calc:
        index = index_info['index']

        # si la campaña es referencia, se debe coger la fecha activa anterior
        if fecha_calc == fecha_referencia:
            # Se le sumará el desplazamiento de la campaña anterior
            referencia_info = next((item for item in fecha_activa_anterior if item['index'] == index), None)
        else:
            # se considera el desplazamiento de la campaña origen
            referencia_info = next((item for item in calc_fecha_referencia if item['index'] == index), None)

        if referencia_info:
            # se suma el desp de la campaña origen
            index_info['desp_a'] = round(index_info['desp_a'] + referencia_info['desp_a'], 2)
            index_info['desp_b'] = round(index_info['desp_b'] + referencia_info['desp_b'], 2)

    return data


def obtener_fecha_activa_anterior(datos, fecha_calc):
    # Extraer fechas activas

    fechas_activas = [fecha for fecha in datos.keys()
                      if isinstance(datos[fecha], dict) and 'campaign_info' in datos[fecha]
                      and datos[fecha]['campaign_info'].get('active') == True]

    # Si no hay fechas activas, devolver un diccionario vacío

    if not fechas_activas:
        return {}

    # Convertir fechas de string a objetos datetime
    fechas_datetime = []
    for fecha_str in fechas_activas:
        try:
            fecha_dt = datetime.fromisoformat(fecha_str)
            fechas_datetime.append((fecha_str, fecha_dt))
        except ValueError:
            continue

    # Convertir fecha_calc a datetime
    try:
        fecha_calc_dt = datetime.fromisoformat(fecha_calc)
    except ValueError:
        return {}

    # Ordenar fechas de más reciente a más antigua
    fechas_ordenadas = sorted(fechas_datetime, key=lambda x: x[1], reverse=True)

    # Buscar la fecha inmediatamente anterior a fecha_calc
    fecha_anterior = None
    for fecha_str, fecha_dt in fechas_ordenadas:
        if fecha_dt < fecha_calc_dt:
            fecha_anterior = fecha_str
            break

    # Si no se encuentra una fecha anterior, devolver un diccionario vacío
    if not fecha_anterior:
        return {}

    # Devolver los datos de la fecha encontrada

    return datos.get(fecha_anterior, {})



def get_color_for_index(index, color_scheme="multicromo", total_colors=10):
    """
    Devuelve un color para un índice determinado según el esquema de colores proporcionado.
    Args:
        index (int): índice del color.
        color_scheme (str): esquema de colores a usar ("monocromo" o "multicromo").
        total_colors (int): número total de colores (aplicable para "monocromo").
    Returns:
        str: Color en formato hexadecimal.
    """
    if color_scheme == "monocromo":
        # Definir los colores inicial y final dentro de la función
        color_start = (173 / 255, 216 / 255, 230 / 255)  # Azul claro
        color_end = (0 / 255, 0 / 255, 139 / 255)          # Azul fuerte

        # Evitar división por cero: si total_colors es menor o igual a 1, usar directamente el color inicial
        if total_colors <= 1:
            color_rgb = color_start
        else:
            # Generar degradado entre color_end y color_start (invertir para que las más antiguas sean más claras)
            color_rgb = [
                color_end[i] + (color_start[i] - color_end[i]) * index / (total_colors - 1)
                for i in range(3)
            ]
        # Convertir RGB a formato hexadecimal
        color_hex = "#%02x%02x%02x" % (
            int(color_rgb[0] * 255),
            int(color_rgb[1] * 255),
            int(color_rgb[2] * 255),
        )
        return color_hex
    elif color_scheme == "multicromo":
        # Usar la paleta de colores de Plotly para mejor diferenciación
        plotly_palette = pcolors.qualitative.Plotly
        color_hex = plotly_palette[index % len(plotly_palette)]
        return color_hex
    else:
        raise ValueError("Esquema de color no reconocido. Usa 'monocromo' o 'multicromo'.")


def df_to_excel(df,nombre_archivo):
    # función para pruebas
    # Obtener la ruta del directorio actual donde está la app
    directorio_actual = os.getcwd()

    # Especificar el nombre del archivo Excel
    #nombre_archivo = 'salida_bias.xlsx'
    nombre_archivo = nombre_archivo + '.xlsx'

    # Crear la ruta completa del archivo
    ruta_archivo = os.path.join(directorio_actual, nombre_archivo)

    # Guardar el DataFrame en Excel
    df.to_excel(ruta_archivo, index=False, engine='openpyxl')

# Definir la función camp_independiente
def camp_independiente(fecha_seleccionada, df):
    """
    Comprueba si la siguiente campaña cumple las condiciones especificadas.

    Parámetros:
    - fecha_seleccionada: Fecha de la campaña actual (datetime).
    - df: DataFrame con las campañas, ordenado cronológicamente descendente.

    Retorna:
    - True si la siguiente campaña cumple las condiciones, False en caso contrario.
    """
    # Ordenar por fecha en orden decreciente (por si acaso)
    df = df.sort_values(by='Fecha', ascending=False).reset_index(drop=True)

    # Encontrar el índice de la campaña seleccionada
    idx = df[df['Fecha'] == fecha_seleccionada].index
    idx = idx[0]

    # condición incial, si es la última campaña true
    if idx == 0:
        return True
    # condición inicial para idx>0, si es referencia es false
    if df.iloc[idx]["Referencia"]:
        # esta condición parece redundante con una posterior
        return False

    # busco el número de campañas más nuevas que son activa y no referencia
    if idx == 1:
        # caso de que se selecciona la penúltima fecha
        if df.iloc[0]["Referencia"]:
            return False
        else:
            return True
    elif idx > 1:
        # siguiente_ref debe ser >0 para que sea campaña independiente, i.e. hay una activa antes de la sig referencia
        siguiente_ref = 0
        for _, row in df.iloc[idx - 1::-1].iterrows():
            if row["Activa"] and not row["Referencia"]:
                siguiente_ref += 1
            else:
                # la campaña es referencia
                if siguiente_ref > 0:
                    return True
                else:
                    return False


# Función para asignar colores a umbrales según reglas
def asignar_colores(umbrales_tubo, colores_disponibles=None):
    """
    Asigna colores a umbrales según reglas específicas.

    Args:
        umbrales_tubo (list): Lista de umbrales a los que asignar colores
        colores_disponibles (list, optional): Lista de colores disponibles. Si es None, se usará colores_basicos.

    Returns:
        dict: Diccionario con los umbrales como claves y los colores asignados como valores
    """
    # Verificación de argumentos
    if umbrales_tubo is None:
        print("Lista de umbrales vacía, no se pueden asignar colores")
        return {}

    if not isinstance(umbrales_tubo, list):
        print(f"Tipo inesperado para umbrales_tubo: {type(umbrales_tubo)}. Se esperaba una lista.")
        return {}

    if not umbrales_tubo:
        print("Lista de umbrales vacía")
        return {}

    if colores_disponibles is None:
        colores_disponibles = colores_basicos

    # Asegurar que colores_disponibles sea una lista
    if not isinstance(colores_disponibles, list):
       print(f"Tipo inesperado para colores_disponibles: {type(colores_disponibles)}. Usando lista predeterminada.")
       colores_disponibles = colores_basicos

    # Dividir umbrales en grupos
    grupo_a = [umbral for umbral in umbrales_tubo if umbral.endswith("_a")]
    grupo_b = [umbral for umbral in umbrales_tubo if umbral.endswith("_b")]

    def asignar_colores_grupo(grupo):
        colores_asignados = {}
        colores_temp = colores_disponibles.copy()

        try:
            random.shuffle(colores_temp)
        except Exception as e:
            print(f"Error al mezclar colores: {e}")
            # En caso de error, asegurar que colores_temp tenga algo válido
            colores_temp = colores_basicos.copy()

        # Asignación de colores fijos para los primeros tres elementos de cada grupo
        if grupo:
            colores_asignados[grupo[0]] = 'verde'
        if len(grupo) > 1:
            colores_asignados[grupo[1]] = 'naranja'
        if len(grupo) > 2:
            colores_asignados[grupo[2]] = 'rojo'

        # Asignación de colores aleatorios para el resto, sin repetirse dentro del grupo
        for i in range(3, len(grupo)):
            if colores_temp:
                colores_asignados[grupo[i]] = colores_temp.pop()
            else:
                # Si nos quedamos sin colores, usar un color predeterminado
                colores_asignados[grupo[i]] = 'gray'
                print(f"Se agotaron los colores disponibles. Usando color predeterminado para {grupo[i]}")

        return colores_asignados

    # Combinar resultados de ambos grupos
    try:
        colores_umbrales = {**asignar_colores_grupo(grupo_a), **asignar_colores_grupo(grupo_b)}
        print(f"Colores asignados correctamente a {len(colores_umbrales)} umbrales")
        print ("salida de la función asignar_colores", colores_umbrales)
        return colores_umbrales
    except Exception as e:
        logger.error(f"Error al asignar colores: {e}")
        return {}
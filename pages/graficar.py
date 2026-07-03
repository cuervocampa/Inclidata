# pages/graficar.py
import dash
import pandas as pd
from dash import html, dcc, callback_context, ctx
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL, MATCH
import dash_mantine_components as dmc
import base64, json, io
from icecream import ic
from datetime import datetime, timedelta
import plotly.graph_objs as go
import re
import math
import logging
from dash_iconify import DashIconify
import os
import copy

import importlib
import importlib.util
import sys
from pathlib import Path

# Importar funciones del archivo externo
from utils.diccionarios import colores_basicos, colores_ingles
from utils.funciones_comunes import get_color_for_index, asignar_colores
from utils.funciones_graficar import (obtener_fecha_desde_slider, obtener_color_para_fecha, extraer_datos_fecha, add_traza, interpolar_def_tubo,
                                      load_module_dynamically, cargar_valores_actuales, obtener_parametros_por_defecto,
                                      generar_seccion_grafico, generar_campos_parametros,
                                      spanish_to_plotly_dash, hex_to_spanish_color)
#from utils.grafico_incli_0 import grafico_incli_0

# Definición de constantes y variables
# Lista de umbrales
umbrales = ["Verde", "Ámbar", "Rojo"]
# Diccionario de umbrales predefinidos (fuera del layout)
datos_tubo = {
    'umbrales': {
        'deformadas': ['umbral1_a', 'umbral2_a', 'umbral3_a', 'umbral4_a', 'umbral1_b', 'umbral2_b', 'umbral3_b', 'umbral4_b']
    }
}



MESES_ES = {1:"ene",2:"feb",3:"mar",4:"abr",5:"may",6:"jun",
            7:"jul",8:"ago",9:"sep",10:"oct",11:"nov",12:"dic"}

logger = logging.getLogger(__name__)


def _construir_marcas_slider(fechas_str):
    """Escala en minutos desde primera campaña. Raises ValueError si dos campañas colisionan."""
    if not fechas_str:
        return {}, {}

    pares = sorted([(datetime.fromisoformat(s), s) for s in fechas_str], key=lambda x: x[0])
    n = len(pares)
    fecha_inicial = pares[0][0]

    claves = [int((dt - fecha_inicial).total_seconds() // 60) for dt, _ in pares]

    seen = {}
    for i, c in enumerate(claves):
        if c in seen:
            raise ValueError(
                f"Colisión en clave de minutos {c}: {pares[seen[c]][1]} y {pares[i][1]}"
            )
        seen[c] = i

    mapa_min_a_iso = {}
    marks = {}
    for clave, (_, s) in zip(claves, pares):
        mapa_min_a_iso[clave] = s
        marks[clave] = {"label": ""}

    return marks, mapa_min_a_iso


def _lookup_fecha_slider(slider_value, fechas_seleccionadas):
    """Devuelve el ISO original de la campaña en slider_value. Fallback defensivo a clave más cercana."""
    if slider_value is None or not fechas_seleccionadas:
        return None
    try:
        _, mapa = _construir_marcas_slider(list(fechas_seleccionadas))
        if slider_value in mapa:
            return mapa[slider_value]
        claves = sorted(mapa.keys())
        if not claves:
            return None
        clave_cercana = min(claves, key=lambda c: abs(c - slider_value))
        logger.debug("slider_value %s no en mapa; fallback a clave %s", slider_value, clave_cercana)
        return mapa[clave_cercana]
    except ValueError as e:
        logger.error("Colisión en slider de fechas: %s", e)
        return list(fechas_seleccionadas)[-1]
    except Exception as e:
        logger.error("Error en lookup de fecha slider: %s", e)
        return list(fechas_seleccionadas)[-1]


def _construir_eje_temporal(fechas_str):
    """Genera html.Span para el eje temporal bajo el slider, uno por inicio de mes natural."""
    if not fechas_str:
        return []

    pares = sorted([(datetime.fromisoformat(s), s) for s in fechas_str], key=lambda x: x[0])
    dt_inicio = pares[0][0]
    dt_fin = pares[-1][0]
    minutos_totales = int((dt_fin - dt_inicio).total_seconds() // 60)
    if minutos_totales <= 0:
        return []

    # Inicios de mes naturales dentro del rango [dt_inicio, dt_fin]
    candidatos = []
    year, month = dt_inicio.year, dt_inicio.month
    while True:
        mes_dt = datetime(year, month, 1)
        if mes_dt > dt_fin:
            break
        if mes_dt >= dt_inicio:
            candidatos.append(mes_dt)
        month += 1
        if month > 12:
            month = 1
            year += 1

    if len(candidatos) < 2:
        candidatos = [dt_inicio, dt_fin]

    num_meses = len(candidatos)
    paso = max(1, math.ceil(0.08 * num_meses))
    incluir_anio = paso > 1

    spans = []
    ultima_pct = None
    for i, mes_dt in enumerate(candidatos):
        if i % paso != 0:
            continue

        minutos_cand = int((mes_dt - dt_inicio).total_seconds() // 60)
        pct = (minutos_cand / minutos_totales) * 100

        if ultima_pct is not None and (pct - ultima_pct) < 8.0:
            continue

        texto = (f"{MESES_ES[mes_dt.month]} {mes_dt.year}" if incluir_anio
                 else f"{MESES_ES[mes_dt.month]} {str(mes_dt.year)[2:]}")

        spans.append(html.Span(
            texto,
            className='eje-fecha-label',
            style={"left": f"{pct:.2f}%"}
        ))
        ultima_pct = pct

    return spans


from pages.graficar_layout import layout

# Registra los callbacks en lugar de definir un nuevo Dash app
def register_callbacks(app):
    """
    Controla la apertura y el cierre del drawer del patrón de configuración.
    :param app:
    - `open_clicks`, `close_clicks`: número de clics en los botones de abrir/cerrar.
    - `is_open`: estado actual del drawer (abierto/cerrado).
    """
    @app.callback(
        Output("drawer-patron", "opened"),
        [Input("open-patron-drawer", "n_clicks"), Input("close-patron-drawer", "n_clicks")],
        [State("drawer-patron", "opened")]
    )
    def toggle_patron_drawer(open_clicks, close_clicks, is_open):
        if open_clicks is None:
            open_clicks = 0
        if close_clicks is None:
            close_clicks = 0

        return open_clicks > close_clicks
    """
    Controla la apertura y cierre del drawer de configuración general.
    - **Inputs**:
    - `open_clicks`, `close_clicks`: número de clics en los botones de abrir/cerrar.
    """
    @app.callback(
        Output("drawer-config", "opened"),
        [Input("open-config-drawer", "n_clicks"), Input("close-config-drawer", "n_clicks")],
        [State("drawer-config", "opened")]
    )
    def toggle_config_drawer(open_clicks, close_clicks, is_open):
        if open_clicks is None:
            open_clicks = 0
        if close_clicks is None:
            close_clicks = 0

        return open_clicks > close_clicks

    @app.callback(
        [Output("valor_positivo_desplazamiento", "disabled"),
         Output("valor_negativo_desplazamiento", "disabled")],
        [Input("escala_graficos_desplazamiento", "value")]
    )
    def update_desplazamiento_inputs(escalado):
        if escalado == "manual":
            return False, False  # Habilitar los inputs
        return True, True  # Deshabilitar los inputs

    @app.callback(
        [Output("valor_positivo_incremento", "disabled"),
         Output("valor_negativo_incremento", "disabled")],
        [Input("escala_graficos_incremento", "value")]
    )
    def update_incrementos_inputs(escalado):
        if escalado == "manual":
            return False, False
        return True, True

    @app.callback(
        [Output("valor_positivo_temporal", "disabled"),
         Output("valor_negativo_temporal", "disabled")],
        [Input("escala_grafico_temporal", "value")]
    )
    def update_temporal_inputs(escalado):
        if escalado == "manual":
            return False, False
        return True, True

    # Callback para actualizar la altura de los contenedores de gráficos según el slider
    @app.callback(
        [Output("grafico_incli_1_a", "style"),
         Output("grafico_incli_1_b", "style"),
         Output("grafico_incli_2_a", "style"),
         Output("grafico_incli_2_b", "style"),
         Output("grafico_incli_chk_a", "style"),
         Output("grafico_incli_chk_b", "style"),
         Output("grafico_incli_3_a", "style"),
         Output("grafico_incli_3_b", "style"),
         Output("grafico_incli_3_total", "style")],
        [Input("alto_graficos_slider", "value")]
    )
    def update_graph_container_height(alto_graficos):
        """
        Actualiza la altura del contenedor de los gráficos según el valor del slider.
        El gráfico ocupará el 100% de este contenedor.
        """
        style = {'height': f'{alto_graficos}px'}
        return [style] * 9

    """
    Carga los datos del archivo JSON subido y actualiza la información de la tarjeta de hover.
    - **Inputs**:
    - `contents`: contenido del archivo.
    - `filename`: nombre del archivo.
    """
    @app.callback(
        [Output("info-hovercard", "children"),
         Output("graficar-tubo", "data"),
         Output("sensor-nom-label", "children")],
        [Input("graficar-uploader", "contents")],
        [State("graficar-uploader", "filename")]
    )
    def update_hovercard_and_store(contents, filename):
        if contents and filename:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            try:
                data = json.loads(decoded)
                nom_sensor = data.get("info", {}).get("nom_sensor", filename)
                sensor_id = data.get("info", {}).get("nom_sensor") or Path(filename).stem

                # Crear el nuevo diccionario
                nuevo_diccionario = {
                    "info": data["info"],
                    "umbrales": data.get("umbrales", {})
                }

                # Recorrer las claves del diccionario original y guardo 'calc' + metadatos de las campañas 'Active'
                for index, (clave, valor) in enumerate(data.items()):
                    if clave != "info" and clave != "umbrales" and "calc" in valor and valor.get("campaign_info", {}).get("active") == True:
                        nuevo_diccionario[clave] = {
                            "campaign_info": valor.get("campaign_info", {}),
                            "info_readout": valor.get("info_readout", {}),
                            "calc": [
                                {
                                    "index": item["index"],
                                    "cota_abs": item["cota_abs"],
                                    "depth": item["depth"],
                                    "incr_dev_a": item.get("incr_dev_a"),
                                    "incr_dev_b": item.get("incr_dev_b"),
                                    "checksum_a": item.get("checksum_a"),
                                    "checksum_b": item.get("checksum_b"),
                                    "incr_checksum_a": item.get("incr_checksum_a"),
                                    "incr_checksum_b": item.get("incr_checksum_b"),
                                    "incr_dev_abs_a": item.get("incr_dev_abs_a"),
                                    "incr_dev_abs_b": item.get("incr_dev_abs_b"),
                                    "desp_a": item.get("desp_a"),
                                    "desp_b": item.get("desp_b")
                                }
                                for item in valor["calc"] if isinstance(item, dict) and "index" in item
                            ],
                            "raw": valor.get("raw", []),
                            "spike": valor.get("spike", []),
                            "bias": valor.get("bias", []),
                        }

                nuevo_diccionario["info"]["_sensor_id"] = sensor_id

                # Persistir JSON completo en disco para el motor HTML (lee json_inclis/{sensor_id}.json)
                try:
                    json_inclis_dir = Path("json_inclis")
                    json_inclis_dir.mkdir(exist_ok=True)
                    (json_inclis_dir / f"{sensor_id}.json").write_text(
                        decoded.decode("utf-8"), encoding="utf-8"
                    )
                    try:
                        from biblioteca_tablas.funciones import columna_incli_json
                        columna_incli_json._json_cache.clear()
                    except Exception:
                        logging.getLogger(__name__).warning(
                            "No se pudo limpiar _json_cache de columna_incli_json"
                        )
                except Exception as write_err:
                    logging.getLogger(__name__).error(
                        "No se pudo escribir json_inclis/%s.json: %s", sensor_id, write_err
                    )

                return f"\t{filename}", nuevo_diccionario, nom_sensor
            except Exception as e:
                ic(e)
                return f"\t{filename}", None, filename
        return "", None, "—"
    """
    - Actualiza las fechas por defecto en el selector de fechas según los datos del archivo subido.
    - **Inputs**:
    - `data`: datos cargados del archivo JSON.
    """
    @app.callback(
        [Output("date_range_picker", "start_date"),
         Output("date_range_picker", "end_date")],
        Input("graficar-tubo", "data")
    )
    def pordefecto_data_picker(data):
        if not data:
            return None, None

        try:
            # Ordenar las fechas correctamente de más antigua a más reciente
            fechas = sorted([clave for clave in data.keys() if clave != "info" and clave != "umbrales"],
                            key=lambda x: datetime.fromisoformat(x))
            fechas = fechas[::-1]  # Cambiar para obtener de más reciente a más antigua

            # Obtener la primera fecha para el rango inicial
            start_date = fechas[-1] if fechas else None
            end_date = fechas[0] if fechas else None

            return start_date, end_date

        except ValueError as e:
            ic(e)  # Añadido para mostrar el error en caso de fallo
            return None, None

    # Gestión de los colores de los umbrales
    # Callback para abrir/cerrar el drawer
    @app.callback(
        Output("drawer-configuracion", "opened"),
        Input("open-umbrales-drawer", "n_clicks"),
        State("drawer-configuracion", "opened")
    )
    def toggle_drawer(n, is_open):
        if n and n > 0:
            return not is_open
        return is_open

    # Callback para inicializar la leyenda de umbrales cuando se carga la app
    @app.callback(
        Output("leyenda_umbrales", "data"),
        Input("graficar-tubo", "data"),
    )
    def inicializar_leyenda(tubo):
        """
        Inicializa la leyenda de umbrales basada en los datos del tubo.
        MODIFICADO: Ahora usa los colores y tipos de línea del JSON por defecto.

        Args:
            tubo (dict): Datos del tubo que contienen los umbrales

        Returns:
            dict: Leyenda con colores y tipos de línea
        """
        # Verificar si tubo es None o no es un diccionario
        if tubo is None:
            pass  # print("ADVERTENCIA: Los datos del tubo son None (inicializar_leyenda)")
            return {}

        if not isinstance(tubo, dict):
            pass  # print(f"ADVERTENCIA: Tipo inesperado para tubo: {type(tubo)}. Se esperaba un diccionario.")
            return {}

        # Obtener umbrales de manera segura
        umbrales = tubo.get('umbrales', {})

        if not isinstance(umbrales, dict):
            pass  # print(f"ADVERTENCIA: Tipo inesperado para umbrales: {type(umbrales)}. Se esperaba un diccionario.")
            return {}

        umbrales_deformadas = umbrales.get('deformadas', {})

        if not isinstance(umbrales_deformadas, dict):
            print(
                f"ADVERTENCIA: Tipo inesperado para deformadas: {type(umbrales_deformadas)}. Se esperaba un diccionario.")
            return {}

        if not umbrales_deformadas:
            pass  # print("ADVERTENCIA: No hay umbrales para asignar colores")
            return {}

        # NUEVA LÓGICA: Extraer colores y tipos de línea del JSON
        try:
            nueva_leyenda = {}

            for nombre_deformada, propiedades in umbrales_deformadas.items():
                if isinstance(propiedades, dict):
                    # Extraer color del JSON (hex) y convertir a nombre de color español si es necesario
                    color_hex = propiedades.get('color', '#3B82F6')  # Azul por defecto
                    tipo_linea = propiedades.get('tipo_linea', 'dashed')  # Discontinua por defecto

                    # Convertir color hex a nombre español para compatibilidad con el sistema existente
                    color_espanol = hex_to_spanish_color(color_hex)

                    nueva_leyenda[nombre_deformada] = {
                        'color': color_espanol,
                        'color_hex': color_hex,  # Mantener el hex original
                        'tipo_linea': tipo_linea
                    }
                else:
                    # Fallback para formato antiguo
                    pass  # print(f"ADVERTENCIA: Formato inesperado para deformada {nombre_deformada}")
                    nueva_leyenda[nombre_deformada] = {
                        'color': 'azul',
                        'color_hex': '#3B82F6',
                        'tipo_linea': 'dashed'
                    }

            print(f"Nueva leyenda creada con colores del JSON: {nueva_leyenda}")
            return nueva_leyenda

        except Exception as e:
            print(f"ERROR: No se pudo generar la leyenda desde JSON: {str(e)}")
            # Fallback al sistema anterior
            umbrales_tubo = list(umbrales_deformadas.keys())
            try:
                nueva_leyenda_fallback = asignar_colores(umbrales_tubo, colores_basicos)
                print(f"Usando leyenda fallback: {nueva_leyenda_fallback}")
                return nueva_leyenda_fallback
            except Exception as e2:
                print(f"ERROR: Tampoco se pudo generar leyenda fallback: {str(e2)}")
                return {}

    # Callback para actualizar dinámicamente el contenido del drawer
    @app.callback(
        Output("contenido-drawer", "children"),
        [Input("graficar-tubo", "data"),
         Input("leyenda_umbrales", "data")]
    )
    def actualizar_drawer(tubo, leyenda_actual):
        """
        MODIFICADO: Ahora incluye selectores para tipos de línea además de colores.
        """
        if tubo is None:
            pass  # print("ADVERTENCIA: Los datos del tubo son None (actualizar_drawer)")
            return []

        umbrales_deformadas = tubo.get('umbrales', {}).get('deformadas', {})
        umbrales_tubo = list(umbrales_deformadas.keys())

        if not umbrales_tubo:
            return []

        # Añadir 'verde', 'naranja', 'rojo' a las opciones si no están ya
        opciones_colores = colores_basicos.copy()
        for color in ['verde', 'naranja', 'rojo']:
            if color not in opciones_colores:
                opciones_colores.append(color)

        # Opciones para tipos de línea
        opciones_tipo_linea = [
            {'label': 'Sólida', 'value': 'solid'},
            {'label': 'Discontinua', 'value': 'dashed'},
            {'label': 'Punteada', 'value': 'dotted'},
            {'label': 'Punto-raya', 'value': 'dashdot'},
            {'label': 'Raya larga', 'value': 'longdash'},
            {'label': 'Raya larga-punto', 'value': 'longdashdot'}
        ]

        filas = []
        for umbral in umbrales_tubo:
            # Obtener valores actuales de la leyenda
            if isinstance(leyenda_actual.get(umbral), dict):
                color_actual = leyenda_actual[umbral].get('color', 'gray')
                tipo_linea_actual = leyenda_actual[umbral].get('tipo_linea', 'dashed')
            else:
                # Compatibilidad con formato anterior
                color_actual = leyenda_actual.get(umbral, 'gray')
                tipo_linea_actual = 'dashed'

            filas.append(
                dbc.Row([
                    # Nombre del umbral
                    dbc.Col(html.Div(umbral, style={'font-weight': 'bold'}), width=3),
                    # Selector de color
                    dbc.Col(dcc.Dropdown(
                        id={'type': 'color-dropdown', 'index': umbral},
                        options=[{'label': c, 'value': c} for c in opciones_colores],
                        value=color_actual,
                        clearable=False,
                        placeholder="Seleccionar color"
                    ), width=4),
                    # Selector de tipo de línea
                    dbc.Col(dcc.Dropdown(
                        id={'type': 'linetype-dropdown', 'index': umbral},
                        options=opciones_tipo_linea,
                        value=tipo_linea_actual,
                        clearable=False,
                        placeholder="Tipo de línea"
                    ), width=5)
                ], className="mb-2")
            )

        # Añadir encabezados
        filas.insert(0,
                     dbc.Row([
                         dbc.Col(html.H5("Umbral"), width=3),
                         dbc.Col(html.H5("Color"), width=4),
                         dbc.Col(html.H5("Tipo de línea"), width=5)
                     ], className="mb-3", style={'border-bottom': '2px solid #dee2e6', 'padding-bottom': '10px'})
                     )

        return filas


    """
    - **Propósito**: Actualiza el MultiSelect de fechas con las fechas seleccionadas y el filtro inteligente aplicado.
    - **Inputs**:
    - `data`: datos cargados.
    - `total_camp`, `ultimas_camp`, `cadencia_dias`: configuraciones de la campaña.
    - `start_date`, `end_date`: rango de fechas.
    - 'color_scheme': colores de la leyenda de fechas y gráficos
    """
    @app.callback(
        [Output("fechas_multiselect", "data"),
         Output("fechas_multiselect", "value")],
        [Input("graficar-tubo", "data"),
         Input("total_camp", "value"),
         Input("ultimas_camp", "value"),
         Input("cadencia_dias", "value"),
         Input("date_range_picker", "start_date"),
         Input("date_range_picker", "end_date"),
         Input("color_scheme_selector", "value")]
    )
    def update_fechas_multiselect(data, total_camp, ultimas_camp, cadencia_dias, start_date, end_date, color_scheme):
        if not data:
            return [], []

        try:
            # Ordenar las fechas correctamente de más antigua a más reciente
            fechas = sorted([clave for clave in data.keys() if clave != "info" and clave != "umbrales"],
                            key=lambda x: datetime.fromisoformat(x))
            fechas = fechas[::-1]  # Cambiar para obtener de más reciente a más antigua

            # Filtrar fechas dentro del rango seleccionado
            fechas = [fecha for fecha in fechas if start_date <= fecha <= end_date]

            # creo el diccionario que carga el multiselect
            total_colors = len(fechas)
            options = []  # Inicializar como lista
            for fecha in fechas:
                # Buscar el color en función del color_scheme y el orden
                index = fechas.index(fecha)
                color_hex = get_color_for_index(index, color_scheme, total_colors)

                # Convertir el color hexadecimal a un diccionario de estilo válido
                style = {"color": color_hex}

                options.append({
                    "value": fecha,
                    "label": fecha,
                    "style": style
                })


            # Seleccionar automáticamente las fechas según los parámetros de configuración
            total_fechas = len(fechas)
            seleccionadas = []

            # Seleccionar las últimas 'ultimas_camp' fechas
            if ultimas_camp > 0:
                seleccionadas.extend(fechas[:ultimas_camp])

            # Seleccionar más fechas según la cadencia de 'cadencia_dias'

            if cadencia_dias > 0 and len(seleccionadas) < total_camp and len(seleccionadas) > 0:
                ultima_fecha_seleccionada = datetime.fromisoformat(seleccionadas[-1])  # Última fecha seleccionada inicialmente
                for fecha_str in fechas[ultimas_camp:]:
                    fecha_actual = datetime.fromisoformat(fecha_str)
                    diferencia_dias = (ultima_fecha_seleccionada - fecha_actual).days

                    # Verificar si la fecha actual cumple con la cadencia de días
                    if diferencia_dias >= cadencia_dias:
                        seleccionadas.append(fecha_str)
                        ultima_fecha_seleccionada = fecha_actual

                    # Parar si ya se han seleccionado las fechas necesarias
                    if len(seleccionadas) >= total_camp:
                        break

            # Asegurarse de que no se seleccionen más fechas de las necesarias
            seleccionadas = seleccionadas[:total_camp]


            return options, seleccionadas
        except ValueError as e:
            ic(e)  # Añadido para mostrar el error en caso de fallo
            return [], []
    """
    - **Propósito**: Actualiza las opciones de profundidades en el MultiSelect según los datos cargados.
    - **Inputs**:
    - `data`: datos cargados.
    """
    @app.callback(
        [Output("profundidades_multiselect", "data"),
         Output("profundidades_multiselect", "value")],
        [Input("graficar-tubo", "data"),
         Input("unidades_eje","value")]
    )
    def update_profundidades_multiselect(data, eje):
        if not data:
            return [], []

        try:
            # adaptado a escoger entre "cota_abs", "depth" o "index"
            # Buscar todas las claves que sean fecha y extraer "cota_abs", "depth" o "index" de "calc"
            serie = set()
            for clave, valor in data.items():
                if clave != "info" and clave != "umbrales" and "calc" in valor:
                    serie.update(item[eje] for item in valor["calc"] if eje in item)

            # Convertir a lista, eliminar duplicados y ordenar
            serie = sorted(serie)
            # Crear las opciones para el MultiSelect
            options = [{"value": str(item), "label": str(item)} for item in serie]
            return options, [str(serie[int(len(serie) * (1 / 3))])]

        except Exception as e:
            ic(e)  # Añadido para mostrar el error en caso de fallo
            return [], []

    # Agregar callbacks para los gráficos
    # Grupo de gráficos 1: Representación de movimientos vs profundidad, con diferentes opciones
    @app.callback(
        [Output("grafico_incli_1_a", "figure"),
         Output("grafico_incli_1_b", "figure"),
         Output("grafico_incli_2_a", "figure"),
         Output("grafico_incli_2_b", "figure"),
         Output("grafico_incli_chk_a", "figure"),
         Output("grafico_incli_chk_b", "figure"),
         Output("grafico_incli_3_a", "figure"),
         Output("grafico_incli_3_b", "figure"),
         Output("grafico_incli_3_total", "figure")],
        [Input("fechas_multiselect", "value"),
         #Input("fechas_multiselect", "data"),
         Input("slider_fechas", "value"),  # CORREGIDO: Usar slider directamente en vez del tooltip para evitar bucle
         Input("graficar-tubo", "data"),
         Input("alto_graficos_slider", "value"),
         Input("color_scheme_selector", "value"),
         Input("escala_graficos_desplazamiento", "value"),
         Input("escala_graficos_incremento", "value"),
         Input("valor_positivo_desplazamiento", "value"),
         Input("valor_negativo_desplazamiento", "value"),
         Input("valor_positivo_incremento", "value"),
         Input("valor_negativo_incremento", "value"),
         Input("leyenda_umbrales", "data"),
         Input("unidades_eje","value"),
         Input("orden", "value")]
    )
    #def actualizar_graficos(fechas_seleccionadas, fechas_colores, slider_value, data, alto_graficos, color_scheme,
    #                        escala_desplazamiento, escala_incremento,
    #                        valor_positivo_desplazamiento, valor_negativo_desplazamiento,
    #                        valor_positivo_incremento, valor_negativo_incremento, leyenda_umbrales,
    #                        eje, orden):

    def actualizar_graficos(fechas_seleccionadas, slider_value, data, alto_graficos, color_scheme,
                            escala_desplazamiento, escala_incremento,
                            valor_positivo_desplazamiento, valor_negativo_desplazamiento,
                            valor_positivo_incremento, valor_negativo_incremento, leyenda_umbrales,
                            eje, orden):

        if not fechas_seleccionadas or not data:
            # CRÍTICO: Las figuras vacías deben tener autosize=False para evitar crecimiento infinito
            fig_vacia = go.Figure()
            fig_vacia.update_layout(
                autosize=False,
                height=alto_graficos,
                uirevision='constant'
            )
            return [fig_vacia for _ in range(9)]

        # RECONSTRUIR fechas_colores internamente en lugar de recibirlo como parámetro
        total_colors = len(fechas_seleccionadas)
        fechas_colores = []
        for fecha in fechas_seleccionadas:
            index = fechas_seleccionadas.index(fecha)
            color_hex = get_color_for_index(index, color_scheme, total_colors)
            fechas_colores.append({
                "value": fecha,
                "label": fecha,
                "style": {"color": color_hex}
            })

        fig1_a = go.Figure()
        fig1_b = go.Figure()
        fig2_a = go.Figure()
        fig2_b = go.Figure()
        fig_chk_a = go.Figure()
        fig_chk_b = go.Figure()
        fig3_a = go.Figure()
        fig3_b = go.Figure()
        fig3_total = go.Figure()

        fecha_slider = _lookup_fecha_slider(slider_value, fechas_seleccionadas) \
            if fechas_seleccionadas and slider_value is not None else None

        # BLOQUE 1: Primero agregar todas las series no seleccionadas
        for fecha in fechas_seleccionadas:
            if fecha in data and "calc" in data[fecha] and fecha != fecha_slider:
                # Obtener color y datos
                color = obtener_color_para_fecha(fecha, fechas_colores)
                datos = extraer_datos_fecha(fecha, data, eje)
                if not datos:
                    continue

                # Normalizar eje Y a float (evitar eje categórico)
                eje_y_num = []
                for v in datos['eje_Y']:
                    try:
                        eje_y_num.append(float(v) if v is not None else None)
                    except Exception:
                        eje_y_num.append(None)

                # Parámetros para series no seleccionadas
                grosor = 2
                opacidad = 0.7

                # Añadir trazas a cada figura individualmente
                # Gráfico 1: Desplazamientos
                add_traza(fig1_a, datos['desp_a'], eje_y_num,
                             f"{fecha} - Desp A", color, grosor, opacidad, fecha)
                add_traza(fig1_b, datos['desp_b'], eje_y_num,
                             f"{fecha} - Desp B", color, grosor, opacidad, fecha)

                # Gráfico 2: Incrementales
                add_traza(fig2_a, datos['incr_dev_abs_a'], eje_y_num,
                             f"{fecha} - Incr Dev A", color, grosor, opacidad, fecha)
                add_traza(fig2_b, datos['incr_dev_abs_b'], eje_y_num,
                             f"{fecha} - Incr Dev B", color, grosor, opacidad, fecha)

                # Gráfico checksum
                add_traza(fig_chk_a, datos['checksum_a'], eje_y_num,
                             f"{fecha} - Checksum A", color, grosor, opacidad, fecha)
                add_traza(fig_chk_b, datos['checksum_b'], eje_y_num,
                             f"{fecha} - Checksum B", color, grosor, opacidad, fecha)

                # Gráfico 3: Desplazamientos Compuestos
                add_traza(fig3_a, datos['desp_a'], eje_y_num,
                             f"{fecha} - Desp A", color, grosor, opacidad, fecha)
                add_traza(fig3_b, datos['desp_b'], eje_y_num,
                             f"{fecha} - Desp B", color, grosor, opacidad, fecha)
                add_traza(fig3_total, datos['desp_total'], eje_y_num,
                             f"{fecha} - Desp Total", color, grosor, opacidad, fecha)

        # BLOQUE 2: Luego agregar la serie seleccionada para que quede encima
        if fecha_slider in fechas_seleccionadas and fecha_slider in data and "calc" in data[fecha_slider]:
            # Obtener datos para la fecha seleccionada
            datos = extraer_datos_fecha(fecha_slider, data, eje)
            if datos:
                # Normalizar eje Y a float (evitar eje categórico)
                eje_y_num = []
                for v in datos['eje_Y']:
                    try:
                        eje_y_num.append(float(v) if v is not None else None)
                    except Exception:
                        eje_y_num.append(None)
                # Parámetros para la serie seleccionada
                color = 'darkblue'
                grosor = 4
                opacidad = 1.0

                # Añadir trazas a cada figura individualmente
                # Gráfico 1: Desplazamientos
                add_traza(fig1_a, datos['desp_a'], eje_y_num,
                             f"{fecha_slider} - Desp A", color, grosor, opacidad, fecha_slider)
                add_traza(fig1_b, datos['desp_b'], eje_y_num,
                             f"{fecha_slider} - Desp B", color, grosor, opacidad, fecha_slider)

                # Gráfico 2: Incrementales
                add_traza(fig2_a, datos['incr_dev_abs_a'], eje_y_num,
                             f"{fecha_slider} - Incr Dev A", color, grosor, opacidad, fecha_slider)
                add_traza(fig2_b, datos['incr_dev_abs_b'], eje_y_num,
                             f"{fecha_slider} - Incr Dev B", color, grosor, opacidad, fecha_slider)

                # Gráfico checksum
                add_traza(fig_chk_a, datos['checksum_a'], eje_y_num,
                             f"{fecha_slider} - Checksum A", color, grosor, opacidad, fecha_slider)
                add_traza(fig_chk_b, datos['checksum_b'], eje_y_num,
                             f"{fecha_slider} - Checksum B", color, grosor, opacidad, fecha_slider)

                # Gráfico 3: Desplazamientos Compuestos
                add_traza(fig3_a, datos['desp_a'], eje_y_num,
                             f"{fecha_slider} - Desp A", color, grosor, opacidad, fecha_slider)
                add_traza(fig3_b, datos['desp_b'], eje_y_num,
                             f"{fecha_slider} - Desp B", color, grosor, opacidad, fecha_slider)
                add_traza(fig3_total, datos['desp_total'], eje_y_num,
                             f"{fecha_slider} - Desp Total", color, grosor, opacidad, fecha_slider)

        # Añade los umbrales
        if leyenda_umbrales:
            # hay umbrales a pintar
            # Extraer los datos
            valores = data['umbrales']['valores']

            # Crear un nuevo diccionario solo con las claves
            deformadas = list(data['umbrales']['deformadas'].keys())

            df = pd.DataFrame(valores)

            # Para cada deformada, añadir una traza en la figura correspondiente
            for deformada in deformadas:
                # Determinar en qué figura debe ir la deformada
                if deformada.endswith("_a"):
                    fig = fig1_a
                elif deformada.endswith("_b"):
                    fig = fig1_b
                else:
                    continue  # Si no termina en _a o _b, no se grafica

                # MODIFICADO: Obtener color y tipo de línea de la leyenda actualizada
                if isinstance(leyenda_umbrales.get(deformada), dict):
                    color_espanol = leyenda_umbrales[deformada].get('color', 'azul')
                    tipo_linea = leyenda_umbrales[deformada].get('tipo_linea', 'dashed')
                else:
                    # Compatibilidad con formato anterior
                    color_espanol = leyenda_umbrales.get(deformada, "azul")
                    tipo_linea = 'dashed'

                opacity = 1.0

                # Si el color es "Ninguno", no se grafica esta serie
                if color_espanol == "Ninguno":
                    continue

                # Convertir el color a inglés o mantenerlo si es un código hexadecimal
                color = colores_ingles.get(color_espanol, color_espanol)

                # NUEVO: Convertir tipo de línea a formato Plotly
                dash_pattern = spanish_to_plotly_dash(tipo_linea)

                if eje == "depth" or eje == "index":
                    # Hay que interpolar las deformadas al caso de index o depth
                    cota_tubo = [punto["cota_abs"] for punto in data[fecha_slider]['calc']]
                    cota_umbral = df['cota_abs'].to_list()
                    def_umbral = df[deformada].to_list()
                    eje_X = interpolar_def_tubo(cota_tubo, cota_umbral, def_umbral)
                else:
                    # caso de "cota_abs"
                    eje_X = df[deformada]

                # selecciono la lista de ordenadas en función de qué se escoja como unidades de eje
                if eje == "depth":
                    # se debe construir la profundidad
                    # busco el paso
                    paso = abs(cota_tubo[1] - cota_tubo[0])
                    eje_Y = []

                    for i in range(len(cota_tubo)):
                        eje_Y.append(paso * i)
                elif eje == "index":
                    # se escoge la lista de índice
                    eje_Y = [punto["index"] for punto in data[fecha_slider]['calc']]
                elif eje == "cota_abs":
                    #eje_Y = df['cota_abs'].to_list()
                    eje_Y = df['cota_abs'].astype(float).to_list()
                # Fuerza numérico
                try:
                    eje_X = [float(x) if x is not None else None for x in eje_X]
                except Exception:
                    pass

                try:
                    eje_Y = [float(y) if y is not None else None for y in eje_Y]
                except Exception:
                    pass

                # MODIFICADO: Agregar la traza con tipo de línea personalizado
                fig.add_trace(go.Scatter(
                    y=eje_Y,
                    x=eje_X,
                    mode="lines",
                    name=f"{deformada}",  # Nombre del ítem de deformadas
                    line=dict(
                        color=color,
                        width=grosor,
                        dash=dash_pattern  # NUEVO: Aplicar patrón de línea
                    ),
                    legendgroup=fecha,
                    opacity=opacity
                ))

        # Configurar ejes y quitar leyendas, ajustar altura de gráficos
        for fig in [fig1_a, fig1_b, fig3_a, fig3_b, fig3_total]:
            if escala_desplazamiento == "manual":
                fig.update_xaxes(range=[valor_negativo_desplazamiento, valor_positivo_desplazamiento])

        # escala automática/manual
        for fig in [fig2_a, fig2_b]:
            if escala_incremento == "manual":
                fig.update_xaxes(range=[valor_negativo_incremento, valor_positivo_incremento])

        # La escala de checksum va automática
        for fig in [fig_chk_a, fig_chk_b]:
            fig.update_layout(
                xaxis=dict(
                    range=[-1, 1],  # Establece el rango mínimo a ±1
                    tickmode='linear',  # Modo de ticks lineal
                    dtick=0.5,  # Espacio entre ticks (0.5 para divisiones intermedias)
                    autorange=False,  # CORREGIDO: No autorange si ya hay un rango fijo (evita conflicto)
                    tick0=0,  # Empezar en 0
                    constrain='domain'  # Mantener la restricción en el dominio
                )
            )

        # Definición de gráficos y rejilla y título ejeY
        for fig in [fig1_a, fig1_b, fig2_a, fig2_b, fig_chk_a, fig_chk_b, fig3_a, fig3_b, fig3_total]:
            # Solo mostrar título si la figura es una de las de la izquierda (fig1_a, fig2_a, fig_chk_a, fig3_a)
            if fig in [fig1_a, fig2_a, fig_chk_a, fig3_a]:
                if eje == "index":
                    titulo_eje_y = "Índice"
                elif eje == "cota_abs":
                    titulo_eje_y = "Cota (m.s.n.m.)"
                elif eje == "depth":
                    titulo_eje_y = "Profundidad (m)"
            else:
                titulo_eje_y = ""
            fig.update_layout(
                uirevision=f'constant_{orden}_{eje}',  # CAMBIADO: Forzar reset UI al cambiar orden o eje
                yaxis=dict(
                    type='linear',
                    title=dict(text=titulo_eje_y, font=dict(color='#888888')),  # Título con color
                    autorange='reversed' if orden == 'descendente' else True,  # MODIFICADO: Lógica para SegmentedControl
                    fixedrange=False,  # Permitir zoom pero sin auto-redimensionado continuo
                    gridcolor='#555555', gridwidth=1, griddash='dash',  # Gris medio visible en modo oscuro
                    anchor='free',
                    #position=0,  # Posicionar el eje Y en x=0
                    constrain='domain',  # ← Fija el eje al área del subplot
                    showline=False,  # Asegurarse de que no se muestra la línea vertical del eje Y
                    tickfont=dict(color='#888888'),  # Color del texto de los ticks
                ),
                xaxis=dict(
                    gridcolor='#555555', gridwidth=1, griddash='dash',  # Gris medio visible en modo oscuro
                    showline=True,  # Mostrar la línea del borde inferior (eje X)
                    linecolor='#666666',  # Color del borde inferior
                    linewidth=1,  # Grosor del borde inferior
                    zeroline=True, zerolinecolor='#666666', zerolinewidth=1,  # muestra el eje vertical en x=0
                    tickfont=dict(color='#888888'),  # Color del texto de los ticks
                ),
                showlegend=False, height=alto_graficos, title_x=0.5,
                plot_bgcolor='rgba(0,0,0,0)',  # Fondo transparente para adaptarse al modo oscuro
                paper_bgcolor='rgba(0,0,0,0)',  # Fondo del papel transparente
                autosize=False  # CRÍTICO: Desactivar para evitar bucle de crecimiento infinito
            )

        return [fig1_a, fig1_b, fig2_a, fig2_b,fig_chk_a, fig_chk_b, fig3_a, fig3_b, fig3_total]

    @app.callback(
        Output("grafico_temporal", "figure"),
        [Input("profundidades_multiselect", "value"),
         Input("graficar-tubo", "data"),
         Input("desplazamientos_multiselect", "value"),
         Input("date_range_picker", "start_date"),
         Input("date_range_picker", "end_date"),
         Input("escala_grafico_temporal", "value"),
         Input("valor_positivo_temporal", "value"),
         Input("valor_negativo_temporal", "value"),
         Input("unidades_eje", "value"),
         ]
    )
    def actualizar_grafico_temporal(profundidades_seleccionadas, data, desplazamientos_seleccionados, start_date, end_date,
                                    escala_temporal, valor_positivo_temporal, valor_negativo_temporal, eje):
        if not profundidades_seleccionadas or not data or not desplazamientos_seleccionados:
            fig_vacia = go.Figure()
            fig_vacia.update_layout(autosize=False, uirevision='constant')
            return fig_vacia

        fig_temporal = go.Figure()

        # Obtener y ordenar las fechas de más antigua a más reciente
        fechas_temp = sorted([fecha for fecha in data.keys() if fecha != "info" and fecha != "umbrales"], key=lambda x: datetime.fromisoformat(x))


        # Filtrar fechas dentro del rango seleccionado
        fechas_temp = [fecha for fecha in fechas_temp if start_date <= fecha <= end_date]

        for profundidad in profundidades_seleccionadas:
            for desplazamiento in desplazamientos_seleccionados:
                valores = []
                for fecha in fechas_temp:
                    if "calc" in data[fecha]:
                        puntos = data[fecha]["calc"]
                        for punto in puntos:
                            #if punto.get("cota_abs") == profundidad and desplazamiento in punto:
                            if str(punto.get(eje)) == str(profundidad) and desplazamiento in punto:
                                valores.append(punto[desplazamiento])
                                break

                        else:
                            valores.append(None)  # Añadir None si no se encuentra la cota

                # Añadir la serie temporal al gráfico
                fig_temporal.add_trace(go.Scatter(x=fechas_temp, y=valores, mode="markers+lines", name=f"{desplazamiento} ({profundidad})"))

        # escala automática/manual
        if escala_temporal == "manual":
            fig_temporal.update_yaxes(range=[valor_negativo_temporal, valor_positivo_temporal])

        fig_temporal.update_layout(
            title=dict(
                text=f"<b>Series Temporales ({eje})</b>",  # negrita en el propio texto
                font=dict(
                    family="Arial",  # Fuente (puedes cambiarla)
                    size=18,  # Tamaño más pequeño del texto
                    color="#c1c2c5",  # Color del texto (gris claro para modo oscuro)
                    #weight="bold"  # Negrita
                ),
                x=0,  # Alineación a la izquierda
                xanchor="left",  # Mantener la referencia de alineación
                yanchor="top"  # Alineado en la parte superior
            ),
            yaxis=dict(
                gridcolor='#555555', gridwidth=1, griddash='dash',
                showline=True,
                linecolor='#666666',
                linewidth=2,
                zeroline=True,
                zerolinecolor='#666666',
                zerolinewidth=1,
                tickfont=dict(color='#888888'),  # Color del texto de los ticks
            ),
            xaxis=dict(
                gridcolor='#555555', gridwidth=1, griddash='dash',
                showline=True,
                linecolor='#666666',
                linewidth=2,
                tickfont=dict(color='#888888'),  # Color del texto de los ticks
            ),
            legend=dict(
                 bgcolor='rgba(0,0,0,0)',
                 font=dict(color='#c1c2c5')
            ),
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            autosize=False,  # CRÍTICO: Desactiva autosize para evitar bucle
            uirevision='constant'  # Mantener estado UI
        )

        return fig_temporal

    # Callback para actualizar el gráfico polar (desplazamiento resultante A/B)
    # CORREGIDO: Grafica todas las profundidades de la fecha seleccionada en el slider
    @app.callback(
        Output("grafico_polar", "figure"),
        [Input("graficar-tubo", "data"),
         Input("slider_fechas", "value"),
         Input("fechas_multiselect", "value"),
         Input("unidades_eje", "value")]
    )
    def actualizar_grafico_polar(data, slider_value, fechas_seleccionadas, eje):
        if not data or not fechas_seleccionadas or slider_value is None:
            fig_vacia = go.Figure()
            fig_vacia.update_layout(autosize=False, uirevision='constant')
            return fig_vacia

        fecha_slider = _lookup_fecha_slider(slider_value, fechas_seleccionadas)

        if not fecha_slider or fecha_slider not in data or "calc" not in data[fecha_slider]:
            fig_vacia = go.Figure()
            fig_vacia.update_layout(autosize=False, uirevision='constant')
            return fig_vacia

        fig_polar = go.Figure()

        # Recorrer TODOS los puntos (profundidades) de la fecha seleccionada
        calc_data = data[fecha_slider]["calc"]
        r_values = []
        theta_values = []
        hover_texts = []
        profundidades_labels = []

        for punto in calc_data:
            desp_a = punto.get("desp_a", 0) or 0
            desp_b = punto.get("desp_b", 0) or 0
            r = math.sqrt(desp_a ** 2 + desp_b ** 2)
            theta = math.degrees(math.atan2(desp_b, desp_a))
            prof_label = punto.get(eje, punto.get("cota_abs", "?"))

            r_values.append(r)
            theta_values.append(theta)
            profundidades_labels.append(str(prof_label))
            hover_texts.append(
                f"{eje}: {prof_label}<br>"
                f"A: {desp_a:.2f}  B: {desp_b:.2f}<br>"
                f"R: {r:.2f}  θ: {theta:.1f}°"
            )

        if r_values:
            fig_polar.add_trace(go.Scatterpolar(
                r=r_values,
                theta=theta_values,
                mode="markers+lines+text",
                name=f"{fecha_slider[:10]}",
                text=profundidades_labels,
                textposition="top right",
                textfont=dict(size=8, color='#aaaaaa'),
                hovertext=hover_texts,
                hoverinfo="text+name",
                marker=dict(size=6),
                line=dict(width=1.5),
            ))

        fig_polar.update_layout(
            title=dict(
                text=f"<b>Polar (A vs B) — {fecha_slider[:10]}</b>",
                font=dict(family="Arial", size=16, color="#c1c2c5"),
                x=0, xanchor="left", yanchor="top"
            ),
            polar=dict(
                bgcolor='rgba(0,0,0,0)',
                domain=dict(x=[0, 1], y=[0, 0.92]),
                angularaxis=dict(
                    direction="counterclockwise",
                    rotation=0,
                    gridcolor='#555555',
                    linecolor='#666666',
                    tickfont=dict(color='#888888', size=10),
                    tickvals=[0, 90, 180, 270],
                    ticktext=["A+", "B+", "A−", "B−"],
                ),
                radialaxis=dict(
                    gridcolor='#555555',
                    linecolor='#666666',
                    tickfont=dict(color='#888888', size=9),
                    angle=45,
                    autorange=True,  # Asegurar que la escala radial incluya todos los puntos
                ),
            ),
            margin=dict(l=30, r=30, t=50, b=30),
            legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color='#c1c2c5', size=10)),
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            autosize=False,
            uirevision='constant'
        )

        return fig_polar

    # Callback TEMPORAL de depuración: exportar cálculos del gráfico polar a Markdown
    @app.callback(
        Output("descargar-debug-polar", "data"),
        Input("btn-debug-polar", "n_clicks"),
        [State("graficar-tubo", "data"),
         State("slider_fechas", "value"),
         State("fechas_multiselect", "value"),
         State("unidades_eje", "value")],
        prevent_initial_call=True
    )
    def exportar_debug_polar(n_clicks, data, slider_value, fechas_seleccionadas, eje):
        if not n_clicks or not data or not fechas_seleccionadas or slider_value is None:
            return None

        import math as _math

        fecha_slider = _lookup_fecha_slider(slider_value, fechas_seleccionadas)
        if not fecha_slider:
            fecha_slider = fechas_seleccionadas[-1]

        if not fecha_slider or fecha_slider not in data or "calc" not in data[fecha_slider]:
            return None

        calc_data = data[fecha_slider]["calc"]

        lines = []
        lines.append("# Depuración: Cálculo del Gráfico Polar\n")
        lines.append(f"**Fecha seleccionada (slider)**: `{fecha_slider}`\n")
        lines.append(f"**Eje utilizado**: `{eje}`\n")
        lines.append(f"**Nº de puntos (profundidades)**: {len(calc_data)}\n")

        lines.append("---\n")
        lines.append("## Fórmulas aplicadas\n")
        lines.append("```")
        lines.append("R = √(desp_a² + desp_b²)")
        lines.append("θ = atan2(desp_b, desp_a)  [en grados]")
        lines.append("")
        lines.append("Donde:")
        lines.append("  desp_a = Σ(incr_dev_a[j], j=i..N) + desp_a(referencia)")
        lines.append("  desp_b = Σ(incr_dev_b[j], j=i..N) + desp_b(referencia)")
        lines.append("  incr_dev_a = dev_a(campaña) − dev_a(referencia)")
        lines.append("  dev_a = (a0c − a180c) / 2")
        lines.append("```\n")
        lines.append("## Ejes del gráfico polar\n")
        lines.append("| Ángulo | Dirección |")
        lines.append("|--------|-----------|")
        lines.append("| 0°     | A+        |")
        lines.append("| 90°    | B+        |")
        lines.append("| 180°   | A−        |")
        lines.append("| 270°   | B−        |\n")

        lines.append("---\n")
        lines.append(f"## Todos los puntos de {fecha_slider[:10]}\n")
        lines.append(f"| {eje} | desp_a | desp_b | R (magnitud) | θ (grados) |")
        lines.append("|-------|--------|--------|--------------|------------|")

        for punto in calc_data:
            prof = punto.get(eje, punto.get("cota_abs", "?"))
            desp_a = punto.get("desp_a", 0) or 0
            desp_b = punto.get("desp_b", 0) or 0
            r = _math.sqrt(desp_a ** 2 + desp_b ** 2)
            theta = _math.degrees(_math.atan2(desp_b, desp_a))
            lines.append(f"| {prof} | {desp_a:.4f} | {desp_b:.4f} | {r:.4f} | {theta:.1f}° |")

        # Detalle completo del primer y último punto
        lines.append(f"\n---\n")
        lines.append(f"### Detalle del primer punto (todos los campos calc)\n")
        lines.append("| Campo | Valor |")
        lines.append("|-------|-------|")
        for k, v in calc_data[0].items():
            lines.append(f"| {k} | {v} |")

        if len(calc_data) > 1:
            lines.append(f"\n### Detalle del último punto\n")
            lines.append("| Campo | Valor |")
            lines.append("|-------|-------|")
            for k, v in calc_data[-1].items():
                lines.append(f"| {k} | {v} |")

        md_content = "\n".join(lines)
        return dict(content=md_content, filename="debug_polar.md")

    # Callback to update the slider properties based on fechas_multiselect data
    from datetime import datetime

    """ update_slider_dates(fechas):
    - **Propósito**: Actualiza las propiedades del slider según las fechas disponibles en el MultiSelect.
    - **Inputs**:
    - `fechas`: lista de fechas seleccionadas."""
    @app.callback(
        [Output('slider_fechas', 'min'),
         Output('slider_fechas', 'max'),
         Output('slider_fechas', 'marks'),
         Output('slider_fechas', 'value'),
         Output('slider_fechas_eje', 'children')],
        [Input('fechas_multiselect', 'value')]
    )
    def update_slider_dates(fechas):
        if not fechas:
            return 0, 0, {}, 0, []
        try:
            marks, mapa = _construir_marcas_slider(list(fechas))
            claves = sorted(mapa.keys())
            eje = _construir_eje_temporal(list(fechas))
            return claves[0], claves[-1], marks, claves[-1], eje
        except ValueError as e:
            logger.error("Colisión en clave de minutos al construir slider: %s", e)
            return 0, 0, {}, 0, []
        except Exception as e:
            logger.error("Error al construir slider de fechas: %s", e)
            return 0, 0, {}, 0, []

    """ update_slider_tooltip(value, fechas)**:
    - **Propósito**: Actualiza el tooltip del slider mostrando la fecha seleccionada.
    - **Inputs**:
        - `value`: valor del slider.
        - `fechas`: lista de fechas seleccionadas."""
    @app.callback(
        Output('slider_fecha_tooltip', 'children'),
        [Input('slider_fechas', 'value')],
        [State('fechas_multiselect', 'value')]
    )
    def update_slider_tooltip(value, fechas):
        if not fechas:
            return "No hay fechas disponibles"
        fecha_iso = _lookup_fecha_slider(value, fechas)
        if not fecha_iso:
            return "Error al actualizar la fecha"
        try:
            dt = datetime.fromisoformat(fecha_iso)
            return f"Fecha seleccionada: {dt.strftime('%d/%m/%Y %H:%M')}"
        except Exception:
            return f"Fecha seleccionada: {fecha_iso}"

    # IMPRIMIR INFORME
    @app.callback(
        Output("modal-configurar-informe", "opened"),
        [Input("btn-abrir-modal-informe", "n_clicks"),
         Input("btn-cancelar-informe", "n_clicks")],
        [State("modal-configurar-informe", "opened")],
        prevent_initial_call=True
    )
    def toggle_modal_informe(n_abrir, n_cancelar, is_open):
        """
        Controla la apertura y cierre del modal de configuración de informe PDF.
        """
        if not ctx.triggered:
            return is_open

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if button_id == "btn-abrir-modal-informe" and n_abrir:
            return True
        elif button_id == "btn-cancelar-informe" and n_cancelar:
            return False
        return is_open

    @app.callback(
        Output("select-plantilla-informe", "data"),
        Input("modal-configurar-informe", "opened"),
        prevent_initial_call=True
    )
    def cargar_plantillas_disponibles(is_open):
        """
        Carga las plantillas disponibles en la carpeta biblioteca_graficos cuando se abre el modal.
        """
        if not is_open:
            return []

        try:
            html_dir = Path("biblioteca_plantillas") / "html"
            if not html_dir.is_dir():
                return [{"label": "No hay plantillas disponibles", "value": ""}]

            plantillas = [
                {"label": p.name, "value": f"html/{p.name}"}
                for p in sorted(html_dir.iterdir())
                if p.is_dir()
            ]

            if not plantillas:
                return [{"label": "No hay plantillas disponibles", "value": ""}]

            return plantillas
        except Exception as e:
            print(f"ERROR al cargar plantillas: {str(e)}")
            import traceback
            traceback.print_exc()
            return [{"label": f"Error: {str(e)}", "value": ""}]

    # callback para cargar la plantilla
    # CALLBACK MODIFICADO: cargar_plantilla_seleccionada
    @app.callback(
        [Output("plantilla-json-data", "data"),
         Output("contenedor-campos-editables", "children")],
        [Input("select-plantilla-informe", "value")],
        [State("graficar-tubo", "data"),
         State("unidades_eje", "value"),
         State("orden", "value"),
         State("color_scheme_selector", "value"),
         State("escala_graficos_desplazamiento", "value"),
         State("escala_graficos_incremento", "value"),
         State("valor_positivo_desplazamiento", "value"),
         State("valor_negativo_desplazamiento", "value"),
         State("valor_positivo_incremento", "value"),
         State("valor_negativo_incremento", "value"),
         State("date_range_picker", "start_date"),
         State("date_range_picker", "end_date"),
         State("total_camp", "value"),
         State("ultimas_camp", "value"),
         State("cadencia_dias", "value"),
         State("info-hovercard", "children"),
         State("leyenda_umbrales", "data")],
        prevent_initial_call=True
    )
    def cargar_plantilla_seleccionada_mejorada(nombre_plantilla, data, eje, orden, color_scheme,
                                               escala_desplazamiento, escala_incremento,
                                               valor_positivo_desplazamiento, valor_negativo_desplazamiento,
                                               valor_positivo_incremento, valor_negativo_incremento,
                                               fecha_inicial, fecha_final, total_camp, ultimas_camp, cadencia_dias,
                                               info_hovercard, leyenda_umbrales):
        """
        Versión mejorada que genera la interfaz con acordeón.
        """
        if not nombre_plantilla:
            return None, []

        try:
            # Cargar JSON de la plantilla
            from utils.template_service import _encontrar_json_plantilla
            ruta_json = _encontrar_json_plantilla(nombre_plantilla)

            if not ruta_json or not ruta_json.is_file():
                return None, [
                    dmc.Alert(f"No se encontró el archivo JSON para la plantilla '{nombre_plantilla}'", c="red")]

            with open(ruta_json, 'r', encoding='utf-8') as file:
                data_json = json.load(file)

            # Normalizar estructura si no tiene 'paginas' (caso plantillas simples como encabezados)
            if "paginas" not in data_json and "elementos" in data_json:
                print(f"Normalizando estructura plana para plantilla: {nombre_plantilla}")
                # Convertir a estructura de paginas con una pagina ficticia "1"
                config = data_json.get("configuracion", {})
                elems = data_json.get("elementos", {})
                
                # Reconstruir data_json manteniendo la referencia
                # Es importante que 'paginas' exista para que el resto del código funcione
                data_json["paginas"] = {
                    "1": {
                        "elementos": elems,
                        "configuracion": config
                    }
                }

            # Obtener valores actuales
            current_values = cargar_valores_actuales(
                data, eje, orden, color_scheme, escala_desplazamiento, escala_incremento,
                valor_positivo_desplazamiento, valor_negativo_desplazamiento,
                valor_positivo_incremento, valor_negativo_incremento,
                fecha_inicial, fecha_final, total_camp, ultimas_camp, cadencia_dias,
                leyenda_umbrales  # ← AÑADIR ESTA LÍNEA
            )

            campos_editables = []

            # ----------------------------------------------------
            # 1. GENERAR CONTENIDO DE TEXTOS EDITABLES
            # ----------------------------------------------------
            textos_content = []
            
            # Obtener nombre del sensor desde info-hovercard
            nombre_sensor_actual = "Sin nombre"
            if info_hovercard:
                if isinstance(info_hovercard, str) and info_hovercard.startswith("\t"):
                    nombre_sensor_actual = info_hovercard.replace("\t", "").strip()
                    if nombre_sensor_actual.endswith(".json"):
                        nombre_sensor_actual = nombre_sensor_actual[:-5]
                else:
                    nombre_sensor_actual = str(info_hovercard).strip()

            # print(f"Nombre del sensor obtenido de hovercard: '{nombre_sensor_actual}'")

            textos_encontrados = 0
            grid_text_inputs = []
            
            for num_pagina, pagina in data_json.get("paginas", {}).items():
                elementos = pagina.get("elementos", {})
                for nombre_elemento, elemento in elementos.items():
                    if (elemento.get("tipo") == "texto" and
                            "contenido" in elemento and
                            elemento["contenido"].get("editable", True)):
                        textos_encontrados += 1

                        if nombre_elemento == "nombre_sensor":
                            texto_actual = nombre_sensor_actual
                        else:
                            texto_actual = elemento.get("contenido", {}).get("texto", "")

                        clean_label = nombre_elemento.replace("_", " ").title()

                        grid_text_inputs.append(
                            dmc.TextInput(
                                label=clean_label,
                                id={"type": "campo-editable", "pagina": num_pagina, "elemento": nombre_elemento},
                                value=texto_actual,
                                size="sm"
                            )
                        )

            if grid_text_inputs:
                textos_content.append(
                    dmc.SimpleGrid(
                        cols=2,
                        spacing="md",
                        verticalSpacing="sm",
                        children=grid_text_inputs,
                        style={"marginBottom": "15px"}
                    )
                )

            for num_pagina, pagina in data_json.get("paginas", {}).items():
                elementos = pagina.get("elementos", {})
                for nombre_elemento, elemento in elementos.items():
                    if (nombre_elemento == "nombre_sensor" and
                            elemento.get("tipo") == "texto" and
                            "contenido" in elemento):
                        data_json["paginas"][num_pagina]["elementos"][nombre_elemento]["contenido"]["texto"] = nombre_sensor_actual
                        break

            if textos_encontrados == 0:
                textos_content.append(
                    dmc.Alert("No se encontraron campos de texto editables en esta plantilla", c="yellow")
                )

            # ----------------------------------------------------
            # 2. GENERAR CONTENIDO DE GRÁFICOS CONFIGURABLES
            # ----------------------------------------------------
            graficos_content = []
            
            # Enumera scripts con nombre canónico "namespace/script.py" (convención Maketator).
            # La ruta se resuelve como Path("biblioteca_graficos") / nombre_canonico.
            graficos_base = Path("biblioteca_graficos")
            scripts_disponibles = []
            if graficos_base.is_dir():
                for ns_dir in sorted(graficos_base.iterdir()):
                    if not ns_dir.is_dir():
                        continue
                    for script_file in sorted(ns_dir.glob("*.py")):
                        if script_file.name.startswith("__"):
                            continue
                        canonical = f"{ns_dir.name}/{script_file.name}"
                        scripts_disponibles.append({"label": script_file.stem, "value": canonical})
            if not scripts_disponibles:
                scripts_disponibles = [{"label": "No hay scripts disponibles", "value": ""}]

            graficos_encontrados = 0
            accordion_items = []

            for num_pagina, pagina in data_json.get("paginas", {}).items():
                elementos = pagina.get("elementos", {})
                for nombre_elemento, elemento in elementos.items():
                    tipo_elem = elemento.get("tipo")
                    if tipo_elem in ["grafico", "tabla"]:
                        graficos_encontrados += 1
                        
                        icono = "mdi:chart-line" if tipo_elem == "grafico" else "mdi:table"
                        color_badge = "blue" if tipo_elem == "grafico" else "green"

                        contenido = generar_seccion_grafico(
                            num_pagina, nombre_elemento, elemento, scripts_disponibles, current_values
                        )

                        accordion_items.append(
                            dmc.AccordionItem(
                                [
                                    dmc.AccordionControl(
                                        dmc.Group([
                                            DashIconify(icon=icono, width=20),
                                            dmc.Text(f"{nombre_elemento} ({tipo_elem})", fw="bold"),
                                            dmc.Badge(f"Página {num_pagina}", variant="light", c=color_badge)
                                        ])
                                    ),
                                    dmc.AccordionPanel(contenido)
                                ],
                                value=f"{num_pagina}-{nombre_elemento}"
                            )
                        )

            if graficos_encontrados > 0:
                graficos_content.append(
                    dmc.Accordion(
                        children=accordion_items,
                        multiple=True,
                        variant="separated",
                        radius="md"
                    )
                )
            else:
                graficos_content.append(
                    dmc.Alert("No se encontraron gráficos configurables en esta plantilla", c="yellow")
                )

            # ----------------------------------------------------
            # 3. ENVOLVER EN ACORDEÓN PRINCIPAL COLAPSADO
            # ----------------------------------------------------
            main_accordion_items = [
                dmc.AccordionItem(
                    [
                        dmc.AccordionControl(
                            dmc.Group([
                                DashIconify(icon="lucide:type", width=20, color="var(--id-primary)"),
                                dmc.Text("Textos Editables", fw=600),
                            ])
                        ),
                        dmc.AccordionPanel(textos_content)
                    ],
                    value="seccion-textos"
                ),
                dmc.AccordionItem(
                    [
                        dmc.AccordionControl(
                            dmc.Group([
                                DashIconify(icon="lucide:settings-2", width=20, color="var(--id-primary)"),
                                dmc.Text("Gráficos y Tablas Configurables", fw=600),
                            ])
                        ),
                        dmc.AccordionPanel(graficos_content)
                    ],
                    value="seccion-graficos"
                )
            ]

            campos_editables.append(
                dmc.Accordion(
                    children=main_accordion_items,
                    multiple=True,
                    variant="filled", # Para diferenciarlo del anidado
                    radius="md",
                    value=None, # IMPORTANTE: value vacío para que empiecen colapsados
                    style={"marginTop": "20px", "marginBottom": "20px"}
                )
            )

            # Tooltip explicativo
            if graficos_encontrados > 0:
                campos_editables.append(
                    dmc.Alert(
                        title="Valores de la interfaz",
                        c="blue",
                        children=[
                            html.P(
                                "Los campos con fondo azul claro son valores tomados directamente de la interfaz actual."),
                            html.P(
                                "Al modificarlos, puede ingresar un valor personalizado o volver al valor '$CURRENT' para usar automáticamente los valores de la interfaz.")
                        ],
                        style={"marginTop": "20px"}
                    )
                )

            return data_json, campos_editables

        except Exception as e:
            print(f"Error al cargar la plantilla: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, [dmc.Alert(f"Error al cargar la plantilla: {str(e)}", c="red")]

    # NUEVO CALLBACK: Detectar cambios en selectores de script y regenerar parámetros
    @app.callback(
        Output({"type": "parametros-container", "pagina": MATCH, "elemento": MATCH}, "children"),
        [Input({"type": "script-grafico", "pagina": MATCH, "elemento": MATCH}, "value")],
        [State("graficar-tubo", "data"),
         State("unidades_eje", "value"),
         State("orden", "value"),
         State("color_scheme_selector", "value"),
         State("escala_graficos_desplazamiento", "value"),
         State("escala_graficos_incremento", "value"),
         State("valor_positivo_desplazamiento", "value"),
         State("valor_negativo_desplazamiento", "value"),
         State("valor_positivo_incremento", "value"),
         State("valor_negativo_incremento", "value"),
         State("date_range_picker", "start_date"),
         State("date_range_picker", "end_date"),
         State("total_camp", "value"),
         State("ultimas_camp", "value"),
         State("cadencia_dias", "value"),
         State("leyenda_umbrales", "data")],
        prevent_initial_call=True
    )
    def actualizar_parametros_por_script(script_seleccionado, data, eje, orden, color_scheme,
                                         escala_desplazamiento, escala_incremento,
                                         valor_positivo_desplazamiento, valor_negativo_desplazamiento,
                                         valor_positivo_incremento, valor_negativo_incremento,
                                         fecha_inicial, fecha_final, total_camp, ultimas_camp, cadencia_dias,
                                         leyenda_umbrales):
        """
        Actualiza los parámetros cuando se cambia el script seleccionado.
        """
        if not script_seleccionado:
            return [dmc.Text("Seleccione un script para ver los parámetros", c="dimmed")]

        # Obtener valores actuales
        current_values = cargar_valores_actuales(
            data, eje, orden, color_scheme, escala_desplazamiento, escala_incremento,
            valor_positivo_desplazamiento, valor_negativo_desplazamiento,
            valor_positivo_incremento, valor_negativo_incremento,
            fecha_inicial, fecha_final, total_camp, ultimas_camp, cadencia_dias,
            leyenda_umbrales  # ← AÑADIR ESTA LÍNEA
        )

        # Obtener parámetros por defecto del script seleccionado
        parametros_script = obtener_parametros_por_defecto(script_seleccionado, current_values)

        # Obtener información del trigger para saber qué gráfico se está actualizando
        trigger_id = ctx.triggered_id
        num_pagina = trigger_id["pagina"]
        nombre_elemento = trigger_id["elemento"]

        # Generar campos de parámetros
        return generar_campos_parametros(num_pagina, nombre_elemento, parametros_script, current_values)


    # imprimir pdf
    @app.callback(
        [Output("descargar-informe-pdf", "data"),
         Output("modal-configurar-informe", "opened", allow_duplicate=True),
         Output("contenedor-grafico-informe", "children", allow_duplicate=True)],
        Input("btn-generar-informe-pdf", "n_clicks"),
        [State("plantilla-json-data", "data"),
         State("graficar-tubo", "data"),
         # Estados para $CURRENT
         State("unidades_eje", "value"),
         State("orden", "value"),
         State("color_scheme_selector", "value"),
         State("escala_graficos_desplazamiento", "value"),
         State("escala_graficos_incremento", "value"),
         State("valor_positivo_desplazamiento", "value"),
         State("valor_negativo_desplazamiento", "value"),
         State("valor_positivo_incremento", "value"),
         State("valor_negativo_incremento", "value"),
         State("escala_grafico_temporal", "value"),
         State("valor_positivo_temporal", "value"),
         State("valor_negativo_temporal", "value"),
         State("date_range_picker", "start_date"),
         State("date_range_picker", "end_date"),
         State("total_camp", "value"),
         State("ultimas_camp", "value"),
         State("cadencia_dias", "value"),
         State("leyenda_umbrales", "data"),
         State("slider_fechas", "value"),
         State("fechas_multiselect", "value")],
        prevent_initial_call=True
    )
    def generar_informe_pdf(n_clicks, plantilla_json, datos_tubo,
                        eje, orden, color_scheme,
                        escala_desplazamiento, escala_incremento,
                        valor_positivo_desplazamiento, valor_negativo_desplazamiento,
                        valor_positivo_incremento, valor_negativo_incremento,
                        escala_temporal, valor_positivo_temporal, valor_negativo_temporal,
                        fecha_inicial, fecha_final, total_camp, ultimas_camp, cadencia_dias,
                        leyenda_umbrales, slider_value, fechas_multiselect):
        """
        Genera un informe PDF basado en una plantilla JSON y los datos del tubo.
        """
        import os
        import copy
        import tempfile
        from pathlib import Path
        from datetime import datetime
        from utils.report_engine import generate_report_pdf_from_state

        _log = logging.getLogger(__name__)

        # [PDF-TRACE] 1 — entrada al callback
        _log.debug("[PDF-TRACE] generar_informe_pdf invocado: n_clicks=%s, plantilla_json=%s",
                  n_clicks, bool(plantilla_json))

        if not n_clicks or not plantilla_json:
            return None, True, []

        try:
            plantilla_modificada = copy.deepcopy(plantilla_json)

            # Resolver fecha seleccionada por lookup directo en el mapa de minutos
            fecha_seleccionada = _lookup_fecha_slider(slider_value, fechas_multiselect)
            _log.debug("[PDF-TRACE] fecha_seleccionada resuelta por lookup: %s", fecha_seleccionada)
            if not fecha_seleccionada and fecha_final:
                fecha_seleccionada = fecha_final

            # Guardas: sensor_id requerido por el motor HTML
            sensor_id = (datos_tubo or {}).get("info", {}).get("_sensor_id")
            # [PDF-TRACE] 2 — sensor_id y resultado de guardas
            _log.debug("[PDF-TRACE] sensor_id=%s, json_incli_existe=%s",
                      sensor_id,
                      (Path("json_inclis") / f"{sensor_id}.json").is_file() if sensor_id else False)
            if sensor_id is None:
                return None, True, [dmc.Alert(
                    "Vuelve a cargar el archivo del sensor: los datos en memoria son de una sesión anterior al nuevo motor.",
                    title="Sensor no identificado", c="orange", icon=[DashIconify(icon="mdi:alert")],
                )]
            if not (Path("json_inclis") / f"{sensor_id}.json").is_file():
                return None, True, [dmc.Alert(
                    f"No se encontró json_inclis/{sensor_id}.json. Vuelve a cargar el archivo del sensor.",
                    title="Archivo de sensor no disponible", c="orange", icon=[DashIconify(icon="mdi:alert")],
                )]

            # Claves de estilo para sustitución $CURRENT (las reservadas del motor viajan solo en context)
            current_values = {
                'eje': eje,
                'orden': True if orden == 'ascendente' else False,
                'orden_ascendente': True if orden == 'ascendente' else False,
                'color_scheme': color_scheme,
                'escala_desplazamiento': escala_desplazamiento,
                'escala_incremento': escala_incremento,
                'valor_positivo_desplazamiento': valor_positivo_desplazamiento,
                'valor_negativo_desplazamiento': valor_negativo_desplazamiento,
                'valor_positivo_incremento': valor_positivo_incremento,
                'valor_negativo_incremento': valor_negativo_incremento,
                'escala_temporal': escala_temporal,
                'valor_positivo_temporal': valor_positivo_temporal,
                'valor_negativo_temporal': valor_negativo_temporal,
                'total_camp': total_camp,
                'cadencia_dias': cadencia_dias,
            }

            # Sustituir $CURRENT en parámetros de elementos grafico/tabla
            for pagina_num, pagina_data in plantilla_modificada.get("paginas", {}).items():
                for elemento_id, elemento in pagina_data.get("elementos", {}).items():
                    tipo_elemento = elemento.get("tipo")
                    if tipo_elemento in ["grafico", "tabla"] and "configuracion" in elemento:
                        parametros = elemento["configuracion"].get("parametros", {})
                        for param_key, param_value in list(parametros.items()):
                            if param_value == "$CURRENT" and param_key in current_values:
                                elemento["configuracion"]["parametros"][param_key] = current_values[param_key]
                        # El motor HTML lee umbrales del JSON del sensor; no inyectar leyenda_umbrales aquí.

            # Contexto del contrato §2.2
            context = {
                "sensor": sensor_id,
                "sensores": [sensor_id],
                "fecha_inicial": fecha_inicial,
                "fecha_final": fecha_final,
                "fecha_seleccionada": fecha_seleccionada,
                "ultimas_camp": ultimas_camp,
                "data": {},
            }
            # [PDF-TRACE] 3 — contexto §2.2 completo antes de llamar al motor
            _log.debug("[PDF-TRACE] context=%s", context)

            nombre_plantilla = plantilla_modificada.get("configuracion", {}).get("nombre_plantilla", "informe") or "informe"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"{nombre_plantilla}_{timestamp}.pdf"

            # Render a archivo temporal (cerrar antes de leer — compatibilidad Windows)
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp.close()
            ruta_temporal = tmp.name
            try:
                log_hitos = generate_report_pdf_from_state(plantilla_modificada, context, ruta_temporal)
                # [PDF-TRACE] 4 — motor retornó; tamaño del archivo temporal
                _log.debug("[PDF-TRACE] generate_report_pdf_from_state retornó; tamaño_tmp=%d bytes; hitos=%s",
                          Path(ruta_temporal).stat().st_size, log_hitos)
                pdf_bytes = Path(ruta_temporal).read_bytes()
            finally:
                try:
                    Path(ruta_temporal).unlink(missing_ok=True)
                except Exception:
                    pass

            # [PDF-TRACE] 5 — antes del return con dcc.send_bytes
            _log.debug("[PDF-TRACE] enviando %s (%d bytes)", nombre_archivo, len(pdf_bytes))
            return dcc.send_bytes(pdf_bytes, nombre_archivo), False, [
                dmc.Alert(
                    f"PDF generado correctamente como {nombre_archivo}",
                    title="PDF generado",
                    c="green",
                    icon=[DashIconify(icon="mdi:check-circle")],
                )
            ]

        except Exception as e:
            import traceback
            error_stack = traceback.format_exc()
            print(f"Error al generar PDF: {str(e)}")
            print(error_stack)

            return None, True, [
                dmc.Alert(
                    f"Error al generar el PDF: {str(e)}",
                    title="Error",
                    c="red",
                    icon=[DashIconify(icon="mdi:alert")],
                ),
                dmc.Space(h=10),
                html.Details(
                    [
                        html.Summary("Detalles del error (para desarrollo)"),
                        html.Pre(
                            error_stack,
                            style={"whiteSpace": "pre-wrap", "fontFamily": "monospace", "padding": "10px",
                                   "backgroundColor": "#f8f9fa"}
                        )
                    ],
                    style={"marginTop": "10px", "border": "1px solid #ddd", "borderRadius": "5px", "padding": "10px"}
                )
            ]

    # Integrar el callback de actualización de parámetros
    @app.callback(
        Output("plantilla-json-data", "data", allow_duplicate=True),
        Input({"type": "param-grafico", "pagina": ALL, "elemento": ALL, "param": ALL}, "value"),
        [State({"type": "param-grafico", "pagina": ALL, "elemento": ALL, "param": ALL}, "id"),
         State("plantilla-json-data", "data")],
        prevent_initial_call=True
    )
    def actualizar_parametros_callback(valores_param, ids_param, plantilla_json):
        """
        Callback que se ejecuta cuando el usuario cambia algún valor en los campos
        de parámetros de gráficos.
        """
        if not ctx.triggered or not plantilla_json:
            return dash.no_update

        # Crear una copia del JSON para no modificar el original
        plantilla_modificada = copy.deepcopy(plantilla_json)

        # Actualizar cada parámetro modificado
        for i, valor in enumerate(valores_param):
            pagina = ids_param[i]["pagina"]
            elemento = ids_param[i]["elemento"]
            param = ids_param[i]["param"]

            # Convertir valor a tipo apropiado
            valor_convertido = valor
            try:
                # Si el valor es "$CURRENT", dejarlo como está
                if valor == "$CURRENT":
                    valor_convertido = "$CURRENT"
                # Convertir a booleano si es "True" o "False"
                elif valor.lower() == "true":
                    valor_convertido = True
                elif valor.lower() == "false":
                    valor_convertido = False
                # Convertir a número si es posible
                elif valor and (valor.replace('.', '', 1).isdigit() or (
                        len(valor) > 1 and valor[0] == '-' and valor[1:].replace('.', '', 1).isdigit())):
                    valor_convertido = float(valor)
                    # Si es un entero, convertirlo a int
                    if valor_convertido.is_integer():
                        valor_convertido = int(valor_convertido)
            except (AttributeError, ValueError):
                pass  # Mantener el valor original si hay error en la conversión

            # Actualizar el parámetro en la plantilla
            try:
                if "." in param:
                    # Parámetro anidado (ej: celdas.N1_C1)
                    grupo, sub_param = param.split(".", 1)
                    # Asegurar que la estructura existe
                    config_params = plantilla_modificada["paginas"][pagina]["elementos"][elemento]["configuracion"]["parametros"]
                    if grupo not in config_params or not isinstance(config_params[grupo], dict):
                        config_params[grupo] = {}
                    
                    config_params[grupo][sub_param] = valor_convertido
                else:
                    # Parámetro simple
                    plantilla_modificada["paginas"][pagina]["elementos"][elemento]["configuracion"]["parametros"][
                        param] = valor_convertido
            except KeyError:
                print(f"Error: No se pudo actualizar el parámetro {param} para pagina={pagina}, elemento={elemento}")

        return plantilla_modificada

    # Callback para actualizar los campos editados de texto
    @app.callback(
        Output("plantilla-json-data", "data", allow_duplicate=True),
        Input({"type": "campo-editable", "pagina": ALL, "elemento": ALL}, "value"),
        [State({"type": "campo-editable", "pagina": ALL, "elemento": ALL}, "id"),
         State("plantilla-json-data", "data")],
        prevent_initial_call=True
    )
    def actualizar_textos_editables_callback(valores_texto, ids_texto, plantilla_json):
        """
        Callback que se ejecuta cuando el usuario cambia algún valor en los campos
        de texto editables.
        """
        if not ctx.triggered or not plantilla_json:
            return dash.no_update

        # Crear una copia del JSON para no modificar el original
        plantilla_modificada = copy.deepcopy(plantilla_json)

        # Actualizar cada texto modificado
        for i, valor in enumerate(valores_texto):
            pagina = ids_texto[i]["pagina"]
            elemento = ids_texto[i]["elemento"]

            # Actualizar el texto en la plantilla
            try:
                plantilla_modificada["paginas"][pagina]["elementos"][elemento]["contenido"]["texto"] = valor
                # print(f"Texto actualizado: pagina={pagina}, elemento={elemento}, nuevo_valor='{valor}'")
            except KeyError as e:
                print(f"Error: No se pudo actualizar el texto para pagina={pagina}, elemento={elemento}: {e}")

        return plantilla_modificada



    #Callback para añadir parámetros por defecto
    @app.callback(
        Output("plantilla-json-data", "data", allow_duplicate=True),
        [Input({"type": "btn-add-params", "pagina": ALL, "elemento": ALL}, "n_clicks")],
        [State({"type": "btn-add-params", "pagina": ALL, "elemento": ALL}, "id"),
         State({"type": "script-grafico", "pagina": ALL, "elemento": ALL}, "value"),
         State({"type": "script-grafico", "pagina": ALL, "elemento": ALL}, "id"),
         State("plantilla-json-data", "data"),
         State("date_range_picker", "start_date"),
         State("date_range_picker", "end_date"),
         State("unidades_eje", "value"),
         State("orden", "value"),
         State("color_scheme_selector", "value"),
         State("total_camp", "value"),
         State("ultimas_camp", "value"),
         State("cadencia_dias", "value"),
         State("graficar-tubo", "data")],
        prevent_initial_call=True
    )
    def agregar_parametros_por_defecto(n_clicks, ids_btn, script_values, script_ids, plantilla_json,
                                       fecha_inicial, fecha_final, eje, orden, color_scheme,
                                       total_camp, ultimas_camp, cadencia_dias, data):
        """
        Agrega parámetros por defecto a un elemento de gráfico en la plantilla JSON.
        """
        if not ctx.triggered or not any(n for n in n_clicks if n):
            return dash.no_update

        # Identificar qué botón se presionó
        triggered_id = ctx.triggered_id
        if not triggered_id:
            return dash.no_update

        # Encontrar el índice del botón presionado
        index = -1
        for i, id_btn in enumerate(ids_btn):
            if id_btn == triggered_id:
                index = i
                break

        if index == -1 or n_clicks[index] is None:
            return dash.no_update

        # Obtener la página y elemento correspondientes
        pagina = triggered_id["pagina"]
        elemento = triggered_id["elemento"]

        # Buscar el script correspondiente
        script_name = "grafico_incli_0"  # Valor por defecto
        for i, id_script in enumerate(script_ids):
            if id_script["pagina"] == pagina and id_script["elemento"] == elemento:
                script_name = script_values[i]
                break

        # Crear una copia del JSON para no modificar el original
        plantilla_modificada = copy.deepcopy(plantilla_json)

        # Parámetros por defecto con token especial
        parametros_default = {
            'nombre_sensor': "$CURRENT",
            'sensor': "$CURRENT",
            'fecha_inicial': "$CURRENT",
            'fecha_final': "$CURRENT",
            'total_camp': "$CURRENT",
            'ultimas_camp': "$CURRENT",
            'cadencia_dias': "$CURRENT",
            'color_scheme': "$CURRENT",
            'escala_desplazamiento': "$CURRENT",
            'escala_incremento': "$CURRENT",
            'valor_positivo_desplazamiento': "$CURRENT",
            'valor_negativo_desplazamiento': "$CURRENT",
            'valor_positivo_incremento': "$CURRENT",
            'valor_negativo_incremento': "$CURRENT",
            'eje': "$CURRENT",
            'orden': "$CURRENT",
            'ancho_cm': 21,
            'alto_cm': 29.7,
            'dpi': 100
        }

        # Actualizar los parámetros en la plantilla
        try:
            plantilla_modificada["paginas"][pagina]["elementos"][elemento]["configuracion"][
                "parametros"] = parametros_default
        except KeyError:
            print(f"Error: No se pudo agregar parámetros para pagina={pagina}, elemento={elemento}")
            return dash.no_update

        return plantilla_modificada


    #  resetee los datos de la plantilla y otros componentes temporales cuando se cierre el modal
    @app.callback(
        [Output("plantilla-json-data", "data", allow_duplicate=True),
         Output("contenedor-campos-editables", "children", allow_duplicate=True),
         Output("contenedor-grafico-informe", "children", allow_duplicate=True),
         Output("parametros-grafico-actual", "children", allow_duplicate=True),
         Output("select-plantilla-informe", "value", allow_duplicate=True)],
        Input("modal-configurar-informe", "opened"),
        prevent_initial_call=True
    )
    def reset_modal_state_on_close(is_open):
        """
        Resetea los datos de la plantilla y componentes temporales cuando se cierra el modal.

        Args:
            is_open (bool): Estado de apertura del modal

        Returns:
            tuple: Valores reiniciados para cada componente
        """
        # Solo reiniciamos cuando el modal se cierra
        if is_open:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        # Cuando el modal se cierra, reiniciamos todos los componentes relacionados
        print("Reseteando componentes del modal de informe")

        # Liberamos memoria matplotlib si se ha usado
        try:
            import matplotlib.pyplot as plt
            plt.close('all')
        except:
            pass

        # Devolvemos valores vacíos para cada componente
        return None, [], [], [], None
    # Actualizar callbacks para manejar cambios en colores Y tipos de línea
    @app.callback(
        Output("leyenda_umbrales", "data", allow_duplicate=True),
        [Input({'type': 'color-dropdown', 'index': dash.ALL}, "value"),
         Input({'type': 'linetype-dropdown', 'index': dash.ALL}, "value")],
        [State({'type': 'color-dropdown', 'index': dash.ALL}, "id"),
         State({'type': 'linetype-dropdown', 'index': dash.ALL}, "id"),
         State("leyenda_umbrales", "data")],
        prevent_initial_call=True
    )
    def actualizar_color_y_linea_individual(valores_color, valores_linea, ids_color, ids_linea, leyenda_actual):
        """
        MODIFICADO: Ahora actualiza tanto colores como tipos de línea.
        """
        if not ctx.triggered or not isinstance(leyenda_actual, dict):
            return dash.no_update

        leyenda_actualizada = copy.deepcopy(leyenda_actual)

        # Actualizar colores
        for i, valor in enumerate(valores_color):
            if valor is not None and i < len(ids_color):
                umbral = ids_color[i]['index']
                if umbral in leyenda_actualizada:
                    if isinstance(leyenda_actualizada[umbral], dict):
                        leyenda_actualizada[umbral]['color'] = valor
                    else:
                        # Convertir formato anterior a nuevo formato
                        leyenda_actualizada[umbral] = {
                            'color': valor,
                            'tipo_linea': 'dashed'
                        }

        # Actualizar tipos de línea
        for i, valor in enumerate(valores_linea):
            if valor is not None and i < len(ids_linea):
                umbral = ids_linea[i]['index']
                if umbral in leyenda_actualizada:
                    if isinstance(leyenda_actualizada[umbral], dict):
                        leyenda_actualizada[umbral]['tipo_linea'] = valor
                    else:
                        # Convertir formato anterior a nuevo formato
                        leyenda_actualizada[umbral] = {
                            'color': 'gray',
                            'tipo_linea': valor
                        }

        return leyenda_actualizada

    # --- Callback: Tarjeta info básica del sensor ---
    @app.callback(
        Output("sensor-info-card", "children"),
        Input("graficar-tubo", "data")
    )
    def update_sensor_info_card(data):
        if not data:
            return html.Div()

        info = data.get("info", {})
        nom_sensor = info.get("nom_sensor", "—")

        # Buscar campaña de referencia y datos generales
        campaigns = {k: v for k, v in data.items() if k not in ("info", "umbrales")}
        n_campaigns = len(campaigns)
        ref_fecha = "—"
        importador = "—"
        alarm = "—"
        probe_serial = "—"

        for fecha, camp in sorted(campaigns.items()):
            ci = camp.get("campaign_info", {})
            ir = camp.get("info_readout", {})
            if ci.get("reference"):
                ref_fecha = fecha.split("T")[0] if "T" in fecha else fecha
            # Tomar datos de la última campaña
            if ci.get("importador"):
                importador = ci["importador"]
            if ci.get("alarm"):
                alarm = ci["alarm"]
            if ir.get("probe_serial"):
                probe_serial = ir["probe_serial"].strip()

        def _row(label, value):
            return html.Div([
                html.Span(label, style={"fontWeight": "600", "fontSize": "0.75rem", "color": "var(--id-text-muted)", "minWidth": "110px"}),
                html.Span(str(value), style={"fontSize": "0.75rem", "color": "var(--id-text-primary)"}),
            ], style={"display": "flex", "gap": "0.5rem", "padding": "0.25rem 0"})

        return html.Div([
            html.Div([
                DashIconify(icon="lucide:info", width=14, style={"color": "var(--id-primary)"}),
                html.Span("Info Sensor", style={"fontWeight": "600", "fontSize": "0.8rem", "color": "var(--id-text-primary)"}),
            ], style={"display": "flex", "alignItems": "center", "gap": "0.4rem", "marginBottom": "0.5rem"}),
            _row("Sensor:", nom_sensor),
            _row("Importador:", importador),
            _row("Sonda:", probe_serial),
            _row("Alarma:", alarm),
            _row("Referencia:", ref_fecha),
            _row("Campañas:", n_campaigns),
            _row("Adquisición:", info.get("adquisicion", "—")),
            _row("Disposición:", info.get("disposicion", "—")),
        ], className="id-graph-card", style={"padding": "0.75rem"})

    # --- Callback: Abrir modal exportar datos ---
    @app.callback(
        Output("modal-exportar-datos", "opened"),
        Input("btn-exportar-datos", "n_clicks"),
        State("modal-exportar-datos", "opened"),
        prevent_initial_call=True
    )
    def toggle_modal_exportar(n_clicks, is_open):
        if n_clicks:
            return not is_open
        return is_open

    # --- Callback: Exportar JSON ---
    @app.callback(
        Output("descargar-datos-export", "data", allow_duplicate=True),
        Input("btn-exportar-json", "n_clicks"),
        State("graficar-tubo", "data"),
        State("graficar-uploader", "contents"),
        State("graficar-uploader", "filename"),
        prevent_initial_call=True
    )
    def exportar_json(n_clicks, tubo_data, contents, filename):
        if not n_clicks or not contents:
            return dash.no_update
        # Exportar el JSON original completo
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        nombre = filename if filename else "datos_sensor.json"
        return dcc.send_bytes(decoded, nombre)

    # --- Callback: Exportar Excel ---
    @app.callback(
        Output("descargar-datos-export", "data", allow_duplicate=True),
        Input("btn-exportar-excel", "n_clicks"),
        State("graficar-tubo", "data"),
        State("graficar-uploader", "contents"),
        State("graficar-uploader", "filename"),
        prevent_initial_call=True
    )
    def exportar_excel(n_clicks, tubo_data, contents, filename):
        if not n_clicks or not contents:
            return dash.no_update

        # Decodificar JSON original completo
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        data = json.loads(decoded)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 1) Info inclinómetro
            info = data.get("info", {})
            info_flat = {}
            for k, v in info.items():
                if isinstance(v, dict):
                    for sk, sv in v.items():
                        info_flat[f"{k}.{sk}"] = sv
                else:
                    info_flat[k] = v
            df_info = pd.DataFrame([info_flat])
            df_info.to_excel(writer, sheet_name="Info", index=False)

            # 2) Umbrales
            umbrales_data = data.get("umbrales", {})
            valores = umbrales_data.get("valores", [])
            if valores:
                df_umbrales = pd.DataFrame(valores)
            else:
                df_umbrales = pd.DataFrame([umbrales_data]) if umbrales_data else pd.DataFrame()
            if not df_umbrales.empty:
                df_umbrales.to_excel(writer, sheet_name="Umbrales", index=False)

            # Recopilar campañas
            campaigns = {k: v for k, v in data.items() if k not in ("info", "umbrales")}
            sorted_dates = sorted(campaigns.keys())

            # 3) Info campañas
            camp_rows = []
            for fecha in sorted_dates:
                camp = campaigns[fecha]
                row = {"fecha": fecha}
                for k, v in camp.get("campaign_info", {}).items():
                    row[f"ci_{k}"] = v
                for k, v in camp.get("info_readout", {}).items():
                    row[f"ir_{k}"] = v
                camp_rows.append(row)
            if camp_rows:
                pd.DataFrame(camp_rows).to_excel(writer, sheet_name="Campañas", index=False)

            # 4-7) Raw, Calc, Spike, Bias — filas=fechas expandidas con profundidades
            for section_name, sheet_name in [("raw", "Raw"), ("calc", "Calc"), ("spike", "Spike"), ("bias", "Bias")]:
                all_rows = []
                for fecha in sorted_dates:
                    section_data = campaigns[fecha].get(section_name, [])
                    if isinstance(section_data, list):
                        for item in section_data:
                            if isinstance(item, dict):
                                row = {"fecha": fecha}
                                row.update(item)
                                all_rows.append(row)
                if all_rows:
                    pd.DataFrame(all_rows).to_excel(writer, sheet_name=sheet_name, index=False)

        output.seek(0)
        nombre_base = (filename or "datos_sensor").replace(".json", "")
        return dcc.send_bytes(output.getvalue(), f"{nombre_base}.xlsx")


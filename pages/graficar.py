# pages/graficar.py
import dash
import pandas as pd
from dash import html, dcc, callback_context, ctx
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL, MATCH
import dash_mantine_components as dmc
import base64, json
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


def layout():
    return html.Div([
            html.Div(style={'height': '50px'}),  # Espacio al comienzo de la página
            dmc.Grid([
                dmc.GridCol(
                    dmc.Card(
                        html.Div(
                            "Plano de localización de dispositivo",
                            style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'height': '400px'}
                        ),
                        shadow='sm', radius='md'
                    ), span=6
                ),
                dmc.GridCol([
                    dmc.Group(
                        [
                            dcc.Upload(
                                id='graficar-uploader',
                                multiple=False,
                                accept='.json',  # Solo acepta archivos JSON
                                children=['Drag and Drop o seleccionar sensores'],
                                style={
                                    'width': '100%',
                                    'height': '60px',
                                    'lineHeight': '60px',
                                    'borderWidth': '2px',  # Línea más gruesa
                                    'borderStyle': 'dashed',
                                    'borderRadius': '5px',
                                    'borderColor': 'blue',  # Color azul para la línea
                                    'textAlign': 'center',
                                    'margin': '10px 0',
                                    'display': 'flex',
                                    'justifyContent': 'center',
                                    'alignItems': 'center',
                                    'color': 'red'
                                }
                            ),
                            dcc.Store(id='graficar-tubo', storage_type='memory'),  # lee el json y lo deja en la memoria
                            dmc.HoverCard(
                                withArrow=True,
                                position="bottom",
                                shadow="md",
                                styles={"dropdown": {"width": "100%"}},  # estilos aplicados al panel
                                children=[
                                    dmc.HoverCardTarget(
                                        dmc.Text("Sensor:", fw=700)
                                    ),
                                    dmc.HoverCardDropdown(
                                        html.Div([
                                            html.Span("Sensor:", style={'fontWeight': 'bold'}),
                                            html.Span(id="info-hovercard"),
                                        ])
                                    ),
                                ],
                            )
                        ],
                        style={'width': '100%'}  # Ambos componentes ocupan el 100% de la línea
                    ),
                    dmc.Group(
                        [
                            dmc.Button("Patrón", id="open-patron-drawer", n_clicks=None, fullWidth=True),
                            dmc.Button("Configuración", id="open-config-drawer", n_clicks=None, fullWidth=True),
                            dmc.Button("Configurar Umbrales", id="open-umbrales-drawer", fullWidth=True),
                            # Botón para abrir el modal
                            dmc.Button(
                                "Generar Informe PDF",
                                id="btn-abrir-modal-informe",
                                leftSection=DashIconify(icon="mdi:file-pdf-box"),
                                variant="filled",
                                fullWidth=True,
                                c="red"
                            ),

                        ],
                        style={'display': 'flex', 'flexDirection': 'column'},
                        gap="1"  # Espaciamiento entre botones
                    ),
                ], span=6)
            ]),
            dmc.Drawer(
                title="Configurar Patrón",
                id="drawer-patron",
                children=[
                    html.P("Seleccionar rango de fechas"),
                    dcc.DatePickerRange(
                        id='date_range_picker',
                        start_date=None,  # Se actualizará dinámicamente con la primera fecha del DataFrame
                        end_date=datetime.now(),
                        display_format='YYYY-MM-DD',
                        style={'marginTop': '10px'}
                    ),
                    html.P("Configuración del patrón aquí."),
                    dmc.NumberInput(
                        label="Total campañas a mostrar",
                        id="total_camp",
                        value=30,# ajustar a posteriori
                        min=1
                    ),
                    dmc.NumberInput(
                        label="Pintar los últimos días",
                        id="ultimas_camp",
                        value=30,# ajustar a posteriori
                        min=1
                    ),
                    dmc.NumberInput(
                        label="Una campaña cada x días",
                        id="cadencia_dias",
                        value=30,
                        min=1
                    ),
                    html.Div(style={'height': '20px'}),  # Espacio en blanco entre el último input y el botón
                    dmc.Button("Cerrar", id="close-patron-drawer", n_clicks=None)
                ],
                opened=False,
                position="right"
            ),
            dmc.Drawer(
                title=dmc.Text("Configuración gráficos", fw="bold", size="xl", style={"marginBottom": "20px"}),
                id="drawer-config",
                children=[
                    dmc.Text("Seleccionar altura de gráficos", fw="bold", style={"marginBottom": "10px"}),
                    dmc.Slider(
                        label="Altura de los gráficos (px)",
                        id="alto_graficos_slider",
                        min=400,
                        max=1000,
                        step=100,
                        value=800,
                        marks=[
                            {"value": 400, "label": "400"},
                            {"value": 500, "label": "500"},
                            {"value": 600, "label": "600"},
                            {"value": 700, "label": "700"},
                            {"value": 800, "label": "800"},
                            {"value": 900, "label": "900"},
                            {"value": 1000, "label": "1000"},
                        ],
                        style={"marginBottom": "50px"}
                    ),
                    dmc.Text("Unidades eje vertical", fw="bold", style={"marginBottom": "10px"}),
                    dmc.Group([
                        dmc.Text("Unidades", style={"marginRight": "10px"}),
                        dmc.Select(
                            id="unidades_eje",
                            data=[
                                {"value": "index", "label": "índice"},
                                {"value": "cota_abs", "label": "cota absoluta"},
                                {"value": "depth", "label": "profundidad"}
                            ],
                            value="cota_abs",
                            style={"width": "150px", "marginRight": "20px"}
                        ),
                        dmc.Checkbox(
                            id="orden",
                            label="Ascendente",
                            checked=True
                        )
                    ], style={"marginBottom": "50px"}),
                    dmc.Text("Seleccionar estilo de colores", fw="bold", style={"marginBottom": "10px"}),
                    dmc.RadioGroup(
                        id="color_scheme_selector",
                        value="monocromo",  # Valor por defecto
                        children=[
                            dmc.Radio("Monocromo", value="monocromo", style={"marginRight": "20px"}),
                            dmc.Radio("Multicromo", value="multicromo", style={"marginRight": "20px"}),
                        ],
                        style={"marginBottom": "50px", "width": "100%", "display": "flex", "flexDirection": "row", "marginRight": "50px"}
                    ),
                    # Component for "Escala gráficos desplazamiento"
                    dmc.Text("Escala gráficos Desplazamiento", fw="bold", style={"marginBottom": "10px"}),
                    dmc.RadioGroup(
                        #label="Escala gráficos desplazamiento",
                        id="escala_graficos_desplazamiento",
                        value="manual",
                        children=[
                            dmc.Radio("Automática", value="automatica", style={"marginBottom": "10px"}),
                            dmc.Radio("Manual", value="manual", style={"marginBottom": "10px"})
                        ],
                        style={"marginBottom": "20px"}
                    ),
                    # Escala manual gráficos de desplazamiento grafico_1 y grafico_3
                    dmc.Group(
                        [
                            dmc.Text("Max", style={"width": "30px"}),
                            dmc.NumberInput(
                                id="valor_positivo_desplazamiento",
                                value=20,
                                min=-1000,
                                max=1000,
                                step=5,
                                disabled=True,
                                style={"flex": 1},
                            ),
                            dmc.Text("Min", style={"width": "30px", "marginLeft": "10px"}),
                            dmc.NumberInput(
                                id="valor_negativo_desplazamiento",
                                value=-20,
                                min=-1000,
                                max=1000,
                                step=5,
                                disabled=True,
                                style={"flex": 1},
                            ),
                        ],
                        ta="center",
                        gap="1",
                        style={"width": "100%"},
                    ),
                    # Component for "Escala gráficos incremento"
                    dmc.Text("Escala gráficos Incremento", fw="bold", style={"marginBottom": "10px"}),
                    dmc.RadioGroup(
                        # label="Escala gráficos incremento",
                        id="escala_graficos_incremento",
                        value="manual",
                        children=[
                            dmc.Radio("Automática", value="automatica", style={"marginBottom": "10px"}),
                            dmc.Radio("Manual", value="manual", style={"marginBottom": "10px"})
                        ],
                        style={"marginBottom": "20px"}
                    ),
                    # Escala manual gráficos de incremento grafico_2
                    dmc.Group(
                        [
                            dmc.Text("Max", style={"width": "30px"}),
                            dmc.NumberInput(
                                id="valor_positivo_incremento",
                                value=1,
                                min=-1000,
                                max=1000,
                                step=1,
                                disabled=True,
                                style={"flex": 1},
                            ),
                            dmc.Text("Min", style={"width": "30px", "marginLeft": "10px"}),
                            dmc.NumberInput(
                                id="valor_negativo_incremento",
                                value=-1,
                                min=-1000,
                                max=1000,
                                step=1,
                                disabled=True,
                                style={"flex": 1},
                            ),
                        ],
                        ta="center",
                        gap="1",
                        style={"width": "100%", "marginBottom": "20px"},
                    ),
                    # Component for "Escala gráfico temporal"
                    dmc.Text("Escala gráficos Evolución Temporal", fw="bold", style={"marginBottom": "10px"}),
                    dmc.RadioGroup(
                        id="escala_grafico_temporal",
                        value="manual",
                        children=[
                            dmc.Radio("Automática", value="automatica", style={"marginBottom": "10px"}),
                            dmc.Radio("Manual", value="manual", style={"marginBottom": "10px"})
                        ],
                        style={"marginBottom": "20px"}
                    ),
                    # Escala manual gráficos temporal
                    dmc.Group(
                        [
                            dmc.Text("Max", style={"width": "30px"}),
                            dmc.NumberInput(
                                id="valor_positivo_temporal",
                                value=10,
                                min=-1000,
                                max=1000,
                                step=5,
                                disabled=True,
                                style={"flex": 1},
                            ),
                            dmc.Text("Min", style={"width": "30px", "marginLeft": "10px"}),
                            dmc.NumberInput(
                                id="valor_negativo_temporal",
                                value=-10,
                                min=-1000,
                                max=1000,
                                step=5,
                                disabled=True,
                                style={"flex": 1},
                            ),
                        ],
                        ta="center",
                        gap="1",
                        style={"width": "100%", "marginBottom": "20px"},
                    ),
                    dmc.Button("Cerrar", id="close-config-drawer", n_clicks=None)
                ],
                opened=False,
                position="right"
            ),
            # Drawer para configurar Umbrales y Colores
            dcc.Store(id='leyenda_umbrales', data={}),
            dmc.Drawer(
                id="drawer-configuracion",
                title="Configuración de Umbrales",
                opened=False,
                #justify="flex-end",  # Abre el drawer desde la derecha
                position="right",
                padding="md",
                size="md",
                children=[html.Div(id='contenido-drawer')]
            ),

            dmc.Divider(style={"marginTop": "20px", "marginBottom": "20px"}),
            dmc.Grid([
                dmc.GridCol( # gráficos de desplazamientos vs profunfidadad
                    dmc.Tabs([
                        dmc.TabsList([
                            dmc.TabsTab("Desplazamientos", value="grafico1",
                                        style={'fontWeight': 'bold', 'fontSize': '1.1rem'}),
                            dmc.TabsTab("Incrementales", value="grafico2",
                                        style={'fontWeight': 'bold', 'fontSize': '1.1rem'}),
                            dmc.TabsTab("Checksum", value="grafico_chk",
                                        style={'fontWeight': 'bold', 'fontSize': '1.1rem'}),
                            dmc.TabsTab("Despl. compuestos", value="grafico3",
                                        style={'fontWeight': 'bold', 'fontSize': '1.1rem'}),
                        ]),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_1_a'),
                                        dmc.Text("Desplazamiento A", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0'}),
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_1_b'),
                                        dmc.Text("Desplazamiento B", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0'}),
                                ])
                            ]),
                            value="grafico1"
                        ),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_2_a'),
                                        dmc.Text("Incremental A", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0'}),
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_2_b'),
                                        dmc.Text("Incremental B", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0'}),
                                ])
                            ]),
                            value="grafico2"
                        ),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_chk_a'),
                                        dmc.Text("Checksum A", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0'}),
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_chk_b'),
                                        dmc.Text("Checksum B", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0'}),
                                ])
                            ]),
                            value="grafico_chk"
                        ),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_3_a'),
                                        dmc.Text("Desplazamiento A", ta="center")
                                    ], span=4, style={'padding': '0', 'margin': '0'}),
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_3_b'),
                                        dmc.Text("Desplazamiento B", ta="center")
                                    ], span=4, style={'padding': '0', 'margin': '0'}),
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_3_total'),
                                        dmc.Text("Desplazamientos Totales", ta="center")
                                    ], span=4, style={'padding': '0', 'margin': '0'}),
                                ])
                            ]),
                            value="grafico3"
                        )
                    ], value="grafico1"),
                    span=9  # Ocupa el 70% de la fila
                ),

                dmc.GridCol([
                    dmc.Title("Fechas", order=4),
                    dmc.Space(h=20),  # espacio entre componentes
                    dmc.MultiSelect(
                        id='fechas_multiselect',
                        data=[],  # Inicialmente vacío
                        placeholder="Selecciona opciones",
                        searchable=True
                    ),
                    dmc.Space(h=10),
                    dcc.Slider(
                        id='slider_fechas',
                        min=0,
                        max=1,  # This will be updated dynamically with the number of dates available
                        value=1,  # Initially set to the most recent date (last index)
                        marks={},  # Marks will be set dynamically to show dates
                        tooltip={"placement": "bottom", "always_visible": False},
                        className='slider-ocultar-tooltip-marks'  # Clase CSS para ocultar tooltip y marcas
                    ),
                    html.Div(id='slider_fecha_tooltip', style={'marginTop': '10px', 'fontWeight': 'bold'}),
                ], span=3)  # Ocupa el 30% de la fila
            ], style={"width": "100%"}),

            dmc.Divider(style={"marginTop": "20px", "marginBottom": "20px"}),
            dmc.Grid([
                dmc.GridCol(
                    dcc.Graph(id='grafico_temporal'),
                    span=9  # Ocupa el 70% de la fila
                ),
                dmc.GridCol([
                    dmc.Title("Profundidades", order=4),
                    dmc.Space(h=20),  # espacio entre componentes
                    dmc.MultiSelect(
                        id='profundidades_multiselect',
                        data=[],  # Inicialmente vacío
                        placeholder="Selecciona profundidades"
                    ),
                    dmc.Space(h=20),  # espacio entre componentes
                    dmc.MultiSelect(
                        id='desplazamientos_multiselect',
                        data=[
                            {"value": "desp_a", "label": "desp_a"},
                            {"value": "desp_b", "label": "desp_b"},
                            {"value": "desp_total", "label": "desp_total"}
                        ],
                        value=["desp_a"],  # Valor por defecto
                        placeholder="Selecciona tipo de desplazamiento"
                    )
                ], span=3)  # Ocupa el 30% de la fila
            ], style={"width": "100%"}),

            # generación de informe pdf
            # Modal para configurar el informe
            dmc.Modal(
                id="modal-configurar-informe",
                title="Configuración del Informe PDF",
                centered=True,
                size="lg",
                children=[
                    # Selector de plantilla
                    dmc.Select(
                        id="select-plantilla-informe",
                        label="Seleccione la plantilla base",
                        placeholder="Elija una plantilla",
                        data=[],
                        style={"marginBottom": "20px"}
                    ),

                    # Contenedor dinámico para los campos editables
                    html.Div(id="contenedor-campos-editables", children=[]),

                    # Botón de depuración (AÑADIR ESTA PARTE)
                    dmc.Button(
                        "Depurar parámetros (consola)",
                        id="btn-debug-parametros",
                        variant="outline",
                        c="teal",
                        leftSection=DashIconify(icon="tabler:bug"),
                        style={"marginTop": "10px", "marginBottom": "20px"}
                    ),

                    # Parámetros de configuración del gráfico
                    dmc.Space(h=20),
                    dmc.Divider(label="Configuración del gráfico"),
                    dmc.Space(h=10),

                    # Botón para generar vista previa
                    dmc.Button(
                        "Generar Vista Previa",
                        id="btn-generar-preview",
                        variant="outline",
                        c="blue",
                        fullWidth=True,
                        leftSection=DashIconify(icon="mdi:eye-outline")
                    ),
                    dmc.Space(h=10),

                    # Contenedor para la vista previa del gráfico
                    html.Div(id="contenedor-grafico-informe", children=[]),

                    # Este div se llenará con los parámetros actuales
                    html.Div(id="parametros-grafico-actual", children=[]),

                    # Almacenamiento de datos de la plantilla
                    dcc.Store(id="plantilla-json-data", storage_type="memory"),

                    # Botones de acción
                    dmc.Group(
                        justify="flex-end",
                        children=[
                            dmc.Button("Cancelar", c="gray", id="btn-cancelar-informe"),
                            dmc.Button("Generar PDF", id="btn-generar-informe-pdf",
                                       leftSection=DashIconify(icon="mdi:file-pdf-box"))
                        ],
                        mt=20
                    )
                ]
            ),

            # Componente de descarga
            dcc.Download(id="descargar-informe-pdf"),
            # borrar
            # componente de descarga provisional
            dcc.Download(id="descargar-debug-html"),
            dcc.Download(id="descargar-vista-previa-html"),
            # Script para abrir automáticamente la descarga de debug en una nueva pestaña
            html.Script("""
               window.dash_clientside = Object.assign({}, window.dash_clientside, {
                   clientside: {
                       open_debug_in_new_tab: function(data) {
                           if (data && data.filename === 'debug_parametros.html') {
                               var blob = new Blob([data.content], {type: 'text/html'});
                               var url = URL.createObjectURL(blob);
                               window.open(url, '_blank');
                           }
                           return window.dash_clientside.no_update;
                       }
                   }
               });
               """),
            # componente dummy para abrir en otra pestaña los resultados
            html.Div(id="dummy-output", style={"display": "none"}),
            # Añade este componente al layout
            html.Div(id="debug-output-dummy", style={"display": "none"})
            # fin borrar
    ])


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
    """
    Carga los datos del archivo JSON subido y actualiza la información de la tarjeta de hover.
    - **Inputs**:
    - `contents`: contenido del archivo.
    - `filename`: nombre del archivo.
    """
    @app.callback(
        [Output("info-hovercard", "children"),
         Output("graficar-tubo", "data")],
        [Input("graficar-uploader", "contents")],
        [State("graficar-uploader", "filename")]
    )
    def update_hovercard_and_store(contents, filename):
        if contents and filename:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            try:
                data = json.loads(decoded)

                # Crear el nuevo diccionario
                nuevo_diccionario = {
                    "info": data["info"],
                    "umbrales": data.get("umbrales", {})  # Si no existe, devuelve {}
                }

                # Recorrer las claves del diccionario original y guardo sólo 'calc' de las campañas 'Active'
                for index, (clave, valor) in enumerate(data.items()):
                    if clave != "info" and clave != "umbrales" and "calc" in valor and valor.get("campaign_info", {}).get("active") == True:
                        nuevo_diccionario[clave] = {
                            "calc": [
                                {
                                    "index": item["index"],
                                    "cota_abs": item["cota_abs"],
                                    "depth": item["depth"],
                                    "incr_dev_a": item["incr_dev_a"],
                                    "incr_dev_b": item["incr_dev_b"],
                                    "checksum_a": item["checksum_a"],
                                    "checksum_b": item["checksum_b"],
                                    "incr_checksum_a": item["incr_checksum_a"],  # ← AÑADIR ESTA LÍNEA
                                    "incr_checksum_b": item["incr_checksum_b"],  # ← AÑADIR ESTA LÍNEA
                                    "incr_dev_abs_a": item["incr_dev_abs_a"],
                                    "incr_dev_abs_b": item["incr_dev_abs_b"],
                                    "desp_a": item["desp_a"],
                                    "desp_b": item["desp_b"]
                                }
                                for item in valor["calc"] if isinstance(item, dict) and "index" in item
                            ],
                        }

                return f"\t{filename}", nuevo_diccionario
            except Exception as e:
                ic(e)  # Añadido para mostrar el error en caso de fallo
                return f"\t{filename}", None
        return "", None
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
            print("ADVERTENCIA: Los datos del tubo son None (inicializar_leyenda)")
            return {}

        if not isinstance(tubo, dict):
            print(f"ADVERTENCIA: Tipo inesperado para tubo: {type(tubo)}. Se esperaba un diccionario.")
            return {}

        # Obtener umbrales de manera segura
        umbrales = tubo.get('umbrales', {})

        if not isinstance(umbrales, dict):
            print(f"ADVERTENCIA: Tipo inesperado para umbrales: {type(umbrales)}. Se esperaba un diccionario.")
            return {}

        umbrales_deformadas = umbrales.get('deformadas', {})

        if not isinstance(umbrales_deformadas, dict):
            print(
                f"ADVERTENCIA: Tipo inesperado para deformadas: {type(umbrales_deformadas)}. Se esperaba un diccionario.")
            return {}

        if not umbrales_deformadas:
            print("ADVERTENCIA: No hay umbrales para asignar colores")
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
                    print(f"ADVERTENCIA: Formato inesperado para deformada {nombre_deformada}")
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
            print("ADVERTENCIA: Los datos del tubo son None (actualizar_drawer)")
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

            if cadencia_dias > 0 and len(seleccionadas) < total_camp:
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
         Input("slider_fecha_tooltip", "children"),
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
         Input("orden", "checked")]
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
            return [go.Figure() for _ in range(9)]

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

        # Obtener la fecha seleccionada en el slider
        fecha_slider = obtener_fecha_desde_slider(slider_value)

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
                    autorange=True,  # Permitir autoajuste si los datos exceden ±1
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
                uirevision='constant',
                yaxis=dict(
                    type='linear',
                    title=titulo_eje_y,
                    autorange=True if orden else 'reversed',
                    gridcolor='lightgray', gridwidth=1, griddash='dash',
                    anchor='free',
                    #position=0,  # Posicionar el eje Y en x=0
                    constrain='domain',  # ← Fija el eje al área del subplot
                    showline=False,  # Asegurarse de que no se muestra la línea vertical del eje Y
                ),
                xaxis=dict(
                    gridcolor='lightgray', gridwidth=1, griddash='dash',
                    showline=True,  # Mostrar la línea del borde inferior (eje X)
                    linecolor='darkgray',  # Color del borde inferior
                    linewidth=1,  # Grosor del borde inferior
                    zeroline=True, zerolinecolor='darkgray', zerolinewidth=1 # muestra el eje vertical en x=0
                ),
                showlegend=False, height=alto_graficos, title_x=0.5, plot_bgcolor='white'
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
            return go.Figure()

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
                    color="black",  # Color del texto
                    #weight="bold"  # Negrita
                ),
                x=0,  # Alineación a la izquierda
                xanchor="left",  # Mantener la referencia de alineación
                yanchor="top"  # Alineado en la parte superior
            ),
            yaxis=dict(
                gridcolor='lightgray', gridwidth=1, griddash='dash',
                showline=True,
                linecolor='darkgray',
                linewidth=2,
                zeroline=True,
                zerolinecolor='darkgray',
                zerolinewidth=1
            ),
            xaxis=dict(
                gridcolor='lightgray', gridwidth=1, griddash='dash',
                showline=True,
                linecolor='darkgray',
                linewidth=2,
            ),
            showlegend=True,
            plot_bgcolor='white'
        )

        return fig_temporal

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
         Output('slider_fechas', 'value')],
        [Input('fechas_multiselect', 'value')]
    )
    def update_slider_dates(fechas):
        if not fechas:
            return 0, 0, {}, 0

        try:
            # Obtener la lista de fechas del campo 'value' de cada elemento del diccionario
            #fechas_str = [fecha['value'] for fecha in fechas if 'value' in fecha]
            fechas_str = fechas

            # Convertir las fechas a objetos datetime
            fechas_dt = [datetime.fromisoformat(fecha) for fecha in fechas_str]

            # Ordenar las fechas para asegurar que están en orden cronológico
            fechas_dt.sort()

            # Obtener la fecha inicial
            fecha_inicial = fechas_dt[0]

            # Crear el diccionario de marcas donde la clave es el número de días desde la fecha inicial
            marks = {(fecha - fecha_inicial).days: fecha.strftime('%Y-%m-%d') for fecha in fechas_dt}

            # Valor mínimo y máximo del slider
            min_value = 0
            max_value = (fechas_dt[-1] - fecha_inicial).days

            # Establecer el valor inicial como el valor máximo (última fecha)
            value = max_value

            return min_value, max_value, marks, value

        except Exception as e:
            # Manejar cualquier error y devolver valores por defecto
            print(f"Error al convertir las fechas: {e}")
            return 0, 0, {}, 0

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

        try:
            # Obtener la lista de fechas del campo 'value' de cada elemento del diccionario
            #fechas_str = [fecha['value'] for fecha in fechas if 'value' in fecha]
            fechas_str = fechas

            # Convertir las fechas a objetos datetime
            fechas_dt = [datetime.fromisoformat(fecha) for fecha in fechas_str]

            # Ordenar las fechas para asegurar que están en orden cronológico
            fechas_dt.sort()

            # Obtener la fecha inicial
            fecha_inicial = fechas_dt[0]

            # Calcular la fecha correspondiente al valor del slider
            fecha_seleccionada = fecha_inicial + timedelta(days=value)

            # Buscar la fecha más cercana a la fecha seleccionada
            fecha_cercana = min(fechas_dt, key=lambda x: abs((x - fecha_seleccionada).days))

            return f"Fecha seleccionada: {fecha_cercana}"

        except Exception as e:
            print(f"Error al actualizar el tooltip del slider: {e}")
            return "Error al actualizar la fecha"

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
            # Ruta a la carpeta de plantillas
            plantillas_dir = r"biblioteca_plantillas"

            # Ruta absoluta para depuración
            ruta_absoluta = os.path.abspath(plantillas_dir)
            print("\n" + "=" * 50)
            print(f"DIAGNÓSTICO DE CARPETAS DE PLANTILLAS")
            print("=" * 50)
            print(f"Buscando plantillas en: {ruta_absoluta}")

            # Verificar si la carpeta existe
            if not os.path.exists(plantillas_dir):
                print(f"ERROR: No se encontró la carpeta: {plantillas_dir}")
                return [{"label": f"No se encontró: {ruta_absoluta}", "value": ""}]

            # Listar contenido para depuración
            contenido = os.listdir(plantillas_dir)
            print(f"Contenido de la carpeta principal: {contenido}")

            # Examinar cada elemento y verificar si es una carpeta
            print("\nSubcarpetas detectadas:")
            subcarpetas = []
            for item in contenido:
                path_item = os.path.join(plantillas_dir, item)
                if os.path.isdir(path_item):
                    subcarpetas.append(item)
                    # Verificar si contiene el archivo JSON esperado
                    json_path = os.path.join(path_item, f"{item}.json")
                    if os.path.exists(json_path):
                        print(f"  ✓ {item} (Contiene archivo JSON '{item}.json')")
                    else:
                        print(f"  ✗ {item} (No contiene archivo JSON '{item}.json')")
                else:
                    print(f"  - {item} (No es una carpeta)")

            print(f"\nTotal de subcarpetas encontradas: {len(subcarpetas)}")

            # Obtener nombres de carpetas (plantillas)
            plantillas = [{"label": nombre, "value": nombre}
                          for nombre in contenido
                          if os.path.isdir(os.path.join(plantillas_dir, nombre))]

            print(f"Plantillas disponibles para selección: {[p['label'] for p in plantillas]}")
            print("=" * 50 + "\n")

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
         State("orden", "checked"),
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
            ruta_json = os.path.join("biblioteca_plantillas", nombre_plantilla, f"{nombre_plantilla}.json")

            if not os.path.exists(ruta_json):
                return None, [
                    dmc.Alert(f"No se encontró el archivo JSON para la plantilla '{nombre_plantilla}'", c="red")]

            with open(ruta_json, 'r', encoding='utf-8') as file:
                data_json = json.load(file)

            # Obtener valores actuales
            current_values = cargar_valores_actuales(
                data, eje, orden, color_scheme, escala_desplazamiento, escala_incremento,
                valor_positivo_desplazamiento, valor_negativo_desplazamiento,
                valor_positivo_incremento, valor_negativo_incremento,
                fecha_inicial, fecha_final, total_camp, ultimas_camp, cadencia_dias,
                leyenda_umbrales  # ← AÑADIR ESTA LÍNEA
            )

            campos_editables = []

            # SECCIÓN DE TEXTOS EDITABLES
            campos_editables.append(
                dmc.Divider(label="TEXTOS EDITABLES", labelPosition="center", size="md",
                            style={"marginTop": "20px", "marginBottom": "20px"})
            )

            # Obtener nombre del sensor desde info-hovercard
            nombre_sensor_actual = "Sin nombre"
            if info_hovercard:
                # El info-hovercard contiene "\t{filename}", extraer solo el filename
                if isinstance(info_hovercard, str) and info_hovercard.startswith("\t"):
                    nombre_sensor_actual = info_hovercard.replace("\t", "").strip()
                    # Opcional: quitar la extensión .json si existe
                    if nombre_sensor_actual.endswith(".json"):
                        nombre_sensor_actual = nombre_sensor_actual[:-5]
                else:
                    nombre_sensor_actual = str(info_hovercard).strip()

            print(f"Nombre del sensor obtenido de hovercard: '{nombre_sensor_actual}'")

            textos_encontrados = 0
            for num_pagina, pagina in data_json.get("paginas", {}).items():
                elementos = pagina.get("elementos", {})
                for nombre_elemento, elemento in elementos.items():
                    if (elemento.get("tipo") == "texto" and
                            "contenido" in elemento and
                            elemento["contenido"].get("editable", True)):
                        textos_encontrados += 1

                        # Verificar si es el campo nombre_sensor
                        if nombre_elemento == "nombre_sensor":
                            # Usar el nombre del sensor desde hovercard
                            texto_actual = nombre_sensor_actual
                            print(f"Sustituyendo nombre_sensor con: '{texto_actual}'")
                        else:
                            # Para otros campos, usar el valor del JSON
                            texto_actual = elemento.get("contenido", {}).get("texto", "")

                        campos_editables.append(
                            dmc.Group([
                                dmc.Text(f"[paginas][{num_pagina}][elementos][{nombre_elemento}][contenido][texto]",
                                         fw="bold", style={"width": "50%"}),
                                dmc.TextInput(
                                    id={"type": "campo-editable", "pagina": num_pagina, "elemento": nombre_elemento},
                                    value=texto_actual, style={"width": "50%"}
                                )
                            ], style={"marginBottom": "10px"})
                        )

            # Actualizar automáticamente el campo nombre_sensor en el JSON cargado
            for num_pagina, pagina in data_json.get("paginas", {}).items():
                elementos = pagina.get("elementos", {})
                for nombre_elemento, elemento in elementos.items():
                    if (nombre_elemento == "nombre_sensor" and
                            elemento.get("tipo") == "texto" and
                            "contenido" in elemento):
                        # Actualizar el valor en el JSON
                        data_json["paginas"][num_pagina]["elementos"][nombre_elemento]["contenido"][
                            "texto"] = nombre_sensor_actual
                        print(f"JSON actualizado: nombre_sensor = '{nombre_sensor_actual}'")
                        break

            if textos_encontrados == 0:
                campos_editables.append(
                    dmc.Alert("No se encontraron campos de texto editables en esta plantilla", c="yellow")
                )

            # SECCIÓN DE GRÁFICOS CON ACORDEÓN
            campos_editables.append(
                dmc.Divider(label="GRÁFICOS CONFIGURABLES", labelPosition="center", size="md",
                            style={"marginTop": "20px", "marginBottom": "20px"})
            )

            # Obtener scripts disponibles
            directorio_graficos = "biblioteca_graficos"
            scripts_disponibles = []

            if os.path.exists(directorio_graficos):
                for item in os.listdir(directorio_graficos):
                    path_item = os.path.join(directorio_graficos, item)
                    if os.path.isdir(path_item):
                        py_path = os.path.join(path_item, f"{item}.py")
                        if os.path.exists(py_path):
                            scripts_disponibles.append({"label": item, "value": item})

            if not scripts_disponibles:
                scripts_disponibles = [{"label": "No hay scripts disponibles", "value": ""}]

            # Generar acordeón para gráficos
            graficos_encontrados = 0
            accordion_items = []

            for num_pagina, pagina in data_json.get("paginas", {}).items():
                elementos = pagina.get("elementos", {})
                for nombre_elemento, elemento in elementos.items():
                    if elemento.get("tipo") == "grafico":
                        graficos_encontrados += 1

                        # Generar contenido del accordion para este gráfico
                        contenido = generar_seccion_grafico(
                            num_pagina, nombre_elemento, elemento, scripts_disponibles, current_values
                        )

                        # Crear item del accordion
                        accordion_items.append(
                            dmc.AccordionItem(
                                [
                                    dmc.AccordionControl(
                                        dmc.Group([
                                            DashIconify(icon="mdi:chart-line", width=20),
                                            dmc.Text(f"{nombre_elemento}", fw="bold"),
                                            dmc.Badge(f"Página {num_pagina}", variant="light", c="blue")
                                        ])
                                    ),
                                    dmc.AccordionPanel(contenido)
                                ],
                                value=f"{num_pagina}-{nombre_elemento}"
                            )
                        )

            if graficos_encontrados > 0:
                campos_editables.append(
                    dmc.Accordion(
                        children=accordion_items,
                        multiple=True,  # Permite múltiples secciones abiertas
                        variant="separated",
                        radius="md"
                    )
                )
            else:
                campos_editables.append(
                    dmc.Alert("No se encontraron gráficos configurables en esta plantilla", c="yellow")
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
         State("orden", "checked"),
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
         State("orden", "checked"),
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
         State("leyenda_umbrales", "data")],  # ← AÑADIR ESTA LÍNEA
        prevent_initial_call=True
    )
    def generar_informe_pdf(n_clicks, plantilla_json, datos_tubo,
                        eje, orden, color_scheme,
                        escala_desplazamiento, escala_incremento,
                        valor_positivo_desplazamiento, valor_negativo_desplazamiento,
                        valor_positivo_incremento, valor_negativo_incremento,
                        escala_temporal, valor_positivo_temporal, valor_negativo_temporal,
                        fecha_inicial, fecha_final, total_camp, ultimas_camp, cadencia_dias,
                        leyenda_umbrales):
        """
        Genera un informe PDF basado en una plantilla JSON y los datos del tubo.

        Aprovecha que los cambios ya están guardados en el dcc.Store "plantilla-json-data",
        por lo que solo necesita sustituir cualquier token $CURRENT restante y generar el PDF.
        """
        import os
        import copy
        from pathlib import Path
        import io
        from datetime import datetime

        # Importar el módulo de generación de PDF
        try:
            from utils.pdf_generator import generate_pdf_from_template
        except ImportError:
            # Si falla, mostrar mensaje de error
            mensaje_error = dmc.Alert(
                "Error: No se pudo importar el módulo pdf_generator.py",
                title="Error de importación",
                c="red",
                icon=[DashIconify(icon="mdi:alert")],
            )
            return None, False, [mensaje_error]

        if not n_clicks or not plantilla_json:
            return None, True, []

        try:
            # Crear una copia profunda de la plantilla para no modificar el original
            plantilla_modificada = copy.deepcopy(plantilla_json)

            # Recopilar valores actuales para sustituciones $CURRENT
            current_values = {
                'eje': eje,
                'orden': orden,
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
                'fecha_inicial': fecha_inicial,
                'fecha_final': fecha_final,
                'total_camp': total_camp,
                'ultimas_camp': ultimas_camp,
                'cadencia_dias': cadencia_dias,
                'sensor': datos_tubo.get('info', {}).get('codigo', 'desconocido') if datos_tubo else 'desconocido',
                'nombre_sensor': datos_tubo.get('info', {}).get('nombre', 'Sin nombre') if datos_tubo else 'Sin nombre',
                'leyenda_umbrales': leyenda_umbrales
            }

            # Procesar la plantilla para reemplazar los valores $CURRENT restantes
            for pagina_num, pagina_data in plantilla_modificada.get("paginas", {}).items():
                for elemento_id, elemento in pagina_data.get("elementos", {}).items():
                    # Solo procesar elementos de tipo gráfico
                    if elemento.get("tipo") == "grafico" and "configuracion" in elemento:
                        # Obtener los parámetros actuales
                        parametros = elemento["configuracion"].get("parametros", {})

                        # Reemplazar valores $CURRENT
                        for param_key, param_value in list(parametros.items()):
                            if param_value == "$CURRENT" and param_key in current_values:
                                elemento["configuracion"]["parametros"][param_key] = current_values[param_key]

            # Obtener el nombre de la plantilla para el archivo
            nombre_plantilla = plantilla_modificada.get("configuracion", {}).get("nombre_plantilla", "informe")
            if not nombre_plantilla:
                nombre_plantilla = "informe"

            # Definir timestamp para el nombre del archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"{nombre_plantilla}_{timestamp}.pdf"

            # Crear buffer para el PDF
            buffer = io.BytesIO()

            # Modificación aquí: Separar las rutas de plantillas y gráficos
            biblioteca_plantillas_path = Path("biblioteca_plantillas")
            biblioteca_graficos_path = Path("biblioteca_graficos")  # Ruta directa, no dentro de plantillas

            # Generar PDF usando el módulo importado
            # Llamar a la función con ambas rutas
            generate_pdf_from_template(
                plantilla_modificada,
                datos_tubo,
                buffer,
                biblioteca_plantillas_path,
                biblioteca_graficos_path  # Pasar ruta de gráficos separadamente
            )


            # Preparar buffer para envío
            buffer.seek(0)

            # Cerrar el modal y retornar el PDF para descarga
            return dcc.send_bytes(buffer.getvalue(), nombre_archivo), False, [
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

            # Mostrar error pero mantener el modal abierto
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

    # callback para generar la vista previa
    @app.callback(
        Output("contenedor-grafico-informe", "children", allow_duplicate=True),
        [Input("btn-generar-preview", "n_clicks")],
        [State("fechas_multiselect", "value"),
         State("fechas_multiselect", "data"),
         State("slider_fecha_tooltip", "children"),
         State("graficar-tubo", "data"),
         State("alto_graficos_slider", "value"),
         State("color_scheme_selector", "value"),
         State("escala_graficos_desplazamiento", "value"),
         State("escala_graficos_incremento", "value"),
         State("valor_positivo_desplazamiento", "value"),
         State("valor_negativo_desplazamiento", "value"),
         State("valor_positivo_incremento", "value"),
         State("valor_negativo_incremento", "value"),
         State("leyenda_umbrales", "data"),
         State("unidades_eje", "value"),
         State("orden", "checked"),
         State("date_range_picker", "start_date"),
         State("date_range_picker", "end_date"),
         State({"type": "script-grafico", "pagina": ALL, "elemento": ALL}, "value"),
         State({"type": "param-grafico", "pagina": ALL, "elemento": ALL, "param": ALL}, "value"),
         State({"type": "param-grafico", "pagina": ALL, "elemento": ALL, "param": ALL}, "id"),
         State("plantilla-json-data", "data"),
         State("total_camp", "value"),
         State("ultimas_camp", "value"),
         State("cadencia_dias", "value")],
        prevent_initial_call=True
    )
    def imprimir_pdf(n_clicks, fechas_seleccionadas, fechas_colores, slider_value,
                     data, alto_graficos, color_scheme, escala_desplazamiento,
                     escala_incremento, valor_positivo_desplazamiento,
                     valor_negativo_desplazamiento, valor_positivo_incremento,
                     valor_negativo_incremento, leyenda_umbrales, eje, orden,
                     fecha_inicial, fecha_final, scripts, param_values, param_ids, plantilla_json,
                     total_camp, ultimas_camp, cadencia_dias):
        """
        Genera una vista previa del gráfico para el informe PDF mostrando los parámetros que se utilizarán.
        """
        if not n_clicks or not plantilla_json:
            return []

        # Inicializar la lista resultados al inicio de la función
        resultados = []

        # Obtener la fecha desde el tooltip del slider
        fecha_slider = slider_value.split(": ")[1] if ": " in slider_value else (
            fechas_seleccionadas[0] if fechas_seleccionadas else None
        )

        # Valores actuales disponibles en la interfaz
        current_values = cargar_valores_actuales(
            data, eje, orden, color_scheme, escala_desplazamiento, escala_incremento,
            valor_positivo_desplazamiento, valor_negativo_desplazamiento,
            valor_positivo_incremento, valor_negativo_incremento,
            fecha_inicial, fecha_final, total_camp, ultimas_camp, cadencia_dias,
            leyenda_umbrales  # ← AÑADIR ESTA LÍNEA
        )

        # Contador para los gráficos encontrados
        graficos_encontrados = 0

        # Analizar cada gráfico en la plantilla
        if "paginas" in plantilla_json:
            for num_pagina, pagina in plantilla_json.get("paginas", {}).items():
                for nombre_elemento, elemento in pagina.get("elementos", {}).items():
                    if elemento.get("tipo") == "grafico":
                        graficos_encontrados += 1

                        # Obtener el script y los parámetros específicos de este gráfico
                        configuracion = elemento.get("configuracion", {})
                        script_valor = configuracion.get("script", "")
                        parametros_json = configuracion.get("parametros", {})

                        # AQUÍ ESTÁ LA MODIFICACIÓN: Procesar los valores especiales
                        parametros_procesados = {}
                        for param, valor in parametros_json.items():
                            if isinstance(valor, str) and valor == "$CURRENT" and param in current_values:
                                # Usar el valor actual de la interfaz
                                parametros_procesados[param] = current_values[param]
                            else:
                                # Mantener el valor original
                                parametros_procesados[param] = valor

                        # Obtener parámetros específicos ingresados por el usuario
                        parametros_especificos = {}
                        for i, param_id in enumerate(param_ids):
                            if (param_id["pagina"] == num_pagina and
                                    param_id["elemento"] == nombre_elemento):
                                param_nombre = param_id["param"]
                                valor = param_values[i]
                                # Convertir valor...
                                parametros_especificos[param_nombre] = valor

                        # Parámetros por defecto (menor prioridad)
                        parametros_default = current_values

                        # Combinar parámetros (default → procesados → específicos)
                        # Los específicos tienen máxima prioridad
                        parametros_combinados = {**parametros_default, **parametros_procesados,
                                                 **parametros_especificos}

                        # Eliminar la extensión .py si está presente
                        if script_valor.endswith('.py'):
                            script_valor_sin_extension = script_valor[:-3]
                        else:
                            script_valor_sin_extension = script_valor

                        # Obtener parámetros específicos de este gráfico desde los campos del formulario
                        parametros_especificos = {}
                        for i, param_id in enumerate(param_ids):
                            if (param_id["pagina"] == num_pagina and
                                    param_id["elemento"] == nombre_elemento):
                                param_nombre = param_id["param"]
                                valor = param_values[i]

                                # Convertir valores a tipos apropiados
                                try:
                                    if valor.lower() == "true":
                                        valor = True
                                    elif valor.lower() == "false":
                                        valor = False
                                    elif valor.replace('.', '', 1).isdigit() or (
                                            valor[0] == '-' and valor[1:].replace('.', '', 1).isdigit()):
                                        valor = float(valor)
                                        if valor.is_integer():
                                            valor = int(valor)
                                except (AttributeError, ValueError):
                                    pass

                                parametros_especificos[param_nombre] = valor

                        # Combinar parámetros (default → json → específicos)
                        parametros_combinados = {**parametros_default, **parametros_json, **parametros_especificos}

                        # Verificar si el script Python existe
                        script_path = os.path.join("biblioteca_graficos", script_valor_sin_extension,
                                                   f"{script_valor_sin_extension}.py")
                        script_existe = os.path.exists(script_path)

                        resultados.append(
                            dmc.Alert(
                                "La vista previa se ha generado y abierto en una nueva pestaña.",
                                title="Vista previa generada",
                                c="green",
                                icon=[DashIconify(icon="mdi:check-circle")],
                                style={"marginBottom": "20px"}
                            )
                        )

        # Si no se encontraron gráficos
        if graficos_encontrados == 0:
            resultados.append(
                dmc.Alert(
                    "No se encontraron gráficos configurables en esta plantilla",
                    c="yellow",
                    title="Sin gráficos"
                )
            )

        return resultados
    def actualizar_script_en_json(valores_script, ids_script, plantilla_json):
        """
        Actualiza el script en el JSON de la plantilla cuando se cambia el selector.
        """
        if not ctx.triggered or not plantilla_json:
            return dash.no_update

        # Crear una copia del JSON para no modificar el original
        plantilla_modificada = copy.deepcopy(plantilla_json)

        # Actualizar el script para cada elemento seleccionado
        for i, valor in enumerate(valores_script):
            pagina = ids_script[i]["pagina"]
            elemento = ids_script[i]["elemento"]

            # Asegurarse de que el valor tenga la extensión .py
            if valor and not valor.endswith('.py'):
                valor = f"{valor}.py"

            # Actualizar el valor del script en la plantilla
            try:
                plantilla_modificada["paginas"][pagina]["elementos"][elemento]["configuracion"]["script"] = valor
            except KeyError:
                print(f"Error: No se pudo actualizar el script para pagina={pagina}, elemento={elemento}")

        return plantilla_modificada

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
                elif valor.replace('.', '', 1).isdigit() or (
                        valor[0] == '-' and valor[1:].replace('.', '', 1).isdigit()):
                    valor_convertido = float(valor)
                    # Si es un entero, convertirlo a int
                    if valor_convertido.is_integer():
                        valor_convertido = int(valor_convertido)
            except (AttributeError, ValueError):
                pass  # Mantener el valor original si hay error en la conversión

            # Actualizar el parámetro en la plantilla
            try:
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
                print(f"Texto actualizado: pagina={pagina}, elemento={elemento}, nuevo_valor='{valor}'")
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
         State("orden", "checked"),
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

    # function to display the debug information in a new browser tab
    @app.callback(
        Output("descargar-debug-html", "data"),  # Componente de descarga específico para depuración
        Input("btn-debug-parametros", "n_clicks"),
        [
            State("select-plantilla-informe", "value"),
            State({"type": "campo-editable", "pagina": ALL, "elemento": ALL}, "value"),
            State({"type": "campo-editable", "pagina": ALL, "elemento": ALL}, "id"),
            State({"type": "script-grafico", "pagina": ALL, "elemento": ALL}, "value"),
            State({"type": "script-grafico", "pagina": ALL, "elemento": ALL}, "id"),
            State({"type": "param-grafico", "pagina": ALL, "elemento": ALL, "param": ALL}, "value"),
            State({"type": "param-grafico", "pagina": ALL, "elemento": ALL, "param": ALL}, "id"),
            State("plantilla-json-data", "data")
        ],
        prevent_initial_call=True
    )
    def debug_parametros_modal(n_clicks, plantilla, textos_valores, textos_ids,
                               scripts_valores, scripts_ids,
                               params_valores, params_ids, plantilla_json):
        if not n_clicks:
            return dash.no_update

        # Creamos una copia de la plantilla para actualizarla con los valores actuales
        plantilla_actualizada = copy.deepcopy(plantilla_json)

        # Construimos el contenido HTML para mostrar en la nueva pestaña
        html_content = f"""<!DOCTYPE html>
        <html>
        <head>
            <title>Depuración de Parámetros - {plantilla}</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                .section {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .header {{ background-color: #f8f9fa; padding: 10px; margin-bottom: 15px; border-radius: 5px; }}
                .item {{ margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px dashed #eee; }}
                .error {{ color: #e74c3c; }}
                pre {{ background-color: #f8f9fa; padding: 10px; border: 1px solid #ddd; border-radius: 5px; overflow-x: auto; }}
                .success {{ color: #27ae60; }}
            </style>
            <script>
                // Este script abre esta página automáticamente en una nueva pestaña
                window.onload = function() {{
                    // Informa al padre que la página está cargada (en caso de estar en un iframe)
                    if (window.opener) {{
                        window.opener.postMessage('debug-loaded', '*');
                    }}
                }};
            </script>
        </head>
        <body>
            <div class="header">
                <h1>Depuración de Parámetros del Modal</h1>
                <p>Plantilla seleccionada: <strong>{plantilla}</strong></p>
                <p>Fecha y hora: <strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong></p>
            </div>
        """

        # Sección de campos de texto
        html_content += """
            <div class="section">
                <h2>Campos de Texto</h2>
        """

        for i, id_campo in enumerate(textos_ids):
            pagina = id_campo["pagina"]
            elemento = id_campo["elemento"]
            valor = textos_valores[i]

            html_content += f"""
                <div class="item">
                    <p>Página <strong>{pagina}</strong>, Elemento <strong>{elemento}</strong>: <code>{valor}</code></p>
            """

            # Actualizar el valor en la plantilla e informar del resultado
            try:
                plantilla_actualizada["paginas"][pagina]["elementos"][elemento]["contenido"]["texto"] = valor
                html_content += f'<p class="success">✓ Actualizado correctamente</p>'
            except KeyError:
                html_content += f'<p class="error">⚠️ No se pudo actualizar: ruta no válida</p>'

            html_content += "</div>"

        html_content += """
            </div>
        """

        # Sección de scripts de gráficos
        html_content += """
            <div class="section">
                <h2>Scripts de Gráficos</h2>
        """

        for i, id_script in enumerate(scripts_ids):
            pagina = id_script["pagina"]
            elemento = id_script["elemento"]
            valor = scripts_valores[i]

            html_content += f"""
                <div class="item">
                    <p>Página <strong>{pagina}</strong>, Elemento <strong>{elemento}</strong>: <code>{valor}</code></p>
            """

            # Actualizar el script en la plantilla
            try:
                # Añadir extensión .py si no la tiene
                if valor and not valor.endswith('.py'):
                    valor = f"{valor}.py"
                plantilla_actualizada["paginas"][pagina]["elementos"][elemento]["configuracion"]["script"] = valor
                html_content += f'<p class="success">✓ Actualizado correctamente</p>'
            except KeyError:
                html_content += f'<p class="error">⚠️ No se pudo actualizar: ruta no válida</p>'

            html_content += "</div>"

        html_content += """
            </div>
        """

        # Sección de parámetros de gráficos
        html_content += """
            <div class="section">
                <h2>Parámetros de Gráficos</h2>
        """

        for i, id_param in enumerate(params_ids):
            pagina = id_param["pagina"]
            elemento = id_param["elemento"]
            param = id_param["param"]
            valor = params_valores[i]

            html_content += f"""
                <div class="item">
                    <p>Página <strong>{pagina}</strong>, Elemento <strong>{elemento}</strong>, Parámetro <strong>{param}</strong>: <code>{valor}</code></p>
            """

            # Convertir el valor al tipo apropiado
            valor_convertido = valor
            try:
                if valor.lower() == "true":
                    valor_convertido = True
                    html_content += f'<p>Valor convertido a: <code>boolean (True)</code></p>'
                elif valor.lower() == "false":
                    valor_convertido = False
                    html_content += f'<p>Valor convertido a: <code>boolean (False)</code></p>'
                elif valor.replace('.', '', 1).isdigit() or (
                        valor[0] == '-' and valor[1:].replace('.', '', 1).isdigit()):
                    valor_convertido = float(valor)
                    if valor_convertido.is_integer():
                        valor_convertido = int(valor_convertido)
                        html_content += f'<p>Valor convertido a: <code>integer ({valor_convertido})</code></p>'
                    else:
                        html_content += f'<p>Valor convertido a: <code>float ({valor_convertido})</code></p>'
            except (AttributeError, ValueError):
                html_content += f'<p>Valor mantenido como: <code>string</code></p>'

            # Actualizar el parámetro en la plantilla
            try:
                plantilla_actualizada["paginas"][pagina]["elementos"][elemento]["configuracion"]["parametros"][
                    param] = valor_convertido
                html_content += f'<p class="success">✓ Actualizado correctamente</p>'
            except KeyError:
                html_content += f'<p class="error">⚠️ No se pudo actualizar: ruta no válida</p>'

            html_content += "</div>"

        html_content += """
            </div>
        """

        # Sección de la plantilla actualizada (JSON completo)
        html_content += """
            <div class="section">
                <h2>Plantilla Actualizada (JSON completo)</h2>
                <pre>
        """
        html_content += json.dumps(plantilla_actualizada, indent=4, ensure_ascii=False)

        html_content += """
                </pre>
            </div>
        </body>
        </html>
        """

        # Creamos el objeto de datos para la descarga con un atributo adicional para ayudar a reconocerlo
        return {
            'content': html_content,
            'filename': 'debug_parametros.html',
            'type': 'text/html',
            'base64': False
        }

    # Añade este callback clientside
    app.clientside_callback(
        """
        function(data) {
            if (data && data.filename === 'debug_parametros.html') {
                var blob = new Blob([data.content], {type: 'text/html'});
                var url = URL.createObjectURL(blob);
                window.open(url, '_blank');
            }
            return '';
        }
        """,
        Output("debug-output-dummy", "children"),
        Input("descargar-debug-html", "data"),
        prevent_initial_call=True
    )

    # pruebas para previsualizar los gráficos en html
    @app.callback(
        Output("descargar-vista-previa-html", "data"),
        Input("btn-generar-preview", "n_clicks"),
        [State("fechas_multiselect", "value"),
         State("fechas_multiselect", "data"),
         State("slider_fecha_tooltip", "children"),
         State("graficar-tubo", "data"),
         State("alto_graficos_slider", "value"),
         State("color_scheme_selector", "value"),
         State("escala_graficos_desplazamiento", "value"),
         State("escala_graficos_incremento", "value"),
         State("valor_positivo_desplazamiento", "value"),
         State("valor_negativo_desplazamiento", "value"),
         State("valor_positivo_incremento", "value"),
         State("valor_negativo_incremento", "value"),
         State("leyenda_umbrales", "data"),
         State("unidades_eje", "value"),
         State("orden", "checked"),
         State("date_range_picker", "start_date"),
         State("date_range_picker", "end_date"),
         State({"type": "script-grafico", "pagina": ALL, "elemento": ALL}, "value"),
         State({"type": "param-grafico", "pagina": ALL, "elemento": ALL, "param": ALL}, "value"),
         State({"type": "param-grafico", "pagina": ALL, "elemento": ALL, "param": ALL}, "id"),
         State("plantilla-json-data", "data"),
         State("total_camp", "value"),
         State("ultimas_camp", "value"),
         State("cadencia_dias", "value")],
        prevent_initial_call=True
    )
    def generar_vista_previa_graficos(n_clicks, fechas_seleccionadas, fechas_colores, slider_value,
                                      data, alto_graficos, color_scheme, escala_desplazamiento,
                                      escala_incremento, valor_positivo_desplazamiento,
                                      valor_negativo_desplazamiento, valor_positivo_incremento,
                                      valor_negativo_incremento, leyenda_umbrales, eje, orden,
                                      fecha_inicial, fecha_final, scripts, param_values, param_ids, plantilla_json,
                                      total_camp, ultimas_camp, cadencia_dias):
        """
        Genera una vista previa de todos los gráficos en la plantilla y los muestra en una nueva ventana.
        """
        if not n_clicks or not plantilla_json:
            return dash.no_update

        # Solución para el error "main thread is not in main loop"
        import matplotlib
        matplotlib.use('Agg')  # Establecer backend no interactivo
        import matplotlib.pyplot as plt


        # Obtener la fecha desde el tooltip del slider
        fecha_slider = slider_value.split(": ")[1] if ": " in slider_value else (
            fechas_seleccionadas[0] if fechas_seleccionadas else None
        )

        # Valores actuales disponibles en la interfaz

        current_values = cargar_valores_actuales(
            data, eje, orden, color_scheme, escala_desplazamiento, escala_incremento,
            valor_positivo_desplazamiento, valor_negativo_desplazamiento,
            valor_positivo_incremento, valor_negativo_incremento,
            fecha_inicial, fecha_final, total_camp, ultimas_camp, cadencia_dias,
            leyenda_umbrales  # ← AÑADIR ESTA LÍNEA
        )

        # Cabecera del HTML
        html_content = f"""<!DOCTYPE html>
        <html>
        <head>
            <title>Vista Previa de Gráficos - {fecha_slider}</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                .grafico-container {{ 
                    margin-bottom: 30px; 
                    padding: 15px; 
                    border: 1px solid #ddd; 
                    border-radius: 5px;
                    background-color: white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .header {{ 
                    background-color: #f8f9fa; 
                    padding: 15px; 
                    margin-bottom: 20px; 
                    border-radius: 5px;
                    border: 1px solid #dee2e6;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }}
                .img-container {{ 
                    display: flex;
                    justify-content: center;
                    margin-top: 15px;
                    background-color: white;
                    padding: 10px;
                    border-radius: 4px;
                }}
                .parametros {{
                    background-color: #f8f9fa;
                    padding: 10px;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    font-family: monospace;
                    font-size: 12px;
                    margin-top: 10px;
                    white-space: pre-wrap;
                    max-height: 200px;
                    overflow: auto;
                }}
                .error {{ color: #e74c3c; padding: 10px; background-color: #fadbd8; border-radius: 4px; }}
                .success {{ color: #27ae60; }}
                img {{ max-width: 100%; height: auto; }}
                .accordion {{
                    margin-top: 10px;
                }}
                .accordion-header {{
                    background-color: #f1f1f1;
                    padding: 10px;
                    cursor: pointer;
                    border: 1px solid #ddd;
                    border-radius: 4px 4px 0 0;
                    user-select: none;
                }}
                .accordion-content {{
                    padding: 0 10px;
                    max-height: 0;
                    overflow: hidden;
                    transition: max-height 0.3s ease-out;
                    border: 1px solid #ddd;
                    border-top: none;
                    border-radius: 0 0 4px 4px;
                }}
                .accordion.active .accordion-content {{
                    max-height: 200px;
                    padding: 10px;
                }}
                .current-value {{
                    background-color: #e3f2fd;
                    border: 1px dashed #90caf9;
                    padding: 2px 5px;
                    border-radius: 3px;
                    color: #0d47a1;
                    font-style: italic;
                }}
            </style>
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    // Script para los acordeones
                    const accordions = document.querySelectorAll('.accordion-header');
                    accordions.forEach(accordion => {{
                        accordion.addEventListener('click', function() {{
                            this.parentElement.classList.toggle('active');
                        }});
                    }});
                }});
            </script>
        </head>
        <body>
            <div class="header">
                <h1>Vista Previa de Gráficos</h1>
                <p>Fecha de generación: <strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong></p>
                <p>Fecha seleccionada en slider: <strong>{fecha_slider}</strong></p>
            </div>
        """

        # Variable para contar gráficos encontrados
        graficos_encontrados = 0

        # Analizar cada gráfico en la plantilla
        if "paginas" in plantilla_json:
            for num_pagina, pagina in plantilla_json.get("paginas", {}).items():
                for nombre_elemento, elemento in pagina.get("elementos", {}).items():
                    if elemento.get("tipo") == "grafico":
                        graficos_encontrados += 1

                        # Obtener el script y los parámetros específicos de este gráfico
                        configuracion = elemento.get("configuracion", {})
                        script_valor = configuracion.get("script", "")
                        parametros_json = configuracion.get("parametros", {})

                        # AQUÍ ESTÁ LA MODIFICACIÓN: Procesar los valores especiales
                        parametros_procesados = {}
                        for param, valor in parametros_json.items():
                            if isinstance(valor, str) and valor == "$CURRENT" and param in current_values:
                                # Usar el valor actual de la interfaz
                                parametros_procesados[param] = current_values[param]
                            else:
                                # Mantener el valor original
                                parametros_procesados[param] = valor

                        # Obtener parámetros específicos ingresados por el usuario
                        parametros_especificos = {}
                        for i, param_id in enumerate(param_ids):
                            if (param_id["pagina"] == num_pagina and
                                    param_id["elemento"] == nombre_elemento):
                                param_nombre = param_id["param"]
                                valor = param_values[i]

                                # Convertir valores a tipos apropiados
                                try:
                                    if isinstance(valor, str):
                                        if valor.lower() == "true":
                                            valor = True
                                        elif valor.lower() == "false":
                                            valor = False
                                        elif valor.replace('.', '', 1).isdigit() or (
                                                valor[0] == '-' and valor[1:].replace('.', '', 1).isdigit()):
                                            valor = float(valor)
                                            if valor.is_integer():
                                                valor = int(valor)
                                except (AttributeError, ValueError):
                                    pass

                                parametros_especificos[param_nombre] = valor

                        # Combinar parámetros (default → procesados → específicos)
                        # Los específicos tienen máxima prioridad
                        parametros_combinados = {**current_values, **parametros_procesados, **parametros_especificos}

                        # Eliminar la extensión .py si está presente
                        if script_valor.endswith('.py'):
                            script_valor_sin_extension = script_valor[:-3]
                        else:
                            script_valor_sin_extension = script_valor

                        # Verificar si el script Python existe
                        script_path = os.path.join("biblioteca_graficos", script_valor_sin_extension,
                                                   f"{script_valor_sin_extension}.py")
                        script_existe = os.path.exists(script_path)

                        # Agregar sección HTML para este gráfico
                        html_content += f"""
                        <div class="grafico-container">
                            <h2>Gráfico: {nombre_elemento} (Página {num_pagina})</h2>
                            <p><strong>Script:</strong> {script_valor}</p>
                        """

                        if script_existe:
                            try:
                                # Añadir el directorio del script al path de Python temporalmente
                                script_dir = os.path.dirname(script_path)
                                import sys
                                sys.path.insert(0, script_dir)

                                try:
                                    # Cargar dinámicamente el módulo
                                    module_spec = importlib.util.spec_from_file_location(
                                        script_valor_sin_extension,
                                        script_path
                                    )

                                    if module_spec:
                                        module = importlib.util.module_from_spec(module_spec)
                                        module_spec.loader.exec_module(module)

                                        # Obtener la función principal (mismo nombre que el script)
                                        if hasattr(module, script_valor_sin_extension):
                                            funcion_grafico = getattr(module, script_valor_sin_extension)

                                            # Llamar a la función para generar el gráfico
                                            try:
                                                # La función devuelve un data URL base64
                                                data_url = funcion_grafico(data, parametros_combinados)

                                                if data_url and data_url.startswith("data:image"):
                                                    html_content += f"""
                                                    <div class="img-container">
                                                        <img src="{data_url}" alt="Gráfico {nombre_elemento}" />
                                                    </div>
                                                    """
                                                    html_content += f"""
                                                    <p class="success">✓ Gráfico generado correctamente</p>
                                                    """
                                                else:
                                                    html_content += f"""
                                                    <p class="error">La función no devolvió una imagen válida</p>
                                                    """
                                            except Exception as e:
                                                import traceback
                                                html_content += f"""
                                                <p class="error">Error al ejecutar la función {script_valor_sin_extension}: {str(e)}</p>
                                                <div class="accordion">
                                                    <div class="accordion-header">Ver detalles del error</div>
                                                    <div class="accordion-content">
                                                        <pre>{traceback.format_exc()}</pre>
                                                    </div>
                                                </div>
                                                """
                                        else:
                                            html_content += f"""
                                            <p class="error">No se encontró la función {script_valor_sin_extension} en el módulo</p>
                                            """
                                    else:
                                        html_content += f"""
                                        <p class="error">No se pudo crear el spec para el módulo {script_valor_sin_extension}</p>
                                        """
                                finally:
                                    # Restaurar el path original
                                    if script_dir in sys.path:
                                        sys.path.remove(script_dir)
                            except Exception as e:
                                import traceback
                                html_content += f"""
                                <p class="error">Error al cargar el módulo {script_valor_sin_extension}: {str(e)}</p>
                                <div class="accordion">
                                    <div class="accordion-header">Ver detalles del error</div>
                                    <div class="accordion-content">
                                        <pre>{traceback.format_exc()}</pre>
                                    </div>
                                </div>
                                """
                        else:
                            html_content += f"""
                            <p class="error">Script no encontrado: {script_path}</p>
                            """

                        # Preparar la visualización de parámetros, resaltando los $CURRENT que se han reemplazado
                        parametros_html = ""
                        for param, valor in parametros_combinados.items():
                            param_original = parametros_json.get(param, None)
                            if param_original == "$CURRENT":
                                # Resaltar que este parámetro era $CURRENT y se ha reemplazado
                                valor_display = json.dumps(valor, ensure_ascii=False)
                                parametros_html += f'    "{param}": <span class="current-value" title="Valor tomado de la interfaz">{valor_display}</span>,\n'
                            else:
                                valor_display = json.dumps(valor, ensure_ascii=False)
                                parametros_html += f'    "{param}": {valor_display},\n'

                        # Quitar la última coma
                        if parametros_html.endswith(",\n"):
                            parametros_html = parametros_html[:-2] + "\n"

                        # Mostrar los parámetros utilizados
                        html_content += f"""
                            <div class="accordion">
                                <div class="accordion-header">Parámetros utilizados</div>
                                <div class="accordion-content">
                                    <pre>{{\n{parametros_html}}}</pre>
                                </div>
                            </div>
                        </div>
                        """

        # Si no se encontraron gráficos
        if graficos_encontrados == 0:
            html_content += """
            <div class="grafico-container">
                <h2 style="color: orange;">No se encontraron gráficos configurables en esta plantilla</h2>
            </div>
            """

        # Cerrar el HTML
        html_content += """
        </body>
        </html>
        """

        # Devolver el HTML para abrir en una nueva ventana
        return {
            'content': html_content,
            'filename': 'vista_previa_graficos.html',
            'type': 'text/html',
            'base64': False
        }

    # Añade este callback clientside para abrir la vista previa
    app.clientside_callback(
        """
        function(data) {
            if (data && data.filename === 'vista_previa_graficos.html') {
                var blob = new Blob([data.content], {type: 'text/html'});
                var url = URL.createObjectURL(blob);
                window.open(url, '_blank');
            }
            return '';
        }
        """,
        Output("debug-output-dummy", "children", allow_duplicate=True),  # Reutilizamos el componente dummy
        Input("descargar-vista-previa-html", "data"),
        prevent_initial_call=True
    )

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


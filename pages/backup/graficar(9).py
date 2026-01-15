# pages/graficar.py
import dash
import pandas as pd
from dash import html, dcc, callback_context, ctx
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
import base64, json
from icecream import ic
from datetime import datetime, timedelta
import plotly.graph_objs as go
import re
import math
import logging
from dash_iconify import DashIconify

# Importar funciones del archivo externo
from utils.diccionarios import colores_basicos, colores_ingles
from utils.funciones_comunes import get_color_for_index, asignar_colores
from utils.funciones_graficar import obtener_fecha_desde_slider, obtener_color_para_fecha, extraer_datos_fecha, add_traza, interpolar_def_tubo
from utils.grafico_incli_0 import grafico_incli_0

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
    return dmc.MantineProvider(
        children=html.Div([
            html.Div(style={'height': '50px'}),  # Espacio al comienzo de la página
            dmc.Grid([
                dmc.Col(
                    dmc.Card(
                        html.Div(
                            "Plano de localización de dispositivo",
                            style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'height': '400px'}
                        ),
                        shadow='sm', radius='md'
                    ), span=6
                ),
                dmc.Col([
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
                                children=html.Div(
                                    [
                                        html.Span("Sensor:", style={'fontWeight': 'bold'}),
                                        html.Span(id="info-hovercard")
                                    ]
                                ),
                                withArrow=True,
                                style={
                                    'width': '100%',
                                    'marginBottom': '20px'  # Espaciamiento entre HoverCard y el siguiente componente
                                }
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
                justify="flex-end"
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
                justify="flex-end"
            ),
            # Drawer para configurar Umbrales y Colores
            dcc.Store(id='leyenda_umbrales', data={}),
            dmc.Drawer(
                id="drawer-configuracion",
                title="Configuración de Umbrales",
                opened=False,
                justify="flex-end",  # Abre el drawer desde la derecha
                padding="md",
                size="md",
                children=[html.Div(id='contenido-drawer')]
            ),

            dmc.Divider(style={"marginTop": "20px", "marginBottom": "20px"}),
            dmc.Grid([
                dmc.Col( # gráficos de desplazamientos vs profunfidadad
                    dmc.Tabs([
                        dmc.TabsList([
                            dmc.Tab("Desplazamientos", value="grafico1", style={'fontWeight': 'bold', 'fontSize': '1.1rem'}),
                            dmc.Tab("Incrementales", value="grafico2", style={'fontWeight': 'bold', 'fontSize': '1.1rem'}),
                            dmc.Tab("Checksum", value="grafico_chk", style={'fontWeight': 'bold', 'fontSize': '1.1rem'}),
                            dmc.Tab("Despl. compuestos", value="grafico3", style={'fontWeight': 'bold', 'fontSize': '1.1rem'})
                        ]),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.Col([
                                        dcc.Graph(id='grafico_incli_1_a'),
                                        dmc.Text("Desplazamiento A", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0'}),
                                    dmc.Col([
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
                                    dmc.Col([
                                        dcc.Graph(id='grafico_incli_2_a'),
                                        dmc.Text("Incremental A", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0'}),
                                    dmc.Col([
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
                                    dmc.Col([
                                        dcc.Graph(id='grafico_incli_chk_a'),
                                        dmc.Text("Checksum A", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0'}),
                                    dmc.Col([
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
                                    dmc.Col([
                                        dcc.Graph(id='grafico_incli_3_a'),
                                        dmc.Text("Desplazamiento A", ta="center")
                                    ], span=4, style={'padding': '0', 'margin': '0'}),
                                    dmc.Col([
                                        dcc.Graph(id='grafico_incli_3_b'),
                                        dmc.Text("Desplazamiento B", ta="center")
                                    ], span=4, style={'padding': '0', 'margin': '0'}),
                                    dmc.Col([
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

                dmc.Col([
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
                dmc.Col(
                    dcc.Graph(id='grafico_temporal'),
                    span=9  # Ocupa el 70% de la fila
                ),
                dmc.Col([
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
                    ),

                    # Contenedor dinámico para los campos editables
                    html.Div(id="contenedor-campos-editables", children=[]),

                    # Parámetros de configuración del gráfico
                    dmc.Space(h=20),
                    dmc.Divider(label="Configuración del gráfico"),
                    dmc.Space(h=10),

                    # Selector de tipo de gráfico (NUEVO)
                    dmc.Select(
                        id="select-tipo-grafico",
                        label="Tipo de gráfico a incluir",
                        placeholder="Seleccione un tipo de gráfico",
                        data=[
                            {"value": "desp_a", "label": "Desplazamiento A"},
                            {"value": "desp_b", "label": "Desplazamiento B"},
                            {"value": "incr_dev_abs_a", "label": "Incremental A"},
                            {"value": "incr_dev_abs_b", "label": "Incremental B"},
                            {"value": "checksum_a", "label": "Checksum A"},
                            {"value": "checksum_b", "label": "Checksum B"},
                            {"value": "desp_total", "label": "Desplazamiento Total"}
                        ],
                        value="desp_a",
                    ),
                    dmc.Space(h=10),

                    # Botón para generar vista previa (NUEVO)
                    dmc.Button(
                        "Generar Vista Previa",
                        id="btn-generar-preview",
                        variant="outline",
                        c="blue",
                        fullWidth=True,
                        leftSection=DashIconify(icon="mdi:eye-outline")
                    ),
                    dmc.Space(h=10),

                    # Contenedor para la vista previa del gráfico (NUEVO)
                    html.Div(id="contenedor-grafico-informe", children=[]),

                    # Este div se llenará con los parámetros actuales
                    html.Div(id="parametros-grafico-actual", children=[]),

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
            dcc.Download(id="descargar-informe-pdf")
        ]),
        inherit=True  # To inherit default Mantine styles
    )


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
        [Output("valor_positivo_incrementos", "disabled"),
         Output("valor_negativo_incrementos", "disabled")],
        [Input("escala_graficos_incrementos", "value")]
    )
    def update_incrementos_inputs(escalado):
        if escalado == "manual":
            return False, False  # Habilitar los inputs
        return True, True  # Deshabilitar los inputs
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
                                    "depth": item["depth"], # lo uso para mostrar la evolución temporal en profundidad
                                    "incr_dev_a": item["incr_dev_a"],
                                    "incr_dev_b": item["incr_dev_b"],
                                    "checksum_a": item["checksum_a"],
                                    "checksum_b": item["checksum_b"],
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
        Asigna nuevos colores cada vez que se cargan datos de tubo.

        Args:
            tubo (dict): Datos del tubo que contienen los umbrales
            leyenda_actual (dict): No se usa, mantenido para compatibilidad con callback

        Returns:
            dict: Nueva leyenda de colores generada
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

        umbrales_tubo = list(umbrales.get('deformadas', []).keys())
        print ("umbrales previos ", umbrales_tubo)
        if not isinstance(umbrales_tubo, list):
            print(f"ADVERTENCIA: Tipo inesperado para umbrales_tubo: {type(umbrales_tubo)}. Se esperaba una lista.")
            return {}

        if not umbrales_tubo:
            print("ADVERTENCIA: No hay umbrales para asignar colores")
            return {}


        # Siempre generar una nueva leyenda de colores
        try:
            nueva_leyenda = asignar_colores(umbrales_tubo, colores_basicos)
            print(f"Nueva leyenda creada: {nueva_leyenda}")
            return nueva_leyenda
        except Exception as e:
            print(f"ERROR: No se pudo generar la leyenda: {str(e)}")
            return {}

    # Callback para actualizar dinámicamente el contenido del drawer
    @app.callback(
        Output("contenido-drawer", "children"),
        [Input("graficar-tubo", "data"),
         Input("leyenda_umbrales", "data")]
    )
    def actualizar_drawer(tubo, leyenda_actual):
        if tubo is None:
            print("ADVERTENCIA: Los datos del tubo son None (actualizar_drawer")
            return []
        #umbrales_tubo = tubo.get('umbrales', {}).get('deformadas', [])
        umbrales_tubo = list(tubo.get('umbrales', {}).get('deformadas', {}).keys())

        if not umbrales_tubo:
            return []

        # Añadir 'verde', 'naranja', 'rojo' a las opciones si no están ya
        opciones_colores = colores_basicos.copy()
        for color in ['verde', 'naranja', 'rojo']:
            if color not in opciones_colores:
                opciones_colores.append(color)

        filas = []
        for umbral in umbrales_tubo:
            filas.append(
                dbc.Row([
                    dbc.Col(html.Div(umbral), width=6),
                    dbc.Col(dcc.Dropdown(
                        id={'type': 'color-dropdown', 'index': umbral},
                        options=[{'label': c, 'value': c} for c in opciones_colores],
                        value=leyenda_actual.get(umbral, 'gray'),
                        clearable=False
                    ), width=6)
                ], className="mb-2")
            )
        return filas

    # Callback para actualizar colores individuales cuando se cambia un dropdown
    @app.callback(
        Output("leyenda_umbrales", "data", allow_duplicate=True),
        Input({'type': 'color-dropdown', 'index': dash.ALL}, "value"),
        State({'type': 'color-dropdown', 'index': dash.ALL}, "id"),
        State("leyenda_umbrales", "data"),
        prevent_initial_call=True
    )
    def actualizar_color_individual(valores, ids, leyenda_actual):
        if not ctx.triggered or not isinstance(leyenda_actual, dict):
            return dash.no_update

        leyenda_actualizada = leyenda_actual.copy()

        for i, valor in enumerate(valores):
            if valor is not None:
                umbral = ids[i]['index']
                leyenda_actualizada[umbral] = valor

        return leyenda_actualizada

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
            options = [{"value": item, "label": str(item)} for item in serie]
            return options, [serie[int(len(serie) * (1 / 3))]]

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
         Input("fechas_multiselect", "data"),
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
    def actualizar_graficos(fechas_seleccionadas, fechas_colores, slider_value, data, alto_graficos, color_scheme,
                            escala_desplazamiento, escala_incremento,
                            valor_positivo_desplazamiento, valor_negativo_desplazamiento,
                            valor_positivo_incremento, valor_negativo_incremento, leyenda_umbrales,
                            eje, orden):

        if not fechas_seleccionadas or not data:
            return [go.Figure() for _ in range(9)]

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

                # Parámetros para series no seleccionadas
                grosor = 2
                opacidad = 0.7

                # Añadir trazas a cada figura individualmente
                # Gráfico 1: Desplazamientos
                add_traza(fig1_a, datos['desp_a'], datos['eje_Y'],
                             f"{fecha} - Desp A", color, grosor, opacidad, fecha)
                add_traza(fig1_b, datos['desp_b'], datos['eje_Y'],
                             f"{fecha} - Desp B", color, grosor, opacidad, fecha)

                # Gráfico 2: Incrementales
                add_traza(fig2_a, datos['incr_dev_abs_a'], datos['eje_Y'],
                             f"{fecha} - Incr Dev A", color, grosor, opacidad, fecha)
                add_traza(fig2_b, datos['incr_dev_abs_b'], datos['eje_Y'],
                             f"{fecha} - Incr Dev B", color, grosor, opacidad, fecha)

                # Gráfico checksum
                add_traza(fig_chk_a, datos['checksum_a'], datos['eje_Y'],
                             f"{fecha} - Checksum A", color, grosor, opacidad, fecha)
                add_traza(fig_chk_b, datos['checksum_b'], datos['eje_Y'],
                             f"{fecha} - Checksum B", color, grosor, opacidad, fecha)

                # Gráfico 3: Desplazamientos Compuestos
                add_traza(fig3_a, datos['desp_a'], datos['eje_Y'],
                             f"{fecha} - Desp A", color, grosor, opacidad, fecha)
                add_traza(fig3_b, datos['desp_b'], datos['eje_Y'],
                             f"{fecha} - Desp B", color, grosor, opacidad, fecha)
                add_traza(fig3_total, datos['desp_total'], datos['eje_Y'],
                             f"{fecha} - Desp Total", color, grosor, opacidad, fecha)

        # BLOQUE 2: Luego agregar la serie seleccionada para que quede encima
        if fecha_slider in fechas_seleccionadas and fecha_slider in data and "calc" in data[fecha_slider]:
            # Obtener datos para la fecha seleccionada
            datos = extraer_datos_fecha(fecha_slider, data, eje)
            if datos:
                # Parámetros para la serie seleccionada
                color = 'darkblue'
                grosor = 4
                opacidad = 1.0

                # Añadir trazas a cada figura individualmente
                # Gráfico 1: Desplazamientos
                add_traza(fig1_a, datos['desp_a'], datos['eje_Y'],
                             f"{fecha_slider} - Desp A", color, grosor, opacidad, fecha_slider)
                add_traza(fig1_b, datos['desp_b'], datos['eje_Y'],
                             f"{fecha_slider} - Desp B", color, grosor, opacidad, fecha_slider)

                # Gráfico 2: Incrementales
                add_traza(fig2_a, datos['incr_dev_abs_a'], datos['eje_Y'],
                             f"{fecha_slider} - Incr Dev A", color, grosor, opacidad, fecha_slider)
                add_traza(fig2_b, datos['incr_dev_abs_b'], datos['eje_Y'],
                             f"{fecha_slider} - Incr Dev B", color, grosor, opacidad, fecha_slider)

                # Gráfico checksum
                add_traza(fig_chk_a, datos['checksum_a'], datos['eje_Y'],
                             f"{fecha_slider} - Checksum A", color, grosor, opacidad, fecha_slider)
                add_traza(fig_chk_b, datos['checksum_b'], datos['eje_Y'],
                             f"{fecha_slider} - Checksum B", color, grosor, opacidad, fecha_slider)

                # Gráfico 3: Desplazamientos Compuestos
                add_traza(fig3_a, datos['desp_a'], datos['eje_Y'],
                             f"{fecha_slider} - Desp A", color, grosor, opacidad, fecha_slider)
                add_traza(fig3_b, datos['desp_b'], datos['eje_Y'],
                             f"{fecha_slider} - Desp B", color, grosor, opacidad, fecha_slider)
                add_traza(fig3_total, datos['desp_total'], datos['eje_Y'],
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

                # Obtener el color de la serie desde leyenda_umbrales
                color_espanol = leyenda_umbrales.get(deformada, "Ninguno")
                opacity = 1.0

                # Si el color es "Ninguno", no se grafica esta serie
                if color_espanol == "Ninguno":
                    continue

                # Convertir el color a inglés o mantenerlo si es un código hexadecimal
                color = colores_ingles.get(color_espanol, color_espanol)


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
                    #eje_Y = [punto["cota_abs"] for punto in data[fecha_slider]['calc']]
                    eje_Y = df['cota_abs'].to_list()

                # Agregar la traza a la figura correspondiente
                fig.add_trace(go.Scatter(
                    #x=df[deformada],  # Valores de la deformada actual
                    #y=df['cota_abs'],  # Lista de cotas absolutas
                    y=eje_Y,
                    x=eje_X,
                    mode="lines",
                    name=f"{deformada}",  # Nombre del ítem de deformadas
                    line=dict(c=color, width=grosor),
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
                yaxis=dict(
                    title=titulo_eje_y,
                    autorange=True if orden else 'reversed',
                    gridc='lightgray', gridwidth=1, griddash='dash',
                    anchor='free',
                    position=0,  # Posicionar el eje Y en x=0
                    showline=False,  # Asegurarse de que no se muestra la línea vertical del eje Y
                ),
                xaxis=dict(
                    gridc='lightgray', gridwidth=1, griddash='dash',
                    showline=True,  # Mostrar la línea del borde inferior (eje X)
                    linec='darkgray',  # Color del borde inferior
                    linewidth=1,  # Grosor del borde inferior
                    zeroline=True, zerolinec='darkgray', zerolinewidth=1 # muestra el eje vertical en x=0
                ),
                showlegend=False, height=alto_graficos, title_x=0.5, plot_bgc='white'
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
                            if punto.get(eje) == profundidad and desplazamiento in punto:
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
                text="   Series Temporales (" + eje + ")",  # Título del gráfico
                font=dict(
                    family="Arial",  # Fuente (puedes cambiarla)
                    size=18,  # Tamaño más pequeño del texto
                    c="black",  # Color del texto
                    fw="bold"  # Negrita
                ),
                x=0,  # Alineación a la izquierda
                xanchor="left",  # Mantener la referencia de alineación
                yanchor="top"  # Alineado en la parte superior
            ),
            yaxis=dict(
                gridc='lightgray', gridwidth=1, griddash='dash',
                showline=True,
                linec='darkgray',
                linewidth=2,
                zeroline=True,
                zerolinec='darkgray',
                zerolinewidth=1
            ),
            xaxis=dict(
                gridc='lightgray', gridwidth=1, griddash='dash',
                showline=True,
                linec='darkgray',
                linewidth=2,
            ),
            showlegend=True,
            plot_bgc='white'
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
    # Añade este código a tu función register_callbacks
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
        Output("contenedor-campos-editables", "children"),
        Input("modal-configurar-informe", "opened"),
        prevent_initial_call=True
    )
    def update_modal_content(is_open):
        """
        Actualiza el contenido del modal cuando se abre, añadiendo un componente
        para cargar archivos JSON de plantilla.
        """
        if is_open:
            return [
                dmc.Text("Seleccione un archivo JSON de plantilla:", fw="bold",
                         style={"marginTop": "20px"}),
                dcc.Upload(
                    id="plantilla-informe-uploader",
                    children=[
                        dmc.Group([
                            DashIconify(icon="mdi:file-upload", width=24),
                            dmc.Text("Arrastre o haga clic para seleccionar el archivo JSON")
                        ])
                    ],
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px 0'
                    },
                    multiple=False,
                    accept='.json'
                ),
                dmc.Space(h=20),
                html.Div(id="plantilla-json-preview"),
                # Almacenamiento de datos de la plantilla
                dcc.Store(id="plantilla-json-data", storage_type="memory")
            ]
        return []

    @app.callback(
        [Output("plantilla-json-preview", "children"),
         Output("plantilla-json-data", "data"),
         Output("select-plantilla-informe", "data")],
        [Input("plantilla-informe-uploader", "contents")],
        [State("plantilla-informe-uploader", "filename")],
        prevent_initial_call=True
    )
    def preview_plantilla_json(contents, filename):
        """
        Procesa el archivo JSON cargado, muestra sus claves principales y
        actualiza las opciones del desplegable de plantillas.
        """
        if contents is None:
            return [], None, []

        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)

        try:
            if filename.endswith('.json'):
                # Parsear JSON
                data = json.loads(decoded)

                # Preparar opciones para el desplegable de plantillas
                template_options = [{"label": key, "value": key} for key in data.keys()]

                # Mostrar las claves principales
                preview = [
                    dmc.Alert(
                        f"Archivo cargado: {filename}",
                        c="green",
                        withCloseButton=False
                    ),
                    dmc.Space(h=10),
                    dmc.Text("Claves principales del archivo:"),
                    html.Ul([html.Li(str(key)) for key in data.keys()]),
                    dmc.Space(h=10),
                    dmc.Text("Estructura JSON completa:"),
                    html.Pre(
                        json.dumps(data, indent=2, ensure_ascii=False),
                        style={
                            "backgroundColor": "#f8f9fa",
                            "padding": "10px",
                            "border": "1px solid #dee2e6",
                            "borderRadius": "4px",
                            "maxHeight": "200px",
                            "overflow": "auto"
                        }
                    )
                ]

                return preview, data, template_options
            else:
                error_message = "Por favor, cargue un archivo JSON válido."
                return [dmc.Alert(error_message, c="red")], None, []
        except Exception as e:
            error_message = f"Error al procesar el archivo: {str(e)}"
            print(error_message)
            return [dmc.Alert(error_message, c="red")], None, []

    @app.callback(
        Output("parametros-grafico-actual", "children"),
        [Input("select-plantilla-informe", "value")],
        [State("plantilla-json-data", "data")],
        prevent_initial_call=True
    )
    def update_parametros_grafico(selected_template, json_data):
        """
        Actualiza la información de parámetros del gráfico basado en la plantilla seleccionada.
        """
        if not selected_template or not json_data:
            return []

        try:
            # Obtener los datos de la plantilla seleccionada
            template_data = json_data.get(selected_template, {})

            # Mostrar los parámetros de la plantilla
            return [
                dmc.Text(f"Parámetros de la plantilla: {selected_template}", fw="bold"),
                dmc.Space(h=10),
                html.Pre(
                    json.dumps(template_data, indent=2, ensure_ascii=False),
                    style={
                        "backgroundColor": "#f8f9fa",
                        "padding": "10px",
                        "border": "1px solid #dee2e6",
                        "borderRadius": "4px",
                        "maxHeight": "200px",
                        "overflow": "auto"
                    }
                )
            ]
        except Exception as e:
            error_message = f"Error al mostrar los parámetros: {str(e)}"
            print(error_message)
            return [dmc.Alert(error_message, c="red")]

    @app.callback(
        Output("contenedor-grafico-informe", "children"),
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
         State("select-tipo-grafico", "value")],
        prevent_initial_call=True
    )
    def generar_preview_grafico(n_clicks, fechas_seleccionadas, fechas_colores, slider_value,
                                data, alto_graficos, color_scheme, escala_desplazamiento,
                                escala_incremento, valor_positivo_desplazamiento,
                                valor_negativo_desplazamiento, valor_positivo_incremento,
                                valor_negativo_incremento, leyenda_umbrales, eje, orden, tipo_grafico):
        """
        Genera una vista previa del gráfico para el informe PDF.
        """
        if not n_clicks or not fechas_seleccionadas:
            return []

        # Obtener la fecha desde el tooltip del slider
        fecha_slider = slider_value.split(": ")[1] if ": " in slider_value else fechas_seleccionadas[0]

        # Generar el gráfico
        imagen_base64 = grafico_incli_0(
            fechas_seleccionadas=fechas_seleccionadas,
            fechas_colores=fechas_colores,
            fecha_slider=fecha_slider,
            data=data,
            alto_graficos=alto_graficos,
            color_scheme=color_scheme,
            escala_desplazamiento=escala_desplazamiento,
            escala_incremento=escala_incremento,
            valor_positivo_desplazamiento=valor_positivo_desplazamiento,
            valor_negativo_desplazamiento=valor_negativo_desplazamiento,
            valor_positivo_incremento=valor_positivo_incremento,
            valor_negativo_incremento=valor_negativo_incremento,
            leyenda_umbrales=leyenda_umbrales,
            eje=eje,
            orden=orden,
            tipo_grafico=tipo_grafico
        )

        # Mostrar la imagen generada
        return [
            dmc.Text("Vista previa del gráfico para el informe:", fw="bold", size="lg"),
            dmc.Space(h=10),
            html.Img(src=imagen_base64, style={"width": "100%", "border": "1px solid #dee2e6"})
        ]

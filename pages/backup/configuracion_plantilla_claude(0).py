# /pages/configuracion_plantilla_claude.py
from dash import html, dcc, callback
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import base64
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from pathlib import Path
import io
from datetime import datetime

from utils.funciones_configuracion_plantilla import actualizar_orientacion_y_reglas

# Constantes

A4_PORTRAIT_WIDTH = 595  # Ancho A4 vertical en puntos (21 cm)
A4_PORTRAIT_HEIGHT = 842  # Alto A4 vertical en puntos (29.7 cm)
A4_LANDSCAPE_WIDTH = 842  # Ancho A4 horizontal en puntos (29.7 cm)
A4_LANDSCAPE_HEIGHT = 595  # Alto A4 horizontal en puntos (21 cm)
SCALE_FACTOR = 0.8  # Factor de escala para visualizar en pantalla
CM_TO_POINTS = 28.35  # 1 cm = 28.35 puntos
MM_TO_POINTS = 2.835  # 1 mm = 2.835 puntos



def layout():
    return dmc.MantineProvider(
        theme={"colorScheme": "light"},
        children=dmc.Container([
            dmc.Title("Editor de Plantillas de Informe", order=1, mb=20),
            # dcc para guardar los elementos que se van creando
            dcc.Store(
                id='store-componentes',
                storage_type='memory',
                data={
                    'elementos': [],  # Lista de todos los elementos (líneas, rectángulos, etc.)
                    'seleccionado': None,  # ID del elemento seleccionado actualmente
                    'configuracion': {
                        'orientacion': 'portrait',
                        'nombre_plantilla': ''
                    }
                }
            ),

            # Sección de configuración (tercio superior)
            dmc.Paper(p="md", withBorder=True, shadow="sm", radius="md", mb=20, children=[
                dmc.Grid([
                    # Primera fila - Configuración general
                    dmc.Col([
                        dmc.TextInput(
                            id="ep-template-name",
                            label="Nombre de la plantilla:",
                            placeholder="Informe de inclinómetro",
                            required=True,
                            mb=10
                        ),
                    ], span=6),
                    dmc.Col([
                        dmc.Select(
                            id="ep-inclinometer-selector",
                            label="Inclinómetro:",
                            placeholder="Seleccionar inclinómetro",
                            data=[
                                {"value": "incl-1", "label": "Inclinómetro 1"},
                                {"value": "incl-2", "label": "Inclinómetro 2"}
                            ],
                            mb=10
                        ),
                    ], span=6),

                    # Segunda fila - Orientación (en línea)
                    dmc.Col([
                        dmc.Group([
                            dmc.Text("Orientación de la página:", size="sm", pt=8),
                            dmc.SegmentedControl(
                                id="ep-orientation-selector",
                                value="portrait",
                                data=[
                                    {"value": "portrait", "label": "Vertical"},
                                    {"value": "landscape", "label": "Horizontal"}
                                ],
                            )
                        ], justify="flex-start", gap="1"),
                    ], span=12, mt=5, mb=10),

                    # Segunda fila - Botones de elementos
                    dmc.Col([
                        dmc.Group([
                            dmc.Button(
                                "Añadir línea",
                                id="ep-add-line-btn",
                                leftSection=DashIconify(icon="mdi:line-horizontal"),
                                variant="outline"
                            ),
                            dmc.Button(
                                "Añadir rectángulo",
                                id="ep-add-rectangle-btn",
                                leftSection=DashIconify(icon="mdi:rectangle-outline"),
                                variant="outline"
                            ),
                            dmc.Button(
                                "Añadir gráfico",
                                id="ep-add-graph-btn",
                                leftSection=DashIconify(icon="mdi:chart-line"),
                                variant="outline"
                            ),
                            dmc.Button(
                                "Añadir tabla",
                                id="ep-add-table-btn",
                                leftSection=DashIconify(icon="mdi:table"),
                                variant="outline"
                            ),
                            dmc.Button(
                                "Imprimir PDF",
                                id="ep-print-pdf-btn",
                                leftSection=DashIconify(icon="mdi:file-pdf-box"),
                                c="red"
                            ),
                        ], justify="center", mt=10)
                    ], span=12),
                ]),

                # Drawers - inicialmente ocultos
                # Drawer líneas
                dmc.Drawer(
                    id="drawer-line",
                    title=html.Span("Configurar Línea", style={"fontWeight": "bold"}),
                    opened=False,
                    position="top",
                    children=[
                        # Selector de líneas existentes
                        dmc.Group([
                            dmc.Text("Seleccionar línea existente:", size="sm", pt=8),
                            dmc.Select(
                                id="line-selector",
                                placeholder="Seleccionar para editar",
                                clearable=True,
                                data=[],
                                style={"width": "200px"}
                            )
                        ], justify="flex-start", gap="1", mb=15),

                        # Tres columnas principales
                        dmc.Grid([
                            # Columna 1: Coordenadas en formato tabla (más compacta)
                            dmc.Col([
                                dmc.Text("Coordenadas", fw="bold", ta="center", mb=10),
                                # Centro la tabla con un div
                                html.Div(
                                    dmc.Table(
                                        [
                                            html.Thead(
                                                html.Tr([
                                                    html.Th("", style={"paddingRight": "15px"}),
                                                    html.Th("X (cm)",
                                                            style={"paddingLeft": "15px", "paddingRight": "15px"}),
                                                    html.Th("Y (cm)",
                                                            style={"paddingLeft": "15px", "paddingRight": "15px"})
                                                ])
                                            ),
                                            html.Tbody([
                                                html.Tr([
                                                    html.Td("Origen",
                                                            style={"fontWeight": "bold", "paddingRight": "15px"}),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="line-x1",
                                                            min=0,
                                                            max=30,
                                                            step=0.1,
                                                            precision=1,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        ),
                                                        style={"paddingLeft": "15px", "paddingRight": "15px"}
                                                    ),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="line-y1",
                                                            min=0,
                                                            max=30,
                                                            step=0.1,
                                                            precision=1,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        ),
                                                        style={"paddingLeft": "15px", "paddingRight": "15px"}
                                                    )
                                                ]),
                                                html.Tr([
                                                    html.Td("Final",
                                                            style={"fontWeight": "bold", "paddingRight": "15px"}),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="line-x2",
                                                            min=0,
                                                            max=30,
                                                            step=0.1,
                                                            precision=1,
                                                            value=5.0,
                                                            style={"width": "80px"}
                                                        ),
                                                        style={"paddingLeft": "15px", "paddingRight": "15px"}
                                                    ),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="line-y2",
                                                            min=0,
                                                            max=30,
                                                            step=0.1,
                                                            precision=1,
                                                            value=5.0,
                                                            style={"width": "80px"}
                                                        ),
                                                        style={"paddingLeft": "15px", "paddingRight": "15px"}
                                                    )
                                                ])
                                            ])
                                        ],
                                        # Propiedades estéticas de Mantine para la tabla
                                        highlightOnHover=True,  # Resalta las filas al pasar el ratón
                                        horizontalgap="1",  # Espaciado horizontal medio
                                        verticalgap="1",  # Espaciado vertical pequeño
                                        withColumnBorders=True,  # Añade líneas verticales entre columnas
                                        withBorder=False,  # Sin borde exterior
                                        striped=False,  # Sin filas alternadas
                                        style={"borderCollapse": "collapse", "width": "auto", "margin": "0 auto"}
                                    ),style={"display": "flex", "justifyContent": "center"}  # Centrado
                                )
                            ], span=4),

                            # Columna 2: Grosor y Color (selectores más anchos)
                            dmc.Col([
                                dmc.Text("Grosor y Color", fw="bold", ta="center", mb=10),
                                # Centro todo el contenido
                                html.Div(
                                    dmc.Stack([
                                        dmc.Text("Grosor de línea (px):", size="sm", ta="center"),
                                        html.Div(
                                            dmc.NumberInput(
                                                id="line-grosor",
                                                min=1,
                                                max=10,
                                                step=1,
                                                value=1,
                                                style={"width": "140px"}  # Ancho aumentado
                                            ),
                                            style={"display": "flex", "justifyContent": "center"}
                                        ),
                                        dmc.Space(h=10),
                                        dmc.Text("Color de línea:", size="sm", ta="center"),
                                        html.Div(
                                            dmc.ColorInput(
                                                id="line-color",
                                                value="#000000",
                                                format="hex",
                                                swatches=[
                                                    "#000000", "#FF0000", "#00FF00", "#0000FF",
                                                    "#FFFF00", "#00FFFF", "#FF00FF", "#C0C0C0"
                                                ],
                                                style={"width": "140px"}  # Ancho aumentado
                                            ),
                                            style={"display": "flex", "justifyContent": "center"}
                                        )
                                    ], gap="1"),
                                    style={"display": "flex", "justifyContent": "center", "flexDirection": "column"}
                                )
                            ], span=4),

                            # Columna 3: Nombre y Botones (actualizado para igualar al drawer de rectángulo)
                            dmc.Col([
                                # Nombre centrado
                                html.Div(
                                    dmc.Group([
                                        dmc.Text("Nombre del identificador:", fw="bold", size="sm", pt=8),
                                        dmc.TextInput(
                                            id="line-nombre",
                                            placeholder="Línea 1",
                                            value="Línea 1",
                                            style={"width": "160px"}
                                        )
                                    ], justify="center", gap="1", mb=20),
                                    style={"display": "flex", "justifyContent": "center", "width": "100%"}
                                ),

                                # Botones centrados verticalmente
                                html.Div(
                                    dmc.Stack([
                                        dmc.Button(
                                            "Crear/Actualizar",
                                            id="btn-create-line",
                                            variant="filled",
                                            c="blue",
                                            style={"width": "150px"}
                                        ),
                                        dmc.Space(h=10),
                                        dmc.Button(
                                            "Borrar",
                                            id="btn-delete-line",
                                            variant="filled",
                                            c="red",
                                            style={"width": "150px"}
                                        )
                                    ], gap="1", ta="center"),
                                    style={
                                        "display": "flex",
                                        "justifyContent": "center",
                                        "alignItems": "center",
                                        "height": "calc(100% - 60px)"
                                    }
                                )
                            ], span=4)
                        ]),
                    ]
                ),
                # Drawer rectángulo
                dmc.Drawer(
                    id="ep-rectangle-drawer",
                    title=html.Span("Configurar Rectángulo", style={"fontWeight": "bold"}),
                    opened=False,
                    position="top",
                    children=[
                        # Selector de rectángulos existentes
                        dmc.Group([
                            dmc.Text("Seleccionar rectángulo existente:", size="sm", pt=8),
                            dmc.Select(
                                id="rectangle-selector",
                                placeholder="Seleccionar para editar",
                                clearable=True,
                                data=[],
                                style={"width": "200px"}
                            )
                        ], justify="flex-start", gap="1", mb=15),

                        # Tres columnas principales
                        dmc.Grid([
                            # Columna 1: Posición y dimensiones en dos tablas verticales
                            dmc.Col([
                                # Tabla de Posición
                                dmc.Text("Esquina superior izquierda", fw="bold", ta="center", mb=10),
                                html.Div(
                                    dmc.Table(
                                        [
                                            html.Thead(
                                                html.Tr([
                                                    html.Th(""),
                                                    html.Th("X (cm)"),
                                                    html.Th("Y (cm)")
                                                ])
                                            ),
                                            html.Tbody([
                                                html.Tr([
                                                    html.Td("Coordenadas", style={"fontWeight": "bold"}),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="rectangle-x",
                                                            min=0,
                                                            max=30,
                                                            step=0.1,
                                                            precision=1,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        )
                                                    ),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="rectangle-y",
                                                            min=0,
                                                            max=30,
                                                            step=0.1,
                                                            precision=1,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        )
                                                    )
                                                ])
                                            ])
                                        ],
                                        highlightOnHover=True,
                                        horizontalgap="1",
                                        verticalgap="1",
                                        withColumnBorders=True,
                                        withBorder=False,
                                        striped=False,
                                        style={"borderCollapse": "collapse", "width": "auto", "margin": "0 auto",
                                               "marginBottom": "15px"}
                                    ),
                                    style={"display": "flex", "justifyContent": "center"}
                                ),

                                # Tabla de Dimensiones
                                dmc.Text("Dimensiones", fw="bold", ta="center", mb=10),
                                html.Div(
                                    dmc.Table(
                                        [
                                            html.Thead(
                                                html.Tr([
                                                    html.Th(""),
                                                    html.Th("Ancho (cm)"),
                                                    html.Th("Alto (cm)")
                                                ])
                                            ),
                                            html.Tbody([
                                                html.Tr([
                                                    html.Td("Tamaño", style={"fontWeight": "bold"}),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="rectangle-width",
                                                            min=0.1,
                                                            max=30,
                                                            step=0.1,
                                                            precision=1,
                                                            value=5.0,
                                                            style={"width": "80px"}
                                                        )
                                                    ),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="rectangle-height",
                                                            min=0.1,
                                                            max=30,
                                                            step=0.1,
                                                            precision=1,
                                                            value=3.0,
                                                            style={"width": "80px"}
                                                        )
                                                    )
                                                ])
                                            ])
                                        ],
                                        highlightOnHover=True,
                                        horizontalgap="1",
                                        verticalgap="1",
                                        withColumnBorders=True,
                                        withBorder=False,
                                        striped=False,
                                        style={"borderCollapse": "collapse", "width": "auto", "margin": "0 auto"}
                                    ),
                                    style={"display": "flex", "justifyContent": "center"}
                                )
                            ], span=4),

                            # Columna 2: Estilo - Optimizada con mejor distribución de espacio
                            dmc.Col([
                                dmc.Text("Estilo", fw="bold", ta="center", mb=15),

                                # Fila de Borde - Nueva proporción 1/4 para título, 3/4 para controles
                                dmc.Grid([
                                    # Título (1/4)
                                    dmc.Col([
                                        dmc.Text("Borde:", fw="bold", size="sm", ta="left", pt=8),
                                    ], span=3, style={"paddingLeft": "10px"}),

                                    # Controles (3/4)
                                    dmc.Col([
                                        dmc.Group([
                                            dmc.Text("Grosor:", size="sm", pt=8, style={"minWidth": "55px"}),
                                            dmc.NumberInput(
                                                id="rectangle-border-width",
                                                min=0,
                                                max=10,
                                                step=1,
                                                value=1,
                                                style={"width": "65px"}
                                            ),
                                            dmc.Text("Color:", size="sm", pt=8,
                                                     style={"minWidth": "45px", "marginLeft": "10px"}),
                                            dmc.ColorInput(
                                                id="rectangle-border-color",
                                                value="#000000",
                                                format="hex",
                                                swatches=[
                                                    "#000000", "#FF0000", "#00FF00", "#0000FF",
                                                    "#FFFF00", "#00FFFF", "#FF00FF", "#C0C0C0"
                                                ],
                                                style={"flex": 1, "minWidth": "120px"}  # Expandible
                                            )
                                        ], justify="flex-start", gap="1", style={"width": "100%"})
                                    ], span=9)
                                ], mb=20),

                                # Fila de Relleno - Nueva proporción 1/4 para título, 3/4 para controles
                                dmc.Grid([
                                    # Título (1/4)
                                    dmc.Col([
                                        dmc.Text("Relleno:", fw="bold", size="sm", ta="left", pt=8),
                                    ], span=3, style={"paddingLeft": "10px"}),

                                    # Controles (3/4)
                                    dmc.Col([
                                        dmc.Group([
                                            dmc.Text("Color:", size="sm", pt=8, style={"minWidth": "45px"}),
                                            dmc.ColorInput(
                                                id="rectangle-fill-color",
                                                value="#FFFFFF",
                                                format="hex",
                                                swatches=[
                                                    "#FFFFFF", "#EEEEEE", "#FFCCCC", "#CCFFCC",
                                                    "#CCCCFF", "#FFFFCC", "#CCFFFF", "#F8F8F8"
                                                ],
                                                style={"width": "120px"}
                                            ),
                                            dmc.Text("Opacidad:", size="sm", pt=8,
                                                     style={"minWidth": "70px", "marginLeft": "10px"}),
                                            dmc.Slider(
                                                id="rectangle-opacity",
                                                min=0,
                                                max=100,
                                                step=5,
                                                value=100,
                                                marks=[
                                                    {"value": 0, "label": "0%"},
                                                    {"value": 100, "label": "100%"}
                                                ],
                                                style={"flex": 1, "minWidth": "100px"}  # Expandible
                                            )
                                        ], justify="flex-start", gap="1", style={"width": "100%"})
                                    ], span=9)
                                ])
                            ], span=4),

                            # Columna 3: Nombre y Botones (sin cambios)
                            dmc.Col([
                                # Nombre centrado
                                html.Div(
                                    dmc.Group([
                                        dmc.Text("Nombre del identificador:", fw="bold", size="sm", pt=8),
                                        dmc.TextInput(
                                            id="rectangle-nombre",
                                            placeholder="Rectángulo 1",
                                            value="Rectángulo 1",
                                            style={"width": "160px"}
                                        )
                                    ], justify="center", gap="1", mb=20),
                                    style={"display": "flex", "justifyContent": "center", "width": "100%"}
                                ),

                                # Botones centrados verticalmente
                                html.Div(
                                    dmc.Stack([
                                        dmc.Button(
                                            "Crear/Actualizar",
                                            id="btn-create-rectangle",
                                            variant="filled",
                                            c="blue",
                                            style={"width": "150px"}
                                        ),
                                        dmc.Space(h=10),
                                        dmc.Button(
                                            "Borrar",
                                            id="btn-delete-rectangle",
                                            variant="filled",
                                            c="red",
                                            style={"width": "150px"}
                                        )
                                    ], gap="1", ta="center"),
                                    style={
                                        "display": "flex",
                                        "justifyContent": "center",
                                        "alignItems": "center",
                                        "height": "calc(100% - 60px)"
                                    }
                                )
                            ], span=4),
                        ]),
                    ]
                ),
                # Resto de drawers para configurar
                dmc.Drawer(
                    id="ep-graph-drawer",
                    title="Configuración de gráfico",
                    opened=False,
                    position="top",
                    children=[
                        dmc.Text("Configuración de gráfico - A implementar")
                    ]
                ),
                dmc.Drawer(
                    id="ep-table-drawer",
                    title="Configuración de tabla",
                    opened=False,
                    position="top",
                    children=[
                        dmc.Text("Configuración de tabla - A implementar")
                    ]
                ),
            ]),

            # Canvas para diseño (dos tercios inferiores)
            dmc.Paper(
                p="md",
                withBorder=True,
                shadow="sm",
                radius="md",
                children=[
                    dmc.Text("Área de Diseño", fw=500, mb=10),

                    # Contenedor del canvas con reglas (se actualizará con callback)
                    html.Div(
                        id="ep-canvas-wrapper",
                        children=[
                            dmc.Group([
                                # Regla vertical
                                html.Div(
                                    id="ep-vertical-ruler",
                                    className="vertical-ruler",
                                    style={
                                        "height": f"{A4_PORTRAIT_HEIGHT * SCALE_FACTOR}px",
                                        "width": "20px",
                                        "background": "#f5f5f5",
                                        "position": "relative",
                                        "borderRight": "1px solid #ccc"
                                    },
                                    children=[
                                        html.Div(
                                            className="ruler-mark",
                                            style={
                                                "position": "absolute",
                                                "left": "0",
                                                "top": f"{i * 100 * SCALE_FACTOR}px",
                                                "width": "20px",
                                                "borderTop": "1px solid #999",
                                                "textAlign": "center",
                                                "fontSize": "8px",
                                                "paddingTop": "2px"
                                            },
                                            children=f"{i}"
                                        ) for i in range(9)
                                    ]
                                ),

                                html.Div([
                                    # Regla horizontal
                                    html.Div(
                                        id="ep-horizontal-ruler",
                                        className="horizontal-ruler",
                                        style={
                                            "width": f"{A4_PORTRAIT_WIDTH * SCALE_FACTOR}px",
                                            "height": "20px",
                                            "background": "#f5f5f5",
                                            "position": "relative",
                                            "borderBottom": "1px solid #ccc"
                                        },
                                        children=[
                                            html.Div(
                                                className="ruler-mark",
                                                style={
                                                    "position": "absolute",
                                                    "top": "0",
                                                    "left": f"{i * 100 * SCALE_FACTOR}px",
                                                    "height": "20px",
                                                    "borderLeft": "1px solid #999",
                                                    "textAlign": "center",
                                                    "fontSize": "8px",
                                                    "paddingLeft": "2px"
                                                },
                                                children=f"{i}"
                                            ) for i in range(6)
                                        ]
                                    ),

                                    # Canvas (área de diseño A4)
                                    html.Div(
                                        id="ep-canvas-container",
                                        style={
                                            "width": f"{A4_PORTRAIT_WIDTH * SCALE_FACTOR}px",
                                            "height": f"{A4_PORTRAIT_HEIGHT * SCALE_FACTOR}px",
                                            "background": "white",
                                            "border": "1px solid #ccc",
                                            "position": "relative",
                                            "boxShadow": "0 4px 8px rgba(0,0,0,0.1)"
                                        },
                                        # Aquí se renderizarán las líneas y otros elementos
                                        children=[]
                                    )
                                ])
                            ], ta="start", gap="1"),
                        ]
                    ),

                    # Estado de la edición
                    dmc.Alert(id='ep-canvas-status', title="", c="blue", hide=True)
                ]
            ),

            # Download component for PDF
            dcc.Download(id="ep-download-pdf")

        ], fluid=True)
    )


def register_callbacks(app):
    # Combinar ambos callbacks para actualizar estilo y contenido del canvas
    @app.callback(
        [Output("ep-canvas-container", "style"),
         Output("ep-horizontal-ruler", "style"),
         Output("ep-horizontal-ruler", "children"),
         Output("ep-vertical-ruler", "style"),
         Output("ep-vertical-ruler", "children"),
         Output("ep-canvas-container", "children")],
        [Input("ep-orientation-selector", "value"),
         Input("store-componentes", "data")]
    )
    def update_canvas(orientation, store_data):
        # Parte 1: Actualizar orientación y reglas (sin cambios)
        (canvas_style, horizontal_ruler_style, horizontal_marks, vertical_ruler_style,
         vertical_marks) = actualizar_orientacion_y_reglas(orientation)

        # Guardar la orientación en la configuración
        store_data['configuracion']['orientacion'] = orientation

        # Parte 2: Renderizar elementos en el canvas
        elementos_canvas = []

        # Función para convertir cm a píxeles escalados
        def cm_a_px(cm_value):
            return cm_value * CM_TO_POINTS * SCALE_FACTOR

        # Procesar cada elemento
        # Procesar cada elemento
        for elemento in store_data['elementos']:
            # Procesar según el tipo de elemento
            if elemento['tipo'] == 'linea':
                # Calcular puntos de inicio y fin en píxeles
                x1_px = cm_a_px(elemento["x1"])
                y1_px = cm_a_px(elemento["y1"])
                x2_px = cm_a_px(elemento["x2"])
                y2_px = cm_a_px(elemento["y2"])

                # Calcular longitud y ángulo para CSS
                import math
                dx = x2_px - x1_px
                dy = y2_px - y1_px
                longitud = math.sqrt(dx ** 2 + dy ** 2)
                angulo = math.atan2(dy, dx) * 180 / math.pi

                # Crear elemento div para la línea
                linea_element = html.Div(
                    id=f"elemento-{elemento['id']}",
                    style={
                        "position": "absolute",
                        "left": f"{x1_px}px",
                        "top": f"{y1_px}px",
                        "width": f"{longitud}px",
                        "height": f"{elemento['grosor']}px",
                        "backgroundColor": elemento["color"],
                        "transform": f"rotate({angulo}deg)",
                        "transformOrigin": "left top",
                        "zIndex": elemento.get("zIndex", 10),  # Usar zIndex si existe
                    },
                    title=elemento["nombre"],  # Mostrar nombre al pasar el ratón
                )

                elementos_canvas.append(linea_element)

            elif elemento['tipo'] == 'rectangulo':
                # Convertir coordenadas y dimensiones a píxeles
                x_px = cm_a_px(elemento["x"])
                y_px = cm_a_px(elemento["y"])
                ancho_px = cm_a_px(elemento["ancho"])
                alto_px = cm_a_px(elemento["alto"])

                # Calcular opacidad (0-1)
                opacidad = elemento.get("opacidad", 100) / 100

                # Crear elemento div para el rectángulo
                rect_element = html.Div(
                    id=f"elemento-{elemento['id']}",
                    style={
                        "position": "absolute",
                        "left": f"{x_px}px",
                        "top": f"{y_px}px",
                        "width": f"{ancho_px}px",
                        "height": f"{alto_px}px",
                        "backgroundColor": elemento["color_relleno"],
                        "opacity": opacidad,
                        "border": f"{elemento['grosor_borde']}px solid {elemento['color_borde']}",
                        "zIndex": elemento.get("zIndex", 5),  # Por defecto debajo de las líneas
                    },
                    title=elemento["nombre"],  # Mostrar nombre al pasar el ratón
                )

                elementos_canvas.append(rect_element)
            # Aquí se añadirán más tipos de elementos en el futuro (rectángulos, etc.)
            # elif elemento['tipo'] == 'rectangulo':
            #     ...

        return canvas_style, horizontal_ruler_style, horizontal_marks, vertical_ruler_style, vertical_marks, elementos_canvas

    # Callback para abrir el drawer de línea
    @app.callback(
        Output("drawer-line", "opened"),
        Input("ep-add-line-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def open_line_drawer(n_clicks):
        if n_clicks:
            return True
        return False

    # callback para crear/actualizar líneas
    @app.callback(
        [Output("store-componentes", "data"),
         Output("drawer-line", "opened", allow_duplicate=True),
         Output("ep-canvas-status", "children"),
         Output("ep-canvas-status", "color"),
         Output("ep-canvas-status", "hide")],
        Input("btn-create-line", "n_clicks"),
        State("line-selector", "value"),
        State("line-x1", "value"),
        State("line-y1", "value"),
        State("line-x2", "value"),
        State("line-y2", "value"),
        State("line-grosor", "value"),
        State("line-color", "value"),
        State("line-nombre", "value"),
        State("store-componentes", "data"),
        State("ep-orientation-selector", "value"),
        prevent_initial_call=True
    )
    def crear_actualizar_linea(n_clicks, selected_line_id, x1, y1, x2, y2, grosor, color, nombre,
                               store_data, orientacion):
        if not n_clicks:
            return store_data, False, "", "blue", True

        # Inicializar elementos si es necesario
        if 'elementos' not in store_data:
            store_data['elementos'] = []

        # Verificar si ya existe un elemento con el mismo nombre (excepto el que estamos editando)
        nombre_original = nombre
        contador = 1
        nombre_es_unico = False

        while not nombre_es_unico:
            nombre_es_unico = True
            for elemento in store_data['elementos']:
                # Si encontramos otro elemento con el mismo nombre (que no sea el que estamos editando)
                if (elemento["nombre"] == nombre and
                        (not selected_line_id or str(elemento["id"]) != selected_line_id)):
                    nombre_es_unico = False
                    # Generar un nuevo nombre
                    nombre = f"{nombre_original} ({contador})"
                    contador += 1
                    break

        # Crear línea con todos sus datos
        linea_datos = {
            "id": None,  # Se asignará después
            "tipo": "linea",
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "grosor": grosor,
            "color": color,
            "nombre": nombre,  # Nombre potencialmente modificado
            "zIndex": 10,  # Valor por defecto
            "creado": datetime.now().isoformat(),
            "visible": True
        }

        # Actualizar o crear línea
        if selected_line_id:
            # Buscar y actualizar la línea existente
            for i, elemento in enumerate(store_data['elementos']):
                if str(elemento["id"]) == selected_line_id and elemento["tipo"] == "linea":
                    # Mantener el ID original y otros campos que no se editan
                    linea_datos["id"] = elemento["id"]
                    linea_datos["zIndex"] = elemento.get("zIndex", 10)
                    linea_datos["creado"] = elemento.get("creado", linea_datos["creado"])
                    # Reemplazar el elemento
                    store_data['elementos'][i] = linea_datos
                    break
        else:
            # Crear una nueva línea con un nuevo ID
            # Encontrar el ID más alto actual y sumar 1
            max_id = 0
            for elemento in store_data['elementos']:
                if isinstance(elemento.get("id"), (int, float)) and elemento["id"] > max_id:
                    max_id = elemento["id"]

            linea_datos["id"] = max_id + 1
            store_data['elementos'].append(linea_datos)

        # Actualizar la orientación en la configuración
        store_data['configuracion']['orientacion'] = orientacion

        # Preparar mensaje de estado
        if nombre != nombre_original:
            mensaje = f"El nombre '{nombre_original}' ya existía. Se ha renombrado a '{nombre}'."
            color_estado = "yellow"
            ocultar_estado = False
        else:
            mensaje = f"Línea '{nombre}' guardada correctamente."
            color_estado = "green"
            ocultar_estado = False

        # Cerrar el drawer y retornar la store actualizada con mensaje
        return store_data, False, mensaje, color_estado, ocultar_estado

    # Callback para borrar la línea seleccionada
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("drawer-line", "opened", allow_duplicate=True),
         Output("line-selector", "value")],
        Input("btn-delete-line", "n_clicks"),
        State("line-selector", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def borrar_linea(n_clicks, selected_line_id, store_data):
        if not n_clicks or not selected_line_id:
            return store_data, True, None

        # Filtrar elementos para eliminar el seleccionado
        if 'elementos' in store_data:
            store_data['elementos'] = [
                elemento for elemento in store_data['elementos']
                if not (str(elemento["id"]) == selected_line_id and elemento["tipo"] == "linea")
            ]

        # Cerrar el drawer y limpiar la selección
        return store_data, False, None

    # Callback para abrir el drawer de rectángulo
    @app.callback(
        Output("ep-rectangle-drawer", "opened"),
        Input("ep-add-rectangle-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def open_rectangle_drawer(n_clicks):
        if n_clicks:
            return True
        return False

    # Callback para abrir el drawer de gráfico
    @app.callback(
        Output("ep-graph-drawer", "opened"),
        Input("ep-add-graph-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def open_graph_drawer(n_clicks):
        if n_clicks:
            return True
        return False

    # Callback para abrir el drawer de tabla
    @app.callback(
        Output("ep-table-drawer", "opened"),
        Input("ep-add-table-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def open_table_drawer(n_clicks):
        if n_clicks:
            return True
        return False

    # Callback para actualizar la lista de líneas en el selectbox de línea
    @app.callback(
        Output("line-selector", "data"),
        Input("store-componentes", "data")
    )
    def update_line_selector(store_data):
        if not store_data or 'elementos' not in store_data:
            return []

        # Crear opciones para el selector solo con las líneas
        options = [
            {"value": str(elemento["id"]), "label": elemento["nombre"]}
            for elemento in store_data['elementos']
            if elemento["tipo"] == "linea"
        ]

        return options

    # Callback para rellenar el formulario cuando se selecciona una línea
    @app.callback(
        [Output("line-x1", "value"),
         Output("line-y1", "value"),
         Output("line-x2", "value"),
         Output("line-y2", "value"),
         Output("line-grosor", "value"),
         Output("line-color", "value"),
         Output("line-nombre", "value")],
        Input("line-selector", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def fill_line_form(selected_line_id, store_data):
        if not selected_line_id or 'elementos' not in store_data:
            # Valores por defecto
            return 1.0, 1.0, 5.0, 5.0, 1, "#000000", "Línea 1"

        # Buscar la línea seleccionada
        for elemento in store_data['elementos']:
            if str(elemento["id"]) == selected_line_id and elemento["tipo"] == "linea":
                # Devolver los valores
                return (
                    elemento["x1"],
                    elemento["y1"],
                    elemento["x2"],
                    elemento["y2"],
                    elemento["grosor"],
                    elemento["color"],
                    elemento["nombre"]
                )

        # Si no se encuentra
        return 1.0, 1.0, 5.0, 5.0, 1, "#000000", "Línea 1"

    # callback para guardar los cambios en el store
    @app.callback(
        Output("store-componentes", "data", allow_duplicate=True),
        [Input("ep-template-name", "value"),
         Input("ep-orientation-selector", "value")],
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def update_config(template_name, orientation, store_data):
        # Inicializar la configuración si no existe
        if 'configuracion' not in store_data:
            store_data['configuracion'] = {}

        # Actualizar valores
        if template_name:
            store_data['configuracion']['nombre_plantilla'] = template_name
        store_data['configuracion']['orientacion'] = orientation

        # Opcional: añadir timestamp de última modificación
        store_data['configuracion']['ultima_modificacion'] = datetime.now().isoformat()

        return store_data


    # Callback para actualizar la lista de rectángulos en el selectbox
    @app.callback(
        Output("rectangle-selector", "data"),
        Input("store-componentes", "data")
    )
    def update_rectangle_selector(store_data):
        if not store_data or 'elementos' not in store_data:
            return []

        # Crear opciones para el selector solo con los rectángulos
        options = [
            {"value": str(elemento["id"]), "label": elemento["nombre"]}
            for elemento in store_data['elementos']
            if elemento["tipo"] == "rectangulo"
        ]

        return options


    # Callback para rellenar el formulario cuando se selecciona un rectángulo
    @app.callback(
        [Output("rectangle-x", "value"),
         Output("rectangle-y", "value"),
         Output("rectangle-width", "value"),
         Output("rectangle-height", "value"),
         Output("rectangle-border-width", "value"),
         Output("rectangle-border-color", "value"),
         Output("rectangle-fill-color", "value"),
         Output("rectangle-opacity", "value"),
         Output("rectangle-nombre", "value")],
        Input("rectangle-selector", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def fill_rectangle_form(selected_rectangle_id, store_data):
        if not selected_rectangle_id or 'elementos' not in store_data:
            # Valores por defecto
            return 1.0, 1.0, 5.0, 3.0, 1, "#000000", "#FFFFFF", 100, "Rectángulo 1"

        # Buscar el rectángulo seleccionado
        for elemento in store_data['elementos']:
            if str(elemento["id"]) == selected_rectangle_id and elemento["tipo"] == "rectangulo":
                # Devolver los valores
                return (
                    elemento["x"],
                    elemento["y"],
                    elemento["ancho"],
                    elemento["alto"],
                    elemento["grosor_borde"],
                    elemento["color_borde"],
                    elemento["color_relleno"],
                    elemento.get("opacidad", 100),  # Por si no existe en elementos antiguos
                    elemento["nombre"]
                )

        # Si no se encuentra
        return 1.0, 1.0, 5.0, 3.0, 1, "#000000", "#FFFFFF", 100, "Rectángulo 1"


    # Callback para crear/actualizar rectángulos
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-rectangle-drawer", "opened", allow_duplicate=True),  # Añadir allow_duplicate=True aquí
         Output("ep-canvas-status", "children", allow_duplicate=True),
         Output("ep-canvas-status", "color", allow_duplicate=True),
         Output("ep-canvas-status", "hide", allow_duplicate=True)],
        Input("btn-create-rectangle", "n_clicks"),
        State("rectangle-selector", "value"),
        State("rectangle-x", "value"),
        State("rectangle-y", "value"),
        State("rectangle-width", "value"),
        State("rectangle-height", "value"),
        State("rectangle-border-width", "value"),
        State("rectangle-border-color", "value"),
        State("rectangle-fill-color", "value"),
        State("rectangle-opacity", "value"),
        State("rectangle-nombre", "value"),
        State("store-componentes", "data"),
        State("ep-orientation-selector", "value"),
        prevent_initial_call=True
    )
    def crear_actualizar_rectangulo(n_clicks, selected_id, x, y, ancho, alto, grosor_borde, color_borde,
                                    color_relleno, opacidad, nombre, store_data, orientacion):
        if not n_clicks:
            return store_data, False, "", "blue", True

        # Inicializar elementos si es necesario
        if 'elementos' not in store_data:
            store_data['elementos'] = []

        # Verificar si ya existe un elemento con el mismo nombre (excepto el que estamos editando)
        nombre_original = nombre
        contador = 1
        nombre_es_unico = False

        while not nombre_es_unico:
            nombre_es_unico = True
            for elemento in store_data['elementos']:
                # Si encontramos otro elemento con el mismo nombre (que no sea el que estamos editando)
                if (elemento["nombre"] == nombre and
                        (not selected_id or str(elemento["id"]) != selected_id)):
                    nombre_es_unico = False
                    # Generar un nuevo nombre
                    nombre = f"{nombre_original} ({contador})"
                    contador += 1
                    break

        # Crear rectángulo con todos sus datos
        rect_datos = {
            "id": None,  # Se asignará después
            "tipo": "rectangulo",
            "x": x,
            "y": y,
            "ancho": ancho,
            "alto": alto,
            "grosor_borde": grosor_borde,
            "color_borde": color_borde,
            "color_relleno": color_relleno,
            "opacidad": opacidad,
            "nombre": nombre,  # Nombre potencialmente modificado
            "zIndex": 5,  # Por defecto, debajo de las líneas
            "creado": datetime.now().isoformat(),
            "visible": True
        }

        # Actualizar o crear rectángulo
        if selected_id:
            # Buscar y actualizar el rectángulo existente
            for i, elemento in enumerate(store_data['elementos']):
                if str(elemento["id"]) == selected_id and elemento["tipo"] == "rectangulo":
                    # Mantener el ID original y otros campos que no se editan
                    rect_datos["id"] = elemento["id"]
                    rect_datos["zIndex"] = elemento.get("zIndex", 5)
                    rect_datos["creado"] = elemento.get("creado", rect_datos["creado"])
                    # Reemplazar el elemento
                    store_data['elementos'][i] = rect_datos
                    break
        else:
            # Crear un nuevo rectángulo con un nuevo ID
            # Encontrar el ID más alto actual y sumar 1
            max_id = 0
            for elemento in store_data['elementos']:
                if isinstance(elemento.get("id"), (int, float)) and elemento["id"] > max_id:
                    max_id = elemento["id"]

            rect_datos["id"] = max_id + 1
            store_data['elementos'].append(rect_datos)

        # Actualizar la orientación en la configuración
        store_data['configuracion']['orientacion'] = orientacion

        # Preparar mensaje de estado
        if nombre != nombre_original:
            mensaje = f"El nombre '{nombre_original}' ya existía. Se ha renombrado a '{nombre}'."
            color_estado = "yellow"
            ocultar_estado = False
        else:
            mensaje = f"Rectángulo '{nombre}' guardado correctamente."
            color_estado = "green"
            ocultar_estado = False

        # Cerrar el drawer y retornar la store actualizada con mensaje
        return store_data, False, mensaje, color_estado, ocultar_estado


    # Callback para borrar el rectángulo seleccionado
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-rectangle-drawer", "opened", allow_duplicate=True),  # Añadir allow_duplicate=True aquí
         Output("rectangle-selector", "value")],
        Input("btn-delete-rectangle", "n_clicks"),
        State("rectangle-selector", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def borrar_rectangulo(n_clicks, selected_id, store_data):
        if not n_clicks or not selected_id:
            return store_data, True, None

        # Filtrar elementos para eliminar el seleccionado
        if 'elementos' in store_data:
            store_data['elementos'] = [
                elemento for elemento in store_data['elementos']
                if not (str(elemento["id"]) == selected_id and elemento["tipo"] == "rectangulo")
            ]

        # Cerrar el drawer y limpiar la selección
        return store_data, False, None

    # se genera el pdf a partir del canvas
    @app.callback(
        [Output("ep-canvas-status", "children", allow_duplicate=True),
         Output("ep-canvas-status", "color", allow_duplicate=True),
         Output("ep-canvas-status", "hide", allow_duplicate=True),
         Output("ep-download-pdf", "data")],
        Input("ep-print-pdf-btn", "n_clicks"),
        State("ep-template-name", "value"),
        State("store-componentes", "data"),
        State("ep-orientation-selector", "value"),
        prevent_initial_call=True
    )
    def generate_pdf(n_clicks, template_name, store_data, orientation):
        if not n_clicks:
            return "", "blue", True, None

        if not template_name:
            return "Por favor, ingrese un nombre para la plantilla", "red", False, None

        try:
            # Crear un buffer para el PDF
            buffer = io.BytesIO()

            # Configurar el tamaño de página según la orientación
            page_size = landscape(A4) if orientation == "landscape" else A4
            page_width, page_height = page_size

            # Crear el PDF
            pdf = canvas.Canvas(buffer, pagesize=page_size)
            pdf.setTitle(f"Plantilla: {template_name}")

            # Actualizar configuración en el store
            store_data['configuracion']['nombre_plantilla'] = template_name
            store_data['configuracion']['orientacion'] = orientation

            # Dibujar cada elemento según su tipo
            if 'elementos' in store_data:
                for elemento in store_data['elementos']:
                    try:
                        # Procesar según el tipo
                        # líneas
                        if elemento["tipo"] == "linea" and elemento.get("visible", True):
                            # Verificar campos requeridos
                            required_fields = ["x1", "y1", "x2", "y2", "grosor", "color"]
                            if not all(field in elemento for field in required_fields):
                                continue

                            # Convertir coordenadas de cm a puntos
                            x1 = elemento["x1"] * CM_TO_POINTS
                            y1 = elemento["y1"] * CM_TO_POINTS
                            x2 = elemento["x2"] * CM_TO_POINTS
                            y2 = elemento["y2"] * CM_TO_POINTS

                            # Ajustar coordenadas por cambio de orientación si es necesario
                            # (Este código se mantiene igual que el original)

                            # En PDF, el origen (0,0) está en la esquina inferior izquierda
                            y1 = page_height - y1
                            y2 = page_height - y2

                            # Configurar el color y grosor
                            pdf.setStrokeColor(elemento["color"])
                            pdf.setLineWidth(elemento["grosor"])

                            # Dibujar la línea
                            pdf.line(x1, y1, x2, y2)
                        # rectángulos
                        elif elemento["tipo"] == "rectangulo" and elemento.get("visible", True):
                            # Verificar campos requeridos
                            required_fields = ["x", "y", "ancho", "alto", "grosor_borde", "color_borde",
                                               "color_relleno"]
                            if not all(field in elemento for field in required_fields):
                                continue

                            # Convertir coordenadas de cm a puntos
                            x = elemento["x"] * CM_TO_POINTS
                            y = elemento["y"] * CM_TO_POINTS
                            ancho = elemento["ancho"] * CM_TO_POINTS
                            alto = elemento["alto"] * CM_TO_POINTS

                            # En PDF, el origen (0,0) está en la esquina inferior izquierda
                            y = page_height - y - alto  # Ajustar Y para dibujar desde la esquina superior izquierda

                            # Configurar color y grosor de borde
                            pdf.setStrokeColor(elemento["color_borde"])
                            pdf.setLineWidth(elemento["grosor_borde"])

                            # Configurar relleno
                            pdf.setFillColor(elemento["color_relleno"])
                            opacidad = elemento.get("opacidad", 100) / 100

                            # Dibujar el rectángulo
                            pdf.rect(x, y, ancho, alto, fill=(opacidad > 0), stroke=(elemento["grosor_borde"] > 0))


                        # Aquí se añadirán otros tipos de elementos
                        #     ...

                    except Exception as e:
                        # Si hay un error con un elemento, continuar
                        continue

            pdf.save()
            buffer.seek(0)

            # Retornar los datos para la descarga
            return ("PDF generado con éxito", "green", False,
                    dcc.send_bytes(buffer.getvalue(), f"{template_name}.pdf"))

        except Exception as e:
            return f"Error al generar PDF: {e}", "red", False, None
# /pages/configuracion_plantilla_claude.py
import dash
from dash import html, dcc, callback
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
from dash_mantine_components import Prism  # Añade esta importación
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
                    'paginas': {
                        "1": {
                            'elementos': {},
                            'configuracion': {
                                'orientacion': 'portrait'
                            }
                        }
                    },
                    'pagina_actual': "1",
                    'seleccionado': None,
                    'configuracion': {
                        'nombre_plantilla': '',
                        'version': '1.0',
                        'num_paginas': 1
                    }
                }
            ),

            # Sección de configuración (tercio superior)
            dmc.Paper(p="md", withBorder=True, shadow="sm", radius="md", mb=20, children=[
                dmc.Grid([
                    # Primera fila - Configuración general
                    dmc.Col([
                        dmc.Group([
                            dmc.TextInput(
                                id="ep-template-name",
                                label="Nombre de la plantilla:",
                                placeholder="Informe de inclinómetro",
                                required=True,
                                style={"width": "300px"}
                            ),
                            dmc.Text("Orientación:", size="sm", pt=8, ml=20),
                            dmc.SegmentedControl(
                                id="ep-orientation-selector",
                                value="landscape",  # Cambiado a horizontal por defecto
                                data=[
                                    {"value": "portrait", "label": "Vertical"},
                                    {"value": "landscape", "label": "Horizontal"}
                                ],
                            ),
                            dmc.Group([
                                dmc.Text("Página:", size="sm", pt=8),
                                dmc.Select(
                                    id="ep-page-number",
                                    data=[{"value": "1", "label": "1"}],  # Comenzamos con solo una página
                                    value="1",
                                    clearable=False,
                                    style={"width": "80px"}
                                ),
                                dmc.Text("de", size="sm", pt=8),
                                dmc.Text(id="ep-total-pages", size="sm", pt=8),
                                dmc.Button(
                                    "←",
                                    id="ep-prev-page-btn",
                                    variant="outline",
                                    compact=True
                                ),
                                dmc.Button(
                                    "→",
                                    id="ep-next-page-btn",
                                    variant="outline",
                                    compact=True
                                ),
                                dmc.Button(
                                    "Añadir página",
                                    id="ep-add-page-btn",
                                    leftSection=DashIconify(icon="mdi:file-plus-outline"),
                                    variant="outline",
                                    c="blue"
                                ),
                            ], justify="flex-end", gap="1"),
                        ], justify="flex-start", gap="1"),
                    ], span=12, mb=10),

                    # NUEVA FILA - Área para arrastrar y soltar archivos JSON
                    dmc.Col([
                        dcc.Upload(
                            id='ep-upload-json',
                            children=dmc.Paper(
                                children=[
                                    dmc.Group([
                                        DashIconify(icon="mdi:file-upload-outline", width=24, height=24),
                                        html.Div([
                                            "Arrastra y suelta un archivo JSON aquí",
                                            html.Br(),
                                            "o haz clic para seleccionarlo"
                                        ])
                                    ], justify="center", gap="1"),  # Sin el direction="row"
                                ],
                                p="md",
                                withBorder=True,
                                shadow="xs",
                                radius="md",
                                style={"backgroundColor": "#f8f9fa"},
                            ),
                            style={
                                'width': '100%',
                                'height': '100px',
                                'cursor': 'pointer'
                            },
                            multiple=False,
                            accept=".json"
                        ),
                    ], span=12, mb=20),

                    # Tercera fila - Botones de elementos (corregido el duplicado)
                    dmc.Col([
                        dmc.Group([
                            dmc.Button(
                                "Guardar JSON",
                                id="ep-save-json-btn",
                                leftSection=DashIconify(icon="mdi:file-download-outline"),
                                variant="outline",
                                c="blue"
                            ),
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
                                "Añadir texto",
                                id="ep-add-text-btn",
                                leftSection=DashIconify(icon="mdi:text"),
                                variant="outline"
                            ),
                            dmc.Button(
                                "Añadir imagen",
                                id="ep-add-image-btn",
                                leftSection=DashIconify(icon="mdi:image-outline"),
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
                                                            step=0.01,
                                                            precision=2,
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
                                                            step=0.01,
                                                            precision=2,
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
                                                            step=0.01,
                                                            precision=2,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        ),
                                                        style={"paddingLeft": "15px", "paddingRight": "15px"}
                                                    ),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="line-y2",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
                                                            value=1.0,
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
                            # Columna 2: Propiedades de línea (reorganizado en filas)
                            dmc.Col([
                                dmc.Text("Propiedades de Línea", fw="bold", ta="center", mb=15),

                                # Fila para Grosor
                                dmc.Grid([
                                    dmc.Col([
                                        dmc.Text("Grosor de línea (px):", size="sm", fw="bold", pt=8),
                                    ], span=5),
                                    dmc.Col([
                                        dmc.NumberInput(
                                            id="line-grosor",
                                            min=0.1,
                                            max=10,
                                            step=0.1,
                                            precision=1,
                                            value=1,
                                            style={"width": "100%"}
                                        ),
                                    ], span=7),
                                ], mb=10),

                                # Fila para Color
                                dmc.Grid([
                                    dmc.Col([
                                        dmc.Text("Color de línea:", size="sm", fw="bold", pt=8),
                                    ], span=5),
                                    dmc.Col([
                                        dmc.ColorInput(
                                            id="line-color",
                                            value="#000000",
                                            format="hex",
                                            swatches=[
                                                "#000000", "#FF0000", "#00FF00", "#0000FF",
                                                "#FFFF00", "#00FFFF", "#FF00FF", "#C0C0C0"
                                            ],
                                            style={"width": "100%"}
                                        ),
                                    ], span=7),
                                ], mb=10),

                                # Fila para Z-Index
                                dmc.Grid([
                                    dmc.Col([
                                        dmc.Text("Orden (Z-Index):", size="sm", fw="bold", pt=8),
                                    ], span=5),
                                    dmc.Col([
                                        dmc.Grid([
                                            dmc.Col([
                                                dmc.NumberInput(
                                                    id="line-zindex",
                                                    min=1,
                                                    max=100,
                                                    step=1,
                                                    value=10,
                                                    style={"width": "100%"}
                                                ),
                                            ], span=7),
                                            dmc.Col([
                                                dmc.Text("Mayor = encima", size="xs", pt=8, c="gray"),
                                            ], span=5),
                                        ], gutter="xs"),
                                    ], span=7),
                                ]),

                                # Información adicional
                                dmc.Space(h=15),
                                dmc.Alert(
                                    title="Consejo",
                                    c="blue",
                                    children=[
                                        "Puedes ajustar el grosor con precisión de 0.1 y las coordenadas con precisión de 0.01 para un posicionamiento exacto."
                                    ],
                                    icon=[DashIconify(icon="mdi:information-outline")],
                                    withCloseButton=False
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
                                                            step=0.01,
                                                            precision=2,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        )
                                                    ),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="rectangle-y",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
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
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        )
                                                    ),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="rectangle-height",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
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
                                                step=0.1,
                                                precision=1,
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
                                ]),
                                # Fila de Z-Index - Nueva adición
                                dmc.Grid([
                                    # Título (1/4)
                                    dmc.Col([
                                        dmc.Text("Orden:", fw="bold", size="sm", ta="left", pt=8),
                                    ], span=3, style={"paddingLeft": "10px"}),

                                    # Controles (3/4)
                                    dmc.Col([
                                        dmc.Group([
                                            dmc.Text("Z-Index:", size="sm", pt=8, style={"minWidth": "55px"}),
                                            dmc.NumberInput(
                                                id="rectangle-zindex",
                                                min=1,
                                                max=100,
                                                step=1,
                                                value=5,
                                                style={"width": "85px"}
                                            ),
                                            dmc.Text("(Mayor valor = encima)", size="xs", pt=8, c="gray")
                                        ], justify="flex-start", gap="1", style={"width": "100%"})
                                    ], span=9)
                                ], mb=10),
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
                # Drawer texto
                dmc.Drawer(
                    id="ep-text-drawer",
                    title=html.Span("Configurar Texto", style={"fontWeight": "bold"}),
                    opened=False,
                    position="top",
                    children=[
                        # Selector de textos existentes
                        dmc.Group([
                            dmc.Text("Seleccionar texto existente:", size="sm", pt=8),
                            dmc.Select(
                                id="text-selector",
                                placeholder="Seleccionar para editar",
                                clearable=True,
                                data=[],
                                style={"width": "200px"}
                            )
                        ], justify="flex-start", gap="1", mb=15),

                        # Tres columnas principales
                        dmc.Grid([
                            # Columna 1: Posición y dimensiones
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
                                                            id="text-x",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        )
                                                    ),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="text-y",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
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
                                                            id="text-width",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
                                                            value=5.0,
                                                            style={"width": "80px"}
                                                        )
                                                    ),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="text-height",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
                                                            value=2.0,
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
                                ),

                                # Rotación
                                dmc.Group([
                                    dmc.Text("Rotación:", fw="bold", size="sm", pt=8),
                                    dmc.NumberInput(
                                        id="text-rotation",
                                        min=0,
                                        max=360,
                                        step=1,
                                        value=0,
                                        description="grados",
                                        style={"width": "120px"}
                                    )
                                ], justify="center", gap="1", mt=15),

                            ], span=4),

                            # Columna 2: Propiedades de texto
                            dmc.Col([
                                dmc.Text("Propiedades de texto", fw="bold", ta="center", mb=15),

                                # Familia de fuente
                                dmc.Select(
                                    id="text-font-family",
                                    label="Tipo de fuente:",
                                    placeholder="Seleccionar fuente",
                                    data=[
                                        {"value": "Helvetica", "label": "Helvetica"},
                                        {"value": "Times-Roman", "label": "Times Roman"},
                                        {"value": "Courier", "label": "Courier"}
                                    ],
                                    value="Helvetica",
                                    style={"marginBottom": "15px"}
                                ),

                                # Tamaño de fuente
                                dmc.Group([
                                    dmc.Text("Tamaño:", size="sm", fw="bold", pt=8),
                                    dmc.NumberInput(
                                        id="text-font-size",
                                        min=6,
                                        max=72,
                                        step=1,
                                        value=10,
                                        style={"width": "80px"}
                                    ),
                                    dmc.Text("pt", size="sm", pt=8),
                                ], justify="flex-start", gap="1", mb=15),

                                # Estilo de texto
                                dmc.Group([
                                    dmc.Text("Estilo:", size="sm", fw="bold", pt=8, style={"marginRight": "10px"}),
                                    dmc.SegmentedControl(
                                        id="text-font-weight",
                                        value="normal",
                                        data=[
                                            {"value": "normal", "label": "Normal"},
                                            {"value": "bold", "label": "Negrita"}
                                        ],
                                        size="xs"
                                    ),
                                    dmc.SegmentedControl(
                                        id="text-font-style",
                                        value="normal",
                                        data=[
                                            {"value": "normal", "label": "Normal"},
                                            {"value": "italic", "label": "Cursiva"}
                                        ],
                                        size="xs"
                                    ),
                                ], justify="flex-start", mb=15),

                                # Color de texto
                                dmc.Group([
                                    dmc.Text("Color:", size="sm", fw="bold", pt=8),
                                    dmc.ColorInput(
                                        id="text-color",
                                        value="#000000",
                                        format="hex",
                                        swatches=[
                                            "#000000", "#FF0000", "#00FF00", "#0000FF",
                                            "#FFFF00", "#00FFFF", "#FF00FF", "#C0C0C0"
                                        ],
                                        style={"width": "120px"}
                                    ),
                                ], justify="flex-start", gap="1", mb=15),

                                # Alineación horizontal (CORREGIDO)
                                dmc.Group([
                                    dmc.Text("Alineación:", size="sm", fw="bold", pt=8,
                                             style={"marginRight": "10px"}),
                                    dmc.SegmentedControl(
                                        id="text-align-h",
                                        value="left",
                                        data=[
                                            {"value": "left", "label": "Izq"},
                                            {"value": "center", "label": "Centro"},
                                            {"value": "right", "label": "Der"},
                                            {"value": "justify", "label": "Just"}
                                        ],
                                        size="xs"
                                    ),
                                ], justify="flex-start", mb=15),

                                # Alineación vertical (CORREGIDO)
                                dmc.Group([
                                    dmc.Text("Vertical:", size="sm", fw="bold", pt=8,
                                             style={"marginRight": "10px"}),
                                    dmc.SegmentedControl(
                                        id="text-align-v",
                                        value="top",
                                        data=[
                                            {"value": "top", "label": "Arriba"},
                                            {"value": "middle", "label": "Medio"},
                                            {"value": "bottom", "label": "Abajo"}
                                        ],
                                        size="xs"
                                    ),
                                ], justify="flex-start", mb=15),

                                # Z-Index
                                dmc.Group([
                                    dmc.Text("Z-Index:", size="sm", fw="bold", pt=8),
                                    dmc.NumberInput(
                                        id="text-zindex",
                                        min=1,
                                        max=100,
                                        step=1,
                                        value=20,
                                        style={"width": "80px"}
                                    ),
                                    dmc.Text("(Mayor valor = encima)", size="xs", pt=8, c="gray")
                                ], justify="flex-start", gap="1", mb=10),

                            ], span=4),

                            # Columna 3: Contenido y botones
                            dmc.Col([
                                # Nombre del identificador
                                html.Div(
                                    dmc.Group([
                                        dmc.Text("Nombre del identificador:", fw="bold", size="sm", pt=8),
                                        dmc.TextInput(
                                            id="text-nombre",
                                            placeholder="Texto 1",
                                            value="Texto 1",
                                            style={"width": "160px"}
                                        )
                                    ], justify="center", gap="1", mb=20),
                                    style={"display": "flex", "justifyContent": "center", "width": "100%"}
                                ),

                                # Contenido de texto
                                dmc.Text("Contenido del texto:", fw="bold", size="sm", mb=5),
                                dmc.Textarea(
                                    id="text-content",
                                    placeholder="Ingrese el texto aquí...",
                                    autosize=True,
                                    minRows=4,
                                    maxRows=10,
                                    style={"width": "100%", "marginBottom": "20px"}
                                ),

                                # Checkbox para mantener proporción
                                dmc.Checkbox(
                                    id="text-auto-adjust",
                                    label="Ajustar automáticamente el texto al contenedor",
                                    checked=True,
                                    mb=20
                                ),
                                # checkbox para definir si el texto será editable
                                dmc.Checkbox(
                                    id="text-editable",
                                    label="Texto editable en aplicaciones externas",
                                    checked=False,  # estado inicial
                                    mb=20
                                ),

                                # Botones de acción
                                html.Div(
                                    dmc.Stack([
                                        dmc.Button(
                                            "Crear/Actualizar",
                                            id="btn-create-text",
                                            variant="filled",
                                            c="blue",
                                            style={"width": "150px"}
                                        ),
                                        dmc.Space(h=10),
                                        dmc.Button(
                                            "Borrar",
                                            id="btn-delete-text",
                                            variant="filled",
                                            c="red",
                                            style={"width": "150px"}
                                        )
                                    ], gap="1", ta="center"),
                                    style={
                                        "display": "flex",
                                        "justifyContent": "center",
                                        "alignItems": "center"
                                    }
                                ),
                            ], span=4),
                        ]),
                    ]
                ),
                # Drawer imágenes
                dmc.Drawer(
                    id="ep-image-drawer",
                    title=html.Span("Configurar Imagen", style={"fontWeight": "bold"}),
                    opened=False,
                    position="top",
                    children=[
                        # Selector de imágenes existentes
                        dmc.Group([
                            dmc.Text("Seleccionar imagen existente:", size="sm", pt=8),
                            dmc.Select(
                                id="image-selector",
                                placeholder="Seleccionar para editar",
                                clearable=True,
                                data=[],
                                style={"width": "200px"}
                            )
                        ], justify="flex-start", gap="1", mb=15),

                        # Tres columnas principales
                        dmc.Grid([
                            # Columna 1: Posición y dimensiones
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
                                                            id="image-x",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        )
                                                    ),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="image-y",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
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
                                                            id="image-width",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        )
                                                    ),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="image-height",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
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
                                        style={"borderCollapse": "collapse", "width": "auto", "margin": "0 auto"}
                                    ),
                                    style={"display": "flex", "justifyContent": "center"}
                                )
                            ], span=4),

                            # Columna 2: Opciones de imagen (reorganizada)
                            dmc.Col([
                                dmc.Text("Opciones de imagen", fw="bold", ta="center", mb=15),

                                # Selector de archivo - Título y Upload en la misma línea
                                dmc.Grid([
                                    dmc.Col([
                                        dmc.Text("Seleccionar imagen:", size="sm", fw="bold", pt=10),
                                    ], span=4),
                                    dmc.Col([
                                        dcc.Upload(
                                            id='image-upload',
                                            children=dmc.Paper(
                                                children=[
                                                    dmc.Group([
                                                        DashIconify(icon="mdi:file-image-outline", width=22, height=22),
                                                        html.Div("Arrastra o haz clic", style={"fontSize": "13px"})
                                                    ], justify="center", gap="1"),
                                                ],
                                                p="xs",
                                                withBorder=True,
                                                shadow="xs",
                                                radius="md",
                                                style={"backgroundColor": "#f8f9fa", "cursor": "pointer"},
                                            ),
                                            style={
                                                'width': '100%',
                                                'height': '40px',  # Altura reducida
                                            },
                                            multiple=False,
                                            accept="image/*"
                                        ),
                                    ], span=8),
                                ], mb=10),

                                # URL de imagen
                                dmc.Grid([
                                    dmc.Col([
                                        dmc.Text("URL de imagen:", size="sm", fw="bold", pt=10),
                                    ], span=4),
                                    dmc.Col([
                                        dmc.TextInput(
                                            id="image-url",
                                            placeholder="https://ejemplo.com/imagen.jpg",
                                            icon=DashIconify(icon="mdi:link-variant"),
                                            size="sm",
                                        ),
                                    ], span=8),
                                ], mb=10),

                                # Checkbox para mantener proporción
                                dmc.Checkbox(
                                    id="image-maintain-aspect-ratio",
                                    label="Mantener proporción de aspecto",
                                    checked=True,
                                ),
                                dmc.Space(h=15),

                                # Opacidad
                                dmc.Grid([
                                    dmc.Col([
                                        dmc.Text("Opacidad:", size="sm", fw="bold", pt=8),
                                    ], span=3),
                                    dmc.Col([
                                        dmc.Slider(
                                            id="image-opacity",
                                            min=0,
                                            max=100,
                                            step=5,
                                            value=100,
                                            marks=[
                                                {"value": 0, "label": "0%"},
                                                {"value": 100, "label": "100%"}
                                            ],
                                            style={"width": "100%"}
                                        ),
                                    ], span=9),
                                ], mb=15),

                                # Reducción y Z-Index en la misma línea
                                dmc.Grid([
                                    # Columna para Reducción
                                    dmc.Col([
                                        dmc.Text("Reducción:", size="sm", fw="bold", pt=8),
                                        dmc.Grid([
                                            dmc.Col([
                                                dmc.NumberInput(
                                                    id="image-reduction",
                                                    min=0,
                                                    max=50,
                                                    step=1,
                                                    value=0,
                                                    style={"width": "100%"}
                                                ),
                                            ], span=8),
                                            dmc.Col([
                                                dmc.Text("px", size="xs", pt=8, c="gray"),
                                            ], span=4),
                                        ], gutter="xs", style={"marginTop": "5px"}),
                                    ], span=6),

                                    # Columna para Z-Index
                                    dmc.Col([
                                        dmc.Text("Z-Index:", size="sm", fw="bold", pt=8),
                                        dmc.Grid([
                                            dmc.Col([
                                                dmc.NumberInput(
                                                    id="image-zindex",
                                                    min=1,
                                                    max=100,
                                                    step=1,
                                                    value=15,
                                                    style={"width": "100%"}
                                                ),
                                            ], span=8),
                                            dmc.Col([
                                                dmc.Text(">", size="xs", pt=8, c="gray"),
                                            ], span=4),
                                        ], gutter="xs", style={"marginTop": "5px"}),
                                    ], span=6),
                                ]),

                                # Tooltip informativo
                                dmc.Space(h=15),
                                dmc.Tooltip(
                                    label="Reducción: espacio en píxeles a reducir en cada borde para insertar en rectángulos. Z-Index: mayor valor = encima.",
                                    withArrow=True,
                                    width=300,
                                    multiline=True,
                                    children=[
                                        dmc.Badge(
                                            "Información sobre Reducción y Z-Index",
                                            size="sm",
                                            radius="sm",
                                            c="blue",
                                            leftSection=DashIconify(icon="mdi:information-outline", width=16),
                                            style={"width": "100%", "textAlign": "center"}
                                        ),
                                    ],
                                ),
                            ], span=4),

                            # Columna 3: Nombre y Botones
                            dmc.Col([
                                # Nombre centrado
                                html.Div(
                                    dmc.Group([
                                        dmc.Text("Nombre del identificador:", fw="bold", size="sm", pt=8),
                                        dmc.TextInput(
                                            id="image-nombre",
                                            placeholder="Imagen 1",
                                            value="Imagen 1",
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
                                            id="btn-create-image",
                                            variant="filled",
                                            c="blue",
                                            style={"width": "150px"}
                                        ),
                                        dmc.Space(h=10),
                                        dmc.Button(
                                            "Borrar",
                                            id="btn-delete-image",
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
                # Drawer para configurar gráficos
                dmc.Drawer(
                    id="ep-graph-drawer",
                    title=html.Span("Configurar Gráfico", style={"fontWeight": "bold"}),
                    opened=False,
                    position="top",
                    children=[
                        # Selector de gráficos existentes
                        dmc.Group([
                            dmc.Text("Seleccionar gráfico existente:", size="sm", pt=8),
                            dmc.Select(
                                id="graph-selector",
                                placeholder="Seleccionar para editar",
                                clearable=True,
                                data=[],
                                style={"width": "200px"}
                            )
                        ], justify="flex-start", gap="1", mb=15),

                        # Tres columnas principales
                        dmc.Grid([
                            # Columna 1: Posición y dimensiones
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
                                                            id="graph-x",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        )
                                                    ),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="graph-y",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
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
                                                            id="graph-width",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
                                                            value=8.0,
                                                            style={"width": "80px"}
                                                        )
                                                    ),
                                                    html.Td(
                                                        dmc.NumberInput(
                                                            id="graph-height",
                                                            min=0,
                                                            max=30,
                                                            step=0.01,
                                                            precision=2,
                                                            value=6.0,
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

                            # Columna 2: Configuración del gráfico
                            dmc.Col([
                                dmc.Text("Configuración del gráfico", fw="bold", ta="center", mb=15),

                                # Script que realiza el gráfico
                                dmc.TextInput(
                                    id="graph-script",
                                    label="Nombre del script gráfico:",
                                    placeholder="nombre_grafico.py",
                                    style={"marginBottom": "15px"}
                                ),

                                # Formato de imagen - NUEVA FUNCIONALIDAD
                                dmc.Text("Formato imagen:", size="sm", fw="bold", mb=5),
                                dmc.Select(
                                    id="graph-format",
                                    data=[
                                        {"value": "svg", "label": "SVG"},
                                        {"value": "png", "label": "PNG"}
                                    ],
                                    value="svg",
                                    clearable=False,
                                    style={"width": "100%", "marginBottom": "15px"}
                                ),

                                # textarea para introducir los campos de parámetros
                                dmc.Text("Parámetros del gráfico", fw="bold", size="sm", mb=10),
                                dmc.Textarea(
                                    id="graph-parameters",
                                    placeholder='"sensor": "desp_a",\n"fecha_i": "2025/06/05",\n"mostrar_titulo": true,\n"valor_numerico": 123',
                                    description="Introduce los parámetros en formato JSON válido (sin llaves exteriores)",
                                    autosize=True,
                                    minRows=4,
                                    maxRows=8,
                                    style={"width": "100%", "marginBottom": "15px"}
                                ),
                                dmc.Alert(
                                    title="Formato de parámetros",
                                    c="blue",
                                    children=[
                                        "Introduce los parámetros como pares clave-valor separados por comas:",
                                        html.Br(),
                                        html.Code('"clave": "valor_texto"'),
                                        " para textos",
                                        html.Br(),
                                        html.Code('"clave": true'),
                                        " o ",
                                        html.Code('"clave": false'),
                                        " para booleanos",
                                        html.Br(),
                                        html.Code('"clave": 123'),
                                        " para números",
                                        html.Br(),
                                        html.Br(),
                                        "Ejemplo:",
                                        html.Br(),
                                        html.Code('"sensor": "desp_a", "mostrar_titulo": true, "dpi": 600'),
                                    ],
                                    icon=[DashIconify(icon="mdi:information-outline")],
                                    withCloseButton=False,
                                    style={"marginBottom": "15px"}
                                ),

                                # Opacidad
                                dmc.Grid([
                                    dmc.Col([
                                        dmc.Text("Opacidad:", size="sm", fw="bold", pt=8),
                                    ], span=3),
                                    dmc.Col([
                                        dmc.Slider(
                                            id="graph-opacity",
                                            min=0,
                                            max=100,
                                            step=5,
                                            value=100,
                                            marks=[
                                                {"value": 0, "label": "0%"},
                                                {"value": 100, "label": "100%"}
                                            ],
                                            style={"width": "100%"}
                                        ),
                                    ], span=9),
                                ], mb=15),

                                # Reducción y Z-Index en la misma línea
                                dmc.Grid([
                                    # Columna para Reducción
                                    dmc.Col([
                                        dmc.Text("Reducción:", size="sm", fw="bold", pt=8),
                                        dmc.Grid([
                                            dmc.Col([
                                                dmc.NumberInput(
                                                    id="graph-reduction",
                                                    min=0,
                                                    max=50,
                                                    step=1,
                                                    value=1,
                                                    style={"width": "100%"}
                                                ),
                                            ], span=8),
                                            dmc.Col([
                                                dmc.Text("px", size="xs", pt=8, c="gray"),
                                            ], span=4),
                                        ], gutter="xs", style={"marginTop": "5px"}),
                                    ], span=6),

                                    # Columna para Z-Index
                                    dmc.Col([
                                        dmc.Text("Z-Index:", size="sm", fw="bold", pt=8),
                                        dmc.Grid([
                                            dmc.Col([
                                                dmc.NumberInput(
                                                    id="graph-zindex",
                                                    min=1,
                                                    max=100,
                                                    step=1,
                                                    value=25,
                                                    style={"width": "100%"}
                                                ),
                                            ], span=8),
                                            dmc.Col([
                                                dmc.Text(">", size="xs", pt=8, c="gray"),
                                            ], span=4),
                                        ], gutter="xs", style={"marginTop": "5px"}),
                                    ], span=6),
                                ]),

                            ], span=4),

                            # Columna 3: Nombre y Botones
                            dmc.Col([
                                # Nombre centrado
                                html.Div(
                                    dmc.Group([
                                        dmc.Text("Nombre del identificador:", fw="bold", size="sm", pt=8),
                                        dmc.TextInput(
                                            id="graph-nombre",
                                            placeholder="Gráfico 1",
                                            value="Gráfico 1",
                                            style={"width": "160px"}
                                        )
                                    ], justify="center", gap="1", mb=20),
                                    style={"display": "flex", "justifyContent": "center", "width": "100%"}
                                ),

                                # Información de uso
                                dmc.Alert(
                                    id="graph-info",
                                    title="Información",
                                    c="blue",
                                    children=[
                                        "Este gráfico se generará desde una aplicación externa. ",
                                        "Aquí solo se define su posición y parámetros básicos."
                                    ],
                                    icon=[DashIconify(icon="mdi:information-outline")],
                                    withCloseButton=False,
                                    style={"marginBottom": "20px"}
                                ),

                                # Botones centrados verticalmente
                                html.Div(
                                    dmc.Stack([
                                        dmc.Button(
                                            "Crear/Actualizar",
                                            id="btn-create-graph",
                                            variant="filled",
                                            c="blue",
                                            style={"width": "150px"}
                                        ),
                                        dmc.Space(h=10),
                                        dmc.Button(
                                            "Borrar",
                                            id="btn-delete-graph",
                                            variant="filled",
                                            c="red",
                                            style={"width": "150px"}
                                        )
                                    ], gap="1", ta="center"),
                                    style={
                                        "display": "flex",
                                        "justifyContent": "center",
                                        "alignItems": "center",
                                        "marginTop": "20px"
                                    }
                                )
                            ], span=4),
                        ]),
                    ]
                ),

                # Resto de drawers para configurar
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
            # Modal para guardar JSON
            dmc.Modal(
                id="modal-save-json",
                title="Guardar plantilla JSON",
                centered=True,
                children=[
                    dmc.Text("Introduzca el nombre del archivo JSON:", mb=10),
                    dmc.TextInput(
                        id="json-filename-input",
                        placeholder="nombre_plantilla",
                        required=True,
                        mb=15
                    ),
                    dmc.Group([
                        dmc.Button(
                            "Cancelar",
                            id="btn-cancel-save-json",
                            variant="outline",
                            c="red"
                        ),
                        dmc.Button(
                            "Guardar",
                            id="btn-confirm-save-json",
                            variant="filled",
                            c="blue"
                        )
                    ], justify="flex-end")
                ]
            ),

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
            dcc.Download(id="ep-download-pdf"),
            # Download component for JSON
            dcc.Download(id="ep-download-json"),
            # Visualizador de JSON del dcc.Store
            html.Div([
                dmc.Text("Contenido del Store:", fw=500, mb=5, mt=15),
                dmc.Card(
                    children=[
                        dmc.Prism(
                            id="json-viewer",
                            language="json",
                            withLineNumbers=True,
                            copyLabel="Copiar",
                            copiedLabel="¡Copiado!",
                            style={"maxHeight": "400px", "overflow": "auto"},
                            children=""  # Añadir un string vacío como contenido inicial
                        )
                    ],
                    withBorder=True,
                    shadow="sm",
                    p="xs"
                )
            ], style={"marginTop": "20px"})

        ], fluid=True)
    )


def register_callbacks(app):
    # Actualizar el contenido del canvas
    @app.callback(
        [Output("ep-canvas-container", "style"),
         Output("ep-horizontal-ruler", "style"),
         Output("ep-horizontal-ruler", "children"),
         Output("ep-vertical-ruler", "style"),
         Output("ep-vertical-ruler", "children"),
         Output("ep-canvas-container", "children")],
        [Input("ep-orientation-selector", "value"),
         Input("store-componentes", "data"),
         Input("ep-page-number", "value")]
    )
    def update_canvas(orientation, store_data, current_page):
        page_key = str(current_page)

        # Obtener la orientación específica de la página
        if page_key in store_data['paginas'] and "configuracion" in store_data['paginas'][page_key]:
            page_orientation = store_data['paginas'][page_key]["configuracion"].get("orientacion", orientation)
        else:
            page_orientation = orientation

        # Actualizar la orientación en el store
        if page_key not in store_data['paginas']:
            store_data['paginas'][page_key] = {
                "elementos": {},
                "configuracion": {
                    "orientacion": page_orientation
                }
            }
        elif "configuracion" not in store_data['paginas'][page_key]:
            store_data['paginas'][page_key]["configuracion"] = {
                "orientacion": page_orientation
            }
        else:
            store_data['paginas'][page_key]["configuracion"]["orientacion"] = page_orientation

        # Actualizar orientación y reglas
        (canvas_style, horizontal_ruler_style, horizontal_marks, vertical_ruler_style,
         vertical_marks) = actualizar_orientacion_y_reglas(page_orientation)

        # Resto del código de renderizado de elementos...
        elementos_canvas = []

        # Verificar si la página existe
        if page_key in store_data['paginas'] and "elementos" in store_data['paginas'][page_key]:
            # Obtener los elementos de la página actual
            elementos_pagina = store_data['paginas'][page_key]['elementos']

            # Función para convertir cm a píxeles escalados
            def cm_a_px(cm_value):
                return cm_value * CM_TO_POINTS * SCALE_FACTOR

            # Recorrer diccionario de elementos
            for nombre, elemento in elementos_pagina.items():

                if elemento['tipo'] == 'linea':
                    # Acceder a la nueva estructura
                    x1_px = cm_a_px(elemento["geometria"]["x1"])
                    y1_px = cm_a_px(elemento["geometria"]["y1"])
                    x2_px = cm_a_px(elemento["geometria"]["x2"])
                    y2_px = cm_a_px(elemento["geometria"]["y2"])

                    # Cálculos de longitud y ángulo
                    import math
                    dx = x2_px - x1_px
                    dy = y2_px - y1_px
                    longitud = math.sqrt(dx ** 2 + dy ** 2)
                    angulo = math.atan2(dy, dx) * 180 / math.pi

                    # Crear elemento div
                    linea_element = html.Div(
                        id=f"elemento-{nombre}",  # Usar nombre en lugar de ID
                        style={
                            "position": "absolute",
                            "left": f"{x1_px}px",
                            "top": f"{y1_px}px",
                            "width": f"{longitud}px",
                            "height": f"{elemento['estilo']['grosor']}px",
                            "backgroundColor": elemento["estilo"]["color"],
                            "transform": f"rotate({angulo}deg)",
                            "transformOrigin": "left top",
                            "zIndex": elemento["metadata"]["zIndex"],
                        },
                        title=nombre,  # Mostrar nombre al pasar el ratón
                    )

                    elementos_canvas.append(linea_element)

                elif elemento['tipo'] == 'rectangulo':
                    # Nueva estructura para rectángulos
                    x_px = cm_a_px(elemento["geometria"]["x"])
                    y_px = cm_a_px(elemento["geometria"]["y"])
                    ancho_px = cm_a_px(elemento["geometria"]["ancho"])
                    alto_px = cm_a_px(elemento["geometria"]["alto"])

                    # Calcular opacidad
                    opacidad = elemento["estilo"]["opacidad"] / 100

                    # Crear elemento div para el rectángulo
                    rect_element = html.Div(
                        id=f"elemento-{nombre}",
                        style={
                            "position": "absolute",
                            "left": f"{x_px}px",
                            "top": f"{y_px}px",
                            "width": f"{ancho_px}px",
                            "height": f"{alto_px}px",
                            "backgroundColor": elemento["estilo"]["color_relleno"],
                            "opacity": opacidad,
                            "border": f"{elemento['estilo']['grosor_borde']}px solid {elemento['estilo']['color_borde']}",
                            "zIndex": elemento["metadata"]["zIndex"],
                        },
                        title=nombre,
                    )

                    elementos_canvas.append(rect_element)

                # visualización de imágenes en el canvas
                elif elemento['tipo'] == 'imagen':
                    # Estructura para imágenes
                    x_px = cm_a_px(elemento["geometria"]["x"])
                    y_px = cm_a_px(elemento["geometria"]["y"])
                    ancho_px = cm_a_px(elemento["geometria"]["ancho"])
                    alto_px = cm_a_px(elemento["geometria"]["alto"])

                    # Obtener datos base64 y opacidad
                    img_src = elemento["imagen"]["datos_temp"]
                    opacidad = elemento["estilo"]["opacidad"] / 100

                    # Crear elemento img para la imagen
                    if img_src:
                        # Obtener reducción
                        reduccion_px = elemento["estilo"].get("reduccion", 0) * SCALE_FACTOR

                        # Aplicar reducción al tamaño y posición
                        x_ajustado = x_px + reduccion_px
                        y_ajustado = y_px + reduccion_px
                        ancho_ajustado = ancho_px - (reduccion_px * 2)
                        alto_ajustado = alto_px - (reduccion_px * 2)

                        img_element = html.Img(
                            id=f"elemento-{nombre}",
                            src=img_src,
                            style={
                                "position": "absolute",
                                "left": f"{x_ajustado}px",
                                "top": f"{y_ajustado}px",
                                "width": f"{ancho_ajustado}px",
                                "height": f"{alto_ajustado}px",
                                "opacity": opacidad,
                                "zIndex": elemento["metadata"]["zIndex"],
                                "objectFit": "fill" if not elemento["estilo"]["mantener_proporcion"] else "contain"
                            },
                            title=nombre,
                        )
                    else:
                        # Obtener reducción
                        reduccion_px = elemento["estilo"].get("reduccion", 0) * SCALE_FACTOR

                        # Aplicar reducción al tamaño y posición
                        x_ajustado = x_px + reduccion_px
                        y_ajustado = y_px + reduccion_px
                        ancho_ajustado = ancho_px - (reduccion_px * 2)
                        alto_ajustado = alto_px - (reduccion_px * 2)

                        # Mostrar un placeholder si no hay imagen
                        img_element = html.Div(
                            id=f"elemento-{nombre}",
                            children=[
                                DashIconify(icon="mdi:image-off", width=48, height=48),
                                html.Div("Imagen no encontrada", style={"fontSize": "10px"})
                            ],
                            style={
                                "position": "absolute",
                                "left": f"{x_ajustado}px",
                                "top": f"{y_ajustado}px",
                                "width": f"{ancho_ajustado}px",
                                "height": f"{alto_ajustado}px",
                                "backgroundColor": "#f0f0f0",
                                "border": "1px dashed #999",
                                "display": "flex",
                                "flexDirection": "column",
                                "justifyContent": "center",
                                "alignItems": "center",
                                "color": "#666",
                                "zIndex": elemento["metadata"]["zIndex"],
                            },
                            title=f"{nombre} - No encontrada",
                        )

                    elementos_canvas.append(img_element)
                # Para elementos tipo texto
                elif elemento['tipo'] == 'texto':
                    # Estructura para textos
                    x_px = cm_a_px(elemento["geometria"]["x"])
                    y_px = cm_a_px(elemento["geometria"]["y"])
                    ancho_px = cm_a_px(elemento["geometria"]["ancho"])
                    alto_px = cm_a_px(elemento["geometria"]["alto"])

                    # Configuración de estilo
                    estilo_elemento = elemento["estilo"]
                    familia_fuente = estilo_elemento["familia_fuente"]
                    tamano_fuente = estilo_elemento["tamano"]
                    color_texto = estilo_elemento["color"]
                    negrita = "bold" if estilo_elemento["negrita"] == "bold" else "normal"
                    cursiva = "italic" if estilo_elemento["cursiva"] == "italic" else "normal"
                    alineacion_h = estilo_elemento["alineacion_h"]
                    alineacion_v = estilo_elemento["alineacion_v"]
                    rotacion = estilo_elemento.get("rotacion", 0)

                    # Obtener el texto y si se ajusta automáticamente
                    texto = elemento["contenido"]["texto"] or ""
                    ajuste_automatico = elemento["contenido"]["ajuste_automatico"]

                    # Mapear alineación vertical a flex-align
                    align_map = {
                        "top": "flex-start",
                        "middle": "center",
                        "bottom": "flex-end"
                    }

                    # Mapear alineación horizontal
                    text_align = alineacion_h

                    # Calcular estilos de texto
                    texto_element = html.Div(
                        id=f"elemento-{nombre}",
                        children=[
                            # Dividir el texto por líneas
                            *[html.Div(line) for line in texto.split('\n')]
                        ],
                        style={
                            "position": "absolute",
                            "left": f"{x_px}px",
                            "top": f"{y_px}px",
                            "width": f"{ancho_px}px",
                            "height": f"{alto_px}px",
                            "color": color_texto,
                            "fontFamily": familia_fuente,
                            "fontSize": f"{tamano_fuente * SCALE_FACTOR}px",
                            "fontWeight": negrita,
                            "fontStyle": cursiva,
                            "textAlign": text_align,
                            "display": "flex",
                            "flexDirection": "column",
                            "justifyContent": align_map.get(alineacion_v, "flex-start"),
                            "transform": f"rotate({rotacion}deg)",
                            "transformOrigin": "center center",
                            "overflow": "hidden" if not ajuste_automatico else "visible",
                            "wordBreak": "break-word" if ajuste_automatico else "normal",
                            "backgroundColor": "rgba(255,255,255,0.1)",  # Ligeramente visible para ayudar a posicionar
                            "border": "1px dashed rgba(0,0,0,0.2)",  # Borde punteado para ver el área
                            "zIndex": elemento["metadata"]["zIndex"],
                            "padding": "1px",
                            "boxSizing": "border-box"
                        },
                        title=nombre,
                        **({'data-editable': 'true'} if elemento["contenido"].get("editable", False) else {})
                        # Añadir atributo de datos si es editable
                    )

                    elementos_canvas.append(texto_element)
                # elementos de tipo gráfico
                elif elemento["tipo"] == "grafico" and elemento["metadata"]["visible"]:
                    # Coordenadas y dimensiones
                    x_px = cm_a_px(elemento["geometria"]["x"])
                    y_px = cm_a_px(elemento["geometria"]["y"])
                    ancho_px = cm_a_px(elemento["geometria"]["ancho"])
                    alto_px = cm_a_px(elemento["geometria"]["alto"])

                    # Aplicar reducción
                    reduccion_px = elemento["estilo"].get("reduccion", 1) * SCALE_FACTOR
                    x_ajustado = x_px + reduccion_px
                    y_ajustado = y_px + reduccion_px
                    ancho_ajustado = ancho_px - (reduccion_px * 2)
                    alto_ajustado = alto_px - (reduccion_px * 2)

                    # Calcular opacidad
                    opacidad = elemento["estilo"]["opacidad"] / 100

                    # Obtener título y tipo
                    titulo = elemento["configuracion"].get("script", "Gráfico")

                    # Crear elemento div para el gráfico (placeholder)
                    graph_element = html.Div(
                        id=f"elemento-{nombre}",
                        children=[
                            DashIconify(icon="mdi:chart-line", width=32, height=32, style={"opacity": 0.7}),
                            html.Div(titulo, style={"fontSize": "12px", "fontWeight": "bold", "marginTop": "5px"}),
                        ],
                        style={
                            "position": "absolute",
                            "left": f"{x_ajustado}px",
                            "top": f"{y_ajustado}px",
                            "width": f"{ancho_ajustado}px",
                            "height": f"{alto_ajustado}px",
                            "backgroundColor": "#f0f0f0",
                            "opacity": opacidad,
                            "border": "1px dashed #666",
                            "display": "flex",
                            "flexDirection": "column",
                            "justifyContent": "center",
                            "alignItems": "center",
                            "color": "#444",
                            "padding": "5px",
                            "boxSizing": "border-box",
                            "zIndex": elemento["metadata"]["zIndex"],
                        },
                        title=nombre,
                    )

                    elementos_canvas.append(graph_element)

        return canvas_style, horizontal_ruler_style, horizontal_marks, vertical_ruler_style, vertical_marks, elementos_canvas

    @app.callback(
        Output("store-componentes", "data", allow_duplicate=True),
        Input("ep-orientation-selector", "value"),
        State("store-componentes", "data"),
        State("ep-page-number", "value"),
        prevent_initial_call=True
    )
    def update_page_orientation(orientation, store_data, current_page):
        page_key = str(current_page)

        # Asegurarse de que existe la página y su configuración
        if page_key not in store_data['paginas']:
            store_data['paginas'][page_key] = {
                "elementos": {},
                "configuracion": {
                    "orientacion": orientation
                }
            }
        elif "configuracion" not in store_data['paginas'][page_key]:
            store_data['paginas'][page_key]["configuracion"] = {
                "orientacion": orientation
            }
        else:
            store_data['paginas'][page_key]["configuracion"]["orientacion"] = orientation

        return store_data

    # callback que actualice las opciones del selector cuando cambie el número total de páginas
    @app.callback(
        Output("ep-page-number", "data"),
        Input("store-componentes", "data")
    )
    def update_page_selector_options(store_data):
        num_pages = store_data['configuracion']['num_paginas']
        return [{"value": str(i), "label": str(i)} for i in range(1, num_pages + 1)]
    # callback para cambiar de página
    @app.callback(
        [Output("ep-page-number", "value"),
         Output("ep-orientation-selector", "value")],
        [Input("ep-prev-page-btn", "n_clicks"),
         Input("ep-next-page-btn", "n_clicks")],
        [State("ep-page-number", "value"),
         State("store-componentes", "data")],
        prevent_initial_call=True
    )
    def change_page(prev_clicks, next_clicks, current_page, store_data):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Convertir current_page de string a entero
        current_page_int = int(current_page)

        if button_id == "ep-prev-page-btn" and current_page_int > 1:
            new_page = current_page_int - 1
        elif button_id == "ep-next-page-btn" and current_page_int < store_data['configuracion']['num_paginas']:
            new_page = current_page_int + 1
        else:
            return current_page, dash.no_update

        # Convertir de nuevo a string
        page_key = str(new_page)

        # Obtener la orientación de la nueva página
        if page_key in store_data['paginas'] and "configuracion" in store_data['paginas'][page_key]:
            orientation = store_data['paginas'][page_key]["configuracion"].get("orientacion", "portrait")
        else:
            orientation = "portrait"

        return page_key, orientation

    # Callback para Inicializar Orientación al Cargar Página
    @app.callback(
        Output("ep-orientation-selector", "value", allow_duplicate=True),
        Input("ep-page-number", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def update_orientation_on_page_change(current_page, store_data):
        page_key = str(current_page)

        # Obtener la orientación de la página actual
        if page_key in store_data['paginas'] and "configuracion" in store_data['paginas'][page_key]:
            orientation = store_data['paginas'][page_key]["configuracion"].get("orientacion", "portrait")
        else:
            orientation = "portrait"

        return orientation

    # Ajustar callback para añadir página:
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-page-number", "value", allow_duplicate=True)],
        Input("ep-add-page-btn", "n_clicks"),
        [State("store-componentes", "data"),
         State("ep-orientation-selector", "value")],
        prevent_initial_call=True
    )
    def add_page(n_clicks, store_data, current_orientation):
        if not n_clicks:
            return store_data, dash.no_update

        # Incrementar el número de páginas
        num_paginas = store_data['configuracion']['num_paginas'] + 1
        store_data['configuracion']['num_paginas'] = num_paginas

        # Crear nueva página vacía con la orientación actual
        page_key = str(num_paginas)
        store_data['paginas'][page_key] = {
            "elementos": {},
            "configuracion": {
                "orientacion": current_orientation
            }
        }

        # Actualizar la página actual
        store_data['pagina_actual'] = page_key

        return store_data, page_key  # Devolver como string

    # Implementación del Callback para Actualizar pagina_actual
    @app.callback(
        Output("store-componentes", "data", allow_duplicate=True),
        Input("ep-page-number", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def update_current_page(current_page, store_data):
        """
        Actualiza el valor de 'pagina_actual' en el store cuando el usuario cambia de página.
        """
        # current_page ya es un string y solo puede ser un valor válido del selector

        # Actualizar la página actual en el store
        store_data['pagina_actual'] = current_page

        return store_data

    # callback para mostrar número total de páginas
    @app.callback(
        Output("ep-total-pages", "children"),
        Input("store-componentes", "data")
    )
    def update_total_pages(store_data):
        return str(store_data['configuracion']['num_paginas'])

    # Callback para abrir el drawer de línea
    @app.callback(
        [Output("drawer-line", "opened"),
         Output("line-nombre", "value")],  # Añadir output para el nombre
        Input("ep-add-line-btn", "n_clicks"),
        State("store-componentes", "data"),  # Añadir el store como state
        prevent_initial_call=True
    )
    def open_line_drawer(n_clicks, store_data):
        if not n_clicks:
            return False, "Línea 1"

        # Obtener la página actual
        page_key = store_data.get('pagina_actual', "1")

        # Generar nombre sugerido
        if ('paginas' in store_data and page_key in store_data['paginas'] and
                'elementos' in store_data['paginas'][page_key]):
            elementos_pagina = store_data['paginas'][page_key]['elementos']
            lineas_existentes = [nombre for nombre, elem in elementos_pagina.items()
                                 if elem["tipo"] == "linea"]

            # Encontrar el siguiente número disponible
            num = 1
            while f"Línea {num}" in lineas_existentes:
                num += 1

            nombre_sugerido = f"Línea {num}"
        else:
            nombre_sugerido = "Línea 1"

        return True, nombre_sugerido


    # callback para crear/actualizar líneas
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("drawer-line", "opened", allow_duplicate=True),
         Output("ep-canvas-status", "children", allow_duplicate=True),
         Output("ep-canvas-status", "color", allow_duplicate=True),
         Output("ep-canvas-status", "hide", allow_duplicate=True)],
        Input("btn-create-line", "n_clicks"),
        [State("line-selector", "value"),
        State("line-x1", "value"),
        State("line-y1", "value"),
        State("line-x2", "value"),
        State("line-y2", "value"),
        State("line-grosor", "value"),
        State("line-color", "value"),
        State("line-nombre", "value"),
        State("line-zindex", "value"),  # Mantener el zIndex
        State("store-componentes", "data"),
        State("ep-orientation-selector", "value"),
        State("ep-page-number", "value")],
        prevent_initial_call = True
    )
    def crear_actualizar_linea(n_clicks, selected_line_name, x1, y1, x2, y2, grosor, color, nombre, zindex, store_data,
                               orientacion, current_page):
        if not n_clicks:
            return store_data, False, "", "blue", True

        page_key = str(current_page)

        # Asegurarse de que existe la página y los elementos
        if page_key not in store_data['paginas']:
            store_data['paginas'][page_key] = {
                "elementos": {},
                "configuracion": {
                    "orientacion": orientacion
                }
            }
        elif "elementos" not in store_data['paginas'][page_key]:
            store_data['paginas'][page_key]["elementos"] = {}

        # Obtener los elementos de la página actual
        elementos_pagina = store_data['paginas'][page_key]['elementos']

        # Verificar si es una actualización o sobrescritura
        es_actualizacion = selected_line_name and selected_line_name == nombre
        sobrescrito = nombre in elementos_pagina and not es_actualizacion

        # Crear línea con la estructura
        linea_datos = {
            "tipo": "linea",
            "geometria": {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2
            },
            "estilo": {
                "grosor": grosor,
                "color": color
            },
            "grupo": {
                "nombre": "Sin grupo",
                "color": "#cccccc"
            },
            "metadata": {
                "zIndex": zindex,
                "visible": True,
                "bloqueado": False
            }
        }

        # Si estamos editando y el nombre ha cambiado, borrar elemento anterior
        if selected_line_name and selected_line_name != nombre:
            if selected_line_name in elementos_pagina:
                del elementos_pagina[selected_line_name]

        # Guardar elemento en el diccionario de la página actual
        elementos_pagina[nombre] = linea_datos

        # Actualizar la orientación en la configuración de la página
        if "configuracion" not in store_data['paginas'][page_key]:
            store_data['paginas'][page_key]["configuracion"] = {}
        store_data['paginas'][page_key]["configuracion"]["orientacion"] = orientacion

        # Preparar mensaje de estado
        if sobrescrito:
            mensaje = f"Se ha sobrescrito la línea '{nombre}'."
            color_estado = "yellow"
        elif es_actualizacion:
            mensaje = f"Línea '{nombre}' actualizada correctamente."
            color_estado = "green"
        else:
            mensaje = f"Línea '{nombre}' creada correctamente."
            color_estado = "green"

        ocultar_estado = False

        # Cerrar el drawer y retornar la store actualizada con mensaje
        return store_data, False, mensaje, color_estado, ocultar_estado

    # Callback para borrar la línea seleccionada
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("drawer-line", "opened", allow_duplicate=True),
         Output("line-selector", "value")],
        [Input("btn-delete-line", "n_clicks"),
        State("line-selector", "value"),
        State("store-componentes", "data"),
        State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def borrar_linea(n_clicks, selected_name, store_data, current_page):
        if not n_clicks or not selected_name:
            return store_data, True, None

        page_key = str(current_page)

        # Verificar si existe la página y sus elementos
        if (page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return store_data, True, None

        elementos_pagina = store_data['paginas'][page_key]['elementos']

        # Eliminar elemento del diccionario de la página actual
        if selected_name in elementos_pagina:
            del elementos_pagina[selected_name]

        # Cerrar el drawer y limpiar la selección
        return store_data, False, None

    # Callback para abrir el drawer de rectángulo
    @app.callback(
        [Output("ep-rectangle-drawer", "opened"),
         Output("rectangle-nombre", "value")],
        Input("ep-add-rectangle-btn", "n_clicks"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def open_rectangle_drawer(n_clicks, store_data):
        if not n_clicks:
            return False, "rectangulo 1"

        # Obtener la página actual
        page_key = store_data.get('pagina_actual', "1")

        # Generar nombre sugerido
        if ('paginas' in store_data and page_key in store_data['paginas'] and
                'elementos' in store_data['paginas'][page_key]):
            elementos_pagina = store_data['paginas'][page_key]['elementos']
            lineas_existentes = [nombre for nombre, elem in elementos_pagina.items()
                                 if elem["tipo"] == "rectangulo"]

            # Encontrar el siguiente número disponible
            num = 1
            while f"rectangulo {num}" in lineas_existentes:
                num += 1

            nombre_sugerido = f"rectangulo {num}"
        else:
            nombre_sugerido = "rectangulo 1"

        return True, nombre_sugerido

    # Callback para abrir el drawer de gráfico
    @app.callback(
        [Output("ep-graph-drawer", "opened"),
         Output("graph-nombre", "value")],
        Input("ep-add-graph-btn", "n_clicks"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def open_graph_drawer(n_clicks, store_data):
        if not n_clicks:
            return False, "grafico 1"

        # Obtener la página actual
        page_key = store_data.get('pagina_actual', "1")

        # Generar nombre sugerido
        if ('paginas' in store_data and page_key in store_data['paginas'] and
                'elementos' in store_data['paginas'][page_key]):
            elementos_pagina = store_data['paginas'][page_key]['elementos']
            graficos_existentes = [nombre for nombre, elem in elementos_pagina.items()
                                   if elem["tipo"] == "grafico"]

            # Encontrar el siguiente número disponible
            num = 1
            while f"grafico {num}" in graficos_existentes:
                num += 1

            nombre_sugerido = f"grafico {num}"
        else:
            nombre_sugerido = "grafico 1"

        return True, nombre_sugerido

    # Callback para actualizar la lista de gráficos en el selectbox
    @app.callback(
        Output("graph-selector", "data"),
        [Input("store-componentes", "data"),
         Input("ep-page-number", "value")]
    )
    def update_graph_selector(store_data, current_page):
        page_key = str(current_page)

        if (not store_data or 'paginas' not in store_data or
                page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return []

        options = [
            {"value": nombre, "label": nombre}
            for nombre, elemento in store_data['paginas'][page_key]['elementos'].items()
            if elemento["tipo"] == "grafico"
        ]

        return options

    # Callback para rellenar el formulario cuando se selecciona un gráfico
    @app.callback(
        [Output("graph-x", "value"),
         Output("graph-y", "value"),
         Output("graph-width", "value"),
         Output("graph-height", "value"),
         Output("graph-script", "value"),
         Output("graph-format", "value"),  # NUEVO OUTPUT
         Output("graph-opacity", "value"),
         Output("graph-reduction", "value"),
         Output("graph-zindex", "value"),
         Output("graph-nombre", "value", allow_duplicate=True),
         Output("graph-parameters", "value")],
        Input("graph-selector", "value"),
        [State("store-componentes", "data"),
         State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def fill_graph_form(selected_graph_name, store_data, current_page):
        page_key = str(current_page)

        if (not selected_graph_name or 'paginas' not in store_data or
                page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return 1.0, 1.0, 8.0, 6.0, "", "svg", 100, 1, 25, "Gráfico 1", ""  # Incluir "svg" por defecto

        elementos_pagina = store_data['paginas'][page_key]['elementos']

        if selected_graph_name in elementos_pagina:
            elemento = elementos_pagina[selected_graph_name]
            if elemento["tipo"] == "grafico":
                # Extraer los valores para cada campo
                configuracion = elemento.get("configuracion", {})
                parametros = configuracion.get("parametros", {})
                formato = configuracion.get("formato", "svg")  # NUEVO: obtener formato, por defecto svg

                # Convertir los parámetros a formato de texto JSON válido
                parametros_texto = ""
                if parametros:
                    import json
                    try:
                        # Usar json.dumps para convertir correctamente los tipos de datos
                        parametros_json = json.dumps(parametros, indent=0, ensure_ascii=False)
                        # Remover las llaves exteriores
                        parametros_texto = parametros_json.strip('{}').strip()
                        # Limpiar formato para que sea más legible en el textarea
                        parametros_texto = parametros_texto.replace('", "', '",\n"')
                        if parametros_texto:
                            parametros_texto = parametros_texto.replace('":', '": ')
                    except Exception as e:
                        print(f"Error al convertir parámetros a JSON: {str(e)}")
                        # Fallback al método anterior si json.dumps falla
                        for clave, valor in parametros.items():
                            if isinstance(valor, str):
                                parametros_texto += f'"{clave}": "{valor}",\n'
                            elif isinstance(valor, bool):
                                parametros_texto += f'"{clave}": {str(valor).lower()},\n'
                            elif valor is None:
                                parametros_texto += f'"{clave}": null,\n'
                            else:
                                parametros_texto += f'"{clave}": {valor},\n'
                        # Eliminar la última coma y salto de línea
                        if parametros_texto:
                            parametros_texto = parametros_texto.rstrip(',\n')

                return (
                    elemento["geometria"]["x"],
                    elemento["geometria"]["y"],
                    elemento["geometria"]["ancho"],
                    elemento["geometria"]["alto"],
                    configuracion.get("script", ""),
                    formato,  # NUEVO: devolver el formato
                    elemento["estilo"].get("opacidad", 100),
                    elemento["estilo"].get("reduccion", 1),
                    elemento["metadata"].get("zIndex", 25),
                    selected_graph_name,
                    parametros_texto
                )

        # Si no se encuentra el gráfico
        return (1.0, 1.0, 8.0, 6.0, "", "svg", 100, 1, 25, "Gráfico 1", "")  # Incluir "svg" por defecto

    # Callback para crear/actualizar gráficos
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-graph-drawer", "opened", allow_duplicate=True),
         Output("ep-canvas-status", "children", allow_duplicate=True),
         Output("ep-canvas-status", "color", allow_duplicate=True),
         Output("ep-canvas-status", "hide", allow_duplicate=True)],
        Input("btn-create-graph", "n_clicks"),
        [State("graph-selector", "value"),
         State("graph-x", "value"),
         State("graph-y", "value"),
         State("graph-width", "value"),
         State("graph-height", "value"),
         State("graph-script", "value"),
         State("graph-format", "value"),  # NUEVO STATE
         State("graph-opacity", "value"),
         State("graph-reduction", "value"),
         State("graph-zindex", "value"),
         State("graph-nombre", "value"),
         State("graph-parameters", "value"),
         State("store-componentes", "data"),
         State("ep-orientation-selector", "value"),
         State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def crear_actualizar_grafico(n_clicks, selected_name, x, y, ancho, alto, script, formato,  # NUEVO PARÁMETRO
                                 opacidad, reduccion, zindex, nombre, parametros_texto, store_data, orientacion,
                                 current_page):
        if not n_clicks:
            return store_data, False, "", "blue", True

        page_key = str(current_page)

        # Asegurarse de que existe la página y los elementos
        if page_key not in store_data['paginas']:
            store_data['paginas'][page_key] = {
                "elementos": {},
                "configuracion": {
                    "orientacion": orientacion
                }
            }
        elif "elementos" not in store_data['paginas'][page_key]:
            store_data['paginas'][page_key]["elementos"] = {}

        # Obtener los elementos de la página actual
        elementos_pagina = store_data['paginas'][page_key]['elementos']

        # Verificar si es una actualización o sobrescritura
        es_actualizacion = selected_name and selected_name == nombre
        sobrescrito = nombre in elementos_pagina and not es_actualizacion

        # Procesar los parámetros del texto a un diccionario
        parametros = {}
        if parametros_texto and parametros_texto.strip():
            try:
                import json
                # Preparar el texto para convertirlo a JSON válido
                json_text = "{" + parametros_texto + "}"

                # Limpiar posibles errores de formato
                json_text = json_text.replace("'", '"')  # Reemplazar comillas simples por dobles

                # Intentar parsear el JSON
                parametros = json.loads(json_text)

            except json.JSONDecodeError as e:
                # Error específico de JSON para dar mejor información
                error_msg = f"Error en formato JSON: {str(e)}"
                print(f"Error al procesar parámetros JSON: {error_msg}")
                print(f"Texto de parámetros problemático: {parametros_texto}")
                return store_data, True, f"Error en el formato de los parámetros: {error_msg}", "red", False

            except Exception as e:
                # Otros errores
                print(f"Error al procesar parámetros: {str(e)}")
                print(f"Texto de parámetros: {parametros_texto}")
                return store_data, True, f"Error en el formato de los parámetros: {str(e)}", "red", False

        # Crear gráfico con la estructura definida
        grafico_datos = {
            "tipo": "grafico",
            "geometria": {
                "x": x,
                "y": y,
                "ancho": ancho,
                "alto": alto
            },
            "configuracion": {
                "script": script,
                "formato": formato,  # NUEVO: incluir el formato
                "parametros": parametros
            },
            "estilo": {
                "opacidad": opacidad,
                "reduccion": reduccion
            },
            "grupo": {
                "nombre": "Sin grupo",
                "color": "#cccccc"
            },
            "metadata": {
                "zIndex": zindex,
                "visible": True,
                "bloqueado": False
            }
        }

        # Si estamos editando y el nombre ha cambiado, borrar elemento anterior
        if selected_name and selected_name != nombre:
            if selected_name in elementos_pagina:
                del elementos_pagina[selected_name]

        # Guardar elemento en el diccionario
        elementos_pagina[nombre] = grafico_datos

        # Actualizar la orientación en la configuración de la página
        if "configuracion" not in store_data['paginas'][page_key]:
            store_data['paginas'][page_key]["configuracion"] = {}
        store_data['paginas'][page_key]["configuracion"]["orientacion"] = orientacion

        # Preparar mensaje de estado
        if sobrescrito:
            mensaje = f"Se ha sobrescrito el gráfico '{nombre}'."
            color_estado = "yellow"
        elif es_actualizacion:
            mensaje = f"Gráfico '{nombre}' actualizado correctamente."
            color_estado = "green"
        else:
            mensaje = f"Gráfico '{nombre}' creado correctamente."
            color_estado = "green"

        ocultar_estado = False

        # Cerrar el drawer y retornar la store actualizada con mensaje
        return store_data, False, mensaje, color_estado, ocultar_estado

    # Callback para borrar el gráfico seleccionado
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-graph-drawer", "opened", allow_duplicate=True),
         Output("graph-selector", "value")],
        Input("btn-delete-graph", "n_clicks"),
        [State("graph-selector", "value"),
         State("store-componentes", "data"),
         State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def borrar_grafico(n_clicks, selected_name, store_data, current_page):
        if not n_clicks or not selected_name:
            return store_data, True, None

        page_key = str(current_page)

        # Verificar si existe la página y sus elementos
        if (page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return store_data, True, None

        elementos_pagina = store_data['paginas'][page_key]['elementos']

        # Eliminar elemento del diccionario de la página actual
        if selected_name in elementos_pagina:
            del elementos_pagina[selected_name]

        # Cerrar el drawer y limpiar la selección
        return store_data, False, None

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
        [Input("store-componentes", "data"),
         Input("ep-page-number", "value")]
    )
    def update_line_selector(store_data, current_page):
        page_key = str(current_page)
        if (not store_data or 'paginas' not in store_data or
                page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return []

        options = [
            {"value": nombre, "label": nombre}
            for nombre, elemento in store_data['paginas'][page_key]['elementos'].items()
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
         Output("line-nombre", "value", allow_duplicate=True),
         Output("line-zindex", "value")],
        Input("line-selector", "value"),
        [State("store-componentes", "data"),
         State("ep-page-number", "value")],  # Añadir esto
        prevent_initial_call=True
    )
    def fill_line_form(selected_line_name, store_data, current_page):
        page_key = str(current_page)  # Convertir a string

        # Verificar si existe la página y sus elementos
        if (not selected_line_name or 'paginas' not in store_data or
                page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            # Valores por defecto
            return 1.0, 1.0, 5.0, 5.0, 1, "#000000", "Línea 1", 10

        # Obtener los elementos de la página actual
        elementos_pagina = store_data['paginas'][page_key]['elementos']

        # Verificar si existe el elemento
        if selected_line_name in elementos_pagina:
            elemento = elementos_pagina[selected_line_name]
            if elemento["tipo"] == "linea":
                return (
                    elemento["geometria"]["x1"],
                    elemento["geometria"]["y1"],
                    elemento["geometria"]["x2"],
                    elemento["geometria"]["y2"],
                    elemento["estilo"]["grosor"],
                    elemento["estilo"]["color"],
                    selected_line_name,
                    elemento["metadata"].get("zIndex", 10)
                )

        # Si no se encuentra
        return 1.0, 1.0, 5.0, 5.0, 1, "#000000", "Línea 1", 10

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
        #store_data['configuracion']['ultima_modificacion'] = datetime.now().isoformat()

        return store_data


    # Callback para actualizar la lista de rectángulos en el selectbox
    @app.callback(
        Output("rectangle-selector", "data"),
        [Input("store-componentes", "data"),
         Input("ep-page-number", "value")]
    )
    def update_rectangle_selector(store_data, current_page):
        page_key = str(current_page)

        if (not store_data or 'paginas' not in store_data or
                page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return []

        options = [
            {"value": nombre, "label": nombre}
            for nombre, elemento in store_data['paginas'][page_key]['elementos'].items()
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
         Output("rectangle-nombre", "value", allow_duplicate=True),
         Output("rectangle-zindex", "value")],
        Input("rectangle-selector", "value"),
        [State("store-componentes", "data"),
         State("ep-page-number", "value")],  # Añadir esto
        prevent_initial_call=True
    )
    def fill_rectangle_form(selected_rectangle_name, store_data, current_page):
        page_key = str(current_page)

        if (not selected_rectangle_name or 'paginas' not in store_data or
                page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return 1.0, 1.0, 5.0, 3.0, 1, "#000000", "#FFFFFF", 100, "Rectángulo 1", 5

        elementos_pagina = store_data['paginas'][page_key]['elementos']

        if selected_rectangle_name in elementos_pagina:
            elemento = elementos_pagina[selected_rectangle_name]
            if elemento["tipo"] == "rectangulo":
                return (
                    elemento["geometria"]["x"],
                    elemento["geometria"]["y"],
                    elemento["geometria"]["ancho"],
                    elemento["geometria"]["alto"],
                    elemento["estilo"]["grosor_borde"],
                    elemento["estilo"]["color_borde"],
                    elemento["estilo"]["color_relleno"],
                    elemento["estilo"]["opacidad"],
                    selected_rectangle_name,
                    elemento["metadata"].get("zIndex", 5)
                )

        return 1.0, 1.0, 5.0, 3.0, 1, "#000000", "#FFFFFF", 100, "Rectángulo 1", 5


    # Callback para crear/actualizar rectángulos
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-rectangle-drawer", "opened", allow_duplicate=True),
         Output("ep-canvas-status", "children", allow_duplicate=True),
         Output("ep-canvas-status", "color", allow_duplicate=True),
         Output("ep-canvas-status", "hide", allow_duplicate=True)],
        Input("btn-create-rectangle", "n_clicks"),
        [State("rectangle-selector", "value"),
        State("rectangle-x", "value"),
        State("rectangle-y", "value"),
        State("rectangle-width", "value"),
        State("rectangle-height", "value"),
        State("rectangle-border-width", "value"),
        State("rectangle-border-color", "value"),
        State("rectangle-fill-color", "value"),
        State("rectangle-opacity", "value"),
        State("rectangle-nombre", "value"),
        State("rectangle-zindex", "value"),  # Incluir zIndex
        State("store-componentes", "data"),
        State("ep-orientation-selector", "value"),
         State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def crear_actualizar_rectangulo(n_clicks, selected_name, x, y, ancho, alto, grosor_borde,
                                    color_borde, color_relleno, opacidad, nombre, zindex, store_data, orientacion,
                                    current_page):
        if not n_clicks:
            return store_data, False, "", "blue", True

        page_key = str(current_page)

        # Asegurarse de que existe la página y los elementos
        if page_key not in store_data['paginas']:
            store_data['paginas'][page_key] = {
                "elementos": {},
                "configuracion": {
                    "orientacion": orientacion
                }
            }
        elif "elementos" not in store_data['paginas'][page_key]:
            store_data['paginas'][page_key]["elementos"] = {}

        # Obtener los elementos de la página actual
        elementos_pagina = store_data['paginas'][page_key]['elementos']

        # Verificar si es una actualización o sobrescritura
        es_actualizacion = selected_name and selected_name == nombre
        sobrescrito = nombre in elementos_pagina and not es_actualizacion

        # Crear rectángulo con la nueva estructura
        rect_datos = {
            "tipo": "rectangulo",
            "geometria": {
                "x": x,
                "y": y,
                "ancho": ancho,
                "alto": alto
            },
            "estilo": {
                "grosor_borde": grosor_borde,
                "color_borde": color_borde,
                "color_relleno": color_relleno,
                "opacidad": opacidad
            },
            "grupo": {
                "nombre": "Sin grupo",
                "color": "#cccccc"
            },
            "metadata": {
                "zIndex": zindex,  # Usar zIndex del input
                "visible": True,
                "bloqueado": False
            }
        }

        # Si estamos editando y el nombre ha cambiado, borrar elemento anterior
        if selected_name and selected_name != nombre:
            if selected_name in elementos_pagina:
                del elementos_pagina[selected_name]

        # Guardar elemento en el diccionario
        elementos_pagina[nombre] = rect_datos

        # Actualizar la orientación en la configuración de la página
        if "configuracion" not in store_data['paginas'][page_key]:
            store_data['paginas'][page_key]["configuracion"] = {}
        store_data['paginas'][page_key]["configuracion"]["orientacion"] = orientacion

        # Preparar mensaje de estado
        if sobrescrito:
            mensaje = f"Se ha sobrescrito el rectángulo '{nombre}'."
            color_estado = "yellow"
        elif es_actualizacion:
            mensaje = f"Rectángulo '{nombre}' actualizado correctamente."
            color_estado = "green"
        else:
            mensaje = f"Rectángulo '{nombre}' creado correctamente."
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
        [State("rectangle-selector", "value"),
        State("store-componentes", "data"),
        State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def borrar_rectangulo(n_clicks, selected_name, store_data, current_page):
        if not n_clicks or not selected_name:
            return store_data, True, None

        page_key = str(current_page)

        # Verificar si existe la página y sus elementos
        if (page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return store_data, True, None

        elementos_pagina = store_data['paginas'][page_key]['elementos']

        # Eliminar elemento del diccionario de la página actual
        if selected_name in elementos_pagina:
            del elementos_pagina[selected_name]

        # Cerrar el drawer y limpiar la selección
        return store_data, False, None

    # callbacks texto
    # Callback para abrir el drawer de texto
    @app.callback(
        [Output("ep-text-drawer", "opened"),
         Output("text-nombre", "value")],
        Input("ep-add-text-btn", "n_clicks"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def open_text_drawer(n_clicks, store_data):
        if not n_clicks:
            return False, "texto 1"

        # Obtener la página actual
        page_key = store_data.get('pagina_actual', "1")

        # Generar nombre sugerido
        if ('paginas' in store_data and page_key in store_data['paginas'] and
                'elementos' in store_data['paginas'][page_key]):
            elementos_pagina = store_data['paginas'][page_key]['elementos']
            lineas_existentes = [nombre for nombre, elem in elementos_pagina.items()
                                 if elem["tipo"] == "texto"]

            # Encontrar el siguiente número disponible
            num = 1
            while f"texto {num}" in lineas_existentes:
                num += 1

            nombre_sugerido = f"texto {num}"
        else:
            nombre_sugerido = "texto 1"

        return True, nombre_sugerido

    # Callback para actualizar la lista de textos en el selector
    @app.callback(
        Output("text-selector", "data"),
        [Input("store-componentes", "data"),
         Input("ep-page-number", "value")]
    )
    def update_text_selector(store_data, current_page):
        page_key = str(current_page)

        if (not store_data or 'paginas' not in store_data or
                page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return []

        options = [
            {"value": nombre, "label": nombre}
            for nombre, elemento in store_data['paginas'][page_key]['elementos'].items()
            if elemento["tipo"] == "texto"
        ]

        return options

    # Callback para rellenar el formulario cuando se selecciona un texto
    @app.callback(
        [Output("text-x", "value"),
         Output("text-y", "value"),
         Output("text-width", "value"),
         Output("text-height", "value"),
         Output("text-rotation", "value"),
         Output("text-font-family", "value"),
         Output("text-font-size", "value"),
         Output("text-font-weight", "value"),
         Output("text-font-style", "value"),
         Output("text-color", "value"),
         Output("text-align-h", "value"),
         Output("text-align-v", "value"),
         Output("text-auto-adjust", "checked"),
         Output("text-content", "value"),
         Output("text-nombre", "value", allow_duplicate=True),
         Output("text-zindex", "value"),
         Output("text-editable", "checked")],
        Input("text-selector", "value"),
        [State("store-componentes", "data"),
         State("ep-page-number", "value")],  # Añadir esto
        prevent_initial_call=True
    )
    def fill_text_form(selected_text_name, store_data, current_page):
        page_key = str(current_page)

        if (not selected_text_name or 'paginas' not in store_data or
                page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return 1.0, 1.0, 5.0, 2.0, 0, "Helvetica", 10, "normal", "normal", "#000000", "left", "top", True, "", "Texto 1", 20, False

        elementos_pagina = store_data['paginas'][page_key]['elementos']

        if selected_text_name in elementos_pagina:
            elemento = elementos_pagina[selected_text_name]
            if elemento["tipo"] == "texto":
                # Valor por defecto False si no existe la propiedad editable
                editable = elemento["contenido"].get("editable", False)

                return (
                    elemento["geometria"]["x"],
                    elemento["geometria"]["y"],
                    elemento["geometria"]["ancho"],
                    elemento["geometria"]["alto"],
                    elemento["estilo"].get("rotacion", 0),
                    elemento["estilo"]["familia_fuente"],
                    elemento["estilo"]["tamano"],
                    elemento["estilo"]["negrita"],
                    elemento["estilo"]["cursiva"],
                    elemento["estilo"]["color"],
                    elemento["estilo"]["alineacion_h"],
                    elemento["estilo"]["alineacion_v"],
                    elemento["contenido"]["ajuste_automatico"],
                    elemento["contenido"]["texto"],
                    selected_text_name,
                    elemento["metadata"].get("zIndex", 20),
                    editable  # valor de editable
                )

        # Si no se encuentra
        return 1.0, 1.0, 5.0, 2.0, 0, "Helvetica", 10, "normal", "normal", "#000000", "left", "top", True, "", "Texto 1", 20, False

    # Callback para crear/actualizar textos
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-text-drawer", "opened", allow_duplicate=True),
         Output("ep-canvas-status", "children", allow_duplicate=True),
         Output("ep-canvas-status", "color", allow_duplicate=True),
         Output("ep-canvas-status", "hide", allow_duplicate=True)],
        Input("btn-create-text", "n_clicks"),
        [State("text-selector", "value"),
        State("text-x", "value"),
        State("text-y", "value"),
        State("text-width", "value"),
        State("text-height", "value"),
        State("text-rotation", "value"),
        State("text-font-family", "value"),
        State("text-font-size", "value"),
        State("text-font-weight", "value"),
        State("text-font-style", "value"),
        State("text-color", "value"),
        State("text-align-h", "value"),
        State("text-align-v", "value"),
        State("text-auto-adjust", "checked"),
        State("text-content", "value"),
        State("text-nombre", "value"),
        State("text-zindex", "value"),
        State("text-editable", "checked"),
        State("store-componentes", "data"),
        State("ep-orientation-selector", "value"),
        State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def crear_actualizar_texto(n_clicks, selected_name, x, y, ancho, alto, rotacion,
                               familia_fuente, tamano, negrita, cursiva, color,
                               alineacion_h, alineacion_v, ajuste_automatico,
                               contenido_texto, nombre, zindex, editable, store_data, orientacion, current_page):
        if not n_clicks:
            return store_data, False, "", "blue", True

        page_key = str(current_page)

        # Asegurarse de que existe la página y los elementos
        if page_key not in store_data['paginas']:
            store_data['paginas'][page_key] = {
                "elementos": {},
                "configuracion": {
                    "orientacion": "portrait"  # Valor por defecto
                }
            }
        elif "elementos" not in store_data['paginas'][page_key]:
            store_data['paginas'][page_key]["elementos"] = {}

        elementos_pagina = store_data['paginas'][page_key]['elementos']

        # Verificar si es una actualización o sobrescritura
        es_actualizacion = selected_name and selected_name == nombre
        sobrescrito = nombre in elementos_pagina and not es_actualizacion

        # Crear texto con la estructura definida
        texto_datos = {
            "tipo": "texto",
            "geometria": {
                "x": x,
                "y": y,
                "ancho": ancho,
                "alto": alto
            },
            "estilo": {
                "familia_fuente": familia_fuente,
                "tamano": tamano,
                "negrita": negrita,
                "cursiva": cursiva,
                "color": color,
                "alineacion_h": alineacion_h,
                "alineacion_v": alineacion_v,
                "rotacion": rotacion
            },
            "contenido": {
                "texto": contenido_texto or "",
                "ajuste_automatico": ajuste_automatico,
                "editable": editable  # ahora viene de checked
            },
            "grupo": {
                "nombre": "Sin grupo",
                "color": "#cccccc"
            },
            "metadata": {
                "zIndex": zindex,
                "visible": True,
                "bloqueado": False
            }
        }

        # Si estamos editando y el nombre ha cambiado, borrar elemento anterior
        if selected_name and selected_name != nombre:
            if selected_name in elementos_pagina:
                del elementos_pagina[selected_name]

        # Guardar elemento en el diccionario
        elementos_pagina[nombre] = texto_datos

        elementos_pagina[nombre] = texto_datos

        # Actualizar la orientación en la configuración de la página
        if "configuracion" not in store_data['paginas'][page_key]:
            store_data['paginas'][page_key]["configuracion"] = {}
        store_data['paginas'][page_key]["configuracion"]["orientacion"] = orientacion

        # Preparar mensaje de estado
        if sobrescrito:
            mensaje = f"Se ha sobrescrito el texto '{nombre}'."
            color_estado = "yellow"
        elif es_actualizacion:
            mensaje = f"Texto '{nombre}' actualizado correctamente."
            color_estado = "green"
        else:
            mensaje = f"Texto '{nombre}' creado correctamente."
            color_estado = "green"

        ocultar_estado = False

        # Cerrar el drawer y retornar la store actualizada con mensaje
        return store_data, False, mensaje, color_estado, ocultar_estado

    # Callback para borrar un texto
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-text-drawer", "opened", allow_duplicate=True),
         Output("text-selector", "value")],
        Input("btn-delete-text", "n_clicks"),
        [State("text-selector", "value"),
        State("store-componentes", "data"),
        State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def borrar_texto(n_clicks, selected_name, store_data, current_page):
        if not n_clicks or not selected_name:
            return store_data, True, None

        page_key = str(current_page)

        # Verificar si existe la página y sus elementos
        if (page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return store_data, True, None

        elementos_pagina = store_data['paginas'][page_key]['elementos']

        # Eliminar elemento del diccionario de la página actual
        if selected_name in elementos_pagina:
            del elementos_pagina[selected_name]

        # Cerrar el drawer y limpiar la selección
        return store_data, False, None

    # fin callbacks texto

    # Callback para abrir el drawer de imagen
    @app.callback(
        [Output("ep-image-drawer", "opened"),
         Output("image-nombre", "value"),
         Output("image-maintain-aspect-ratio", "checked", allow_duplicate=True)],  # Añadir este output
        Input("ep-add-image-btn", "n_clicks"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def open_image_drawer(n_clicks, store_data):
        if not n_clicks:
            return True, nombre_sugerido, True  # Tercer valor para mantener aspecto

        # Obtener la página actual
        page_key = store_data.get('pagina_actual', "1")

        # Generar nombre sugerido
        if ('paginas' in store_data and page_key in store_data['paginas'] and
                'elementos' in store_data['paginas'][page_key]):
            elementos_pagina = store_data['paginas'][page_key]['elementos']
            lineas_existentes = [nombre for nombre, elem in elementos_pagina.items()
                                 if elem["tipo"] == "imagen"]

            # Encontrar el siguiente número disponible
            num = 1
            while f"imagen {num}" in lineas_existentes:
                num += 1

            nombre_sugerido = f"imagen {num}"
        else:
            nombre_sugerido = "imagen 1"

        return True, nombre_sugerido, True  # Añadido el tercer valor para maintain-aspect-ratio

    # ------
    # Callback para actualizar la lista de imágenes en el selectbox
    @app.callback(
        Output("image-selector", "data"),
        [Input("store-componentes", "data"),
         Input("ep-page-number", "value")]
    )
    def update_image_selector(store_data, current_page):
        page_key = str(current_page)

        if (not store_data or 'paginas' not in store_data or
                page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return []

        options = [
            {"value": nombre, "label": nombre}
            for nombre, elemento in store_data['paginas'][page_key]['elementos'].items()
            if elemento["tipo"] == "imagen"
        ]

        return options

    # Callback para procesar la carga de imágenes
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-canvas-status", "children", allow_duplicate=True),
         Output("ep-canvas-status", "color", allow_duplicate=True),
         Output("ep-canvas-status", "hide", allow_duplicate=True)],
        Input("image-upload", "contents"),
        State("image-upload", "filename"),
        State("image-nombre", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def process_image_upload(contents, filename, nombre, store_data):
        if contents is None:
            return store_data, "", "blue", True

        # Verificar si ya existe una imagen temporal
        temp_img_key = f"temp_img_{nombre}"
        store_data[temp_img_key] = contents

        # Extraer información del tipo de archivo
        try:
            content_type = contents.split(";")[0].split(":")[1]
            img_format = content_type.split("/")[1].lower()
            if img_format == "jpeg":
                img_format = "jpg"

            # Mostrar mensaje de éxito
            return store_data, f"Imagen '{filename}' cargada. Haz clic en Crear/Actualizar para aplicarla.", "green", False

        except Exception as e:
            return store_data, f"Error al procesar la imagen: {str(e)}", "red", False

    # Callback para procesar URL de imágenes
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-canvas-status", "children", allow_duplicate=True),
         Output("ep-canvas-status", "color", allow_duplicate=True),
         Output("ep-canvas-status", "hide", allow_duplicate=True)],
        Input("image-url", "value"),
        State("image-nombre", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def process_image_url(url, nombre, store_data):
        import requests
        from io import BytesIO
        import base64

        if not url or not url.strip():
            return store_data, "", "blue", True

        try:
            # Intentar descargar la imagen
            response = requests.get(url, timeout=5)
            if response.status_code != 200:
                return store_data, f"Error al descargar imagen: Status {response.status_code}", "red", False

            # Determinar el tipo de imagen
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                return store_data, "La URL no contiene una imagen válida", "red", False

            # Convertir a base64
            img_format = content_type.split('/')[1].lower()
            if img_format == "jpeg":
                img_format = "jpg"

            img_base64 = base64.b64encode(response.content).decode('utf-8')
            img_src = f"data:{content_type};base64,{img_base64}"

            # Guardar en el store temporal
            temp_img_key = f"temp_img_{nombre}"
            store_data[temp_img_key] = img_src

            return store_data, f"Imagen descargada. Haz clic en Crear/Actualizar para aplicarla.", "green", False

        except Exception as e:
            return store_data, f"Error al procesar la URL: {str(e)}", "red", False

    # Callback para rellenar el formulario cuando se selecciona una imagen
    @app.callback(
        [Output("image-x", "value"),
         Output("image-y", "value"),
         Output("image-width", "value"),
         Output("image-height", "value"),
         Output("image-opacity", "value"),
         Output("image-maintain-aspect-ratio", "checked", allow_duplicate=True),  # Añadir allow_duplicate=True aquí
         Output("image-nombre", "value", allow_duplicate=True),
         Output("image-zindex", "value"),
         Output("image-reduction", "value")],
        Input("image-selector", "value"),
        [State("store-componentes", "data"),
         State("ep-page-number", "value")],  # Añadir esto
        prevent_initial_call=True
    )
    def fill_image_form(selected_image_name, store_data, current_page):
        page_key = str(current_page)

        if (not selected_image_name or 'paginas' not in store_data or
                page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return 1.0, 1.0, 5.0, 3.0, 100, True, "Imagen 1", 15, 0

        elementos_pagina = store_data['paginas'][page_key]['elementos']

        if selected_image_name in elementos_pagina:
            elemento = elementos_pagina[selected_image_name]
            if elemento["tipo"] == "imagen":
                return (
                    elemento["geometria"]["x"],
                    elemento["geometria"]["y"],
                    elemento["geometria"]["ancho"],
                    elemento["geometria"]["alto"],
                    elemento["estilo"]["opacidad"],
                    elemento["estilo"]["mantener_proporcion"],
                    selected_image_name,
                    elemento["metadata"].get("zIndex", 15),
                    elemento["estilo"].get("reduccion", 0)  # Obtener reducción o valor predeterminado
                )

        # Si no se encuentra
        return 1.0, 1.0, 5.0, 3.0, 100, True, "Imagen 1", 15, 0

    # Callback para crear/actualizar imágenes
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-image-drawer", "opened", allow_duplicate=True),
         Output("ep-canvas-status", "children", allow_duplicate=True),
         Output("ep-canvas-status", "color", allow_duplicate=True),
         Output("ep-canvas-status", "hide", allow_duplicate=True)],
        Input("btn-create-image", "n_clicks"),
        [State("image-selector", "value"),
        State("image-x", "value"),
        State("image-y", "value"),
        State("image-width", "value"),
        State("image-height", "value"),
        State("image-opacity", "value"),
        State("image-maintain-aspect-ratio", "checked"),
        State("image-nombre", "value"),
        State("image-zindex", "value"),
        State("image-reduction", "value"),  # Nuevo parámetro
        State("store-componentes", "data"),
        State("image-url", "value"),
        State("ep-orientation-selector", "value"),
        State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def crear_actualizar_imagen(n_clicks, selected_name, x, y, ancho, alto, opacidad, mantener_proporcion,
                                nombre, zindex, reduccion, store_data, image_url, orientacion, current_page):
        if not n_clicks:
            return store_data, False, "", "blue", True

        page_key = str(current_page)

        # Asegurarse de que existe la página y los elementos
        if page_key not in store_data['paginas']:
            store_data['paginas'][page_key] = {
                "elementos": {},
                "configuracion": {
                    "orientacion": "portrait"  # Valor por defecto
                }
            }
        elif "elementos" not in store_data['paginas'][page_key]:
            store_data['paginas'][page_key]["elementos"] = {}

        elementos_pagina = store_data['paginas'][page_key]['elementos']

        # Verificar si es una actualización o sobrescritura
        es_actualizacion = selected_name and selected_name == nombre
        sobrescrito = nombre in elementos_pagina and not es_actualizacion

        # Buscar datos de imagen temporal
        temp_img_key = f"temp_img_{nombre}"
        datos_temp = store_data.get(temp_img_key, None)

        # Si estamos editando y no hay imagen temporal, usar la existente
        if not datos_temp and selected_name and selected_name in elementos_pagina:
            if elementos_pagina[selected_name]["tipo"] == "imagen":
                datos_temp = elementos_pagina[selected_name]["imagen"].get("datos_temp", None)

        # Determinar formato y nombre de archivo
        formato = "png"  # Por defecto
        nombre_archivo = f"{nombre}.{formato}"

        # Si tenemos datos de imagen, intentar determinar el formato
        if datos_temp and "data:image/" in datos_temp:
            formato_parte = datos_temp.split(";")[0].split("/")[1]
            if formato_parte:
                formato = formato_parte
                if formato == "jpeg":
                    formato = "jpg"
                nombre_archivo = f"{nombre}.{formato}"
        elif image_url:
            # Intentar extraer nombre de archivo y formato de URL
            try:
                nombre_archivo_url = image_url.split("/")[-1]
                if "." in nombre_archivo_url:
                    ext = nombre_archivo_url.split(".")[-1].lower()
                    if ext in ["png", "jpg", "jpeg", "gif", "bmp", "webp"]:
                        formato = ext
                        if formato == "jpeg":
                            formato = "jpg"
                        nombre_archivo = f"{nombre}.{formato}"
            except:
                pass

        # Crear imagen con la estructura definida
        imagen_datos = {
            "tipo": "imagen",
            "geometria": {
                "x": x,
                "y": y,
                "ancho": ancho,
                "alto": alto
            },
            "estilo": {
                "opacidad": opacidad,
                "mantener_proporcion": mantener_proporcion,
                "reduccion": reduccion
            },
            "imagen": {
                "formato": formato,
                "datos_temp": datos_temp,
                "ruta_original": "",
                "ruta_nueva": f"assets/{nombre_archivo}",
                "nombre_archivo": nombre_archivo,
                "estado": "nueva" if datos_temp else "faltante"
            },
            "grupo": {
                "nombre": "Sin grupo",
                "color": "#cccccc"
            },
            "metadata": {
                "zIndex": zindex,  # Usar zIndex del input
                "visible": True,
                "bloqueado": False
            }
        }

        # Si estamos editando y el nombre ha cambiado, borrar elemento anterior
        if selected_name and selected_name != nombre:
            if selected_name in elementos_pagina:
                del elementos_pagina[selected_name]

        # Limpiar claves temporales
        if temp_img_key in store_data:
            del store_data[temp_img_key]

        # Guardar elemento en el diccionario
        elementos_pagina[nombre] = imagen_datos

        # Preparar mensaje de estado
        if sobrescrito:
            mensaje = f"Se ha sobrescrito la imagen '{nombre}'."
            color_estado = "yellow"
        elif es_actualizacion:
            mensaje = f"Imagen '{nombre}' actualizada correctamente."
            color_estado = "green"
        else:
            mensaje = f"Imagen '{nombre}' creada correctamente."
            color_estado = "green"

        # Si no hay datos de imagen, advertir
        if not imagen_datos["imagen"]["datos_temp"]:
            mensaje += " No se ha cargado ninguna imagen, se mostrará un marcador de posición."
            color_estado = "yellow"

        ocultar_estado = False

        # Cerrar el drawer y retornar la store actualizada con mensaje
        return store_data, False, mensaje, color_estado, ocultar_estado

    # Callback para borrar la imagen seleccionada
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-image-drawer", "opened", allow_duplicate=True),
         Output("image-selector", "value")],
        Input("btn-delete-image", "n_clicks"),
        [State("image-selector", "value"),
        State("store-componentes", "data"),
        State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def borrar_imagen(n_clicks, selected_name, store_data, current_page):
        if not n_clicks or not selected_name:
            return store_data, True, None

        page_key = str(current_page)

        # Verificar si existe la página y sus elementos
        if (page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return store_data, True, None

        elementos_pagina = store_data['paginas'][page_key]['elementos']

        # Eliminar elemento del diccionario de la página actual
        if selected_name in elementos_pagina:
            del elementos_pagina[selected_name]

        # Cerrar el drawer y limpiar la selección
        return store_data, False, None


    # fin imagen callback

    # se genera el pdf a partir del store-data
    @app.callback(
        [Output("ep-canvas-status", "children", allow_duplicate=True),
         Output("ep-canvas-status", "color", allow_duplicate=True),
         Output("ep-canvas-status", "hide", allow_duplicate=True),
         Output("ep-download-pdf", "data")],
        Input("ep-print-pdf-btn", "n_clicks"),
        State("ep-template-name", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def generate_pdf(n_clicks, template_name, store_data):
        if not n_clicks:
            return "", "blue", True, None

        if not template_name:
            return "Por favor, ingrese un nombre para la plantilla", "red", False, None

        try:
            # Crear un buffer para el PDF
            buffer = io.BytesIO()

            # Crear el PDF (no establecemos un tamaño de página aún)
            pdf = canvas.Canvas(buffer)
            pdf.setTitle(f"Plantilla: {template_name}")

            # Actualizar nombre de plantilla en la configuración
            store_data['configuracion']['nombre_plantilla'] = template_name

            # Obtener el número total de páginas
            num_pages = store_data['configuracion']['num_paginas']

            # Iterar sobre todas las páginas
            for page_num in range(1, num_pages + 1):
                page_key = str(page_num)

                # Si no existe la página en el store, continuar con la siguiente
                if page_key not in store_data['paginas']:
                    continue

                # Obtener la orientación específica de esta página
                if "configuracion" in store_data['paginas'][page_key]:
                    orientation = store_data['paginas'][page_key]["configuracion"].get("orientacion", "portrait")
                else:
                    orientation = "portrait"

                # Configurar el tamaño de página según la orientación
                page_size = landscape(A4) if orientation == "landscape" else A4
                page_width, page_height = page_size

                # Si no es la primera página, añadir una nueva página
                if page_num > 1:
                    pdf.showPage()

                # Establecer el tamaño de la página
                pdf.setPageSize(page_size)

                # Obtener los elementos de la página actual
                elementos_pagina = store_data['paginas'][page_key]['elementos']

                # Ordenar elementos por zIndex
                elementos_ordenados = sorted(
                    elementos_pagina.items(),
                    key=lambda x: x[1]["metadata"].get("zIndex", 0)
                )

                # Dibujar cada elemento según su tipo
                for nombre, elemento in elementos_ordenados:
                    try:
                        if elemento["tipo"] == "linea" and elemento["metadata"]["visible"]:
                            # Coordenadas
                            x1 = elemento["geometria"]["x1"] * CM_TO_POINTS
                            y1 = elemento["geometria"]["y1"] * CM_TO_POINTS
                            x2 = elemento["geometria"]["x2"] * CM_TO_POINTS
                            y2 = elemento["geometria"]["y2"] * CM_TO_POINTS

                            # Ajustar Y
                            y1 = page_height - y1
                            y2 = page_height - y2

                            # Configurar estilo
                            pdf.setStrokeColor(elemento["estilo"]["color"])
                            pdf.setLineWidth(elemento["estilo"]["grosor"])

                            # Dibujar línea
                            pdf.line(x1, y1, x2, y2)

                        elif elemento["tipo"] == "rectangulo" and elemento["metadata"]["visible"]:
                            # Coordenadas y dimensiones
                            x = elemento["geometria"]["x"] * CM_TO_POINTS
                            y = elemento["geometria"]["y"] * CM_TO_POINTS
                            ancho = elemento["geometria"]["ancho"] * CM_TO_POINTS
                            alto = elemento["geometria"]["alto"] * CM_TO_POINTS

                            # Ajustar Y
                            y = page_height - y - alto

                            # Configurar estilos
                            pdf.setStrokeColor(elemento["estilo"]["color_borde"])
                            pdf.setLineWidth(elemento["estilo"]["grosor_borde"])
                            pdf.setFillColor(elemento["estilo"]["color_relleno"])
                            opacidad = elemento["estilo"]["opacidad"] / 100

                            # Dibujar
                            pdf.rect(x, y, ancho, alto,
                                     fill=(opacidad > 0),
                                     stroke=(elemento["estilo"]["grosor_borde"] > 0))

                        elif elemento["tipo"] == "imagen" and elemento["metadata"]["visible"]:
                            # Coordenadas y dimensiones
                            x = elemento["geometria"]["x"] * CM_TO_POINTS
                            y = elemento["geometria"]["y"] * CM_TO_POINTS
                            ancho = elemento["geometria"]["ancho"] * CM_TO_POINTS
                            alto = elemento["geometria"]["alto"] * CM_TO_POINTS

                            # Aplicar reducción
                            reduccion = elemento["estilo"].get("reduccion", 0)
                            x += reduccion
                            y += reduccion
                            ancho -= (reduccion * 2)
                            alto -= (reduccion * 2)

                            # Ajustar Y (en ReportLab el origen está en la esquina inferior izquierda)
                            y = page_height - y - alto

                            # Obtener la ruta de la imagen del JSON
                            ruta_imagen = elemento["imagen"].get("ruta_nueva", "")

                            # Buscar la imagen en diversas ubicaciones posibles
                            imagen_encontrada = False
                            if ruta_imagen:
                                # Construir posibles rutas para encontrar la imagen
                                nombre_plantilla = store_data['configuracion'].get('nombre_plantilla', '')
                                posibles_rutas = [
                                    Path(ruta_imagen),  # Ruta directa
                                    Path("plantillas") / nombre_plantilla / ruta_imagen,  # En carpeta de plantilla
                                    Path("plantillas") / nombre_plantilla / "assets" / Path(ruta_imagen).name,  # En assets
                                    Path("assets") / Path(ruta_imagen).name,  # En assets global
                                    Path(Path(ruta_imagen).name)  # Solo el nombre del archivo (directorio actual)
                                ]

                                # Probar cada ruta
                                for ruta in posibles_rutas:
                                    try:
                                        if ruta.exists():
                                            # Configurar parámetros de imagen
                                            preserveAspectRatio = elemento["estilo"].get("mantener_proporcion", True)

                                            # Usar directamente el archivo de imagen
                                            pdf.drawImage(
                                                str(ruta),
                                                x, y,
                                                width=ancho,
                                                height=alto,
                                                preserveAspectRatio=preserveAspectRatio,
                                                mask='auto'
                                            )
                                            imagen_encontrada = True
                                            print(f"Imagen encontrada y dibujada desde: {ruta}")
                                            break
                                    except Exception as e:
                                        print(f"Error con ruta {ruta}: {str(e)}")
                                        continue

                            # Si no se encuentra la imagen, intentar usar los datos base64
                            if not imagen_encontrada and elemento["imagen"].get("datos_temp"):
                                try:
                                    from io import BytesIO
                                    import base64
                                    import tempfile
                                    import os

                                    # Extraer datos base64
                                    img_data = elemento["imagen"]["datos_temp"]
                                    if "," in img_data:  # Si tiene formato "data:image/png;base64,DATOS"
                                        img_data = img_data.split(",")[1]

                                    # Enfoque con archivo temporal
                                    img_binary = base64.b64decode(img_data)

                                    # Crear archivo temporal con la extensión correcta
                                    ext = elemento["imagen"].get("formato", "png")
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_file:
                                        temp_file.write(img_binary)
                                        temp_path = temp_file.name

                                    # Determinar modo de ajuste de imagen
                                    preserveAspectRatio = elemento["estilo"].get("mantener_proporcion", True)

                                    # Dibujar imagen desde archivo temporal
                                    pdf.drawImage(temp_path, x, y, width=ancho, height=alto,
                                                  preserveAspectRatio=preserveAspectRatio, mask='auto')

                                    # Eliminar el archivo temporal
                                    os.unlink(temp_path)
                                    imagen_encontrada = True
                                    print(f"Imagen dibujada desde datos base64 temporales")
                                except Exception as e:
                                    print(f"Error al procesar imagen base64: {str(e)}")

                            # Si no se encontró la imagen, mostrar un rectángulo indicativo
                            if not imagen_encontrada:
                                pdf.setStrokeColor("#999999")
                                pdf.setFillColor("#eeeeee")
                                pdf.rect(x, y, ancho, alto, fill=True, stroke=True)
                                pdf.setFillColor("#666666")
                                pdf.setFont("Helvetica", 8)

                                if ruta_imagen:
                                    pdf.drawCentredString(x + ancho / 2, y + alto / 2, "Imagen no encontrada")
                                    pdf.setFont("Helvetica", 6)
                                    pdf.drawCentredString(x + ancho / 2, y + alto / 2 - 10,
                                                          f"Ruta: {Path(ruta_imagen).name}")
                                else:
                                    pdf.drawCentredString(x + ancho / 2, y + alto / 2, "Sin imagen asignada")
                            elif elemento["tipo"] == "texto" and elemento["metadata"]["visible"]:
                                # Coordenadas y dimensiones
                                x = elemento["geometria"]["x"] * CM_TO_POINTS
                                y = elemento["geometria"]["y"] * CM_TO_POINTS
                                ancho = elemento["geometria"]["ancho"] * CM_TO_POINTS
                                alto = elemento["geometria"]["alto"] * CM_TO_POINTS

                                # Ajustar Y (en ReportLab el origen está en la esquina inferior izquierda)
                                y = page_height - y - alto

                                # Configurar estilos de texto
                                font_name = elemento["estilo"]["familia_fuente"]
                                font_size = elemento["estilo"]["tamano"]

                                # Aplicar negrita/cursiva si es necesario
                                if elemento["estilo"]["negrita"] == "bold" and elemento["estilo"]["cursiva"] == "italic":
                                    font_name = f"{font_name}-BoldItalic"
                                elif elemento["estilo"]["negrita"] == "bold":
                                    font_name = f"{font_name}-Bold"
                                elif elemento["estilo"]["cursiva"] == "italic":
                                    font_name = f"{font_name}-Italic"

                                pdf.setFont(font_name, font_size)
                                pdf.setFillColor(elemento["estilo"]["color"])

                                # Obtener el texto
                                texto = elemento["contenido"]["texto"] or ""

                                # Aplicar rotación si es necesario
                                if elemento["estilo"].get("rotacion", 0) != 0:
                                    pdf.saveState()
                                    # Calcular el centro del área de texto
                                    center_x = x + ancho / 2
                                    center_y = y + alto / 2
                                    # Rotar
                                    pdf.translate(center_x, center_y)
                                    pdf.rotate(elemento["estilo"]["rotacion"])
                                    pdf.translate(-center_x, -center_y)

                                # Procesar el texto según alineación
                                lines = texto.split('\n')

                                # Altura de una línea
                                line_height = font_size * 1.2

                                # Calcular posición vertical inicial según alineación vertical
                                if elemento["estilo"]["alineacion_v"] == "top":
                                    y_pos = y + alto - font_size
                                elif elemento["estilo"]["alineacion_v"] == "middle":
                                    y_pos = y + alto / 2 + (len(lines) * line_height) / 2 - font_size
                                else:  # bottom
                                    y_pos = y + (len(lines) * line_height) - font_size

                                # Dibujar cada línea de texto
                                for line in lines:
                                    # Calcular posición horizontal según alineación
                                    if elemento["estilo"]["alineacion_h"] == "left":
                                        pdf.drawString(x, y_pos, line)
                                    elif elemento["estilo"]["alineacion_h"] == "center":
                                        pdf.drawCentredString(x + ancho / 2, y_pos, line)
                                    elif elemento["estilo"]["alineacion_h"] == "right":
                                        pdf.drawRightString(x + ancho, y_pos, line)
                                    elif elemento["estilo"]["alineacion_h"] == "justify" and line:
                                        # Implementar justificación básica
                                        words = line.split()
                                        if len(words) > 1:
                                            word_width = pdf.stringWidth(line, font_name, font_size) / len(words)
                                            space_width = (ancho - pdf.stringWidth(line, font_name, font_size)) / (
                                                        len(words) - 1)
                                            x_pos = x
                                            for word in words:
                                                pdf.drawString(x_pos, y_pos, word)
                                                x_pos += pdf.stringWidth(word, font_name, font_size) + space_width
                                        else:
                                            pdf.drawString(x, y_pos, line)

                                    # Pasar a la siguiente línea
                                    y_pos -= line_height

                                # Restaurar estado si se aplicó rotación
                                if elemento["estilo"].get("rotacion", 0) != 0:
                                    pdf.restoreState()
                        elif elemento["tipo"] == "texto" and elemento["metadata"]["visible"]:
                            # Coordenadas y dimensiones
                            x = elemento["geometria"]["x"] * CM_TO_POINTS
                            y = elemento["geometria"]["y"] * CM_TO_POINTS
                            ancho = elemento["geometria"]["ancho"] * CM_TO_POINTS
                            alto = elemento["geometria"]["alto"] * CM_TO_POINTS

                            # Ajustar Y (en ReportLab el origen está en la esquina inferior izquierda)
                            y = page_height - y - alto

                            # Configurar estilos de texto
                            font_name = elemento["estilo"]["familia_fuente"]
                            font_size = elemento["estilo"]["tamano"]

                            # Aplicar negrita/cursiva si es necesario
                            if elemento["estilo"]["negrita"] == "bold" and elemento["estilo"]["cursiva"] == "italic":
                                font_name = f"{font_name}-BoldItalic"
                            elif elemento["estilo"]["negrita"] == "bold":
                                font_name = f"{font_name}-Bold"
                            elif elemento["estilo"]["cursiva"] == "italic":
                                font_name = f"{font_name}-Italic"

                            pdf.setFont(font_name, font_size)
                            pdf.setFillColor(elemento["estilo"]["color"])

                            # Obtener el texto
                            texto = elemento["contenido"]["texto"] or ""

                            # Aplicar rotación si es necesario
                            if elemento["estilo"].get("rotacion", 0) != 0:
                                pdf.saveState()
                                # Calcular el centro del área de texto
                                center_x = x + ancho / 2
                                center_y = y + alto / 2
                                # Rotar
                                pdf.translate(center_x, center_y)
                                pdf.rotate(elemento["estilo"]["rotacion"])
                                pdf.translate(-center_x, -center_y)

                            # Procesar el texto según alineación
                            lines = texto.split('\n')

                            # Altura de una línea
                            line_height = font_size * 1.2

                            # Calcular posición vertical inicial según alineación vertical
                            if elemento["estilo"]["alineacion_v"] == "top":
                                y_pos = y + alto - font_size
                            elif elemento["estilo"]["alineacion_v"] == "middle":
                                y_pos = y + alto / 2 + (len(lines) * line_height) / 2 - font_size
                            else:  # bottom
                                y_pos = y + (len(lines) * line_height) - font_size

                            # Dibujar cada línea de texto
                            for line in lines:
                                # Calcular posición horizontal según alineación
                                if elemento["estilo"]["alineacion_h"] == "left":
                                    pdf.drawString(x, y_pos, line)
                                elif elemento["estilo"]["alineacion_h"] == "center":
                                    pdf.drawCentredString(x + ancho / 2, y_pos, line)
                                elif elemento["estilo"]["alineacion_h"] == "right":
                                    pdf.drawRightString(x + ancho, y_pos, line)
                                elif elemento["estilo"]["alineacion_h"] == "justify" and line:
                                    # Implementar justificación básica
                                    words = line.split()
                                    if len(words) > 1:
                                        word_width = pdf.stringWidth(line, font_name, font_size) / len(words)
                                        space_width = (ancho - pdf.stringWidth(line, font_name, font_size)) / (
                                                    len(words) - 1)
                                        x_pos = x
                                        for word in words:
                                            pdf.drawString(x_pos, y_pos, word)
                                            x_pos += pdf.stringWidth(word, font_name, font_size) + space_width
                                    else:
                                        pdf.drawString(x, y_pos, line)

                                # Pasar a la siguiente línea
                                y_pos -= line_height

                            # Restaurar estado si se aplicó rotación
                            if elemento["estilo"].get("rotacion", 0) != 0:
                                pdf.restoreState()

                    except Exception as e:
                        print(f"Error al procesar elemento {nombre}: {str(e)}")
                        continue

            pdf.save()
            buffer.seek(0)

            # Retornar los datos para la descarga
            return ("PDF generado con éxito", "green", False,
                    dcc.send_bytes(buffer.getvalue(), f"{template_name}.pdf"))

        except Exception as e:
            return f"Error al generar PDF: {str(e)}", "red", False, None

    # Callback para mostrar el contenido del store en formato JSON
    @app.callback(
        Output("json-viewer", "children"),
        Input("store-componentes", "data")
    )
    def update_json_viewer(store_data):
        # Formatear el JSON para una mejor visualización
        import json
        formatted_json = json.dumps(store_data, indent=2, ensure_ascii=False)
        return formatted_json

    # Callback para procesar el archivo JSON cargado
    @app.callback(
        [Output('store-componentes', 'data', allow_duplicate=True),
         Output('ep-canvas-status', 'children', allow_duplicate=True),
         Output('ep-canvas-status', 'color', allow_duplicate=True),
         Output('ep-canvas-status', 'hide', allow_duplicate=True),
         Output('ep-page-number', 'value', allow_duplicate=True),
         Output('ep-orientation-selector', 'value', allow_duplicate=True)],
        Input('ep-upload-json', 'contents'),
        State('ep-upload-json', 'filename'),
        State('store-componentes', 'data'),
        prevent_initial_call=True
    )
    def process_json_upload(contents, filename, store_data):
        if contents is None:
            return store_data, "", "blue", True, dash.no_update, dash.no_update

        try:
            # Decodificar y cargar el JSON
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            loaded_data = json.loads(decoded)

            # Función para asegurarse de que los textos tengan la propiedad editable
            def ensure_editable_property(elementos):
                if not elementos:
                    return

                for nombre, elemento in elementos.items():
                    if elemento.get("tipo") == "texto" and "contenido" in elemento:
                        if "editable" not in elemento["contenido"]:
                            elemento["contenido"]["editable"] = False

            # Comprobar si el JSON tiene la nueva estructura de múltiples páginas
            if 'paginas' in loaded_data:
                # Verificar que cada página tiene configuración de orientación
                for page_key, page_data in loaded_data['paginas'].items():
                    if "configuracion" not in page_data:
                        page_data["configuracion"] = {"orientacion": "portrait"}
                    elif "orientacion" not in page_data["configuracion"]:
                        page_data["configuracion"]["orientacion"] = "portrait"

                    # Asegurarse de que los textos tengan la propiedad editable
                    if "elementos" in page_data:
                        ensure_editable_property(page_data["elementos"])

                store_data = loaded_data
            else:
                # Convertir estructura antigua a nueva
                orientacion = loaded_data.get('configuracion', {}).get('orientacion', 'portrait')

                # Asegurarse de que los textos tengan la propiedad editable
                if "elementos" in loaded_data:
                    ensure_editable_property(loaded_data["elementos"])

                store_data = {
                    'paginas': {
                        "1": {
                            'elementos': loaded_data.get('elementos', {}),
                            'configuracion': {
                                'orientacion': orientacion
                            }
                        }
                    },
                    'pagina_actual': "1",
                    'seleccionado': loaded_data.get('seleccionado', None),
                    'configuracion': {
                        'nombre_plantilla': loaded_data.get('configuracion', {}).get('nombre_plantilla', ''),
                        'version': loaded_data.get('configuracion', {}).get('version', '1.0'),
                        'num_paginas': 1
                    }
                }

            # Obtener la orientación de la primera página
            orientation = "portrait"
            if "1" in store_data['paginas'] and "configuracion" in store_data['paginas']["1"]:
                orientation = store_data['paginas']["1"]["configuracion"].get("orientacion", "portrait")

            return store_data, f"JSON '{filename}' cargado correctamente", "green", False, 1, orientation

        except Exception as e:
            return store_data, f"Error al cargar JSON: {str(e)}", "red", False, dash.no_update, dash.no_update

    # Callback para guardar el JSON al hacer clic en "Guardar JSON"
    # 1. Mostrar el modal al hacer clic en "Guardar JSON"
    @app.callback(
        [Output("modal-save-json", "opened"),
         Output("json-filename-input", "value")],
        Input("ep-save-json-btn", "n_clicks"),
        State("ep-template-name", "value"),
        prevent_initial_call=True
    )
    def show_save_json_modal(n_clicks, template_name):
        if not n_clicks:
            return False, ""

        # Proponer un nombre de archivo basado en el nombre de la plantilla
        suggested_filename = ""
        if template_name:
            suggested_filename = template_name.replace(" ", "_")

        return True, suggested_filename

    # 2. Cerrar el modal al hacer clic en "Cancelar"
    @app.callback(
        Output("modal-save-json", "opened", allow_duplicate=True),
        Input("btn-cancel-save-json", "n_clicks"),
        prevent_initial_call=True
    )
    def cancel_save_json(n_clicks):
        if n_clicks:
            return False
        return False

    # 3. Guardar el JSON al hacer clic en "Guardar" en el modal
    @app.callback(
        [Output("modal-save-json", "opened", allow_duplicate=True),
         Output("ep-download-json", "data"),
         Output("ep-canvas-status", "children", allow_duplicate=True),
         Output("ep-canvas-status", "color", allow_duplicate=True),
         Output("ep-canvas-status", "hide", allow_duplicate=True),
         Output("store-componentes", "data", allow_duplicate=True)],  # Añadimos output para actualizar el store
        Input("btn-confirm-save-json", "n_clicks"),
        State("json-filename-input", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def save_json_with_custom_name(n_clicks, filename, store_data):
        if not n_clicks or not filename:
            return True, None, "", "blue", True, store_data

        try:
            import json
            import os
            import base64
            import shutil  # Añadimos esta importación para copiar archivos
            from io import BytesIO
            from pathlib import Path
            from datetime import datetime

            # Asegurarse de que el nombre del archivo termine con .json
            if not filename.lower().endswith('.json'):
                filename = f"{filename}.json"

            # Obtener el nombre base del archivo (sin extensión) para usar como nombre de grupo
            grupo_nombre = filename.replace('.json', '')

            # Crear estructura de carpetas
            plantillas_dir = Path('biblioteca_plantillas')
            plantillas_dir.mkdir(exist_ok=True)

            plantilla_dir = plantillas_dir / grupo_nombre
            plantilla_dir.mkdir(exist_ok=True)

            assets_dir = plantilla_dir / 'assets'
            assets_dir.mkdir(exist_ok=True)

            # Función para procesar imágenes en un diccionario de elementos
            def process_images_in_elementos(elementos):
                if not elementos:
                    return

                for nombre, elemento in elementos.items():
                    if 'grupo' in elemento:
                        elemento['grupo']['nombre'] = grupo_nombre

                    # Procesar imágenes si son del tipo 'imagen'
                    if elemento.get("tipo") == "imagen":
                        try:
                            # CASO 1: Si tiene datos_temp, guardar la imagen desde esos datos
                            if elemento["imagen"].get("datos_temp"):
                                try:
                                    img_data = elemento["imagen"]["datos_temp"]
                                    if "," in img_data:  # Si tiene formato "data:image/png;base64,DATOS"
                                        img_data = img_data.split(",")[1]

                                    img_binary = base64.b64decode(img_data)

                                    # Generar nombre de archivo
                                    nombre_archivo = elemento["imagen"]["nombre_archivo"]
                                    if not nombre_archivo:
                                        formato = elemento["imagen"]["formato"] or "png"
                                        nombre_archivo = f"{nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{formato}"

                                    # Ruta completa del archivo
                                    img_path = assets_dir / nombre_archivo

                                    # Guardar imagen
                                    with open(img_path, 'wb') as f:
                                        f.write(img_binary)

                                    # Actualizar la ruta en el JSON - IMPORTANTE: usar ruta relativa a la plantilla
                                    elemento["imagen"]["ruta_nueva"] = f"assets/{nombre_archivo}"
                                    elemento["imagen"]["estado"] = "guardada"

                                    # Para depuración, imprimir la ruta
                                    print(f"Imagen guardada en: {img_path}")
                                except Exception as e:
                                    print(f"Error al guardar imagen {nombre}: {str(e)}")

                            # CASO 2: Si no tiene datos_temp pero tiene ruta_nueva, intentar copiar el archivo
                            elif elemento["imagen"].get("ruta_nueva"):
                                ruta_origen = elemento["imagen"]["ruta_nueva"]
                                if ruta_origen:
                                    nombre_archivo = os.path.basename(ruta_origen)

                                    # Buscar el archivo en posibles ubicaciones
                                    paths_to_check = [
                                        Path(ruta_origen),  # Ruta directa
                                        plantillas_dir / grupo_nombre.replace('.json', '') / ruta_origen,
                                        # En carpeta actual
                                        # Buscar en todas las subcarpetas de plantillas
                                        *[p / ruta_origen for p in plantillas_dir.glob("*") if p.is_dir()],
                                        *[p / "assets" / nombre_archivo for p in plantillas_dir.glob("*") if p.is_dir()]
                                    ]

                                    found = False
                                    for p in paths_to_check:
                                        if p.exists():
                                            # Copiar el archivo
                                            destino = assets_dir / nombre_archivo
                                            shutil.copy2(p, destino)
                                            found = True
                                            elemento["imagen"]["estado"] = "copiada"
                                            print(f"Imagen copiada de {p} a {destino}")
                                            break

                                    if not found:
                                        print(f"No se pudo encontrar la imagen {ruta_origen}")
                                        elemento["imagen"]["estado"] = "no encontrada"
                        except Exception as e:
                            print(f"Error al procesar imagen {nombre}: {str(e)}")

            # Procesar imágenes en todas las páginas
            if 'paginas' in store_data:
                for page_key, page_data in store_data['paginas'].items():
                    if 'elementos' in page_data:
                        process_images_in_elementos(page_data['elementos'])
            elif 'elementos' in store_data:  # Para compatibilidad con formato antiguo
                process_images_in_elementos(store_data['elementos'])

            # Actualizar el nombre de la plantilla en la configuración si existe
            if 'configuracion' in store_data:
                store_data['configuracion']['nombre_plantilla'] = grupo_nombre

            # Convertir el store a JSON
            json_string = json.dumps(store_data, indent=2, ensure_ascii=False)

            # Guardar el JSON
            json_path = plantilla_dir / filename
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(json_string)

            # También enviamos el JSON como descarga para compatibilidad con versiones anteriores
            return False, dcc.send_string(json_string,
                                          filename), f"JSON guardado como '{filename}' en la carpeta biblioteca_plantillas/{grupo_nombre}", "green", False, store_data

        except Exception as e:
            return False, None, f"Error al guardar JSON: {str(e)}", "red", False, store_data

    # borrar
    @app.callback(
        Output("ep-canvas-status", "children", allow_duplicate=True),
        Output("ep-canvas-status", "color", allow_duplicate=True),
        Output("ep-canvas-status", "hide", allow_duplicate=True),
        Input("text-editable", "checked"),
        prevent_initial_call=True
    )
    def show_checkbox_value(value):
        return f"Checkbox editable cambiado a: {value}", "blue", False
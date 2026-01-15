# /pages/configuracion_plantilla_claude.py
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
                    'elementos': {},  # Cambiado de lista a diccionario
                    'seleccionado': None,  # Ahora será el nombre del elemento seleccionado
                    'configuracion': {
                        'orientacion': 'portrait',
                        'nombre_plantilla': '',
                        'version': '1.0',
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
                            )
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
                                    value=True,
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
                                    value=True,
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

        # Función para convertir cm a píxeles escalados
        def cm_a_px(cm_value):
            return cm_value * CM_TO_POINTS * SCALE_FACTOR

        elementos_canvas = []

        # Recorrer diccionario en lugar de lista
        for nombre, elemento in store_data['elementos'].items():
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
                )

                elementos_canvas.append(texto_element)

        return canvas_style, horizontal_ruler_style, horizontal_marks, vertical_ruler_style, vertical_marks, elementos_canvas

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

        # Generar nombre sugerido
        if 'elementos' in store_data:
            # Contar líneas existentes
            lineas_existentes = [nombre for nombre, elem in store_data['elementos'].items()
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
        State("line-selector", "value"),
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
        prevent_initial_call=True
    )
    def crear_actualizar_linea(n_clicks, selected_line_name, x1, y1, x2, y2, grosor, color, nombre, zindex, store_data,
                               orientacion):
        if not n_clicks:
            return store_data, False, "", "blue", True

        # Inicializar elementos si es necesario
        if 'elementos' not in store_data:
            store_data['elementos'] = {}

        # Verificar si es una actualización o sobrescritura
        es_actualizacion = selected_line_name and selected_line_name == nombre
        sobrescrito = nombre in store_data['elementos'] and not es_actualizacion

        # Crear línea con la nueva estructura
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
            if selected_line_name in store_data['elementos']:
                del store_data['elementos'][selected_line_name]

        # Guardar elemento en el diccionario
        store_data['elementos'][nombre] = linea_datos

        # Actualizar la orientación en la configuración
        store_data['configuracion']['orientacion'] = orientacion

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
        Input("btn-delete-line", "n_clicks"),
        State("line-selector", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def borrar_linea(n_clicks, selected_line_name, store_data):
        if not n_clicks or not selected_line_name:
            return store_data, True, None

        # Eliminar elemento del diccionario
        if selected_line_name in store_data['elementos']:
            del store_data['elementos'][selected_line_name]

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
            return False, "Rectángulo 1"

        # Generar nombre sugerido
        if 'elementos' in store_data:
            # Contar rectángulos existentes
            rects_existentes = [nombre for nombre, elem in store_data['elementos'].items()
                                if elem["tipo"] == "rectangulo"]

            # Encontrar el siguiente número disponible
            num = 1
            while f"Rectángulo {num}" in rects_existentes:
                num += 1

            nombre_sugerido = f"Rectángulo {num}"
        else:
            nombre_sugerido = "Rectángulo 1"

        return True, nombre_sugerido




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
            {"value": nombre, "label": nombre}
            for nombre, elemento in store_data['elementos'].items()
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
         Output("line-zindex", "value")],  # Nuevo output
        Input("line-selector", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def fill_line_form(selected_line_name, store_data):
        if not selected_line_name or 'elementos' not in store_data:
            # Valores por defecto
            return 1.0, 1.0, 5.0, 5.0, 1, "#000000", "Línea 1", 10  # Valor por defecto de zIndex

        # Obtener el elemento directamente del diccionario
        if selected_line_name in store_data['elementos']:
            elemento = store_data['elementos'][selected_line_name]
            if elemento["tipo"] == "linea":
                # Devolver los valores
                return (
                    elemento["geometria"]["x1"],
                    elemento["geometria"]["y1"],
                    elemento["geometria"]["x2"],
                    elemento["geometria"]["y2"],
                    elemento["estilo"]["grosor"],
                    elemento["estilo"]["color"],
                    selected_line_name,
                    elemento["metadata"].get("zIndex", 10)  # Obtener zIndex o valor predeterminado
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
        Input("store-componentes", "data")
    )
    def update_rectangle_selector(store_data):
        if not store_data or 'elementos' not in store_data:
            return []

        # Crear opciones para el selector solo con los rectángulos
        options = [
            {"value": nombre, "label": nombre}
            for nombre, elemento in store_data['elementos'].items()
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
         Output("rectangle-zindex", "value")],  # Nuevo output
        Input("rectangle-selector", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def fill_rectangle_form(selected_rectangle_name, store_data):
        if not selected_rectangle_name or 'elementos' not in store_data:
            # Valores por defecto
            return 1.0, 1.0, 5.0, 3.0, 1, "#000000", "#FFFFFF", 100, "Rectángulo 1", 5  # Valor por defecto de zIndex

        # Obtener el elemento directamente del diccionario
        if selected_rectangle_name in store_data['elementos']:
            elemento = store_data['elementos'][selected_rectangle_name]
            if elemento["tipo"] == "rectangulo":
                # Devolver los valores
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
                    elemento["metadata"].get("zIndex", 5)  # Obtener zIndex o valor predeterminado
                )

        # Si no se encuentra
        return 1.0, 1.0, 5.0, 3.0, 1, "#000000", "#FFFFFF", 100, "Rectángulo 1", 5


    # Callback para crear/actualizar rectángulos
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-rectangle-drawer", "opened", allow_duplicate=True),
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
        State("rectangle-zindex", "value"),  # Incluir zIndex
        State("store-componentes", "data"),
        State("ep-orientation-selector", "value"),
        prevent_initial_call=True
    )
    def crear_actualizar_rectangulo(n_clicks, selected_name, x, y, ancho, alto, grosor_borde,
                                    color_borde, color_relleno, opacidad, nombre, zindex, store_data, orientacion):
        if not n_clicks:
            return store_data, False, "", "blue", True

        # Inicializar elementos si es necesario
        if 'elementos' not in store_data:
            store_data['elementos'] = {}

        # Verificar si es una actualización o sobrescritura
        es_actualizacion = selected_name and selected_name == nombre
        sobrescrito = nombre in store_data['elementos'] and not es_actualizacion

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
            if selected_name in store_data['elementos']:
                del store_data['elementos'][selected_name]

        # Guardar elemento en el diccionario
        store_data['elementos'][nombre] = rect_datos

        # Actualizar la orientación en la configuración
        store_data['configuracion']['orientacion'] = orientacion

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
        State("rectangle-selector", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def borrar_rectangulo(n_clicks, selected_name, store_data):
        if not n_clicks or not selected_name:
            return store_data, True, None

        # Eliminar elemento del diccionario
        if selected_name in store_data['elementos']:
            del store_data['elementos'][selected_name]

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
            return False, "Texto 1"

        # Generar nombre sugerido
        if 'elementos' in store_data:
            # Contar textos existentes
            textos_existentes = [nombre for nombre, elem in store_data['elementos'].items()
                                 if elem["tipo"] == "texto"]

            # Encontrar el siguiente número disponible
            num = 1
            while f"Texto {num}" in textos_existentes:
                num += 1

            nombre_sugerido = f"Texto {num}"
        else:
            nombre_sugerido = "Texto 1"

        return True, nombre_sugerido

    # Callback para actualizar la lista de textos en el selector
    @app.callback(
        Output("text-selector", "data"),
        Input("store-componentes", "data")
    )
    def update_text_selector(store_data):
        if not store_data or 'elementos' not in store_data:
            return []

        # Crear opciones para el selector solo con los textos
        options = [
            {"value": nombre, "label": nombre}
            for nombre, elemento in store_data['elementos'].items()
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
         Output("text-auto-adjust", "value"),
         Output("text-content", "value"),
         Output("text-nombre", "value", allow_duplicate=True),
         Output("text-zindex", "value")],
        Input("text-selector", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def fill_text_form(selected_text_name, store_data):
        if not selected_text_name or 'elementos' not in store_data:
            # Valores por defecto
            return 1.0, 1.0, 5.0, 2.0, 0, "Helvetica", 10, "normal", "normal", "#000000", "left", "top", True, "", "Texto 1", 20

        # Obtener el elemento directamente del diccionario
        if selected_text_name in store_data['elementos']:
            elemento = store_data['elementos'][selected_text_name]
            if elemento["tipo"] == "texto":
                # Devolver los valores
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
                    elemento["metadata"].get("zIndex", 20)
                )

        # Si no se encuentra
        return 1.0, 1.0, 5.0, 2.0, 0, "Helvetica", 10, "normal", "normal", "#000000", "left", "top", True, "", "Texto 1", 20

    # Callback para crear/actualizar textos
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-text-drawer", "opened", allow_duplicate=True),
         Output("ep-canvas-status", "children", allow_duplicate=True),
         Output("ep-canvas-status", "color", allow_duplicate=True),
         Output("ep-canvas-status", "hide", allow_duplicate=True)],
        Input("btn-create-text", "n_clicks"),
        State("text-selector", "value"),
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
        State("text-auto-adjust", "value"),
        State("text-content", "value"),
        State("text-nombre", "value"),
        State("text-zindex", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def crear_actualizar_texto(n_clicks, selected_name, x, y, ancho, alto, rotacion,
                               familia_fuente, tamano, negrita, cursiva, color,
                               alineacion_h, alineacion_v, ajuste_automatico,
                               contenido_texto, nombre, zindex, store_data):
        if not n_clicks:
            return store_data, False, "", "blue", True

        # Inicializar elementos si es necesario
        if 'elementos' not in store_data:
            store_data['elementos'] = {}

        # Verificar si es una actualización o sobrescritura
        es_actualizacion = selected_name and selected_name == nombre
        sobrescrito = nombre in store_data['elementos'] and not es_actualizacion

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
                "ajuste_automatico": ajuste_automatico
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
            if selected_name in store_data['elementos']:
                del store_data['elementos'][selected_name]

        # Guardar elemento en el diccionario
        store_data['elementos'][nombre] = texto_datos

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
        State("text-selector", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def borrar_texto(n_clicks, selected_name, store_data):
        if not n_clicks or not selected_name:
            return store_data, True, None

        # Eliminar elemento del diccionario
        if selected_name in store_data['elementos']:
            del store_data['elementos'][selected_name]

        # Cerrar el drawer y limpiar la selección
        return store_data, False, None

    # fin callbacks texto

    # Callback para abrir el drawer de imagen
    @app.callback(
        [Output("ep-image-drawer", "opened"),
         Output("image-nombre", "value"),
         Output("image-maintain-aspect-ratio", "value", allow_duplicate=True)],  # Añadir este output
        Input("ep-add-image-btn", "n_clicks"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def open_image_drawer(n_clicks, store_data):
        if not n_clicks:
            return False, "Imagen 1", True

        # Generar nombre sugerido
        if 'elementos' in store_data:
            # Contar imágenes existentes
            imgs_existentes = [nombre for nombre, elem in store_data['elementos'].items()
                               if elem["tipo"] == "imagen"]

            # Encontrar el siguiente número disponible
            num = 1
            while f"Imagen {num}" in imgs_existentes:
                num += 1

            nombre_sugerido = f"Imagen {num}"
        else:
            nombre_sugerido = "Imagen 1"

        return True, nombre_sugerido, True  # Forzar que el checkbox esté activado


    # ------
    # Callback para actualizar la lista de imágenes en el selectbox
    @app.callback(
        Output("image-selector", "data"),
        Input("store-componentes", "data")
    )
    def update_image_selector(store_data):
        if not store_data or 'elementos' not in store_data:
            return []

        # Crear opciones para el selector solo con las imágenes
        options = [
            {"value": nombre, "label": nombre}
            for nombre, elemento in store_data['elementos'].items()
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
         Output("image-maintain-aspect-ratio", "value", allow_duplicate=True),  # Añadir allow_duplicate=True aquí
         Output("image-nombre", "value", allow_duplicate=True),
         Output("image-zindex", "value"),
         Output("image-reduction", "value")],
        Input("image-selector", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def fill_image_form(selected_image_name, store_data):
        if not selected_image_name or 'elementos' not in store_data:
            # Valores por defecto
            return 1.0, 1.0, 5.0, 3.0, 100, True, "Imagen 1", 15, 0  # Añadir valor por defecto de reducción

        # Obtener el elemento directamente del diccionario
        if selected_image_name in store_data['elementos']:
            elemento = store_data['elementos'][selected_image_name]
            if elemento["tipo"] == "imagen":
                # Devolver los valores
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
        State("image-selector", "value"),
        State("image-x", "value"),
        State("image-y", "value"),
        State("image-width", "value"),
        State("image-height", "value"),
        State("image-opacity", "value"),
        State("image-maintain-aspect-ratio", "value"),
        State("image-nombre", "value"),
        State("image-zindex", "value"),
        State("image-reduction", "value"),  # Nuevo parámetro
        State("store-componentes", "data"),
        State("image-url", "value"),
        prevent_initial_call=True
    )
    def crear_actualizar_imagen(n_clicks, selected_name, x, y, ancho, alto, opacidad, mantener_proporcion,
                                nombre, zindex, reduccion, store_data, image_url):
        if not n_clicks:
            return store_data, False, "", "blue", True

        # Inicializar elementos si es necesario
        if 'elementos' not in store_data:
            store_data['elementos'] = {}

        # Verificar si es una actualización o sobrescritura
        es_actualizacion = selected_name and selected_name == nombre
        sobrescrito = nombre in store_data['elementos'] and not es_actualizacion

        # Buscar datos de imagen temporal
        temp_img_key = f"temp_img_{nombre}"
        datos_temp = store_data.get(temp_img_key, None)

        # Si estamos editando y no hay imagen temporal, usar la existente
        if not datos_temp and selected_name and selected_name in store_data['elementos']:
            if store_data['elementos'][selected_name]["tipo"] == "imagen":
                datos_temp = store_data['elementos'][selected_name]["imagen"].get("datos_temp", None)

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
            if selected_name in store_data['elementos']:
                del store_data['elementos'][selected_name]

        # Limpiar claves temporales
        if temp_img_key in store_data:
            del store_data[temp_img_key]

        # Guardar elemento en el diccionario
        store_data['elementos'][nombre] = imagen_datos

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
        State("image-selector", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def borrar_imagen(n_clicks, selected_name, store_data):
        if not n_clicks or not selected_name:
            return store_data, True, None

        # Eliminar elemento del diccionario
        if selected_name in store_data['elementos']:
            del store_data['elementos'][selected_name]

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

            # Ordenar elementos por zIndex (de menor a mayor para que los de mayor zIndex queden encima)
            elementos_ordenados = sorted(
                store_data['elementos'].items(),
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
         Output('ep-canvas-status', 'hide', allow_duplicate=True)],
        Input('ep-upload-json', 'contents'),
        State('ep-upload-json', 'filename'),
        State('store-componentes', 'data'),
        prevent_initial_call=True
    )
    def process_json_upload(contents, filename, store_data):
        if contents is None:
            return store_data, "", "blue", True

        import base64
        import json
        import os
        from pathlib import Path

        try:
            # Decodificar el contenido del archivo
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)

            # Parsear el JSON
            loaded_data = json.loads(decoded)

            # Inicializar store si es necesario
            if 'elementos' not in store_data:
                store_data['elementos'] = {}

            # Obtener ruta del archivo cargado (si es posible)
            json_path = None
            try:
                # Intentar buscar en carpeta plantillas
                plantillas_dir = Path('plantillas')
                for root, dirs, files in os.walk(plantillas_dir):
                    if filename in files:
                        json_path = Path(root)
                        break
            except:
                json_path = None

            # Procesar elementos del JSON y agregarlos al store
            for nombre, elemento in loaded_data.get('elementos', {}).items():
                # Crear nuevo nombre combinando nombre del elemento y grupo
                grupo = elemento.get('grupo', {}).get('nombre', 'Sin grupo')
                nuevo_nombre = f"{grupo}_{nombre}"

                # Verificar si ya existe un elemento con el mismo nombre
                nombre_base = nuevo_nombre
                contador = 1
                while nuevo_nombre in store_data['elementos']:
                    nuevo_nombre = f"{nombre_base} {contador}"
                    contador += 1

                # Si es una imagen, intentar cargar los datos de la imagen
                if elemento["tipo"] == "imagen":
                    try:
                        # Intentar buscar la imagen en las rutas relacionadas
                        ruta_imagen = elemento["imagen"].get("ruta_nueva", "")
                        if ruta_imagen and json_path:
                            # Intentar varias ubicaciones posibles
                            posibles_rutas = [
                                json_path / ruta_imagen,  # Relativa a la carpeta del JSON
                                json_path / 'assets' / os.path.basename(ruta_imagen),  # En la carpeta assets
                                plantillas_dir / grupo / ruta_imagen  # En la carpeta de la plantilla
                            ]

                            imagen_cargada = False
                            for ruta in posibles_rutas:
                                if ruta.exists():
                                    with open(ruta, 'rb') as f:
                                        img_binary = f.read()
                                        img_base64 = base64.b64encode(img_binary).decode('utf-8')
                                        formato = elemento["imagen"].get("formato", "png")
                                        elemento["imagen"]["datos_temp"] = f"data:image/{formato};base64,{img_base64}"
                                        elemento["imagen"]["estado"] = "cargada"
                                        imagen_cargada = True
                                        break

                            if not imagen_cargada and elemento["imagen"].get("datos_temp"):
                                # Si no encontramos la imagen pero tenemos datos base64, los mantenemos
                                elemento["imagen"]["estado"] = "temporal"
                            elif not imagen_cargada:
                                elemento["imagen"]["estado"] = "faltante"

                    except Exception as e:
                        print(f"Error al cargar imagen: {str(e)}")
                        if elemento["imagen"].get("datos_temp"):
                            elemento["imagen"]["estado"] = "temporal"
                        else:
                            elemento["imagen"]["estado"] = "faltante"

                # Agregar el elemento con el nuevo nombre
                store_data['elementos'][nuevo_nombre] = elemento

            # Actualizar configuración si existe en el JSON
            if 'configuracion' in loaded_data:
                store_data['configuracion'] = loaded_data['configuracion']

            return store_data, f"JSON '{filename}' cargado correctamente", "green", False

        except Exception as e:
            return store_data, f"Error al cargar JSON: {str(e)}", "red", False

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
            from io import BytesIO
            from pathlib import Path

            # Asegurarse de que el nombre del archivo termine con .json
            if not filename.lower().endswith('.json'):
                filename = f"{filename}.json"

            # Obtener el nombre base del archivo (sin extensión) para usar como nombre de grupo
            grupo_nombre = filename.replace('.json', '')

            # Crear estructura de carpetas
            plantillas_dir = Path('plantillas')
            plantillas_dir.mkdir(exist_ok=True)

            plantilla_dir = plantillas_dir / grupo_nombre
            plantilla_dir.mkdir(exist_ok=True)

            assets_dir = plantilla_dir / 'assets'
            assets_dir.mkdir(exist_ok=True)

            # Actualizar el nombre del grupo en cada elemento y guardar imágenes
            if 'elementos' in store_data:
                for nombre, elemento in store_data['elementos'].items():
                    if 'grupo' in elemento:
                        elemento['grupo']['nombre'] = grupo_nombre

                    # Guardar imágenes en assets si son del tipo 'imagen'
                    if elemento["tipo"] == "imagen" and elemento["imagen"]["datos_temp"]:
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

            # Convertir el store a JSON
            json_string = json.dumps(store_data, indent=2, ensure_ascii=False)

            # Guardar el JSON
            json_path = plantilla_dir / filename
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(json_string)

            # También enviamos el JSON como descarga para compatibilidad con versiones anteriores
            return False, dcc.send_string(json_string,
                                          filename), f"JSON guardado como '{filename}' en la carpeta plantillas/{grupo_nombre}", "green", False, store_data

        except Exception as e:
            return False, None, f"Error al guardar JSON: {str(e)}", "red", False, store_data
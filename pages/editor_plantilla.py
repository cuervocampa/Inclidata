# /pages/editor_plantilla.py
import dash
from dash import html, dcc, callback
from dash.dependencies import Input, Output, State, ALL
import dash_mantine_components as dmc
#from dash_mantine_components import Prism  # Añade esta importación
from dash_iconify import DashIconify
import base64
import os
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from pathlib import Path
import io
from datetime import datetime

from utils.funciones_configuracion_plantilla import actualizar_orientacion_y_reglas
from utils.funciones_grupos import listar_grupos_disponibles, leer_datos_grupo, copiar_assets_grupo, guardar_nuevo_grupo
import uuid



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
                    dmc.GridCol([
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
                                    size="xs"
                                ),
                                dmc.Button(
                                    "→",
                                    id="ep-next-page-btn",
                                    variant="outline",
                                    size="xs"
                                ),
                                dmc.Button(
                                    "Añadir página",
                                    id="ep-add-page-btn",
                                    leftSection=DashIconify(icon="mdi:file-plus-outline"),
                                    variant="outline",
                                    color="blue"
                                ),
                            ], justify="flex-end", gap="1"),
                        ], justify="flex-start", gap="1"),
                    ], span=12, mb=10),

                    # NUEVA FILA - Áreas de carga divididas (1/3 Grupo, 2/3 Plantilla)
                    # NUEVA FILA - Áreas de carga divididas (2/3 Plantilla, 1/3 Grupo)
                    dmc.GridCol([
                        dmc.Grid([
                            # Zona Cargar Plantilla (2/3) - IZQUIERDA
                            dmc.GridCol([
                                dmc.Paper(
                                    children=[
                                        dcc.Upload(
                                            id='ep-upload-json',
                                            children=dmc.Group([
                                                DashIconify(icon="mdi:file-document-outline", width=30, height=30, color="blue"),
                                                html.Div([
                                                    dmc.Text("Arrastra PLANTILLA aquí", size="sm", fw=500),
                                                    dmc.Text("Reemplazar todo", size="xs", c="dimmed", ta="center")
                                                ])
                                            ], justify="center", gap="md"),
                                            style={'width': '100%', 'cursor': 'pointer', 'padding': '10px'},
                                            multiple=False,
                                            accept=".json"
                                        )
                                    ],
                                    p="md",
                                    withBorder=True,
                                    shadow="xs",
                                    radius="md",
                                    style={
                                        "backgroundColor": "#e7f5ff", 
                                        "height": "120px", 
                                        "display": "flex", 
                                        "flexDirection": "column", 
                                        "alignItems": "center", 
                                        "justifyContent": "center"
                                    },
                                )
                            ], span=8),

                            # Zona Importar Grupo (1/3) - DERECHA
                            dmc.GridCol([
                                dmc.Paper(
                                    children=[
                                        dcc.Upload(
                                            id='ep-upload-group',
                                            children=dmc.Stack([
                                                DashIconify(icon="mdi:package-variant-closed", width=30, height=30, color="grape"),
                                                dmc.Text("Arrastra GRUPO aquí", size="sm", fw=500),
                                                dmc.Text("(Fusionar)", size="xs", c="dimmed")
                                            ], align="center", gap="xs"),
                                            style={'width': '100%', 'cursor': 'pointer', 'padding': '10px'},
                                            multiple=False,
                                            accept=".json"
                                        ),
                                        dmc.Button(
                                            "Abrir carpeta grupos",
                                            id="btn-open-folder-group",
                                            variant="subtle",
                                            color="grape",
                                            size="xs",
                                            # compact=True, <-- PROPIEDAD ELIMINADA
                                            leftSection=DashIconify(icon="mdi:folder-open-outline"), # <-- CAMBIADO leftIcon por leftSection
                                            style={"marginTop": "5px"}
                                        )
                                    ],
                                    p="xs",
                                    withBorder=True,
                                    shadow="xs",
                                    radius="md",
                                    style={
                                        "backgroundColor": "#f3f0ff", 
                                        "height": "120px", 
                                        "display": "flex", 
                                        "flexDirection": "column", 
                                        "alignItems": "center", 
                                        "justifyContent": "center"
                                    },
                                )
                            ], span=4),
                        ], gutter="md")
                    ], span=12, mb=20),

                    # Tercera fila - Botones de elementos (corregido el duplicado)
                    dmc.GridCol([
                        dmc.Group([
                            # Botón importar eliminado del grupo principal
                            dmc.Button(
                                "Guardar JSON",
                                id="ep-save-json-btn",
                                leftSection=DashIconify(icon="mdi:file-download-outline"),
                                variant="outline",
                                color="blue"
                            ),
                            dmc.Button(
                                "Crear Grupo",
                                id="ep-create-group-btn",
                                leftSection=DashIconify(icon="mdi:package-variant-plus"),
                                variant="filled",
                                color="grape"
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
                                color="red"
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
                            dmc.GridCol([
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
                                                            decimalScale=2,
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
                                                            decimalScale=2,
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
                                                            decimalScale=2,
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
                                                            decimalScale=2,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        ),
                                                        style={"paddingLeft": "15px", "paddingRight": "15px"}
                                                    )
                                                ])
                                            ])
                                        ],
                                        # Propiedades estéticas de Mantine para la tabla
                                        highlightOnHover=True,
                                        horizontalSpacing="xs",
                                        verticalSpacing="xs",
                                        withColumnBorders=True,
                                        withTableBorder=False,
                                        striped=False,
                                        style={"borderCollapse": "collapse", "width": "auto", "margin": "0 auto"}
                                    ),style={"display": "flex", "justifyContent": "center"}  # Centrado
                                )
                            ], span=4),

                            # Columna 2: Grosor y Color (selectores más anchos)
                            # Columna 2: Propiedades de línea (reorganizado en filas)
                            dmc.GridCol([
                                dmc.Text("Propiedades de Línea", fw="bold", ta="center", mb=15),

                                # Fila para Grosor
                                dmc.Grid([
                                    dmc.GridCol([
                                        dmc.Text("Grosor de línea (px):", size="sm", fw="bold", pt=8),
                                    ], span=5),
                                    dmc.GridCol([
                                        dmc.NumberInput(
                                            id="line-grosor",
                                            min=0.1,
                                            max=10,
                                            step=0.1,
                                            decimalScale=1,
                                            value=1,
                                            style={"width": "100%"}
                                        ),
                                    ], span=7),
                                ], mb=10),

                                # Fila para Color
                                dmc.Grid([
                                    dmc.GridCol([
                                        dmc.Text("Color de línea:", size="sm", fw="bold", pt=8),
                                    ], span=5),
                                    dmc.GridCol([
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
                                    dmc.GridCol([
                                        dmc.Text("Orden (Z-Index):", size="sm", fw="bold", pt=8),
                                    ], span=5),
                                    dmc.GridCol([
                                        dmc.Grid([
                                            dmc.GridCol([
                                                dmc.NumberInput(
                                                    id="line-zindex",
                                                    min=1,
                                                    max=100,
                                                    step=1,
                                                    value=10,
                                                    style={"width": "100%"}
                                                ),
                                            ], span=7),
                                            dmc.GridCol([
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
                            dmc.GridCol([
                                # Nombre centrado
                                html.Div([
                                    dmc.Group([
                                        dmc.TextInput(
                                            id="line-nombre",
                                            placeholder="Línea 1",
                                            value="Línea 1",
                                            style={"width": "160px"}
                                        )
                                    ], justify="center", gap="1", mb=5), # mb reducido
                                    
                                    # SELECCIÓN DE GRUPO
                                    dmc.Group([
                                        dmc.Text("Grupo:", fw="bold", size="sm", pt=8),
                                        dmc.Autocomplete(
                                            id="line-grupo",
                                            placeholder="Seleccionar o nuevo...",
                                            data=[],
                                            value="", 
                                            style={"width": "160px"}
                                        )
                                    ], justify="center", gap="1", mb=20)
                                    ], # Cierre de lista
                                    style={"display": "flex", "flexDirection": "column", "alignItems": "center", "width": "100%"}
                                ),

                                # Botones centrados verticalmente
                                html.Div(
                                    dmc.Stack([
                                        dmc.Button(
                                            "Crear/Actualizar",
                                            id="btn-create-line",
                                            variant="filled",
                                            color="blue",
                                            style={"width": "150px"}
                                        ),
                                        dmc.Space(h=10),
                                        dmc.Button(
                                            "Borrar",
                                            id="btn-delete-line",
                                            variant="filled",
                                            color="red",
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
                            dmc.GridCol([
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
                                                            decimalScale=2,
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
                                                            decimalScale=2,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        )
                                                    )
                                                ])
                                            ])
                                        ],
                                        highlightOnHover=True,
                                        horizontalSpacing="xs",
                                        verticalSpacing="xs",
                                        withColumnBorders=True,
                                        withTableBorder=False,
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
                                                            decimalScale=2,
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
                                                            decimalScale=2,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        )
                                                    )
                                                ])
                                            ])
                                        ],
                                        highlightOnHover=True,
                                        horizontalSpacing="xs",
                                        verticalSpacing="xs",
                                        withColumnBorders=True,
                                        withTableBorder=False,
                                        striped=False,
                                        style={"borderCollapse": "collapse", "width": "auto", "margin": "0 auto"}
                                    ),
                                    style={"display": "flex", "justifyContent": "center"}
                                )
                            ], span=4),

                            # Columna 2: Estilo - Optimizada con mejor distribución de espacio
                            dmc.GridCol([
                                dmc.Text("Estilo", fw="bold", ta="center", mb=15),

                                # Fila de Borde - Nueva proporción 1/4 para título, 3/4 para controles
                                dmc.Grid([
                                    # Título (1/4)
                                    dmc.GridCol([
                                        dmc.Text("Borde:", fw="bold", size="sm", ta="left", pt=8),
                                    ], span=3, style={"paddingLeft": "10px"}),

                                    # Controles (3/4)
                                    dmc.GridCol([
                                        dmc.Group([
                                            dmc.Text("Grosor:", size="sm", pt=8, style={"minWidth": "55px"}),
                                            dmc.NumberInput(
                                                id="rectangle-border-width",
                                                min=0,
                                                max=10,
                                                step=0.1,
                                                decimalScale=1,
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
                                    dmc.GridCol([
                                        dmc.Text("Relleno:", fw="bold", size="sm", ta="left", pt=8),
                                    ], span=3, style={"paddingLeft": "10px"}),

                                    # Controles (3/4)
                                    dmc.GridCol([
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
                                    dmc.GridCol([
                                        dmc.Text("Orden:", fw="bold", size="sm", ta="left", pt=8),
                                    ], span=3, style={"paddingLeft": "10px"}),

                                    # Controles (3/4)
                                    dmc.GridCol([
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
                            dmc.GridCol([
                                # Nombre centrado
                                html.Div([
                                    dmc.Group([
                                        dmc.TextInput(
                                            id="rectangle-nombre",
                                            placeholder="Rectángulo 1",
                                            value="Rectángulo 1",
                                            style={"width": "160px"}
                                        )
                                    ], justify="center", gap="1", mb=5),
                                    # SELECCIÓN DE GRUPO
                                    dmc.Group([
                                        dmc.Text("Grupo:", fw="bold", size="sm", pt=8),
                                        dmc.Autocomplete(
                                            id="rect-grupo",
                                            placeholder="Seleccionar o nuevo...",
                                            data=[],
                                            value="", 
                                            style={"width": "160px"}
                                        )
                                    ], justify="center", gap="1", mb=20)
                                    ],
                                    style={"display": "flex", "flexDirection": "column", "alignItems": "center", "width": "100%"}
                                ),

                                # Botones centrados verticalmente
                                html.Div(
                                    dmc.Stack([
                                        dmc.Button(
                                            "Crear/Actualizar",
                                            id="btn-create-rectangle",
                                            variant="filled",
                                            color="blue",
                                            style={"width": "150px"}
                                        ),
                                        dmc.Space(h=10),
                                        dmc.Button(
                                            "Borrar",
                                            id="btn-delete-rectangle",
                                            variant="filled",
                                            color="red",
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
                            dmc.GridCol([
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
                                                            decimalScale=2,
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
                                                            decimalScale=2,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        )
                                                    )
                                                ])
                                            ])
                                        ],
                                        highlightOnHover=True,
                                        horizontalSpacing="xs",
                                        verticalSpacing="xs",
                                        withColumnBorders=True,
                                        withTableBorder=False,
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
                                                            decimalScale=2,
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
                                                            decimalScale=2,
                                                            value=2.0,
                                                            style={"width": "80px"}
                                                        )
                                                    )
                                                ])
                                            ])
                                        ],
                                        highlightOnHover=True,
                                        horizontalSpacing="xs",
                                        verticalSpacing="xs",
                                        withColumnBorders=True,
                                        withTableBorder=False,
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
                            dmc.GridCol([
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
                            dmc.GridCol([
                                # Nombre del identificador
                                html.Div([
                                    dmc.Group([
                                        dmc.TextInput(
                                            id="text-nombre",
                                            placeholder="Texto 1",
                                            value="Texto 1",
                                            style={"width": "160px"}
                                        )
                                    ], justify="center", gap="1", mb=5),
                                    # SELECCIÓN DE GRUPO
                                    dmc.Group([
                                        dmc.Text("Grupo:", fw="bold", size="sm", pt=8),
                                        dmc.Autocomplete(
                                            id="text-grupo",
                                            placeholder="Seleccionar o nuevo...",
                                            data=[],
                                            value="", 
                                            style={"width": "160px"}
                                        )
                                    ], justify="center", gap="1", mb=20)
                                    ],
                                    style={"display": "flex", "flexDirection": "column", "alignItems": "center", "width": "100%"}
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
                                            color="blue",
                                            style={"width": "150px"}
                                        ),
                                        dmc.Space(h=10),
                                        dmc.Button(
                                            "Borrar",
                                            id="btn-delete-text",
                                            variant="filled",
                                            color="red",
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
                            dmc.GridCol([
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
                                                            decimalScale=2,
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
                                                            decimalScale=2,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        )
                                                    )
                                                ])
                                            ])
                                        ],
                                        highlightOnHover=True,
                                        horizontalSpacing="xs",
                                        verticalSpacing="xs",
                                        withColumnBorders=True,
                                        withTableBorder=False,
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
                                                            decimalScale=2,
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
                                                            decimalScale=2,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        )
                                                    )
                                                ])
                                            ])
                                        ],
                                        highlightOnHover=True,
                                        horizontalSpacing="xs",
                                        verticalSpacing="xs",
                                        withColumnBorders=True,
                                        withTableBorder=False,
                                        striped=False,
                                        style={"borderCollapse": "collapse", "width": "auto", "margin": "0 auto"}
                                    ),
                                    style={"display": "flex", "justifyContent": "center"}
                                )
                            ], span=4),

                            # Columna 2: Opciones de imagen (reorganizada)
                            dmc.GridCol([
                                dmc.Text("Opciones de imagen", fw="bold", ta="center", mb=15),

                                # Selector de archivo - Título y Upload en la misma línea
                                dmc.Grid([
                                    dmc.GridCol([
                                        dmc.Text("Seleccionar imagen:", size="sm", fw="bold", pt=10),
                                    ], span=4),
                                    dmc.GridCol([
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
                                    dmc.GridCol([
                                        dmc.Text("URL de imagen:", size="sm", fw="bold", pt=10),
                                    ], span=4),
                                    dmc.GridCol([
                                        dmc.TextInput(
                                            id="image-url",
                                            placeholder="https://ejemplo.com/imagen.jpg",
                                            leftSection=DashIconify(icon="mdi:link-variant"),
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
                                    dmc.GridCol([
                                        dmc.Text("Opacidad:", size="sm", fw="bold", pt=8),
                                    ], span=3),
                                    dmc.GridCol([
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
                                    dmc.GridCol([
                                        dmc.Text("Reducción:", size="sm", fw="bold", pt=8),
                                        dmc.Grid([
                                            dmc.GridCol([
                                                dmc.NumberInput(
                                                    id="image-reduction",
                                                    min=0,
                                                    max=50,
                                                    step=1,
                                                    value=0,
                                                    style={"width": "100%"}
                                                ),
                                            ], span=8),
                                            dmc.GridCol([
                                                dmc.Text("px", size="xs", pt=8, c="gray"),
                                            ], span=4),
                                        ], gutter="xs", style={"marginTop": "5px"}),
                                    ], span=6),

                                    # Columna para Z-Index
                                    dmc.GridCol([
                                        dmc.Text("Z-Index:", size="sm", fw="bold", pt=8),
                                        dmc.Grid([
                                            dmc.GridCol([
                                                dmc.NumberInput(
                                                    id="image-zindex",
                                                    min=1,
                                                    max=100,
                                                    step=1,
                                                    value=15,
                                                    style={"width": "100%"}
                                                ),
                                            ], span=8),
                                            dmc.GridCol([
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
                                    w=300,
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
                            dmc.GridCol([
                                # Nombre centrado
                                html.Div([
                                    dmc.Group([
                                        dmc.TextInput(
                                            id="image-nombre",
                                            placeholder="Imagen 1",
                                            value="Imagen 1",
                                            style={"width": "160px"}
                                        )
                                    ], justify="center", gap="1", mb=5),
                                    # SELECCIÓN DE GRUPO
                                    dmc.Group([
                                        dmc.Text("Grupo:", fw="bold", size="sm", pt=8),
                                        dmc.Autocomplete(
                                            id="image-grupo",
                                            placeholder="Seleccionar o nuevo...",
                                            data=[],
                                            value="", 
                                            style={"width": "160px"}
                                        )
                                    ], justify="center", gap="1", mb=20)
                                    ],
                                    style={"display": "flex", "flexDirection": "column", "alignItems": "center", "width": "100%"}
                                ),

                                # Botones centrados verticalmente
                                html.Div(
                                    dmc.Stack([
                                        dmc.Button(
                                            "Crear/Actualizar",
                                            id="btn-create-image",
                                            variant="filled",
                                            color="blue",
                                            style={"width": "150px"}
                                        ),
                                        dmc.Space(h=10),
                                        dmc.Button(
                                            "Borrar",
                                            id="btn-delete-image",
                                            variant="filled",
                                            color="red",
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
                            dmc.GridCol([
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
                                                            decimalScale=2,
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
                                                            decimalScale=2,
                                                            value=1.0,
                                                            style={"width": "80px"}
                                                        )
                                                    )
                                                ])
                                            ])
                                        ],
                                        highlightOnHover=True,
                                        horizontalSpacing="xs",
                                        verticalSpacing="xs",
                                        withColumnBorders=True,
                                        withTableBorder=False,
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
                                                            decimalScale=2,
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
                                                            decimalScale=2,
                                                            value=6.0,
                                                            style={"width": "80px"}
                                                        )
                                                    )
                                                ])
                                            ])
                                        ],
                                        highlightOnHover=True,
                                        horizontalSpacing="xs",
                                        verticalSpacing="xs",
                                        withColumnBorders=True,
                                        withTableBorder=False,
                                        striped=False,
                                        style={"borderCollapse": "collapse", "width": "auto", "margin": "0 auto"}
                                    ),
                                    style={"display": "flex", "justifyContent": "center"}
                                )
                            ], span=4),

                            # Columna 2: Configuración del gráfico
                            dmc.GridCol([
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
                                    dmc.GridCol([
                                        dmc.Text("Opacidad:", size="sm", fw="bold", pt=8),
                                    ], span=3),
                                    dmc.GridCol([
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
                                    dmc.GridCol([
                                        dmc.Text("Reducción:", size="sm", fw="bold", pt=8),
                                        dmc.Grid([
                                            dmc.GridCol([
                                                dmc.NumberInput(
                                                    id="graph-reduction",
                                                    min=0,
                                                    max=50,
                                                    step=1,
                                                    value=1,
                                                    style={"width": "100%"}
                                                ),
                                            ], span=8),
                                            dmc.GridCol([
                                                dmc.Text("px", size="xs", pt=8, c="gray"),
                                            ], span=4),
                                        ], gutter="xs", style={"marginTop": "5px"}),
                                    ], span=6),

                                    # Columna para Z-Index
                                    dmc.GridCol([
                                        dmc.Text("Z-Index:", size="sm", fw="bold", pt=8),
                                        dmc.Grid([
                                            dmc.GridCol([
                                                dmc.NumberInput(
                                                    id="graph-zindex",
                                                    min=1,
                                                    max=100,
                                                    step=1,
                                                    value=25,
                                                    style={"width": "100%"}
                                                ),
                                            ], span=8),
                                            dmc.GridCol([
                                                dmc.Text(">", size="xs", pt=8, c="gray"),
                                            ], span=4),
                                        ], gutter="xs", style={"marginTop": "5px"}),
                                    ], span=6),
                                ]),

                            ], span=4),

                            # Columna 3: Nombre y Botones
                            dmc.GridCol([
                                # Nombre centrado
                                html.Div([
                                    dmc.Group([
                                        dmc.TextInput(
                                            id="graph-nombre",
                                            placeholder="Gráfico 1",
                                            value="Gráfico 1",
                                            style={"width": "160px"}
                                        )
                                    ], justify="center", gap="1", mb=5),
                                    # SELECCIÓN DE GRUPO
                                    dmc.Group([
                                        dmc.Text("Grupo:", fw="bold", size="sm", pt=8),
                                        dmc.Autocomplete(
                                            id="graph-grupo",
                                            placeholder="Seleccionar o nuevo...",
                                            data=[],
                                            value="", 
                                            style={"width": "160px"}
                                        )
                                    ], justify="center", gap="1", mb=20)
                                    ],
                                    style={"display": "flex", "flexDirection": "column", "alignItems": "center", "width": "100%"}
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
                                            color="blue",
                                            style={"width": "150px"}
                                        ),
                                        dmc.Space(h=10),
                                        dmc.Button(
                                            "Borrar",
                                            id="btn-delete-graph",
                                            variant="filled",
                                            color="red",
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

                # Drawer para configurar tablas
                dmc.Drawer(
                    id="ep-table-drawer",
                    title=html.Span("Configurar Tabla", style={"fontWeight": "bold"}),
                    opened=False,
                    position="top",
                    size="xl",
                    children=[
                        # === BLOQUE 1: Selector existente, Script y JSON ===
                        dmc.Paper([
                            dmc.Grid([
                                dmc.GridCol([
                                    dmc.Select(
                                        id="table-selector",
                                        label="Seleccionar tabla existente:",
                                        placeholder="Seleccionar para editar",
                                        clearable=True,
                                        data=[],
                                        size="sm"
                                    )
                                ], span=3),
                                dmc.GridCol([
                                    dmc.TextInput(
                                        id="table-script",
                                        label="Script de datos:",
                                        placeholder="tabla_resumen_campana",
                                        size="sm"
                                    ),
                                ], span=4),
                                dmc.GridCol([
                                    html.Div([
                                        dmc.Text("Parámetros JSON:", size="sm", fw=500, mb=5),
                                        dmc.Button(
                                            "Ver/Editar JSON",
                                            id="btn-open-json-modal",
                                            leftSection=DashIconify(icon="mdi:code-json", width=16),
                                            variant="light",
                                            color="blue",
                                            size="sm",
                                            fullWidth=True
                                        ),
                                    ])
                                ], span=5),
                            ]),
                        ], p="md", withBorder=True, radius="sm", mb=15),

                        # === BLOQUE 2: Posición/Área (izquierda) + Identificador/Botones (derecha) ===
                        dmc.Grid([
                            # Mitad izquierda: Posición y Área Máxima
                            dmc.GridCol([
                                dmc.Paper([
                                    dmc.Text("Posición y Área Máxima", fw="bold", size="sm", mb=15),
                                    
                                    dmc.Grid([
                                        # Esquina superior izquierda
                                        dmc.GridCol([
                                            dmc.Text("Esquina superior izquierda", size="xs", c="dimmed", mb=5),
                                            dmc.Group([
                                                dmc.NumberInput(
                                                    id="table-x",
                                                    label="X (cm):",
                                                    min=0,
                                                    max=30,
                                                    step=0.1,
                                                    decimalScale=1,
                                                    value=1.0,
                                                    size="xs",
                                                    style={"width": "100px"}
                                                ),
                                                dmc.NumberInput(
                                                    id="table-y",
                                                    label="Y (cm):",
                                                    min=0,
                                                    max=30,
                                                    step=0.1,
                                                    decimalScale=1,
                                                    value=2.0,
                                                    size="xs",
                                                    style={"width": "100px"}
                                                ),
                                            ], gap="md"),
                                        ], span=6),
                                        
                                        # Área máxima (ancho y alto)
                                        dmc.GridCol([
                                            dmc.Text("Área máxima", size="xs", c="dimmed", mb=5),
                                            dmc.Group([
                                                dmc.NumberInput(
                                                    id="table-width",
                                                    label="Ancho (cm):",
                                                    min=1,
                                                    max=30,
                                                    step=0.5,
                                                    decimalScale=1,
                                                    value=18.0,
                                                    size="xs",
                                                    style={"width": "100px"}
                                                ),
                                                dmc.NumberInput(
                                                    id="table-height",
                                                    label="Alto (cm):",
                                                    min=1,
                                                    max=30,
                                                    step=0.5,
                                                    decimalScale=1,
                                                    value=6.0,
                                                    size="xs",
                                                    style={"width": "100px"}
                                                ),
                                            ], gap="md"),
                                        ], span=6),
                                    ]),
                                    
                                    dmc.Text("La tabla se ajustará dentro de esta área", 
                                            size="xs", c="dimmed", ta="center", mt=15),
                                ], p="md", withBorder=True, radius="sm", h="100%"),
                            ], span=6),
                            
                            # Mitad derecha: Identificador y Botones
                            dmc.GridCol([
                                dmc.Paper([
                                    dmc.Text("Identificador", fw="bold", size="sm", mb=15),
                                    
                                    dmc.Grid([
                                        dmc.GridCol([
                                            dmc.TextInput(
                                                id="table-nombre",
                                                label="Nombre:",
                                                placeholder="tabla 1",
                                                value="tabla 1",
                                                size="sm"
                                            ),
                                        ], span=4),
                                        dmc.GridCol([
                                            dmc.Autocomplete(
                                                id="table-grupo",
                                                label="Grupo:",
                                                placeholder="Seleccionar...",
                                                data=[],
                                                value="", 
                                                size="sm"
                                            ),
                                        ], span=4),
                                        dmc.GridCol([
                                            dmc.NumberInput(
                                                id="table-zindex",
                                                label="Z-Index:",
                                                min=1,
                                                max=100,
                                                step=1,
                                                value=30,
                                                size="sm"
                                            ),
                                        ], span=4),
                                    ], mb=15),
                                    
                                    dmc.Group([
                                        dmc.Button(
                                            "Crear/Actualizar",
                                            id="btn-create-table",
                                            variant="filled",
                                            color="blue",
                                            size="sm",
                                            style={"flex": "1"}
                                        ),
                                        dmc.Button(
                                            "Borrar",
                                            id="btn-delete-table",
                                            variant="filled",
                                            color="red",
                                            size="sm",
                                            style={"flex": "1"}
                                        ),
                                    ], grow=True, gap="md"),
                                ], p="md", withBorder=True, radius="sm", h="100%"),
                            ], span=6),
                        ], mb=15),

                        # === SEPARADOR HORIZONTAL: Aquí comenzará la configuración de cuadrícula ===
                        dmc.Divider(
                            label="Configuración de Cuadrícula", 
                            labelPosition="center",
                            mb=15
                        ),
                        
                        # Controles de niveles
                        dmc.Paper([
                            dmc.Group([
                                dmc.Text("Niveles de la cuadrícula:", fw="bold", size="sm"),
                                dmc.Badge(id="grid-level-count", children="0 niveles", color="blue", variant="light"),
                                dmc.Space(style={"flex": "1"}),
                                dmc.Button(
                                    "Nivel Estático",
                                    id="btn-add-grid-level",
                                    variant="filled",
                                    color="green",
                                    size="xs",
                                    leftSection=DashIconify(icon="mdi:plus", width=16)
                                ),
                                dmc.Button(
                                    "Nivel Autorrelleno",
                                    id="btn-add-grid-level-dynamic",
                                    variant="filled",
                                    color="teal",
                                    size="xs",
                                    leftSection=DashIconify(icon="mdi:database-plus", width=16)
                                ),
                                dmc.Button(
                                    "Quitar Último",
                                    id="btn-remove-grid-level",
                                    variant="outline",
                                    color="red",
                                    size="xs",
                                    leftSection=DashIconify(icon="mdi:minus", width=16),
                                    disabled=True
                                ),
                            ], justify="flex-start", gap="md", mb=10),
                            
                            # Información del ancho disponible
                            dmc.Group([
                                dmc.Text(id="grid-available-width", 
                                        children="Ancho disponible: 18.0 cm", 
                                        size="xs", c="dimmed"),
                                dmc.Text(id="grid-width-warning", 
                                        children="", 
                                        size="xs", c="red"),
                            ], gap="lg"),
                        ], p="sm", withBorder=True, radius="sm", mb=10),
                        
                        # Store para guardar la configuración de niveles
                        dcc.Store(id="store-grid-levels", data={"niveles": []}),
                        
                        # Contenedor dinámico para los niveles de cuadrícula
                        html.Div(
                            id="grid-levels-container",
                            children=[
                                # Estado vacío inicial
                                dmc.Alert(
                                    children="No hay niveles definidos. Pulsa 'Añadir Nivel' para comenzar a definir la estructura de la tabla.",
                                    color="gray",
                                    icon=[DashIconify(icon="mdi:information-outline", width=20)],
                                    withCloseButton=False,
                                )
                            ],
                            style={"maxHeight": "350px", "overflowY": "auto", "marginBottom": "15px"}
                        ),
                        
                        # === SEPARADOR DE PREVISUALIZACIÓN ===
                        dmc.Divider(
                            label="Previsualización de la Tabla", 
                            labelPosition="center",
                            mb=10
                        ),
                        
                        # Contenedor de previsualización
                        dmc.Paper([
                            html.Div(
                                id="table-preview-container",
                                children=[
                                    dmc.Text("Añade niveles para ver la previsualización de la tabla.", 
                                            size="sm", c="dimmed", ta="center", py=20)
                                ],
                                style={
                                    "minHeight": "100px",
                                    "maxHeight": "200px",
                                    "overflowY": "auto",
                                    "overflowX": "auto",
                                    "backgroundColor": "white"
                                }
                            )
                        ], p="xs", withBorder=True, radius="sm", bg="gray.0"),
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
                            color="red"
                        ),
                        dmc.Button(
                            "Guardar",
                            id="btn-confirm-save-json",
                            variant="filled",
                            color="blue"
                        )
                    ], justify="flex-end")
                ]
            ),
            # Modal flotante para ver/editar Parámetros JSON
            dmc.Modal(
                id="modal-json-params",
                title="Parámetros JSON de la Tabla",
                centered=True,
                size="lg",
                children=[
                    dmc.Text("Contenido de las celdas y parámetros:", size="sm", c="dimmed", mb=10),
                    dmc.Textarea(
                        id="table-parameters",
                        placeholder='{"celdas": {"N1_C1": "Col 1"}}',
                        minRows=15,
                        maxRows=20,
                        autosize=True,
                        style={"fontFamily": "monospace", "fontSize": "12px"}
                    ),
                    dmc.Group([
                        dmc.Button(
                            "Cerrar",
                            id="btn-close-json-modal",
                            variant="outline",
                            color="gray"
                        )
                    ], justify="flex-end", mt=15)
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
                        dmc.Code(
                            id="json-viewer",
                            block=True,
                            style={"maxHeight": "400px", "overflow": "auto", "whiteSpace": "pre"},
                            children=""  # Añadir un string vacío como contenido inicial
                        )
                    ],
                    withBorder=True,
                    shadow="sm",
                    p="xs"
                )
            ], style={"marginTop": "20px"}),

            # Nuevo Modal para CREAR GRUPO (TransferList)
            dmc.Modal(
                id="modal-create-group",
                title="Crear Nuevo Grupo",
                size="lg",
                zIndex=10000,
                children=[
                    dcc.Store(id="store-transfer-state", data={"left": [], "right": []}),
                    dmc.Stack([
                        dmc.TextInput(id="group-name-input", label="Nombre del Grupo", placeholder="Ej: mi_nuevo_grupo", required=True),
                        dmc.Textarea(id="group-desc-input", label="Descripción", placeholder="Opcional"),

                        dmc.Text("Selecciona los elementos a exportar:", fw=500, mt="md"),

                        # TRANSFER LIST SIMULADO
                        dmc.Grid([
                            # IZQUIERDA: DISPONIBLES
                            dmc.GridCol([
                                dmc.Paper([
                                    dmc.Text("Disponibles en página", size="xs", c="dimmed", mb=5),
                                    dmc.ScrollArea([
                                        dmc.CheckboxGroup(
                                            id="transfer-list-left", 
                                            size="sm",
                                            children=[]
                                        )
                                    ], h=300, type="auto")
                                ], p="xs", withBorder=True, shadow="xs")
                            ], span=5),

                            # CENTRO: BOTONES
                            dmc.GridCol([
                                dmc.Stack([
                                    dmc.ActionIcon(
                                        DashIconify(icon="mdi:chevron-right"),
                                        id="btn-transfer-move-right",
                                        variant="filled", color="blue", size="lg"
                                    ),
                                    dmc.ActionIcon(
                                        DashIconify(icon="mdi:chevron-left"),
                                        id="btn-transfer-move-left",
                                        variant="outline", color="gray", size="lg"
                                    ),
                                ], justify="center", align="center", h="100%")
                            ], span=2),

                            # DERECHA: SELECCIONADOS
                            dmc.GridCol([
                                dmc.Paper([
                                    dmc.Text("A Exportar (Grupo)", size="xs", mb=5, fw=700, c="grape"),
                                    dmc.ScrollArea([
                                        dmc.CheckboxGroup(
                                            id="transfer-list-right", 
                                            size="sm",
                                            children=[]
                                        )
                                    ], h=300, type="auto")
                                ], p="xs", withBorder=True, shadow="xs")
                            ], span=5),
                        ], align="stretch"),

                        dmc.Group([
                            dmc.Text(id="create-group-msg", size="sm"),
                            dmc.Button("Cancelar", id="btn-cancel-create-group", variant="outline", color="red"),
                            dmc.Button("Guardar Grupo", id="btn-save-create-group", variant="filled", color="green"),
                        ], justify="space-between", mt="xl")
                    ])
                ]
            )

        ], fluid=True)
    )


def register_callbacks(app):
    # Callback separado para actualizar opciones de paginación (evita conflictos y duplicados)
    @app.callback(
        Output("ep-page-number", "data", allow_duplicate=True),
        Input("store-componentes", "data"),
        prevent_initial_call=True
    )
    def update_page_select_options(store_data):
        if not store_data or "paginas" not in store_data:
             return [{"value": "1", "label": "1"}]
        
        paginas_keys = [int(k) for k in store_data["paginas"].keys() if str(k).isdigit()]
        total_paginas = max(paginas_keys) if paginas_keys else 1
        
        return [{"value": str(i), "label": str(i)} for i in range(1, total_paginas + 1)]

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
        # Determinar número total de páginas para el paginador
        total_paginas = 1
        if store_data and "paginas" in store_data:
            paginas_keys = [int(k) for k in store_data["paginas"].keys() if str(k).isdigit()]
            if paginas_keys:
                total_paginas = max(paginas_keys)
        
        # Generar opciones para el Select
        page_options = [{"value": str(i), "label": str(i)} for i in range(1, total_paginas + 1)]

        # Asegurar tipo correcto para current_page
        try:
            if current_page is not None:
                current_page = int(current_page)
        except (ValueError, TypeError):
            current_page = 1

        # Asegurar página actual válida
        if current_page is None or current_page < 1:
            current_page = 1
        elif current_page > total_paginas:
            current_page = total_paginas

        page_key = str(current_page)

        # Si el store está vacío o corrupto, devolver valores por defecto
        if not store_data or "paginas" not in store_data:
             (canvas_style, horizontal_ruler_style, horizontal_marks, vertical_ruler_style,
             vertical_marks) = actualizar_orientacion_y_reglas(orientation)
             return canvas_style, horizontal_ruler_style, horizontal_marks, vertical_ruler_style, vertical_marks, []

        # Obtener la orientación específica de la página
        if page_key in store_data['paginas'] and "configuracion" in store_data['paginas'][page_key]:
            page_orientation = store_data['paginas'][page_key]["configuracion"].get("orientacion", orientation)
        else:
            page_orientation = orientation

        # Actualizar la orientación en el store (solo si falta y la página es nueva pero válida)
        # Nota: No creamos la página aquí si no existe, solo leemos.
        # Si la página no existe en el store, no se renderiza nada o se renderiza vacío.
        
        # Actualizar orientación y reglas
        (canvas_style, horizontal_ruler_style, horizontal_marks, vertical_ruler_style,
         vertical_marks) = actualizar_orientacion_y_reglas(page_orientation)

        elementos_canvas = []

        if page_key in store_data['paginas'] and "elementos" in store_data['paginas'][page_key]:
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
                    img_src = elemento["imagen"].get("datos_temp", "")
                    opacidad = elemento["estilo"]["opacidad"] / 100
                    
                    # Intentar recuperar imagen de disco si no hay datos temporales (caso cargar plantilla)
                    # Intentar recuperar imagen de disco si no hay datos temporales (caso cargar plantilla o grupo)
                    if not img_src:
                        ruta_nueva = elemento["imagen"].get("ruta_nueva", "")
                        nombre_plantilla = store_data.get("configuracion", {}).get("nombre_plantilla", "")
                        
                        if ruta_nueva:
                            base_dir = os.getcwd() # Debería ser la raíz del proyecto
                            posibles_rutas = []
                            
                            # 1. Ruta relativa a la plantilla actual (si tenemos nombre de plantilla)
                            # Se asume que ruta_nueva es algo como "assets/imagen.png"
                            if nombre_plantilla:
                                posibles_rutas.append(os.path.join(base_dir, "biblioteca_plantillas", nombre_plantilla, ruta_nueva))
                                # Intentar también sin el subdirectorio assets si la ruta ya lo incluye
                                posibles_rutas.append(os.path.join(base_dir, "biblioteca_plantillas", nombre_plantilla, "assets", os.path.basename(ruta_nueva)))

                            # 2. Ruta relativa a la raíz del proyecto (donde también hay una carpeta assets)
                            posibles_rutas.append(os.path.join(base_dir, ruta_nueva))
                            
                            # 3. Ruta directa en assets global
                            posibles_rutas.append(os.path.join(base_dir, "assets", os.path.basename(ruta_nueva)))
                            
                            # 4. Ruta relativa dentro de biblioteca_grupos (intento de recuperación desesperada)
                            # Esto es más difícil porque no sabemos el nombre de la carpeta del grupo original,
                            # pero podemos intentar buscar en todas las carpetas de grupos si es crítico, 
                            # aunque por rendimiento mejor nos limitamos a assets global.

                            for ruta_img in posibles_rutas:
                                if os.path.exists(ruta_img):
                                    try:
                                        with open(ruta_img, "rb") as image_file:
                                            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                                            # Detectar mime type básico por extensión
                                            ext = os.path.splitext(ruta_img)[1].lower()
                                            mime = "image/png" if ext == ".png" else ("image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png")
                                            img_src = f"data:{mime};base64,{encoded_string}"
                                            break # Encontrada, salir del bucle
                                    except Exception as e:
                                        print(f"Error cargando imagen de disco {ruta_img}: {e}")
                    
                    # Fallback si sigue vacío
                    if not img_src:
                        # Placeholder gris de 1x1 pixel
                        img_src = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="

                    # Crear elemento img para la imagen
                    if img_src and img_src != "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=":
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
                    es_editable = elemento["contenido"].get("editable", False)
                    
                    # Estilo de borde para indicar editabilidad
                    borde_texto = "1px dashed #2196F3" if es_editable else "none"

                    # Mapear alineación vertical a flex-align
                    align_map = {
                        "top": "flex-start",
                        "middle": "center",
                        "bottom": "flex-end"
                    }

                    # Mapear alineación horizontal
                    text_align = alineacion_h

                    # Calcular estilos de texto
                    # Crear el div del texto (elemento interno)
                    texto_div = html.Div(
                        id=f"elemento-{nombre}",
                        children=[
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
                            "zIndex": elemento["metadata"]["zIndex"],
                            "padding": "1px",
                            "boxSizing": "border-box",
                            "border": "1px solid transparent" # Borde transparente para mantener box model estable
                        }
                    )

                    # Envolver en Tooltip moderno con contenido detallado
                    tooltip_content = html.Div([
                        html.Div(nombre, style={"fontWeight": "bold", "marginBottom": "3px"}),
                        html.Div(f'"{texto[:40]}..."' if len(texto) > 40 else f'"{texto}"', 
                                 style={"fontStyle": "italic", "marginBottom": "3px", "opacity": 0.9, "maxWidth": "200px", "whiteSpace": "normal"}),
                        html.Div("Editable" if es_editable else "Estático", 
                                 style={"fontSize": "0.85em", "opacity": 0.8, "textTransform": "uppercase"})
                    ])

                    texto_element = dmc.Tooltip(
                        children=texto_div,
                        label=tooltip_content,
                        color="blue" if es_editable else "gray",
                        position="right",
                        withArrow=True,
                        multiline=True  # Permite contenido multilinea más flexible
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

                # Elementos de tipo tabla
                elif elemento["tipo"] == "tabla" and elemento["metadata"]["visible"]:
                    # Coordenadas y dimensiones
                    x_px = cm_a_px(elemento["geometria"]["x"])
                    y_px = cm_a_px(elemento["geometria"]["y"])
                    ancho_px = cm_a_px(elemento["geometria"]["ancho_maximo"])
                    alto_px = cm_a_px(elemento["geometria"]["alto_maximo"])

                    # Obtener información
                    script = elemento["configuracion"].get("script", "Tabla")
                    
                    # Detectar si es una tabla basada en cuadrícula (nuevo formato) o estructura simple (viejo)
                    mini_contenido = [] # Lista de elementos a renderizar (tablas por nivel)
                    info_columnas = ""
                    
                    if "cuadricula" in elemento and "niveles" in elemento["cuadricula"]:
                        # Nuevo formato: Cuadrícula con niveles
                        niveles = elemento["cuadricula"].get("niveles", [])
                        num_col_total = 0
                        
                        # Generar preview basado en niveles - CADA NIVEL ES UNA TABLA INDEPENDIENTE (para permitir distintos anchos de col)
                        for nivel in niveles:
                            columnas = nivel.get("columnas", [])
                            num_col_total = max(num_col_total, len(columnas))
                            
                            es_dinamico = nivel.get("tipo") == "autorrelleno"
                            # Renderizar 1 fila si es estático, 2 si es dinámico (ejemplo)
                            filas_a_mostrar = 2 if es_dinamico else 1
                            
                            filas_nivel = []
                            for idx_fila in range(filas_a_mostrar):
                                celdas_fila = []
                                for col in columnas:
                                    # Estilo básico para preview en canvas
                                    bg_color = col.get("formato", {}).get("color_fondo", "#fff")
                                    # Si es dinámico y alterno, simularlo (simplificado)
                                    if es_dinamico and idx_fila % 2 != 0:
                                        bg_color = nivel.get("configuracion_dinamica", {}).get("color_impar", "#eee")
                                    elif es_dinamico:
                                        bg_color = nivel.get("configuracion_dinamica", {}).get("color_par", "#fff")
                                        
                                    # Calcular ancho en px para el canvas
                                    ancho_c_px = cm_a_px(col.get("ancho", 3.0))
                                    
                                    celdas_fila.append(html.Td(
                                        "..." if es_dinamico else col.get("contenido", "")[:10],
                                        style={
                                            "width": f"{ancho_c_px}px",
                                            "minWidth": f"{ancho_c_px}px",
                                            "maxWidth": f"{ancho_c_px}px",
                                            "fontSize": "6px",
                                            "padding": "1px",
                                            "backgroundColor": bg_color,
                                            "border": "1px solid #ccc",
                                            "overflow": "hidden", 
                                            "whiteSpace": "nowrap",
                                            "boxSizing": "border-box"
                                        }
                                    ))
                                filas_nivel.append(html.Tr(celdas_fila))
                            
                            # Crear tabla para este nivel
                            tabla_nivel = html.Table(
                                filas_nivel,
                                style={
                                    "width": "100%", # Se ajustará a la suma de los anchos de celdas
                                    "borderCollapse": "collapse",
                                    "tableLayout": "fixed",
                                    "margin": "0",
                                    "padding": "0",
                                    "borderSpacing": "0"
                                }
                            )
                            mini_contenido.append(tabla_nivel)
                                
                        info_columnas = f"{len(niveles)} niveles"
                    
                    elif "estructura" in elemento:
                        # Viejo formato
                        num_columnas = elemento["estructura"].get("num_columnas", 5)
                        
                        mini_celdas_viejo = []
                        # Encabezado
                        if elemento["estructura"].get("mostrar_encabezados", True):
                            header_cells = html.Tr([
                                html.Th(f"C{i+1}", style={
                                    "border": "1px solid #999", 
                                    "fontSize": "6px", 
                                    "padding": "1px",
                                    "backgroundColor": "#eee"
                                }) for i in range(num_columnas)
                            ])
                            mini_celdas_viejo.append(header_cells)
                        
                        # Filas de ejemplo (2)
                        for _ in range(2):
                            row_cells = html.Tr([
                                html.Td(f"...", style={
                                    "border": "1px solid #ccc", 
                                    "fontSize": "6px", 
                                    "padding": "1px"
                                }) for i in range(num_columnas)
                            ])
                            mini_celdas_viejo.append(row_cells)
                            
                        # Estilo tabla vieja
                        tabla_vieja = html.Table(
                            mini_celdas_viejo,
                            style={
                                "width": "100%",
                                "borderCollapse": "collapse"
                            }
                        )
                        mini_contenido.append(tabla_vieja)
                        info_columnas = f"{num_columnas} cols"

                    # Crear elemento div para la tabla (placeholder complejo con mini-tabla)
                    table_element = html.Div(
                        id=f"elemento-{nombre}",
                        children=[
                            html.Div(f"{script} ({info_columnas})", style={
                                "position": "absolute", 
                                "top": "-15px", 
                                "left": "0", 
                                "fontSize": "8px", 
                                "color": "#666",
                                "whiteSpace": "nowrap"
                            }),
                            *mini_contenido # Renderizar las mini tablas
                        ],
                        style={
                            "position": "absolute",
                            "left": f"{x_px}px",
                            "top": f"{y_px}px",
                            "width": f"{ancho_px}px",
                            "height": f"{alto_px}px",
                            "backgroundColor": "transparent",
                            "border": "1px dashed #4CAF50", # Borde verde para indicar tabla
                            "zIndex": elemento["metadata"]["zIndex"],
                            "overflow": "hidden"
                        },
                        title=f"{nombre} - {script}",
                    )

                    elementos_canvas.append(table_element)

        return canvas_style, horizontal_ruler_style, horizontal_marks, vertical_ruler_style, vertical_marks, elementos_canvas

    @app.callback(
        Output("store-componentes", "data", allow_duplicate=True),
        Input("ep-orientation-selector", "value"),
        [State("store-componentes", "data"),
         State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def update_page_orientation(orientation, store_data, current_page):
        # Solo actualizar si realmente cambió
        page_key = str(current_page)

        if page_key not in store_data['paginas']:
            store_data['paginas'][page_key] = {
                "elementos": {},
                "configuracion": {"orientacion": orientation}
            }
        elif "configuracion" not in store_data['paginas'][page_key]:
            store_data['paginas'][page_key]["configuracion"] = {"orientacion": orientation}
        else:
            # Solo actualizar si realmente cambió
            current_orientation = store_data['paginas'][page_key]["configuracion"].get("orientacion")
            if current_orientation != orientation:
                store_data['paginas'][page_key]["configuracion"]["orientacion"] = orientation
            else:
                # Si no cambió, no retornar nada para evitar re-renders
                return dash.no_update

        # Actualizar pagina_actual aquí en lugar de tener un callback separado
        store_data['pagina_actual'] = current_page

        return store_data

    # callback que actualice las opciones del selector cuando cambie el número total de páginas
    @app.callback(
        Output("ep-page-number", "data"),
        Input("store-componentes", "data")
    )
    def update_page_selector_options(store_data):
        if not store_data or 'configuracion' not in store_data:
            num_pages = 1
        else:
            num_pages = store_data['configuracion'].get('num_paginas', 1)
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
        current_page_int = int(current_page)

        if button_id == "ep-prev-page-btn" and current_page_int > 1:
            new_page = current_page_int - 1
        elif button_id == "ep-next-page-btn" and current_page_int < store_data['configuracion']['num_paginas']:
            new_page = current_page_int + 1
        else:
            return current_page, dash.no_update

        page_key = str(new_page)

        # Solo obtener orientación, NO actualizar store
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

    """
    # Implementación del Callback para Actualizar pagina_actual
    @app.callback(
        Output("store-componentes", "data", allow_duplicate=True),
        Input("ep-page-number", "value"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def update_current_page(current_page, store_data):
        
        #Actualiza el valor de 'pagina_actual' en el store cuando el usuario cambia de página.
        
        # current_page ya es un string y solo puede ser un valor válido del selector

        # Actualizar la página actual en el store
        store_data['pagina_actual'] = current_page

        return store_data
    """

    # callback para mostrar número total de páginas
    @app.callback(
        Output("ep-total-pages", "children"),
        Input("store-componentes", "data")
    )
    def update_total_pages(store_data):
        if not store_data or 'configuracion' not in store_data:
            return "1"
        return str(store_data['configuracion'].get('num_paginas', 1))

    # Callback para abrir el drawer de línea
    @app.callback(
        [Output("drawer-line", "opened"),
         Output("line-nombre", "value"),
         Output("line-grupo", "data"),
         Output("line-grupo", "value")],
        Input("ep-add-line-btn", "n_clicks"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def open_line_drawer(n_clicks, store_data):
        if not n_clicks:
            return False, "Línea 1", [], ""

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

        # Extraer grupos existentes de todas las páginas
        grupos_set = set()
        if 'paginas' in store_data:
             for p in store_data['paginas'].values():
                 if 'elementos' in p:
                     for elem in p['elementos'].values():
                         if 'grupo' in elem and 'nombre' in elem['grupo']:
                             g_nom = elem['grupo']['nombre']
                             if g_nom and g_nom != "Sin grupo": # Opcional: filtrar "Sin grupo"
                                grupos_set.add(g_nom)
        
        opciones_grupo = sorted(list(grupos_set))

        return True, nombre_sugerido, opciones_grupo, ""


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
        State("line-grupo", "value"), # Nuevo State
        State("line-zindex", "value"),  # Mantener el zIndex
        State("store-componentes", "data"),
        State("ep-orientation-selector", "value"),
        State("ep-page-number", "value")],
        prevent_initial_call = True
    )
    def crear_actualizar_linea(n_clicks, selected_line_name, x1, y1, x2, y2, grosor, color, nombre, grupo_nombre, zindex, store_data,
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

        # Procesar grupo
        grupo_data = {
            "nombre": "Sin grupo",
            "color": "#cccccc"
        }
        if grupo_nombre and grupo_nombre.strip():
             grupo_data["nombre"] = grupo_nombre.strip()

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
            "grupo": grupo_data, 
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
         Output("rectangle-nombre", "value"),
         Output("rect-grupo", "data"),
         Output("rect-grupo", "value")],
        Input("ep-add-rectangle-btn", "n_clicks"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def open_rectangle_drawer(n_clicks, store_data):
        if not n_clicks:
            return False, "rectangulo 1", [], ""

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

        # Extraer grupos
        grupos_set = set()
        if 'paginas' in store_data:
             for p in store_data['paginas'].values():
                 if 'elementos' in p:
                     for elem in p['elementos'].values():
                         if 'grupo' in elem and 'nombre' in elem['grupo']:
                             g_nom = elem['grupo']['nombre']
                             if g_nom and g_nom != "Sin grupo":
                                grupos_set.add(g_nom)
        
        opciones_grupo = sorted(list(grupos_set))

        return True, nombre_sugerido, opciones_grupo, ""

    # Callback para abrir el drawer de gráfico
    @app.callback(
        [Output("ep-graph-drawer", "opened"),
         Output("graph-nombre", "value"),
         Output("graph-grupo", "data"),
         Output("graph-grupo", "value")],
        Input("ep-add-graph-btn", "n_clicks"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def open_graph_drawer(n_clicks, store_data):
        if not n_clicks:
            return False, "grafico 1", [], ""

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

        # Extraer grupos
        grupos_set = set()
        if 'paginas' in store_data:
             for p in store_data['paginas'].values():
                 if 'elementos' in p:
                     for elem in p['elementos'].values():
                         if 'grupo' in elem and 'nombre' in elem['grupo']:
                             g_nom = elem['grupo']['nombre']
                             if g_nom and g_nom != "Sin grupo":
                                grupos_set.add(g_nom)
        
        opciones_grupo = sorted(list(grupos_set))

        return True, nombre_sugerido, opciones_grupo, ""

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
         Output("graph-grupo", "value", allow_duplicate=True),
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
            return 1.0, 1.0, 8.0, 6.0, "", "svg", 100, 1, 25, "Gráfico 1", "", ""  # Incluir "svg" por defecto

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
                    elemento.get("grupo", {}).get("nombre", ""),
                    parametros_texto
                )

        # Si no se encuentra el gráfico
        return (1.0, 1.0, 8.0, 6.0, "", "svg", 100, 1, 25, "Gráfico 1", "", "")  # Incluir "svg" por defecto y grupo vacío

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
         State("graph-grupo", "value"), # Nuevo State
         State("graph-parameters", "value"),
         State("store-componentes", "data"),
         State("ep-orientation-selector", "value"),
         State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def crear_actualizar_grafico(n_clicks, selected_name, x, y, ancho, alto, script, formato,  # NUEVO PARÁMETRO
                                 opacidad, reduccion, zindex, nombre, grupo_nombre, parametros_texto, store_data, orientacion,
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
        
        # Procesar grupo
        grupo_data = {
            "nombre": "Sin grupo",
            "color": "#cccccc"
        }
        if grupo_nombre and grupo_nombre.strip():
             grupo_data["nombre"] = grupo_nombre.strip()

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
            "grupo": grupo_data,
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
        [Output("ep-table-drawer", "opened"),
         Output("table-nombre", "value"),
         Output("table-grupo", "data"),
         Output("table-grupo", "value")],
        Input("ep-add-table-btn", "n_clicks"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def open_table_drawer(n_clicks, store_data):
        if not n_clicks:
            return False, "tabla 1", [], ""

        # Obtener la página actual
        page_key = store_data.get('pagina_actual', "1")

        # Generar nombre sugerido
        if ('paginas' in store_data and page_key in store_data['paginas'] and
                'elementos' in store_data['paginas'][page_key]):
            elementos_pagina = store_data['paginas'][page_key]['elementos']
            tablas_existentes = [nombre for nombre, elem in elementos_pagina.items()
                                 if elem["tipo"] == "tabla"]

            # Encontrar el siguiente número disponible
            num = 1
            while f"tabla {num}" in tablas_existentes:
                num += 1

            nombre_sugerido = f"tabla {num}"
        else:
            nombre_sugerido = "tabla 1"

        # Extraer grupos
        grupos_set = set()
        if 'paginas' in store_data:
             for p in store_data['paginas'].values():
                 if 'elementos' in p:
                     for elem in p['elementos'].values():
                         if 'grupo' in elem and 'nombre' in elem['grupo']:
                             g_nom = elem['grupo']['nombre']
                             if g_nom and g_nom != "Sin grupo":
                                grupos_set.add(g_nom)
        
        opciones_grupo = sorted(list(grupos_set))

        return True, nombre_sugerido, opciones_grupo, ""

    # ============================================================
    # CALLBACKS PARA CONFIGURACIÓN DE CUADRÍCULA DINÁMICA
    # ============================================================
    
    # Callback para añadir/quitar niveles y actualizar columnas
    @app.callback(
        [Output("store-grid-levels", "data"),
         Output("grid-levels-container", "children"),
         Output("grid-level-count", "children"),
         Output("btn-remove-grid-level", "disabled")],
        [Input("btn-add-grid-level", "n_clicks"),
         Input("btn-add-grid-level-dynamic", "n_clicks"),
         Input("btn-remove-grid-level", "n_clicks"),
         Input({"type": "grid-level-num-cols", "index": ALL}, "value"),
         Input({"type": "grid-level-row-height", "index": ALL}, "value"),
         Input({"type": "grid-level-font-family", "index": ALL}, "value"),
         Input({"type": "grid-level-font-size", "index": ALL}, "value"),
         Input({"type": "grid-level-alternate", "index": ALL}, "checked"),
         Input({"type": "grid-level-even-color", "index": ALL}, "value"),
         Input({"type": "grid-level-odd-color", "index": ALL}, "value"),
         Input({"type": "col-content", "nivel": ALL, "col": ALL}, "value"),
         Input({"type": "col-width", "nivel": ALL, "col": ALL}, "value"),
         Input({"type": "col-bold", "nivel": ALL, "col": ALL}, "checked"),
         Input({"type": "col-align", "nivel": ALL, "col": ALL}, "value"),
         Input({"type": "col-bgcolor", "nivel": ALL, "col": ALL}, "value"),
         Input({"type": "col-textcolor", "nivel": ALL, "col": ALL}, "value"),
         Input({"type": "col-border-preset", "nivel": ALL, "col": ALL}, "value"),
         Input({"type": "col-border-width", "nivel": ALL, "col": ALL}, "value"),
         Input({"type": "col-border-color", "nivel": ALL, "col": ALL}, "value")],
        [State("store-grid-levels", "data"),
         State("table-width", "value")],
        prevent_initial_call=True
    )
    def gestionar_niveles_cuadricula(add_static_clicks, add_dynamic_clicks, remove_clicks, 
                                     num_cols_values, row_height_values,
                                     font_family_values, font_size_values,
                                     alternate_values, even_color_values, odd_color_values,
                                     contenidos, anchos, negritas, alineaciones, bg_colors, text_colors,
                                     border_presets, border_widths, border_colors,
                                     store_data, ancho_tabla):
        import json
        from dash import ctx
        
        if not ctx.triggered:
            raise dash.exceptions.PreventUpdate
        
        triggered_id = ctx.triggered_id
        niveles = store_data.get("niveles", [])
        
        # Función para crear bordes por defecto
        def crear_bordes_default():
            return {
                "superior": {"activo": True, "grosor": 1, "color": "#333333"},
                "inferior": {"activo": True, "grosor": 1, "color": "#333333"},
                "izquierdo": {"activo": True, "grosor": 1, "color": "#333333"},
                "derecho": {"activo": True, "grosor": 1, "color": "#333333"}
            }
        
        # Función para crear columna por defecto
        def crear_columna_default(i, ancho_col, es_dinamico=False):
            if es_dinamico:
                contenido_default = f"[Dato {i+1}]"
                bg_color = "transparent" # El fondo lo gestiona la fila dinámica
            else:
                contenido_default = f"Col {i+1}"
                bg_color = "#f8f9fa" if i % 2 == 0 else "#ffffff"
                
            return {
                "ancho": ancho_col,
                "contenido": contenido_default,
                "formato": {
                    "fuente": "Aptos",
                    "tamano": 10,
                    "color_texto": "#333333",
                    "color_fondo": bg_color,
                    "alineacion": "center",
                    "negrita": False
                },
                "bordes": crear_bordes_default()
            }
        
        # Función para aplicar preset de bordes
        def aplicar_preset_bordes(preset, grosor, color):
            bordes = {
                "superior": {"activo": False, "grosor": grosor, "color": color},
                "inferior": {"activo": False, "grosor": grosor, "color": color},
                "izquierdo": {"activo": False, "grosor": grosor, "color": color},
                "derecho": {"activo": False, "grosor": grosor, "color": color}
            }
            if preset == "todos":
                bordes["superior"]["activo"] = True
                bordes["inferior"]["activo"] = True
                bordes["izquierdo"]["activo"] = True
                bordes["derecho"]["activo"] = True
            elif preset == "externos":
                bordes["superior"]["activo"] = True
                bordes["inferior"]["activo"] = True
                bordes["izquierdo"]["activo"] = True
                bordes["derecho"]["activo"] = True
            elif preset == "inferior":
                bordes["inferior"]["activo"] = True
            elif preset == "superior":
                bordes["superior"]["activo"] = True
            elif preset == "izquierdo":
                bordes["izquierdo"]["activo"] = True
            elif preset == "derecho":
                bordes["derecho"]["activo"] = True
            elif preset == "horizontal":
                bordes["superior"]["activo"] = True
                bordes["inferior"]["activo"] = True
            elif preset == "vertical":
                bordes["izquierdo"]["activo"] = True
                bordes["derecho"]["activo"] = True
            # Si es "ninguno", todos quedan en False
            return bordes
        
        # Determinar la acción basada en el trigger
        if triggered_id == "btn-add-grid-level":
            # Añadir nuevo nivel estático
            ancho_col = round((ancho_tabla or 18.0) / 3, 2)
            nuevo_nivel = {
                "id": len(niveles) + 1,
                "tipo": "estatico",
                "num_columnas": 3,
                "alto_fila": 0.5,
                "estilo": {
                    "fuente": "Aptos",
                    "tamano": 10
                },
                "columnas": [crear_columna_default(i, ancho_col, False) for i in range(3)]
            }
            niveles.append(nuevo_nivel)
            
        elif triggered_id == "btn-add-grid-level-dynamic":
            # Añadir nuevo nivel dinámico (autorrelleno)
            ancho_col = round((ancho_tabla or 18.0) / 3, 2)
            nuevo_nivel = {
                "id": len(niveles) + 1,
                "tipo": "autorrelleno",
                "num_columnas": 3,
                "alto_fila": 0.5,
                "estilo": {
                    "fuente": "Aptos",
                    "tamano": 10
                },
                "configuracion_dinamica": {
                    "sombreado_alterno": True,
                    "color_par": "#f8f9fa",
                    "color_impar": "#ffffff"
                },
                "columnas": [crear_columna_default(i, ancho_col, True) for i in range(3)]
            }
            niveles.append(nuevo_nivel)
            
        elif triggered_id == "btn-remove-grid-level":
            # Quitar último nivel
            if niveles:
                niveles.pop()
                
        elif isinstance(triggered_id, dict):
            tipo = triggered_id.get("type", "")
            
            if tipo in ["grid-level-num-cols", "grid-level-row-height", 
                       "grid-level-font-family", "grid-level-font-size",
                       "grid-level-alternate", "grid-level-even-color", "grid-level-odd-color"]:
                # Actualizar propiedades de nivel
                nivel_idx = triggered_id["index"] - 1
                if 0 <= nivel_idx < len(niveles):
                    nivel = niveles[nivel_idx]
                    es_dinamico = nivel.get("tipo") == "autorrelleno"
                    
                    if tipo == "grid-level-num-cols":
                        nuevo_num_cols = num_cols_values[nivel_idx] or 3
                        ancho_col_default = round((ancho_tabla or 18.0) / nuevo_num_cols, 2)
                        
                        columnas_actuales = nivel.get("columnas", [])
                        nuevas_columnas = []
                        
                        for i in range(nuevo_num_cols):
                            if i < len(columnas_actuales):
                                col = columnas_actuales[i]
                                if "bordes" not in col:
                                    col["bordes"] = crear_bordes_default()
                                nuevas_columnas.append(col)
                            else:
                                nuevas_columnas.append(crear_columna_default(i, ancho_col_default, es_dinamico))
                        
                        nivel["columnas"] = nuevas_columnas
                        nivel["num_columnas"] = nuevo_num_cols
                        
                    elif tipo == "grid-level-row-height":
                        # Actualizar alto de fila
                        nivel["alto_fila"] = row_height_values[nivel_idx] or 0.5
                    
                    elif tipo == "grid-level-font-family":
                        # Actualizar fuente
                        nivel.setdefault("estilo", {})["fuente"] = font_family_values[nivel_idx] or "Aptos"
                        
                    elif tipo == "grid-level-font-size":
                        # Actualizar tamaño fuente
                        nivel.setdefault("estilo", {})["tamano"] = font_size_values[nivel_idx] or 10
                        
                    elif tipo == "grid-level-alternate":
                        # Actualizar sombreado alterno
                        # Usar el valor del trigger directamente ya que la lista puede no tener entrada para niveles estáticos previos
                        nivel.setdefault("configuracion_dinamica", {})["sombreado_alterno"] = ctx.triggered[0]['value']
                        
                    elif tipo == "grid-level-even-color":
                        # Actualizar color par
                        nivel.setdefault("configuracion_dinamica", {})["color_par"] = ctx.triggered[0]['value']
                        
                    elif tipo == "grid-level-odd-color":
                        # Actualizar color impar
                        nivel.setdefault("configuracion_dinamica", {})["color_impar"] = ctx.triggered[0]['value']
                    
            elif tipo in ["col-content", "col-width", "col-bgcolor", "col-textcolor", "col-bold", "col-align",
                         "col-border-preset", "col-border-width", "col-border-color"]:
                # Actualizar propiedades de columna específica
                nivel_id = triggered_id.get("nivel")
                col_idx = triggered_id.get("col")
                
                # Encontrar el nivel
                nivel = next((n for n in niveles if n["id"] == nivel_id), None)
                if nivel and 0 <= col_idx < len(nivel.get("columnas", [])):
                    col = nivel["columnas"][col_idx]
                    
                    # Buscar el índice real en las listas ALL
                    idx_global = None
                    contador = 0
                    for n in niveles:
                        for c_idx in range(len(n.get("columnas", []))):
                            if n["id"] == nivel_id and c_idx == col_idx:
                                idx_global = contador
                                break
                            contador += 1
                        if idx_global is not None:
                            break
                    
                    if idx_global is not None:
                        if tipo == "col-content" and idx_global < len(contenidos):
                            col["contenido"] = contenidos[idx_global] or ""
                        elif tipo == "col-width" and idx_global < len(anchos):
                            col["ancho"] = anchos[idx_global] or 3.0
                        elif tipo == "col-bgcolor" and idx_global < len(bg_colors):
                            col.setdefault("formato", {})["color_fondo"] = bg_colors[idx_global] or "#ffffff"
                        elif tipo == "col-textcolor" and idx_global < len(text_colors):
                            col.setdefault("formato", {})["color_texto"] = text_colors[idx_global] or "#333333"
                        elif tipo == "col-bold" and idx_global < len(negritas):
                            col.setdefault("formato", {})["negrita"] = negritas[idx_global] or False
                        elif tipo == "col-align" and idx_global < len(alineaciones):
                            col.setdefault("formato", {})["alineacion"] = alineaciones[idx_global] or "center"
                        elif tipo == "col-border-preset" and idx_global < len(border_presets):
                            grosor = border_widths[idx_global] if idx_global < len(border_widths) else 1
                            color = border_colors[idx_global] if idx_global < len(border_colors) else "#333333"
                            col["bordes"] = aplicar_preset_bordes(border_presets[idx_global] or "todos", grosor or 1, color or "#333333")
                        elif tipo == "col-border-width" and idx_global < len(border_widths):
                            for lado in ["superior", "inferior", "izquierdo", "derecho"]:
                                col.setdefault("bordes", {}).setdefault(lado, {})["grosor"] = border_widths[idx_global] or 1
                        elif tipo == "col-border-color" and idx_global < len(border_colors):
                            for lado in ["superior", "inferior", "izquierdo", "derecho"]:
                                col.setdefault("bordes", {}).setdefault(lado, {})["color"] = border_colors[idx_global] or "#333333"
        
        # Guardar datos actualizados
        store_data["niveles"] = niveles
        
        # Generar UI de niveles
        children = generar_ui_niveles(niveles, ancho_tabla or 18.0)
        
        # Actualizar conteo y estado del botón
        count_text = f"{len(niveles)} nivel{'es' if len(niveles) != 1 else ''}"
        btn_disabled = len(niveles) == 0
        
        return store_data, children, count_text, btn_disabled
    
    def generar_ui_niveles(niveles, ancho_total):
        """Genera la UI para todos los niveles de cuadrícula"""
        if not niveles:
            return [
                dmc.Alert(
                    children="No hay niveles definidos. Pulsa 'Añadir Nivel' para comenzar a definir la estructura de la tabla.",
                    color="gray",
                    icon=[DashIconify(icon="mdi:information-outline", width=20)],
                    withCloseButton=False,
                )
            ]
        
        # Opciones de bordes estilo Excel
        border_options = [
            {"value": "ninguno", "label": "Sin borde"},
            {"value": "todos", "label": "Todos"},
            {"value": "externos", "label": "Externos"},
            {"value": "inferior", "label": "Inferior"},
            {"value": "superior", "label": "Superior"},
            {"value": "horizontal", "label": "Sup+Inf"},
            {"value": "vertical", "label": "Izq+Der"},
        ]
        
        # Opciones de alineación
        align_options = [
            {"value": "left", "label": "Izq"},
            {"value": "center", "label": "Centro"},
            {"value": "right", "label": "Der"},
        ]
        
        # Opciones de fuente
        font_options = [
            {"value": "Helvetica", "label": "Helvetica (Sans)"},
            {"value": "Times-Roman", "label": "Times (Serif)"},
            {"value": "Courier", "label": "Courier (Mono)"},
            {"value": "Arial", "label": "Arial"},
            {"value": "Aptos", "label": "Aptos"},
            {"value": "Verdana", "label": "Verdana"},
            {"value": "Tahoma", "label": "Tahoma"},
            {"value": "Trebuchet MS", "label": "Trebuchet MS"},
            {"value": "Georgia", "label": "Georgia"},
            {"value": "Garamond", "label": "Garamond"},
            {"value": "Roboto", "label": "Roboto"},
            {"value": "Open Sans", "label": "Open Sans"},
            {"value": "Lato", "label": "Lato"},
        ]
        
        nivel_components = []
        
        nivel_components = []
        for nivel in niveles:
            nivel_id = nivel["id"]
            tipo_nivel = nivel.get("tipo", "estatico")
            es_dinamico = tipo_nivel == "autorrelleno"
            
            num_cols = nivel.get("num_columnas", 3)
            alto_fila = nivel.get("alto_fila", 0.5)
            estilo_nivel = nivel.get("estilo", {})
            fuente_nivel = estilo_nivel.get("fuente", "Aptos")
            tamano_nivel = estilo_nivel.get("tamano", 10)
            
            # Configuración dinámica
            config_dinamica = nivel.get("configuracion_dinamica", {})
            sombreado_alterno = config_dinamica.get("sombreado_alterno", True)
            color_par = config_dinamica.get("color_par", "#f8f9fa")
            color_impar = config_dinamica.get("color_impar", "#ffffff")
            
            columnas = nivel.get("columnas", [])
            
            # Calcular suma de anchos
            suma_anchos = sum(col.get("ancho", 0) for col in columnas)
            excede = suma_anchos > ancho_total
            
            # Crear filas de columnas
            filas_columnas = []
            for idx, col in enumerate(columnas):
                bordes = col.get("bordes", {})
                formato = col.get("formato", {})
                
                # Determinar preset de borde actual
                b_sup = bordes.get("superior", {}).get("activo", True)
                b_inf = bordes.get("inferior", {}).get("activo", True)
                b_izq = bordes.get("izquierdo", {}).get("activo", True)
                b_der = bordes.get("derecho", {}).get("activo", True)
                
                if not any([b_sup, b_inf, b_izq, b_der]):
                    preset_actual = "ninguno"
                elif all([b_sup, b_inf, b_izq, b_der]):
                    preset_actual = "todos"
                elif all([b_sup, b_inf]) and not any([b_izq, b_der]):
                    preset_actual = "horizontal"
                elif all([b_izq, b_der]) and not any([b_sup, b_inf]):
                    preset_actual = "vertical"
                else:
                    preset_actual = "externos"
                
                # Placeholder específico para niveles dinámicos
                placeholder_txt = f"Clave (ej. dato_{idx+1})" if es_dinamico else f"Col {idx + 1}"
                label_contenido = "Clave de Datos" if (idx == 0 and es_dinamico) else ("Contenido" if idx == 0 else None)
                
                # Fila principal de configuración de columna
                # Ajuste para alinear verticalmente el checkbox de Negrita con los otros inputs
                fila_principal = dmc.Grid([
                    # Número de columna
                    dmc.GridCol([
                        dmc.Badge(f"{idx + 1}", color="blue", variant="filled", size="sm")
                    ], span={"base": 12, "sm": 1}, style={"display": "flex", "alignItems": "center", "height": "100%", "paddingTop": "24px"} if idx == 0 else {"display": "flex", "alignItems": "center", "height": "100%"}),
                    
                    # Ancho (cm)
                    dmc.GridCol([
                        dmc.NumberInput(
                            id={"type": "col-width", "nivel": nivel_id, "col": idx},
                            label="Ancho" if idx == 0 else None,
                            min=0.5, max=ancho_total, step=0.01, decimalScale=2,
                            value=col.get("ancho", 3.0),
                            size="xs"
                        )
                    ], span={"base": 6, "sm": 1}),
                    
                    # Contenido
                    dmc.GridCol([
                        dmc.TextInput(
                            id={"type": "col-content", "nivel": nivel_id, "col": idx},
                            label=label_contenido,
                            placeholder=placeholder_txt,
                            value=col.get("contenido", placeholder_txt),
                            size="xs"
                        )
                    ], span={"base": 6, "sm": 2}),
                    
                    # Negrita - Alineado verticalmente con los inputs de su fila
                    dmc.GridCol([
                        # Si es fila 0 (idx=0), renderizamos etiqueta y el checkbox
                        # Usamos Stack para alinear verticalmente: Texto (Label) arriba, Checkbox abajo
                        dmc.Stack([
                            dmc.Text("Negrita", size="sm", fw=500, ta="center", mb=0),
                            dmc.Center(
                                dmc.Checkbox(
                                    id={"type": "col-bold", "nivel": nivel_id, "col": idx},
                                    label=None,
                                    checked=formato.get("negrita", False),
                                    size="xs"
                                )
                            )
                        ], gap="xs", align="center") if idx == 0 
                        # Si es fila > 0, solo checkbox centrado en el alto de la celda (aprox 30px del input vecino)
                        else dmc.Center(
                            dmc.Checkbox(
                                id={"type": "col-bold", "nivel": nivel_id, "col": idx},
                                label=None,
                                checked=formato.get("negrita", False),
                                size="xs"
                            ),
                            style={"height": "30px"} # Altura aproximada de un TextInput size="xs" para centrar
                        )
                    ], span={"base": 3, "sm": 1}),
                    
                    # Alineación
                    dmc.GridCol([
                        dmc.Select(
                            id={"type": "col-align", "nivel": nivel_id, "col": idx},
                            label="Alineación" if idx == 0 else None,
                            data=align_options,
                            value=formato.get("alineacion", "center"),
                            size="xs"
                        )
                    ], span={"base": 3, "sm": 1}),
                    
                    # Color texto
                    dmc.GridCol([
                        dmc.ColorInput(
                            id={"type": "col-textcolor", "nivel": nivel_id, "col": idx},
                            label="Texto" if idx == 0 else None,
                            value=formato.get("color_texto", "#333333"),
                            format="hex",
                            size="xs"
                        )
                    ], span={"base": 3, "sm": 1}),
                    
                    # Color fondo (solo si no es dinámico, o deshabilitado visualmente)
                    dmc.GridCol([
                        dmc.ColorInput(
                            id={"type": "col-bgcolor", "nivel": nivel_id, "col": idx},
                            label="Fondo" if idx == 0 else None,
                            value=formato.get("color_fondo", "#ffffff"),
                            format="hex",
                            size="xs",
                            disabled=es_dinamico # Deshabilitar si es dinámico (usa colores alternos)
                        )
                    ], span={"base": 3, "sm": 1}),
                    
                    # Selector de bordes
                    dmc.GridCol([
                        dmc.Select(
                            id={"type": "col-border-preset", "nivel": nivel_id, "col": idx},
                            label="Bordes" if idx == 0 else None,
                            data=border_options,
                            value=preset_actual,
                            size="xs"
                        )
                    ], span={"base": 4, "sm": 2}),
                    
                    # Grosor de borde
                    dmc.GridCol([
                        dmc.NumberInput(
                            id={"type": "col-border-width", "nivel": nivel_id, "col": idx},
                            label="Grosor" if idx == 0 else None,
                            min=0.5, max=3, step=0.5, decimalScale=1,
                            value=bordes.get("superior", {}).get("grosor", 1),
                            size="xs"
                        )
                    ], span={"base": 4, "sm": 1}),
                    
                    # Color de borde
                    dmc.GridCol([
                        dmc.ColorInput(
                            id={"type": "col-border-color", "nivel": nivel_id, "col": idx},
                            label="Borde" if idx == 0 else None,
                            value=bordes.get("superior", {}).get("color", "#333333"),
                            format="hex",
                            size="xs"
                        )
                    ], span={"base": 4, "sm": 1}),
                ], gutter="xs", mb=5, align="flex-start")
                
                filas_columnas.append(fila_principal)
            
            # Badge de tipo
            tipo_component = dmc.Badge("ESTÁTICO", color="blue", variant="filled", size="sm") if not es_dinamico else \
                             dmc.Badge("AUTORRELLENO", color="orange", variant="filled", size="sm")
                             
            # Bloque de configuración dinámica (solo para 'autorrelleno')
            dynamic_config_block = None
            if es_dinamico:
                dynamic_config_block = dmc.Grid([
                    dmc.GridCol([
                        dmc.Checkbox(
                            id={"type": "grid-level-alternate", "index": nivel_id},
                            label="Sombreado alterno",
                            checked=sombreado_alterno,
                            size="xs",
                            mt=5
                        )
                    ], span=4),
                    dmc.GridCol([
                        dmc.ColorInput(
                            id={"type": "grid-level-even-color", "index": nivel_id},
                            label="Color Par",
                            value=color_par,
                            format="hex",
                            size="xs"
                        )
                    ], span=4),
                    dmc.GridCol([
                        dmc.ColorInput(
                            id={"type": "grid-level-odd-color", "index": nivel_id},
                            label="Color Impar",
                            value=color_impar,
                            format="hex",
                            size="xs"
                        )
                    ], span=4),
                ], mt=10, pb=5, style={"borderTop": "1px dashed #ddd"})

            # Bloque del nivel
            nivel_component = dmc.Accordion(
                children=[
                    dmc.AccordionItem(
                        value=f"nivel-{nivel_id}",
                        children=[
                            dmc.AccordionControl(
                                dmc.Group([
                                    dmc.Text(f"Nivel {nivel_id}", fw="bold"),
                                    tipo_component,
                                    dmc.Badge(f"{num_cols} cols", color="gray", variant="light", size="sm"),
                                    dmc.Text(f"Σ {suma_anchos:.2f} cm", 
                                            size="xs", 
                                            c="red" if excede else "green"),
                                ], gap="sm")
                            ),
                            dmc.AccordionPanel([
                                # Selector de número de columnas, alto de fila y fuentes
                                dmc.Paper([
                                    dmc.Grid([
                                        # Num Columnas
                                        dmc.GridCol([
                                            dmc.Group([
                                                dmc.Text("Nº Columnas:", size="sm"),
                                                dmc.NumberInput(
                                                    id={"type": "grid-level-num-cols", "index": nivel_id},
                                                    min=1, max=20, step=1,
                                                    value=num_cols,
                                                    size="xs",
                                                    style={"width": "60px"}
                                                ),
                                            ], gap="xs"),
                                        ], span=3),
                                        
                                        # Alto fila
                                        dmc.GridCol([
                                            dmc.Group([
                                                dmc.Text("Alto fila:", size="sm"),
                                                dmc.NumberInput(
                                                    id={"type": "grid-level-row-height", "index": nivel_id},
                                                    min=0.3, max=3, step=0.1, decimalScale=1,
                                                    value=alto_fila,
                                                    size="xs",
                                                    style={"width": "60px"}
                                                ),
                                                dmc.Text("cm", size="xs", c="dimmed"),
                                            ], gap="xs"),
                                        ], span=3),
                                        
                                        # Fuente
                                        dmc.GridCol([
                                            dmc.Group([
                                                dmc.Text("Fuente:", size="sm"),
                                                dmc.Select(
                                                    id={"type": "grid-level-font-family", "index": nivel_id},
                                                    data=font_options,
                                                    value=fuente_nivel,
                                                    size="xs",
                                                    style={"width": "110px"},
                                                    clearable=False
                                                ),
                                            ], gap="xs"),
                                        ], span=3),
                                        
                                        # Tamaño Fuente
                                        dmc.GridCol([
                                            dmc.Group([
                                                dmc.Text("Tamaño:", size="sm"),
                                                dmc.NumberInput(
                                                    id={"type": "grid-level-font-size", "index": nivel_id},
                                                    min=6, max=24, step=1,
                                                    value=tamano_nivel,
                                                    size="xs",
                                                    style={"width": "60px"}
                                                ),
                                            ], gap="xs"),
                                        ], span=3),
                                    ]),
                                    # Insertar bloque de configuración dinámica si procede
                                    dynamic_config_block if es_dinamico else None,
                                ], p="xs", withBorder=True, radius="sm", mb=10, bg="gray.0"),
                                
                                # Alerta si excede el ancho
                                dmc.Alert(
                                    children=f"⚠ La suma de anchos ({suma_anchos:.2f} cm) excede el ancho máximo ({ancho_total:.1f} cm).",
                                    color="red",
                                    withCloseButton=False,
                                    mb=10
                                ) if excede else None,
                                
                                # Encabezado de columnas
                                dmc.Text("Configuración de columnas:", size="sm", fw="bold", mb=5),
                                
                                # Filas de columnas
                                html.Div(filas_columnas),
                            ]),
                        ],
                    )
                ],
                variant="separated",
                chevronPosition="left",
                value=f"nivel-{nivel_id}",
                mb=10
            )
            nivel_components.append(nivel_component)
        
        return nivel_components 
    
    # Callback para actualizar el ancho disponible
    @app.callback(
        Output("grid-available-width", "children"),
        Input("table-width", "value")
    )
    def actualizar_ancho_disponible(ancho):
        return f"Ancho disponible: {ancho or 18.0} cm"

    # Callback para generar previsualización de la tabla
    @app.callback(
        Output("table-preview-container", "children"),
        [Input("store-grid-levels", "data"),
         Input("table-width", "value")],
        prevent_initial_call=True
    )
    def generar_preview_tabla(grid_data, ancho_tabla):
        """Genera una previsualización visual HTML de la tabla"""
        niveles = grid_data.get("niveles", []) if grid_data else []
        
        if not niveles:
            return dmc.Text("Añade niveles para ver la previsualización de la tabla.", 
                          size="sm", c="dimmed", ta="center", py=20)
        
        # Factor de escala: convertir cm a px (aproximado)
        escala = 28  # 1 cm = 28 px en el preview
        
        tablas_niveles = []
        
        for nivel in niveles:
            tipo_nivel = nivel.get("tipo", "estatico")
            es_dinamico = tipo_nivel == "autorrelleno"
            
            # Configuración dinámica
            config_dinamica = nivel.get("configuracion_dinamica", {})
            sombreado_alterno = config_dinamica.get("sombreado_alterno", True)
            color_par = config_dinamica.get("color_par", "#f8f9fa")
            color_impar = config_dinamica.get("color_impar", "#ffffff")
            
            columnas = nivel.get("columnas", [])
            alto_fila = nivel.get("alto_fila", 0.5)
            
            # Obtener estilos de nivel
            estilo_nivel = nivel.get("estilo", {})
            fuente_default = estilo_nivel.get("fuente", "Aptos")
            tamano_default = estilo_nivel.get("tamano", 10)
            
            # Mapeo de fuentes simple para preview
            font_map = {
                "Helvetica": "Helvetica, Arial, sans-serif",
                "Times-Roman": "'Times New Roman', Times, serif",
                "Courier": "'Courier New', Courier, monospace",
                "Arial": "Arial, Helvetica, sans-serif",
                "Aptos": "Aptos, sans-serif",
                "Verdana": "Verdana, Geneva, sans-serif",
                "Tahoma": "Tahoma, Verdana, sans-serif",
                "Trebuchet MS": "'Trebuchet MS', Helvetica, sans-serif",
                "Georgia": "Georgia, serif",
                "Garamond": "Garamond, serif",
                "Roboto": "Roboto, sans-serif",
                "Open Sans": "'Open Sans', sans-serif",
                "Lato": "Lato, sans-serif",
            }
            font_family_css = font_map.get(fuente_default, "sans-serif")
            
            # Determinar cuántas filas renderizar en el preview
            # Si es estático: 1 fila. Si es dinámico: 3 filas simuladas
            filas_a_renderizar = 3 if es_dinamico else 1
            
            filas_nivel_html = []
            
            for i_fila in range(filas_a_renderizar):
                celdas_fila = []
                # Calcular color de fondo para esta fila simulada si es dinámica
                bg_fila_dinamica = None
                if es_dinamico:
                    if sombreado_alterno:
                        bg_fila_dinamica = color_par if (i_fila % 2 == 0) else color_impar
                    else:
                        bg_fila_dinamica = color_par # o blanco, según preferencia
                
                for col in columnas:
                    ancho_col = col.get("ancho", 3.0)
                    contenido = col.get("contenido", "")
                    formato = col.get("formato", {})
                    bordes = col.get("bordes", {})
                    
                    # Obtener estilos
                    # Si es dinámico, usamos el color calculado, si no, el de la columna
                    if es_dinamico:
                         color_fondo = bg_fila_dinamica
                    else:
                         color_fondo = formato.get("color_fondo", "#ffffff")
                         
                    color_texto = formato.get("color_texto", "#333333")
                    tamano_fuente = tamano_default 
                    negrita = formato.get("negrita", False)
                    alineacion = formato.get("alineacion", "center")
                    
                    # Simular contenido variable para niveles dinámicos
                    contenido_mostrar = contenido
                    if es_dinamico:
                        if i_fila == 0:
                            # Extraer clave si tiene formato [Clave] o usar contenido
                            if contenido.startswith("[") and contenido.endswith("]"):
                                clave = contenido[1:-1]
                                contenido_mostrar = f"Valor {clave}"
                            else:
                                 contenido_mostrar = f"{contenido}"
                        else:
                             contenido_mostrar = ""
                    
                    # Determinar bordes
                    b_sup = bordes.get("superior", {}).get("activo", True)
                    b_inf = bordes.get("inferior", {}).get("activo", True)
                    b_izq = bordes.get("izquierdo", {}).get("activo", True)
                    b_der = bordes.get("derecho", {}).get("activo", True)
                    grosor = bordes.get("superior", {}).get("grosor", 1)
                    color_borde = bordes.get("superior", {}).get("color", "#333333")
                    
                    # Estilo de celda
                    estilo_celda = {
                        "width": f"{ancho_col * escala}px",
                        "minWidth": f"{ancho_col * escala}px",
                        "maxWidth": f"{ancho_col * escala}px",
                        "height": f"{alto_fila * escala}px",
                        "backgroundColor": color_fondo,
                        "color": color_texto,
                        "fontFamily": font_family_css,
                        "fontSize": f"{tamano_fuente}px",
                        "fontWeight": "bold" if negrita else "normal",
                        "textAlign": alineacion,
                        "verticalAlign": "middle",
                        "padding": "2px 4px",
                        "borderTop": f"{grosor}px solid {color_borde}" if b_sup else "none",
                        "borderBottom": f"{grosor}px solid {color_borde}" if b_inf else "none",
                        "borderLeft": f"{grosor}px solid {color_borde}" if b_izq else "none",
                        "borderRight": f"{grosor}px solid {color_borde}" if b_der else "none",
                        "whiteSpace": "nowrap",
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "boxSizing": "border-box"
                    }
                    
                    celdas_fila.append(html.Td(contenido_mostrar, style=estilo_celda))
                
                filas_nivel_html.append(html.Tr(celdas_fila))
            
            # Crear una tabla independiente para este nivel
            tabla_nivel = html.Table(
                children=[html.Tbody(filas_nivel_html)],
                style={
                    "borderCollapse": "collapse",
                    "tableLayout": "auto",
                    "width": "max-content", # Ajustar al contenido
                    "margin": "0",
                    "padding": "0",
                    "display": "block" # Asegurar que se comporte como bloque
                }
            )
            tablas_niveles.append(tabla_nivel)
        
        return html.Div([
            dmc.Text(f"Vista previa (escala 1cm ≈ {escala}px)", size="xs", c="dimmed", mb=5),
            html.Div(tablas_niveles, style={"display": "flex", "flexDirection": "column"})
        ])

    # Callback para abrir/cerrar el modal de Parámetros JSON
    @app.callback(
        Output("modal-json-params", "opened"),
        [Input("btn-open-json-modal", "n_clicks"),
         Input("btn-close-json-modal", "n_clicks")],
        State("modal-json-params", "opened"),
        prevent_initial_call=True
    )
    def toggle_json_modal(open_clicks, close_clicks, is_open):
        from dash import ctx
        if not ctx.triggered:
            return is_open
        triggered_id = ctx.triggered_id
        if triggered_id == "btn-open-json-modal":
            return True
        elif triggered_id == "btn-close-json-modal":
            return False
        return is_open

    @app.callback(
        Output("table-parameters", "value", allow_duplicate=True),
        Input("store-grid-levels", "data"),
        State("table-parameters", "value"),
        prevent_initial_call=True
    )
    def sincronizar_parametros_json(grid_data, current_params_text):
        """Actualiza el campo de parámetros JSON con el contenido de las celdas"""
        import json
        
        niveles = grid_data.get("niveles", []) if grid_data else []
        
        # Intentar preservar parámetros existentes
        parametros = {}
        if current_params_text:
            try:
                parametros = json.loads(current_params_text)
            except:
                parametros = {}
        
        # Asegurar que existe la clave 'sensor' con el valor por defecto si no está presente
        if "sensor" not in parametros:
            parametros["sensor"] = "$CURRENT"

        if not niveles:
            # Si no hay niveles, pero queremos mantener otros parámetros, actualizamos celdas a vacio
            if "celdas" in parametros:
                 parametros["celdas"] = {}
            return json.dumps(parametros, indent=2, ensure_ascii=False)
        
        # Construir/Actualizar objeto de parámetros con el contenido de las celdas
        if "celdas" not in parametros:
            parametros["celdas"] = {}
            
        # Reconstruir celdas para asegurar sincronización con la cuadrícula actual
        parametros["celdas"] = {}
        
        for nivel in niveles:
            nivel_id = nivel.get("id", 1)
            columnas = nivel.get("columnas", [])
            
            for idx, col in enumerate(columnas):
                # Crear clave para cada celda: nivel_columna
                clave = f"N{nivel_id}_C{idx + 1}"
                parametros["celdas"][clave] = col.get("contenido", f"Col {idx + 1}")
        
        return json.dumps(parametros, indent=2, ensure_ascii=False)

    # Callback para actualizar la lista de tablas en el selector
    @app.callback(
        Output("table-selector", "data"),
        [Input("store-componentes", "data"),
         Input("ep-page-number", "value")]
    )
    def update_table_selector(store_data, current_page):
        page_key = str(current_page)

        if (not store_data or 'paginas' not in store_data or
                page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return []

        options = [
            {"value": nombre, "label": nombre}
            for nombre, elemento in store_data['paginas'][page_key]['elementos'].items()
            if elemento["tipo"] == "tabla"
        ]

        return options

    # Callback para rellenar el formulario cuando se selecciona una tabla
    @app.callback(
        [Output("table-x", "value"),
         Output("table-y", "value"),
         Output("table-width", "value"),
         Output("table-height", "value"),
         Output("table-script", "value"),
         Output("table-parameters", "value"),
         Output("table-zindex", "value"),
         Output("table-nombre", "value", allow_duplicate=True),
         Output("table-grupo", "value", allow_duplicate=True),
         Output("store-grid-levels", "data", allow_duplicate=True),
         Output("grid-levels-container", "children", allow_duplicate=True),
         Output("grid-level-count", "children", allow_duplicate=True),
         Output("btn-remove-grid-level", "disabled", allow_duplicate=True)],
        Input("table-selector", "value"),
        [State("store-componentes", "data"),
         State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def fill_table_form(selected_table_name, store_data, current_page):
        # Valores por defecto
        # store_levels, levels_ui, count_text, btn_disabled
        default_levels_ui = generar_ui_niveles([], 18.0)
        defaults = (1.0, 2.0, 18.0, 6.0, "", "", 30, "tabla 1", "", {}, default_levels_ui, "0 niveles", True)
        
        page_key = str(current_page)

        if (not selected_table_name or 'paginas' not in store_data or
                page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return 1.0, 2.0, 18.0, 6.0, "", "", 30, "tabla 1", "", {}, default_levels_ui, "0 niveles", True

        elementos_pagina = store_data['paginas'][page_key]['elementos']

        if selected_table_name in elementos_pagina:
            elemento = elementos_pagina[selected_table_name]
            if elemento["tipo"] == "tabla":
                import json
                
                # Extraer valores
                geometria = elemento.get("geometria", {})
                configuracion = elemento.get("configuracion", {})
                
                # Extraer niveles de cuadrícula
                cuadricula = elemento.get("cuadricula", {})
                niveles = cuadricula.get("niveles", [])
                store_levels = {"niveles": niveles}
                
                # Generar UI de niveles
                ancho = geometria.get("ancho_maximo", 18.0)
                levels_ui = generar_ui_niveles(niveles, ancho)
                count_text = f"{len(niveles)} nivel{'es' if len(niveles) != 1 else ''}"
                btn_disabled = len(niveles) == 0
                
                # Convertir parámetros a texto
                parametros = configuracion.get("parametros", {})
                parametros_texto = ""
                if parametros:
                    try:
                        parametros_texto = json.dumps(parametros, indent=0, ensure_ascii=False)
                    except:
                        parametros_texto = ""
                
                return (
                    geometria.get("x", 1.0),
                    geometria.get("y", 2.0),
                    ancho,
                    geometria.get("alto_maximo", 6.0),
                    configuracion.get("script", ""),
                    parametros_texto,
                    elemento["metadata"].get("zIndex", 30),
                    selected_table_name,
                    elemento.get("grupo", {}).get("nombre", ""),
                    store_levels,
                    levels_ui,
                    count_text,
                    btn_disabled
                )

        return defaults

    # Callback para crear/actualizar tablas
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-table-drawer", "opened", allow_duplicate=True),
         Output("ep-canvas-status", "children", allow_duplicate=True),
         Output("ep-canvas-status", "color", allow_duplicate=True),
         Output("ep-canvas-status", "hide", allow_duplicate=True)],
        Input("btn-create-table", "n_clicks"),
        [State("table-selector", "value"),
         State("table-x", "value"),
         State("table-y", "value"),
         State("table-width", "value"),
         State("table-height", "value"),
         State("table-script", "value"),
         State("table-parameters", "value"),
         State("table-zindex", "value"),
         State("table-nombre", "value"),
         State("table-grupo", "value"),
         State("store-componentes", "data"),
         State("ep-orientation-selector", "value"),
         State("ep-page-number", "value"),
         State("store-grid-levels", "data")],
        prevent_initial_call=True
    )
    def crear_actualizar_tabla(n_clicks, selected_name, x, y, ancho, alto, script, parametros_texto,
                               zindex, nombre, grupo_nombre, store_data, orientacion, current_page, grid_levels_data):
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

        elementos_pagina = store_data['paginas'][page_key]['elementos']

        # Verificar si es una actualización o sobrescritura
        es_actualizacion = selected_name and selected_name == nombre
        sobrescrito = nombre in elementos_pagina and not es_actualizacion

        # Procesar grupo
        grupo_data = {
            "nombre": "Sin grupo",
            "color": "#cccccc"
        }
        if grupo_nombre and grupo_nombre.strip():
             grupo_data["nombre"] = grupo_nombre.strip()

        # Procesar los parámetros
        parametros = {}
        if parametros_texto and parametros_texto.strip():
            try:
                import json
                parametros = json.loads(parametros_texto)
            except json.JSONDecodeError as e:
                return store_data, True, f"Error en el formato de los parámetros: {str(e)}", "red", False

        # Obtener niveles de cuadrícula del store
        niveles_cuadricula = grid_levels_data.get("niveles", []) if grid_levels_data else []

        # Crear tabla con la estructura básica
        tabla_datos = {
            "tipo": "tabla",
            "geometria": {
                "x": x,
                "y": y,
                "ancho_maximo": ancho,
                "alto_maximo": alto
            },
            "configuracion": {
                "script": script,
                "parametros": parametros
            },
            "cuadricula": {
                "niveles": niveles_cuadricula
            },
            "grupo": grupo_data,
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
        elementos_pagina[nombre] = tabla_datos

        # Preparar mensaje de estado
        if sobrescrito:
            mensaje = f"Se ha sobrescrito la tabla '{nombre}'."
            color_estado = "yellow"
        elif es_actualizacion:
            mensaje = f"Tabla '{nombre}' actualizada correctamente."
            color_estado = "green"
        else:
            mensaje = f"Tabla '{nombre}' creada correctamente."
            color_estado = "green"

        return store_data, False, mensaje, color_estado, False

    # Callback para borrar la tabla seleccionada
    @app.callback(
        [Output("store-componentes", "data", allow_duplicate=True),
         Output("ep-table-drawer", "opened", allow_duplicate=True),
         Output("table-selector", "value")],
        Input("btn-delete-table", "n_clicks"),
        [State("table-selector", "value"),
         State("store-componentes", "data"),
         State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def borrar_tabla(n_clicks, selected_name, store_data, current_page):
        if not n_clicks or not selected_name:
            return store_data, True, None

        page_key = str(current_page)

        if (page_key not in store_data['paginas'] or
                'elementos' not in store_data['paginas'][page_key]):
            return store_data, True, None

        elementos_pagina = store_data['paginas'][page_key]['elementos']

        if selected_name in elementos_pagina:
            del elementos_pagina[selected_name]

        return store_data, False, None

    # Callback para actualizar el display del ancho total
    @app.callback(
        Output("table-total-width-display", "children"),
        Input("table-width", "value")
    )
    def update_total_width_display(width):
        return f"Disponible: {width} cm"

    # Callback para generar dinámicamente los inputs de ancho por columna
    @app.callback(
        Output("table-column-widths-dynamic", "children"),
        [Input("table-num-columns", "value"),
         Input("table-width", "value"),
         Input("table-width-mode", "value"),
         Input("btn-distribute-columns", "n_clicks")],
        prevent_initial_call=False
    )
    def generate_column_width_inputs(num_columns, total_width, mode, distribute_clicks):
        if not num_columns or num_columns < 1:
            num_columns = 1
        if not total_width:
            total_width = 18.0
            
        # Calcular ancho equitativo
        equal_width = round(total_width / num_columns, 2)
        
        # Generar filas de inputs
        rows = []
        for i in range(num_columns):
            rows.append(
                dmc.Group([
                    dmc.Text(f"Col {i+1}:", size="xs", w=50),
                    dmc.NumberInput(
                        id={"type": "table-col-width-input", "index": i},
                        min=0.5,
                        max=total_width,
                        step=0.1,
                        value=equal_width if mode == "iguales" else equal_width,
                        decimalScale=2,
                        size="xs",
                        style={"width": "80px"},
                        disabled=(mode == "iguales")
                    ),
                    dmc.Text("cm", size="xs", c="dimmed"),
                ], gap="xs", mb=5)
            )
        
        return rows

    # Callback para actualizar la barra de progreso y validación de anchos
    @app.callback(
        [Output("table-width-progress", "value"),
         Output("table-width-progress", "color"),
         Output("table-sum-display", "children"),
         Output("table-sum-display", "c"),
         Output("table-width-alert", "children"),
         Output("table-width-alert", "color"),
         Output("table-width-alert", "hide")],
        [Input({"type": "table-col-width-input", "index": ALL}, "value"),
         Input("table-width", "value"),
         Input("table-width-mode", "value")],
        prevent_initial_call=True
    )
    def update_width_progress(col_widths, total_width, mode):
        if not col_widths or not total_width:
            return 0, "blue", "Suma: 0.0 cm", "blue", "", "blue", True
        
        # Calcular suma de anchos
        suma = sum([w for w in col_widths if w is not None])
        porcentaje = min((suma / total_width) * 100, 100) if total_width > 0 else 0
        
        # Determinar color según la suma
        if suma > total_width:
            color = "red"
            text_color = "red"
            alert_msg = f"⚠️ La suma ({suma:.1f} cm) excede el ancho disponible ({total_width:.1f} cm)"
            alert_color = "red"
            hide_alert = False
        elif suma < total_width * 0.95:
            color = "yellow"
            text_color = "yellow"
            espacio_libre = total_width - suma
            alert_msg = f"ℹ️ Espacio libre: {espacio_libre:.1f} cm"
            alert_color = "yellow"
            hide_alert = False
        else:
            color = "green"
            text_color = "green"
            alert_msg = "✓ Distribución correcta"
            alert_color = "green"
            hide_alert = False
        
        return porcentaje, color, f"Suma: {suma:.1f} cm", text_color, alert_msg, alert_color, hide_alert

    # Callback para generar la vista previa dinámica
    @app.callback(
        Output("table-preview-dynamic", "children"),
        [Input("table-num-columns", "value"),
         Input("table-preview-rows", "value"),
         Input("table-show-headers", "checked"),
         Input("table-border-type", "value"),
         Input("table-border-color", "value"),
         Input("table-shading-style", "value"),
         Input("table-color-even", "value"),
         Input("table-color-odd", "value"),
         Input("table-color-header", "value"),
         Input({"type": "table-col-width-input", "index": ALL}, "value"),
         Input("table-width", "value")],
        prevent_initial_call=False
    )
    def generate_table_preview(num_columns, num_rows, show_headers, border_type,
                               border_color, shading_style, color_even, color_odd,
                               color_header, col_widths, total_width):
        if not num_columns or num_columns < 1:
            num_columns = 1
        if not num_rows or num_rows < 1:
            num_rows = 3
        if not total_width:
            total_width = 18.0
            
        # Calcular anchos proporcionales para la vista previa
        if col_widths and len(col_widths) == num_columns:
            suma = sum([w for w in col_widths if w is not None])
            if suma > 0:
                widths_percent = [(w / suma * 100) if w else (100 / num_columns) for w in col_widths]
            else:
                widths_percent = [100 / num_columns] * num_columns
        else:
            widths_percent = [100 / num_columns] * num_columns
        
        # Estilos de borde
        border_style = "none"
        if border_type == "todos":
            border_style = f"1px solid {border_color}"
        elif border_type == "horizontal":
            border_style = f"1px solid {border_color}"
        elif border_type == "exterior":
            border_style = "none"
        
        # Generar encabezados
        header_row = None
        if show_headers:
            header_cells = []
            for i in range(num_columns):
                cell_style = {
                    "backgroundColor": color_header if shading_style != "ninguno" else "#ffffff",
                    "padding": "6px",
                    "fontWeight": "bold",
                    "textAlign": "center",
                    "width": f"{widths_percent[i]}%"
                }
                if border_type in ["todos", "horizontal"]:
                    cell_style["borderBottom"] = f"1px solid {border_color}"
                if border_type == "todos":
                    cell_style["borderRight"] = f"1px solid {border_color}"
                    cell_style["borderLeft"] = f"1px solid {border_color}" if i == 0 else "none"
                    
                header_cells.append(
                    html.Th(
                        dmc.TextInput(
                            id={"type": "table-preview-header", "index": i},
                            value=f"Columna {i+1}",
                            size="xs",
                            variant="unstyled",
                            style={"width": "100%", "textAlign": "center", "fontWeight": "bold"}
                        ),
                        style=cell_style
                    )
                )
            header_row = html.Thead(html.Tr(header_cells))
        
        # Generar filas de datos
        body_rows = []
        for row_idx in range(num_rows):
            # Determinar color de fondo
            if shading_style == "alternado":
                bg_color = color_even if row_idx % 2 == 0 else color_odd
            elif shading_style == "ninguno":
                bg_color = "#ffffff"
            else:
                bg_color = "#ffffff"
            
            row_cells = []
            for col_idx in range(num_columns):
                cell_style = {
                    "backgroundColor": bg_color,
                    "padding": "6px",
                    "width": f"{widths_percent[col_idx]}%"
                }
                if border_type in ["todos", "horizontal"]:
                    cell_style["borderBottom"] = f"1px solid {border_color}"
                if border_type == "todos":
                    cell_style["borderRight"] = f"1px solid {border_color}"
                    cell_style["borderLeft"] = f"1px solid {border_color}" if col_idx == 0 else "none"
                
                row_cells.append(
                    html.Td(
                        dmc.TextInput(
                            id={"type": "table-preview-cell", "row": row_idx, "col": col_idx},
                            value=f"Dato {row_idx+1}-{col_idx+1}",
                            size="xs",
                            variant="unstyled",
                            style={"width": "100%"}
                        ),
                        style=cell_style
                    )
                )
            body_rows.append(html.Tr(row_cells))
        
        # Construir tabla
        table_style = {"width": "100%", "borderCollapse": "collapse"}
        if border_type == "exterior":
            table_style["border"] = f"1px solid {border_color}"
        
        table_children = []
        if header_row:
            table_children.append(header_row)
        table_children.append(html.Tbody(body_rows))
        
        preview_table = html.Table(
            table_children,
            style=table_style
        )
        
        return preview_table

    # Callback para distribuir columnas equitativamente
    @app.callback(
        Output("table-width-mode", "value", allow_duplicate=True),
        Input("btn-distribute-columns", "n_clicks"),
        prevent_initial_call=True
    )
    def distribute_columns_equally(n_clicks):
        if n_clicks:
            return "iguales"
        return "iguales"

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
         Output("line-grupo", "value", allow_duplicate=True),
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
            return 1.0, 1.0, 5.0, 5.0, 1, "#000000", "Línea 1", "", 10

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
                    elemento.get("grupo", {}).get("nombre", ""),
                    elemento["metadata"].get("zIndex", 10)
                )

        # Si no se encuentra
        return 1.0, 1.0, 5.0, 5.0, 1, "#000000", "Línea 1", "", 10

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
         Output("rect-grupo", "value", allow_duplicate=True),
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
            return 1.0, 1.0, 5.0, 3.0, 1, "#000000", "#FFFFFF", 100, "Rectángulo 1", "", 5

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
                    elemento.get("grupo", {}).get("nombre", ""),
                    elemento["metadata"].get("zIndex", 5)
                )

        return 1.0, 1.0, 5.0, 3.0, 1, "#000000", "#FFFFFF", 100, "Rectángulo 1", "", 5


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
        State("rect-grupo", "value"), # Nuevo State
        State("rectangle-zindex", "value"),  # Incluir zIndex
        State("store-componentes", "data"),
        State("ep-orientation-selector", "value"),
         State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def crear_actualizar_rectangulo(n_clicks, selected_name, x, y, ancho, alto, grosor_borde,
                                    color_borde, color_relleno, opacidad, nombre, grupo_nombre, zindex, store_data, orientacion,
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

        # Procesar grupo
        grupo_data = {
            "nombre": "Sin grupo",
            "color": "#cccccc"
        }
        if grupo_nombre and grupo_nombre.strip():
             grupo_data["nombre"] = grupo_nombre.strip()

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
            "estilo": {
                "grosor_borde": grosor_borde,
                "color_borde": color_borde,
                "color_relleno": color_relleno,
                "opacidad": opacidad
            },
            "grupo": grupo_data,
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
         Output("text-nombre", "value"),
         Output("text-grupo", "data"),
         Output("text-grupo", "value")],
        Input("ep-add-text-btn", "n_clicks"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def open_text_drawer(n_clicks, store_data):
        if not n_clicks:
            return False, "texto 1", [], ""

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

        # Extraer grupos
        grupos_set = set()
        if 'paginas' in store_data:
             for p in store_data['paginas'].values():
                 if 'elementos' in p:
                     for elem in p['elementos'].values():
                         if 'grupo' in elem and 'nombre' in elem['grupo']:
                             g_nom = elem['grupo']['nombre']
                             if g_nom and g_nom != "Sin grupo":
                                grupos_set.add(g_nom)
        
        opciones_grupo = sorted(list(grupos_set))

        return True, nombre_sugerido, opciones_grupo, ""

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
         Output("text-grupo", "value", allow_duplicate=True), # Nuevo Output
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
            return 1.0, 1.0, 5.0, 2.0, 0, "Helvetica", 10, "normal", "normal", "#000000", "left", "top", True, "", "Texto 1", "", 20, False

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
                    elemento.get("grupo", {}).get("nombre", ""), # Grupo (Pos 16)
                    elemento["metadata"].get("zIndex", 20),
                    editable  # valor de editable
                )

        # Si no se encuentra
        return 1.0, 1.0, 5.0, 2.0, 0, "Helvetica", 10, "normal", "normal", "#000000", "left", "top", True, "", "Texto 1", "", 20, False

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
        State("text-grupo", "value"), # Nuevo State
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
                               contenido_texto, nombre, grupo_nombre, zindex, editable, store_data, orientacion, current_page):
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

        es_actualizacion = selected_name and selected_name == nombre
        sobrescrito = nombre in elementos_pagina and not es_actualizacion

        # Procesar grupo
        grupo_data = {
            "nombre": "Sin grupo",
            "color": "#cccccc"
        }
        if grupo_nombre and grupo_nombre.strip():
             grupo_data["nombre"] = grupo_nombre.strip()

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
            "contenido": {
                "texto": contenido_texto or "",
                "ajuste_automatico": ajuste_automatico,
                "editable": editable  # ahora viene de checked
            },
            "grupo": grupo_data,
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
         Output("image-maintain-aspect-ratio", "checked", allow_duplicate=True),
         Output("image-grupo", "data"),
         Output("image-grupo", "value")],
        Input("ep-add-image-btn", "n_clicks"),
        State("store-componentes", "data"),
        prevent_initial_call=True
    )
    def open_image_drawer(n_clicks, store_data):
        if not n_clicks:
            return True, nombre_sugerido, True, [], ""

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

        # Extraer grupos
        grupos_set = set()
        if 'paginas' in store_data:
             for p in store_data['paginas'].values():
                 if 'elementos' in p:
                     for elem in p['elementos'].values():
                         if 'grupo' in elem and 'nombre' in elem['grupo']:
                             g_nom = elem['grupo']['nombre']
                             if g_nom and g_nom != "Sin grupo":
                                grupos_set.add(g_nom)
        
        opciones_grupo = sorted(list(grupos_set))

        return True, nombre_sugerido, True, opciones_grupo, "" # Maintain Checked=True

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
         Output("image-grupo", "value", allow_duplicate=True), # Nuevo Output
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
            return 1.0, 1.0, 5.0, 3.0, 100, True, "Imagen 1", "", 15, 0

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
                    elemento.get("grupo", {}).get("nombre", ""), # Grupo
                    elemento["metadata"].get("zIndex", 15),
                    elemento["estilo"].get("reduccion", 0)  # Obtener reducción o valor predeterminado
                )

        # Si no se encuentra
        return 1.0, 1.0, 5.0, 3.0, 100, True, "Imagen 1", "", 15, 0

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
        State("image-grupo", "value"), # Nuevo State
        State("image-zindex", "value"),
        State("image-reduction", "value"),  # Nuevo parámetro
        State("store-componentes", "data"),
        State("image-url", "value"),
        State("ep-orientation-selector", "value"),
        State("ep-page-number", "value")],
        prevent_initial_call=True
    )
    def crear_actualizar_imagen(n_clicks, selected_name, x, y, ancho, alto, opacidad, mantener_proporcion,
                                nombre, grupo_nombre, zindex, reduccion, store_data, image_url, orientacion, current_page):
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

        # Procesar grupo
        grupo_data = {
            "nombre": "Sin grupo",
            "color": "#cccccc"
        }
        if grupo_nombre and grupo_nombre.strip():
             grupo_data["nombre"] = grupo_nombre.strip()

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
            "grupo": grupo_data,
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

    # (Callback process_json_upload eliminado en favor de handle_file_uploads unificado al final del archivo)


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

    # ==============================================================================
    # ==============================================================================
    # ==============================================================================
    # CALLBACK UNIFICADO PARA GESTIÓN DE CARGA DE ARCHIVOS
    # ==============================================================================
    @app.callback(
        [Output('store-componentes', 'data', allow_duplicate=True),
         Output('ep-canvas-status', 'children', allow_duplicate=True),
         Output('ep-canvas-status', 'color', allow_duplicate=True),
         Output('ep-canvas-status', 'hide', allow_duplicate=True),
         Output('ep-page-number', 'value', allow_duplicate=True),
         Output('ep-orientation-selector', 'value', allow_duplicate=True)],
        [Input('ep-upload-group', 'contents'),
         Input('ep-upload-json', 'contents')],
        [State('ep-upload-group', 'filename'),
         State('ep-upload-json', 'filename'),
         State('store-componentes', 'data')],
        prevent_initial_call=True
    )
    def handle_file_uploads(group_contents, template_contents, group_filename, template_filename, store_data):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update, True, dash.no_update, dash.no_update

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # ----------------------------------------------------------------------
        # CASO 1: IMPORTAR GRUPO (Fusión)
        # ----------------------------------------------------------------------
        if trigger_id == 'ep-upload-group' and group_contents:
            try:
                content_type, content_string = group_contents.split(',')
                decoded = base64.b64decode(content_string)
                loaded_data = json.loads(decoded)

                if 'elementos' not in loaded_data:
                    return dash.no_update, f"Error: '{group_filename}' no es un grupo válido.", "red", False, dash.no_update, dash.no_update

                # Copiar assets
                nombre_grupo = group_filename.replace('.json', '')
                try:
                    BASE_PLANTILLAS = Path(__file__).parents[1] / "biblioteca_plantillas"
                    nom_plantilla = store_data.get('configuracion', {}).get('nombre_plantilla', 'temp_plantilla') or 'temp_plantilla'
                    copiar_assets_grupo(nombre_grupo, str(BASE_PLANTILLAS / nom_plantilla))
                except Exception:
                    pass # Fallo silencioso en assets no es crítico

                # Fusionar
                pagina_actual = store_data.get('pagina_actual', "1")
                if pagina_actual not in store_data['paginas']:
                     store_data['paginas'][pagina_actual] = {'elementos': {}, 'configuracion': {'orientacion': 'portrait'}}
                
                if 'elementos' not in store_data['paginas'][pagina_actual]:
                    store_data['paginas'][pagina_actual]['elementos'] = {}

                elems_actuales = store_data['paginas'][pagina_actual]['elementos']
                sufijo = str(uuid.uuid4())[:4]
                count = 0
                
                for id_elem, props in loaded_data['elementos'].items():
                    nuevo_id = f"{id_elem}_{sufijo}"
                    # Ajuste path imagen
                    if props.get('tipo') == 'imagen' and 'imagen' in props:
                        if not props['imagen'].get('ruta_nueva', '').startswith('assets/'):
                            n = props['imagen'].get('nombre_archivo', '')
                            if n: props['imagen']['ruta_nueva'] = f"assets/{n}"
                    elems_actuales[nuevo_id] = props
                    count += 1
                
                store_data['paginas'][pagina_actual]['elementos'] = elems_actuales
                return store_data, f"Grupo '{group_filename}' importado ({count} elementos)", "green", False, dash.no_update, dash.no_update

            except Exception as e:
                return dash.no_update, f"Error importando grupo: {e}", "red", False, dash.no_update, dash.no_update

        # ----------------------------------------------------------------------
        # CASO 2: CARGAR PLANTILLA (Reemplazo)
        # ----------------------------------------------------------------------
        elif trigger_id == 'ep-upload-json' and template_contents:
            try:
                content_type, content_string = template_contents.split(',')
                decoded = base64.b64decode(content_string)
                loaded_data = json.loads(decoded)

                def ensure_editable(elems):
                    if not elems: return
                    for _, el in elems.items():
                        if el.get("tipo") == "texto" and "contenido" in el and "editable" not in el["contenido"]:
                            el["contenido"]["editable"] = False

                new_store = {
                    'paginas': {}, 'pagina_actual': "1", 'seleccionado': None,
                    'configuracion': {'nombre_plantilla': '', 'version': '1.0', 'num_paginas': 1}
                }

                if 'paginas' in loaded_data:
                    for k, v in loaded_data['paginas'].items():
                        if "configuracion" not in v: v["configuracion"] = {"orientacion": "portrait"}
                        if "orientacion" not in v["configuracion"]: v["configuracion"]["orientacion"] = "portrait"
                        if "elementos" in v: ensure_editable(v["elementos"])
                    new_store = loaded_data
                    # Asegurar pagina_actual en el store raíz
                    if 'pagina_actual' not in new_store:
                        new_store['pagina_actual'] = "1"
                else:
                    # Formato antiguo
                    ori = loaded_data.get('configuracion', {}).get('orientacion', 'portrait')
                    if "elementos" in loaded_data: ensure_editable(loaded_data["elementos"])
                    new_store = {
                        'paginas': {"1": {'elementos': loaded_data.get('elementos', {}), 'configuracion': {'orientacion': ori}}},
                        'pagina_actual': "1",
                        'configuracion': loaded_data.get('configuracion', {'version': '1.0', 'num_paginas': 1})
                    }

                # Determinar orientación inicial
                orientation = "portrait"
                if "1" in new_store['paginas'] and "configuracion" in new_store['paginas']["1"]:
                    orientation = new_store['paginas']["1"]["configuracion"].get("orientacion", "portrait")

                return new_store, f"Plantilla '{template_filename}' cargada", "green", False, "1", orientation

            except Exception as e:
                return dash.no_update, f"Error cargando plantilla: {e}", "red", False, dash.no_update, dash.no_update

        return dash.no_update, dash.no_update, dash.no_update, True, dash.no_update, dash.no_update

    # Callback para abrir carpetas locales (solo grupos)
    @app.callback(
        Input("btn-open-folder-group", "n_clicks"),
        prevent_initial_call=True
    )
    def open_local_folders(n_group):
        ctx = dash.callback_context
        if not ctx.triggered: return
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        base_dir = Path(__file__).resolve().parent.parent
        
        target_dir = None
        if trigger_id == "btn-open-folder-group":
            target_dir = base_dir / "biblioteca_grupos"
            
        if target_dir:
            try:
                if not target_dir.exists():
                    target_dir.mkdir(parents=True, exist_ok=True)
                os.startfile(target_dir)
            except Exception as e:
                print(f"Error abriendo carpeta {target_dir}: {e}")
        return

    # ==============================================================================
    # CALLBACKS PARA CREAR GRUPO (TransferList + Guardado)
    # ==============================================================================

    # 1. Abrir modal e inicializar listas
    @app.callback(
        [Output("modal-create-group", "opened"),
         Output("store-transfer-state", "data"),
         Output("group-name-input", "value"),
         Output("group-desc-input", "value"),
         Output("create-group-msg", "children")],
        [Input("ep-create-group-btn", "n_clicks"),
         Input("btn-cancel-create-group", "n_clicks"),
         Input("btn-save-create-group", "n_clicks")],
        [State("store-componentes", "data"),
         State("modal-create-group", "opened")],
        prevent_initial_call=True
    )
    def toggle_create_group_modal(n_open, n_cancel, n_save, store_data, is_open):
        ctx = dash.callback_context
        if not ctx.triggered: return dash.no_update
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "ep-create-group-btn":
            # Cargar elementos de la página actual
            try:
                if not store_data:
                    return True, {"left": [], "right": []}, "", "", "Error: No hay datos en el almacén (Store vacío)."

                pagina_actual = str(store_data.get('pagina_actual', "1"))
                paginas = store_data.get('paginas', {})
                
                # Debug
                print(f"DEBUG: Creando grupo. Pág actual: {pagina_actual}. Páginas disponibles: {list(paginas.keys())}")
                
                datos_pagina = paginas.get(pagina_actual, {})
                elementos = datos_pagina.get('elementos', {})
                
                if not elementos:
                     # Intentar buscar en int por si acaso
                     if int(pagina_actual) in paginas:
                         print(f"DEBUG: Encontrada página como int {int(pagina_actual)}")
                         elementos = paginas.get(int(pagina_actual), {}).get('elementos', {})

                # Crear lista para el estado
                left_list = []
                for k, v in elementos.items():
                    tipo = v.get('tipo', 'Desconocido')
                    texto_desc = k
                    if tipo == 'texto':
                         cont = v.get('contenido', {}).get('texto', '')
                         if len(cont) > 20: cont = cont[:20] + "..."
                         texto_desc = f"Texto: '{cont}'"
                    elif tipo == 'imagen':
                         nombre = v.get('imagen', {}).get('nombre_archivo', 'imagen')
                         if len(nombre) > 20: nombre = nombre[:20] + "..."
                         texto_desc = f"Img: {nombre}"
                    else:
                        texto_desc = f"{tipo}: {k}"
                        
                    left_list.append({"value": k, "label": texto_desc})
                
                if not left_list:
                    # Mensaje aviso si no hay nada
                    msg = f"No hay elementos en la página {pagina_actual}."
                    return True, {"left": [], "right": []}, "", "", msg

                return True, {"left": left_list, "right": []}, "", "", ""
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                return True, {"left": [], "right": []}, "", "", f"Error cargando elementos: {e}"
                
        elif trigger_id == "btn-cancel-create-group":
            return False, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
        return dash.no_update
        
    # 2. Renderizar listas cuando cambia el Store
    @app.callback(
        [Output("transfer-list-left", "children"),
         Output("transfer-list-right", "children")],
        Input("store-transfer-state", "data")
    )
    def render_transfer_lists(data):
        if not data: return [], []
        
        left_items = data.get("left", [])
        right_items = data.get("right", [])
        
        # Ojo: dmc.CheckboxGroup en v2 usa children=[dmc.Checkbox(..)]
        left_checkboxes = [dmc.Checkbox(label=item["label"], value=item["value"], mb=5) for item in left_items]
        right_checkboxes = [dmc.Checkbox(label=item["label"], value=item["value"], mb=5) for item in right_items]
        
        return left_checkboxes, right_checkboxes

    # 3. Mover items (Transferencia)
    @app.callback(
        [Output("store-transfer-state", "data", allow_duplicate=True),
         Output("transfer-list-left", "value"),  # Limpiar selección
         Output("transfer-list-right", "value")], # Limpiar selección
        [Input("btn-transfer-move-right", "n_clicks"),
         Input("btn-transfer-move-left", "n_clicks")],
        [State("transfer-list-left", "value"),
         State("transfer-list-right", "value"),
         State("store-transfer-state", "data")],
        prevent_initial_call=True
    )
    def transfer_items(n_right, n_left, selected_left, selected_right, current_data):
        ctx = dash.callback_context
        if not ctx.triggered: return dash.no_update
        
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        
        new_left = current_data["left"].copy()
        new_right = current_data["right"].copy()
        
        if trigger == "btn-transfer-move-right" and selected_left:
            items_to_move = [item for item in new_left if item["value"] in selected_left]
            new_left = [item for item in new_left if item["value"] not in selected_left]
            new_right.extend(items_to_move)

        elif trigger == "btn-transfer-move-left" and selected_right:
            items_to_move = [item for item in new_right if item["value"] in selected_right]
            new_right = [item for item in new_right if item["value"] not in selected_right]
            new_left.extend(items_to_move)
            
        return {"left": new_left, "right": new_right}, [], []

    # 4. Guardar grupo seleccionado
    @app.callback(
        [Output("create-group-msg", "children", allow_duplicate=True),
         Output("create-group-msg", "color"),
         Output("modal-create-group", "opened", allow_duplicate=True)], # Nuevo output para cerrar
        Input("btn-save-create-group", "n_clicks"),
        [State("store-transfer-state", "data"),
         State("group-name-input", "value"),
         State("group-desc-input", "value"),
         State("store-componentes", "data")],
        prevent_initial_call=True
    )
    def save_new_group(n_clicks, transfer_data, name, desc, store_data):
        if not n_clicks: return dash.no_update, dash.no_update, dash.no_update
        
        right_items = transfer_data.get("right", [])
        if not right_items:
            return "Error: Lista de exportación vacía", "red", dash.no_update
        if not name:
            return "Error: Debes poner un nombre al grupo", "red", dash.no_update
            
        ids_a_exportar = [item["value"] for item in right_items]
        
        pagina_actual = str(store_data.get('pagina_actual', "1"))
        paginas = store_data.get('paginas', {})
        # Usar la misma lógica de búsqueda robusta que en el toggle
        elementos = paginas.get(pagina_actual, {}).get('elementos', {})
        if not elementos and int(pagina_actual) in paginas:
             elementos = paginas.get(int(pagina_actual), {}).get('elementos', {})
        
        seleccion_dict = {k: v for k, v in elementos.items() if k in ids_a_exportar}
        
        APP_ASSETS = Path(__file__).resolve().parent.parent / "assets"
        exito, msg = guardar_nuevo_grupo(name, desc, seleccion_dict, APP_ASSETS)
        
        if exito:
            # Si tuvo éxito, cerramos el modal (y quizás podríamos mostrar una notificación global, 
            # pero por ahora cerramos y el usuario verá la carpeta si la abre).
            # Opcional: Dejar el mensaje 1 seg y cerrar? Dash no permite "sleep" fácil en callbacks sin bloquear.
            # Mejor cerramos directamente.
            return "", "green", False
        else:
            # Si falla (ej: ya existe), mantenemos abierto y mostramos error
            return msg, "red", True

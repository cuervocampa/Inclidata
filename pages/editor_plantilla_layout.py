# pages/editor_plantilla_layout.py
# Layout del editor de plantillas JSON. Separado de callbacks para facilitar mantenimiento.

from dash import html, dcc
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify

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



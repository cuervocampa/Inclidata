# pages/graficar_layout.py
# Layout de la página Graficar. Separado de la lógica de callbacks para facilitar mantenimiento.

from datetime import datetime

from dash import html, dcc
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify

def layout():
    return html.Div([
            html.Div(style={'height': '1.5rem'}),  # Espacio al comienzo de la página
            dmc.Grid([
                dmc.GridCol(
                    dmc.Card(
                        html.Div(
                            "Plano de localización de dispositivo",
                            style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'height': '100%', 'minHeight': '200px',
                                   'color': 'var(--id-text-muted)', 'fontSize': '0.875rem'}
                        ),
                        shadow='sm', radius='xl', className='id-card',
                        style={'height': '100%'}
                    ), span=8
                ),
                dmc.GridCol([
                    dcc.Store(id='graficar-tubo', storage_type='memory'),
                    html.Span(id="info-hovercard", style={"display": "none"}),

                    # Cabecera: Inclinómetro + botón importar
                    dmc.Paper([
                        dmc.Group([
                            dmc.Group([
                                DashIconify(icon="lucide:radio-tower", width=18,
                                            style={"color": "var(--id-primary)"}),
                                dmc.Text("Inclinómetro", fw=600, size="sm",
                                         style={"color": "var(--id-text-primary)"}),
                                dmc.Text(id="sensor-nom-label", size="sm", c="dimmed"),
                            ], gap="xs"),
                            dcc.Upload(
                                id='graficar-uploader',
                                multiple=False,
                                accept='.json',
                                children=dmc.Button(
                                    "Importar",
                                    leftSection=DashIconify(icon="lucide:upload", width=14),
                                    variant="light", size="compact-sm", color="blue",
                                ),
                                style={'cursor': 'pointer'},
                            ),
                        ], justify="space-between"),
                    ], p="xs", radius="md", withBorder=True,
                       style={"marginBottom": "0.5rem"}),

                    # Botones de acción: 2 filas compactas
                    dmc.SimpleGrid([
                        dmc.Button(
                            "Configuración", id="open-config-drawer", n_clicks=None,
                            fullWidth=True, variant="outline", size="compact-sm",
                            leftSection=DashIconify(icon="lucide:settings", width=14),
                            className="id-btn id-btn-outline",
                        ),
                        dmc.Button(
                            "Patrón", id="open-patron-drawer", n_clicks=None,
                            fullWidth=True, variant="outline", size="compact-sm",
                            leftSection=DashIconify(icon="lucide:scan-line", width=14),
                            className="id-btn id-btn-outline",
                        ),
                    ], cols=2, spacing="xs", style={"marginBottom": "0.4rem"}),

                    dmc.SimpleGrid([
                        dmc.Button(
                            "Umbrales", id="open-umbrales-drawer",
                            fullWidth=True, variant="outline", size="compact-sm",
                            leftSection=DashIconify(icon="lucide:alert-triangle", width=14),
                            className="id-btn id-btn-outline",
                        ),
                        dmc.Button(
                            "PDF", id="btn-abrir-modal-informe",
                            leftSection=DashIconify(icon="lucide:file-down", width=14),
                            variant="filled", fullWidth=True, size="compact-sm",
                            className="id-btn", color="blue",
                        ),
                        dmc.Button(
                            "Excel", id="btn-exportar-datos",
                            leftSection=DashIconify(icon="lucide:grid-3x3", width=14),
                            variant="outline", fullWidth=True, size="compact-sm",
                            className="id-btn id-btn-outline",
                        ),
                    ], cols=3, spacing="xs", style={"marginBottom": "0.4rem"}),

                    # Tarjeta info sensor (scroll si se corta)
                    html.Div(id="sensor-info-card",
                             style={"maxHeight": "200px", "overflowY": "auto"}),
                    # Modal exportar datos
                    dmc.Modal(
                        id="modal-exportar-datos",
                        title="Exportar Datos",
                        centered=True,
                        size="sm",
                        children=[
                            dmc.Text("Selecciona el formato de exportación:", size="sm", style={"marginBottom": "1rem"}),
                            dmc.Group([
                                dmc.Button(
                                    "Exportar JSON",
                                    id="btn-exportar-json",
                                    leftSection=DashIconify(icon="lucide:file-json", width=16),
                                    variant="outline",
                                    className="id-btn id-btn-outline",
                                ),
                                dmc.Button(
                                    "Exportar Excel",
                                    id="btn-exportar-excel",
                                    leftSection=DashIconify(icon="lucide:file-spreadsheet", width=16),
                                    variant="filled",
                                    color="green",
                                    className="id-btn",
                                ),
                            ], justify="center", gap="md"),
                        ],
                    ),
                    dcc.Download(id="descargar-datos-export"),
                ], span=4)
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
                title=dmc.Text("Configuración gráficos", fw="bold", size="lg"),
                id="drawer-config",
                padding="md",
                size="sm",
                children=[
                    # Sección: Altura de gráficos
                    dmc.Text("Seleccionar altura de gráficos", fw="bold", size="sm", c="dimmed", style={"marginBottom": "10px"}),
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
                        style={"marginBottom": "30px"}
                    ),
                    
                    dmc.Divider(style={"marginTop": "15px", "marginBottom": "20px"}),
                    
                    # Sección: Unidades y orden eje vertical
                    dmc.Text("Unidades eje vertical", fw="bold", size="sm", c="dimmed", style={"marginBottom": "10px"}),
                    dmc.Group([
                        dmc.Text("Unidades", style={"marginRight": "10px"}),
                        dmc.Select(
                            id="unidades_eje",
                            data=[
                                {"value": "index", "label": "índice"},
                            {"value": "cota_abs", "label": "cota absoluta"},
                                {"value": "depth", "label": "profundidad"}
                            ],
                            value="depth",
                            style={"width": "150px"}
                        ),
                    ], style={"marginBottom": "20px"}),
                    
                    dmc.Text("Orden del eje vertical", fw="bold", size="sm", c="dimmed", style={"marginBottom": "10px"}),
                    dmc.SegmentedControl(
                        id="orden",
                        value="descendente",
                        data=[
                            {"value": "ascendente", "label": "↑ Ascendente"},
                            {"value": "descendente", "label": "↓ Descendente"},
                        ],
                        fullWidth=True,
                        color="blue",
                        radius="xl",
                        size="md",
                        style={"marginBottom": "20px"}
                    ),
                    
                    dmc.Divider(style={"marginTop": "15px", "marginBottom": "20px"}),
                    
                    # Sección: Estilo de colores
                    dmc.Text("Estilo de colores", fw="bold", size="sm", c="dimmed", style={"marginBottom": "10px"}),
                    dmc.SegmentedControl(
                        id="color_scheme_selector",
                        value="monocromo",
                        data=[
                            {"value": "monocromo", "label": "Monocromo"},
                            {"value": "multicromo", "label": "Multicromo"},
                        ],
                        fullWidth=True,
                        color="blue",
                        radius="xl",
                        size="md",
                        style={"marginBottom": "20px"}
                    ),
                    
                    dmc.Divider(style={"marginTop": "15px", "marginBottom": "20px"}),
                    
                    # Sección: Escala Desplazamiento
                    dmc.Text("Escala gráficos Desplazamiento", fw="bold", size="sm", c="dimmed", style={"marginBottom": "10px"}),
                    dmc.SegmentedControl(
                        id="escala_graficos_desplazamiento",
                        value="manual",
                        data=[
                            {"value": "automatica", "label": "Automática"},
                            {"value": "manual", "label": "Manual"},
                        ],
                        fullWidth=True,
                        color="blue",
                        radius="xl",
                        size="sm",
                        style={"marginBottom": "15px"}
                    ),
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
                        gap="xs",
                        style={"width": "100%", "marginBottom": "20px"},
                    ),
                    
                    # Sección: Escala Incremento
                    dmc.Text("Escala gráficos Incremento", fw="bold", size="sm", c="dimmed", style={"marginBottom": "10px"}),
                    dmc.SegmentedControl(
                        id="escala_graficos_incremento",
                        value="manual",
                        data=[
                            {"value": "automatica", "label": "Automática"},
                            {"value": "manual", "label": "Manual"},
                        ],
                        fullWidth=True,
                        color="blue",
                        radius="xl",
                        size="sm",
                        style={"marginBottom": "15px"}
                    ),
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
                        gap="xs",
                        style={"width": "100%", "marginBottom": "20px"},
                    ),
                    
                    # Sección: Escala Evolución Temporal
                    dmc.Text("Escala gráficos Evolución Temporal", fw="bold", size="sm", c="dimmed", style={"marginBottom": "10px"}),
                    dmc.SegmentedControl(
                        id="escala_grafico_temporal",
                        value="manual",
                        data=[
                            {"value": "automatica", "label": "Automática"},
                            {"value": "manual", "label": "Manual"},
                        ],
                        fullWidth=True,
                        color="blue",
                        radius="xl",
                        size="sm",
                        style={"marginBottom": "15px"}
                    ),
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
                        gap="xs",
                        style={"width": "100%", "marginBottom": "30px"},
                    ),
                    
                    dmc.Divider(style={"marginTop": "10px", "marginBottom": "20px"}),
                    
                    dmc.Button("Cerrar", id="close-config-drawer", variant="outline", fullWidth=True)
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
                  html.Div(
                    dmc.Tabs([
                        dmc.TabsList([
                            dmc.TabsTab("Desplazamientos", value="grafico1",
                                        style={'fontWeight': '600', 'fontSize': '0.875rem'}),
                            dmc.TabsTab("Incrementales", value="grafico2",
                                        style={'fontWeight': '600', 'fontSize': '0.875rem'}),
                            dmc.TabsTab("Checksum", value="grafico_chk",
                                        style={'fontWeight': '600', 'fontSize': '0.875rem'}),
                            dmc.TabsTab("Despl. compuestos", value="grafico3",
                                        style={'fontWeight': '600', 'fontSize': '0.875rem'}),
                        ]),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_1_a', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Desplazamiento A", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_1_b', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Desplazamiento B", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                ])
                            ]),
                            value="grafico1"
                        ),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_2_a', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Incremental A", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_2_b', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Incremental B", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                ])
                            ]),
                            value="grafico2"
                        ),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_chk_a', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Checksum A", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_chk_b', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Checksum B", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                ])
                            ]),
                            value="grafico_chk"
                        ),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_3_a', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Desplazamiento A", ta="center")
                                    ], span=4, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_3_b', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Desplazamiento B", ta="center")
                                    ], span=4, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                    dmc.GridCol([
                                        dcc.Graph(id='grafico_incli_3_total', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Desplazamientos Totales", ta="center")
                                    ], span=4, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                ])
                            ]),
                            value="grafico3"
                        )
                    ], value="grafico1"),
                  className="id-graph-card"),
                    span=9  # Ocupa el 70% de la fila
                ),

                dmc.GridCol(
                  html.Div([
                    dmc.Title("Fechas", order=4, style={"color": "var(--id-text-primary)"}),
                    dmc.Space(h=20),
                    dmc.MultiSelect(
                        id='fechas_multiselect',
                        data=[],
                        placeholder="Selecciona opciones",
                        searchable=True
                    ),
                    dmc.Space(h=10),
                    html.Div(
                        dcc.Slider(
                            id='slider_fechas',
                            min=0,
                            max=1,
                            value=1,
                            marks={},
                            step=None,
                            tooltip={"placement": "bottom", "always_visible": False},
                            className='slider-timeline-fechas'
                        ),
                        style={"paddingBottom": "38px"}
                    ),
                    html.Div(id='slider_fecha_tooltip', style={'marginTop': '10px', 'fontWeight': 'bold'}),
                  ], className="id-graph-card"),
                span=3)  # Ocupa el 30% de la fila
            ], style={"width": "100%"}),

            dmc.Divider(style={"marginTop": "40px", "marginBottom": "20px"}),
            # Serie temporal (40%) + Polar (40%) + Controles (20%)
            html.Div([
                # Serie temporal
                html.Div(
                    dcc.Graph(id='grafico_temporal', config={'responsive': True}, style={'height': '100%'}),
                    className='id-graph-card',
                    style={'width': '40%', 'height': '600px', 'flexShrink': '0'}
                ),
                # Gráfico polar
                html.Div([
                    dcc.Graph(id='grafico_polar', config={'responsive': True, 'scrollZoom': True}, style={'height': '100%'}),
                    dmc.Button("🔍 Debug Polar", id="btn-debug-polar", variant="subtle", size="xs",
                              style={"position": "absolute", "top": "5px", "right": "5px", "zIndex": 10,
                                     "opacity": 0.7}),
                    ],
                    className='id-graph-card',
                    style={'width': '40%', 'height': '600px', 'flexShrink': '0', 'position': 'relative'}
                ),
                # Controles
                html.Div([
                    dmc.MultiSelect(
                        id='profundidades_multiselect',
                        label="Profundidades",
                        data=[],
                        placeholder="Selecciona profundidades"
                    ),
                    dmc.Space(h=15),
                    dmc.MultiSelect(
                        id='desplazamientos_multiselect',
                        label="Desplazamientos",
                        data=[
                            {"value": "desp_a", "label": "desp_a"},
                            {"value": "desp_b", "label": "desp_b"},
                            {"value": "desp_total", "label": "desp_total"}
                        ],
                        value=["desp_a"],
                        placeholder="Selecciona tipo"
                    ),
                ], className='id-graph-card',
                   style={'width': '20%', 'flexShrink': '0', 'paddingLeft': '10px', 'paddingTop': '10px'}),
            ], style={'display': 'flex', 'width': '100%', 'gap': '1rem'}),

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

                    # Parámetros de configuración del gráfico
                    dmc.Space(h=20),
                    dmc.Divider(label="Configuración del gráfico"),
                    dmc.Space(h=10),

                    # Vista Previa deshabilitada: era un mini-motor ReportLab; los scripts HTML de Maketator
                    # tienen otro contrato (punto de entrada, datos y salida). Reactivable en el futuro via render del motor.
                    # dmc.Button(
                    #     "Generar Vista Previa",
                    #     id="btn-generar-preview",
                    #     variant="outline",
                    #     color="blue",
                    #     fullWidth=True,
                    #     leftSection=DashIconify(icon="mdi:eye-outline")
                    # ),
                    # dmc.Space(h=10),

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
                            dmc.Button("Cancelar", color="gray", id="btn-cancelar-informe"),
                            dcc.Loading(
                                id="loading-generar-pdf",
                                type="circle",
                                color="var(--id-primary)",
                                children=[
                                    dmc.Button("Generar PDF", id="btn-generar-informe-pdf",
                                               leftSection=DashIconify(icon="mdi:file-pdf-box")),
                                    dcc.Download(id="descargar-informe-pdf")
                                ]
                            )
                        ],
                        mt=20
                    )
                ]
            ),

            # Componente de descarga
            dcc.Download(id="descargar-vista-previa-html"),
            dcc.Download(id="descargar-debug-polar"),
            # componente dummy para abrir en otra pestaña los resultados
            html.Div(id="dummy-output", style={"display": "none"}),
            # Añade este componente al layout
            html.Div(id="debug-output-dummy", style={"display": "none"})
            # fin borrar
    ])


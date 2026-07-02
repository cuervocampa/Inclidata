# pages/correcciones_layout.py
# Layout de la página Correcciones. Separado de la lógica de callbacks.

from dash import html, dcc
import dash_mantine_components as dmc
from dash_ag_grid import AgGrid
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify

def layout():
    return html.Div([
        html.Div(style={'height': '1.5rem'}),

        # ============================================
        # SECCIÓN 1: CARGA DE ARCHIVO + INFO
        # ============================================
        html.Div(
            dmc.Grid([
                # Upload
                dmc.GridCol(
                    dcc.Upload(
                        id='archivo-uploader',
                        multiple=False,
                        accept='.json',
                        children=html.Div([
                            DashIconify(icon="lucide:upload", width=18, className="id-upload-icon"),
                            html.Span("Arrastra o selecciona archivo .json", className="id-upload-text")
                        ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'gap': '0.5rem', 'height': '100%'}),
                        className='id-upload-area',
                        style={'width': '100%', 'cursor': 'pointer'}
                    ),
                    span=4
                ),
                # Info archivo
                dmc.GridCol(
                    html.Div(id='informacion-archivo', style={'width': '100%', 'display': 'flex', 'alignItems': 'center', 'height': '100%'}),
                    span=4
                ),
                # Selector de campaña
                dmc.GridCol(
                    dmc.Group([
                        dmc.Text('Campaña a Graficar:', fw=600, size="sm", style={"color": "var(--id-text-primary)"}),
                        dmc.Select(
                            id='camp_a_graficar',
                            placeholder='Selecciona una fecha',
                            clearable=True,
                            data=[],
                            style={'minWidth': '200px'}
                        )
                    ], gap="md", style={'width': '100%', 'alignItems': 'center'}),
                    span=4
                )
            ], style={'width': '100%'}),
            className='id-card',
            style={'padding': '1rem', 'marginBottom': '1rem'}
        ),

        # Stores
        dcc.Store(id='corregir-tubo', storage_type='memory'),
        dcc.Store(id='corregir_archivo', storage_type='memory'),
        dcc.Store(id="json_spikes", storage_type='memory'),
        dcc.Store(id="json_bias", storage_type='memory'),
        dcc.Store(id='tabla_inicial', data={}, storage_type='memory'),
        dcc.Store(id='log_cambios', data={}, storage_type='memory'),
        dcc.Store(id='bias-table-change-flag', data=False, storage_type='memory'),
        dcc.Store(id="error-store", data={"opened": False, "message": ""}),

        # ============================================
        # SECCIÓN 2: TABLA DE CAMPAÑAS + LOG
        # ============================================
        html.Div(
            dmc.Grid([
                dmc.GridCol(
                    AgGrid(
                        id='tabla-json',
                        className='ag-theme-quartz',
                        style={'height': '200px', 'width': '100%', 'margin': '0 auto'},
                        columnDefs=[
                            {'headerName': 'Fecha', 'field': 'Fecha', 'editable': False, 'resizable': True},
                            {'headerName': 'Referencia', 'field': 'Referencia', 'editable': True,
                             'cellEditor': 'agSelectCellEditor', 'cellEditorParams': {'values': [True, False]}, 'resizable': True},
                            {'headerName': 'Activa', 'field': 'Activa', 'editable': True,
                             'cellEditor': 'agSelectCellEditor', 'cellEditorParams': {'values': [True, False]}, 'resizable': True},
                            {'headerName': 'Cuarentena', 'field': 'Cuarentena', 'editable': True,
                             'cellEditor': 'agSelectCellEditor', 'cellEditorParams': {'values': [True, False]}, 'resizable': True},
                            {'headerName': 'Correc Spike', 'field': 'spike', 'editable': False, 'resizable': True},
                            {'headerName': 'Correc Bias', 'field': 'bias', 'editable': False, 'resizable': True},
                            {'headerName': 'Limpiar', 'field': 'Limpiar', 'editable': True, 'cellEditor': 'agCheckboxCellEditor', 'resizable': True},
                        ],
                        defaultColDef={
                            'flex': 1,
                            'minWidth': 100,
                            'resizable': True,
                            'wrapHeaderText': True,
                            'autoSizeAllColumns': True
                        },
                        rowData=[],
                        columnSize='responsiveSizeToFit'
                    ),
                    span=8
                ),
                dmc.GridCol(
                    children=[
                        html.Div(
                            id='log-cambios',
                            className='id-card',
                            style={'height': '200px', 'overflowY': 'auto', 'padding': '0.75rem', 'fontSize': '0.875rem'}
                        ),
                        dmc.Group(
                            children=[
                                dmc.Button(
                                    "Guardar Tabla", id='guardar_tabla',
                                    leftSection=DashIconify(icon="lucide:save", width=14),
                                    variant='outline', color='green',
                                    className="id-btn id-btn-outline",
                                ),
                                dmc.Button(
                                    "Configuración", id="correc-open-drawer-1", n_clicks=None,
                                    leftSection=DashIconify(icon="lucide:settings", width=14),
                                    variant='outline', color='blue',
                                    className="id-btn id-btn-outline",
                                )
                            ],
                            style={'marginTop': '0.75rem', 'width': '100%'},
                            grow=True
                        ),
                        dmc.Modal(
                            id="guardar-cambios-tabla",
                            title="Confirmación",
                            children=[
                                html.Div(id="guardar-mensaje-tabla"),
                                dmc.Button("Cerrar", id="cerrar-cambios-tabla", variant="outline",
                                           className="id-btn id-btn-outline", style={"marginTop": "10px"})
                            ],
                            centered=True,
                            size="md",
                            opened=False
                        ),
                    ],
                    span=4
                )
            ], style={'width': '100%'}),
            className='id-card',
            style={'padding': '1rem', 'marginBottom': '1rem'}
        ),

        dmc.Space(h=20),

        # ============================================
        # SECCIÓN 3: GRÁFICOS PRINCIPALES (Tabs)
        # ============================================
        html.Div(
            dmc.Grid([
                dmc.GridCol(
                    dmc.Tabs([
                        dmc.TabsList([
                            dmc.TabsTab("Desplazamientos", value="corr_grafico1",
                                        style={'fontWeight': '600', 'fontSize': '0.875rem'}),
                            dmc.TabsTab("Incrementales", value="corr_grafico2",
                                        style={'fontWeight': '600', 'fontSize': '0.875rem'}),
                            dmc.TabsTab("Compuestos", value="corr_grafico3",
                                        style={'fontWeight': '600', 'fontSize': '0.875rem'})
                        ]),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.GridCol([
                                        dcc.Graph(id='corr_grafico_incli_1_a', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Desplazamiento A (mm)", ta="center", c="dimmed", size="sm")
                                    ], span=6, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                    dmc.GridCol([
                                        dcc.Graph(id='corr_grafico_incli_1_b', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Desplazamiento B (mm)", ta="center", c="dimmed", size="sm")
                                    ], span=6, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                ])
                            ]),
                            value="corr_grafico1"
                        ),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.GridCol([
                                        dcc.Graph(id='corr_grafico_incli_2_a', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Incremental A (mm)", ta="center", c="dimmed", size="sm")
                                    ], span=6, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                    dmc.GridCol([
                                        dcc.Graph(id='corr_grafico_incli_2_b', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Incremental B (mm)", ta="center", c="dimmed", size="sm")
                                    ], span=6, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                ])
                            ]),
                            value="corr_grafico2"
                        ),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.GridCol([
                                        dcc.Graph(id='corr_grafico_incli_3_a', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Desplazamiento A", ta="center", c="dimmed", size="sm")
                                    ], span=4, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                    dmc.GridCol([
                                        dcc.Graph(id='corr_grafico_incli_3_b', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Desplazamiento B", ta="center", c="dimmed", size="sm")
                                    ], span=4, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                    dmc.GridCol([
                                        dcc.Graph(id='corr_grafico_incli_3_total', config={'responsive': True}, style={'height': '800px'}),
                                        dmc.Text("Desplazamientos (mm)", ta="center", c="dimmed", size="sm")
                                    ], span=4, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                                ])
                            ]),
                            value="corr_grafico3"
                        )
                    ], value="corr_grafico1"),
                    span=12
                )
            ], style={"width": "100%"}),
            className='id-graph-card',
            style={'marginBottom': '1.5rem'}
        ),

        # Drawer configuración gráficos
        dmc.Drawer(
            title=dmc.Text("Configuración gráficos", fw="bold", size="lg"),
            id="correc-drawer-1",
            padding="md",
            size="sm",
            children=[
                dmc.Text("Altura de gráficos", fw="bold", size="sm", c="dimmed", style={"marginBottom": "10px"}),
                dmc.Slider(
                    label="Altura de los gráficos (px)",
                    id="corr_alto_graficos_slider_grafico1",
                    min=400, max=1000, step=100, value=800,
                    marks=[
                        {"value": 400, "label": "400"}, {"value": 500, "label": "500"},
                        {"value": 600, "label": "600"}, {"value": 700, "label": "700"},
                        {"value": 800, "label": "800"}, {"value": 900, "label": "900"},
                        {"value": 1000, "label": "1000"},
                    ],
                    style={"marginBottom": "30px"}
                ),
                dmc.Divider(style={"marginTop": "15px", "marginBottom": "20px"}),
                dmc.Text("Orden del eje vertical", fw="bold", size="sm", c="dimmed", style={"marginBottom": "10px"}),
                dmc.SegmentedControl(
                    id="correc_orden_eje", value="descendente",
                    data=[{"value": "ascendente", "label": "↑ Ascendente"}, {"value": "descendente", "label": "↓ Descendente"}],
                    fullWidth=True, color="blue", radius="xl", size="md", style={"marginBottom": "20px"}
                ),
                dmc.Divider(style={"marginTop": "15px", "marginBottom": "20px"}),
                dmc.Text("Estilo de colores", fw="bold", size="sm", c="dimmed", style={"marginBottom": "10px"}),
                dmc.SegmentedControl(
                    id="correcciones_color_grafico1", value="monocromo",
                    data=[{"value": "monocromo", "label": "Monocromo"}, {"value": "multicromo", "label": "Multicromo"}],
                    fullWidth=True, color="blue", radius="xl", size="md", style={"marginBottom": "20px"}
                ),
                dmc.Text("Campañas previas", fw="bold", size="sm", c="dimmed", style={"marginBottom": "10px"}),
                dmc.Group(
                    children=[dmc.Text("Número a mostrar"), dmc.NumberInput(id="correc_num_camp_previas_grafico1", value=10, min=0, max=1000, step=1, disabled=False, style={"width": "100px"})],
                    style={"width": "100%", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "20px"}
                ),
                dmc.Divider(style={"marginTop": "10px", "marginBottom": "20px"}),
                dmc.Text("Escala gráficos Desplazamiento", fw="bold", size="sm", c="dimmed", style={"marginBottom": "10px"}),
                dmc.SegmentedControl(
                    id="correc_escala_graficos_desplazamiento", value="manual",
                    data=[{"value": "automatica", "label": "Automática"}, {"value": "manual", "label": "Manual"}],
                    fullWidth=True, color="blue", radius="xl", size="sm", style={"marginBottom": "15px"}
                ),
                dmc.Group(
                    [dmc.Text("Max", style={"width": "30px"}), dmc.NumberInput(id="correc_valor_positivo_desplazamiento", value=20, min=-1000, max=1000, step=5, disabled=True, style={"flex": 1}),
                     dmc.Text("Min", style={"width": "30px", "marginLeft": "10px"}), dmc.NumberInput(id="correc_valor_negativo_desplazamiento", value=-20, min=-1000, max=1000, step=5, disabled=True, style={"flex": 1})],
                    ta="center", gap="xs", style={"width": "100%", "marginBottom": "20px"}
                ),
                dmc.Text("Escala gráficos Incremento", fw="bold", size="sm", c="dimmed", style={"marginBottom": "10px"}),
                dmc.SegmentedControl(
                    id="correc_escala_graficos_incremento", value="manual",
                    data=[{"value": "automatica", "label": "Automática"}, {"value": "manual", "label": "Manual"}],
                    fullWidth=True, color="blue", radius="xl", size="sm", style={"marginBottom": "15px"}
                ),
                dmc.Group(
                    [dmc.Text("Max", style={"width": "30px"}), dmc.NumberInput(id="correc_valor_positivo_incremento", value=1, min=-1000, max=1000, step=1, disabled=True, style={"flex": 1}),
                     dmc.Text("Min", style={"width": "30px", "marginLeft": "10px"}), dmc.NumberInput(id="correc_valor_negativo_incremento", value=-1, min=-1000, max=1000, step=1, disabled=True, style={"flex": 1})],
                    ta="center", gap="xs", style={"width": "100%", "marginBottom": "30px"}
                ),
                dmc.Divider(style={"marginTop": "10px", "marginBottom": "20px"}),
                dmc.Button("Cerrar", id="close-correc-drawer-1", variant="outline", fullWidth=True, className="id-btn id-btn-outline")
            ],
            opened=False,
            position="right"
        ),

        dmc.Space(h=20),

        # ============================================
        # SECCIÓN 4: CORRECCIÓN DE SPIKES
        # ============================================
        dmc.Divider(label="Sección: Corrección de Spikes", labelPosition="center", color="gray", variant="dashed",
                    style={"marginBottom": "1.5rem"}),

        dmc.Grid([
            # Gráficos spikes (70%)
            dmc.GridCol(
                html.Div(
                    dmc.Grid([
                        dmc.GridCol([
                            dcc.Graph(id='corr_graf_spike_a', config={'responsive': True}, style={'height': '800px'}),
                            dmc.Text("Incr CheckSum A", ta="center", c="dimmed", size="sm")
                        ], span=3, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                        dmc.GridCol([
                            dcc.Graph(id='corr_graf_spike_b', config={'responsive': True}, style={'height': '800px'}),
                            dmc.Text("Incr CheckSum B", ta="center", c="dimmed", size="sm")
                        ], span=3, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                        dmc.GridCol([
                            dcc.Graph(id='corr_graf_stats_a', config={'responsive': True}, style={'height': '800px'}),
                            dmc.Text("Estadística seleccionada", ta="center", c="dimmed", size="sm")
                        ], span=6, style={'padding': '0', 'margin': '0', 'overflow': 'visible'})
                    ], style={'width': '100%', 'display': 'flex', 'flexWrap': 'nowrap'}),
                    className='id-graph-card'
                ),
                span=8, style={'padding': '0', 'margin': '0'}
            ),

            # Panel spikes (30%)
            dmc.GridCol(
                html.Div([
                    dmc.Title("Corrección de spikes", order=3, ta="center",
                              style={"color": "var(--id-text-primary)", "marginBottom": "1rem"}),
                    dmc.Group([
                        dmc.Text("Campañas anteriores", fw=500, size="sm"),
                        dmc.Select(
                            id='n_spikes', value='5', clearable=False,
                            data=[{'value': 'max', 'label': 'max'}] + [{'value': str(i), 'label': str(i)} for i in range(1, 21)],
                            style={'width': '140px'}
                        ),
                    ], gap="md", style={'width': '100%', 'marginBottom': '0.75rem'}, justify="space-between"),

                    dmc.Group([
                        dmc.Text("Estadísticas Spikes", fw=500, size="sm"),
                        dmc.Select(
                            id='estadisticas_spikes', value='incr_checksum_a', clearable=False,
                            data=[
                                {'value': 'a0', 'label': 'a0'}, {'value': 'a180', 'label': 'a180'},
                                {'value': 'b0', 'label': 'b0'}, {'value': 'b180', 'label': 'b180'},
                                {'value': 'incr_checksum_a', 'label': 'incr_checksum_a'}, {'value': 'incr_checksum_b', 'label': 'incr_checksum_b'},
                                {'value': 'incr_dev_a', 'label': 'incr_dev_a'}, {'value': 'incr_dev_b', 'label': 'incr_dev_b'}
                            ],
                            style={'width': '140px'}
                        )
                    ], gap="md", style={'width': '100%', 'marginBottom': '0.75rem'}, justify="space-between"),

                    dmc.Group([
                        dmc.Text("Criterio corrección", fw=500, size="sm"),
                        dmc.Select(
                            id='spikes_criterio', value='media', clearable=False,
                            data=[{'value': 'media', 'label': 'media'}, {'value': 'mediana', 'label': 'mediana'}, {'value': 'moda', 'label': 'moda'}],
                            style={'width': '140px'}
                        )
                    ], gap="md", style={'width': '100%', 'marginBottom': '0.75rem'}, justify="space-between"),

                    dmc.Group(
                        children=[
                            dmc.MultiSelect(id='spike_profundidad', placeholder='Selecciona profundidad', data=[], style={'flex': '1'}),
                            dmc.Button(
                                "Temporal Spike", id='temporal_spike',
                                leftSection=DashIconify(icon="lucide:clock", width=14),
                                variant='outline', color='blue',
                                className="id-btn id-btn-outline",
                            )
                        ],
                        style={'marginBottom': '1rem', 'width': '100%'},
                        justify="space-between", gap="md"
                    ),
                    AgGrid(
                        id='spikes-table',
                        className='ag-theme-quartz',
                        rowData=[],
                        columnDefs=[
                            {'headerName': 'Selec', 'field': 'Corregir', 'cellRenderer': 'agCheckboxCellRenderer'},
                            {'headerName': 'Prof', 'field': 'Profundidad'},
                        ],
                        defaultColDef={'flex': 1, 'minWidth': 100, 'resizable': True, 'wrapHeaderText': True, 'autoSizeAllColumns': True},
                        columnSize='responsiveSizeToFit'
                    ),
                    dmc.Modal(
                        id="temporal-spike-modal",
                        title="Detalles del Histórico Temporal",
                        children=[
                            dmc.Group([
                                dmc.Text("Elegir variables", fw=600, size="sm"),
                                dmc.MultiSelect(
                                    id='temporal-spike-variables',
                                    data=[
                                        {"value": "a0", "label": "a0"}, {"value": "a180", "label": "a180"},
                                        {"value": "b0", "label": "b0"}, {"value": "b180", "label": "b180"},
                                        {"value": "checksum_a", "label": "checksum_a"}, {"value": "checksum_b", "label": "checksum_b"},
                                        {"value": "incr_checksum_a", "label": "incr_checksum_a"}, {"value": "incr_checksum_b", "label": "incr_checksum_b"},
                                    ],
                                    value=["incr_checksum_a", "incr_checksum_b"],
                                    style={"flex": "1", "minWidth": "200px"}
                                ),
                            ], ta="center", style={"marginBottom": "20px"}),
                            dcc.Graph(id='temporal-spike-graph', config={'responsive': False}, style={'height': '600px'})
                        ],
                        opened=False, size="xl", centered=True
                    ),
                    dmc.Modal(
                        id="error-modal", title="Error",
                        children=[html.Div(id="error-message")],
                        centered=True, size="md", opened=False,
                    )
                ], className='id-card', style={'padding': '1rem'}),
                span=4, style={'padding': '0', 'margin': '0'}
            ),
        ], style={'width': '100%', 'display': 'flex', 'flexWrap': 'nowrap', 'marginBottom': '1.5rem'}),

        # ============================================
        # SECCIÓN 5: CORRECCIÓN DE BIAS
        # ============================================
        dmc.Divider(label="Sección: Corrección de Bias", labelPosition="center", color="gray", variant="dashed",
                    style={"marginBottom": "1.5rem"}),

        dmc.Grid([
            # Gráficos bias (70%)
            dmc.GridCol(
                html.Div(
                    dmc.Grid([
                        dmc.GridCol(dcc.Graph(id='corr_graf_bias_a', config={'responsive': True}, style={'height': '800px'}), span=4, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                        dmc.GridCol(dcc.Graph(id='corr_estad_bias_a', config={'responsive': True}, style={'height': '800px'}), span=2, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                        dmc.GridCol(dcc.Graph(id='corr_graf_bias_b', config={'responsive': True}, style={'height': '800px'}), span=4, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                        dmc.GridCol(dcc.Graph(id='corr_estad_bias_b', config={'responsive': True}, style={'height': '800px'}), span=2, style={'padding': '0', 'margin': '0', 'overflow': 'visible'}),
                    ], style={'width': '100%', 'display': 'flex', 'flexWrap': 'nowrap'}),
                    className='id-graph-card'
                ),
                span=8, style={'padding': '0', 'margin': '0'}
            ),

            # Panel bias (30%)
            dmc.GridCol(
                html.Div([
                    dmc.Title("Corrección de bias", order=3, ta="center",
                              style={"color": "var(--id-text-primary)", "marginBottom": "1rem"}),

                    dmc.Group(
                        children=[
                            dmc.Text("Evolución temporal", fw=500, size="sm"),
                            dmc.Button(
                                "Análisis Bias", id='boton_ventana_modal_bias',
                                leftSection=DashIconify(icon="lucide:line-chart", width=14),
                                variant='outline', color='blue',
                                className="id-btn id-btn-outline",
                            )
                        ],
                        gap="md", style={'width': '100%', 'marginBottom': '0.75rem'}, justify="space-between"
                    ),
                    dmc.Group(
                        children=[
                            dmc.Text("Evolución temporal std", fw=500, size="sm"),
                            dmc.Button(
                                "Evolución std", id='boton_ventana_modal_bias_1',
                                leftSection=DashIconify(icon="lucide:trending-up", width=14),
                                variant='outline', color='blue',
                                className="id-btn id-btn-outline",
                            )
                        ],
                        gap="md", style={'width': '100%', 'marginBottom': '0.75rem'}, justify="space-between"
                    ),
                    dmc.Group(
                        children=[
                            dmc.Text("Empotramiento teórico", fw=500, size="sm"),
                            dmc.NumberInput(id='empotramiento', value=5, min=1, max=99, step=1, style={"width": "140px"})
                        ],
                        gap="md", style={'width': '100%', 'marginBottom': '0.75rem'}, justify="space-between"
                    ),

                    # Modales
                    dmc.Modal(
                        id="ventana_modal_bias", title="Búsqueda de parámetro",
                        children=[
                            dmc.Group([
                                dmc.Text("Elegir variables", fw=600, size="sm"),
                                dmc.Select(
                                    id='temporal-bias-variables',
                                    data=[
                                        {"value": "checksum_a", "label": "checksum_a"}, {"value": "checksum_b", "label": "checksum_b"},
                                        {"value": "incr_dev_a", "label": "incr_dev_a"}, {"value": "incr_dev_b", "label": "incr_dev_b"},
                                    ],
                                    value="checksum_a",
                                    style={"flex": "1", "minWidth": "200px"}
                                ),
                            ], ta="center", style={"marginBottom": "20px"}),
                            dcc.Graph(id='modal_bias_graph_1', config={'responsive': False}, style={'height': '600px'}),
                        ],
                        opened=False, size="xl", centered=True
                    ),
                    dmc.Modal(
                        id="ventana_modal_bias_1", title="Búsqueda de parámetro",
                        children=[dcc.Graph(id='modal_bias_graph_2', config={'responsive': False}, style={'height': '600px'})],
                        opened=False, size="xl", centered=True
                    ),

                    dmc.Space(h=15),

                    # Tabla bias
                    AgGrid(
                        id='bias-table',
                        className='ag-theme-quartz',
                        rowData=[
                            {'Correccion': 'Bias_1_A', 'Selec': False, 'Prof_inf': 0, 'Prof_sup': 0, 'Delta': ''},
                            {'Correccion': 'Bias_1_B', 'Selec': False, 'Prof_inf': 0, 'Prof_sup': 0, 'Delta': ''},
                            {'Correccion': 'Bias_2_A', 'Selec': False, 'Prof_inf': 0, 'Prof_sup': 0, 'Delta': ''},
                            {'Correccion': 'Bias_2_B', 'Selec': False, 'Prof_inf': 0, 'Prof_sup': 0, 'Delta': ''}
                        ],
                        columnDefs=[
                            {'headerName': 'Corrección', 'field': 'Correccion', 'editable': False},
                            {'headerName': 'Selec.', 'field': 'Selec', 'editable': True, 'cellRenderer': 'agCheckboxCellRenderer'},
                            {'headerName': 'Prof. inf.', 'field': 'Prof_inf', 'editable': True, 'cellEditor': 'agTextCellEditor'},
                            {'headerName': 'Prof. sup.', 'field': 'Prof_sup', 'editable': True, 'cellEditor': 'agTextCellEditor'},
                            {'headerName': 'Delta', 'field': 'Delta', 'editable': True, 'cellEditor': 'agTextCellEditor'},
                        ],
                        defaultColDef={'flex': 1, 'minWidth': 100, 'resizable': True, 'wrapHeaderText': True, 'autoSizeAllColumns': True},
                        columnSize='responsiveSizeToFit',
                        dashGridOptions={'getRowHeight': 'function(params) { return 40; }'},
                        style={'width': '100%', 'height': '220px'}
                    ),

                    dmc.Space(h=15),

                    dmc.Group(
                        children=[
                            dmc.Text("Sugerir correcciones", fw=500, size="sm"),
                            dmc.Button(
                                "Sugerir", id="sugerir_bias",
                                leftSection=DashIconify(icon="lucide:lightbulb", width=14),
                                variant="outline", color="blue",
                                className="id-btn id-btn-outline",
                            )
                        ],
                        gap="md", style={'width': '100%', 'marginBottom': '0.75rem'}, justify="space-between"
                    ),

                    # Acción principal: Guardar
                    html.Div(
                        dmc.Group(
                            children=[
                                dmc.Text("Aplicar cambios Spikes y Bias", fw=600, size="sm",
                                         style={"color": "var(--id-text-primary)"}),
                                dmc.Button(
                                    "Guardar cambios", id="save_json",
                                    leftSection=DashIconify(icon="lucide:check-circle", width=14),
                                    className="id-btn", color="blue",
                                ),
                                dmc.Modal(
                                    id="guardar-modal", title="Confirmación",
                                    children=[
                                        html.Div(id="guardar-mensaje"),
                                        dmc.Button("Cerrar", id="cerrar-guardar-modal", variant="outline",
                                                   className="id-btn id-btn-outline", style={"marginTop": "10px"})
                                    ],
                                    centered=True, size="md", opened=False
                                ),
                            ],
                            gap="md", justify="space-between",
                            style={'width': '100%'}
                        ),
                        className='id-card',
                        style={'padding': '0.75rem', 'marginTop': '0.5rem'}
                    ),

                ], className='id-card', style={'padding': '1rem'}),
                span=4, style={'padding': '0', 'margin': '0'}
            ),
        ], style={'width': '100%', 'display': 'flex', 'flexWrap': 'nowrap', 'marginBottom': '1.5rem'}),

    ])


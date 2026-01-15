from dash import html, dcc, callback_context
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
import base64, json
import dash
from icecream import ic

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
                            dmc.Button("Configuración", id="open-config-drawer", n_clicks=None, fullWidth=True)
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
                    html.P("Configuración del patrón aquí."),
                    dmc.NumberInput(
                        label="Total campañas a mostrar",
                        id="total_camp",
                        value=30,
                        min=1
                    ),
                    dmc.NumberInput(
                        label="Pintar los últimos días",
                        id="ultimas_camp",
                        value=10,
                        min=1
                    ),
                    dmc.NumberInput(
                        label="Campañas mensuales previas",
                        id="camp_mes",
                        value=1,
                        min=0
                    ),
                    html.Div(style={'height': '20px'}),  # Espacio en blanco entre el último input y el botón
                    dmc.Button("Cerrar", id="close-patron-drawer", n_clicks=None)
                ],
                opened=False,
                justify="flex-end"
            ),
            dmc.Drawer(
                title="Configuración General",
                id="drawer-config",
                children=[
                    html.P("Configuración general aquí."),
                    dmc.Button("Cerrar", id="close-config-drawer", n_clicks=None)
                ],
                opened=False,
                justify="flex-end"
            ),
            dmc.Divider(style={"marginTop": "20px", "marginBottom": "20px"}),
            dmc.Grid([
                dmc.Col(
                    dmc.Tabs([
                        dmc.TabsList([
                            dmc.Tab("Gráfico 1", value="grafico1"),
                            dmc.Tab("Gráfico 2", value="grafico2"),
                            dmc.Tab("Gráfico 3", value="grafico3")
                        ]),
                        dmc.TabsPanel(
                            dcc.Graph(id='grafico_incli_1'),
                            value="grafico1"
                        ),
                        dmc.TabsPanel(
                            dcc.Graph(id='grafico_incli_2'),
                            value="grafico2"
                        ),
                        dmc.TabsPanel(
                            dcc.Graph(id='grafico_incli_3'),
                            value="grafico3"
                        )
                    ], value="grafico1"),
                    span=9  # Ocupa el 70% de la fila
                ),
                dmc.Col([
                    dmc.Title("Fechas", order=4),
                    dmc.MultiSelect(
                        id='fechas_multiselect',
                        data=["Opción 1", "Opción 2", "Opción 3"],
                        placeholder="Selecciona opciones"
                    )
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
                    dmc.MultiSelect(
                        id='profundidades_multiselect',
                        data=["Profundidad 1", "Profundidad 2", "Profundidad 3"],
                        placeholder="Selecciona profundidades"
                    )
                ], span=3)  # Ocupa el 30% de la fila
            ], style={"width": "100%"}),
        ]),
        inherit=True  # To inherit default Mantine styles
    )

# Registra los callbacks en lugar de definir un nuevo Dash app
def register_callbacks(app):
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
        [Output("info-hovercard", "children"), Output("graficar-tubo", "data")],
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
                }

                # Recorrer las claves del diccionario original y guardo sólo lo que interesa
                for clave, valor in data.items():
                    if clave != "info" and "calc" in valor:
                        nuevo_diccionario[clave] = {
                            "calc": [
                                {
                                    "index": item["index"],
                                    "cota_abs": item["cota_abs"],
                                    "incr_dev_a": item["desp_a"],
                                    "incr_dev_b": item["desp_a"],
                                    "desp_a": item["desp_a"],
                                    "desp_b": item["desp_b"]
                                }
                                for item in valor["calc"] if isinstance(item, dict) and "index" in item
                            ]
                        }
                #ic(nuevo_diccionario)

                return f"\t{filename}", nuevo_diccionario
            except Exception as e:
                ic(e)  # Añadido para mostrar el error en caso de fallo
                return f"\t{filename}", None
        return "", None

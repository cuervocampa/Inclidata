from dash import Dash, html, dcc, callback_context
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc

app = Dash(__name__)

app.layout = dmc.MantineProvider(
    children=html.Div([
        html.Div(style={'height': '50px'}),  # Espacio al comienzo de la página
        dmc.Grid([
            dmc.Col(
                dmc.Card(
                    dcc.Graph(id='mapa'),
                    shadow='sm', radius='md'
                ), span=6
            ),
            dmc.Col([
                dmc.Grid([
                    dmc.Col(
                        dcc.Upload(id='uploader', children=html.Button('Seleccionar Sensores', n_clicks=0)),
                        span=6,
                        style={'marginBottom': '20px'}  # Espaciamiento entre uploader y el siguiente componente
                    ),
                    dmc.Col(
                        dmc.HoverCard(
                            children=html.Div(
                                "Información del archivo subido",
                                id="info-hovercard"
                            ),
                            withArrow=True
                        ),
                        span=6,
                        style={'marginBottom': '20px'}  # Espaciamiento entre HoverCard y el siguiente componente
                    )
                ]),
                dmc.Group(
                    [
                        dmc.Button("Patrón", id="open-patron-drawer", n_clicks=0, fullWidth=True),
                        dmc.Button("Configuración", id="open-config-drawer", n_clicks=0, fullWidth=True)
                    ],
                    style={'display': 'flex', 'flexDirection': 'column'},
                    spacing="lg"  # Espaciamiento entre botones
                ),
            ], span=6)
        ]),
        dmc.Drawer(
            title="Configurar Patrón",
            id="drawer-patron",
            children=[
                html.P("Configuración del patrón aquí."),
                dmc.Button("Cerrar", id="close-patron-drawer", n_clicks=0)
            ],
            opened=False,
            position="right"
        ),
        dmc.Drawer(
            title="Configuración General",
            id="drawer-config",
            children=[
                html.P("Configuración general aquí."),
                dmc.Button("Cerrar", id="close-config-drawer", n_clicks=0)
            ],
            opened=False,
            position="right"
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

if __name__ == "__main__":
    app.run_server(debug=True)

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

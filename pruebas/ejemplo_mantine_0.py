from dash import Dash, html, dcc, callback_context
from dash.dependencies import Input, Output
import dash_mantine_components as dmc

app = Dash(__name__)

app.layout = dmc.MantineProvider(
    children=html.Div([
        dmc.Grid([
            dmc.Col(
                dmc.Card(
                    dcc.Graph(id='mapa'),
                    shadow='sm', radius='md'
                ), span=6
            ),
            dmc.Col([
                dmc.Group(
                    [
                        dcc.Upload(id='uploader', children=html.Button('Seleccionar Sensores')),
                        dmc.HoverCard(
                            children=dmc.Card(
                                "Información del archivo subido",
                                id="info-hovercard",
                                shadow='sm'
                            ),
                            withArrow=True
                        ),
                        dmc.Button("Patrón", id="open-patron-drawer"),
                        dmc.Button("Configuración", id="open-config-drawer")
                    ]
                )
            ], span=3)
        ]),
        dmc.Drawer(
            title="Configurar Patrón",
            id="drawer-patron",
            children=[
                html.P("Configuración del patrón aquí."),
                dmc.Button("Cerrar", id="close-patron-drawer")
            ],
            opened=False,
            position="right"
        ),
        dmc.Drawer(
            title="Configuración General",
            id="drawer-config",
            children=[
                html.P("Configuración general aquí."),
                dmc.Button("Cerrar", id="close-config-drawer")
            ],
            opened=False,
            position="right"
        ),
        dmc.Tabs([
            dmc.Tab(value="graficos", children=[dcc.Graph(id="graficos_inclis")]),
            dmc.Tab(value="fechas", children=[html.Div(id="fechas")])
        ],
        id="tabs-graficos",
        value="graficos"
    ),
        dcc.Graph(id="temporal"),
        html.Div("Profundidades disponibles", id="profundidad")
    ])
)

@app.callback(
    Output("drawer-patron", "opened"),
    [Input("open-patron-drawer", "n_clicks"), Input("close-patron-drawer", "n_clicks")]
)
def toggle_patron_drawer(open_clicks, close_clicks):
    if open_clicks or close_clicks:
        ctx = callback_context
        if not ctx.triggered:
            return False
        else:
            triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
            return triggered_id == "open-patron-drawer"
    return False

@app.callback(
    Output("drawer-config", "opened"),
    [Input("open-config-drawer", "n_clicks"), Input("close-config-drawer", "n_clicks")]
)
def toggle_config_drawer(open_clicks, close_clicks):
    if open_clicks or close_clicks:
        ctx = callback_context
        if not ctx.triggered:
            return False
        else:
            triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
            return triggered_id == "open-config-drawer"
    return False

if __name__ == "__main__":
    app.run_server(debug=True)

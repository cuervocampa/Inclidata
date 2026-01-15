from dash import Dash, html, callback_context
from dash.dependencies import Input, Output
import dash_mantine_components as dmc

app = Dash(__name__)

app.layout = dmc.MantineProvider(
    children=html.Div([
        dmc.Button("Open Drawer", id="open-drawer-button"),
        dmc.Drawer(
            title="Drawer Example",
            id="drawer",
            children=[
                html.P("Este es un ejemplo de un drawer usando Dash Mantine Components."),
                dmc.Button("Cerrar", id="close-drawer-button")
            ],
            opened=False,
            position="right",
        )
    ])
)

@app.callback(
    Output("drawer", "opened"),
    [Input("open-drawer-button", "n_clicks"), Input("close-drawer-button", "n_clicks")]
)
def toggle_drawer(open_clicks, close_clicks):
    if open_clicks or close_clicks:
        ctx = callback_context
        if not ctx.triggered:
            return False
        else:
            triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
            return triggered_id == "open-drawer-button"
    return False

if __name__ == "__main__":
    app.run_server(debug=True)

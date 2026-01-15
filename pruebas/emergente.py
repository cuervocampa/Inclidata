import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px
import pandas as pd

app = dash.Dash(__name__)

# Datos de ejemplo
df = pd.DataFrame({
    "x": [1, 2, 3, 4],
    "y": [10, 11, 12, 13],
    "category": ["A", "B", "A", "B"]
})

app.layout = html.Div([
    # Botón para abrir el modal
    html.Button("Configurar Gráfico", id="open-modal-button"),

    # Modal de configuración
    html.Div(
        id="config-modal",
        style={"display": "none", "position": "fixed", "top": "20%", "left": "20%", "width": "60%", "backgroundColor": "white", "padding": "20px", "border": "1px solid #ccc", "zIndex": 1000},
        children=[
            html.H3("Configuración del Gráfico"),
            html.Label("Seleccione el eje X"),
            dcc.Dropdown(
                id="x-axis-dropdown",
                options=[{"label": col, "value": col} for col in df.columns],
                value="x"
            ),
            html.Label("Seleccione el eje Y"),
            dcc.Dropdown(
                id="y-axis-dropdown",
                options=[{"label": col, "value": col} for col in df.columns],
                value="y"
            ),
            html.Button("Generar Gráfico", id="generate-graph-button"),
            html.Button("Cerrar", id="close-modal-button", style={"float": "right"})
        ]
    ),

    # Contenedor para el gráfico
    dcc.Graph(id="graph-output")
])

# Callback para abrir y cerrar el modal
@app.callback(
    Output("config-modal", "style"),
    [Input("open-modal-button", "n_clicks"), Input("close-modal-button", "n_clicks")],
    [State("config-modal", "style")]
)
def toggle_modal(open_clicks, close_clicks, style):
    # Cambia la visibilidad del modal en función de los clics en los botones
    if open_clicks or close_clicks:
        style["display"] = "block" if style["display"] == "none" else "none"
    return style

# Callback para actualizar el gráfico en función de los parámetros seleccionados
@app.callback(
    Output("graph-output", "figure"),
    Input("generate-graph-button", "n_clicks"),
    [State("x-axis-dropdown", "value"), State("y-axis-dropdown", "value")]
)
def update_graph(n_clicks, x_axis, y_axis):
    if n_clicks:
        fig = px.scatter(df, x=x_axis, y=y_axis, color="category")
        return fig
    return {}

if __name__ == "__main__":
    app.run_server(debug=True)

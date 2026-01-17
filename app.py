# app.py

# ejecución en windows
# .\venv\Scripts\Activate.ps1
# python app.py


import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

# Importar layouts de cada página
from pages import (
    info,
    importar,
    configuraciones,
    graficar,
    correcciones,
    importar_umbrales,
    configuracion_plantilla_claude,
    # configuracion_plantilla_gpt,
)
from utils import funciones_comunes as utils


# Inicializa la aplicación
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

# Define la barra lateral
sidebar = html.Div(
    [
        html.H2("Menú", className="display-4"),
        html.Hr(),
        html.P("Navegación", className="lead"),
        dbc.Nav(
            [
                dbc.NavLink("Info", href="/", active="exact"),
                dbc.NavLink("Importar", href="/importar", active="exact"),
                dbc.NavLink("Graficar", href="/graficar", active="exact"),
                dbc.NavLink("Correcciones", href="/correcciones", active="exact"),
                dbc.NavLink("Importar umbrales", href="/importar_umbrales", active="exact"),
                # dbc.NavLink("Plantilla gpt", href="/configuracion_plantilla_gpt", active="exact"),
                dbc.NavLink("Plantilla claude", href="/configuracion_plantilla_claude", active="exact"),
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "16rem",
        "padding": "2rem 1rem",
        "background-color": "#f8f9fa",
    },
)

# Define el contenedor del contenido principal (panel derecho)
content = html.Div(id="page-content", style={"margin-left": "18rem", "padding": "2rem 1rem"})

# Layout de la aplicación envuelto en MantineProvider (requisito DMC v2)
app.layout = dmc.MantineProvider(
    defaultColorScheme="light",
    theme={
        "fontFamily": "Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
    },
    children=[dcc.Location(id="url"),
        sidebar,
        content,
    ],
)

# Registra los callbacks de todas las páginas
importar.register_callbacks(app)
# info.register_callbacks(app)
graficar.register_callbacks(app)  # CORREGIDO: Con fix de responsive=False y autosize=False
# graficar_debug.register_callbacks(app)  # DEBUG ya no necesario
correcciones.register_callbacks(app)
importar_umbrales.register_callbacks(app)
# configuraciones.register_callbacks(app)
# configuracion_plantilla_gpt.register_callbacks(app)
configuracion_plantilla_claude.register_callbacks(app)
# graficar_debug.register_callbacks(app)  # Ya registrado arriba


# Callback de enrutado de páginas
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname: str):
    if pathname == "/":
        return info.layout()
    elif pathname == "/importar":
        return importar.layout()
    elif pathname == "/graficar":
        return graficar.layout()
    elif pathname == "/correcciones":
        return correcciones.layout()
    elif pathname == "/importar_umbrales":
        return importar_umbrales.layout()
    # elif pathname == "/configuracion_plantilla_gpt":
    #     return configuracion_plantilla_gpt.layout()
    elif pathname == "/configuracion_plantilla_claude":
        return configuracion_plantilla_claude.layout()

    # Página no encontrada
    return html.Div([
        html.H1("404: Página no encontrada", className="text-danger"),
        html.P("La página que está buscando no existe."),
    ])


if __name__ == "__main__":
    if hasattr(app, "run"):
        app.run(debug=True)
    else:
        app.run_server(debug=True)

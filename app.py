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
    editor_plantilla,
    # configuracion_plantilla_gpt,
)
from utils import funciones_comunes as utils


# Inicializa la aplicación
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

# Define la barra lateral con switch de modo oscuro
sidebar = html.Div(
    [
        html.H2("Menú", className="display-4"),
        html.Hr(),
        # Switch para alternar modo claro/oscuro
        dmc.Group([
            dmc.Text("🌙 Modo oscuro", size="sm"),
            dmc.Switch(id="color-scheme-toggle", size="md", checked=False)
        ], gap="xs", style={"marginBottom": "15px"}),
        html.P("Navegación", className="lead"),
        dbc.Nav(
            [
                dbc.NavLink("Info", href="/", active="exact"),
                dbc.NavLink("Importar", href="/importar", active="exact"),
                dbc.NavLink("Graficar", href="/graficar", active="exact"),
                dbc.NavLink("Correcciones", href="/correcciones", active="exact"),
                dbc.NavLink("Importar umbrales", href="/importar_umbrales", active="exact"),
                # dbc.NavLink("Plantilla gpt", href="/configuracion_plantilla_gpt", active="exact"),
                dbc.NavLink("Editor plantillas", href="/editor_plantilla", active="exact"),
            ],
            vertical=True,
            pills=True,
        ),
    ],
    id="sidebar",
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

# Define el contenedor del contenido principal (panel derecho) con estilo oscuro por defecto
content = html.Div(
    id="page-content",
    style={
        "margin-left": "18rem",
        "padding": "2rem 1rem",
        "background-color": "#ffffff",
        "color": "#000000",
        "min-height": "100vh",
    }
)

# Store para el esquema de color
color_scheme_store = dcc.Store(id="color-scheme-store", data="light", storage_type="local")

# Layout de la aplicación envuelto en MantineProvider (requisito DMC v2)
app.layout = html.Div(
    id="app-container",
    style={"background-color": "#ffffff", "min-height": "100vh"},  # Estilo claro por defecto
    children=[
        color_scheme_store,
        dmc.MantineProvider(
            id="mantine-provider",
            forceColorScheme="light",  # Por defecto modo claro
            theme={
                "fontFamily": "Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
            },
            children=[
                dcc.Location(id="url"),
                sidebar,
                content,
            ],
        ),
    ]
)

# Callback para alternar modo claro/oscuro
@app.callback(
    [Output("mantine-provider", "forceColorScheme"),
     Output("sidebar", "style"),
     Output("page-content", "style"),
     Output("app-container", "style")],
    [Input("color-scheme-toggle", "checked")]
)
def toggle_color_scheme(is_dark):
    if is_dark:
        sidebar_style = {
            "position": "fixed",
            "top": 0,
            "left": 0,
            "bottom": 0,
            "width": "16rem",
            "padding": "2rem 1rem",
            "background-color": "#1a1b1e",
            "color": "#c1c2c5",
        }
        content_style = {
            "margin-left": "18rem",
            "padding": "2rem 1rem",
            "background-color": "#141517",
            "color": "#c1c2c5",
            "min-height": "100vh",
        }
        app_style = {
            "background-color": "#141517",
            "min-height": "100vh",
        }
        return "dark", sidebar_style, content_style, app_style
    else:
        sidebar_style = {
            "position": "fixed",
            "top": 0,
            "left": 0,
            "bottom": 0,
            "width": "16rem",
            "padding": "2rem 1rem",
            "background-color": "#f8f9fa",
            "color": "#000000",
        }
        content_style = {
            "margin-left": "18rem",
            "padding": "2rem 1rem",
            "background-color": "#ffffff",
            "color": "#000000",
            "min-height": "100vh",
        }
        app_style = {
            "background-color": "#ffffff",
            "min-height": "100vh",
        }
        return "light", sidebar_style, content_style, app_style



# Registra los callbacks de todas las páginas
importar.register_callbacks(app)
# info.register_callbacks(app)
graficar.register_callbacks(app)  # CORREGIDO: Con fix de responsive=False y autosize=False
# graficar_debug.register_callbacks(app)  # DEBUG ya no necesario
correcciones.register_callbacks(app)
importar_umbrales.register_callbacks(app)
# configuraciones.register_callbacks(app)
# configuracion_plantilla_gpt.register_callbacks(app)
editor_plantilla.register_callbacks(app)
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
    elif pathname == "/editor_plantilla":
        return editor_plantilla.layout()

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

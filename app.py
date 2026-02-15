# app.py

# ejecución en windows
# .\venv\Scripts\Activate.ps1
# python app.py


import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_iconify import DashIconify

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
    editor_visual,
)
from utils import funciones_comunes as utils


# Inicializa la aplicación
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

# --- Sidebar con iconos y estilo premium ---
NAV_ITEMS = [
    {"label": "Info",               "href": "/",                  "icon": "lucide:info"},
    {"label": "Importar",           "href": "/importar",          "icon": "lucide:upload"},
    {"label": "Graficar",           "href": "/graficar",          "icon": "lucide:bar-chart-3"},
    {"label": "Correcciones",       "href": "/correcciones",      "icon": "lucide:wrench"},
    {"label": "Importar umbrales",  "href": "/importar_umbrales", "icon": "lucide:alert-triangle"},
    {"label": "Editor plantillas",  "href": "/editor_plantilla",  "icon": "lucide:file-text"},
    {"label": "Editor Visual",      "href": "/editor-visual",     "icon": "lucide:layout-dashboard"},
]

sidebar = html.Div(
    [
        # Header
        html.Div("IncliData", className="sidebar-header"),

        # Dark mode toggle
        html.Div([
            DashIconify(icon="lucide:moon", width=16, style={"color": "var(--id-text-muted)"}),
            html.Span("Modo oscuro", className="sidebar-toggle-label"),
            dmc.Switch(id="color-scheme-toggle", size="md", checked=False),
        ], className="sidebar-toggle-container"),

        # Nav section label
        html.Div("Navegación", className="sidebar-nav-label"),

        # Nav items (keep dbc.NavLink for active="exact" auto-highlighting)
        dbc.Nav(
            [
                dbc.NavLink(
                    children=[
                        DashIconify(icon=item["icon"], width=18, className="sidebar-nav-icon"),
                        html.Span(item["label"]),
                    ],
                    href=item["href"],
                    active="exact",
                    className="sidebar-nav-item",
                )
                for item in NAV_ITEMS
            ],
            vertical=True,
            pills=False,
            id="sidebar-nav-list",
        ),
    ],
    id="sidebar",
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "240px",
        "padding": "1.5rem 0.75rem",
        "display": "flex",
        "flexDirection": "column",
        "backgroundColor": "#F5F7FA",
        "borderRight": "1px solid #E5E7EB",
    },
)

# Define el contenedor del contenido principal
content = html.Div(
    id="page-content",
    style={
        "margin-left": "260px",
        "padding": "2rem 1.5rem",
        "background-color": "#FFFFFF",
        "color": "#1F2937",
        "min-height": "100vh",
    }
)

# Store para el esquema de color
color_scheme_store = dcc.Store(id="color-scheme-store", data="light", storage_type="local")

# Layout de la aplicación envuelto en MantineProvider (requisito DMC v2)
app.layout = html.Div(
    id="app-container",
    style={"background-color": "#FFFFFF", "min-height": "100vh"},
    children=[
        color_scheme_store,
        dmc.MantineProvider(
            id="mantine-provider",
            forceColorScheme="light",
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
            "width": "240px",
            "padding": "1.5rem 0.75rem",
            "display": "flex",
            "flexDirection": "column",
            "backgroundColor": "hsl(225, 10%, 7%)",
            "borderRight": "1px solid hsl(225, 6%, 18%)",
            "color": "hsl(220, 9%, 78%)",
        }
        content_style = {
            "margin-left": "260px",
            "padding": "2rem 1.5rem",
            "backgroundColor": "hsl(225, 8%, 8%)",
            "color": "hsl(220, 9%, 78%)",
            "min-height": "100vh",
        }
        app_style = {
            "backgroundColor": "hsl(225, 8%, 8%)",
            "min-height": "100vh",
        }
        return "dark", sidebar_style, content_style, app_style
    else:
        sidebar_style = {
            "position": "fixed",
            "top": 0,
            "left": 0,
            "bottom": 0,
            "width": "240px",
            "padding": "1.5rem 0.75rem",
            "display": "flex",
            "flexDirection": "column",
            "backgroundColor": "#F5F7FA",
            "borderRight": "1px solid #E5E7EB",
            "color": "#1F2937",
        }
        content_style = {
            "margin-left": "260px",
            "padding": "2rem 1.5rem",
            "backgroundColor": "#FFFFFF",
            "color": "#1F2937",
            "min-height": "100vh",
        }
        app_style = {
            "backgroundColor": "#FFFFFF",
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
editor_visual.register_callbacks(app)
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
    elif pathname == "/editor-visual":
        return editor_visual.layout()


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

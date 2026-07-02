# app.py
# Arranque: python app.py
# Windows:  .\venv\Scripts\Activate.ps1 && python app.py

import logging

import matplotlib
matplotlib.use('Agg')

import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import dcc, html
from dash.dependencies import Input, Output
from dash_iconify import DashIconify

from pages import (
    configuraciones,
    correcciones,
    editor_plantilla,
    editor_visual,
    graficar,
    importar,
    importar_umbrales,
    info,
)
from utils import funciones_comunes as utils

# ---------------------------------------------------------------------------
# Logging de errores del servidor Flask
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.ERROR)
_logger = logging.getLogger("inclidata")

# ---------------------------------------------------------------------------
# Inicialización de la app
# ---------------------------------------------------------------------------
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)


@app.server.errorhandler(Exception)
def _handle_server_error(e):
    _logger.exception("Server error")
    return "Internal Server Error", 500


# ---------------------------------------------------------------------------
# Estilos de tema (light / dark)
# ---------------------------------------------------------------------------
_SIDEBAR_BASE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "240px",
    "padding": "1.5rem 0.75rem",
    "display": "flex",
    "flexDirection": "column",
}
_CONTENT_BASE = {
    "margin-left": "260px",
    "padding": "2rem 1.5rem",
    "min-height": "100vh",
}

_THEMES = {
    "light": {
        "sidebar": {**_SIDEBAR_BASE, "backgroundColor": "#fafaf9", "borderRight": "1px solid #d6d3d1", "color": "#1c1917"},
        "content": {**_CONTENT_BASE, "backgroundColor": "#f5f5f4", "color": "#1c1917"},
        "app":     {"backgroundColor": "#f5f5f4", "min-height": "100vh"},
    },
    "dark": {
        "sidebar": {**_SIDEBAR_BASE, "backgroundColor": "#0c0a09", "borderRight": "1px solid #44403c", "color": "#e7e5e4"},
        "content": {**_CONTENT_BASE, "backgroundColor": "#1c1917", "color": "#e7e5e4"},
        "app":     {"backgroundColor": "#1c1917", "min-height": "100vh"},
    },
}

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
NAV_ITEMS = [
    {"label": "Info",              "href": "/",                  "icon": "lucide:info"},
    {"label": "Importar",          "href": "/importar",          "icon": "lucide:upload"},
    {"label": "Graficar",          "href": "/graficar",          "icon": "lucide:bar-chart-3"},
    {"label": "Correcciones",      "href": "/correcciones",      "icon": "lucide:wrench"},
    {"label": "Importar umbrales", "href": "/importar_umbrales", "icon": "lucide:alert-triangle"},
    {"label": "Editor plantillas", "href": "/editor_plantilla",  "icon": "lucide:file-text"},
    {"label": "Editor Visual",     "href": "/editor-visual",     "icon": "lucide:layout-dashboard"},
]

sidebar = html.Div(
    [
        html.Div("IncliData", className="sidebar-header"),
        html.Div(
            [
                DashIconify(icon="lucide:moon", width=16, style={"color": "var(--id-text-muted)"}),
                html.Span("Modo oscuro", className="sidebar-toggle-label"),
                dmc.Switch(id="color-scheme-toggle", size="md", checked=False),
            ],
            className="sidebar-toggle-container",
        ),
        html.Div("Navegación", className="sidebar-nav-label"),
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
    style=_THEMES["light"]["sidebar"],
)

content = html.Div(id="page-content", style=_THEMES["light"]["content"])

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
app.layout = html.Div(
    id="app-container",
    style=_THEMES["light"]["app"],
    children=[
        dcc.Store(id="color-scheme-store", data="light", storage_type="local"),
        dmc.MantineProvider(
            id="mantine-provider",
            forceColorScheme="light",
            theme={"fontFamily": "Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif"},
            children=[
                dmc.NotificationProvider(position="top-right", zIndex=9999),
                dcc.Location(id="url"),
                sidebar,
                content,
            ],
        ),
    ],
)

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
@app.callback(
    [
        Output("mantine-provider", "forceColorScheme"),
        Output("sidebar", "style"),
        Output("page-content", "style"),
        Output("app-container", "style"),
    ],
    [Input("color-scheme-toggle", "checked")],
)
def toggle_color_scheme(is_dark: bool):
    theme = _THEMES["dark"] if is_dark else _THEMES["light"]
    scheme = "dark" if is_dark else "light"
    return scheme, theme["sidebar"], theme["content"], theme["app"]


@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname: str):
    routes = {
        "/":                 info.layout,
        "/importar":         importar.layout,
        "/graficar":         graficar.layout,
        "/correcciones":     correcciones.layout,
        "/importar_umbrales": importar_umbrales.layout,
        "/editor_plantilla": editor_plantilla.layout,
        "/editor-visual":    editor_visual.layout,
    }
    if pathname in routes:
        return routes[pathname]()
    return html.Div([
        html.H1("404: Página no encontrada", className="text-danger"),
        html.P("La página que está buscando no existe."),
    ])


# Registro de callbacks de páginas
importar.register_callbacks(app)
graficar.register_callbacks(app)
correcciones.register_callbacks(app)
importar_umbrales.register_callbacks(app)
editor_plantilla.register_callbacks(app)
editor_visual.register_callbacks(app)


if __name__ == "__main__":
    from utils.dev_logging import apply_callback_logging
    apply_callback_logging(app)

    if hasattr(app, "run"):
        app.run(debug=True, dev_tools_hot_reload=False, port=8051)
    else:
        app.run_server(debug=True, port=8051)

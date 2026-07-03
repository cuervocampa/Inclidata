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
    graficar,
    importar,
    importar_umbrales,
    info,
)
from utils import funciones_comunes as utils

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


if __name__ == "__main__":
    import os
    import sys
    from logging.handlers import RotatingFileHandler

    _fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    _console = logging.StreamHandler(sys.stdout)
    _console.setFormatter(_fmt)
    _logfile = RotatingFileHandler("debug_incli.log", maxBytes=5_000_000, backupCount=1, encoding="utf-8")
    _logfile.setFormatter(_fmt)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[_console, _logfile],
        force=True,
    )
    # Werkzeug: handlers propios (propagate=False) para que los logs de acceso lleguen
    # al archivo aunque Dash/reloader reconfigure la cadena de propagación.
    _wz = logging.getLogger("werkzeug")
    _wz.setLevel(logging.INFO)
    _wz.propagate = False
    _wz.handlers.clear()
    _wz.addHandler(_console)
    _wz.addHandler(_logfile)

    from utils.dev_logging import apply_callback_logging
    apply_callback_logging(app)

    # CRITICO: en modo dev, exclude_patterns evita que el reloader reinicie el servidor cuando la app
    # escribe archivos en runtime (json_inclis, logs). Sin esto, los callbacks en vuelo mueren con
    # 'server did not respond'. Ver CONTEXT.md.
    modo_dev = os.environ.get("INCLIDATA_DEBUG") == "1"
    if modo_dev:
        app.run(debug=True, dev_tools_hot_reload=False, port=8051,
                exclude_patterns=["*json_inclis*", "*.log", "*.pdf", "*vista_previa*",
                                   "*_assets/registry.json*"])
    else:
        app.run(debug=False, use_reloader=False, port=8051)

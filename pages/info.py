from dash import html


def layout():
    return html.Div([
        html.H1("Información General", className="text-center"),
        html.P("Esta es la información general sobre la aplicación...")
    ])

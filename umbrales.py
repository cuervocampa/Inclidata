import dash
from dash import dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc  # Importamos la librería Dash Mantine Components
import random

# Lista de colores básicos disponibles para asignación
colores_basicos = ['blue', 'yellow', 'purple', 'pink', 'brown', 'gray', 'cyan']

# Diccionario de umbrales predefinidos (fuera del layout)
datos_tubo = {
    'umbrales': {
        'deformadas': ['umbral1_a', 'umbral2_a', 'umbral3_a', 'umbral4_a', 'umbral1_b', 'umbral2_b', 'umbral3_b',
                       'umbral4_b']
    }
}


# Función para asignar colores a umbrales según reglas
def asignar_colores(umbrales_tubo):
    grupo_a = [umbral for umbral in umbrales_tubo if umbral.endswith("_a")]
    grupo_b = [umbral for umbral in umbrales_tubo if umbral.endswith("_b")]

    def asignar_colores_grupo(grupo):
        colores_asignados = {}
        colores_disponibles = colores_basicos.copy()
        random.shuffle(colores_disponibles)

        # Asignación de colores fijos para los primeros tres elementos de cada grupo
        if grupo:
            colores_asignados[grupo[0]] = 'verde'
        if len(grupo) > 1:
            colores_asignados[grupo[1]] = 'naranja'
        if len(grupo) > 2:
            colores_asignados[grupo[2]] = 'rojo'

        # Asignación de colores aleatorios para el resto, sin repetirse dentro del grupo
        for i in range(3, len(grupo)):
            if colores_disponibles:
                colores_asignados[grupo[i]] = colores_disponibles.pop()

        return colores_asignados

    colores_umbrales = {**asignar_colores_grupo(grupo_a), **asignar_colores_grupo(grupo_b)}
    return colores_umbrales


# Inicialización de la app con Bootstrap
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# Definición del layout de la aplicación
app.layout = html.Div([
    dcc.Store(id='tubo', data=datos_tubo),
    dcc.Store(id='leyenda_umbrales', data={}),
    dbc.Button("Abrir Configuración", id="abrir-drawer", n_clicks=0),
    dmc.Drawer(
        id="drawer-configuracion",
        title="Configuración de Umbrales",
        opened=False,
        position="right",  # Abre el drawer desde la derecha
        padding="md",
        size="md",
        children=[html.Div(id='contenido-drawer')]
    )
])


# Callback para abrir/cerrar el drawer
@app.callback(
    Output("drawer-configuracion", "opened"),
    Input("abrir-drawer", "n_clicks"),
    State("drawer-configuracion", "opened")
)
def toggle_drawer(n, is_open):
    if n and n > 0:
        return not is_open
    return is_open


# Callback para inicializar la leyenda de umbrales cuando se carga la app
@app.callback(
    Output("leyenda_umbrales", "data"),
    Input("tubo", "data"),
    State("leyenda_umbrales", "data")
)
def inicializar_leyenda(tubo, leyenda_actual):
    umbrales_tubo = tubo.get('umbrales', {}).get('deformadas', [])

    # Solo inicializar si no hay datos o si hay cambios en los umbrales
    if not leyenda_actual or not isinstance(leyenda_actual, dict) or set(umbrales_tubo) != set(leyenda_actual.keys()):
        return asignar_colores(umbrales_tubo)

    return leyenda_actual


# Callback para actualizar dinámicamente el contenido del drawer
@app.callback(
    Output("contenido-drawer", "children"),
    [Input("tubo", "data"), Input("leyenda_umbrales", "data")]
)
def actualizar_drawer(tubo, leyenda_actual):
    umbrales_tubo = tubo.get('umbrales', {}).get('deformadas', [])
    if not umbrales_tubo:
        return []

    # Añadir 'verde', 'naranja', 'rojo' a las opciones si no están ya
    opciones_colores = colores_basicos.copy()
    for color in ['verde', 'naranja', 'rojo']:
        if color not in opciones_colores:
            opciones_colores.append(color)

    filas = []
    for umbral in umbrales_tubo:
        filas.append(
            dbc.Row([
                dbc.Col(html.Div(umbral), width=6),
                dbc.Col(dcc.Dropdown(
                    id={'type': 'color-dropdown', 'index': umbral},
                    options=[{'label': c, 'value': c} for c in opciones_colores],
                    value=leyenda_actual.get(umbral, 'gray'),
                    clearable=False
                ), width=6)
            ], className="mb-2")
        )
    return filas


# Callback para actualizar colores individuales cuando se cambia un dropdown
@app.callback(
    Output("leyenda_umbrales", "data", allow_duplicate=True),
    Input({'type': 'color-dropdown', 'index': dash.ALL}, "value"),
    State({'type': 'color-dropdown', 'index': dash.ALL}, "id"),
    State("leyenda_umbrales", "data"),
    prevent_initial_call=True
)
def actualizar_color_individual(valores, ids, leyenda_actual):
    if not ctx.triggered or not isinstance(leyenda_actual, dict):
        return dash.no_update

    leyenda_actualizada = leyenda_actual.copy()

    for i, valor in enumerate(valores):
        if valor is not None:
            umbral = ids[i]['index']
            leyenda_actualizada[umbral] = valor

    return leyenda_actualizada


# Ejecución de la aplicación
if __name__ == "__main__":
    app.run_server(debug=True)
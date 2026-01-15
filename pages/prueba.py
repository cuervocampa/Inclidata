# pages/importar.py

import os
import dash
from dash import dcc, html, Input, Output, State, ctx, dash_table
import dash_bootstrap_components as dbc
import json
import base64
import io
from utils.diccionarios import importadores
from utils.funciones_comunes import import_RST

# Inicialización de la app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'Prueba Wizard Dash'
app.config.suppress_callback_exceptions = True
server = app.server

# Definición de layout
app.layout = html.Div([
    html.H1("Aplicación Wizard con Dash", style={'textAlign': 'left'}),
    html.Div(id='step-1', children=[
        html.H4("Paso 1: Seleccionar archivos", style={'textAlign': 'left'}),
        dcc.Dropdown(
            id='file-dropdown',
            options=[{'label': file, 'value': file} for file in os.listdir('../data') if
                     os.path.isfile(os.path.join('../data', file))],
            multi=True,
            placeholder="Selecciona archivos...",
            style={'width': '33%', 'margin': '10px 0'}
        ),
        html.Button("Primero", id='first-button', n_clicks=0, style={'display': 'block', 'margin': '10px 0'})
    ]),
    html.Div(id='step-2'),
    html.Div(id='step-3'),
    html.Div(id='output-container')
])


# Callbacks para manejar la lógica del wizard

# Callback para cargar los campos Cte1, Cte2, Cte3 después de seleccionar archivos y presionar "Primero"
@app.callback(
    Output('step-2', 'children'),
    Input('first-button', 'n_clicks'),
    State('file-dropdown', 'value'),
    prevent_initial_call=True
)
def display_dropdown_input(n_clicks, selected_files):
    if n_clicks > 0 and selected_files:
        return html.Div([
            html.H4("Paso 2: Seleccionar características", style={'textAlign': 'left'}),
            dcc.Dropdown(
                id='cte-dropdown',
                options=[{'label': key, 'value': value} for key, value in importadores.items()],
                placeholder='Selecciona una opción',
                value=default_value(selected_files),
                style={'width': '33%', 'margin': '10px 0'}
            ),
            html.Button("Segundo", id='second-button', n_clicks=0, style={'display': 'block', 'margin': '10px 0'})
        ])
    return None


# Callback para cargar la ventana de upload después de presionar "Segundo"
@app.callback(
    Output('step-3', 'children'),
    Input('second-button', 'n_clicks'),
    prevent_initial_call=True
)
def display_upload_section(n_clicks):
    if n_clicks > 0:
        return html.Div([
            html.H4("Paso 3: Subir archivos", style={'textAlign': 'left'}),
            html.Hr(),
            dcc.Upload(id='file-upload', multiple=True, children=[
                'Drag and Drop or ',
                html.A('Select Files')
            ], style={
                'width': '33%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px 0'
            }),
            html.Div(id='uploaded-files-list', style={'textAlign': 'left', 'marginTop': '10px', 'width': '33%'}),
            html.Button("Tercero", id='third-button', n_clicks=0, style={'display': 'block', 'margin': '10px 0'})
        ])
    return None


# Callback para mostrar los archivos subidos dinámicamente en la página
@app.callback(
    Output('uploaded-files-list', 'children'),
    Input('file-upload', 'filename')
)
def update_uploaded_files_list(uploaded_files):
    if uploaded_files:
        if isinstance(uploaded_files, str):
            uploaded_files = [uploaded_files]
        return html.Ul([html.Li(file) for file in uploaded_files],
                       style={'listStyleType': 'none', 'textAlign': 'left', 'width': '33%', 'margin': '10px 0'})
    return "No se subieron archivos."


# Callback para ejecutar una función basada en la selección del dropdown al presionar "Tercero"
@app.callback(
    Output('output-container', 'children'),
    Input('third-button', 'n_clicks'),
    State('cte-dropdown', 'value'),
    State('file-upload', 'contents'),
    State('file-upload', 'filename'),
    prevent_initial_call=True
)
def execute_function_third(n_clicks, selected_value, uploaded_contents, uploaded_files):
    if n_clicks > 0:
        if selected_value == 'RST':
            # Llamar a la función import_RST con los archivos cargados
            try:
                if isinstance(uploaded_files, str):
                    uploaded_files = [uploaded_files]
                if isinstance(uploaded_contents, str):
                    uploaded_contents = [uploaded_contents]

                # Decodificar los archivos y convertirlos en diccionarios
                input_files = []
                for content, filename in zip(uploaded_contents, uploaded_files):
                    content_type, content_string = content.split(',')
                    decoded = base64.b64decode(content_string)
                    lines = decoded.decode('utf-8').splitlines()
                    input_files.append({'filename': filename, 'lines': lines})

                result = import_RST(input_files)
                return html.Div(
                    [html.H5(f"Resultado de importación: {result}", style={'textAlign': 'left', 'width': '33%'})])
            except Exception as e:
                return html.Div([html.H5(f"Error al importar: {str(e)}", style={'textAlign': 'left', 'width': '33%'})])
        elif selected_value == 'Sisgeo':
            return html.Div([html.H5("No disponible", style={'textAlign': 'left', 'width': '33%'})])
        else:
            return html.Div([html.H5("Opción no reconocida", style={'textAlign': 'left', 'width': '33%'})])
    return None


# Funciones auxiliares
def default_value(selected_files):
    if not selected_files:
        return None

    latest_file = selected_files[-1]
    file_path = os.path.join('../data', latest_file)

    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            latest_campaign = None
            latest_date = None

            # Iterar sobre las campañas para encontrar la fecha más reciente
            for date_str, campaign in data.items():
                if isinstance(campaign, dict) and "Tipo_archivo" in campaign:
                    if not latest_date or date_str > latest_date:
                        latest_campaign = campaign
                        latest_date = date_str

            if latest_campaign:
                tipo_archivo = latest_campaign.get("Tipo_archivo", None)
                if tipo_archivo in importadores.values():
                    return tipo_archivo
    except Exception as e:
        print(f"Error al leer el archivo JSON: {e}")

    return None


# Ejecutar la app
if __name__ == '__main__':
    app.run_server(debug=True)
# pages/importar.py

import plotly.graph_objs as go
import os
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import json
import base64
from utils.diccionarios import importadores
from utils.funciones_comunes import import_RST, calcular_incrementos
from utils.funciones_graficos import importar_graficos
from utils.funciones_importar import insertar_camp, es_fecha_isoformat, default_value
import pprint
import datetime
import re

# Definir la ruta al directorio 'data'
DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))

# Verificar si la carpeta 'data' existe
if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(f"El directorio {DATA_PATH} no existe. Verifica la estructura de tu proyecto.")

# Variable global para almacenar el contenido del archivo JSON cargado
selected_file_data = None

# Definición del layout
def layout():
    return html.Div([
        html.H1("Aplicación Wizard con Dash", style={'textAlign': 'left'}),
        html.Div(id='import-step-1', children=[
            html.H4("Paso 1: Seleccionar archivos", style={'textAlign': 'left'}),
            dcc.Dropdown(
                id='import-file-dropdown',
                options=[
                    {'label': file, 'value': file} for file in os.listdir(DATA_PATH) if
                    os.path.isfile(os.path.join(DATA_PATH, file))
                ],
                multi=False,
                placeholder="Selecciona archivos...",
                style={'width': '33%', 'margin': '10px 0'}
            ),
            html.Button("Primero", id='import-first-button', n_clicks=0, style={'display': 'block', 'margin': '10px 0'}),
            dcc.Store(id='selected-file-store')
        ]),
        html.Div(id='import-step-2'),
        html.Div(id='import-step-3'),
        html.Div(id='import-output-container')
    ])
# Variable global para almacenar el nombre del archivo seleccionado
selected_filename = None
# Callbacks para manejar la lógica del wizard
def register_callbacks(app):
    global selected_file_data, selected_filename
    @app.callback(
        Output('import-step-2', 'children'),
        Input('import-first-button', 'n_clicks'),
        State('import-file-dropdown', 'value'),
        prevent_initial_call=True
    )
    def display_dropdown_input(n_clicks, selected_files):
        # Debugging log
        global selected_file_data, selected_filename
        print(f"Botón 'Primero' clickeado: {n_clicks} veces, archivos seleccionados: {selected_files}")
        triggered = callback_context.triggered
        if triggered and 'import-first-button' in triggered[0]['prop_id'] and n_clicks > 0:
            if selected_files:
                # Guardar el nombre del archivo seleccionado
                selected_filename = selected_files
                # Leer y almacenar el archivo JSON en la variable global
                file_path = os.path.join(DATA_PATH, selected_files)
                try:
                    with open(file_path, 'r') as json_file:
                        selected_file_data = json.load(json_file)
                except json.JSONDecodeError as e:
                    print(f"Error al leer el archivo JSON (formato incorrecto): {e}")
                    return html.Div([
                        html.H5(
                            f"Error al leer el archivo JSON: formato incorrecto. Corrige el archivo antes de continuar.",
                            style={'textAlign': 'left', 'width': '33%', 'color': 'red'})
                    ])
                # datos en el archivo del tubo
                campaign_info = default_value(selected_files, DATA_PATH)

                # obtiene el importador de la última campaña
                if campaign_info:
                    default_importador_value = campaign_info.get('importador', None)
                else:
                    # Manejar el caso donde campaign_info es None
                    print("Error: No se pudo obtener información de la campaña.")
                    return html.Div([
                        html.H5("Error: No se pudo obtener información de la campaña seleccionada.",
                                style={'textAlign': 'left', 'color': 'red'})
                    ])

                return html.Div([
                    html.H4("Paso 2: Seleccionar importador", style={'textAlign': 'left'}),
                    html.Pre(f"Info del inclinómetro en TD:{pprint.pformat(campaign_info)}", style={'color': 'blue', 'whiteSpace': 'pre-wrap', 'marginLeft': '20px'}),  # Mostrar el valor con formato amigable
                    dcc.Dropdown(
                        id='import-importador',
                        options=[{'label': key, 'value': value} for key, value in importadores.items()],
                        placeholder='Selecciona una opción',
                        value=default_importador_value if default_importador_value in importadores.values() else None,
                        style={'width': '33%', 'margin': '10px 0'}
                    ),
                    html.Button("Segundo", id='import-second-button', n_clicks=0,
                                style={'display': 'block', 'margin': '10px 0'}),
                    dcc.Store(id='selected-file-store', data=selected_files)
                ])
        return None

    @app.callback(
        Output('import-step-3', 'children'),
        Input('import-second-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def display_upload_section(n_clicks):
        # Debugging log
        print(f"Botón 'Segundo' clickeado: {n_clicks} veces")
        triggered = callback_context.triggered
        if triggered and 'import-second-button' in triggered[0]['prop_id'] and n_clicks > 0:
            return html.Div([
                html.H4("Paso 3: Subir archivos", style={'textAlign': 'left'}),
                html.Hr(),
                dcc.Upload(id='import-file-upload', multiple=True, children=[
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
                html.Div(id='import-uploaded-files-list', style={'textAlign': 'left', 'marginTop': '10px', 'width': '33%'}),
                html.Button("Tercero", id='import-third-button', n_clicks=0, style={'display': 'block', 'margin': '10px 0'})
            ])
        return None

    @app.callback(
        Output('import-uploaded-files-list', 'children'),
        Input('import-file-upload', 'filename')
    )
    def update_uploaded_files_list(uploaded_files):
        # Debugging log
        print(f"Archivos subidos: {uploaded_files}")
        if uploaded_files:
            if isinstance(uploaded_files, str):
                uploaded_files = [uploaded_files]
            return html.Ul([html.Li(file) for file in uploaded_files],
                           style={'listStyleType': 'none', 'textAlign': 'left', 'width': '33%', 'margin': '10px 0'})
        return "No se subieron archivos."

    @app.callback(
        Output('import-output-container', 'children'),
        Input('import-third-button', 'n_clicks'),
        State('import-importador', 'value'),
        State('import-file-upload', 'contents'),
        State('import-file-upload', 'filename'),
        prevent_initial_call=True
    )
    def execute_function_third(n_clicks, selected_value, uploaded_contents, uploaded_files):
        global selected_file_data

        print(f"Botón 'Tercero' clickeado: {n_clicks} veces, valor seleccionado: {selected_value}")
        triggered = callback_context.triggered
        if triggered and 'import-third-button' in triggered[0]['prop_id'] and n_clicks > 0:
            try:
                # Procesamiento de los archivos subidos
                if isinstance(uploaded_files, str):
                    uploaded_files = [uploaded_files]
                if isinstance(uploaded_contents, str):
                    uploaded_contents = [uploaded_contents]

                input_files = []
                for content, filename in zip(uploaded_contents, uploaded_files):
                    content_type, content_string = content.split(',')
                    decoded = base64.b64decode(content_string)
                    lines = decoded.decode('utf-8').splitlines()
                    input_files.append({'filename': filename, 'lines': lines})

                # Condicional dependiendo del valor seleccionado
                if selected_value == 'RST':
                    # campaña pasada al formato del diccionario, con los campos raw, normalizados y calculados directos (calc)
                    result = import_RST(input_files)
                    # fechas que hay que añadir al archivo final
                    fechas_agg = []
                    for clave in result.keys():
                        if es_fecha_isoformat(clave):
                            fechas_agg.append(clave)

                    # Añadir las nuevas campañas al archivo JSON almacenado
                    for campaign_date, campaign_data in result.items():
                        if campaign_date != "info":
                            selected_file_data[campaign_date] = campaign_data
                    print('archivo json temporal almacenado')
                    print (fechas_agg)
                    
                    # añado los campos calculados al archivo json almacenado
                    for fecha in fechas_agg:
                        calcular_incrementos(selected_file_data, fecha)
                    # agregamos en el json original sólo los nuevos
                    insertar_camp(selected_file_data, fechas_agg) #ojo, esto debería estar después de un botón de confirmación de 

                    # Generar gráficos utilizando la función externa
                    graphs = importar_graficos(selected_file_data, fechas_agg)
                    return graphs

                elif selected_value == 'Sisgeo':
                    return html.Div([html.H5("No disponible", style={'textAlign': 'left', 'width': '33%'})])
                else:
                    return html.Div([html.H5("Opción no reconocida", style={'textAlign': 'left', 'width': '33%'})])

            except Exception as e:
                print(f"Error al procesar archivos: {e}")
                return html.Div([
                    html.H5(f"Error al importar: {str(e)}", style={'textAlign': 'left', 'width': '33%'})
                ])

        return None



# Update to the existing callback functionality
# pages/importar.py

import plotly.graph_objs as go
import os
from dash import dcc, html, Input, Output, State, callback_context, ALL
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
selected_file_data = {}

# Variable global para almacenar las opciones de actualización
temp_campaign_options = {}

# Variable global para almacenar el nombre del archivo seleccionado
selected_filename = None


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
            html.Button("Primero", id='import-first-button', n_clicks=0,
                        style={'display': 'block', 'margin': '10px 0'}),
            dcc.Store(id='selected-file-store')
        ]),
        html.Div(id='import-step-2'),
        html.Div(id='import-step-3'),
        html.Div(id='import-step-4'),
        html.Div(id='import-output-container')
    ])

# Callbacks para manejar la lógica del wizard
def register_callbacks(app):
    global selected_file_data, selected_filename, temp_campaign_options, DATA_PATH

    @app.callback(
        [Output('import-step-2', 'children'), Output('selected-file-store', 'data')],
        Input('import-first-button', 'n_clicks'),
        State('import-file-dropdown', 'value'),
        prevent_initial_call=True
    )
    def display_dropdown_input(n_clicks, selected_files):
        # Debugging log
        print(f"Botón 'Primero' clickeado: {n_clicks} veces, archivos seleccionados: {selected_files}")
        triggered = callback_context.triggered
        if triggered and 'import-first-button' in triggered[0]['prop_id'] and n_clicks > 0:
            if selected_files:
                # Guardar el nombre del archivo seleccionado
                global selected_filename
                selected_filename = selected_files
                # Leer y almacenar el archivo JSON en la variable global
                file_path = os.path.join(DATA_PATH, selected_files)
                try:
                    with open(file_path, 'r') as json_file:
                        selected_file_data = json.load(json_file)
                except json.JSONDecodeError as e:
                    return html.Div([
                        html.H5(
                            f"Error al leer el archivo JSON: formato incorrecto. Corrige el archivo antes de continuar.",
                            style={'textAlign': 'left', 'width': '33%', 'color': 'red'})
                    ]), selected_files

                campaign_info = default_value(selected_files, DATA_PATH)
                if campaign_info:
                    default_importador_value = campaign_info.get('importador', None)
                else:
                    return html.Div([
                        html.H5("Error: No se pudo obtener información de la campaña seleccionada.",
                                style={'textAlign': 'left', 'color': 'red'})
                    ]), selected_files

                return html.Div([
                    html.H4("Paso 2: Seleccionar importador", style={'textAlign': 'left'}),
                    html.Pre(f"Info del inclinómetro en TD:{pprint.pformat(campaign_info)}",
                             style={'color': 'blue', 'whiteSpace': 'pre-wrap', 'marginLeft': '20px'}),
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
                ]), selected_files
        return None, None

    @app.callback(
        Output('import-step-3', 'children', allow_duplicate=True),
        Input('import-second-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def display_upload_section(n_clicks):
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
                html.Div(id='import-uploaded-files-list',
                         style={'textAlign': 'left', 'marginTop': '10px', 'width': '33%'}),
                html.Button("Tercero", id='import-third-button', n_clicks=0,
                            style={'display': 'block', 'margin': '10px 0'})
            ])
        return None

    @app.callback(
        Output('import-uploaded-files-list', 'children'),
        Input('import-file-upload', 'filename')
    )
    def update_uploaded_files_list(uploaded_files):
        print(f"Archivos subidos: {uploaded_files}")
        if uploaded_files:
            if isinstance(uploaded_files, str):
                uploaded_files = [uploaded_files]
            return html.Ul([html.Li(file) for file in uploaded_files],
                           style={'listStyleType': 'none', 'textAlign': 'left', 'width': '33%', 'margin': '10px 0'})
        return "No se subieron archivos."

    @app.callback(
        [Output('import-output-container', 'children'), Output('import-step-4', 'children')],
        Input('import-third-button', 'n_clicks'),
        State('import-importador', 'value'),
        State('import-file-upload', 'contents'),
        State('import-file-upload', 'filename'),
        State('selected-file-store', 'data'),
        prevent_initial_call=True
    )
    def execute_function_third(n_clicks, selected_value, uploaded_contents, uploaded_files, selected_filename):
        global selected_file_data, temp_campaign_options

        # Definir DATA_PATH dentro del ámbito local
        data_path = DATA_PATH

        print(f"Botón 'Tercero' clickeado: {n_clicks} veces, valor seleccionado: {selected_value}")
        triggered = callback_context.triggered
        if triggered and 'import-third-button' in triggered[0]['prop_id'] and n_clicks > 0:
            if not selected_filename:
                return html.Div([
                    html.H5("Error: No se ha seleccionado ningún archivo para guardar.",
                            style={'textAlign': 'left', 'width': '33%', 'color': 'red'})
                ]), None

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
                    result = import_RST(input_files)
                    fechas_agg = []
                    for clave in result.keys():
                        if es_fecha_isoformat(clave):
                            fechas_agg.append(clave)

                    for campaign_date, campaign_data in result.items():
                        if campaign_date != "info":
                            if selected_file_data is None:
                                selected_file_data = {}
                            else:
                                selected_file_data[campaign_date] = campaign_data
                    print('archivo json temporal almacenado')
                    print(fechas_agg)


                    for fecha in fechas_agg:
                        calcular_incrementos(selected_file_data, fecha)
                    try:
                        insertar_camp(selected_file_data, fechas_agg, selected_filename, data_path)
                    except Exception as e:
                        print(f"Error al actualizar el archivo JSON 1: {e}")

                    # Generar gráficos
                    graphs = importar_graficos(selected_file_data, fechas_agg)

                    # Generar controles de opciones
                    options_div = html.Div([
                        graphs,
                        html.Table([
                            html.Thead(html.Tr([html.Th("Fecha"), html.Th("Active"), html.Th("Quarantine"),
                                                html.Th("Subir campaña")])),
                            html.Tbody([
                                html.Tr([
                                    html.Td(fecha),
                                    html.Td(dcc.Dropdown(
                                        id={'type': 'active-dropdown', 'index': i},
                                        options=[{'label': "True", 'value': True}, {'label': "False", 'value': False}],
                                        value=True
                                    )),
                                    html.Td(dcc.Dropdown(
                                        id={'type': 'quarantine-dropdown', 'index': i},
                                        options=[{'label': "True", 'value': True}, {'label': "False", 'value': False}],
                                        value=True
                                    )),
                                    html.Td(dcc.Dropdown(
                                        id={'type': 'upload-dropdown', 'index': i},
                                        options=[{'label': "True", 'value': True}, {'label': "False", 'value': False}],
                                        value=True
                                    ))
                                ]) for i, fecha in enumerate(fechas_agg)
                            ])
                        ])
                    ])
                    temp_campaign_options = {fecha: {'Active': True, 'Quarantine': True, 'Upload': True} for fecha in
                                             fechas_agg}

                    # Generar nuevo botón "Cuarto"
                    fourth_button = html.Button("Cuarto", id='import-fourth-button', n_clicks=0,
                                                style={'display': 'block', 'margin': '10px 0'})
                    return graphs, html.Div([options_div, fourth_button])

                elif selected_value == 'Sisgeo':
                    return html.Div([html.H5("No disponible", style={'textAlign': 'left', 'width': '33%'})]), None
                else:
                    return html.Div([
                        html.H5("Opción no reconocida", style={'textAlign': 'left', 'width': '33%'})
                    ]), None
            except Exception as e:
                print(f"Error al procesar archivos: {e}")
                return html.Div([
                    html.H5(f"Error al importar: {str(e)}", style={'textAlign': 'left', 'width': '33%'})
                ]), None

        return None, None

    @app.callback(
        Output('import-output-container', 'children', allow_duplicate=True),
        Input('import-fourth-button', 'n_clicks'),
        [State({'type': 'active-dropdown', 'index': ALL}, 'value'),
         State({'type': 'quarantine-dropdown', 'index': ALL}, 'value'),
         State({'type': 'upload-dropdown', 'index': ALL}, 'value')],
        prevent_initial_call=True
    )
    def update_campaign_settings(n_clicks, active_values, quarantine_values, upload_values):
        global temp_campaign_options
        print(f"Botón 'Cuarto' clickeado: {n_clicks} veces")
        if n_clicks > 0:
            for i, fecha in enumerate(temp_campaign_options.keys()):
                temp_campaign_options[fecha]['Active'] = active_values[i]
                temp_campaign_options[fecha]['Quarantine'] = quarantine_values[i]
                temp_campaign_options[fecha]['Upload'] = upload_values[i]
            # Aqui se procesan las opciones según se requiera, como se sugiere en el paso 4
            print("Opciones de campaña actualizadas:")
            pprint.pprint(temp_campaign_options)
            return html.Div([html.H5("Campañas actualizadas correctamente", style={'color': 'green'})])
        return None

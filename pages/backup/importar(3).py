import json
import os
from dash import dcc, html, Input, Output, State, callback_context, ALL
import dash_bootstrap_components as dbc
import base64
from utils.diccionarios import importadores
from utils.funciones_comunes import import_RST, calcular_incrementos
from utils.funciones_graficos import importar_graficos
from utils.funciones_importar import insertar_camp, es_fecha_isoformat, default_value
import pprint
from datetime import datetime
import re

# Definir la ruta al directorio 'data'
data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))

# Verificar si la carpeta 'data' existe
if not os.path.exists(data_path):
    raise FileNotFoundError(f"El directorio {data_path} no existe. Verifica la estructura de tu proyecto.")

# Definición del layout
def layout():
    return html.Div([
        html.H1("Importador de inclinómetros", style={'textAlign': 'left'}), # Paso 1. Selección del tubo
        html.Div(id='import-step-1', children=[
            html.H4("Paso 1: Seleccionar archivos", style={'textAlign': 'left'}),
            dcc.Dropdown(
                id='import-file-dropdown',
                options=[
                    {'label': file, 'value': file} for file in os.listdir(data_path) if
                    os.path.isfile(os.path.join(data_path, file))
                ],
                multi=False,
                placeholder="Selecciona archivos...",
                style={'width': '33%', 'margin': '10px 0'}
            ),
            html.Button("Primero", id='import-first-button', n_clicks=0,
                        style={'display': 'block', 'margin': '10px 0'}),
            dcc.Store(id='tubo', storage_type='memory'), # lee el json y lo deja en la memoria
            dcc.Store(id='camp_added', storage_type='memory'), # campañas añadidas, con cálculos y en json
            dcc.Store(id='selected-file-store'), # a eliminar
            dcc.Store(id='selected-file-data-store')  # a eliminar
        ]),
        html.Div(id='import-step-2'), # Paso 2. Selección del importador
        html.Div(id='import-step-3'), # Paso 3. Carga de archivos de campañas
        html.Div(id='import-step-4'), # Paso 4. Calcular, graficar y selección de estado de campañas a añadir
        html.Div(id='import-step-5'), # Paso 5. Guardar los cambios en el archivo tubo seleccionado (json)
        #html.Div(id='import-output-container') # no sé para qué es esto
    ])

# Callbacks para manejar la lógica del wizard
def register_callbacks(app):
    #global selected_filename, temp_campaign_options, data_path # evitar variables globales - a quitar excepto data_path
    # Paso 2 - Selección del importador
    # callback_01 - Acciones:
    # a) Guarda el json del tubo seleccionado en memoria -- id='tubo'
    # b) Genera el siguiente paso del wizard creando:
    #    i) información del tubo
    #    ii) dropdown para seleccionar el importador
    #    iii) botón 'Segundo'
    @app.callback(
        [Output('import-step-2', 'children'), # Div del Paso 2
         Output('tubo', 'data')],
        Input('import-first-button', 'n_clicks'),
        State('import-file-dropdown', 'value'),
        prevent_initial_call=True # ver si es necesario
    )
    def display_dropdown_input(n_clicks, selected_files):
        # selected_files es el archivo cargado en el Uploader del tubo
        print(f"Botón 'Primero' clickeado: {n_clicks} veces, archivos seleccionados: {selected_files}")
        triggered = callback_context.triggered # entender qué hace esto
        if triggered and 'import-first-button' in triggered[0]['prop_id'] and n_clicks > 0:
            if selected_files:
                # Guardar el nombre del archivo seleccionado
                #selected_filename = selected_files # hace falta?
                # Leer y almacenar el archivo JSON en 'tubo'
                file_path = os.path.join(data_path, selected_files)
                try:
                    with open(file_path, 'r') as json_file:
                        tempo_tubo = json.load(json_file) # es temporal para cargar 'tubo'
                except json.JSONDecodeError as e:
                    return html.Div([
                        html.H5(
                            f"Error al leer el archivo JSON: formato incorrecto. Corrige el archivo antes de continuar.",
                            style={'textAlign': 'left', 'width': '33%', 'color': 'red'})
                    ]), selected_files
                campaign_info = default_value(selected_files, data_path) # hace falta esto? Mirar si es más fácil sacarlo directamente del diccionario
                if campaign_info:
                    default_importador_value = campaign_info.get('importador', None)
                else:
                    return html.Div([
                        html.H5("Error: No se pudo obtener información de la campaña seleccionada.",
                                style={'textAlign': 'left', 'color': 'red'})
                    ]), selected_files, selected_file_data

                return (html.Div([
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
                                style={'display': 'block', 'margin': '10px 0'})
                ]),
                        tempo_tubo,
                )
        return None, None
    # Paso 3. Carga de archivos de campañas
    # callback_02 - Acciones: crea los siguientes componentes
    # a) El upload de archivos de campaña
    # b) Un Div de texto para listar los archivos subidos (se actualiza con la callback_03)
    # c) Botón "Tercero"
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
    # callback_03 - al cargar archivos en el Upload actualiza la lista. No hace nada mas
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

    # Paso 4. Cálculo, pintado y selección de opciones de campaña
    # callback_04 - es la principal, se calculan los valores de la campaña
    # Usa las siguientes variables:
    # a) El archivo json del tubo en memoria. No hace falta modificarlo, tampoco se puede ya que tiene asignado otro Output
    # b) Los archivos cargados en el Uploader, (import-file-upload', 'contents')
    # c) Los nombres de los archivos cargados en el Uploader, ('import-file-upload', 'filename') ¿para qué?
    # d) El importador ('import-importador', 'value')
    # Acciones que realiza:
    # i) Procesa cada archivo en funcion del importador (es el mismo para todos) con al función import_xxx y lo guarda en json agregado
    # ii) Calcula cada archivo con calcular_incrementos. Esta función necesita el archivo json del tubo. ESTO SE DEBERÍA GUARDAR EN UN
    #     ARCHIVO TEMPORAL DE MEMORIA PARA USARLO EN LAS SIGUIENTES CALLBACK - NUEVO OUTPUT
    # iii) Genera los gráficos de las nuevas campañas
    # iv) Genera Div con los gráficos y las opciones seleccionables de Active, Quarentine y Subir, una línea por campaña
    # v) Guarda la selección en un diccionario
    # MODIFICARLA ENTERA, HAY QUE SUBIR LAS OPCIONES DE IMPORTADOR, DOS OUTPUT??
    @app.callback(
        [Output('import-step-4', 'children'),
         Output('camp_added', 'data')], # div con las campañas pasadas por el importador],
        Input('import-third-button', 'n_clicks'),
        State('import-importador', 'value'),
        State('import-file-upload', 'contents'),
        State('import-file-upload', 'filename'),
        State('tubo', 'data'),
        prevent_initial_call=True
    )
    def execute_function_third(n_clicks, selected_value, uploaded_contents, uploaded_files, tubo): # selected_filename_state, selected_file_data_state):
        # n_clicks - botón "Tercero"
        # 'import_importador' - importador seleccionado
        # 'import-file-upload' - archivos de campañas subidos, tanto los archivos (contents) como los nombres (filenames)
        # 'tubo' archivo json del inclinómetro

        print(f"Botón 'Tercero' clickeado: {n_clicks} veces, valor seleccionado: {selected_value}")
        triggered = callback_context.triggered
        if triggered and 'import-third-button' in triggered[0]['prop_id'] and n_clicks > 0:
            if uploaded_contents is None: # evalúa si se seleccionaron archivos
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

                    for campaign_date, campaign_data in result.items(): # no sé qué hace esto
                        if campaign_date != "info":
                            if tubo is None:
                                tubo = {}
                            else:
                                tubo[campaign_date] = campaign_data
                    print('archivo json temporal almacenado')
                    print(fechas_agg)

                    for fecha in fechas_agg:
                        calcular_incrementos(tubo, fecha) # ojo, no sé si esto devuelve tubo con los cambios

                    # Crear el nuevo diccionario 'camp_added' con solo las claves en fechas_agg
                    camp_added = {clave: tubo[clave] for clave in fechas_agg if clave in tubo}

                    # Generar gráficos
                    graphs = importar_graficos(tubo, fechas_agg)

                    # Generar controles de opciones
                    options_div = html.Div([
                        graphs,
                        html.Table([
                            html.Thead(html.Tr([html.Th("Fecha"), html.Th("Active"), html.Th("Quarentine"),
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
                                        id={'type': 'quarentine-dropdown', 'index': i},
                                        options=[{'label': "True", 'value': True}, {'label': "False", 'value': False}],
                                        value=False
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

                    # Generar nuevo botón "Cuarto"
                    fourth_button = html.Button("Cuarto", id='import-fourth-button', n_clicks=0,
                                                style={'display': 'block', 'margin': '10px 0'})
                    return html.Div([options_div, fourth_button]), camp_added

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

        return None, None#, None
    # callback_05: Guarda las campañas seleccionadas en el paso anterior en el json del inclinómetro
    # Está hecho en local, al hacerlo en TD habrá que adaptarlo
    @app.callback(
        Output('import-step-5', 'children'),
        Input('import-fourth-button', 'n_clicks'),
        [State({'type': 'active-dropdown', 'index': ALL}, 'value'),
         State({'type': 'quarentine-dropdown', 'index': ALL}, 'value'),
         State({'type': 'upload-dropdown', 'index': ALL}, 'value'),
         State('camp_added', 'data'),
         State('import-file-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_campaign_settings(n_clicks, active_values, quarentine_values, upload_values, camp_added, selected_filename):
        print(f"Botón 'Cuarto' clickeado: {n_clicks} veces")

        # Verifica que el botón se haya clickeado y que los valores existan
        if n_clicks > 0 and active_values and quarentine_values and upload_values and camp_added:
            opciones_seleccionadas = {}

            # Itera a través de las fechas en 'camp_added' y los valores de los dropdowns
            for i, fecha in enumerate(camp_added.keys()):
                opciones_seleccionadas[fecha] = {
                    'Active': active_values[i],
                    'Quarentine': quarentine_values[i],
                    'Upload': upload_values[i]
                }

            # Log para ver los valores seleccionados
            print("Opciones de campaña actualizadas:")
            pprint.pprint(opciones_seleccionadas)

            # Generar la lista 'fechas_agg' con las claves donde 'Upload' es True
            fechas_agg = [fecha for fecha, opciones in opciones_seleccionadas.items() if opciones['Upload'] == True]

            # Log para ver las fechas seleccionadas para subir
            print("Fechas seleccionadas para subir:")
            print(fechas_agg)

            # lógica para añadir las campañas al archivo json
            # debería hacerse una comprobación si se sobreescriben campañas?
            # antes actualizo la selección del usuario para active y quarentine
            for fecha, opciones in opciones_seleccionadas.items():
                # Verifica que 'fecha' esté presente en camp_added y 'campaign_info' exista
                if fecha in camp_added and 'campaign_info' in camp_added[fecha]:
                    # Actualizar los valores de 'active' y 'quarentine'
                    camp_added[fecha]['campaign_info']['active'] = opciones.get('Active', False)
                    camp_added[fecha]['campaign_info']['quarentine'] = opciones.get('Quarentine', False)
                else:
                    print(f"Error: No se encontró 'campaign_info' para la fecha {fecha} en camp_added.")
            # actualizo el archivo
            insertar_camp(camp_added, fechas_agg, selected_filename, data_path)

            return html.Div([
                html.H5("Campañas actualizadas correctamente", style={'color': 'green'}),
                html.Pre(f"Fechas seleccionadas para subir: {fechas_agg}",
                         style={'whiteSpace': 'pre-wrap', 'marginTop': '10px'})
            ])

        # Si no se cumplen las condiciones, no se hace nada
        return None

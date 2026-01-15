import json
import os
from dash import dcc, html, Input, Output, State, callback_context, ALL
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_mantine_components import Paper, Text, Group, Button, Alert, Space, Divider, Select, NumberInput, Checkbox, Card, CardSection, Stack, Grid, Col
from dash_iconify import DashIconify
import base64
from utils.diccionarios import importadores
from utils.funciones_comunes import calcular_incrementos, buscar_referencia, buscar_ant_referencia
from utils.funciones_graficos import importar_graficos
from utils.funciones_importar import import_RST, import_Sisgeo, import_soil_dux, insertar_camp, es_fecha_isoformat, \
    default_value
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
        # Título principal con estilo mejorado
        Paper(
            p="lg",
            radius="md",
            withBorder=True,
            shadow="md",
            mb=20,
            style={"backgroundColor": "#f8fbff"},
            children=[
                Group([
                    DashIconify(icon="mdi:inclinometer", width=40, c="#1976d2"),
                    Text("Importador de inclinómetros", size="xl", fw=700),
                ], position="apart"),
            ]
        ),

        # Paso 1: Selección del archivo JSON
        Paper(
            p="md",
            withBorder=True,
            shadow="md",
            radius="lg",
            mb=20,
            style={"backgroundColor": "#f8f9fa"},
            id='import-step-1',
            children=[
                Group([
                    DashIconify(icon="mdi:file-document", width=24, c="#1976d2"),
                    Text("Paso 1: Seleccionar archivo JSON base", fw=700, size="lg"),
                ], gap="1", mb=10),

                Select(
                    id='import-file-dropdown',
                    data=[
                        {"label": file, "value": file} for file in os.listdir(data_path) if
                        os.path.isfile(os.path.join(data_path, file))
                    ],
                    placeholder="Selecciona un archivo...",
                    style={'width': '100%', 'marginBottom': '15px'},
                    searchable=True,
                    clearable=True,
                    icon=DashIconify(icon="mdi:file-search")
                ),

                Button(
                    "Continuar",
                    id='import-first-button',
                    variant="filled",
                    c="blue",
                    radius="md",
                    leftSection=DashIconify(icon="mdi:arrow-right-circle")
                ),

                # Stores para datos
                dcc.Store(id='tubo', storage_type='memory'),
                dcc.Store(id='camp_added', storage_type='memory'),
                dcc.Store(id='selected-file-store'),
                dcc.Store(id='selected-file-data-store')
            ]
        ),

        # Contenedores para los siguientes pasos
        html.Div(id='import-step-2'),
        html.Div(id='import-step-3'),
        html.Div(id='import-step-4'),
        html.Div(id='import-step-5'),
    ])


# Callbacks para manejar la lógica del wizard
def register_callbacks(app):
    # Paso 2 - Selección del importador y el index_0
    @app.callback(
        [Output('import-step-2', 'children'),
         Output('tubo', 'data')],
        Input('import-first-button', 'n_clicks'),
        State('import-file-dropdown', 'value'),
        prevent_initial_call=True
    )
    def display_dropdown_input(n_clicks, selected_files):
        print(f"Botón 'Continuar' clickeado: {n_clicks} veces, archivos seleccionados: {selected_files}")
        triggered = callback_context.triggered
        if triggered and 'import-first-button' in triggered[0]['prop_id'] and n_clicks > 0:
            if selected_files:
                # Leer y almacenar el archivo JSON en 'tubo'
                file_path = os.path.join(data_path, selected_files)
                try:
                    with open(file_path, 'r') as json_file:
                        tempo_tubo = json.load(json_file)
                except json.JSONDecodeError as e:
                    return Alert(
                        title="Error de formato JSON",
                        c="red",
                        icon=DashIconify(icon="mdi:alert-circle"),
                        children=[
                            Text(
                                "Error al leer el archivo JSON: formato incorrecto. Corrige el archivo antes de continuar.")
                        ]
                    ), selected_files

                campaign_info = default_value(tempo_tubo)

                if campaign_info:
                    default_importador_value = campaign_info.get('importador', None)
                    last_index_0 = campaign_info.get('index_0', None)
                else:
                    return Alert(
                        title="Error de información",
                        c="red",
                        icon=DashIconify(icon="mdi:alert-circle"),
                        children=[
                            Text("No se pudo obtener información de la campaña seleccionada.")
                        ]
                    ), selected_files

                return Paper(
                    p="md",
                    withBorder=True,
                    shadow="md",
                    radius="lg",
                    mb=20,
                    style={"backgroundColor": "#f8f9fa"},
                    children=[
                        Group([
                            DashIconify(icon="mdi:tools", width=24, c="#1976d2"),
                            Text("Paso 2: Seleccionar importador", fw=700, size="lg"),
                        ], gap="1", mb=10),

                        # Info del inclinómetro
                        Card(
                            withBorder=True,
                            shadow="sm",
                            radius="md",
                            mb=15,
                            children=[
                                CardSection(
                                    withBorder=True,
                                    inheritPadding=True,
                                    pb="xs",
                                    children=[
                                        Group([
                                            DashIconify(icon="mdi:information", width=20, c="#1976d2"),
                                            Text("Información del inclinómetro en TD", fw=500),
                                        ], gap="1"),
                                    ]
                                ),
                                CardSection(
                                    inheritPadding=True,
                                    py="xs",
                                    children=[
                                        html.Pre(
                                            f"{pprint.pformat(campaign_info)}",
                                            style={'whiteSpace': 'pre-wrap', 'fontSize': '0.9rem', 'color': '#2c3e50'}
                                        )
                                    ]
                                )
                            ]
                        ),

                        # Selección de importador
                        Select(
                            id='import-importador',
                            data=[{"label": key, "value": value} for key, value in importadores.items()],
                            placeholder='Selecciona un importador',
                            value=default_importador_value if default_importador_value in importadores.values() else None,
                            style={'marginBottom': '15px'},
                            searchable=True,
                            clearable=False,
                            icon=DashIconify(icon="mdi:database-import")
                        ),

                        # Input para index_0
                        dmc.Grid(
                            children=[
                                dmc.Col(
                                    span=3,
                                    children=[
                                        dmc.NumberInput(
                                            id='index_0-input',
                                            value=last_index_0 if last_index_0 is not None else 1000,
                                            label="Index_0",
                                            description="Valor de referencia para posición absoluta",
                                            min=0,
                                            step=1,
                                            style={"width": "100%"}
                                        )
                                    ]
                                ),
                                dmc.Col(
                                    span=9,
                                    children=[
                                        dmc.Text(
                                            "Introduce index_0 en caso de que haya cambios respecto a la última campaña (por defecto es 1000)",
                                            c="dimmed",
                                            size="sm",
                                            mt=25
                                        )
                                    ]
                                )
                            ],
                            gutter="xs",
                            mb=15
                        ),

                        # Checkbox para referencia
                        Checkbox(
                            id="importar-checkbox-reference",
                            label="Es referencia",
                            checked=campaign_info.get('latest_campaign') is None,
                            mb=15
                        ),

                        # Botón para continuar
                        Button(
                            "Continuar",
                            id='import-second-button',
                            variant="filled",
                            c="blue",
                            radius="md",
                            leftSection=DashIconify(icon="mdi:arrow-right-circle")
                        )
                    ]
                ), tempo_tubo
        return None, None

    # Paso 3. Carga de archivos de campañas
    @app.callback(
        Output('import-step-3', 'children', allow_duplicate=True),
        Input('import-second-button', 'n_clicks'),
        State('import-importador', 'value'),
        prevent_initial_call=True
    )
    def display_upload_section(n_clicks, importador_value):
        print(f"Botón 'Continuar' clickeado: {n_clicks} veces")
        triggered = callback_context.triggered

        # Verificar si el dropdown tiene un valor seleccionado
        if not importador_value:
            return Alert(
                title="Importador no seleccionado",
                c="yellow",
                icon=DashIconify(icon="mdi:alert"),
                children=[
                    Text("Selecciona un importador para continuar")
                ]
            )

        #if triggered and 'import-second-button' in triggered[0]['prop_id'] and n_clicks > 0:
        if triggered and 'import-second-button' in triggered[0]['prop_id'] and (n_clicks is not None and n_clicks > 0):
            return Paper(
                p="md",
                withBorder=True,
                shadow="md",
                radius="lg",
                mb=20,
                style={"backgroundColor": "#f8f9fa"},
                children=[
                    Group([
                        DashIconify(icon="mdi:file-upload", width=24, c="#1976d2"),
                        Text("Paso 3: Subir archivos de campaña", fw=700, size="lg"),
                    ], gap="1", mb=10),

                    Divider(mb=15),

                    # Uploader
                    dcc.Upload(
                        id='import-file-upload',
                        multiple=True,
                        children=[
                            Paper(
                                p="md",
                                style={
                                    'textAlign': 'center',
                                    'borderStyle': 'dashed',
                                    'borderWidth': '2px',
                                    'borderRadius': '5px',
                                    'borderColor': '#cccccc',
                                    'height': '100px',
                                    'display': 'flex',
                                    'flexDirection': 'column',
                                    'justifyContent': 'center',
                                    'alignItems': 'center'
                                },
                                children=[
                                    DashIconify(icon="mdi:cloud-upload", width=40, c="#1976d2"),
                                    Text("Arrastra y suelta archivos aquí o", ta="center", mt=5),
                                    Button(
                                        "Seleccionar archivos",
                                        variant="outline",
                                        c="blue",
                                        radius="md",
                                        compact=True,
                                        mt=5
                                    )
                                ]
                            )
                        ]
                    ),

                    # Lista de archivos subidos
                    Card(
                        withBorder=True,
                        radius="md",
                        shadow="sm",
                        mt=15,
                        children=[
                            CardSection(
                                withBorder=True,
                                inheritPadding=True,
                                pb="xs",
                                children=[
                                    Group([
                                        DashIconify(icon="mdi:file-document-multiple", width=20, c="#1976d2"),
                                        Text("Archivos seleccionados", fw=500),
                                    ], gap="1"),
                                ]
                            ),
                            CardSection(
                                inheritPadding=True,
                                py="xs",
                                children=[
                                    html.Div(id='import-uploaded-files-list', style={'minHeight': '50px'})
                                ]
                            )
                        ]
                    ),

                    Button(
                        "Continuar",
                        id='import-third-button',
                        variant="filled",
                        c="blue",
                        radius="md",
                        leftSection=DashIconify(icon="mdi:arrow-right-circle"),
                        mt=15
                    )
                ]
            )
        return None

    # Actualizar la lista de archivos cargados
    @app.callback(
        Output('import-uploaded-files-list', 'children'),
        Input('import-file-upload', 'filename')
    )
    def update_uploaded_files_list(uploaded_files):
        print(f"Archivos subidos: {uploaded_files}")
        if uploaded_files:
            if isinstance(uploaded_files, str):
                uploaded_files = [uploaded_files]

            file_items = []
            for file in uploaded_files:
                file_items.append(
                    Group(
                        [
                            DashIconify(icon="mdi:file", width=16, c="#1976d2"),
                            Text(file, size="sm"),
                        ],
                        gap="1",
                        mb=5
                    )
                )
            return Stack(children=file_items)

        return Text("No se han seleccionado archivos.", c="dimmed", italic=True, size="sm")

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
    #     Dentro de la opciones para las campañas a exportar, se tiene la posibilidad de cambiar de fecha de la campaña a importar
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
        State('index_0-input', 'value'),
        State('importar-checkbox-reference', 'value'),
        prevent_initial_call=True
    )

    def execute_function_third(n_clicks, selected_value, uploaded_contents, uploaded_files, tubo, index_0, checkbox_ref_value):
        # n_clicks - botón "Tercero"
        # 'import_importador' - importador seleccionado
        # 'import-file-upload' - archivos de campañas subidos, tanto los archivos (contents) como los nombres (filenames)
        # 'tubo' archivo json del inclinómetro
        # 'index_0' referencia para la posición absoluta de cada profundidad
        # 'checkbox_ref_value' sirve para calcular la primera campaña subida como referencia (la más antigua si hay varias)

        print(f"Botón 'Tercero' clickeado: {n_clicks} veces, valor seleccionado: {selected_value}")
        triggered = callback_context.triggered

        #if triggered and 'import-third-button' in triggered[0]['prop_id'] and n_clicks > 0:
        if triggered and 'import-third-button' in triggered[0]['prop_id'] and (n_clicks is not None and n_clicks > 0):

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

                # Valores del tubo por defecto que se usan en el importador (de tubo)
                cota = tubo['info']['cota_1000']

                # Condicional dependiendo del valor seleccionado
                if selected_value == 'RST':
                    result = import_RST(input_files, index_0, cota)
                elif selected_value == 'Sisgeo':
                    result = import_Sisgeo(input_files, index_0, cota)
                elif selected_value == 'Soil (dux)':
                    result = import_soil_dux(input_files, index_0, cota)

                # elif... aquí irán el resto de importadores
                else:
                    return html.Div([
                        html.H5("Opción no reconocida", style={'textAlign': 'left', 'width': '33%'})
                    ]), None

                fechas_agg = []
                for clave in result.keys():
                    if es_fecha_isoformat(clave):
                        fechas_agg.append(clave)
                # las ordeno por si hay algo raro
                fechas_agg = sorted(fechas_agg)

                # trabaja añadiendo las campañas nuevas a tubo, que es una variable local del callback
                for campaign_date, campaign_data in result.items():
                    if campaign_date != "info":
                        if tubo is None:
                            tubo = {}
                        else:
                            tubo[campaign_date] = campaign_data
                print('archivo json temporal almacenado')
                print('fechas agregadas: ',fechas_agg)

                # calcula las variables que dependen de la referencia y la profundidades anteriores
                for fecha in fechas_agg:
                    # calcula la referencia anterior a fecha
                    fecha_referencia = buscar_referencia(tubo, fecha)

                    # referencia a aplicar al cálculo, casos de ser la primera campaña o elegirla como referencia
                    if checkbox_ref_value == 1 or not fecha_referencia :
                        # la fecha más antigua de los archivos seleccionados será la fecha_referencia
                        fecha_referencia = fechas_agg[0]
                        # añado la información al diccionario de la campaña
                        if fecha == fecha_referencia:
                            tubo[fecha_referencia]["campaign_info"]["reference"] = True

                    # calcula la campaña activa anterior a la última referencia
                    #fecha_ant_referencia = buscar_ant_referencia(tubo, fecha_referencia) if fecha_referencia else None # esto parece que sobra
                    # llama a la función para calcular la variables dependientes, devuelve tubo con ellas añadidas
                    print ('antes de incrementos')
                    calcular_incrementos(tubo, fecha, fecha_referencia) # función externa utils/funciones_comunes.py
                    print ('después de incrementos ')

                # Crear el nuevo diccionario 'camp_added' con solo las claves en fechas_agg
                camp_added = {clave: tubo[clave] for clave in fechas_agg if clave in tubo}

                # Generar gráficos
                graphs = importar_graficos(tubo, fechas_agg)
                # https://www.dash-mantine-components.com/components/timeinput
                # Generar controles de opciones
                options_div = html.Div([
                    graphs,
                    html.Table([
                        html.Thead(html.Tr([
                            html.Th("Fecha", style={'width': '20%'}),
                            html.Th("Fecha Tunneldata", style={'width': '20%'}),
                            html.Th("Hora Tunneldata", style={'width': '20%'}),
                            html.Th("Active", style={'width': '10%', 'padding-left': '4%'}),
                            html.Th("Quarentine", style={'width': '10%'}),
                            html.Th("Subir Campaña", style={'width': '10%'})
                        ])),
                        html.Tbody([
                            html.Tr([
                                html.Td(fecha, style={'padding': '0.25%', 'vertical-align': 'middle'}),
                                html.Td(dcc.DatePickerSingle(
                                    id={'type': 'date-picker', 'index': i},
                                    date=fecha.split('T')[0],
                                    display_format='YYYY-MM-DD',
                                    style={'height': '38px', 'width': '90%', 'vertical-align': 'right'}
                                ), style={'padding': '0.1%', 'vertical-align': 'middle'}),
                                html.Td(dcc.Input(
                                    id={'type': 'time-input', 'index': i},
                                    type='text',
                                    value=fecha.split('T')[1],
                                    debounce=True,
                                    placeholder="HH:MM:SS",
                                    style={'height': '38px', 'width': '50%', 'vertical-align': 'left'}
                                ), style={'padding': '0.1%', 'vertical-align': 'middle'}),
                                html.Td(dcc.Dropdown(
                                    id={'type': 'active-dropdown', 'index': i},
                                    options=[{'label': "True", 'value': True}, {'label': "False", 'value': False}],
                                    value=True,
                                    style={'height': '38px', 'width': '90%', 'vertical-align': 'middle'}
                                ), style={'padding': '1%', 'vertical-align': 'middle'}),
                                html.Td(dcc.Dropdown(
                                    id={'type': 'quarentine-dropdown', 'index': i},
                                    options=[{'label': "True", 'value': True}, {'label': "False", 'value': False}],
                                    value=False,
                                    style={'height': '38px', 'width': '90%', 'vertical-align': 'middle'}
                                ), style={'padding': '1%', 'vertical-align': 'middle'}),
                                html.Td(dcc.Dropdown(
                                    id={'type': 'upload-dropdown', 'index': i},
                                    options=[{'label': "True", 'value': True}, {'label': "False", 'value': False}],
                                    value=True,
                                    style={'height': '38px', 'width': '90%', 'vertical-align': 'middle'}
                                ), style={'padding': '1%', 'vertical-align': 'middle'})
                            ]) for i, fecha in enumerate(fechas_agg)
                        ])
                    ])
                ])

                # Generar nuevo botón "Cuarto"
                fourth_button = html.Button("Cuarto", id='import-fourth-button', n_clicks=0,
                                            style={'display': 'block', 'margin': '10px 0'})
                return html.Div([options_div, fourth_button]), camp_added

            except Exception as e:
                print(f"Error al procesar archivos: {e}")
                return html.Div([
                    html.H5(f"Error al importar: {str(e)}", style={'textAlign': 'left', 'width': '33%'})
                ]), None

        return None, None

    # callback_05: Guarda las campañas seleccionadas en el paso anterior en el json del inclinómetro
    # Está hecho en local, al hacerlo en TD habrá que adaptarlo
    @app.callback(
        Output('import-step-5', 'children'),
        Input('import-fourth-button', 'n_clicks'),
        [State({'type': 'date-picker', 'index': ALL}, 'date'),
         State({'type': 'time-input', 'index': ALL}, 'value'),
         State({'type': 'active-dropdown', 'index': ALL}, 'value'),
         State({'type': 'quarentine-dropdown', 'index': ALL}, 'value'),
         State({'type': 'upload-dropdown', 'index': ALL}, 'value'),
         State('camp_added', 'data'),
         State('import-file-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_campaign_settings(n_clicks, dates, times, active_values, quarentine_values, upload_values, camp_added, selected_filename):
        print(f"Botón 'Cuarto' clickeado: {n_clicks} veces")

        # Verifica que el botón se haya clickeado y que los valores existan
        if n_clicks > 0 and active_values and quarentine_values and upload_values and dates and times and camp_added:
            opciones_seleccionadas = {}

            # Cambiar las keys de camp_added por las fechas formateadas
            camp_added_formateado = {}
            for i, fecha in enumerate(camp_added.keys()):
                # Combinar la fecha y hora del DatePicker y del Input de hora
                fecha_hora_str = f"{dates[i]}T{times[i]}"
                # Convertir al formato datetime
                fecha_hora = datetime.strptime(fecha_hora_str, "%Y-%m-%dT%H:%M:%S")
                # Formatear al formato requerido
                fecha_hora_formateada = fecha_hora.strftime("%Y-%m-%dT%H:%M:%S")
                # Actualizar el nuevo diccionario con la fecha formateada como clave
                camp_added_formateado[fecha_hora_formateada] = camp_added[fecha]

            # Itera a través de las fechas en 'camp_added' y los valores de los dropdowns
            for i, fecha in enumerate(camp_added_formateado.keys()):
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
                if fecha in camp_added_formateado and 'campaign_info' in camp_added_formateado[fecha]:
                    # Actualizar los valores de 'active' y 'quarentine'
                    camp_added_formateado[fecha]['campaign_info']['active'] = opciones.get('Active', False)
                    camp_added_formateado[fecha]['campaign_info']['quarentine'] = opciones.get('Quarentine', False)
                else:
                    print(f"Error: No se encontró 'campaign_info' para la fecha {fecha} en camp_added.")
            # actualizo el archivo
            insertar_camp(camp_added_formateado, fechas_agg, selected_filename, data_path)

            return html.Div([
                html.H5("Campañas actualizadas correctamente", style={'color': 'green'}),
                html.Pre(f"Fechas seleccionadas para subir: {fechas_agg}",
                         style={'whiteSpace': 'pre-wrap', 'marginTop': '10px'})
            ])

        # Si no se cumplen las condiciones, no se hace nada
        return None

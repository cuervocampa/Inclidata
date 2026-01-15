import json
import os
import dash
from dash.exceptions import PreventUpdate
from dash import dcc, html, Input, Output, State, callback_context, ALL
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_mantine_components import (
    Paper, Text, Group, Button, Alert, Space, Divider, Select, NumberInput, Checkbox,
    Card, CardSection, Stack, Grid)
from dash_iconify import DashIconify
import base64
from utils.diccionarios import importadores
from utils.funciones_comunes import calcular_incrementos, buscar_referencia, buscar_ant_referencia, evaluar_umbrales
from utils.funciones_graficos import importar_graficos
from utils.funciones_importar import import_RST, import_Sisgeo, import_soil_dux, insertar_camp, es_fecha_isoformat, \
    default_value, parse_alarm_val
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
                    DashIconify(icon="mdi:inclinometer", width=40, color="#1976d2"),
                    Text("Importador de inclinómetros", size="xl", fw=700),
                ], justify="flex-start"),
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
                    DashIconify(icon="mdi:file-document", width=24, color="#1976d2"),
                    Text("Paso 1: Seleccionar archivo JSON base", fw=700, size="lg"),
                ], gap="xs", mb=10),

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
                    leftSection=DashIconify(icon="mdi:file-search")  # v2: icon -> leftSection
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
                            DashIconify(icon="mdi:tools", width=24, color="#1976d2"),
                            Text("Paso 2: Seleccionar importador", fw=700, size="lg"),
                        ], gap="xs", mb=10),

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
                                            DashIconify(icon="mdi:information", width=20, color="#1976d2"),
                                            Text("Información del inclinómetro en TD", fw=500),
                                        ], gap="xs"),
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
                            leftSection=DashIconify(icon="mdi:database-import")  # v2: icon -> leftSection
                        ),

                        # Input para index_0
                        dmc.Grid(
                            children=[
                                dmc.GridCol(
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
                                dmc.GridCol(
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
                        DashIconify(icon="mdi:file-upload", width=24, color="#1976d2"),
                        Text("Paso 3: Subir archivos de campaña", fw=700, size="lg"),
                    ], gap="xs", mb=10),

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
                                    DashIconify(icon="mdi:cloud-upload", width=40, color="#1976d2"),
                                    Text("Arrastra y suelta archivos aquí o", ta="center", mt=5),
                                    Button(
                                        "Seleccionar archivos",
                                        variant="outline",
                                        c="blue",
                                        radius="md",
                                        size="sm",  # v2: sustituye a compact=True
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
                                        DashIconify(icon="mdi:file-document-multiple", width=20, color="#1976d2"),
                                        Text("Archivos seleccionados", fw=500),
                                    ], gap="xs"),
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
                            DashIconify(icon="mdi:file", width=16, color="#1976d2"),
                            Text(file, size="sm"),
                        ],
                        gap="xs",
                        mb=5
                    )
                )
            return Stack(children=file_items)

        return Text("No se han seleccionado archivos.", c="dimmed", fs="italic", size="sm")  # v2: fs en lugar de italic

    # Paso 4. Cálculo, pintado y selección de opciones de campaña
    # callback_04 - es la principal, se calculan los valores de la campaña
    @app.callback(
        [Output('import-step-4', 'children'),
         Output('camp_added', 'data')],
        Input('import-third-button', 'n_clicks'),
        [State('import-importador', 'value'),
        State('import-file-upload', 'contents'),
        State('import-file-upload', 'filename'),
        State('tubo', 'data'),
        State('index_0-input', 'value'),
        State('importar-checkbox-reference', 'checked')],
        prevent_initial_call=True
    )
    def execute_function_third(n_clicks, selected_value, uploaded_contents, uploaded_files, tubo, index_0, checkbox_ref_value):

        print(f"Botón 'Continuar' clickeado: {n_clicks} veces, importador seleccionado: {selected_value}")
        triggered = callback_context.triggered

        if triggered and 'import-third-button' in triggered[0]['prop_id'] and (
                n_clicks is not None and n_clicks > 0):
            if uploaded_contents is None:
                return Alert(
                    title="Error de carga",
                    c="red",
                    icon=DashIconify(icon="mdi:alert-circle"),
                    children=[
                        Text("No se ha seleccionado ningún archivo para procesar.")
                    ]
                ), None

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

                # Valores del tubo por defecto que se usan en el importador
                cota = tubo['info']['cota_1000'] # la cota se define en el archivo de configuración json

                # Condicional dependiendo del importador seleccionado
                if selected_value == 'RST':
                    result = import_RST(input_files, index_0, cota)
                elif selected_value == 'Sisgeo':
                    result = import_Sisgeo(input_files, index_0, cota)
                elif selected_value == 'Soil (dux)':
                    result = import_soil_dux(input_files, index_0, cota)
                else:
                    return Alert(
                        title="Importador no reconocido",
                        c="red",
                        icon=DashIconify(icon="mdi:alert-circle"),
                        children=[
                            Text("El importador seleccionado no está implementado.")
                        ]
                    ), None

                fechas_agg = []
                for clave in result.keys():
                    if es_fecha_isoformat(clave):
                        fechas_agg.append(clave)
                # Ordenar fechas
                fechas_agg = sorted(fechas_agg)

                # Añadir las campañas nuevas a tubo
                for campaign_date, campaign_data in result.items():
                    if campaign_date != "info":
                        if tubo is None:
                            tubo = {}
                        else:
                            tubo[campaign_date] = campaign_data
                print('Archivo JSON temporal almacenado')
                print('Fechas agregadas: ', fechas_agg)

                # Calcular las variables que dependen de la referencia y las profundidades anteriores
                # se inicializa fecha_referencia para el caso de la primera carga
                primera_fecha = fechas_agg[0]
                for fecha in fechas_agg:
                    # Si es referencia, se añade a la información de la campaña
                    if checkbox_ref_value == True and fecha == primera_fecha:
                        tubo[fecha]["campaign_info"]["reference"] = True
                    else:
                        tubo[fecha]["campaign_info"]["reference"] = False
                    # Calcular la referencia anterior a fecha
                    fecha_referencia = buscar_referencia(tubo, fecha)


                    calcular_incrementos(tubo, fecha, fecha_referencia)

                # Crear el nuevo diccionario 'camp_added' con solo las claves en fechas_agg
                camp_added = {clave: tubo[clave] for clave in fechas_agg if clave in tubo}

                # Evaluar umbrales para cada campaña
                umbrales = tubo.get('umbrales', {
                    'deformadas': {},
                    'valores': []
                })

                # Solo evaluar umbrales si existe la estructura completa
                if umbrales.get('deformadas') and umbrales.get('valores'):
                    eval_por_fecha = {fecha: evaluar_umbrales(tubo[fecha]['calc'], umbrales)
                                      for fecha in fechas_agg
                                      }
                else:
                    # Valores por defecto si no hay umbrales configurados
                    eval_por_fecha = {fecha: None for fecha in fechas_agg}

                print ("paso intermedio de eval ", eval_por_fecha)

                # Generar gráficos
                graphs = importar_graficos(tubo, fechas_agg)

                # Encabezados para la tabla de configuración
                header = Grid([
                    dmc.GridCol(span=2, children=[Text("Fecha Original", fw=700, size="sm")]),
                    dmc.GridCol(span=1, children=[Text("Fecha TunnelData", fw=700, size="sm")]),
                    dmc.GridCol(span=1, children=[Text("Hora TunnelData", fw=700, size="sm")]),
                    dmc.GridCol(span=1, children=[Text("Activa", fw=700, size="sm")]),
                    dmc.GridCol(span=1, children=[Text("Cuarentena", fw=700, size="sm")]),
                    dmc.GridCol(span=4, children=[Text("Alarm", fw=700, size="sm")]),
                    dmc.GridCol(span=2, children=[Text("Subir Campaña", fw=700, size="sm")])
                ], gutter="xs", mb=10, ta="center")

                # Filas de configuración
                campaign_config_rows = []
                for i, fecha in enumerate(fechas_agg):
                    campaign_config_rows.append(
                        Grid([
                            dmc.GridCol(span=2, children=[Text(fecha, size="sm", fw=500)]),
                            dmc.GridCol(span=1, children=[
                                dmc.TextInput(
                                    id={'type': 'date-input', 'index': i},
                                    value=datetime.strptime(fecha, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d"),
                                    placeholder="YYYY-MM-DD",
                                    size="sm", style={"width": "100%"}, type="text"
                                )
                            ]),
                            dmc.GridCol(span=1, children=[
                                dmc.TimeInput(
                                    id={'type': 'time-input', 'index': i},
                                    value=datetime.strptime(fecha.split('T')[1], "%H:%M:%S").strftime("%H:%M:%S"),  # v2: string
                                    size="sm", style={"width": "100%"}
                                )
                            ]),
                            dmc.GridCol(span=1, children=[
                                Select(
                                    id={'type': 'active-dropdown', 'index': i},
                                    data=[{"label": "Activo", "value": True},
                                          {"label": "Inactivo", "value": False}],
                                    value=True, size="sm", style={"width": "100%"}
                                )
                            ]),
                            dmc.GridCol(span=1, children=[
                                Select(
                                    id={'type': 'quarentine-dropdown', 'index': i},
                                    data=[{"label": "En cuarentena", "value": True},
                                          {"label": "Normal", "value": False}],
                                    value=False, size="sm", style={"width": "100%"}
                                )
                            ]),
                            dmc.GridCol(span=4, children=[
                                dmc.TextInput(
                                    id = {'type': 'alarm-input', 'index': i},
                                    value = str(eval_por_fecha[fecha]),
                                    size = "sm",
                                    style = {"width": "100%"},
                                    disabled = True)
                            ]),
                            dmc.GridCol(span=2, children=[
                                Select(
                                    id={'type': 'upload-dropdown', 'index': i},
                                    data=[{"label": "Subir", "value": True},
                                          {"label": "Ignorar", "value": False}],
                                    value=True, size="sm", style={"width": "100%"}
                                )
                            ])
                        ], gutter="xs", mb=10, ta="center")
                    )

                return (
                    Paper(
                        p="md", withBorder=True, shadow="md", radius="lg", mb=20,
                        style={"backgroundColor": "#f8f9fa"},
                        children=[
                            Group([
                                DashIconify(icon="mdi:clipboard-check", width=24, color="#1976d2"),
                                Text("Paso 4: Configurar campañas importadas", fw=700, size="lg"),
                            ], gap="xs", mb=10),
                            # Gráficos
                            Card(
                                withBorder=True, shadow="sm", radius="md", mb=15,
                                children=[
                                    CardSection(
                                        withBorder=True, inheritPadding=True, pb="xs",
                                        children=[
                                            Group([
                                                DashIconify(icon="mdi:chart-line", width=20, color="#1976d2"),
                                                Text("Visualización de campañas", fw=500),
                                            ], gap="xs"),
                                        ]
                                    ),
                                    CardSection(inheritPadding=True, py="xs", children=[graphs])
                                ]
                            ),
                            # Tabla de configuración
                            Card(
                                withBorder=True, shadow="sm", radius="md", mb=15,
                                children=[
                                    CardSection(
                                        withBorder=True, inheritPadding=True, pb="xs",
                                        children=[
                                            Group([
                                                DashIconify(icon="mdi:table-settings", width=20, color="#1976d2"),
                                                Text("Configuración de campañas", fw=500),
                                            ], gap="xs"),
                                        ]
                                    ),
                                    CardSection(inheritPadding=True, py="xs", children=[
                                        header,
                                        Divider(mb=10),
                                        Stack(children=campaign_config_rows)
                                    ])
                                ]
                            ),
                            Button(
                                "Guardar campañas",
                                id='import-fourth-button',
                                variant="filled",
                                c="blue",
                                radius="md",
                                leftSection=DashIconify(icon="mdi:content-save"),
                                mt=10
                            )
                        ]
                    ),
                    camp_added
                )

            except Exception as e:
                print(f"Error al procesar archivos: {e}")
                import traceback; traceback.print_exc()
                return (
                    Alert(
                        title="Error al procesar archivos",
                        c="red",
                        icon=DashIconify(icon="mdi:alert-circle"),
                        children=[Text(f"Se produjo un error: {e}")]
                    ),
                    None
                )
        return None, None

    # Paso 5: Guardar las campañas seleccionadas
    @app.callback(
        Output('import-step-5', 'children'),
        Input('import-fourth-button', 'n_clicks'),
        [State({'type': 'date-input', 'index': ALL}, 'value'),
         State({'type': 'time-input', 'index': ALL}, 'value'),
         State({'type': 'active-dropdown', 'index': ALL}, 'value'),
         State({'type': 'quarentine-dropdown', 'index': ALL}, 'value'),
         State({'type': 'upload-dropdown', 'index': ALL}, 'value'),
         State({'type': 'alarm-input', 'index': ALL}, 'value'),
         State('camp_added', 'data'),
         State('import-file-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_campaign_settings(
        n_clicks,
        dates,
        times,
        active_values,
        quarentine_values,
        upload_values,
        alarm_values,             # ← Añadido
        camp_added,
        selected_filename
    ):
        print("alarm_values:", alarm_values)
        print(f"Botón 'Guardar campañas' clickeado: {n_clicks} veces")

        if n_clicks is None:
            raise dash.exceptions.PreventUpdate

        print("active values", active_values)
        print("quarentine_values", quarentine_values)
        print("upload_values", upload_values)
        print("dates", dates)
        print("times", times)

        if n_clicks and dates and times and camp_added:
            opciones_seleccionadas = {}

            # Cambiar keys de camp_added por fechas formateadas
            camp_added_formateado = {}
            for i, fecha in enumerate(camp_added.keys()):
                try:
                    fecha_hora_str = f"{dates[i]}T{times[i]}"
                    fecha_hora = datetime.strptime(fecha_hora_str, "%Y-%m-%dT%H:%M:%S")
                    fecha_hora_fmt = fecha_hora.strftime("%Y-%m-%dT%H:%M:%S")
                    camp_added_formateado[fecha_hora_fmt] = camp_added[fecha]
                except Exception as e:
                    print(f"Error al formatear fecha {fecha}: {e}")
                    return Alert(
                        title="Error al formatear fechas",
                        c="red",
                        icon=DashIconify(icon="mdi:alert-circle"),
                        children=[Text(f"Error al procesar la fecha {fecha}: {e}")]
                    )

            # Asignar alarma desde alarm_values
            for i, fecha in enumerate(camp_added_formateado.keys()):
                camp_added_formateado[fecha]['campaign_info']['alarm'] = parse_alarm_val(alarm_values[i])

            # Iterar para active/quarentine/upload
            for i, fecha in enumerate(camp_added_formateado.keys()):
                opciones_seleccionadas[fecha] = {
                    'Active':     active_values[i],
                    'Quarentine': quarentine_values[i],
                    'Upload':     upload_values[i]
                }

            print("Opciones de campaña actualizadas:")
            pprint.pprint(opciones_seleccionadas)

            fechas_agg = [f for f, opt in opciones_seleccionadas.items() if opt['Upload']]
            print("Fechas seleccionadas para subir:", fechas_agg)

            # Actualizar campaign_info con active y quarentine
            for fecha, opt in opciones_seleccionadas.items():
                if fecha in camp_added_formateado and 'campaign_info' in camp_added_formateado[fecha]:
                    ci = camp_added_formateado[fecha]['campaign_info']
                    ci['active']     = opt['Active']
                    ci['quarentine'] = opt['Quarentine']
                else:
                    print(f"Error: No se encontró 'campaign_info' para la fecha {fecha}.")

            insertar_camp(camp_added_formateado, fechas_agg, selected_filename, data_path)

            return html.Div([
                html.H5("Campañas actualizadas correctamente", style={'color': 'green'}),
                html.Pre(f"Fechas seleccionadas para subir: {fechas_agg}",
                         style={'whiteSpace': 'pre-wrap', 'marginTop': '10px'})
            ])

        return None

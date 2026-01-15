from dash import html, dcc, callback_context
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
from dash_ag_grid import AgGrid
import dash
import base64, json
from icecream import ic
from datetime import datetime, timedelta
import plotly.graph_objs as go
import re
import pandas as pd
from sqlalchemy import false


#from TD_medias.vol_td.main import height
from utils.funciones_comunes import get_color_for_index, buscar_referencia, calcular_incrementos
from utils.funciones_correcciones import grafico_violines, dict_a_df

# Layout function
def layout():
    return dmc.MantineProvider(
        children=dmc.Grid([
            html.Div(style={'height': '50px'}),

            # Upload section
            dmc.Group(
                children=[
                    dmc.Col(
                        dcc.Upload(
                            id='archivo-uploader',
                            multiple=False,
                            accept='.json',
                            children=['Drag and Drop o seleccionar archivo'],
                            style={
                                'flexShrink': 1,  # Permite que el componente se reduzca si no hay suficiente espacio
                                'width': '100%', 'height': '60px', 'lineHeight': '60px', 'borderWidth': '2px',
                                'borderStyle': 'dashed', 'borderRadius': '5px', 'borderColor': 'blue',
                                'textAlign': 'center', 'margin': '10px 0', 'display': 'flex',
                                'justifyContent': 'center',
                                'alignItems': 'center', 'color': 'red'
                            }
                        ),
                        span=3
                    ),
                    dmc.Col(
                        html.Div(id='informacion-archivo', style={'width': '100%', 'display':'flex', 'alignItems': 'center','height': '100%'}),
                        span=3
                    ),
                    dmc.Col(
                        html.Div(
                            children=[
                                html.B('Campaña a Graficar: '),
                                dmc.Select(
                                    id='camp_a_graficar',
                                    placeholder='Selecciona una fecha',
                                    value= None,  # Valor por defecto será actualizado en el callback
                                    clearable=False,
                                    data=[]  # Inicialmente vacío, será llenado por el callback
                                )
                            ],
                            style={'width': '100%', 'display': 'flex','justifyContent': 'flex-start', 'alignItems': 'center', 'gap': '20px'}
                        ),
                        span=4
                    )
                ],
                style={'width': '100%'},noWrap=True  # Evitar que los elementos hagan salto de línea
            ),
            dcc.Store(id='corregir-tubo', storage_type='memory'),  # archivo json, se parte del original y se incorporan modificaciones
            dcc.Store(id='corregir_archivo', storage_type='memory'),  # nombre del archivo json. Pensado para funcionamiento en local
            dcc.Store(id='camp_corregida', storage_type='memory'), # nombre del archivo json. Campaña seleccionada con las correcciones
            dcc.Store(id='tabla_inicial', data={}, storage_type='memory'),  # tabla resumen de campañas de 'corregir-tubo'
            dcc.Store(id='log_cambios', data={}, storage_type='memory'),  # interacciones que se van haciendo en la tabla
            dcc.Store(id='cambios_a_realizar', data={}, storage_type='memory'),  # modificaciones que se van haciendo sobre corregir-tubo

            # Table and Info Section
            dmc.Grid(
                children=[
                    dmc.Col(
                        AgGrid(
                            id='tabla-json',
                            style={
                                'height': '200px', 'width': '100%', 'margin': '0 auto'
                            },
                            columnDefs=[
                                {'headerName': 'Fecha', 'field': 'Fecha', 'editable': False, 'resizable': True},
                                {'headerName': 'Referencia', 'field': 'Referencia', 'editable': True,
                                 'cellEditor': 'agSelectCellEditor', 'cellEditorParams': {'values': [True, False]}, 'resizable': True},
                                {'headerName': 'Activa', 'field': 'Activa', 'editable': True,
                                 'cellEditor': 'agSelectCellEditor', 'cellEditorParams': {'values': [True, False]}, 'resizable': True},
                                {'headerName': 'Cuarentena', 'field': 'Cuarentena', 'editable': True,
                                 'cellEditor': 'agSelectCellEditor', 'cellEditorParams': {'values': [True, False]}, 'resizable': True},
                                {'headerName': 'Correc Spike', 'field': 'spike', 'editable': False, 'resizable': True},
                                {'headerName': 'Correc Bias', 'field': 'bias', 'editable': False, 'resizable': True},
                                {'headerName': 'Limpiar', 'field': 'Limpiar', 'editable': True, 'cellEditor': 'agCheckboxCellEditor', 'resizable': True},
                            ],
                            defaultColDef={
                                'flex': 1,  # Ajustar el ancho de las columnas para que ocupen el ancho disponible
                                'minWidth': 100,  # Ancho mínimo de cada columna
                                'resizable': True,
                                'wrapHeaderText': True,  # Ajuste automático de encabezado si es necesario
                                'autoSizeAllColumns': True  # Ajustar automáticamente todas las columnas
                            },
                            rowData=[],  # Inicialmente vacío
                            columnSize='responsiveSizeToFit' # Ajustar el tamaño de las columnas automáticamente para evitar scroll horizontal
                        ),
                        span=8
                    ),
                    dmc.Col(
                        children=[
                            html.Div(id='log-cambios',
                                     style={'height': '200px', 'overflowY': 'auto', 'border': '1px solid #ccc', 'padding': '10px'}),
                            dmc.Group(
                                children=[
                                    dmc.Button("Recalcular Tabla", id='recalcular_tabla', variant='outline', c='blue'),
                                    dmc.Button("Guardar Tabla", id='guardar_tabla', variant='outline', c='green')
                                ],
                                style={'marginTop': '10px'}
                            )
                        ],
                        span=4
                    )
                ],
                style={'width': '100%'}
            ),
            # Gráficos del incli - GRAFICO 1

            dmc.Divider(style={"marginTop": "50px", "marginBottom": "20px"}),
            dmc.Grid([
                dmc.Col(  # gráficos de desplazamientos vs profunfidadad
                    dmc.Tabs([
                        dmc.TabsList([
                            dmc.Tab("Desplazamientos", value="corr_grafico1", style={'fontWeight': 'bold', 'fontSize': '1.1rem'}),
                            dmc.Tab("Incrementales", value="corr_grafico2", style={'fontWeight': 'bold', 'fontSize': '1.1rem'}),
                            dmc.Tab("Despl. compuestos", value="corr_grafico3", style={'fontWeight': 'bold', 'fontSize': '1.1rem'})
                        ]),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.Col([
                                        dcc.Graph(id='corr_grafico_incli_1_a'),
                                        dmc.Text("Desplazamiento A", ta="center")], span=6, style={'padding': '0', 'margin': '0'}),
                                    dmc.Col([
                                        dcc.Graph(id='corr_grafico_incli_1_b'),
                                        dmc.Text("Desplazamiento B", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0'}),
                                ])
                            ]),
                            value="corr_grafico1"
                        ),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.Col([
                                        dcc.Graph(id='corr_grafico_incli_2_a'),
                                        dmc.Text("Incremental A", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0'}),
                                    dmc.Col([
                                        dcc.Graph(id='corr_grafico_incli_2_b'),
                                        dmc.Text("Incremental B", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0'}),
                                ])
                            ]),
                            value="corr_grafico2"
                        ),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.Col([
                                        dcc.Graph(id='corr_grafico_incli_3_a'),
                                        dmc.Text("Desplazamiento A", ta="center")],
                                        span=4, style={'padding': '0', 'margin': '0'}),
                                    dmc.Col([
                                        dcc.Graph(id='corr_grafico_incli_3_b'),
                                        dmc.Text("Desplazamiento B", ta="center")],
                                        span=4, style={'padding': '0', 'margin': '0'}),
                                    dmc.Col([
                                        dcc.Graph(id='corr_grafico_incli_3_total'),
                                        dmc.Text("Desplazamientos Totales", ta="center")
                                    ], span=4, style={'padding': '0', 'margin': '0'}),
                                ])
                            ]),
                            value="corr_grafico3"
                        )
                    ], value="corr_grafico1"),
                    span=10  # Ocupa el 70% de la fila
                ),

                dmc.Col([
                    html.Div(style={'height': '50px'}),  # Espacio al comienzo
                    dmc.Group(
                        [
                            dmc.Button("Configuración", id="correc-open-drawer-1", n_clicks=None, fullWidth=True),
                            #dmc.Button("Configuración", id="open-config-drawer", n_clicks=None, fullWidth=True)
                        ],
                        style={'display': 'flex', 'flexDirection': 'column'},
                        gap="1"  # Espaciamiento entre botones
                    ),
                ], span=2)  # Ocupa el 30% de la fila
            ], style={"width": "100%"}),
            # drawer con la configuración del GRAFICO 1: correc-drawer-1
            dmc.Drawer(
                title=dmc.Text("Configuración gráficos", fw="bold", size="xl", style={"marginBottom": "20px"}),
                id="correc-drawer-1",
                children=[
                    dmc.Text("Seleccionar altura de gráficos", fw="bold", style={"marginBottom": "10px"}),
                    dmc.Slider(
                        label="Altura de los gráficos (px)",
                        id="corr_alto_graficos_slider_grafico1",
                        min=400,
                        max=1000,
                        step=100,
                        value=800,
                        marks=[
                            {"value": 400, "label": "400"},
                            {"value": 500, "label": "500"},
                            {"value": 600, "label": "600"},
                            {"value": 700, "label": "700"},
                            {"value": 800, "label": "800"},
                            {"value": 900, "label": "900"},
                            {"value": 1000, "label": "1000"},
                        ],
                        style={"marginBottom": "50px"}
                    ),
                    dmc.Text("Seleccionar estilo de colores", fw="bold", style={"marginBottom": "10px"}),
                    dmc.RadioGroup(
                        id="correcciones_color_grafico1",
                        value="monocromo",  # Valor por defecto
                        children=[
                            dmc.Radio("Monocromo", value="monocromo", style={"marginRight": "20px"}),
                            dmc.Radio("Multicromo", value="multicromo", style={"marginRight": "20px"}),
                        ],
                        style={"marginBottom": "30px", "width": "100%", "display": "flex",
                               "flexDirection": "row", "marginRight": "50px"}
                    ),
                    # insertar número de campañas previas a graficar
                    dmc.Group(
                        children=[
                            dmc.Text("Campañas previas a mostrar", fw="bold", style={"marginBottom": "10px", "flex": "2"}),
                            dmc.NumberInput(
                                id="correc_num_camp_previas_grafico1",
                                value=3,  # Valor por defecto
                                min=0,
                                max=100,
                                step=1,
                                disabled=False,
                                style={"flex": "1"}
                            )
                        ],
                        style={"width": "100%", "alignItems": "center", "justifyContent": "space-between"}
                    ),
                    html.Div(style={'height': '20px'}),  # Espaciado
                    # Component for "Escala gráficos desplazamiento"
                    dmc.Text("Escala gráficos Desplazamiento", fw="bold", style={"marginBottom": "10px"}),
                    dmc.RadioGroup(
                        # label="Escala gráficos desplazamiento",
                        id="correc_escala_graficos_desplazamiento",
                        value="manual",
                        children=[
                            dmc.Radio("Automática", value="automatica", style={"marginBottom": "10px"}),
                            dmc.Radio("Manual", value="manual", style={"marginBottom": "10px"})
                        ],
                        style={"marginBottom": "20px"}
                    ),
                    # Escala manual gráficos de desplazamiento grafico_1 y grafico_3
                    dmc.Group(
                        [
                            dmc.Text("Max", style={"width": "30px"}),
                            dmc.NumberInput(
                                id="correc_valor_positivo_desplazamiento",
                                value=10,
                                min=-1000,
                                max=1000,
                                step=5,
                                disabled=True,
                                style={"flex": 1},
                            ),
                            dmc.Text("Min", style={"width": "30px", "marginLeft": "10px"}),
                            dmc.NumberInput(
                                id="correc_valor_negativo_desplazamiento",
                                value=-10,
                                min=-1000,
                                max=1000,
                                step=5,
                                disabled=True,
                                style={"flex": 1},
                            ),
                        ],
                        ta="center",
                        gap="1",
                        style={"width": "100%"},
                    ),
                    # Component for "Escala gráficos incremento"
                    dmc.Text("Escala gráficos Incremento", fw="bold", style={"marginBottom": "10px"}),
                    dmc.RadioGroup(
                        # label="Escala gráficos incremento",
                        id="correc_escala_graficos_incremento",
                        value="manual",
                        children=[
                            dmc.Radio("Automática", value="automatica", style={"marginBottom": "10px"}),
                            dmc.Radio("Manual", value="manual", style={"marginBottom": "10px"})
                        ],
                        style={"marginBottom": "20px"}
                    ),
                    # Escala manual gráficos de incremento grafico_2
                    dmc.Group(
                        [
                            dmc.Text("Max", style={"width": "30px"}),
                            dmc.NumberInput(
                                id="correc_valor_positivo_incremento",
                                value=1,
                                min=-1000,
                                max=1000,
                                step=1,
                                disabled=True,
                                style={"flex": 1},
                            ),
                            dmc.Text("Min", style={"width": "30px", "marginLeft": "10px"}),
                            dmc.NumberInput(
                                id="correc_valor_negativo_incremento",
                                value=-1,
                                min=-1000,
                                max=1000,
                                step=1,
                                disabled=True,
                                style={"flex": 1},
                            ),
                        ],
                        ta="center",
                        gap="1",
                        style={"width": "100%", "marginBottom": "20px"},
                    ),

                    # Escala manual gráficos temporal
                    dmc.Button("Cerrar", id="close-correc-drawer-1", n_clicks=None)
                ],
                opened=False,
                justify="flex-end"
            ),
            # Correcciones de spikes
            dmc.Grid([
                # Espacio en blanco para separación
                html.Div(style={'height': '100px'}),
            ], style={'width': '100%'}),

            dmc.Grid([
                # Primera columna - 70% de ancho, contiene los gráficos
                dmc.Col([
                    dmc.Grid([
                        dmc.Col(dcc.Graph(id='corr_graf_spike_a'), span=3, style={'padding': '0', 'margin': '0'}),
                        dmc.Col(dcc.Graph(id='corr_graf_spike_b'), span=3, style={'padding': '0', 'margin': '0'}),
                        dmc.Col(dcc.Graph(id='corr_graf_stats_a'), span=6, style={'padding': '0', 'margin': '0'})
                    ], style={'width': '100%', 'display': 'flex', 'flexWrap': 'nowrap'})
                ], span=8, style={'padding': '0', 'margin': '0'}),

                # Segunda columna - 30% de ancho, contiene la tabla 'spikes'
                dmc.Col([
                    # Primer grupo
                    dmc.Group(
                        [
                            dmc.Text("Campañas anteriores", fw="bold"),
                            dmc.Select(
                                id='n_spikes',
                                value='max',  # Valor por defecto
                                clearable=False,
                                data=[{'value': 'max', 'label': 'max'}] + [{'value': str(i), 'label': str(i)} for i in
                                                                           range(1, 21)],
                                style={'width': '200px', 'marginLeft': 'auto'}  # Alineado a la derecha
                            ),
                        ],
                        gap="1",  # Espaciado entre el texto y el dropdown
                        style={'width': '100%', 'marginBottom': '15px', 'display': 'flex', 'alignItems': 'center',
                               'justifyContent': 'flex-end'}
                    ),

                    # dropdown de estadística a elegir
                    dmc.Group(
                        [
                            dmc.Text("Estadísticas Spikes", fw="bold"),
                            dmc.Select(
                                id='estadisticas_spikes',
                                value='checksum_a',  # Valor por defecto
                                clearable=False,
                                data=[
                                    {'value': 'a0', 'label': 'a0'},
                                    {'value': 'a180', 'label': 'a180'},
                                    {'value': 'b0', 'label': 'b0'},
                                    {'value': 'b180', 'label': 'b180'},
                                    {'value': 'checksum_a', 'label': 'checksum_a'},
                                    {'value': 'checksum_b', 'label': 'checksum_b'},
                                    {'value': 'incr_dev_a', 'label': 'incr_dev_a'},
                                    {'value': 'incr_dev_b', 'label': 'incr_dev_b'}
                                ],
                                style={'width': '200px', 'marginLeft': 'auto'}  # Alineado a la derecha
                            )
                        ],
                        gap="1",  # Espaciado entre el texto y el dropdown
                        style={'width': '100%', 'marginBottom': '15px', 'display': 'flex', 'alignItems': 'center',
                               'justifyContent': 'flex-end'}
                    ),
                    # dropdown de corrección a realizar
                    dmc.Group(
                        [
                            dmc.Text("Criterio corrección", fw="bold"),
                            dmc.Select(
                                id='spikes_criterio',
                                value= 'media',  # Valor por defecto
                                clearable=False,
                                data=[
                                    {'value': 'media', 'label': 'media'},
                                    {'value': 'mediana', 'label': 'mediana'},
                                    {'value': 'moda', 'label': 'moda'}
                                ],
                                style={'width': '200px', 'marginLeft': 'auto'}  # Alineado a la derecha
                            )
                        ],
                        gap="1",  # Espaciado entre el texto y el dropdown
                        style={'width': '100%', 'marginBottom': '15px', 'display': 'flex', 'alignItems': 'center',
                               'justifyContent': 'flex-end'}
                    ),
                    AgGrid(
                        id='spikes-table',
                        rowData=[],  # Inicialmente vacío
                        columnDefs=[
                            {'headerName': 'Selec', 'field': 'Corregir', 'cellRenderer': 'agCheckboxCellRenderer'},
                            {'headerName': 'Prof', 'field': 'Profundidad'},
                        ],
                        defaultColDef={
                            'flex': 1,  # Ajustar el ancho de las columnas para que ocupen el ancho disponible
                            'minWidth': 100,  # Ancho mínimo de cada columna
                            'resizable': True,
                            'wrapHeaderText': True,  # Ajuste automático de encabezado si es necesario
                            'autoSizeAllColumns': True  # Ajustar automáticamente todas las columnas
                        },
                        columnSize='responsiveSizeToFit' # Ajustar el tamaño de las columnas automáticamente para evitar scroll horizontal
                    ),
                ], span=4, style={'padding': '0', 'margin': '0'}),
            ], style={'width': '100%', 'display': 'flex', 'flexWrap': 'nowrap'}),

        ])
    )


# Registra los callbacks en lugar de definir un nuevo Dash app
def register_callbacks(app):
    # función para cargar la tablas y div ocultos con la información del archivo json del incli
    @app.callback(
        [Output('corregir-tubo', 'data'),
         Output('informacion-archivo', 'children'),
         Output('corregir_archivo', 'data'),
         Output('tabla-json', 'columnDefs'),
         Output('tabla-json', 'rowData'),
         Output('tabla_inicial', 'data'),
         Output('camp_a_graficar', 'data'),  # Añadir salida para actualizar las opciones del listbox
         Output('camp_a_graficar', 'value')],  # Añadir salida para seleccionar el valor por defecto
        [Input('archivo-uploader', 'contents')],
        [State('archivo-uploader', 'filename')]
    )
    def procesar_archivo_contenido(contents, filename):
        if contents is None:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            data = json.loads(decoded)
            corregir_tubo_data = data
            informacion_archivo = html.Span([
                html.B("Inclinómetro: "),
                html.Span(data['info']['nom_sensor'])
            ])
            corregir_archivo_data = filename

            if isinstance(data, dict):
                fechas = sorted([key for key in data.keys() if key != 'info'], reverse=True)
                table_data = []
                for fecha in fechas:
                    row = {
                        'Fecha': fecha,
                        'Referencia': data[fecha].get('campaign_info', {}).get('reference', 'N/A'),
                        'Activa': data[fecha].get('campaign_info', {}).get('active', 'N/A'),
                        'Cuarentena': data[fecha].get('campaign_info', {}).get('quarentine', 'N/A'),
                        'spike': data[fecha].get('campaign_info', {}).get('spike', 'N/A'),
                        'bias': data[fecha].get('campaign_info', {}).get('bias', 'N/A'),
                        'Limpiar': False  # Valor por defecto
                    }
                    table_data.append(row)
                    columnDefs = [
                        {'headerName': 'Fecha', 'field': 'Fecha', 'editable': False, 'resizable': True},
                        {'headerName': 'Referencia', 'field': 'Referencia', 'editable': True,
                         'cellEditor': 'agSelectCellEditor', 'cellEditorParams': {'values': [True, False]}, 'resizable': True},
                        {'headerName': 'Activa', 'field': 'Activa', 'editable': True,
                         'cellEditor': 'agSelectCellEditor', 'cellEditorParams': {'values': [True, False]}, 'resizable': True},
                        {'headerName': 'Cuarentena', 'field': 'Cuarentena', 'editable': True,
                         'cellEditor': 'agSelectCellEditor', 'cellEditorParams': {'values': [True, False]}, 'resizable': True},
                        {'headerName': 'Correc Spike', 'field': 'spike', 'editable': False, 'resizable': True},
                        {'headerName': 'Correc Bias', 'field': 'bias', 'editable': False, 'resizable': True},
                        {'headerName': 'Limpiar', 'field': 'Limpiar', 'editable': True,
                         'cellEditor': 'agCheckboxCellEditor', 'resizable': True},
                    ]

                # Almacenar los valores iniciales de la tabla-json en tabla_inicial
                tabla_inicial = {row['Fecha']: row for row in table_data}
                camp_a_graficar_data = [{'value': fecha, 'label': fecha} for fecha in fechas]
                camp_a_graficar_value = fechas[0] if fechas else ''  # Selecciona la fecha más reciente
            else:
                columnDefs, table_data, tabla_inicial, camp_a_graficar_data, camp_a_graficar_value = [], [], {}, [], ''

        except Exception as e:
            ic(e)
            return dash.no_update, "Error al procesar el archivo", dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        return corregir_tubo_data, informacion_archivo, corregir_archivo_data, columnDefs, table_data, tabla_inicial, camp_a_graficar_data, camp_a_graficar_value

    @app.callback(
        Output("camp_corregida", "data"),  # Update the "camp_corregida" Store
        [Input("corregir-tubo", "data"), # archivo json data
         Input("spikes-table", "cellValueChanged"),# Listen for changes in the table
         Input("camp_a_graficar", "value")],  # campaña a graficar
        [State("spikes-table", "rowData"),  # Current data of the table
        #State("camp_corregida", "data") # Existing data in "camp_corregida"
         ]
    )
    def actualizar_camp_corregida(data, cellValueChanged, camp_graficar, table_data):#, camp_corregida):
        if camp_graficar == None:
            # no hay nada cargado
            return dash.no_update

        if not table_data or all((not fila.get("A")) and (not fila.get("B")) for fila in table_data):
            # no hay corrección puntual o no se ha seleccionado nada en A y B
            resultado = {camp_graficar: {"calc": data[camp_graficar]['calc']}}
            # = data[camp_graficar]['calc']
            print("Cargado el valor original")
            return resultado
        # Inicializar el diccionario final
        correccion = {camp_graficar: {"calc": []}}

        # Iterar sobre cada elemento en data_table
        for item in table_data:
            # Crear una nueva entrada con los valores requeridos
            # debe haber coherencia con la construcción del diccionario del tubo (json)
            nueva_entrada = {
                "index": next((entry['index'] for entry in data[camp_graficar]["calc"] if entry['depth'] == item["Profundidad"]), None),
                "cota_abs": next((entry['cota_abs'] for entry in data[camp_graficar]["calc"] if entry['depth'] == item["Profundidad"]), None),
                "depth": item["Profundidad"],
                "A_spk": item["A"], # esto originalmente no está en 'calc'
                "B_spk": item["B"], # esto originalmente no está en 'calc'
                "a0": item["a0_c"] if item["A"] else item["a0"],
                "a180": item["a180_c"] if item["A"] else item["a180"],
                "b0": item["b0_c"] if item["B"] else item["b0"],
                "b180": item["b180_c"] if item["B"] else item["b180"]
            }
            # Añadir la nueva entrada al diccionario
            correccion[camp_graficar]["calc"].append(nueva_entrada)
        # Calcular dev_a después de crear las entradas
        for entrada in correccion[camp_graficar]["calc"]:
            entrada["dev_a"] = round((entrada["a0"] - entrada["a180"]) / 2, 2)
            entrada["dev_b"] = round((entrada["b0"] - entrada["b180"]) / 2, 2)
        # busco referencia
        fecha_referencia = buscar_referencia(data, camp_graficar)

        # calcula los desplazamientos de la campañas con las correcciones seleccionadas
        # para usar la función común, hay que digerir los datos, haciendo un data_new que tenga sólo la campaña origen y la corregida
        #print(f"fecha_referencia: {repr(fecha_referencia)}")  # Verifica la cadena exacta
        #print(f"Claves de data: {list(data.keys())}")  # Muestra las claves disponibles en el diccionario


        data_new = {}
        data_new[fecha_referencia] = {"calc": data[fecha_referencia]['calc']}
        data_new[camp_graficar] = {"calc": correccion[camp_graficar]['calc']}
        resultado = calcular_incrementos(data_new, camp_graficar, fecha_referencia)
        #print ({camp_graficar: {"calc": resultado[camp_graficar]['calc']}})
        return {camp_graficar: {"calc": resultado[camp_graficar]['calc']}}

    # Callback para manejar cambios en la tabla y guardar el log_cambios
    @app.callback(
        Output('log_cambios', 'data'),
        Output('log-cambios', 'children'),
        Input('tabla-json', 'cellValueChanged'),
        State('corregir-tubo', 'data'),
        State('log_cambios', 'data'),
        State('tabla_inicial', 'data')
    )
    def registrar_cambios(cell_value_changed, corregir_tubo, log_cambios, tabla_inicial):
        if cell_value_changed is None:
            raise dash.exceptions.PreventUpdate

        for change in cell_value_changed:
            fecha_cambio = change['data']['Fecha']  # Obtener la fecha de la primera columna de la fila
            key = change.get('colId')
        new_value = change.get('value') # valor recien cambiado en la tabla
        old_value = change.get('oldValue') # valor anterior
        # Añadir la nueva entrada para la fecha y clave actual
        cambios_key = f"{fecha_cambio}_{key}"
        log_cambios[cambios_key] = {
            'fecha': fecha_cambio,
            'clave': key,
            'original': tabla_inicial[fecha_cambio][key], # valor inicial de la tabla
            'old_value': old_value,
            'new_value': new_value
        }
        # Eliminar las líneas en las que "original" y "new_value" son iguales
        log_cambios = {k: v for k, v in log_cambios.items() if v['original'] != v['new_value']}

        # Ordenar el diccionario cambios de manera cronológica por fecha y luego por clave ('Referencia' primero)
        log_cambios = dict(sorted(log_cambios.items(), key=lambda item: (item[1]['fecha'], item[1]['clave'] != 'Referencia')))

        # Construir log_lines después de finalizar con cambios
        log_lines = []
        for key, value in log_cambios.items():
            if key != 'log_lines':
                log_lines.append(html.Span([
                    html.B('fecha'), f": {value['fecha']} ",
                    html.B(value['clave']), f": {value['original']} → {value['old_value']} → {value['new_value']}"
                ]))
                log_lines.append(html.Br())

        return log_cambios, log_lines

    """
    Controla la apertura y el cierre del drawer-1.
    :param app:
    - `open_clicks`, `close_clicks`: número de clics en los botones de abrir/cerrar.
    - `is_open`: estado actual del drawer (abierto/cerrado).
    """
    @app.callback(
        Output("correc-drawer-1", "opened"),
        [Input("correc-open-drawer-1", "n_clicks"),
         Input("close-correc-drawer-1", "n_clicks")],
        [State("correc-drawer-1", "opened")]
    )
    def toggle_patron_drawer(open_clicks, close_clicks, is_open):
        if open_clicks is None:
            open_clicks = 0
        if close_clicks is None:
            close_clicks = 0

        return open_clicks > close_clicks

    # valores de los input en el drawer-1
    @app.callback(
        [Output("correc_valor_positivo_desplazamiento", "disabled"),
         Output("correc_valor_negativo_desplazamiento", "disabled"),
         Output("correc_valor_positivo_incremento", "disabled"),
         Output("correc_valor_negativo_incremento", "disabled")],
        [Input("correc_escala_graficos_desplazamiento", "value"),
         Input("correc_escala_graficos_incremento", "value")]
    )
    def habilitar_inputs(escala_desplazamiento, escala_incremento):
        # Para habilitar los inputs solo si la escala es "manual"
        habilitar_desplazamiento = escala_desplazamiento == "manual"
        habilitar_incremento = escala_incremento == "manual"
        return not habilitar_desplazamiento, not habilitar_desplazamiento, not habilitar_incremento, not habilitar_incremento

    # Grupo de gráficos 1: Representación de movimientos vs profundidad, con diferentes opciones
    @app.callback(
        [Output("corr_grafico_incli_1_a", "figure"),
         Output("corr_grafico_incli_1_b", "figure"),
         Output("corr_grafico_incli_2_a", "figure"),
         Output("corr_grafico_incli_2_b", "figure"),
         Output("corr_grafico_incli_3_a", "figure"),
         Output("corr_grafico_incli_3_b", "figure"),
         Output("corr_grafico_incli_3_total", "figure")],
        [Input("corregir-tubo", "data"), # archivo json data
         Input("camp_corregida", "data"), # valores temporales de la campaña corregida
         Input("camp_a_graficar", "value"), #fecha_seleccionada
         Input("camp_a_graficar", "data"), # no sé si es necesario fechas_incli
         Input("correc_num_camp_previas_grafico1", "value"),#camp_previas
         Input("corr_alto_graficos_slider_grafico1", "value"), #alto_graficos
         Input("correcciones_color_grafico1", "value"), # color
         Input("correc_escala_graficos_desplazamiento", "value"),
         Input("correc_escala_graficos_incremento", "value"),
         Input("correc_valor_positivo_desplazamiento", "value"),
         Input("correc_valor_negativo_desplazamiento", "value"),
         Input("correc_valor_positivo_incremento", "value"),
         Input("correc_valor_negativo_incremento", "value")]
    )
    def corr_grafico_1(data, camp_corregida, fecha_seleccionada, fechas_incli, camp_previas, alto_graficos, color_scheme,
                            escala_desplazamiento, escala_incremento,
                            valor_positivo_desplazamiento, valor_negativo_desplazamiento,
                            valor_positivo_incremento, valor_negativo_incremento):
        if not fecha_seleccionada or not data:
            return [go.Figure() for _ in range(7)]

        fig1_a = go.Figure()
        fig1_b = go.Figure()
        fig2_a = go.Figure()
        fig2_b = go.Figure()
        fig3_a = go.Figure()
        fig3_b = go.Figure()
        fig3_total = go.Figure()
        # suma 1 a las camp_previas
        camp_previas +=1
        # filtro las fechas a graficar en función de la fecha seleccionada y el número de anteriores a mostrar
        series_a_graficar = [item['value'] for item in fechas_incli if item['value'] <= fecha_seleccionada]
        series_a_graficar = series_a_graficar[0:camp_previas]

        for fecha in series_a_graficar:
            if fecha != fecha_seleccionada:
                #item_correspondiente = next(item for item in fechas_colores if item['value'] == fecha)
                #color = item_correspondiente['style']['color']
                index = series_a_graficar.index(fecha)
                color = get_color_for_index(index, color_scheme, camp_previas)
                grosor = 2
                opacity = 0.7

                # se pasa a una lista el diccionario
                cota_abs_list = [punto["cota_abs"] for punto in data[fecha]["calc"]]
                desp_a_list = [punto["desp_a"] for punto in data[fecha]["calc"]]
                desp_b_list = [punto["desp_b"] for punto in data[fecha]["calc"]]
                incr_dev_a_list = [punto["incr_dev_a"] for punto in data[fecha]["calc"]]
                incr_dev_b_list = [punto["incr_dev_b"] for punto in data[fecha]["calc"]]
                desp_total_list = [punto["desp_a"] + punto["desp_b"] for punto in data[fecha]["calc"]]

                # Gráfico 1: Desplazamientos
                fig1_a.add_trace(go.Scatter(x=desp_a_list, y=cota_abs_list, mode="lines", name=f"{fecha} - Desp A",
                                            line=dict(c=color, width=grosor), legendgroup=fecha,
                                            opacity=opacity))
                fig1_b.add_trace(go.Scatter(x=desp_b_list, y=cota_abs_list, mode="lines", name=f"{fecha} - Desp B",
                                            line=dict(c=color, width=grosor), legendgroup=fecha,
                                            opacity=opacity))

                # Gráfico 2: Incrementales
                fig2_a.add_trace(
                    go.Scatter(x=incr_dev_a_list, y=cota_abs_list, mode="lines", name=f"{fecha} - Incr Dev A",
                               line=dict(c=color, width=grosor), legendgroup=fecha, opacity=opacity))
                fig2_b.add_trace(
                    go.Scatter(x=incr_dev_b_list, y=cota_abs_list, mode="lines", name=f"{fecha} - Incr Dev B",
                               line=dict(c=color, width=grosor), legendgroup=fecha, opacity=opacity))

                # Gráfico 3: Desplazamientos Compuestos
                fig3_a.add_trace(go.Scatter(x=desp_a_list, y=cota_abs_list, mode="lines", name=f"{fecha} - Desp A",
                                            line=dict(c=color, width=grosor), legendgroup=fecha,
                                            opacity=opacity))
                fig3_b.add_trace(go.Scatter(x=desp_b_list, y=cota_abs_list, mode="lines", name=f"{fecha} - Desp B",
                                            line=dict(c=color, width=grosor), legendgroup=fecha,
                                            opacity=opacity))
                fig3_total.add_trace(
                    go.Scatter(x=desp_total_list, y=cota_abs_list, mode="lines", name=f"{fecha} - Desp Total",
                               line=dict(c=color, width=grosor), legendgroup=fecha, opacity=opacity))
        # Luego agregar la serie seleccionada (= corregida temporal) para que quede encima
        if fecha_seleccionada in series_a_graficar: # este condicional sobra
            fecha = fecha_seleccionada
            color = 'darkblue'
            grosor = 4
            opacity = 1.0
            # marker = dict(size=4, c='yellow', symbol='circle')
            print('paso por aquí')

            # se pasa a una lista el diccionario
            cota_abs_list = [punto["cota_abs"] for punto in camp_corregida[fecha]["calc"]]
            desp_a_list = [punto["desp_a"] for punto in camp_corregida[fecha]["calc"]]
            desp_b_list = [punto["desp_b"] for punto in camp_corregida[fecha]["calc"]]
            incr_dev_a_list = [punto["incr_dev_a"] for punto in camp_corregida[fecha]["calc"]]
            incr_dev_b_list = [punto["incr_dev_b"] for punto in camp_corregida[fecha]["calc"]]
            desp_total_list = [punto["desp_a"] + punto["desp_b"] for punto in camp_corregida[fecha]["calc"]]

            # Gráfico 1: Desplazamientos
            fig1_a.add_trace(
                go.Scatter(x=desp_a_list, y=cota_abs_list, mode="lines", name=f"{fecha} - Desp A",
                           line=dict(c=color, width=grosor),
                           # marker=marker,
                           legendgroup=fecha,
                           opacity=opacity))
            fig1_b.add_trace(
                go.Scatter(x=desp_b_list, y=cota_abs_list, mode="lines", name=f"{fecha} - Desp B",
                           line=dict(c=color, width=grosor),
                           # marker=marker,
                           legendgroup=fecha,
                           opacity=opacity))

            # Gráfico 2: Incrementales
            fig2_a.add_trace(go.Scatter(x=incr_dev_a_list, y=cota_abs_list, mode="lines",
                                        name=f"{fecha} - Incr Dev A",
                                        line=dict(c=color, width=grosor),
                                        # marker=marker,
                                        legendgroup=fecha, opacity=opacity))
            fig2_b.add_trace(go.Scatter(x=incr_dev_b_list, y=cota_abs_list, mode="lines",
                                        name=f"{fecha} - Incr Dev B",
                                        line=dict(c=color, width=grosor),
                                        # marker=marker,
                                        legendgroup=fecha, opacity=opacity))

            # Gráfico 3: Desplazamientos Compuestos
            fig3_a.add_trace(
                go.Scatter(x=desp_a_list, y=cota_abs_list, mode="lines", name=f"{fecha} - Desp A",
                           line=dict(c=color, width=grosor),
                           # marker=marker,
                           legendgroup=fecha,
                           opacity=opacity))
            fig3_b.add_trace(
                go.Scatter(x=desp_b_list, y=cota_abs_list, mode="lines", name=f"{fecha} - Desp B",
                           line=dict(c=color, width=grosor),
                           # marker=marker,
                           legendgroup=fecha,
                           opacity=opacity))
            fig3_total.add_trace(go.Scatter(x=desp_total_list, y=cota_abs_list, mode="lines",
                                            name=f"{fecha} - Desp Total",
                                            line=dict(c=color, width=grosor),
                                            # marker=marker,
                                            legendgroup=fecha, opacity=opacity))
        # Configurar ejes y quitar leyendas, ajustar altura de gráficos
        for fig in [fig1_a, fig1_b, fig3_a, fig3_b, fig3_total]:
            if escala_desplazamiento == "manual":
                fig.update_xaxes(range=[valor_negativo_desplazamiento, valor_positivo_desplazamiento])

        # escala automática/manual
        for fig in [fig2_a, fig2_b]:
            if escala_incremento == "manual":
                fig.update_xaxes(range=[valor_negativo_incremento, valor_positivo_incremento])

        # Definición de gráficos y rejilla
        for fig in [fig1_a, fig1_b, fig2_a, fig2_b, fig3_a, fig3_b, fig3_total]:
            fig.update_layout(
                yaxis=dict(
                    autorange="reversed",
                    gridc='lightgray', gridwidth=1, griddash='dash',
                    anchor='free',
                    position=0,  # Posicionar el eje Y en x=0
                    showline=False,  # Asegurarse de que no se muestra la línea vertical del eje Y
                ),
                xaxis=dict(
                    gridc='lightgray', gridwidth=1, griddash='dash',
                    showline=True,  # Mostrar la línea del borde inferior (eje X)
                    linec='darkgray',  # Color del borde inferior
                    linewidth=1,  # Grosor del borde inferior
                    zeroline=True, zerolinec='darkgray', zerolinewidth=1  # muestra el eje vertical en x=0
                ),
                showlegend=False, height=alto_graficos, title_x=0.5, plot_bgc='white'
            )


        return [fig1_a, fig1_b, fig2_a, fig2_b, fig3_a, fig3_b, fig3_total]

    # Grupo de gráficos 2
    @app.callback(
        [Output("corr_graf_spike_a", "figure"),
         Output("corr_graf_spike_b", "figure"),
         Output("corr_graf_stats_a", "figure")],
        [Input("corregir-tubo", "data"),  # archivo json data
         Input("camp_a_graficar", "value"),  # fecha_seleccionada
         Input("camp_a_graficar", "data"),#  fechas_incli
         Input('n_spikes', "value"), #  campañas anteriores
         Input("correcciones_color_grafico1", "value"),# color
         Input('estadisticas_spikes', "value")]) # lo que se muestra en las estadísticas

    def corr_spike(data, fecha_seleccionada, fechas, n_spikes, color_scheme, estadistica):
        if not fecha_seleccionada or not data:
            return [go.Figure() for _ in range(3)]

        # busco la campaña referencia
        fecha_referencia = buscar_referencia(data, fecha_seleccionada)

        # filtro las fechas desde la referencia (incluida) a la fecha_seleccionada, excluyendo las active = False
        conjunto_fechas =  [fecha['value'] for fecha in fechas if fecha_referencia <= fecha['value'] <= fecha_seleccionada
                            and data[fecha['value']]['campaign_info']['active'] == True]

        # considero sólo las que marca n_spikes
        if n_spikes != 'max':
            # cojo sólo las que correspondan, ojo que están ordenadas de más actual a más antigua
            conjunto_fechas = conjunto_fechas[:int(n_spikes)+1] # añado 1 para que sean la selec + n_spikes
        # convertir el diccionario en un dataframe
        dfs = dict_a_df(data, ['a0', 'a180', 'b0', 'b180', 'checksum_a', 'checksum_b', 'incr_dev_a', 'incr_dev_b'], conjunto_fechas)

        # creo los gráficos
        fig1_a = go.Figure()
        fig1_b = go.Figure()

        camp_previas = len(conjunto_fechas)

        # Añado las gráficas seleccionadas
        for fecha in conjunto_fechas:

            index = conjunto_fechas.index(fecha)
            color = get_color_for_index(index, color_scheme, camp_previas)
            grosor = 2
            opacity = 0.7

            # Gráfico 1: Desplazamientos
            fig1_a.add_trace(go.Scatter(x=dfs['checksum_a'][fecha], y=dfs['checksum_a'].index, mode="lines", name=f"{fecha} - CheckSum A",
                                        line=dict(c=color, width=grosor), legendgroup=fecha,
                                        opacity=opacity))
            fig1_b.add_trace(go.Scatter(x=dfs['checksum_b'][fecha], y=dfs['checksum_b'].index, mode="lines", name=f"{fecha} - CheckSum B",
                                        line=dict(c=color, width=grosor), legendgroup=fecha,
                                        opacity=opacity))
        fig_3 = grafico_violines(dfs[estadistica], fecha_seleccionada)

        # Definición de gráficos y rejilla
        alto_graficos = 800
        for fig in [fig1_a, fig1_b, fig_3]:#, fig2_a, fig2_b, fig3_a, fig3_b, fig3_total]:
            fig.update_layout(
                yaxis=dict(
                    autorange="reversed",
                    gridc='lightgray', gridwidth=1, griddash='dash',
                    anchor='free',
                    position=0,  # Posicionar el eje Y en x=0
                    showline=False,  # Asegurarse de que no se muestra la línea vertical del eje Y
                ),
                xaxis=dict(
                    gridc='lightgray', gridwidth=1, griddash='dash',
                    showline=True,  # Mostrar la línea del borde inferior (eje X)
                    linec='darkgray',  # Color del borde inferior
                    linewidth=1,  # Grosor del borde inferior
                    zeroline=True, zerolinec='darkgray', zerolinewidth=1  # muestra el eje vertical en x=0
                ),
                showlegend=False, height=alto_graficos, title_x=0.5, plot_bgc='white'
            )

        return fig1_a, fig1_b, fig_3

    @app.callback(
        [Output("spikes-table", "rowData"),
         Output("spikes-table", "columnDefs")],
        [Input("corregir-tubo", "data"),
         Input("camp_a_graficar", "value"),
         Input("camp_a_graficar", "data"),
         Input("n_spikes", "value"),
         Input("spikes_criterio", "value")]  # Cambiamos estadisticas_spikes por spikes_criterio
    )
    def actualizar_spikes_table(data, fecha_seleccionada, fechas, n_spikes, criterio):
        if not fecha_seleccionada or not data:
            return [], []

        # Buscar la campaña referencia
        fecha_referencia = buscar_referencia(data, fecha_seleccionada)

        # Filtrar las fechas desde la referencia (incluida) hasta la fecha seleccionada
        conjunto_fechas = [
            fecha['value'] for fecha in fechas
            if fecha_referencia <= fecha['value'] <= fecha_seleccionada
               and data[fecha['value']]['campaign_info']['active'] == True
        ]

        # Considerar solo las campañas marcadas por n_spikes
        if n_spikes != 'max':
            conjunto_fechas = conjunto_fechas[:int(n_spikes) + 1]  # Incluir la fecha seleccionada

        # Convertir el diccionario en un DataFrame
        dfs = dict_a_df(
            data,
            ['a0', 'a180', 'b0', 'b180'],  # Restringir a estas columnas
            conjunto_fechas
        )

        # Calcular las columnas "a0_c", "b0_c", "a180_c", "b180_c"
        columnas_c = {}
        for variable in ['a0', 'a180', 'b0', 'b180']:
            df_variable = dfs[variable].drop(columns=[fecha_seleccionada],
                                             errors="ignore")  # Excluir fecha_seleccionada
            if criterio == "media":
                columnas_c[f"{variable}_c"] = df_variable.mean(axis=1).round(2)
            elif criterio == "mediana":
                columnas_c[f"{variable}_c"] = df_variable.median(axis=1).round(2)
            elif criterio == "moda":
                columnas_c[f"{variable}_c"] = df_variable.mode(axis=1).iloc[:, 0].round(
                    2)  # Seleccionar la primera moda
            else:
                columnas_c[f"{variable}_c"] = None  # Por defecto, si el criterio no es válido

        # Preparar los datos para la tabla
        rowData = []
        for profundidad in dfs['a0'].index.tolist():
            row = {"Profundidad": profundidad, "A": False, "B": False}  # Inicializar "A" y "B" como no seleccionados
            for variable in ['a0', 'a180', 'b0', 'b180']:
                row[variable] = dfs[variable].loc[profundidad, fecha_seleccionada]
            for columna_c, valores_c in columnas_c.items():
                row[columna_c] = valores_c.loc[profundidad]
            rowData.append(row)

        # Definir las columnas de la tabla
        columnDefs = [
            {
                "headerName": "A",
                "field": "A",
                "cellRenderer": "agCheckboxCellRenderer",
                "cellEditor": "agCheckboxCellEditor",
                "editable": True
            },
            {
                "headerName": "B",
                "field": "B",
                "cellRenderer": "agCheckboxCellRenderer",
                "cellEditor": "agCheckboxCellEditor",
                "editable": True
            },
            {"headerName": "Prof", "field": "Profundidad"}
        ]
        columnDefs.extend(
            {"headerName": variable, "field": variable} for variable in ['a0', 'a180', 'b0', 'b180']
        )
        columnDefs.extend(
            {"headerName": columna_c, "field": columna_c} for columna_c in columnas_c.keys()
        )

        return rowData, columnDefs







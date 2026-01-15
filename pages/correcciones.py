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
import json
import os
from pathlib import Path
import math



#from TD_medias.vol_td.main import height
from utils.funciones_comunes import get_color_for_index, buscar_referencia, calcular_incrementos, df_to_excel, debug_funcion, camp_independiente
from utils.funciones_correcciones import grafico_violines, dict_a_df, creacion_df_bias, calculos_bias, calculos_bias_1, tabla_del_json, std
from utils.funciones_importar import valores_calc_directos


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
            dcc.Store(id="json_spikes", storage_type='memory'), # Campaña seleccionada con las correcciones spikes
            dcc.Store(id="json_bias", storage_type='memory'), # Campaña seleccionada con las correcciones bias
            dcc.Store(id='tabla_inicial', data={}, storage_type='memory'),  # tabla resumen de campañas de 'corregir-tubo'
            dcc.Store(id='log_cambios', data={}, storage_type='memory'),  # interacciones que se van haciendo en la tabla
            dcc.Store(id='cambios_a_realizar', data={}, storage_type='memory'),  # modificaciones que se van haciendo sobre corregir-tubo NO SE USA
            dcc.Store(id='calculated_bias_values', storage_type='memory'), # gestiona la carga inicial de la tabla bias-table
            dcc.Store(id="json_final", storage_type='memory'),# Campaña seleccionada con las correcciones spk+bias NO SE USA
            dcc.Store(id='bias-table-change-flag', data=False, storage_type='memory'), # variable para que se actualice json_bias en la primera carga
            dcc.Store(id="error-store", data={"opened": False, "message": ""}), # gestión de mensajes de error en bias-table

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
                                    #dmc.Button("Recalcular Tabla", id='recalcular_tabla', variant='outline', c='blue'),
                                    dmc.Button("Guardar Tabla", id='guardar_tabla', variant='outline', c='green')
                                ],
                                style={'marginTop': '10px'}
                            ),
                            dmc.Modal(
                                id="guardar-cambios-tabla",
                                title="Confirmación",
                                children=[
                                    html.Div(id="guardar-mensaje-tabla"),
                                    dmc.Button("Cerrar", id="cerrar-cambios-tabla", variant="outline",
                                               style={"marginTop": "10px"})
                                ],
                                centered=True,
                                size="md",
                                opened=False  # Inicialmente cerrado
                            ),
                        ],
                        span=4
                    )
                ],
                style={'width': '100%'}
            ),
            # Gráficos del incli - GRAFICO 1

            html.Div(style={"height": "200px"}),  # Espacio. No funciona bien, quiero que esté un poco más separado

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
                                        dmc.Text("Desplazamiento A (mm)", ta="center")], span=6, style={'padding': '0', 'margin': '0'}),
                                    dmc.Col([
                                        dcc.Graph(id='corr_grafico_incli_1_b'),
                                        dmc.Text("Desplazamiento B (mm)", ta="center")
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
                                        dmc.Text("Incremental A (mm)", ta="center")
                                    ], span=6, style={'padding': '0', 'margin': '0'}),
                                    dmc.Col([
                                        dcc.Graph(id='corr_grafico_incli_2_b'),
                                        dmc.Text("Incremental B (mm)", ta="center")
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
                                        dmc.Text("Desplazamientos  (mm)", ta="center")
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
                                value=10,  # Valor por defecto
                                min=0,
                                max=1000,
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
                                value=20,
                                min=-1000,
                                max=1000,
                                step=5,
                                disabled=True,
                                style={"flex": 1},
                            ),
                            dmc.Text("Min", style={"width": "30px", "marginLeft": "10px"}),
                            dmc.NumberInput(
                                id="correc_valor_negativo_desplazamiento",
                                value=-20,
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
                        dmc.Col([
                            dcc.Graph(id='corr_graf_spike_a'),
                            dmc.Text("Incr CheckSum A", ta="center")],
                            span=3, style={'padding': '0', 'margin': '0'}),
                        dmc.Col([
                            dcc.Graph(id='corr_graf_spike_b'),
                            dmc.Text("Incr CheckSum B", ta="center")],
                            span=3, style={'padding': '0', 'margin': '0'}),
                        dmc.Col([
                            dcc.Graph(id='corr_graf_stats_a'),
                            dmc.Text("Estadística seleccionada", ta="center")],
                            span=6, style={'padding': '0', 'margin': '0'})
                    ], style={'width': '100%', 'display': 'flex', 'flexWrap': 'nowrap'})
                ], span=8, style={'padding': '0', 'margin': '0'}),


                # Segunda columna - 30% de ancho, contiene la tabla 'spikes'
                dmc.Col([
                    html.H2("Corrección de spikes"),
                    html.Div(style={"height": "20px"}),
                    # Primer grupo
                    dmc.Group(
                        [
                            html.H4("Campañas anteriores"),
                            #dmc.Text("Campañas anteriores", fw="bold"),
                            dmc.Select(
                                id='n_spikes',
                                value='5',  # Valor por defecto
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
                            html.H4("Estadísticas Spikes"),
                            #dmc.Text("Estadísticas Spikes", fw="bold"),
                            dmc.Select(
                                id='estadisticas_spikes',
                                value='incr_checksum_a',  # Valor por defecto
                                clearable=False,
                                data=[
                                    {'value': 'a0', 'label': 'a0'},
                                    {'value': 'a180', 'label': 'a180'},
                                    {'value': 'b0', 'label': 'b0'},
                                    {'value': 'b180', 'label': 'b180'},
                                    {'value': 'incr_checksum_a', 'label': 'incr_checksum_a'},
                                    {'value': 'incr_checksum_b', 'label': 'incr_checksum_b'},
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
                            html.H4("Criterio corrección"),
                            #dmc.Text("Criterio corrección", fw="bold"),
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
                    # Dropdown and button above the table
                    dmc.Group(
                        children=[
                            dmc.Col(
                                dmc.MultiSelect(
                                    id='spike_profundidad',
                                    placeholder='Selecciona profundidad',
                                    data=[],  # This will be populated dynamically
                                    style={'width': '100%'}
                                ),
                                span=6
                            ),
                            dmc.Col(
                                dmc.Button(
                                    "Cargar Temporal Spike",
                                    id='temporal_spike',
                                    variant='outline',
                                    c='blue'
                                ),
                                span=2
                            )
                        ],
                        ta='center',
                        style={'marginBottom': '20px'}
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
                    dmc.Modal(
                        id="temporal-spike-modal",
                        title="Detalles del Histórico Temporal",
                        children=[
                            # Grupo para el texto y el multiselect alineados horizontalmente
                            dmc.Group(
                                [
                                    html.H4("Elegir variables"),
                                    #dmc.Text("Elegir variables", style={"marginRight": "10px", "fontWeight": "bold"}),
                                    dmc.MultiSelect(
                                        id='temporal-spike-variables',
                                        data=[
                                            {"value": "a0", "label": "a0"},
                                            {"value": "a180", "label": "a180"},
                                            {"value": "b0", "label": "b0"},
                                            {"value": "b180", "label": "b180"},
                                            {"value": "checksum_a", "label": "checksum_a"},
                                            {"value": "checksum_b", "label": "checksum_b"},
                                            {"value": "incr_checksum_a", "label": "incr_checksum_a"},
                                            {"value": "incr_checksum_b", "label": "incr_checksum_b"},
                                        ],
                                        value=["incr_checksum_a", "incr_checksum_b"],  # Valores por defecto
                                        style={"flex": "1", "minWidth": "200px"}
                                    ),
                                ],
                                ta="center",
                                style={"marginBottom": "20px"}
                            ),
                            # Gráfico
                            dcc.Graph(id='temporal-spike-graph')
                        ],
                        opened=False,
                        size="xl",
                        centered=True
                    ),
                    dmc.Modal(
                        id="error-modal",
                        title="Error",
                        children=[
                            html.Div(id="error-message"),
                            #dmc.Button("Cerrar", id="close-error-modal", variant="outline", style={"marginTop": "10px"})
                        ],
                        centered=True,
                        size="md",
                        opened=False,
                    )
                ], span=4, style={'padding': '0', 'margin': '0'}),
            ], style={'width': '100%', 'display': 'flex', 'flexWrap': 'nowrap'}),

            # Correcciones de bias
            dmc.Grid([
                # Espacio en blanco para separación
                html.Div(style={'height': '100px'}),], style={'width': '100%'}),

            dmc.Grid([
                # Primera columna - 70% de ancho, contiene los gráficos
                dmc.Col([
                    dmc.Grid([
                        dmc.Col(dcc.Graph(id='corr_graf_bias_a'), span=4, style={'padding': '0', 'margin': '0'}),
                        dmc.Col(dcc.Graph(id='corr_estad_bias_a'), span=2, style={'padding': '0', 'margin': '0'}),
                        dmc.Col(dcc.Graph(id='corr_graf_bias_b'), span=4, style={'padding': '0', 'margin': '0'}),
                        dmc.Col(dcc.Graph(id='corr_estad_bias_b'), span=2, style={'padding': '0', 'margin': '0'}),
                    ], style={'width': '100%', 'display': 'flex', 'flexWrap': 'nowrap'})
                ], span=8, style={'padding': '0', 'margin': '0'}), # ancho de la columna de gráficos

                # Segunda columna - 30% de ancho, contiene la definición de correcciones bias
                dmc.Col([
                    html.H2("Corrección de bias"),
                    html.Div(style={"height": "20px"}),
                    # Modal para el análisis de checksum o lo que sea, por definir
                    dmc.Group(
                        children=[
                            dmc.Col(
                                html.H4("Evolución temporal"),
                                span=6
                            ),
                            dmc.Col(
                                dmc.Button(
                                    "Cargar Análisis Bias",
                                    id='boton_ventana_modal_bias',
                                    variant='outline',
                                    c='blue'
                                ),
                                span=2
                            )
                        ],
                        ta='center',
                        style={'marginBottom': '20px'}
                    ),
                    # Modal para el análisis de std de checksum o lo que sea, por definir
                    dmc.Group(
                        children=[
                            dmc.Col(
                                html.H4("Evolución temporal std"),
                                span=6
                            ),
                            dmc.Col(
                                dmc.Button(
                                    "Cargar Evolución std",
                                    id='boton_ventana_modal_bias_1',
                                    variant='outline',
                                    c='blue'
                                ),
                                span=2
                            )
                        ],
                        ta='center',
                        style={'marginBottom': '20px'}
                    ),

                    dmc.Group(
                        children=[
                            dmc.Col(
                                html.H4("Empotramiento teórico"),
                                span=6
                            ),
                            dmc.Col(
                                dmc.NumberInput(
                                    id='empotramiento',
                                    value=5, # valor por defecto
                                    min=1, max=99,
                                    step=1,
                                    style={"width": "100px"}
                                ),
                                span=2
                            )
                        ],
                        ta='center',
                        style={'marginBottom': '20px'}
                    ),
                    # ventana modal del analisis del checksum por intervalos
                    dmc.Modal(
                        id="ventana_modal_bias",
                        title="Bùsqueda de parámetro",
                        children=[
                            # Grupo para el texto y el multiselect alineados horizontalmente
                            dmc.Group(
                                [
                                    dmc.Text("Elegir variables", style={"marginRight": "10px", "fontWeight": "bold"}),
                                    dmc.Select(
                                        id='temporal-bias-variables',
                                        data=[
                                            {"value": "checksum_a", "label": "checksum_a"},
                                            {"value": "checksum_b", "label": "checksum_b"},
                                            {"value": "incr_dev_a", "label": "incr_dev_a"},
                                            {"value": "incr_dev_b", "label": "incr_dev_b"},

                                        ],
                                        value="checksum_a",#["checksum_a", "checksum_b"],  # Valores por defecto
                                        #maxSelectedValues=1,  # Solo permite una opción seleccionada
                                        #clearable=False,  # Evita que se puedan eliminar todas las opciones
                                        style={"flex": "1", "minWidth": "200px"}
                                    ),
                                ],
                                ta="center",
                                style={"marginBottom": "20px"}
                            ),
                            # Gráficos en el modal
                            dcc.Graph(id='modal_bias_graph_1'),
                        ],
                        opened=False,
                        size="xl",
                        centered=True
                    ),
                    # ventana modal del analisis del std del  checksum
                    dmc.Modal(
                        id="ventana_modal_bias_1",
                        title="Bùsqueda de parámetro",
                        children=[
                            # Gráficos en el modal
                            dcc.Graph(id='modal_bias_graph_2'),
                        ],
                        opened=False,
                        size="xl",
                        centered=True
                    ),

                    # separación
                    html.Div(style={"height": "20px"}),
                    # tabla de configuración de bias a aplicar
                    AgGrid(
                        id='bias-table',
                        #rowData=[],  # Inicialmente vacío
                        rowData=[
                            {'Correccion': 'Bias_1_A', 'Selec': False, 'Prof_inf': 0, 'Prof_sup': 0, 'Delta': ''},
                            {'Correccion': 'Bias_1_B', 'Selec': False, 'Prof_inf': 0, 'Prof_sup': 0, 'Delta': ''},
                            {'Correccion': 'Bias_2_A', 'Selec': False, 'Prof_inf': 0, 'Prof_sup': 0, 'Delta': ''},
                            {'Correccion': 'Bias_2_B', 'Selec': False, 'Prof_inf': 0, 'Prof_sup': 0, 'Delta': ''}
                        ],  # Datos iniciales
                        columnDefs=[
                                    {'headerName': 'Corrección', 'field': 'Correccion', 'editable': False},
                                    {'headerName': 'Selec.', 'field': 'Selec','editable': True, 'cellRenderer': 'agCheckboxCellRenderer'},
                                    {'headerName': 'Prof. inf.', 'field': 'Prof_inf', 'editable': True, 'cellEditor': 'agTextCellEditor'},
                                    {'headerName': 'Prof. sup.', 'field': 'Prof_sup', 'editable': True, 'cellEditor': 'agTextCellEditor'},
                                    {'headerName': 'Delta', 'field': 'Delta', 'editable': True, 'cellEditor': 'agTextCellEditor'},
                                ], # Inicialmente vacío
                        defaultColDef={
                            'flex': 1,  # Ajustar el ancho de las columnas para que ocupen el ancho disponible
                            'minWidth': 100,  # Ancho mínimo de cada columna
                            'resizable': True,
                            'wrapHeaderText': True,  # Ajuste automático de encabezado si es necesario
                            'autoSizeAllColumns': True  # Ajustar automáticamente todas las columnas
                        },
                        columnSize='responsiveSizeToFit',
                        dashGridOptions={
                            'getRowHeight': 'function(params) { return 40; }'  # Altura fija de 40 píxeles
                        },
                        style={'width': '100%', 'height': '220px'}  # Altura inicial
                    ),
                    # botón para Refrescar sugerencias
                    # separación
                    html.Div(style={"height": "20px"}),
                    dmc.Group(
                        children=[
                            dmc.Col(
                                html.H4("Sugerir correcciones"),
                                span=6
                            ),
                            dmc.Col(
                                dmc.Button("Sugerir", id="sugerir_bias", c="blue", variant="outline"),
                                span=2
                            )
                        ],
                        ta='center',
                        style={'marginBottom': '20px'}
                    ),
                    html.Div(style={"height": "20px"}),
                    html.Hr(style={"borderTop": "2px solid black", "width": "100%", "margin": "20px 0","borderBottom": "none"}),  # Línea divisoria
                    # botón para aplicar los cambios de bias
                    dmc.Group(
                        children=[
                            dmc.Col(
                                html.H4("Aplicar cambios Spikes y Bias", style={"fontWeight": "bold"}),  # Negrita
                                span=6
                            ),
                            dmc.Col(
                                dmc.Button("Guardar cambios", id="save_json", style={"backgroundColor": "#4c78af",  # Azul más suave
                                                                           "color": "white",  # Texto en blanco para contraste
                                                                           "border": "none",  # Quita el borde del botón
                                                                           "fontSize": "1rem",  # Tamaño de fuente un poco más grande
                                                                           "padding": "12px 24px",  # Aumenta el tamaño del botón (20% más grande)
                                                                           }),
                                span=2
                            ),
                            dmc.Modal(
                                id="guardar-modal",
                                title="Confirmación",
                                children=[
                                    html.Div(id="guardar-mensaje"),
                                    dmc.Button("Cerrar", id="cerrar-guardar-modal", variant="outline",
                                               style={"marginTop": "10px"})
                                ],
                                centered=True,
                                size="md",
                                opened=False  # Inicialmente cerrado
                            ),
                        ],
                        ta='center',
                        #style={'marginBottom': '20px'}
                        style={
                            'marginBottom': '20px',
                            'padding': '10px',  # Espaciado interno
                            'borderRadius': '8px',  # Bordes redondeados
                            'backgroundColor': 'rgba(173, 216, 230, 0.5)'  # Azul claro con transparencia
                        }
                    ),

                ], span=4, style={'padding': '0', 'margin': '0'}), # definición de la columna de la tabla, ancho 4
            ], style={'width': '100%', 'display': 'flex', 'flexWrap': 'nowrap'}),

        ])
    )


# Registra los callbacks en lugar de definir un nuevo Dash app
def register_callbacks(app):
    # función para cargar la tablas y div ocultos con la información del archivo json del incli
    # Callback combinado para procesar archivo JSON y guardar cambios en la tabla
    @app.callback(
        [Output('corregir-tubo', 'data'),
         Output('informacion-archivo', 'children'),
         Output('corregir_archivo', 'data'),
         Output('tabla-json', 'columnDefs'),
         Output('tabla-json', 'rowData'),
         Output('tabla_inicial', 'data'),
         Output('camp_a_graficar', 'data'),
         Output('camp_a_graficar', 'value'),
         Output("guardar-cambios-tabla", "opened"),
         Output("guardar-mensaje-tabla", "children")],
        [Input('archivo-uploader', 'contents'),
         Input("guardar_tabla", "n_clicks"),
         Input("cerrar-cambios-tabla", "n_clicks")],
        [State('archivo-uploader', 'filename'),
         State("tabla-json", "rowData"),
         State('log_cambios', "data"),
         State('corregir-tubo', 'data'),
         State('corregir_archivo', 'data')],
        prevent_initial_call=True
    )
    def manejar_archivo_y_guardar(contents, guardar_clicks, cerrar_clicks, filename, tabla_json, log_cambios, corregir_tubo, nombre_archivo):
        # Explicación función
        # Outputs:
            # corregir-tubo/data: archivo json, bien de la carga inicial, como los cambios
            # informacion-archivo/children: aclarar para qué es
            # corregir_archivo/data: idem
            # tabla-json/columDefs: formato de la aggrid
            # tabla-json/rodData: datos de la aggrid
            # tabla_inicial/data: aclarar qué es
            # camp_a_graficar/data: aclarar
            # camp_a_graficar/value: fecha
            # guardar-cambios-tabla/ opnened y children: ventana emergente
        # Inputs:
            # archivo-uploader/contents: archivo que se carga desde el uploader
            # guardar_tabla/n_clicks: botón. Acciones:
            # cerrar-cambios-tabla/n-clicks. Acciones:
        # State
            # archivo-uploader/filename. Se usa para la carga del archivo.
            # tabla-json/rowData: datos actuales de la tabla
            # log-cambios/data: acciones a realizar. Realmente se podría quitar, pero conviene por claridad de las acciones a realizar
            # corregir-tubo/data: archivo json. Ojo también es un output
            # corregir_archivo/data: nombre del archivo. ES PARA LOCAL, EN TD HAY QUE AJUSTARLO A LA BBDD QUE SE USE


        ctx = callback_context
        if not ctx.triggered:
            raise dash.exceptions.PreventUpdate

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # Procesamiento del archivo JSON si se ha subido
        if trigger_id == 'archivo-uploader' and contents is not None:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            try:
                data = json.loads(decoded)
                corregir_tubo_data = data
                informacion_archivo = html.Span([
                    html.B("Inclinómetro: "),
                    html.Span(data['info']['nom_sensor'])])
                corregir_archivo_data = filename


                if isinstance(data, dict):
                    # se cargan los datos del archivo para la tabla
                    fechas = sorted([key for key in data.keys() if key != 'info' and key != 'umbrales'], reverse=True)

                    datos_del_json = tabla_del_json(data, fechas)

                    # se definen las columnas aggrid

                    columnDefs = [
                        {'headerName': 'Fecha', 'field': 'Fecha', 'editable': False, 'resizable': True},
                        {'headerName': 'Referencia', 'field': 'Referencia', 'editable': True,
                         'cellEditor': 'agSelectCellEditor', 'cellEditorParams': {'values': [True, False]},
                         'resizable': True},
                        {'headerName': 'Activa', 'field': 'Activa', 'editable': True,
                         'cellEditor': 'agSelectCellEditor', 'cellEditorParams': {'values': [True, False]},
                         'resizable': True},
                        {'headerName': 'Cuarentena', 'field': 'Cuarentena', 'editable': True,
                         'cellEditor': 'agSelectCellEditor', 'cellEditorParams': {'values': [True, False]},
                         'resizable': True},
                        {'headerName': 'Correc Spike', 'field': 'spike', 'editable': False, 'resizable': True},
                        {'headerName': 'Correc Bias', 'field': 'bias', 'editable': False, 'resizable': True},
                        {'headerName': 'Limpiar', 'field': 'Limpiar', 'editable': True,
                         'cellEditor': 'agCheckboxCellEditor', 'resizable': True},
                    ]

                    # Almacenar los valores iniciales de la tabla-json en tabla_inicial
                    tabla_inicial = {row['Fecha']: row for row in datos_del_json}
                    camp_a_graficar_data = [{'value': fecha, 'label': fecha} for fecha in fechas]
                    camp_a_graficar_value = fechas[0] if fechas else ''  # Selecciona la fecha más reciente
                return corregir_tubo_data, informacion_archivo, corregir_archivo_data, columnDefs, datos_del_json, tabla_inicial, camp_a_graficar_data, camp_a_graficar_value, dash.no_update, dash.no_update
            except Exception as e:
                return dash.no_update, "Error al procesar el archivo", dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        # Lógica para guardar cambios de la tabla
        if trigger_id == "guardar_tabla":
            # primero se comprueba que hay acciones a realizar
            if not log_cambios:
                # error, no hay ninguna acción seleccionada
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, True, "No hay cambios a aplicar"

            # paso la tabla_json a un df
            df_tabla_json = pd.DataFrame(tabla_json)

            # Control de fallos: la primera campaña debe ser Referencia y debe haber una campaña que sea Active y Referencia
            control_de_fallos = False

            # construyo la tabla_json desde el archivo cargado
            fechas = sorted([key for key in corregir_tubo.keys() if key != 'info' and key != 'umbrales'], reverse=True)
            tabla_original = tabla_del_json(corregir_tubo, fechas)
            df_original = pd.DataFrame(tabla_original) # df del json original, sin cambios en la tabla

            # Crear una copia simulada del DataFrame original
            df_simulado = df_tabla_json.copy()


            # Aplicar los cambios simulados
            for key, cambio in log_cambios.items():
                fecha = cambio['fecha']
                clave = cambio['clave']
                nuevo_valor = cambio['new_value']

                # Buscar las filas que coinciden con la fecha
                indices = df_simulado.index[df_simulado['Fecha'] == fecha]
                df_simulado.loc[indices, clave] = nuevo_valor

            # HAGO UN CONTROL INICIAL DE FALLOS EN LOS CAMBIOS A APLICAR. HAY QUE DARLE UNA VUELTA

            # Verificar que la última fila tenga 'Referencia' en True
            if not df_simulado.iloc[-1]['Referencia']:
                error_message = "Error: La última fila debe tener 'Referencia' activada (True)."
                control_de_fallos = True
                print(error_message)
                # Aquí puedes manejar el error, por ejemplo, lanzando una excepción o retornando

            # Verificar que exista al menos una campaña con Referencia y Activa = True
            if df_simulado[(df_simulado['Referencia'] == True) & (df_simulado['Activa'] == True)].empty:
                print("Error: Tras aplicar los cambios simulados, no existe ninguna campaña que tenga Referencia y Activa en True.")
                control_de_fallos = True
                error_message = error_message + "Error: Tras aplicar los cambios simulados, no existe ninguna campaña que tenga Referencia y Activa en True."

            # Verifica que no hay una campaña (activa = true y referencia = false) sin que antes haya una Referencia Activa

            # Suponiendo que df_simulado ya viene ordenado de:
            # fila 0: campaña más reciente ... fila (n-1): campaña más antigua

            valid_found = False  # Indicador de si ya se encontró una campaña con Activa y Referencia en True

            # Iteramos desde la última fila (la campaña más antigua) hasta la primera (la campaña más reciente)
            for i in range(len(df_simulado) - 1, -1, -1):
                row = df_simulado.iloc[i]

                # Solo consideramos las campañas activas
                if row['Activa']:
                    if row['Referencia']:
                        # Esta campaña es válida, la guardamos para futuras comparaciones.
                        valid_found = True
                    else:
                        # Esta campaña es Activa=True y Referencia=False.
                        # Debe existir, en las campañas "anteriores en el tiempo" (ya recorridas en el bucle),
                        # al menos una campaña válida.
                        if valid_found:
                            print(f"Condición cumplida en la fila {i} (Fecha: {row['Fecha']}): "
                                  "se encontró una campaña anterior válida (Activa=True y Referencia=True).")
                            break  # Se cumple la condición, salimos del bucle
                        else:
                            error_message = (f"Error en la fila {i} (Fecha: {row['Fecha']}): "
                                             "es Activa=True y Referencia=False, pero no hay campaña anterior válida.")
                            print(error_message)
                            control_de_fallos = True
                            break  # Salimos del bucle al detectar el error


            if control_de_fallos:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, True, error_message
            # FIN CONTROL INICIAL DE FALLOS A APLICAR

            # INICIO APLICACIÓN CAMBIOS EN LA TABLA

            # se crea el diccionario 'acciones' que recoge lo que hay que hacer en cada campaña del tubo (tabla_json)
            acciones = {}
            # explicar estructura del diccionario
            recalcular_todos_siguientes = False # variable de control
            fecha_ref_cambio = df_simulado['Fecha'].min() # inicializo con la fecha más antigua
            for fila in range(len(df_tabla_json) - 1, -1, -1):
                # Obtener las filas correspondientes de cada DataFrame
                fila_json = df_original.iloc[fila]
                fila_simulado = df_simulado.iloc[fila]
                fecha = fila_simulado['Fecha']

                # Inicialmente se fija recalcular y limpiar = False para cada campaña
                valor_recalcular = False
                bool_referencia = False
                bool_cuarentena = False
                bool_activa = False
                valor_limpiar = False
                valor_cambios = False

                # Se evalúa la condición para determinar 'cambiar' y 'valor' en [fecha][cambios_camp][referencia]
                if fila_simulado['Referencia'] != fila_json['Referencia']:
                    bool_referencia = True
                    valor_referencia = fila_simulado['Referencia']
                    # En este caso implica que todas las campañas posteriores tienen que ser recalculadas y con cambios a cero
                    recalcular_todos_siguientes = True
                else:
                    valor_referencia = fila_json['Referencia']

                # Idem con [fecha][cambios_camp][activa]
                if fila_simulado['Activa'] != fila_json['Activa']:
                    # se determina si es una campaña independiente
                    if not camp_independiente(fecha, df_simulado):
                        # Esta campaña cambia el resto
                        recalcular_todos_siguientes = True
                    # cambio en activa
                    bool_activa = True
                    valor_activa = fila_simulado['Activa']
                    # se recalcula la campaña
                    valor_recalcular = True
                else:
                    # no cambia el estado
                    valor_activa = fila_json['Activa']

                # Idem con [fecha][cambios_camp][cuarentena]
                if fila_simulado['Cuarentena'] != fila_json['Cuarentena']:
                    # sólo se cambia el valor, no influye en más
                    bool_cuarentena = True
                    valor_cuarentena = fila_simulado['Cuarentena']
                    valor_cambios = True
                else:
                    valor_cuarentena = fila_json['Cuarentena']

                # Idem con [fecha][cambios_camp][limpiar]
                if fila_simulado['Limpiar'] == True:
                    # Hay que ver si es independiente
                    if not camp_independiente(fecha, df_tabla_json):
                        # Esta campaña cambia el resto
                        recalcular_todos_siguientes = True
                    # se escribe el cambio en el diccionario
                    valor_limpiar = True
                    valor_recalcular = True

                # Establecemos el valor de recalcular en el caso de recalcular_todos_siguientes
                if recalcular_todos_siguientes:
                    valor_recalcular = True

                # Estado de limpiar
                if valor_recalcular or recalcular_todos_siguientes:
                    valor_limpiar = True
                    valor_cambios = True

                # actualizo la referencia para esta campaña
                if fila_simulado['Referencia'] == True:
                    fecha_ref_cambio = fecha

                # Dentro de cada fecha, se crean las subclaves con sus respectivos elementos
                acciones[fecha] = {
                    'cambios_camp': {
                        'referencia': {
                            'bool_referencia': bool_referencia,
                            'valor_referencia': valor_referencia
                        },
                        'activa': {
                            'bool_activa': bool_activa,
                            'valor_activa': valor_activa,
                        },
                        'cuarentena': {
                            'bool_cuarentena': bool_cuarentena,
                            'valor_cuarentena': valor_cuarentena,
                        },
                        'limpiar': valor_limpiar
                    },
                    'recalcular': valor_recalcular,
                    'ref_cambio': fecha_ref_cambio,
                    'cambios': valor_cambios # está pensado para usarse en el momento de guardar los cambios. Evito tocar todo el archivo
                }

            # Ejecuto las acciones, recorriendo todas las campañas de antiguas a nuevas
            for fila in range(len(df_tabla_json) - 1, -1, -1):
                # fecha
                fecha = df_original.iloc[fila]['Fecha']
                # Evalúa si hay cambios a realizar en esa campaña
                if acciones[fecha]['cambios']:
                    # Se aplican los cambios
                    # Cambios 1/3. Se reescribe el bloque 'campaign info'
                    # reference
                    if acciones[fecha]['cambios_camp']['referencia']['bool_referencia']:
                        print('fecha', fecha,'valoor bool',acciones[fecha]['cambios_camp']['referencia']['bool_referencia'] )
                        corregir_tubo[fecha]['campaign_info']['reference'] = acciones[fecha]['cambios_camp']['referencia']['valor_referencia']

                    # active
                    if acciones[fecha]['cambios_camp']['activa']['bool_activa']:
                        corregir_tubo[fecha]['campaign_info']['active'] = acciones[fecha]['cambios_camp']['activa']['valor_activa']

                    # quarentine
                    if acciones[fecha]['cambios_camp']['cuarentena']['bool_cuarentena']:
                        corregir_tubo[fecha]['campaign_info']['quarentine'] = acciones[fecha]['cambios_camp']['cuarentena']['valor_cuarentena']

                    # Cambios 2/3. Recalculo si procede
                    if acciones[fecha]['recalcular']:
                        fecha_referencia = acciones[fecha]['ref_cambio']
                        # hay que meter en 'calc' los valores de a0-b180 calculados desde raw
                        calc_entries = []
                        # constante de conversión
                        cte = corregir_tubo[fecha]['campaign_info']['instrument_constant']
                        # recorre el diccionario 'raw' de corregir_tubo y obtiene los valores directos de la campaña
                        for i, item in enumerate(corregir_tubo[fecha]["raw"]):
                            entry = valores_calc_directos(  # función externa utils/funciones_comunes.py
                                item['index'], item['cota_abs'], item['depth'],
                                item['a0'], item['a180'], item['b0'], item['b180'], cte)
                            calc_entries.append(entry)
                        # inserto el nuevo 'calc' en el archivo del tubo
                        corregir_tubo[fecha]['calc'] = calc_entries
                        # se obtienen los valores calculados en función de la referencia. Ojo correcciones es todo el tubo
                        corregir_tubo = calcular_incrementos(corregir_tubo, fecha, fecha_referencia)  # función externa utils/funciones_comunes.py
                    # Cambios 3/3. Limpio las correcciones si se elige limpiar o hay que recalcular
                    if acciones[fecha]['cambios_camp']['limpiar']:
                        # borro todas las correcciones.
                        corregir_tubo[fecha]['spike'] = None
                        corregir_tubo[fecha]['bias'] = None
                else:
                    # no hay cambios
                    pass


            # GUARDO LOS CAMBIOS EN EL ARCHIVO JSON. OJO, EN ESTE CASO LO REESCRIBO ENTERO
            # AL PASARLO A TD ESTO HAY QUE VER CÓMO SE HACE

            # Ruta del script - FUNCIONAMIENTO EN LOCAL
            ruta_script = Path(__file__).resolve().parent.parent  # Sube un nivel desde 'pages'
            ruta_data = ruta_script / "data"  # Ahora apunta a 'IncliData/data'

            # Nombre del archivo JSON
            ruta_json = ruta_data / nombre_archivo

            # Sobrescribir completamente el archivo JSON
            with open(ruta_json, "w", encoding="utf-8") as f:
                with open(ruta_json, "w", encoding="utf-8") as f:
                    json.dump(corregir_tubo, f, ensure_ascii=False, indent=4,
                              default=lambda o: o.item() if hasattr(o, 'item') else o)


            return (corregir_tubo, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,dash.no_update, True, "Guardados los cambios")
        elif trigger_id == "cerrar-cambios-tabla":
            return (dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,dash.no_update,False, dash.no_update)  # Cierra el modal sin cambiar el mensaje

    @app.callback(
        Output("json_spikes", "data"),  # Update the "json_spikes" Store
        [Input("corregir-tubo", "data"), # archivo json data
         Input("spikes-table", "cellValueChanged"),# Listen for changes in the table
         Input("camp_a_graficar", "value")],  # campaña a graficar
        [State("spikes-table", "rowData"),  # Current data of the table
        #State("json_spikes", "data") # Existing data in "json_spikes"
         ]
    )

    def cambio_json_spikes(data, cellValueChanged, camp_graficar, table_data):#, camp_corregida):
        # se guarda el "calc" modificado y las profundidades en las que se realiza un corrección de spk
        # el registro de correcciones se guarda en la clave "spike": {"A": [], "B": []}
        if camp_graficar == None:
            # no hay nada cargado
            return dash.no_update

        if not table_data or all((not fila.get("A")) and (not fila.get("B")) for fila in table_data):
            # no hay corrección puntual o no se ha seleccionado nada en A y B. Carga el valor original
            resultado = {camp_graficar: {"calc": data[camp_graficar]['calc']}}
            return resultado
        # Caso 1. hay cambios en spikes
        # Inicializar el diccionario final
        correccion = {camp_graficar: {"calc": [], "spike": {"A": [], "B": []}}}

        # Iterar sobre cada elemento en data_table
        for item in table_data:
            # Crear una nueva entrada con los valores requeridos
            # debe haber coherencia con la construcción del diccionario del tubo (json)
            indice = next((entry['index'] for entry in data[camp_graficar]["calc"] if entry['depth'] == item["Profundidad"]), None)
            cota = next((entry['cota_abs'] for entry in data[camp_graficar]["calc"] if entry['depth'] == item["Profundidad"]), None)
            nueva_entrada = {
                "index": indice,
                "cota_abs": cota,
                "depth": item["Profundidad"],
                #"A_spk": item["A"], # esto originalmente no está en 'calc'
                #"B_spk": item["B"], # esto originalmente no está en 'calc'
                "a0": item["a0_c"] if item["A"] else item["a0"],
                "a180": item["a180_c"] if item["A"] else item["a180"],
                "b0": item["b0_c"] if item["B"] else item["b0"],
                "b180": item["b180_c"] if item["B"] else item["b180"],
            }
            # Añadir la nueva entrada al diccionario
            correccion[camp_graficar]["calc"].append(nueva_entrada)
            # si hay correcciones, se guarda el registro
            if item["A"]:
                correccion[camp_graficar]["spike"]["A"].append({
                    "index":  indice,
                    "cota_abs": cota,
                    "depth": item["Profundidad"],
                    "A_spk": True
                })
            if item["B"]:
                correccion[camp_graficar]["spike"]["B"].append({
                    "index":  indice,
                    "cota_abs": cota,
                    "depth": item["Profundidad"],
                    "B_spk": True
                })
        # Calcular dev_a después de crear las entradas
        for entrada in correccion[camp_graficar]["calc"]:
            entrada["dev_a"] = round((entrada["a0"] - entrada["a180"]) / 2, 2)
            entrada["dev_b"] = round((entrada["b0"] - entrada["b180"]) / 2, 2)
            #entrada["checksum_a"] = round(entrada["a0"] + entrada["a180"], 4), # eliminado al pasar de chk a incr_check
            #entrada["checksum_b"] = round(entrada["b0"] + entrada["b180"], 4)
        # busco referencia
        fecha_referencia = buscar_referencia(data, camp_graficar)
        data_new = {
            fecha_referencia: {"calc": data[fecha_referencia]['calc']},
            camp_graficar: {"calc": correccion[camp_graficar]['calc'], "spike": correccion[camp_graficar]['spike']}
        }
        # para calcular_incrementos hace falta meter todo el histórico
        dic_temporal = data.copy()
        dic_temporal[camp_graficar]['calc'] = correccion[camp_graficar]['calc']

        resultado = calcular_incrementos(dic_temporal, camp_graficar, fecha_referencia)

        # Control de ejecución
        debug_funcion('cambios_json_spikes')

        # provisional para ver el resultado de forma externa
        # Crear el diccionario
        #data = {camp_graficar: {"spike": correccion[camp_graficar]['spike']}}
        data = {camp_graficar: {"calc": resultado[camp_graficar]['calc'], "spike": correccion[camp_graficar]['spike']}}

        # Obtener la ruta del script y agregar el nombre del archivo
        ruta_script = os.path.dirname(os.path.abspath(__file__))  # Ruta del script
        ruta_archivo = os.path.join(ruta_script, "spikes.json")  # Archivo JSON en la misma carpeta
        print ("json_spikes guardado")

        # Guardar el JSON
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


        return {camp_graficar: {"calc": resultado[camp_graficar]['calc'], "spike": correccion[camp_graficar]['spike']}}

    # Callback para manejar cambios en la tabla y guardar el log_cambios
    @app.callback(
        Output('log_cambios', 'data'),
        Output('log-cambios', 'children'),
        Input('tabla-json', 'cellValueChanged'),
        Input('corregir-tubo', 'data'),
        State('log_cambios', 'data'),
        State('tabla_inicial', 'data')
    )
    def registrar_cambios(cell_value_changed, corregir_tubo, log_cambios, tabla_inicial):
        if cell_value_changed is None:
            raise dash.exceptions.PreventUpdate

        # si corregir_tubo, significa que o se cargó un nuevo tubo o se modificó, se debe borrar el log_cambios
        triggered_input = callback_context.triggered[0]['prop_id'].split('.')[0]
        if triggered_input == 'corregir-tubo':
            return {}, {}


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

        # Control de ejecución
        debug_funcion('registrar_cambios')

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
    # cambiar el nombre a la función: graficos_1
    @app.callback(
        [Output("corr_grafico_incli_1_a", "figure"),
         Output("corr_grafico_incli_1_b", "figure"),
         Output("corr_grafico_incli_2_a", "figure"),
         Output("corr_grafico_incli_2_b", "figure"),
         Output("corr_grafico_incli_3_a", "figure"),
         Output("corr_grafico_incli_3_b", "figure"),
         Output("corr_grafico_incli_3_total", "figure")],
        [Input("corregir-tubo", "data"), # archivo json data
         Input("json_spikes", "data"), # valores temporales de la campaña corregida
         Input("json_bias", "data"),  # valores temporales de la campaña de bias
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
    def corr_grafico_1(data, camp_corregida, corr_bias, fecha_seleccionada, fechas_incli, camp_previas, alto_graficos, color_scheme,
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

        fechas_activas = [fecha for fecha in data.keys()
                          if isinstance(data[fecha], dict) and 'campaign_info' in data[fecha]
                          and data[fecha]['campaign_info'].get('active') == True]

        # Si no hay fechas activas, devolver un diccionario vacío

        if not fechas_activas:
            return {}
        #series_a_graficar = [item['value'] for item in fechas_incli if item['value'] <= fecha_seleccionada]
        series_a_graficar = sorted([fecha for fecha in fechas_activas if fecha <= fecha_seleccionada], reverse=True)
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
                depth_list = [punto["depth"] for punto in data[fecha]["calc"]] # cambio de concepto de versión inicial
                desp_a_list = [punto["desp_a"] for punto in data[fecha]["calc"]]
                desp_b_list = [punto["desp_b"] for punto in data[fecha]["calc"]]
                incr_dev_a_list = [punto["incr_dev_a"] for punto in data[fecha]["calc"]]
                incr_dev_b_list = [punto["incr_dev_b"] for punto in data[fecha]["calc"]]
                #desp_total_list = [punto["desp_a"] + punto["desp_b"] for punto in data[fecha]["calc"]]
                desp_total_list = [round(math.sqrt(punto["desp_a"] ** 2 + punto["desp_b"] ** 2), 2) for punto in
                                   data[fecha]["calc"]]
                eje_y = depth_list  # por facilidad para hacer pruebas
                # Gráfico 1: Desplazamientos
                fig1_a.add_trace(go.Scatter(x=desp_a_list, y=eje_y, mode="lines", name=f"{fecha} - Desp A",
                                            line=dict(c=color, width=grosor), legendgroup=fecha,
                                            opacity=opacity))
                fig1_b.add_trace(go.Scatter(x=desp_b_list, y=eje_y, mode="lines", name=f"{fecha} - Desp B",
                                            line=dict(c=color, width=grosor), legendgroup=fecha,
                                            opacity=opacity))

                # Gráfico 2: Incrementales
                fig2_a.add_trace(
                    go.Scatter(x=incr_dev_a_list, y=eje_y, mode="lines", name=f"{fecha} - Incr Dev A",
                               line=dict(c=color, width=grosor), legendgroup=fecha, opacity=opacity))
                fig2_b.add_trace(
                    go.Scatter(x=incr_dev_b_list, y=eje_y, mode="lines", name=f"{fecha} - Incr Dev B",
                               line=dict(c=color, width=grosor), legendgroup=fecha, opacity=opacity))

                # Gráfico 3: Desplazamientos Compuestos
                fig3_a.add_trace(go.Scatter(x=desp_a_list, y=eje_y, mode="lines", name=f"{fecha} - Desp A",
                                            line=dict(c=color, width=grosor), legendgroup=fecha,
                                            opacity=opacity))
                fig3_b.add_trace(go.Scatter(x=desp_b_list, y=eje_y, mode="lines", name=f"{fecha} - Desp B",
                                            line=dict(c=color, width=grosor), legendgroup=fecha,
                                            opacity=opacity))
                fig3_total.add_trace(
                    go.Scatter(x=desp_total_list, y=eje_y, mode="lines", name=f"{fecha} - Desp Total",
                               line=dict(c=color, width=grosor), legendgroup=fecha, opacity=opacity))
        # agrego la campaña con las correcciones de bias, en línea discontínua
        # el motivo de agregarla es que cuando hay cambio de referencia, no se ve el resultado final
        # sólo se agrega en caso de que haya correcciones y sólo en "Desplazamientos"
        if corr_bias[fecha_seleccionada]['bias']:
            fecha = fecha_seleccionada
            color = 'red'
            grosor = 4
            opacity = 1.0

            # profundidades
            cota_abs_list = [punto["cota_abs"] for punto in corr_bias[fecha_seleccionada]["calc"]]

            print ('bias corregido')
            bias_list = corr_bias[fecha_seleccionada]['bias']  # Extrae la lista de bias
            # bias A
            if next((item['Selec'] for item in bias_list if item['Correccion'] == 'Bias_1_A'), None) or next((item['Selec'] for item in bias_list if item['Correccion'] == 'Bias_2_A'), None):
                # inserto la campaña A con correcciones
                desp_a_list = [punto["desp_a_corr"] for punto in corr_bias[fecha_seleccionada]["calc"]]
                fig1_a.add_trace(go.Scatter(x=desp_a_list, y=eje_y, mode="lines", name=f"{fecha} - Desp A_corr",
                    line=dict(
                        c=color,  # Puedes usar un color en formato string o hexadecimal
                        width=grosor,  # Aumenta el grosor de la línea (valores más altos = más grueso)
                        dash="dash"  # Define el estilo de la línea (puede ser "dash", "dot", "dashdot", etc.)
                    ),
                    legendgroup=fecha,
                    opacity=opacity
                ))
            # bias B
            if next((item['Selec'] for item in bias_list if item['Correccion'] == 'Bias_1_B'), None) or next((item['Selec'] for item in bias_list if item['Correccion'] == 'Bias_2_B'), None):
                # inserto la campaña B con correcciones
                desp_b_list = [punto["desp_b_corr"] for punto in corr_bias[fecha_seleccionada]["calc"]]
                fig1_b.add_trace(go.Scatter(x=desp_b_list, y=eje_y, mode="lines", name=f"{fecha} - Desp B_corr",
                                            line=dict(
                                                c=color,  # Puedes usar un color en formato string o hexadecimal
                                                width=grosor,
                                                # Aumenta el grosor de la línea (valores más altos = más grueso)
                                                dash="dash"
                                                # Define el estilo de la línea (puede ser "dash", "dot", "dashdot", etc.)
                                            ),
                                            legendgroup=fecha,
                                            opacity=opacity
                                            ))



        # Luego agregar la serie seleccionada (= corregida temporal) para que quede encima
        if fecha_seleccionada in series_a_graficar: # este condicional sobra
            fecha = fecha_seleccionada
            color = 'darkblue'
            grosor = 4
            opacity = 1.0
            # marker = dict(size=4, c='yellow', symbol='circle')
            # se pasa a una lista el diccionario
            cota_abs_list = [punto["cota_abs"] for punto in camp_corregida[fecha]["calc"]]
            desp_a_list = [punto["desp_a"] for punto in camp_corregida[fecha]["calc"]]
            desp_b_list = [punto["desp_b"] for punto in camp_corregida[fecha]["calc"]]
            incr_dev_a_list = [punto["incr_dev_a"] for punto in camp_corregida[fecha]["calc"]]
            incr_dev_b_list = [punto["incr_dev_b"] for punto in camp_corregida[fecha]["calc"]]
            #desp_total_list = [punto["desp_a"] + punto["desp_b"] for punto in camp_corregida[fecha]["calc"]]
            desp_total_list = [round(math.sqrt(punto["desp_a"] ** 2 + punto["desp_b"] ** 2), 2) for punto in
                               camp_corregida[fecha]["calc"]]

            # Gráfico 1: Desplazamientos
            fig1_a.add_trace(
                go.Scatter(x=desp_a_list, y=eje_y, mode="lines", name=f"{fecha} - Desp A",
                           line=dict(c=color, width=grosor),
                           # marker=marker,
                           legendgroup=fecha,
                           opacity=opacity))
            fig1_b.add_trace(
                go.Scatter(x=desp_b_list, y=eje_y, mode="lines", name=f"{fecha} - Desp B",
                           line=dict(c=color, width=grosor),
                           # marker=marker,
                           legendgroup=fecha,
                           opacity=opacity))

            # Gráfico 2: Incrementales
            fig2_a.add_trace(go.Scatter(x=incr_dev_a_list, y=eje_y, mode="lines",
                                        name=f"{fecha} - Incr Dev A",
                                        line=dict(c=color, width=grosor),
                                        # marker=marker,
                                        legendgroup=fecha, opacity=opacity))
            fig2_b.add_trace(go.Scatter(x=incr_dev_b_list, y=eje_y, mode="lines",
                                        name=f"{fecha} - Incr Dev B",
                                        line=dict(c=color, width=grosor),
                                        # marker=marker,
                                        legendgroup=fecha, opacity=opacity))

            # Gráfico 3: Desplazamientos Compuestos
            fig3_a.add_trace(
                go.Scatter(x=desp_a_list, y=eje_y, mode="lines", name=f"{fecha} - Desp A",
                           line=dict(c=color, width=grosor),
                           # marker=marker,
                           legendgroup=fecha,
                           opacity=opacity))
            fig3_b.add_trace(
                go.Scatter(x=desp_b_list, y=eje_y, mode="lines", name=f"{fecha} - Desp B",
                           line=dict(c=color, width=grosor),
                           # marker=marker,
                           legendgroup=fecha,
                           opacity=opacity))
            fig3_total.add_trace(go.Scatter(x=desp_total_list, y=eje_y, mode="lines",
                                            name=f"{fecha} - Desp Total",
                                            line=dict(c=color, width=grosor),
                                            # marker=marker,
                                            legendgroup=fecha, opacity=opacity))
        # añado la corrección tras el bias (el puntual lo coge antes)

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

        # Control de ejecución
        debug_funcion('corr_grafico_1')


        return [fig1_a, fig1_b, fig2_a, fig2_b, fig3_a, fig3_b, fig3_total]

    # Grupo de gráficos 2 - SPIKES
    @app.callback(
        [Output("corr_graf_spike_a", "figure"),
         Output("corr_graf_spike_b", "figure"),
         Output("corr_graf_stats_a", "figure")],
        [Input("corregir-tubo", "data"),  # archivo json data
         Input("json_spikes", "data"), # correccion de spikes
         Input("camp_a_graficar", "value"),  # fecha_seleccionada
         Input("camp_a_graficar", "data"),#  fechas_incli
         Input('n_spikes', "value"), #  campañas anteriores
         Input("correcciones_color_grafico1", "value"),# color
         Input('estadisticas_spikes', "value")]) # lo que se muestra en las estadísticas

    def graficos_spike(data, json_spikes, fecha_seleccionada, fechas, n_spikes, color_scheme, estadistica):
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
            #conjunto_fechas = conjunto_fechas[:int(n_spikes)+1] # añado 1 para que sean la selec + n_spikes
            conjunto_fechas = conjunto_fechas[1:int(n_spikes) + 1]  # añado 1 para que sean la selec + n_spikes, descarto la campaña seleccionada

        else:
            # cojo todas menos la seleccionada
            conjunto_fechas = conjunto_fechas[1:]

        # convertir los diccionarios en un dataframes
        dfs_1 = dict_a_df(json_spikes, ['a0', 'a180', 'b0', 'b180', 'incr_checksum_a', 'incr_checksum_b', 'incr_dev_a',
                                        'incr_dev_b'], [fecha_seleccionada])
        dfs_2 = dict_a_df(data, ['a0', 'a180', 'b0', 'b180', 'incr_checksum_a', 'incr_checksum_b', 'incr_dev_a',
                                 'incr_dev_b'], conjunto_fechas)

        # Concatenar y agrupar por índice para fusionar las filas duplicadas
        dfs = {
            key: pd.concat([dfs_1[key], dfs_2[key]], axis=0)
            .groupby(level=0)  # Agrupa por índice (profundidad)
            .first()  # Puedes usar .sum(), .mean(), o .first() según el criterio deseado
            for key in dfs_1
        }

        # los valores del json_spikes que vienen corregidos de la tabla vienen en formato lista, en lugar de número
        # Función para convertir listas a valores numéricos
        def limpiar_valores(columna):
            return columna.apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else x)

        # Aplicar la transformación a todos los DataFrames en el diccionario
        dfs = {key: df.apply(limpiar_valores) for key, df in dfs.items()}

        # creo los gráficos
        fig1_a = go.Figure()
        fig1_b = go.Figure()

        # vuelvo a añadir la fecha seleccionada
        conjunto_fechas = [fecha_seleccionada] + conjunto_fechas

        camp_previas = len(conjunto_fechas)

        # Añado las gráficas seleccionadas
        for fecha in conjunto_fechas:

            index = conjunto_fechas.index(fecha)
            color = get_color_for_index(index, color_scheme, camp_previas)
            grosor = 2
            opacity = 0.7

            # Gráfico 1: icnre Checksums
            fig1_a.add_trace(go.Scatter(x=dfs['incr_checksum_a'][fecha], y=dfs['incr_checksum_a'].index, mode="lines",
                                        name=f"{fecha} - Incr CheckSum A",
                                        line=dict(c=color, width=grosor), legendgroup=fecha,
                                        opacity=opacity))
            fig1_b.add_trace(go.Scatter(x=dfs['incr_checksum_b'][fecha], y=dfs['incr_checksum_b'].index, mode="lines",
                                        name=f"{fecha} - Incr CheckSum B",
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
        # títulos
        #fig1_a.update_layout(xaxis_title='CheckSum A')
        #fig1_b.update_layout(xaxis_title='CheckSum B')
        # Control de ejecución
        debug_funcion('graficos_spike')

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

    # Populate the spike_profundidad dropdown
    @app.callback(
        Output('spike_profundidad', 'data'),
        Input('corregir-tubo', 'data')
    )
    def update_dropdown(data):
        if not data:
            return []
        # Extract depths from the corregir-tubo dictionary
        depths = [item['depth'] for key, value in data.items() if 'calc' in value for item in value['calc']]
        # Obtener valores únicos y ordenarlos
        unique_depths = sorted(set(depths))
        return [{'value': depth, 'label': f"{depth} m"} for depth in unique_depths]

    # Load temporal data for selected depths and show in modal
    # Load temporal data for selected depths and show in modal
    @app.callback(
        [Output('temporal-spike-modal', 'opened'),
         Output('temporal-spike-graph', 'figure')],
        [Input('temporal_spike', 'n_clicks'),
         Input('temporal-spike-variables', 'value')],  # Entrada del multiselect
        [State('spike_profundidad', 'value'),
         State('corregir-tubo', 'data'),
         State("json_spikes", "data"),  # valores temporales de la campaña corregida
         State("camp_a_graficar", "data"),  # lista de fechas
         State("camp_a_graficar", "value")]  # fecha_seleccionada
    )
    def emergente_spike(n_clicks, selected_vars, selected_depths, data, camp_corregida, fechas, fecha_seleccionada):
        # Valores por defecto para selected_vars
        # default_vars = ["checksum_a", "checksum_b"]

        # Si no se ha hecho clic en el botón o faltan datos, no actualizar
        if not n_clicks or not selected_depths or not data:
            return False, go.Figure()

        # Filtrar las fechas desde el inicio hasta la fecha seleccionada
        conjunto_fechas = [fecha['value'] for fecha in fechas if
                           'value' in fecha and fecha['value'] <= fecha_seleccionada
                           and data[fecha['value']]['campaign_info']['active'] == True]

        # Inserto la clave 'calc' corregida en el archivo del tubo
        data[fecha_seleccionada]['calc'] = camp_corregida[fecha_seleccionada]['calc']

        # Convertir el diccionario en un DataFrame
        dfs = dict_a_df(data, selected_vars, conjunto_fechas)

        # Crear la figura
        figure = go.Figure()

        # Iterar sobre las variables seleccionadas y profundidades
        if not selected_vars:
            return True, figure
        else:
            # Paleta de colores minimalista
            color_palette = [
                '#1f77b4',  # Azul
                '#ff7f0e',  # Naranja
                '#2ca02c',  # Verde
                '#d62728',  # Rojo
                '#9467bd',  # Púrpura
                '#8c564b'  # Marrón
            ]

            # Identificar fechas de referencia
            fechas_referencia = []
            for fecha in data.keys():
                if (isinstance(data[fecha], dict) and
                        'campaign_info' in data[fecha] and
                        data[fecha]['campaign_info'].get('reference', False)):
                    fechas_referencia.append(fecha)

            var_index = 0
            for var in selected_vars:
                for depth in selected_depths:
                    # Extraer las fechas y los valores para 'depth'
                    fechas_data = dfs[var].columns
                    valores = dfs[var].loc[depth]

                    # Color para esta serie
                    color = color_palette[var_index % len(color_palette)]

                    # Traza principal con TODOS los valores (serie completa)
                    figure.add_trace(go.Scatter(
                        x=fechas_data,
                        y=valores,
                        mode='lines+markers',
                        name=f'{var} - Profundidad {depth}',
                        line=dict(c=color, width=2),
                        marker=dict(size=5, c=color),
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                      'Fecha: %{x}<br>' +
                                      'Valor: %{y:.4f}<br>' +
                                      '<extra></extra>'
                    ))

                    # Separar solo los valores de referencia para los marcadores especiales
                    valores_ref = []
                    fechas_ref = []

                    for fecha, valor in zip(fechas_data, valores):
                        if fecha in fechas_referencia:
                            valores_ref.append(valor)
                            fechas_ref.append(fecha)

                    # Marcadores especiales SOLO para fechas de referencia (encima de la serie)
                    if fechas_ref:
                        figure.add_trace(go.Scatter(
                            x=fechas_ref,
                            y=valores_ref,
                            mode='markers',
                            marker=dict(
                                size=10,
                                c='rgba(255, 255, 255, 0.9)',  # Blanco semi-transparente
                                symbol='diamond',
                                line=dict(width=2, c=color)  # Borde del mismo color que la serie
                            ),
                            hovertemplate='<b>REFERENCIA</b><br>' +
                                          f'{var} - Profundidad {depth}<br>' +
                                          'Fecha: %{x}<br>' +
                                          'Valor: %{y:.4f}<br>' +
                                          '<extra></extra>',
                            showlegend=False  # No aparece en la leyenda
                        ))

                    var_index += 1

            # Diseño minimalista y limpio
            figure.update_layout(
                title={
                    'text': "Serie Temporal para las Profundidades Seleccionadas",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 14, 'color': '#2c3e50'}
                },
                xaxis=dict(
                    title="Fecha",
                    title_font={'size': 12, 'color': '#34495e'},
                    showgrid=True,
                    gridwidth=0.5,
                    gridc='rgba(128, 128, 128, 0.1)',
                    showline=True,
                    linewidth=1,
                    linec='rgba(128, 128, 128, 0.3)'
                ),
                yaxis=dict(
                    title="Valor",
                    title_font={'size': 12, 'color': '#34495e'},
                    showgrid=True,
                    gridwidth=0.5,
                    gridc='rgba(128, 128, 128, 0.1)',
                    showline=True,
                    linewidth=1,
                    linec='rgba(128, 128, 128, 0.3)'
                ),
                template='plotly_white',
                hovermode='closest',
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=0.98,
                    xanchor="left",
                    x=1.02,
                    bgc="rgba(255, 255, 255, 0.95)",
                    borderc="rgba(128, 128, 128, 0.2)",
                    borderwidth=1,
                    font={'size': 10}
                ),
                margin=dict(l=60, r=140, t=50, b=50),
                plot_bgc='white',
                paper_bgc='white'
            )

            return True, figure

    # Función para rellenar por primera vez bias-table
    @app.callback(
        [Output('bias-table', 'rowData'), # valores por defecto de bias-table
         Output('bias-table-change-flag', 'data')], # controla la primera carga
        [Input("json_spikes", "data"),  # camp selecc con los cambios de spikes
         Input('empotramiento', 'value'),  # valor del empotramiento teórico
         Input("sugerir_bias", "n_clicks"),  # Botón para sugerir correcciones
         Input("camp_a_graficar", "value")],  # escucha los cambios de campaña
        [State("bias-table", 'rowData'),  # valores existentes en la bias-table
         State('corregir-tubo', 'data')],  # datos originales
    )
    def cambios_bias_table(corr_spikes,  empotramiento, sugerir, camp_a_graficar, bias_table, corregir_tubo):
        # Se desencadena en caso de que haya: corrección de spikes, cambio de empotramiento, botón de sugerir bias,
        # o cambio de campaña (o carga se supone)
        # faltaría meter un control de errores en caso de que empotramiento sea = 0 o mayor que la profundidad
        if corr_spikes: # esto es heredado, no sé si realmente es necesario
            # CASO I. Cuando se (carga una campaña) o (cambio de campaña) o (cambios en empotramiento) o (botón sugerir_bias)
            # Identificar si empotramiento fue el trigger
            triggered_input = callback_context.triggered[0]['prop_id'].split('.')[0]
            # Paso 1. Evalúa si es la primera carga para "sugerir" correcciones
            # paso los valores actuales de la tabla a un df, por comodidad
            df_bias_table = pd.DataFrame(bias_table)

            # Tomo como criterio para considerar que es la primera carga que la suma de las prof = 0
            if (df_bias_table['Prof_inf'].sum() + df_bias_table['Prof_sup'].sum()) == 0 or sugerir or triggered_input == 'empotramiento': # condición repetida?? si no hay correc o sugerir
                # Paso 1.a. Se calculan las correcciones sugeridas
                # a. Extraer la fecha seleccionada (primera clave del diccionario corr_spikes)
                fecha_selec = list(corr_spikes.keys())[0]

                # b. Buscar la fecha de referencia usando buscar_referencia
                fecha_referencia = buscar_referencia(corregir_tubo, fecha_selec)

                # c. extrae los diccionarios con valores de referencia y corrección
                calc_ref = corregir_tubo[fecha_referencia]['calc']  # datos de la campaña de referencia
                calc_corr = corr_spikes[fecha_selec]['calc']  # datos de la campaña a corregir

                # d. Crea df_bias con la estructura y cálculos
                df_bias = creacion_df_bias(calc_ref, calc_corr)

                # Control de errores en empotramiento, evita que sea <=0 o mayor que la profundidad
                if empotramiento > df_bias['depth'].max() or empotramiento <= 0:
                    # hay un error, no hace nada. Debería enviar un error
                    return dash.no_update

                # Paso 1.b. Correcciones sugeridas
                # Calculo el valor de incr en profundidad h-empotramiento m
                # se ha de suponer que este error se reproduce en el resto, independientemente del movimiento adicional que haya
                h = df_bias['depth'].iloc[-1]  # fondo del tubo
                # por defecto calcula para A y B. ojo, son el extremo superior de una recta con la pendiente avg del incr
                count = df_bias.loc[(df_bias['depth'] <= h), 'depth'].count()  # numero de pasos de sonda, inicialmente será toda la prof
                delta_a = round(df_bias.loc[df_bias['depth'] == h - empotramiento, 'avg_Incr_A'].iloc[0] * count, 2)
                delta_b = round(df_bias.loc[df_bias['depth'] == h - empotramiento, 'avg_Incr_B'].iloc[0] * count, 2)

                # se carga el df_bias_table con las profundidades y true/false
                # Por defecto, al cargar la tabla se calculan las sugerencias, pero se deja en False
                df_bias_table['Prof_inf'] = df_bias_table['Prof_inf'].astype(float)
                df_bias_table['Prof_sup'] = df_bias_table['Prof_sup'].astype(float)

                # Fila Bias_1_A
                df_bias_table.loc[0, 'Selec'] = True if sugerir else False
                df_bias_table.loc[0, 'Prof_inf'] = float(df_bias['depth'].max())
                df_bias_table.loc[0, 'Prof_sup'] = float(df_bias['depth'].min())
                df_bias_table.loc[0, 'Delta'] = delta_a # se introduce el valor de delta
                # Fila Bias_1_B
                df_bias_table.loc[1, 'Selec'] = True if sugerir else False
                df_bias_table.loc[1, 'Prof_inf'] = float(df_bias['depth'].max())
                df_bias_table.loc[1, 'Prof_sup'] = float(df_bias['depth'].min())
                df_bias_table.loc[1, 'Delta'] = delta_b  # se introduce el valor de delta
                # Fila Bias_2_A
                df_bias_table.loc[2, 'Selec'] = False
                df_bias_table.loc[2, 'Prof_inf'] = float(df_bias['depth'].min())
                df_bias_table.loc[2, 'Prof_sup'] = float(df_bias['depth'].min())
                df_bias_table.loc[2, 'Delta'] = 0.00
                # Fila Bias_2_B
                df_bias_table.loc[3, 'Selec'] = False
                df_bias_table.loc[3, 'Prof_inf'] = float(df_bias['depth'].min())
                df_bias_table.loc[3, 'Prof_sup'] = float(df_bias['depth'].min())
                df_bias_table.loc[3, 'Delta'] = 0.00



                # corrección
                """
                df_bias = calculos_bias(df_bias,
                                        df_bias['depth'].max(), df_bias['depth'].min(), df_bias['depth'].max(),df_bias['depth'].min(), delta_a, delta_b,
                                        0.5,0.5,0.5,0.5,0,0) # el segundo paso de corrección es cero
                
                df_bias = calculos_bias_1(df_bias, df_bias_table)
                """


                # Paso 1.c. Carga de valores en la tabla
                # evito un deprecated

                # Fila Bias_1_A
                #df_bias_table.loc[0, 'Selec'] = True
                #df_bias_table.loc[0, 'Prof_inf'] = float(df_bias['depth'].max())
                #df_bias_table.loc[0, 'Prof_sup'] = float(df_bias['depth'].min())
                #df_bias_table.loc[0, 'Delta'] = round(df_bias.loc[df_bias['depth'].idxmin(), 'recta_a'], 2)
                # Fila Bias_1_B
                #df_bias_table.loc[1, 'Selec'] = True
                #df_bias_table.loc[1, 'Prof_inf'] = float(df_bias['depth'].max())
                #df_bias_table.loc[1, 'Prof_sup'] = float(df_bias['depth'].min())
                #df_bias_table.loc[1, 'Delta'] = round(df_bias.loc[df_bias['depth'].idxmin(), 'recta_b'], 2)
                # Fila Bias_2_A
                #df_bias_table.loc[2, 'Selec'] = False
                #df_bias_table.loc[2, 'Prof_inf'] = float(df_bias['depth'].min())
                #df_bias_table.loc[2, 'Prof_sup'] = float(df_bias['depth'].min())
                #df_bias_table.loc[2, 'Delta'] = 0.00
                # Fila Bias_2_B
                #df_bias_table.loc[3, 'Selec'] = False
                #df_bias_table.loc[3, 'Prof_inf'] = float(df_bias['depth'].min())
                #df_bias_table.loc[3, 'Prof_sup'] = float(df_bias['depth'].min())
                #df_bias_table.loc[3, 'Delta'] = 0.00


                # Convierte el DataFrame actualizado en una lista de diccionarios
                rowData_actualizado = df_bias_table.to_dict(orient='records')

                return rowData_actualizado, True

        return dash.no_update, False

    # actualización del archivo json-bias. Depende exclusivamente de que haya cambios en la tabla
    # hay que tener en cuenta que el bias siempre va después de spikes. Si se cambia un spike, se vuelve a cero en bias
    @app.callback(
        [Output("json_bias", "data"), # archivo con las correcciones de bias
        Output("error-store", "data")], # gestiona la ventana emergente de errores
        [Input('bias-table', 'cellValueChanged'),  # cambios en bias-table
        Input('bias-table-change-flag', 'data')], # se escribió la tabla por primera vez en la carga
        [State("json_spikes", "data"),# camp selecc con los cambios de spikes
         State("camp_a_graficar", "value"), # escucha los cambios de campaña, NO SÉ SI ES NECESARIO
         State("bias-table",'rowData'), # valores existentes en la bias-table ¿hace falta?
         State('corregir-tubo', 'data')], # datos originales
    )
    def cambios_json_bias(cellValueChanged, change_flag, corr_spikes, camp_a_graficar, bias_table, corregir_tubo ):
        # paso los valores actuales de la tabla a un df, por comodidad
        df_bias_table = pd.DataFrame(bias_table)

        if not corr_spikes:  # Comprueba si corr_spikes es None o está vacío
            # Si corr_spikes es None o vacío, devuelve dash.no_update
            return dash.no_update, dash.no_update
        # Se calculan las correcciones de la tabla
        # antes se verifica que son correctas las entradas manuales de la tabla
        # Verificar que los rangos de profundidad sean válidos solo si están seleccionados
        error = "No" # se resetea al principio
        if df_bias_table.loc[0, 'Selec'] and df_bias_table.loc[0, 'Prof_inf'] < df_bias_table.loc[0, 'Prof_sup']:
            # profundidades para bias 1A
            error = "El rango para A en el paso 1 no es válido: h_inf debe ser mayor o igual a h_sup."
        if df_bias_table.loc[1, 'Selec'] and df_bias_table.loc[1, 'Prof_inf'] < df_bias_table.loc[1, 'Prof_sup']:
            # comprobación de profundidades para bias 1B
            error = "El rango para B en el paso 1 no es válido: el intervalo va de más a menos profundo."
        if df_bias_table.loc[2, 'Selec'] and df_bias_table.loc[2, 'Prof_inf'] < df_bias_table.loc[2, 'Prof_sup']:
            # profundidades para bias 2A
            error = "El rango para A en el paso 2 no es válido: h_inf debe ser mayor o igual a h_sup."
        if df_bias_table.loc[3, 'Selec'] and df_bias_table.loc[3, 'Prof_inf'] < df_bias_table.loc[3, 'Prof_sup']:
            # comprobación de profundidades para bias 1B
            error = "El rango para B en el paso 2 no es válido: el intervalo va de más a menos profundo."
        if df_bias_table.loc[2, 'Selec'] and df_bias_table.loc[2, 'Prof_inf'] > df_bias_table.loc[0, 'Prof_sup']:
            # Mal la segunda corr de bias A, los intervalos no pueden coincidir
            error = "Los intervalos de corrección de los pasos 1 y 2 no se pueden solapar, tanto para A como para B."
        if df_bias_table.loc[3, 'Selec'] and df_bias_table.loc[3, 'Prof_inf'] > df_bias_table.loc[1, 'Prof_sup']:
            # Mal la segunda corr de bias A, los intervalos no pueden coincidir
            error = "Los intervalos de corrección de los pasos 1 y 2 no se pueden solapar, tanto para A como para B."
        # si hay errores debe salir un modal emergente con la advertencia y se interrumpe la corrección
        #if error != "No" and (df_bias_table.loc[0, 'Selec'] or df_bias_table.loc[0, 'Selec'] or df_bias_table.loc[0, 'Selec'] or df_bias_table.loc[0, 'Selec']):
        if error != "No":
            # hay un error, devuelve el texto
            return dash.no_update,  {"opened": True, "message": error}


        # a. Extraer la fecha seleccionada (primera clave del diccionario corr_spikes)
        fecha_selec = list(corr_spikes.keys())[0]

        # b. Buscar la fecha de referencia usando buscar_referencia
        fecha_referencia = buscar_referencia(corregir_tubo, fecha_selec)

        # c. extrae los diccionarios con valores de referencia y corrección
        calc_ref = corregir_tubo[fecha_referencia]['calc']  # datos de la campaña de referencia
        calc_corr = corr_spikes[fecha_selec]['calc']  # datos de la campaña a corregir

        # d. Crea df_bias
        df_bias = creacion_df_bias(calc_ref, calc_corr)

        # corrección
        df_bias_corr = calculos_bias_1(df_bias, df_bias_table,corr_spikes)

        # En caso de que haya referencia, se debe sumar el desplazamiento acumulado que tiene
        # Crear un diccionario con los valores de desp_a y desp_b de df_ref, indexados por 'index'
        df_ref = pd.DataFrame(calc_ref)
        desp_values = df_ref.set_index('index')[['desp_a', 'desp_b']]

        # Sumar directamente sin necesidad de fusionar
        df_bias_corr['desp_a_corr'] = df_bias_corr['index'].map(desp_values['desp_a']) + df_bias_corr['corr_a']
        df_bias_corr['desp_b_corr'] = df_bias_corr['index'].map(desp_values['desp_b']) + df_bias_corr['corr_b']

        # Reemplazar posibles NaN con 0 en caso de índices no coincidentes
        df_bias_corr['desp_a_corr'].fillna(df_bias_corr['corr_a'], inplace=True)
        df_bias_corr['desp_b_corr'].fillna(df_bias_corr['corr_b'], inplace=True)


        # Convierte el DataFrame actualizado en una lista de diccionarios
        rowData_actualizado = df_bias_table.to_dict(orient='records')
        # da formato al diccionario dict_df_bias_final.
        # se incluye en este diccionario las correcciones, aunque puede que no se vaya a usar
        dict_df_bias = df_bias_corr.to_dict(orient='records')
        dict_df_bias_final = {fecha_selec: {'calc': dict_df_bias, 'bias': rowData_actualizado}}

        # Obtener la primera clave
        first_key = next(iter(dict_df_bias_final))

        # Filtrar por index = 0.5 (según tu descripción, pero parece que debería ser depth o cota_abs = 0.5)
        #filtered_values = [entry for entry in dict_df_bias_final[first_key]['calc'] if entry.get('depth') == 0.5]


        # Control de ejecución
        debug_funcion('cambios_json_bias')

        return dict_df_bias_final, dash.no_update

    # añadir descripción
    @app.callback(
        [Output('corr_graf_bias_a', 'figure'),
         Output('corr_estad_bias_a', 'figure'),
         Output('corr_graf_bias_b', 'figure'),
         Output('corr_estad_bias_b', 'figure')],
        [Input("json_bias", "data"), # Correcciones calculadas - bias
         Input("correc_escala_graficos_desplazamiento", "value"),
         Input("correc_valor_positivo_desplazamiento", "value"),
         Input("correc_valor_negativo_desplazamiento", "value")
         ]
    )

    def graficos_bias(json_bias, escala_desplazamiento, valor_positivo_desplazamiento, valor_negativo_desplazamiento):
        # ojo, en los gráficos se muestran los valores de desplazamiento desde la última referenica, no A ORIGEN DEL TUBO

        # control primeras cargas
        if not json_bias:
            return go.Figure(), go.Figure(), go.Figure(), go.Figure()

        # Paso json_bias a un df para poder graficar
        print('estamos en gráficos -----------------------------')

        df_bias = pd.DataFrame(json_bias[list(json_bias.keys())[0]]['calc'])

        # Control de ejecución
        debug_funcion('graficos_bias')

        # 6. Crear gráficos
        fig_a = go.Figure()
        fig_a_estad = go.Figure()
        fig_b = go.Figure()
        fig_b_estad = go.Figure()
        # 6.a. gráficos de desplazamiento, curva de abatimiento y curva corregida resultante
        # Desplazamiento
        fig_a.add_trace(go.Scatter(
            x=df_bias['desp_a'],
            y=df_bias['depth'],
            mode='lines+markers',
            name='Despl. A'
        ))
        fig_b.add_trace(go.Scatter(
            x=df_bias['desp_b'],
            y=df_bias['depth'],
            mode='lines+markers',
            name='Despl. B'
        ))
        # añado la serie corregida
        fig_a.add_trace(go.Scatter(
            x=df_bias['corr_a'],
            y=df_bias['depth'],
            mode='lines',
            line=dict(c='red', dash='dash', width=3),
            name='Despl. A_corr'
        ))
        fig_b.add_trace(go.Scatter(
            x=df_bias['corr_b'],
            y=df_bias['depth'],
            mode='lines',
            line=dict(c='red', dash='dash', width=3),
            name='Despl. B_corr'
        ))
        # Añado la recta de abatimiento
        fig_a.add_trace(go.Scatter(
            x=df_bias['recta_a'],
            y=df_bias['depth'],
            mode='lines',
            line=dict(c='red', dash='dash', width=3),
            name='Abat_A'
        ))
        # Añado la recta de abatimiento
        fig_b.add_trace(go.Scatter(
            x=df_bias['recta_b'],
            y=df_bias['depth'],
            mode='lines',
            line=dict(c='red', dash='dash', width=3),
            name='Abat_B'
        ))

        # 6.b. Gráficos de estadística: Avg_checksum, Incr y recta promedio de Incr
        # Avg checksum
        fig_a_estad.add_trace(go.Bar(
            x=df_bias['avg_Incr_A'],
            y=df_bias['depth'],
            name='avg_Incr_A',
            orientation='h',  # Barras horizontales
            marker=dict(c='rgb(100, 149, 237)')  # Azul intermedio (Cornflower Blue)
        ))
        fig_b_estad.add_trace(go.Bar(
            x=df_bias['avg_Incr_B'],
            y=df_bias['depth'],
            name='avg_Incr_B',
            orientation='h',  # Barras horizontales
            marker=dict(c='rgb(100, 149, 237)')  # Azul intermedio (Cornflower Blue)
        ))
        # Scatter para incr_checksum_a vs depth
        fig_a_estad.add_trace(go.Scatter(
            x=df_bias['incr_checksum_a'],
            y=df_bias['depth'],
            mode='markers',
            name='incr_checksum_a',
            marker=dict(c='rgb(255, 127, 80)', size=8),  # Coral
            xaxis='x2'  # Asocia esta serie a la segunda escala horizontal
        ))
        fig_b_estad.add_trace(go.Scatter(
            x=df_bias['incr_checksum_b'],
            y=df_bias['depth'],
            mode='markers',
            name='incr_checksum_b',
            marker=dict(c='rgb(255, 127, 80)', size=8),  # Coral
            xaxis='x2'  # Asocia esta serie a la segunda escala horizontal
        ))
        # Agregar la línea vertical en la media
        fig_a_estad.add_trace(go.Scatter(
            x=[df_bias["incr_checksum_a"].mean(), df_bias["incr_checksum_a"].mean()],
            y=[df_bias['depth'].iloc[0], df_bias['depth'].iloc[-1]],  # Extremos del rango en el eje Y
            mode='lines',
            name=f'Incr_Checksum',
            line=dict(c='rgb(255, 69, 0)', dash='dash'),  # Rojo oscuro con línea discontinua
            xaxis='x2'  # Asocia esta serie a la segunda escala horizontal
        ))
        fig_b_estad.add_trace(go.Scatter(
            x=[df_bias["incr_checksum_b"].mean(), df_bias["incr_checksum_b"].mean()],
            y=[df_bias['depth'].iloc[0], df_bias['depth'].iloc[-1]],  # Extremos del rango en el eje Y
            mode='lines',
            name=f'Incr_Checksum',
            line=dict(c='rgb(255, 69, 0)', dash='dash'),  # Rojo oscuro con línea discontinua
            xaxis='x2'  # Asocia esta serie a la segunda escala horizontal
        ))

        # 7. Configuración de los gráficos
        # 7.a. Gráficos desplazamiento
        for fig in [fig_a, fig_b]:
            if fig == fig_a:
                titulo = "Corr.Despl.Bias A"
            else:
                titulo = "Corr.Despl.Bias B"
            fig.update_layout(
                yaxis=dict(autorange='reversed', title='Profundidad'),
                xaxis=dict(title=titulo),
                template='plotly_white',
                margin=dict(l=40, r=20, t=40, b=20),
                height=600,
                showlegend=False  # Oculta la leyenda
            )
        # Configurar escala horizontal en desplazamiento
        for fig in [fig_a, fig_b]:
            if escala_desplazamiento == "manual":
                fig.update_xaxes(range=[valor_negativo_desplazamiento, valor_positivo_desplazamiento])
        # 7.b. Configuración de los gráficos estadística
        for fig in [fig_a_estad, fig_b_estad]:
            if fig == fig_a_estad:
                titulo = 'Avg_CheckSum_A'
                titulo_2 = 'Incr_A'
            else:
                titulo = 'Avg_CheckSum_B'
                titulo_2 = 'Incr_B'
            fig.update_layout(
                yaxis=dict(
                    autorange='reversed',
                    showticklabels=False,  # Ocultar etiquetas del eje vertical
                    zeroline=True,  # Asegura que la línea cero del eje vertical se muestre
                ),
                xaxis=dict(
                    title= titulo,
                    title_font=dict(c='blue'),  # Título del eje principal en azul
                    zeroline=True,  # Asegura que la línea cero del eje x esté visible
                    zerolinec='gray',  # Color de la línea cero
                    zerolinewidth=2  # Grosor de la línea cero
                ),
                xaxis2=dict(
                    title= titulo_2,
                    overlaying='x',  # Superpone este eje sobre el eje 'x'
                    side='top',  # Coloca el eje en la parte superior
                    title_font=dict(c='red'),  # Título del segundo eje en rojo
                    zeroline=False  # Este eje no necesita una línea cero porque comparte la del principal
                ),
                template='plotly_white',
                margin=dict(l=40, r=20, t=40, b=20),
                height=600,
                showlegend=False  # Oculta la leyenda
            )


        return fig_a,fig_a_estad, fig_b, fig_b_estad

    # ventana emergente para evolución del checksum por intervalos
    @app.callback(
        [Output('ventana_modal_bias', 'opened'),
         Output('modal_bias_graph_1', 'figure'),],
        [Input('boton_ventana_modal_bias', 'n_clicks'),
         Input('temporal-bias-variables', 'value')],  # Entrada del multiselect
        [State('corregir-tubo', 'data'), # archivo json original
         State("json_spikes", "data"), # valores temporales de la campaña corregida
         State("camp_a_graficar", "data"),  # lista de fechas
         State("camp_a_graficar", "value")]  # fecha_seleccionada
    )


    def emergente_bias(n_clicks, selected_vars, data_json, data_corr, lista_fechas, fecha_selec):
        # Si no se ha hecho clic en el botón o faltan datos, no actualizar
        if not n_clicks or not data_json or not data_corr or not fecha_selec:# or not selected_vars:
            return False, go.Figure()
        # Manejo de estado vacío: si no se seleccionan variables, devolver gráfico vacío
        if not selected_vars:
            # Mantener el modal abierto pero mostrar un gráfico vacío
            return True, go.Figure()

        # Paso 1. Pasamos los diccionarios a df
        # Paso 1a. Búsqueda de la campaña referencia para fecha_selec
        fecha_ref = buscar_referencia(data_json, fecha_selec)
        # Paso 1b. creo un diccionario con los df a considerar, de forma dinámica
        # Filtrar las fechas desde la rferencia hasta la fecha seleccionada
        conjunto_fechas = [fecha['value'] for fecha in lista_fechas if
                           'value' in fecha and fecha['value'] <= fecha_selec
                           and 'value' in fecha and fecha['value'] >= fecha_ref
                           and data_json[fecha['value']]['campaign_info']['active'] == True] # la ordeno

        # Inserto la clave 'calc' corregida en el archivo del tubo
        data_json[fecha_selec]['calc'] = data_corr[fecha_selec]['calc']

        # tengo que considerar que si están las std, se quitan en esta fase,las extraigo por el momento

        selected_vars_provisional = [item for item in [selected_vars] if item not in ['std_checksum_a', 'std_checksum_b',
                                                                                      'std_incr_dev_a', 'std_incr_dev_b']]
        dfs = dict_a_df(data_json, [selected_vars], conjunto_fechas)

        # Paso 2. key parameters. Busco parámetros para ver si se ve algo
        # vamos a probar a hacer medias cada 5 metros y la global
        # defino las profundidades
        depth = dfs[selected_vars].index.to_list()
        depth.sort(reverse=True)
        gap=5 # conjunto de datos a coger
        depth_m = [depth[0]]
        while True:
            next_value = depth_m[-1] - gap
            if next_value > 0:
                depth_m.append(next_value)
            else:
                break
        # Crear un nuevo DataFrame para almacenar las medias
        columns = dfs[selected_vars].columns

        # DataFrame final
        df_checksum_a_mean = pd.DataFrame(columns=columns)
        df_checksum_a = dfs[selected_vars]
        for dm in reversed(depth_m):
            group = df_checksum_a[(df_checksum_a.index > dm) & (df_checksum_a.index <= dm + gap)]
            if not group.empty:
                mean_row = group.mean(numeric_only=True).to_dict()
                mean_row["depth_m"] = group.index.to_series().median()
                df_checksum_a_mean = pd.concat([df_checksum_a_mean, pd.DataFrame([mean_row])], ignore_index=True)

        # Crear el gráfico
        fig = go.Figure()

        # Recorrer las filas para agregar las series al gráfico
        for _, row in df_checksum_a_mean.iterrows():
            depth = row["depth_m"]
            x = df_checksum_a_mean.columns[:-1]  # Columnas excepto 'depth_m'
            y = row[:-1]  # Valores excepto 'depth_m'
            fig.add_trace(go.Scatter(
                x=x,
                y=y,
                mode='lines+markers',
                name=f'{selected_vars}_{depth}'
            ))
        # añado las std

        # Personalizar el diseño del gráfico
        fig.update_layout(
            title="Gráfico",
            xaxis_title="Fecha",
            yaxis_title="Valores",
            template="plotly_white"
        )

        # Control de ejecución
        debug_funcion('emergente_bias')

        return True, fig

    # Callback to handle error modal updates
    @app.callback(
        [Output("error-modal", "opened"),
         Output("error-message", "children")],
        [Input("error-store", "data")]
    )
    def handle_error_modal(error_store):
        return error_store["opened"], error_store["message"]

    # ventana emergente para evolución del std del checksum
    @app.callback(
        [Output('ventana_modal_bias_1', 'opened'),
         Output('modal_bias_graph_2', 'figure'), ],
        Input('boton_ventana_modal_bias_1', 'n_clicks'),
        [State('empotramiento', 'value'),  # valor del empotramiento teórico
         State('corregir-tubo', 'data'),  # archivo json original
         State("json_spikes", "data"),  # valores temporales de la campaña corregida
         State("camp_a_graficar", "value")]  # fecha_seleccionada
    )
    def emergente_bias_1(n_clicks, empotramiento, corregir_tubo, json_spikes, fecha_selec):
        #kilo
        # Si no se ha hecho clic en el botón o faltan datos, no actualizar
        if not n_clicks or not corregir_tubo or not json_spikes or not fecha_selec:  # or not selected_vars:
            return False, go.Figure()
        # Manejo de estado vacío: si no se seleccionan variables, devolver gráfico vacío

        # Paso 1. Pasamos los diccionarios a df
        # Paso 1a. Búsqueda de la campaña referencia para fecha_selec
        fecha_ref = buscar_referencia(corregir_tubo, fecha_selec)
        # Paso 1b. creo un diccionario con los df a considerar, de forma dinámica
        # Filtrar las fechas desde la rferencia hasta la fecha seleccionada
        fechas_activas = [fecha for fecha in corregir_tubo.keys()
                          if isinstance(corregir_tubo[fecha], dict) and 'campaign_info' in corregir_tubo[fecha]
                          and corregir_tubo[fecha]['campaign_info'].get('active') == True]

        # Inserto la clave 'calc' corregida en el archivo del tubo
        data_json = corregir_tubo.copy()
        data_json[fecha_selec]['calc'] = json_spikes[fecha_selec]['calc']


        variables = ['incr_checksum_a', 'incr_checksum_b', 'incr_dev_a', 'incr_dev_b']

        df_std = std(variables, fechas_activas, data_json, empotramiento)

        fig = go.Figure()

        # Agregar cada columna del DataFrame como una serie independiente
        for col in df_std.columns:
            fig.add_trace(go.Scatter(
                x=df_std.index,
                y=df_std[col],
                mode='lines+markers',
                name=col
            ))

        # Personalizar el diseño del gráfico
        fig.update_layout(
            title="Gráfico evolución desviación estándard",
            xaxis_title="Fecha",
            yaxis_title="Valores",
            template="plotly_white",
            hovermode='x unified'
        )

        # Control de ejecución
        debug_funcion('emergente_bias_std')

        return True, fig

    """
    # Callback to handle error modal updates
    @app.callback(
        [Output("error-modal", "opened"),
         Output("error-message", "children")],
        [Input("error-store", "data")]
    )
    def handle_error_modal(error_store):
        return error_store["opened"], error_store["message"]
    """




    @app.callback(
        [Output("guardar-modal", "opened"),
         Output("guardar-mensaje", "children")],
        [Input("save_json", "n_clicks"),
         Input("cerrar-guardar-modal", "n_clicks")],
        [State("json_spikes", "data"),
         State("json_bias", "data"),
         State("corregir-tubo", "data"),
         State("corregir_archivo", "data"),
         State("camp_a_graficar", "value"),
         State("tabla-json", "rowData")],
        prevent_initial_call=True  # Evita que se ejecute automáticamente al cargar la app
    )
    def guardar_cambios(n_clicks_save, n_clicks_close, json_spikes, json_bias, corregir_tubo, nombre_archivo, fecha_seleccionada, tabla_json):
        # se combina el guardar los cambios con un modal para mostrar los errores o que se guardaron los cambios en el json
        ctx = callback_context  # Para saber qué elemento activó el callback
        if not ctx.triggered:
            raise dash.exceptions.PreventUpdate

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "save_json":
            # Comprueba si hay correcciones previas en la tabla_json
            fila_seleccionada = next((fila for fila in tabla_json if fila['Fecha'] == fecha_seleccionada), None)

            if fila_seleccionada:
                if fila_seleccionada.get('spike') or fila_seleccionada.get('bias'):
                    # Error, no hay nada que guardar
                    return True, "Error: Las correcciones deben ser en campañas sin correcciones previas"

            # Filtrar los bias  con 'Selec' == true
            bias_seleccionado = [item for item in json_bias[fecha_seleccionada].get("bias") if item['Selec']]
            bias_seleccionado = bias_seleccionado if bias_seleccionado else None # lo pone como None en caso de vacío
            spikes_seleccionado = json_spikes[fecha_seleccionada].get("spike")
            if bias_seleccionado == [] and spikes_seleccionado == None:
                # Error, no hay nada que guardar
                return True, "Error: No hay datos para guardar"

            # Reconstruye el campo 'calc' con los datos corregidos de a0-b180
            # uso los datos de json_bias, que ya contemplan los cambios en spikes
            ### INICIO

            # Crear el nuevo diccionario con la clave 'calc' y los valores filtrados
            nuevo_calc = {
                fecha_seleccionada: {
                    'calc': [
                        {
                            'index': item['index'],
                            'cota_abs': item['cota_abs'],
                            'depth': item['depth'],
                            'a0': round(item['a0'], 2),  # Redondeado a 2 decimales
                            'a180': round(item['a180'], 2),  # Redondeado a 2 decimales
                            'b0': round(item['b0'], 2),  # Redondeado a 2 decimales
                            'b180': round(item['b180'], 2),  # Redondeado a 2 decimales
                            'checksum_a': round(item['a0'] + item['a180'], 4),
                            'checksum_b': round(item['b0'] + item['b180'], 4),
                            'dev_a': round((item['a0'] - item['a180']) / 2, 2),  # Redondeado a 2 decimales
                            'dev_b': round((item['b0'] - item['b180']) / 2, 2)  # Redondeado a 2 decimales
                        }
                        for item in json_bias[fecha_seleccionada]['calc']
                    ]
                }
            }
            # busco referencia
            fecha_referencia = buscar_referencia(corregir_tubo, fecha_seleccionada)
            data_new = {
                fecha_referencia: {"calc": corregir_tubo[fecha_referencia]['calc']},
                fecha_seleccionada: {"calc":  nuevo_calc[fecha_seleccionada]['calc']}
            }
            resultado = calcular_incrementos(data_new, fecha_seleccionada, fecha_referencia)

            # Ruta del script - FUNCIONAMIENTO EN LOCAL
            ruta_script = Path(__file__).resolve().parent.parent  # Sube un nivel desde 'pages'
            ruta_data = ruta_script / "data"  # Ahora apunta a 'IncliData/data'

            # Nombre del archivo JSON
            ruta_json = ruta_data / nombre_archivo
            # Abrir el archivo en modo lectura/escritura sin sobrescribir todo
            with open(ruta_json, "r+", encoding="utf-8") as f:
                data = json.load(f)  # Cargar el JSON existente

                # Modificar solo la clave necesaria
                if fecha_seleccionada in data:
                    data[fecha_seleccionada]['calc'] = resultado[fecha_seleccionada]['calc'] # campaña con mod y recalculada
                    data[fecha_seleccionada]['bias'] = bias_seleccionado # lo añado aunque esté vacío
                    data[fecha_seleccionada]['spike'] = spikes_seleccionado # lo añado aunque esté vacío
                else:
                    print(f"⚠️ La fecha {fecha_seleccionada} no existe en el archivo JSON.")
                    raise ValueError(f"La fecha {fecha_seleccionada} no se encuentra en el JSON.")

                # Volver a escribir SOLO la parte modificada
                f.seek(0)  # Mover el puntero al inicio para sobrescribir correctamente
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.truncate()  # Elimina cualquier contenido sobrante
                print(f"🛠️ Editando el archivo: {ruta_json}")
            print(f"Archivo actualizado con bias en {ruta_json}")

            # Construye el mensaje de guardado
            if bias_seleccionado is not None and spikes_seleccionado is not None:
                mensaje = f"En la fecha {fecha_seleccionada}, se guardan cambios en Bias y Spike."
            elif bias_seleccionado is not None:
                mensaje = f"En la fecha {fecha_seleccionada}, se guardan cambios en Bias."
            elif spikes_seleccionado is not None:
                mensaje = f"En la fecha {fecha_seleccionada}, se guardan cambios en Spike."
            return True, mensaje

        elif trigger_id == "cerrar-guardar-modal":
            return False, dash.no_update  # Cierra el modal sin cambiar el mensaje


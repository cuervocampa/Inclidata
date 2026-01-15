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



#from TD_medias.vol_td.main import height
from utils.funciones_comunes import get_color_for_index, buscar_referencia, calcular_incrementos, df_to_excel, debug_funcion
from utils.funciones_correcciones import grafico_violines, dict_a_df, creacion_df_bias, calculos_bias, calculos_bias_1
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
                                    dmc.Button("Recalcular Tabla", id='recalcular_tabla', variant='outline', c='blue'),
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
                    html.H2("Corrección de spikes"),
                    html.Div(style={"height": "20px"}),
                    # Primer grupo
                    dmc.Group(
                        [
                            html.H4("Campañas anteriores"),
                            #dmc.Text("Campañas anteriores", fw="bold"),
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
                            html.H4("Estadísticas Spikes"),
                            #dmc.Text("Estadísticas Spikes", fw="bold"),
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
                                        ],
                                        value=["checksum_a", "checksum_b"],  # Valores por defecto
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
                    # ventana modal
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
                        'spike': True if data.get(fecha, {}).get('spike') else False,
                        'bias': True if data.get(fecha, {}).get('bias') else False,
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
        # Control de ejecución
        debug_funcion('procesar_archivo_contenido')
        return corregir_tubo_data, informacion_archivo, corregir_archivo_data, columnDefs, table_data, tabla_inicial, camp_a_graficar_data, camp_a_graficar_value

    # botón de la cambios en la tabla
    @app.callback(
        [Output("guardar-cambios-tabla", "opened"),
         Output("guardar-mensaje-tabla", "children")],
        [Input("guardar_tabla", "n_clicks"),
         Input("cerrar-cambios-tabla","n_clicks")],
        [State("tabla-json", "rowData"),
         State('log_cambios',"data"),
         State('corregir-tubo', 'data'),
         State('corregir_archivo', 'data')],
        prevent_initial_call=True  # Evita que se ejecute en la carga inicial
    )

    def callback_guardar_tabla(n_clicks, n_clicks_cerrar, tabla_json, log_cambios, corregir_tubo, nombre_archivo):
        # Función para aplicar los cambios de la tabla
        # Los posibles cambios son: Referencia, Activa, Cuarentena y Limpiar. Lógica:
        # Si es Referencia, se cambia el estado y se recalculan las siguientes campañas
        # Si es Activa, en caso de que sea la anterior activa antes de la referencia, se deben recalcular las siguientes
        # Si es Cuarentena, sólo aplica al cambio de clave
        # Si es Limpiar, en caso de ser antes de referencia, se recalcula esta campaña y el resto
        # Nota: En caso de hacer cambios que impliquen recalcular campañas (no Limpiar individual), se activa Cuarentena en las
        # campañas recalculadas para no liarla con alarmas
        # las acciones se ejecutan por orden cronológico, en teoría le log viene ordenado

        # ojo, asegurarse de que si hay varias acciones en la misma fecha las ordene Referencia, Activa, Cuarentena, Limpiar

        # se combina el guardar los cambios con un modal para mostrar los errores o que se guardaron los cambios en el json
        ctx = callback_context  # Para saber qué elemento activó el callback
        if not ctx.triggered:
            raise dash.exceptions.PreventUpdate

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "guardar_tabla":
            print (tabla_json)
            return True, "Salida de emergencia"
            # primero se comprueba que hay acciones a realizar
            if not log_cambios:
                # error, no hay ninguna acción seleccionada
                return True, "No hay cambios a aplicar"
            # Hay cambios
            # Extraer las claves principales en una lista
            acciones = list(log_cambios.keys())
            # recorro acciones
            for accion in acciones:
                # si es Referencia, o Activa o Limpiar antes justo antes de una referencia, cambias todas camp posteriores
                if log_cambios[accion]['clave'] == 'Referencia': # falta comprobar las fechas anteriores
                    # aplica los cambios e itera sobre el resto. CÓDIGO COMPLICADO
                    print ('cambios en resto de campañas nuevas')
                elif log_cambios[accion]['clave'] == "Limpiar":
                    # recalcula la campaña y guarda los cambios en el json
                    # calcula la referencia anterior a fecha
                    fecha_seleccionada = log_cambios[accion]['fecha']
                    fecha_referencia = buscar_referencia(corregir_tubo, fecha_seleccionada)
                    # hay que meter en 'calc' los valores de a0-b180 calculados desde raw
                    calc_entries = []
                    # constante de conversión
                    cte = corregir_tubo[fecha_seleccionada]['campaign_info']['instrument_constant']
                    # recorre el diccionario 'raw' y obtiene los valores directos de la campaña
                    for i, item in enumerate(corregir_tubo[fecha_seleccionada]["raw"]):
                        entry = valores_calc_directos(
                            item['index'], item['cota_abs'], item['depth'],
                            item['a0'], item['a180'], item['b0'], item['b180'], cte)
                        calc_entries.append(entry)
                    # inserto el nuevo 'calc' en el archivo del tubo
                    corregir_tubo[fecha_seleccionada]['calc'] = calc_entries
                    # se obtienen los valores calculados en función de la referencia. Ojo correcciones es todo el tubo
                    correcciones = calcular_incrementos(corregir_tubo, fecha_seleccionada, fecha_referencia)  # función externa utils/funciones_comunes.py

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
                            data[fecha_seleccionada]['calc'] = correcciones[fecha_seleccionada]['calc']  # campaña recalculada sin modificaciones
                            data[fecha_seleccionada]['bias'] = None  # lo añado vacío
                            data[fecha_seleccionada]['spike'] = None  # lo añado vacío
                        else:
                            print(f"⚠️ La fecha {fecha_seleccionada} no existe en el archivo JSON.")
                            raise ValueError(f"La fecha {fecha_seleccionada} no se encuentra en el JSON.")

                        # Volver a escribir SOLO la parte modificada
                        f.seek(0)  # Mover el puntero al inicio para sobrescribir correctamente
                        json.dump(data, f, ensure_ascii=False, indent=4)
                        f.truncate()  # Elimina cualquier contenido sobrante
                        print(f"🛠️ Editando el archivo: {ruta_json}")
                    print(f"Archivo actualizado con bias en {ruta_json}")
                    # kilo



            return True, "Guardados los cambios"

        elif trigger_id == "cerrar-cambios-tabla":
            return False, dash.no_update  # Cierra el modal sin cambiar el mensaje

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
            entrada["checksum_a"] = round(entrada["a0"] + entrada["a180"], 4),
            entrada["checksum_b"] = round(entrada["b0"] + entrada["b180"], 4)
        # busco referencia
        fecha_referencia = buscar_referencia(data, camp_graficar)
        data_new = {
            fecha_referencia: {"calc": data[fecha_referencia]['calc']},
            camp_graficar: {"calc": correccion[camp_graficar]['calc'], "spike": correccion[camp_graficar]['spike']}
        }
        resultado = calcular_incrementos(data_new, camp_graficar, fecha_referencia)

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

        # Control de ejecución
        debug_funcion('corr_grafico_1')


        return [fig1_a, fig1_b, fig2_a, fig2_b, fig3_a, fig3_b, fig3_total]

    # Grupo de gráficos 2 - SPIKES
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

    def graficos_spike(data, fecha_seleccionada, fechas, n_spikes, color_scheme, estadistica):
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
        #default_vars = ["checksum_a", "checksum_b"]

        # Si no se ha hecho clic en el botón o faltan datos, no actualizar
        if not n_clicks or not selected_depths or not data:
            return False, go.Figure()

        # Filtrar las fechas desde el inicio hasta la fecha seleccionada
        conjunto_fechas = [fecha['value'] for fecha in fechas if 'value' in fecha and fecha['value'] <= fecha_seleccionada
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
            for var in selected_vars:
                for depth in selected_depths:
                    # Extraer las fechas y los valores para 'depth'
                    fechas = dfs[var].columns
                    valores = dfs[var].loc[depth]

                    # Agregar una nueva traza para cada combinación de variable y profundidad
                    figure.add_trace(go.Scatter(
                        x=fechas,
                        y=valores,
                        mode='lines+markers',  # Puedes usar 'lines', 'markers' o una combinación
                        name=f'{var} - Profundidad {depth}'
                    ))

            # Definir el diseño del gráfico
            figure.update_layout(
                title="Serie Temporal para las Profundidades Seleccionadas",
                xaxis=dict(title="Fecha"),
                yaxis=dict(title="Valor"),
                template='plotly_white'  # Opcional: añade un estilo limpio
            )
            # Control de ejecución
            debug_funcion('emergente_spike')
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

        # Convierte el DataFrame actualizado en una lista de diccionarios
        rowData_actualizado = df_bias_table.to_dict(orient='records')
        # da formato al diccionario dict_df_bias_final.
        # se incluye en este diccionario las correcciones, aunque puede que no se vaya a usar
        dict_df_bias = df_bias_corr.to_dict(orient='records')
        dict_df_bias_final = {fecha_selec: {'calc': dict_df_bias, 'bias': rowData_actualizado}}

        # Control de ejecución
        debug_funcion('cambios_json_bias')
        """
        #print (dict_df_bias_final)

        # provisional para ver el resultado de forma externa
        # Crear el diccionario
        data = {fecha_selec: {'bias': rowData_actualizado}}

        # Obtener la ruta del script y agregar el nombre del archivo
        ruta_script = os.path.dirname(os.path.abspath(__file__))  # Ruta del script
        ruta_archivo = os.path.join(ruta_script, "tabla_bias.json")  # Archivo JSON en la misma carpeta
        print ("json_bias guardado")

        # Guardar el JSON de correcciones
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        # Guardar el JSON completo del bias
        ruta_archivo = os.path.join(ruta_script, "bias.json")  # Archivo JSON en la misma carpeta
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(dict_df_bias_final, f, ensure_ascii=False, indent=4)

        # guardar el excel
        # Crear el DataFrame con las claves requeridas
        df_extracted_generic = pd.DataFrame(calc_ref, columns=['depth', 'abs_dev_a', 'abs_dev_b'])
        df_comprobacion = df_bias_corr.merge(df_extracted_generic, on="depth", how="left")
        ruta_archivo = os.path.join(ruta_script, "bias.xlsx")  # Archivo xlsx en la misma carpeta
        # Guardar el DataFrame en un archivo Excel
        df_comprobacion.to_excel(ruta_archivo, index=True)
        """

        return dict_df_bias_final, dash.no_update


    """
    # Guarda las modificaciones de json_bias
    @app.callback(
        [Output("json_bias", "data"),
        Output('bias-table', 'rowData')],
        [Input("json_spikes", "data"),# camp selecc con los cambios de spikes
         Input('bias-table','cellValueChanged'), # cambios en bias-table
         Input('empotramiento', 'value'), # valor del empotramiento teórico
         Input("sugerir_bias", "n_clicks"), # Botón para sugerir correcciones
         Input("camp_a_graficar", "value")], # escucha los cambios de campaña, NO SÉ SI ES NECESARIO
        [State("bias-table",'rowData'), # valores existentes en la bias-table
         State('corregir-tubo', 'data')], # datos originales
    )
    def cambios_json_bias(corr_spikes , cellValueChanged,  empotramiento, sugerir, camp_a_graficar, bias_table, corregir_tubo):
        # ¿Hay que meter alguna condición inicial?
        # faltaría meter un control de errores en caso de que empotramiento sea = 0 o mayor que la profundidad
        if corr_spikes:
            # CASO I. Cuando se (carga una campaña) o (cambio de campaña) o (cambios en empotramiento) o (botón sugerir_bias)
            # Identificar si empotramiento fue el trigger
            triggered_input = callback_context.triggered[0]['prop_id'].split('.')[0]
            # Paso 1. Evalúa si es la primera carga para "sugerir" correcciones
            df_bias_table = pd.DataFrame(bias_table) # por comodidad lo pongo en un df

            # Tomo como criterio para considerar que es la primera carga que la suma de las prof = 0
            if (df_bias_table['Prof_inf'].sum() + df_bias_table['Prof_sup'].sum()) == 0 or sugerir or triggered_input == 'empotramiento':
                # Paso 1.a. Se calculan las correcciones sugeridas
                # a. Extraer la fecha seleccionada (primera clave del diccionario corr_spikes)
                fecha_selec = list(corr_spikes.keys())[0]

                # b. Buscar la fecha de referencia usando buscar_referencia
                fecha_referencia = buscar_referencia(corregir_tubo, fecha_selec)

                # c. extrae los diccionarios con valores de referencia y corrección
                calc_ref = corregir_tubo[fecha_referencia]['calc']  # datos de la campaña de referencia
                calc_corr = corr_spikes[fecha_selec]['calc']  # datos de la campaña a corregir

                # d. Crea df_bias
                df_bias = creacion_df_bias(calc_ref, calc_corr)
                
                # Control de errores en empotramiento, evita que sea <=0 o mayor que la profundidad
                if empotramiento > df_bias['depth'].max() or empotramiento <= 0:
                    # hay un error, no hace nada. Debería enviar un error
                    return dash.no_update, dash.no_update

                # Paso 1.b. Correcciones sugeridas
                # Calculo el valor de incr en profundidad h-empotramiento m
                # se ha de suponer que este error se reproduce en el resto, independientemente del movimiento adicional que haya
                h = df_bias['depth'].iloc[-1]  # fondo del tubo
                # por defecto calcula para A y B. ojo, son valores unitarios por paso de sonda
                delta_a = df_bias.loc[df_bias['depth'] == h - empotramiento, 'avg_Incr_A'].iloc[0]
                delta_b = df_bias.loc[df_bias['depth'] == h - empotramiento, 'avg_Incr_B'].iloc[0]

                # corrección
                df_bias = calculos_bias(df_bias, df_bias['depth'].max(), df_bias['depth'].min(),  df_bias['depth'].max(),
                                        df_bias['depth'].min(), delta_a, delta_b)

                # Paso 1.c. Carga de valores en la tabla
                # evito un deprecated
                df_bias_table['Prof_inf'] = df_bias_table['Prof_inf'].astype(float)
                df_bias_table['Prof_sup'] = df_bias_table['Prof_sup'].astype(float)
                # Fila Bias_1_A
                df_bias_table.loc[0, 'Selec'] = True
                df_bias_table.loc[0, 'Prof_inf'] = float(df_bias['depth'].max())
                df_bias_table.loc[0, 'Prof_sup'] = float(df_bias['depth'].min())
                df_bias_table.loc[0, 'Delta'] = round(df_bias.loc[df_bias['depth'].idxmin(), 'recta_a'],2)
                # Fila Bias_1_B
                df_bias_table.loc[1, 'Selec'] = True
                df_bias_table.loc[1, 'Prof_inf'] = float(df_bias['depth'].max())
                df_bias_table.loc[1, 'Prof_sup'] = float(df_bias['depth'].min())
                df_bias_table.loc[1, 'Delta'] = round(df_bias.loc[df_bias['depth'].idxmin(), 'recta_b'],2)
                # dejo Bias_2_A y Bias_2_B igual que en la carga

                # Convierte el DataFrame actualizado en una lista de diccionarios
                rowData_actualizado = df_bias_table.to_dict(orient='records')
                # da formato al diccionario dict_df_bias_final.
                # se incluye en este diccionario las correcciones, aunque puede que no se vaya a usar
                dict_df_bias = df_bias.to_dict(orient='records')
                dict_df_bias_final = {fecha_selec:{'calc':dict_df_bias, 'bias':rowData_actualizado}}

                # Control de ejecución
                debug_funcion('cambios_json_bias')
                return  dict_df_bias_final, rowData_actualizado
            # CASO II. Se aplican las correcciones que se introducen manualmente en la tabla


            # campaña seleccionada.
            camp_graficar = list(corr_spikes.keys())[0]
            # hay cambios en spikes, se modifican las correcciones de bias
            resultado = {camp_graficar: {"calc": corr_spikes[camp_graficar]['calc']}}
            return dash.no_update, dash.no_update
        else:
            return dash.no_update, dash.no_update
    """


    # añadir descripción
    @app.callback(
        [Output('corr_graf_bias_a', 'figure'),
         Output('corr_estad_bias_a', 'figure'),
         Output('corr_graf_bias_b', 'figure'),
         Output('corr_estad_bias_b', 'figure')],
         #Output('calculated_bias_values', 'data')], # intermedio para carga inicial de bias-table
        Input("json_bias", "data"), # Correcciones calculadas - bias
         #Input("json_spikes", 'data'),# SOBRA - camp_corregida
         #Input('run_bias', 'n_clicks'), # SOBRA - run_bias
         #Input('bias-table', 'cellValueChanged')], # si no hay cambios, coge la anterior SOBRA - bias_table
        [#State('bias-table', 'rowData'), # SOBRA - cellValu...
         #State('corregir-tubo', 'data'), # datos originales  SOBRA corregir_tubo
         State("correc_escala_graficos_incremento", "value"),
         State("correc_valor_positivo_desplazamiento", "value"),
         State("correc_valor_negativo_desplazamiento", "value")
         ]
    )

    def graficos_bias(json_bias, escala_desplazamiento, valor_positivo_desplazamiento, valor_negativo_desplazamiento):
        # ojo, en los gráficos se muestran los valores de desplazamiento desde la última referenica, no A ORIGEN DEL TUBO
        #if not camp_corregida or not corregir_tubo:# or not bias_table or not run_bias:
        #    return go.Figure(), go.Figure(), go.Figure(), go.Figure()

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
            fig.update_layout(
                yaxis=dict(autorange='reversed', title='Profundidad'),
                xaxis=dict(title='Desplazamiento'),
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
            fig.update_layout(
                yaxis=dict(
                    autorange='reversed',
                    showticklabels=False,  # Ocultar etiquetas del eje vertical
                    zeroline=True,  # Asegura que la línea cero del eje vertical se muestre
                ),
                xaxis=dict(
                    title='Avg_CheckSum',
                    title_font=dict(c='blue'),  # Título del eje principal en azul
                    zeroline=True,  # Asegura que la línea cero del eje x esté visible
                    zerolinec='gray',  # Color de la línea cero
                    zerolinewidth=2  # Grosor de la línea cero
                ),
                xaxis2=dict(
                    title='Incr',
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

    # ventana emergente para evolución y estadística de bias
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
            print (fila_seleccionada)

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


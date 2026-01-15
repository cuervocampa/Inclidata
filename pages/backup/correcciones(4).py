from dash import html, dcc, callback_context
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
from dash import dash_table
import dash
import base64, json
from icecream import ic
from datetime import datetime, timedelta
import plotly.graph_objs as go
import re
import pandas as pd
from sqlalchemy import false


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
                                'width': '100%', 'height': '60px', 'lineHeight': '60px', 'borderWidth': '2px',
                                'borderStyle': 'dashed', 'borderRadius': '5px', 'borderColor': 'blue',
                                'textAlign': 'center', 'margin': '10px 0', 'display': 'flex', 'justifyContent': 'center',
                                'alignItems': 'center', 'color': 'red'
                            }
                        ),
                        span=3
                    ),
                    dmc.Col(
                        html.Div(id='informacion-archivo', style={'width': '100%'}),
                        span=4
                    ),
                    dmc.Col(
                        html.Div(),
                        span=3
                    )
                ],
                style={'width': '100%'}
            ),
            dcc.Store(id='corregir-tubo', storage_type='memory'), # archivo json, se parte del original y se incorporan modificaciones
            dcc.Store(id='corregir_archivo', storage_type='memory'), # nombre del archivo json. Pensado para funcionamiento en local
            dcc.Store(id='tabla_inicial', data={}, storage_type='memory'), # tabla resumen de campañas de 'corregir-tubo'
            dcc.Store(id='log_cambios', data={}, storage_type='memory'), # interacciones que se van haciendo en la tabla
            dcc.Store(id='cambios_a_realizar', data={}, storage_type='memory'), # modificaciones que se van haciendo sobre corregir-tubo
                # pretendo cambiar en el archivo original solo los cambios, respetando el resto de datos

            # Table and Info Section
            dmc.Grid(
                children=[
                    dmc.Col(
                        dash_table.DataTable(
                            id='tabla-json',
                            style_table={
                                'maxHeight': '200px', 'overflowY': 'auto', 'overflowX': 'auto',
                                'width': '100%', 'margin': '0 auto'
                            },
                            style_cell={'textAlign': 'left'},
                            style_header={
                                'position': 'sticky', 'top': 0, 'backgroundColor': 'white', 'zIndex': 1, 'fontWeight': 'bold'
                            },
                            columns=[
                                {'name': 'Fecha', 'id': 'Fecha', 'editable': False},
                                {'name': 'Referencia', 'id': 'Referencia', 'editable': True, 'presentation': 'dropdown'},
                                {'name': 'Activa', 'id': 'Activa', 'editable': True, 'presentation': 'dropdown'},
                                {'name': 'Cuarentena', 'id': 'Cuarentena', 'editable': True, 'presentation': 'dropdown'},
                                {'name': 'Correc Spike', 'id': 'spike', 'editable': False},
                                {'name': 'Correc Bias', 'id': 'bias', 'editable': False},
                                #{'name': 'Limpiar', 'id': 'limpiar', 'editable': True, 'presentation': 'dropdown'}
                            ],
                            data=[],  # Inicialmente vacío
                            row_selectable='single',
                            selected_rows=[0],
                            page_action='none',
                            page_size=10,
                            editable=True,
                            dropdown={
                                'Referencia': {'options': [{'label': 'True', 'value': True}, {'label': 'False', 'value': False}]},
                                'Activa': {'options': [{'label': 'True', 'value': True}, {'label': 'False', 'value': False}]},
                                'Cuarentena': {'options': [{'label': 'True', 'value': True}, {'label': 'False', 'value': False}]},
                                #'limpiar': {'options': [{'label': 'True', 'value': True}, {'label': 'False', 'value': False}]},
                                #'spike': {'options': [{'label': 'True', 'value': True}, {'label': 'False', 'value': False}]},
                                #'bias': {'options': [{'label': 'True', 'value': True}, {'label': 'False', 'value': False}]}
                            }
                        ),
                        span=6
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
                        span=6
                    )
                ],
                style={'width': '100%'}
            )
        ])
    )


# Registra los callbacks en lugar de definir un nuevo Dash app
def register_callbacks(app):
    @app.callback(
        [Output('corregir-tubo', 'data'),
         Output('informacion-archivo', 'children'),
         Output('corregir_archivo', 'data'),
         Output('tabla-json', 'columns'),
         Output('tabla-json', 'data'),
         Output('tabla_inicial', 'data')],
        [Input('archivo-uploader', 'contents')],
        [State('archivo-uploader', 'filename')]
    )
    def procesar_archivo_contenido(contents, filename):
        if contents is None:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

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
                        #'limpiar': 'false'
                    }
                    table_data.append(row)
                    columns = [
                        {'name': 'Fecha', 'id': 'Fecha', 'editable': False},
                        {'name': 'Referencia', 'id': 'Referencia', 'editable': True, 'presentation': 'dropdown'},
                        {'name': 'Activa', 'id': 'Activa', 'editable': True, 'presentation': 'dropdown'},
                        {'name': 'Cuarentena', 'id': 'Cuarentena', 'editable': True, 'presentation': 'dropdown'},
                        {'name': 'Correc Spike', 'id': 'spike', 'editable': False},
                        {'name': 'Correc Bias', 'id': 'bias', 'editable': False},
                        #{'name': 'Limpiar', 'id': 'limpiar', 'editable': True, 'presentation': 'dropdown'}
                    ]

                # Almacenar los valores iniciales de la tabla-json en tabla_inicial
                tabla_inicial = {row['Fecha']: row for row in table_data}
                #tabla_inicial = {'valores_iniciales': valores_iniciales}
            else:
                columns, table_data, log_cambios = [], [], {}

        except Exception as e:
            ic(e)
            return dash.no_update, "Error al procesar el archivo", dash.no_update, dash.no_update, dash.no_update, dash.no_update

        print('previo')
        print (tabla_inicial)

        return corregir_tubo_data, informacion_archivo, corregir_archivo_data, columns, table_data, tabla_inicial

    # Callback para manejar cambios en la tabla
    @app.callback(
        Output('log_cambios', 'data'),
        Output('log-cambios', 'children'),
        Input('tabla-json', 'data_previous'),
        Input('tabla-json', 'data'),
        State('corregir-tubo', 'data'),
        State('log_cambios', 'data'),
        State('tabla_inicial', 'data')
    )
    def registrar_cambios(data_previous, data, corregir_tubo, log_cambios, tabla_inicial):
        if data_previous is None:
            raise dash.exceptions.PreventUpdate

        cambios = {k: v for k, v in log_cambios.items() if k != 'log_lines'} if isinstance(log_cambios, dict) else {}

        for i, (prev_row, new_row) in enumerate(zip(data_previous, data)):
            fecha_cambio = new_row['Fecha']  # Obtener la fecha de la primera columna de la fila
            for key in ['Referencia', 'Activa', 'Cuarentena']:
                # Evitar registros si el valor es None
                if new_row[key] is None:
                    continue
                # Solo registrar si hay un cambio válido
                if prev_row[key] != new_row[key]:
                    # Añadir la nueva entrada para la fecha y clave actual
                    cambios_key = f"{fecha_cambio}_{key}"
                    cambios[cambios_key] = {
                        'fecha': fecha_cambio,
                        'clave': key,
                        'original': tabla_inicial[fecha_cambio][key],
                        'old_value': prev_row[key],
                        'new_value': new_row[key]
                    }

        # Eliminar las líneas en las que "original" y "new_value" son iguales
        cambios = {k: v for k, v in cambios.items() if v['original'] != v['new_value']}

        # Ordenar el diccionario cambios de manera cronológica por fecha y luego por clave ('Referencia' primero)
        cambios = dict(sorted(cambios.items(), key=lambda item: (item[1]['fecha'], item[1]['clave'] != 'Referencia')))

        # Construir log_lines después de finalizar con cambios
        log_lines = []
        for key, value in cambios.items():
            if key != 'log_lines':
                log_lines.append(html.Span([
                    html.B('fecha'), f": {value['fecha']} ",
                    html.B(value['clave']), f": {value['original']} → {value['old_value']} → {value['new_value']}"
                ]))
                log_lines.append(html.Br())

        return cambios, log_lines

    # Callback para manejar la selección de filas
    @app.callback(
        Output('salida', 'children'),
        Input('tabla-json', 'selected_rows'),
        State('tabla-json', 'data')
    )
    def mostrar_fila_seleccionada(selected_rows, data):
        if selected_rows:
            fila_seleccionada = data[selected_rows[0]]
            return f"Fila seleccionada: {fila_seleccionada}"
        return "No se ha seleccionado ninguna fila"

    # Callback para guardar los cambios en el archivo corregir-tubo
    @dash.callback(
        Output('recalcular_tabla', 'n_clicks'),
        Input('recalcular_tabla', 'n_clicks'),
        State('log_cambios', 'data')
    )
    def imprimir_cambios(n_clicks, log_cambios):
        if n_clicks:
            print('Cambios registrados:', log_cambios)
        return dash.no_update


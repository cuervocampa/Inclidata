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
                                'width': '100%',
                                'height': '60px',
                                'lineHeight': '60px',
                                'borderWidth': '2px',
                                'borderStyle': 'dashed',
                                'borderRadius': '5px',
                                'borderColor': 'blue',
                                'textAlign': 'center',
                                'margin': '10px 0',
                                'display': 'flex',
                                'justifyContent': 'center',
                                'alignItems': 'center',
                                'color': 'red'
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
            dcc.Store(id='corregir-tubo', storage_type='memory'),
            dcc.Store(id='corregir_archivo', storage_type='memory'),
            dcc.Store(id='log_cambios', data={}, storage_type='memory'),

            # Table and Info Section
            dmc.Grid(
                children=[
                    dmc.Col(
                        dash_table.DataTable(
                            id='tabla-json',
                            style_table={
                                'maxHeight': '200px',
                                'overflowY': 'auto',
                                'overflowX': 'auto',
                                'width': '100%',
                                'margin': '0 auto'
                            },
                            style_cell={'textAlign': 'left'},
                            style_header={
                                'position': 'sticky',
                                'top': 0,
                                'backgroundColor': 'white',
                                'zIndex': 1,
                                'fontWeight': 'bold'
                            },
                            columns=[
                                {'name': 'Fecha', 'id': 'Fecha', 'editable': False},
                                {'name': 'Referencia', 'id': 'Referencia', 'editable': True,
                                 'presentation': 'dropdown'},
                                {'name': 'Activa', 'id': 'Activa', 'editable': True, 'presentation': 'dropdown'},
                                {'name': 'Cuarentena', 'id': 'Cuarentena', 'editable': True, 'presentation': 'dropdown'}
                            ],
                            data=[],  # Inicialmente vacío
                            row_selectable='single',
                            selected_rows=[0],
                            page_action='none',
                            page_size=10,
                            editable=True,
                            dropdown={
                                'Referencia': {
                                    'options': [
                                        {'label': 'True', 'value': True},
                                        {'label': 'False', 'value': False}
                                    ]
                                },
                                'Activa': {
                                    'options': [
                                        {'label': 'True', 'value': True},
                                        {'label': 'False', 'value': False}
                                    ]
                                },
                                'Cuarentena': {
                                    'options': [
                                        {'label': 'True', 'value': True},
                                        {'label': 'False', 'value': False}
                                    ]
                                }
                            }
                        ),
                        span=6
                    ),
                    dmc.Col(
                        children=[
                            html.Div(id='log-cambios',
                                     style={'height': '200px', 'overflowY': 'auto', 'border': '1px solid #ccc',
                                            'padding': '10px'}),
                            dmc.Group(
                                children=[
                                    dmc.Button("Recalcular Tabla", id='recalcular_tabla', variant='outline',
                                               c='blue'),
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
         Output('tabla-json', 'data')],
        [Input('archivo-uploader', 'contents')],
        [State('archivo-uploader', 'filename')]
    )
    def procesar_archivo_contenido(contents, filename):
        if contents is None:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

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
                        'Cuarentena': data[fecha].get('campaign_info', {}).get('quarentine', 'N/A')
                    }
                    table_data.append(row)

                columns = [
                    {'name': 'Fecha', 'id': 'Fecha', 'editable': False},
                    {'name': 'Referencia', 'id': 'Referencia', 'editable': True, 'presentation': 'dropdown'},
                    {'name': 'Activa', 'id': 'Activa', 'editable': True, 'presentation': 'dropdown'},
                    {'name': 'Cuarentena', 'id': 'Cuarentena', 'editable': True, 'presentation': 'dropdown'}
                ]
            else:
                columns, table_data = [], []
        except Exception as e:
            ic(e)
            return dash.no_update, "Error al procesar el archivo", dash.no_update, dash.no_update, dash.no_update

        return corregir_tubo_data, informacion_archivo, corregir_archivo_data, columns, table_data

    # Callback para manejar cambios en la tabla
    @app.callback(
        Output('log_cambios', 'data'),
        Output('log-cambios', 'children'),
        Input('tabla-json', 'data_previous'),
        Input('tabla-json', 'data'),
        State('corregir-tubo', 'data'),
        State('log_cambios', 'data')
    )
    def registrar_cambios(data_previous, data, corregir_tubo, log_cambios):
        if data_previous is None:
            raise dash.exceptions.PreventUpdate

        cambios = {k: v for k, v in log_cambios.items() if k != 'log_lines'} if isinstance(log_cambios, dict) else {}
        log_lines = []

        for i, (prev_row, new_row) in enumerate(zip(data_previous, data)):
            fecha_cambio = new_row['Fecha']  # Obtener la fecha de la primera columna de la fila
            for key in ['Referencia', 'Activa', 'Cuarentena']:
                # Evitar registros si el valor es None
                if new_row[key] is None:
                    continue
                # Solo registrar si hay un cambio válido
                if prev_row[key] != new_row[key]:
                    # Eliminar entradas repetidas para la misma fecha y clave
                    cambios = {k: v for k, v in cambios.items() if
                               not (v['fecha'] == fecha_cambio and v['field'] == key)}

                    cambios_key = f"{fecha_cambio}_{key}"
                    cambios[cambios_key] = {
                        'row': i,
                        'field': key,
                        'fecha': fecha_cambio,
                        'old_value': prev_row[key],
                        'new_value': new_row[key]
                    }
                    log_lines.append(html.Span([
                        html.B('fecha'), f": {fecha_cambio} ",
                        html.B(key), f": {prev_row[key]} → {new_row[key]}"
                    ]))
                    log_lines.append(html.Br())

        # Concatena los nuevos cambios con los existentes para mostrarlos todos
        existing_log_lines = log_cambios.get('log_lines', []) if isinstance(log_cambios, dict) else []
        log_lines = existing_log_lines + log_lines

        # Actualiza log_lines dentro de log_cambios para mantener un historial completo
        cambios['log_lines'] = log_lines

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
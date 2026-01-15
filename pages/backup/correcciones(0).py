# pages/correcciones.py

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

def layout():
    return dmc.MantineProvider(
        children=dmc.Grid([
            html.Div(style={'height': '50px'}),  # Espacio al comienzo de la página

            # Nueva línea con uploader y texto
            dmc.Group(
                children=[
                    dmc.Col(
                        dcc.Upload(
                            id='archivo-uploader',
                            multiple=False,
                            accept='.json',  # Solo acepta archivos JSON
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
                        span=3  # Ocupa el 30% del ancho
                    ),
                    dmc.Col(
                        html.Div(id='informacion-archivo', style={'width': '100%'}),
                        span=4  # Ocupa el 40% del ancho
                    ),
                    dmc.Col(
                        html.Div(),
                        span=3  # Ocupa el 30% restante del ancho
                    )
                ],
                style={'width': '100%'}  # Toda la línea ocupa el 100% del ancho
            ),
            dcc.Store(id='corregir-tubo', storage_type='memory'),  # lee el json y lo deja en la memoria
            dcc.Store(id='corregir_archivo', storage_type='memory'),  # deja en memoria el nombre del archivo

            # Nueva fila para la tabla
            dmc.Grid(
                children=[
                    dmc.Col(
                        dash_table.DataTable(
                            id='tabla-json',
                            style_table={
                                'maxHeight': '200px',
                                'overflowY': 'auto',
                                'overflowX': 'auto',
                                'width': '100%',  # La tabla ocupa todo el ancho de su columna
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
                            columns=[],  # Las columnas se actualizarán dinámicamente según el archivo subido
                            data=[],
                            row_selectable='single',
                            selected_rows=[0],
                            page_action='none',
                            page_size=10,  # Limita el número de filas mostradas a 10
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
                        span=6,  # La tabla ocupa la mitad de la fila
                    )
                ],
                style={'width': '100%'}  # La fila ocupa todo el ancho de la pantalla
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
            # Guarda el archivo en 'corregir-tubo'
            corregir_tubo_data = data
            # Actualiza 'informacion-archivo' con el valor de data['info']['nom_sensor']
            informacion_archivo = html.Span([
                html.B("Inclinómetro: "),
                html.Span(data['info']['nom_sensor'])
            ])
            # Guarda el nombre del archivo en 'corregir_archivo'
            corregir_archivo_data = filename

            # Extrae las fechas y prepara los datos para la tabla
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

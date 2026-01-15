import dash
from dash import Input, Output, State, html, dcc, dash_table, MATCH, ALL, ctx
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time, timedelta
import time as time_pck
import os
import dash_daq as daq
import plotly.express as px

app = dash.Dash(__name__, external_stylesheets=['https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap'])

app.layout = html.Div(
    style={'margin-top': '70px'},
    children=[
        html.Div(
            style={'display': 'grid', 'gridTemplateColumns': '2fr 1fr', 'gap': '20px'},
            children=[
                # Section for Map (Component 2)
                html.Div(
                    style={'border': '1px solid #e0e0e0', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'},
                    children=[
                        html.H4('Mapa', style={'textAlign': 'center'}),
                        dcc.Graph(id='mapa', style={'height': '400px'})
                    ]
                ),

                # Uploader, Information, Pattern, and Configuration (Components 3, 4, 5, 6)
                html.Div(
                    style={'display': 'flex', 'flexDirection': 'column', 'gap': '10px'},
                    children=[
                        html.Div(
                            style={'display': 'flex', 'alignItems': 'center', 'gap': '10px'},
                            children=[
                                dcc.Upload(
                                    id='uploader',
                                    children=html.Div([
                                        'Seleccionar Sensores'
                                    ]),
                                    style={
                                        'width': '200px',
                                        'height': '40px',
                                        'lineHeight': '40px',
                                        'borderWidth': '1px',
                                        'borderStyle': 'dashed',
                                        'borderRadius': '5px',
                                        'textAlign': 'center'
                                    },
                                    multiple=False,
                                ),
                                html.Div(
                                    children=[
                                        html.Button('Información', id='informacion-button'),
                                        html.Div(id='hover-info', style={'marginLeft': '10px', 'fontSize': '12px', 'color': '#555'})
                                    ]
                                )
                            ]
                        ),
                        html.Button('Configurar Patrón', id='patron-button', style={'backgroundColor': 'indigo', 'color': 'white'}),
                        html.Div(
                            id='drawer-patron-content',
                            style={'display': 'none', 'position': 'fixed', 'top': 0, 'right': 0, 'width': '300px', 'height': '100%', 'backgroundColor': 'white', 'padding': '20px', 'boxShadow': '0 0 15px rgba(0,0,0,0.2)', 'zIndex': 1000},
                            children=[
                                html.H4('Barra Lateral de Configuración', style={'textAlign': 'center'}),
                                dcc.Dropdown(
                                    id='dropdown-1',
                                    options=[
                                        {'label': 'Opción 1', 'value': 'opcion1'},
                                        {'label': 'Opción 2', 'value': 'opcion2'}
                                    ],
                                    placeholder='Selecciona una opción'
                                ),
                                dcc.Dropdown(
                                    id='dropdown-2',
                                    options=[
                                        {'label': 'Opción A', 'value': 'opcionA'},
                                        {'label': 'Opción B', 'value': 'opcionB'}
                                    ],
                                    placeholder='Selecciona otra opción'
                                )
                            ]
                        ),
                        html.Button('Configuración', id='configuracion-button', style={'backgroundColor': 'blue', 'color': 'white'}),
                    ]
                )
            ]
        ),

        # Tabs for Inclis Graphs (Component 7) and Dates Component (Component 8)
        html.Div(
            style={'display': 'grid', 'gridTemplateColumns': '3fr 1fr', 'gap': '20px', 'margin-top': '20px'},
            children=[
                html.Div(
                    style={'border': '1px solid #e0e0e0', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'},
                    children=[
                        dcc.Tabs(
                            id='graficos-inclis',
                            value='tab-1',
                            children=[
                                dcc.Tab(label='Gráfico 1', value='tab-1'),
                                dcc.Tab(label='Gráfico 2', value='tab-2'),
                                dcc.Tab(label='Gráfico 3', value='tab-3')
                            ],
                        )
                    ]
                ),
                html.Div(
                    style={'border': '1px solid #e0e0e0', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'},
                    children=[
                        html.H4('Fechas', style={'textAlign': 'center'}),
                        dcc.Dropdown(id='fechas', placeholder='Selecciona una campaña')
                    ]
                )
            ]
        ),

        # Temporal Graph (Component 9) and Depth List Component (Component 10)
        html.Div(
            style={'display': 'grid', 'gridTemplateColumns': '3fr 1fr', 'gap': '20px', 'margin-top': '20px'},
            children=[
                html.Div(
                    style={'border': '1px solid #e0e0e0', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'},
                    children=[
                        html.H4('Gráfico Temporal', style={'textAlign': 'center'}),
                        dcc.Graph(id='temporal')
                    ]
                ),
                html.Div(
                    style={'border': '1px solid #e0e0e0', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'},
                    children=[
                        html.H4('Profundidad', style={'textAlign': 'center'}),
                        dcc.Dropdown(id='profundidad', placeholder='Selecciona una profundidad')
                    ]
                )
            ]
        )
    ]
)


@app.callback(
    Output('hover-info', 'children'),
    Input('uploader', 'contents')
)
def update_hover_info(file_value):
    if file_value:
        return 'Archivo subido correctamente'
    return 'No hay información disponible'  # Placeholder


@app.callback(
    Output('drawer-patron-content', 'style'),
    Input('patron-button', 'n_clicks'),
    State('drawer-patron-content', 'style')
)
def toggle_drawer_patron(n_clicks, current_style):
    if n_clicks:
        return {'display': 'block'} if current_style['display'] == 'none' else {'display': 'none'}
    return current_style


if __name__ == '__main__':
    app.run_server(debug=True)

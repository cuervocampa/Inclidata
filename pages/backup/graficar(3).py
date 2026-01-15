from turtledemo.penrose import start

from dash import html, dcc, callback_context
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
import base64, json
import dash
from icecream import ic
from datetime import datetime, timedelta
import plotly.graph_objs as go
import plotly.colors as pcolors
import re

#from xlwings.pro.reports.filters import width


#from xlwings.pro.reports.filters import width


def layout():
    return dmc.MantineProvider(
        children=html.Div([
            html.Div(style={'height': '50px'}),  # Espacio al comienzo de la página
            dmc.Grid([
                dmc.Col(
                    dmc.Card(
                        html.Div(
                            "Plano de localización de dispositivo",
                            style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'height': '400px'}
                        ),
                        shadow='sm', radius='md'
                    ), span=6
                ),
                dmc.Col([
                    dmc.Group(
                        [
                            dcc.Upload(
                                id='graficar-uploader',
                                multiple=False,
                                accept='.json',  # Solo acepta archivos JSON
                                children=['Drag and Drop o seleccionar sensores'],
                                style={
                                    'width': '100%',
                                    'height': '60px',
                                    'lineHeight': '60px',
                                    'borderWidth': '2px',  # Línea más gruesa
                                    'borderStyle': 'dashed',
                                    'borderRadius': '5px',
                                    'borderColor': 'blue',  # Color azul para la línea
                                    'textAlign': 'center',
                                    'margin': '10px 0',
                                    'display': 'flex',
                                    'justifyContent': 'center',
                                    'alignItems': 'center',
                                    'color': 'red'
                                }
                            ),
                            dcc.Store(id='graficar-tubo', storage_type='memory'),  # lee el json y lo deja en la memoria
                            dmc.HoverCard(
                                children=html.Div(
                                    [
                                        html.Span("Sensor:", style={'fontWeight': 'bold'}),
                                        html.Span(id="info-hovercard")
                                    ]
                                ),
                                withArrow=True,
                                style={
                                    'width': '100%',
                                    'marginBottom': '20px'  # Espaciamiento entre HoverCard y el siguiente componente
                                }
                            )
                        ],
                        style={'width': '100%'}  # Ambos componentes ocupan el 100% de la línea
                    ),
                    dmc.Group(
                        [
                            dmc.Button("Patrón", id="open-patron-drawer", n_clicks=None, fullWidth=True),
                            dmc.Button("Configuración", id="open-config-drawer", n_clicks=None, fullWidth=True)
                        ],
                        style={'display': 'flex', 'flexDirection': 'column'},
                        gap="1"  # Espaciamiento entre botones
                    ),
                ], span=6)
            ]),
            dmc.Drawer(
                title="Configurar Patrón",
                id="drawer-patron",
                children=[
                    html.P("Seleccionar rango de fechas"),
                    dcc.DatePickerRange(
                        id='date_range_picker',
                        start_date=None,  # Se actualizará dinámicamente con la primera fecha del DataFrame
                        end_date=datetime.now(),
                        display_format='YYYY-MM-DD',
                        style={'marginTop': '10px'}
                    ),
                    html.P("Configuración del patrón aquí."),
                    dmc.NumberInput(
                        label="Total campañas a mostrar",
                        id="total_camp",
                        value=30,# ajustar a posteriori
                        min=1
                    ),
                    dmc.NumberInput(
                        label="Pintar los últimos días",
                        id="ultimas_camp",
                        value=30,# ajustar a posteriori
                        min=1
                    ),
                    dmc.NumberInput(
                        label="Una campaña cada x días",
                        id="cadencia_dias",
                        value=30,
                        min=1
                    ),
                    html.Div(style={'height': '20px'}),  # Espacio en blanco entre el último input y el botón
                    dmc.Button("Cerrar", id="close-patron-drawer", n_clicks=None)
                ],
                opened=False,
                justify="flex-end"
            ),
            dmc.Drawer(
                title="Configuración General",
                id="drawer-config",
                children=[
                    html.P("Configuración general aquí."),
                    dmc.NumberInput(
                        label="Altura de los gráficos (px)",
                        id="alto_graficos",
                        value=800,
                        min=100,
                        step=50
                    ),
                    dmc.Button("Cerrar", id="close-config-drawer", n_clicks=None)
                ],
                opened=False,
                justify="flex-end"
            ),
            dmc.Divider(style={"marginTop": "20px", "marginBottom": "20px"}),
            dmc.Grid([
                dmc.Col( # gráficos de desplazamientos vs profunfidadad
                    dmc.Tabs([
                        dmc.TabsList([
                            dmc.Tab("Desplazamientos", value="grafico1", style={'fontWeight': 'bold', 'fontSize': '1.1rem'}),
                            dmc.Tab("Incrementales", value="grafico2", style={'fontWeight': 'bold', 'fontSize': '1.1rem'}),
                            dmc.Tab("Despl. compuestos", value="grafico3", style={'fontWeight': 'bold', 'fontSize': '1.1rem'})
                        ]),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.Col([
                                        dcc.Graph(id='grafico_incli_1_a'),
                                        dmc.Text("Desplazamiento A", ta="center")
                                    ], span=6),
                                    dmc.Col([
                                        dcc.Graph(id='grafico_incli_1_b'),
                                        dmc.Text("Desplazamiento B", ta="center")
                                    ], span=6)
                                ])
                            ]),
                            value="grafico1"
                        ),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.Col([
                                        dcc.Graph(id='grafico_incli_2_a'),
                                        dmc.Text("Incremental A", ta="center")
                                    ], span=6),
                                    dmc.Col([
                                        dcc.Graph(id='grafico_incli_2_b'),
                                        dmc.Text("Incremental B", ta="center")
                                    ], span=6)
                                ])
                            ]),
                            value="grafico2"
                        ),
                        dmc.TabsPanel(
                            html.Div([
                                dmc.Grid([
                                    dmc.Col([
                                        dcc.Graph(id='grafico_incli_3_a'),
                                        dmc.Text("Desplazamiento A", ta="center")
                                    ], span=4),
                                    dmc.Col([
                                        dcc.Graph(id='grafico_incli_3_b'),
                                        dmc.Text("Desplazamiento B", ta="center")
                                    ], span=4),
                                    dmc.Col([
                                        dcc.Graph(id='grafico_incli_3_total'),
                                        dmc.Text("Desplazamientos Totales", ta="center")
                                    ], span=4)
                                ])
                            ]),
                            value="grafico3"
                        )
                    ], value="grafico1"),
                    span=9  # Ocupa el 70% de la fila
                ),

                dmc.Col([
                    dmc.Title("Fechas", order=4),
                    dmc.Space(h=20),  # espacio entre componentes
                    dmc.MultiSelect(
                        id='fechas_multiselect',
                        data=[],  # Inicialmente vacío
                        placeholder="Selecciona opciones",
                        searchable=True
                    ),
                    dmc.Space(h=10),
                    dcc.Slider(
                        id='slider_fechas',
                        min=0,
                        max=1,  # This will be updated dynamically with the number of dates available
                        value=1,  # Initially set to the most recent date (last index)
                        marks={},  # Marks will be set dynamically to show dates
                        tooltip={"placement": "bottom", "always_visible": False},
                        className='slider-ocultar-tooltip-marks'  # Clase CSS para ocultar tooltip y marcas
                    ),
                    html.Div(id='slider_fecha_tooltip', style={'marginTop': '10px', 'fontWeight': 'bold'}),
                ], span=3)  # Ocupa el 30% de la fila
            ], style={"width": "100%"}),

            dmc.Divider(style={"marginTop": "20px", "marginBottom": "20px"}),
            dmc.Grid([
                dmc.Col(
                    dcc.Graph(id='grafico_temporal'),
                    span=9  # Ocupa el 70% de la fila
                ),
                dmc.Col([
                    dmc.Title("Profundidades", order=4),
                    dmc.Space(h=20),  # espacio entre componentes
                    dmc.MultiSelect(
                        id='profundidades_multiselect',
                        data=[],  # Inicialmente vacío
                        placeholder="Selecciona profundidades"
                    ),
                    dmc.Space(h=20),  # espacio entre componentes
                    dmc.MultiSelect(
                        id='desplazamientos_multiselect',
                        data=[
                            {"value": "desp_a", "label": "desp_a"},
                            {"value": "desp_b", "label": "desp_b"},
                            {"value": "desp_total", "label": "desp_total"}
                        ],
                        value=["desp_a"],  # Valor por defecto
                        placeholder="Selecciona tipo de desplazamiento"
                    )
                ], span=3)  # Ocupa el 30% de la fila
            ], style={"width": "100%"})
        ]),
        inherit=True  # To inherit default Mantine styles
    )

# Definir una paleta de colores para las series
color_palette = pcolors.qualitative.Plotly

def get_color_for_index(index):
    return color_palette[index % len(color_palette)]

# Registra los callbacks en lugar de definir un nuevo Dash app
def register_callbacks(app):
    @app.callback(
        Output("drawer-patron", "opened"),
        [Input("open-patron-drawer", "n_clicks"), Input("close-patron-drawer", "n_clicks")],
        [State("drawer-patron", "opened")]
    )
    def toggle_patron_drawer(open_clicks, close_clicks, is_open):
        if open_clicks is None:
            open_clicks = 0
        if close_clicks is None:
            close_clicks = 0

        return open_clicks > close_clicks

    @app.callback(
        Output("drawer-config", "opened"),
        [Input("open-config-drawer", "n_clicks"), Input("close-config-drawer", "n_clicks")],
        [State("drawer-config", "opened")]
    )
    def toggle_config_drawer(open_clicks, close_clicks, is_open):
        if open_clicks is None:
            open_clicks = 0
        if close_clicks is None:
            close_clicks = 0

        return open_clicks > close_clicks

    # Carga de datos del archivo
    @app.callback(
        [Output("info-hovercard", "children"),
         Output("graficar-tubo", "data")],
        [Input("graficar-uploader", "contents")],
        [State("graficar-uploader", "filename")]
    )
    def update_hovercard_and_store(contents, filename):
        if contents and filename:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            try:
                data = json.loads(decoded)

                # Crear el nuevo diccionario
                nuevo_diccionario = {
                    "info": data["info"],
                }

                # Recorrer las claves del diccionario original y guardo sólo lo que interesa
                for index, (clave, valor) in enumerate(data.items()):
                    #if clave != "info" and "calc" in valor:
                    if clave != "info" and "calc" in valor and valor.get("campaign_info", {}).get("active") == True:

                        nuevo_diccionario[clave] = {
                            "calc": [
                                {
                                    "index": item["index"],
                                    "cota_abs": item["cota_abs"],
                                    "incr_dev_a": item["incr_dev_a"],
                                    "incr_dev_b": item["incr_dev_b"],
                                    "desp_a": item["desp_a"],
                                    "desp_b": item["desp_b"]
                                }
                                for item in valor["calc"] if isinstance(item, dict) and "index" in item
                            ],
                            "color": get_color_for_index(index)
                        }
                return f"\t{filename}", nuevo_diccionario
            except Exception as e:
                ic(e)  # Añadido para mostrar el error en caso de fallo
                return f"\t{filename}", None
        return "", None

    # Carga de las fechas del data-picker
    @app.callback(
        [Output("date_range_picker", "start_date"),
         Output("date_range_picker", "end_date")],
        Input("graficar-tubo", "data")
    )
    def pordefecto_data_picker(data):
        if not data:
            return None, None

        try:
            # Ordenar las fechas correctamente de más antigua a más reciente
            fechas = sorted([clave for clave in data.keys() if clave != "info"],
                            key=lambda x: datetime.fromisoformat(x))
            fechas = fechas[::-1]  # Cambiar para obtener de más reciente a más antigua

            # Obtener la primera fecha para el rango inicial
            start_date = fechas[-1] if fechas else None
            end_date = fechas[0] if fechas else None

            return start_date, end_date

        except ValueError as e:
            ic(e)  # Añadido para mostrar el error en caso de fallo
            return None, None

    # carga de las campañas seleccionadas en el multiselect a partir del filtro-inteligente
    @app.callback(
        [Output("fechas_multiselect", "data"),
         Output("fechas_multiselect", "value")],
        [Input("graficar-tubo", "data"),
         Input("total_camp", "value"),
         Input("ultimas_camp", "value"),
         Input("cadencia_dias", "value"),
         Input("date_range_picker", "start_date"),
         Input("date_range_picker", "end_date")]
    )
    def update_fechas_multiselect(data, total_camp, ultimas_camp, cadencia_dias, start_date, end_date):
        if not data:
            return [], []

        try:
            # Ordenar las fechas correctamente de más antigua a más reciente
            fechas = sorted([clave for clave in data.keys() if clave != "info"],
                            key=lambda x: datetime.fromisoformat(x))
            fechas = fechas[::-1]  # Cambiar para obtener de más reciente a más antigua

            # Filtrar fechas dentro del rango seleccionado
            fechas = [fecha for fecha in fechas if start_date <= fecha <= end_date]

            options = [
                {
                    "value": fecha,
                    "label": fecha,
                    "style": {"color": data[fecha]["color"]}
                }
                for fecha in fechas
            ]

            # Seleccionar automáticamente las fechas según los parámetros de configuración
            total_fechas = len(fechas)
            seleccionadas = []

            # Seleccionar las últimas 'ultimas_camp' fechas
            if ultimas_camp > 0:
                seleccionadas.extend(fechas[:ultimas_camp])

            # Seleccionar más fechas según la cadencia de 'cadencia_dias'
            if cadencia_dias > 0 and len(seleccionadas) < total_camp:
                ultima_fecha_seleccionada = datetime.fromisoformat(
                    seleccionadas[-1])  # Última fecha seleccionada inicialmente
                for fecha_str in fechas[ultimas_camp:]:
                    fecha_actual = datetime.fromisoformat(fecha_str)
                    diferencia_dias = (ultima_fecha_seleccionada - fecha_actual).days

                    # Verificar si la fecha actual cumple con la cadencia de días
                    if diferencia_dias >= cadencia_dias:
                        seleccionadas.append(fecha_str)
                        ultima_fecha_seleccionada = fecha_actual

                    # Parar si ya se han seleccionado las fechas necesarias
                    if len(seleccionadas) >= total_camp:
                        break

            # Asegurarse de que no se seleccionen más fechas de las necesarias
            seleccionadas = seleccionadas[:total_camp]

            return options, seleccionadas
        except ValueError as e:
            ic(e)  # Añadido para mostrar el error en caso de fallo
            return [], []

    @app.callback(
        Output("profundidades_multiselect", "data"),
        [Input("graficar-tubo", "data")]
    )
    def update_profundidades_multiselect(data):
        if not data:
            return []

        try:
            # Buscar todas las claves que sean fecha y extraer "cota_abs" de "calc"
            cotas_abs = set()
            for clave, valor in data.items():
                if clave != "info" and "calc" in valor:
                    cotas_abs.update(item["cota_abs"] for item in valor["calc"] if "cota_abs" in item)

            # Convertir a lista, eliminar duplicados y ordenar
            cotas_abs = sorted(cotas_abs)

            # Crear las opciones para el MultiSelect
            options = [{"value": cota, "label": str(cota)} for cota in cotas_abs]

            return options
        except Exception as e:
            ic(e)  # Añadido para mostrar el error en caso de fallo
            return []

    # Agregar callbacks para los gráficos
    # Grupo de gráficos 1: Representación de movimientos vs profundidad, con diferentes opciones
    @app.callback(
        [Output("grafico_incli_1_a", "figure"),
         Output("grafico_incli_1_b", "figure"),
         Output("grafico_incli_2_a", "figure"),
         Output("grafico_incli_2_b", "figure"),
         Output("grafico_incli_3_a", "figure"),
         Output("grafico_incli_3_b", "figure"),
         Output("grafico_incli_3_total", "figure")],
        [Input("fechas_multiselect", "value"),
         Input("slider_fecha_tooltip", "children"),
         Input("graficar-tubo", "data"),
         Input("alto_graficos", "value")]
    )
    def actualizar_graficos(fechas_seleccionadas, slider_value, data, alto_graficos):
        if not fechas_seleccionadas or not data:
            return [go.Figure() for _ in range(7)]

        fig1_a = go.Figure()
        fig1_b = go.Figure()
        fig2_a = go.Figure()
        fig2_b = go.Figure()
        fig3_a = go.Figure()
        fig3_b = go.Figure()
        fig3_total = go.Figure()

        # Obtener la fecha seleccionada en el slider, ojo viene en una cadena del tipo Fecha seleccionada: 2024-10-30 11:57:29
        # extraigo la fecha
        patron = r'Fecha seleccionada: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
        resultado = re.search(patron, slider_value)
        if resultado:
            fecha_hora = resultado.group(1)
            # Convertir la cadena a un objeto datetime
            dt_obj = datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M:%S")
            # Convertir al formato deseado con 'T' en el medio
            fecha_slider = dt_obj.strftime("%Y-%m-%dT%H:%M:%S")


        for fecha in fechas_seleccionadas:
            if fecha in data and "calc" in data[fecha]:
                # Aplica formato específico a la selección del slider
                if fecha == fecha_slider:
                    color = 'yellow'
                    grosor = 6   # El doble de grueso que las líneas normales
                else:
                    color = data[fecha]["color"]
                    grosor = 2

                #color = data[fecha]["color"]
                cota_abs_list = [punto["cota_abs"] for punto in data[fecha]["calc"]]
                desp_a_list = [punto["desp_a"] for punto in data[fecha]["calc"]]
                desp_b_list = [punto["desp_b"] for punto in data[fecha]["calc"]]
                incr_dev_a_list = [punto["incr_dev_a"] for punto in data[fecha]["calc"]]
                incr_dev_b_list = [punto["incr_dev_b"] for punto in data[fecha]["calc"]]
                desp_total_list = [punto["desp_a"] + punto["desp_b"] for punto in data[fecha]["calc"]]

                # Gráfico 1: Desplazamientos
                fig1_a.add_trace(go.Scatter(x=desp_a_list, y=cota_abs_list, mode="markers+lines", name=f"{fecha} - Desp A", line=dict(c=color,width=grosor)))
                fig1_b.add_trace(go.Scatter(x=desp_b_list, y=cota_abs_list, mode="markers+lines", name=f"{fecha} - Desp B", line=dict(c=color,width=grosor)))

                # Gráfico 2: Incrementales
                fig2_a.add_trace(go.Scatter(x=incr_dev_a_list, y=cota_abs_list, mode="markers+lines", name=f"{fecha} - Incr Dev A", line=dict(c=color,width=grosor)))
                fig2_b.add_trace(go.Scatter(x=incr_dev_b_list, y=cota_abs_list, mode="markers+lines", name=f"{fecha} - Incr Dev B", line=dict(c=color,width=grosor)))

                # Gráfico 3: Desplazamientos Compuestos
                fig3_a.add_trace(go.Scatter(x=desp_a_list, y=cota_abs_list, mode="markers+lines", name=f"{fecha} - Desp A", line=dict(c=color,width=grosor)))
                fig3_b.add_trace(go.Scatter(x=desp_b_list, y=cota_abs_list, mode="markers+lines", name=f"{fecha} - Desp B", line=dict(c=color,width=grosor)))
                fig3_total.add_trace(go.Scatter(x=desp_total_list, y=cota_abs_list, mode="markers+lines", name=f"{fecha} - Desp Total", line=dict(c=color,width=grosor)))

        # Configurar ejes y quitar leyendas, ajustar altura de gráficos
        for fig in [fig1_a, fig1_b, fig2_a, fig2_b, fig3_a, fig3_b, fig3_total]:
            fig.update_layout(yaxis=dict(autorange="reversed"), showlegend=False, height=alto_graficos, title_x=0.5)

        return [fig1_a, fig1_b, fig2_a, fig2_b, fig3_a, fig3_b, fig3_total]

    @app.callback(
        Output("grafico_temporal", "figure"),
        [Input("profundidades_multiselect", "value"),
         Input("graficar-tubo", "data"),
         Input("desplazamientos_multiselect", "value"),
         Input("date_range_picker", "start_date"),
         Input("date_range_picker", "end_date")]
    )
    def actualizar_grafico_temporal(profundidades_seleccionadas, data, desplazamientos_seleccionados, start_date, end_date):
        if not profundidades_seleccionadas or not data or not desplazamientos_seleccionados:
            return go.Figure()

        fig_temporal = go.Figure()

        # Obtener y ordenar las fechas de más antigua a más reciente
        fechas_temp = sorted([fecha for fecha in data.keys() if fecha != "info"], key=lambda x: datetime.fromisoformat(x))

        # Filtrar fechas dentro del rango seleccionado
        fechas_temp = [fecha for fecha in fechas_temp if start_date <= fecha <= end_date]

        for profundidad in profundidades_seleccionadas:
            for desplazamiento in desplazamientos_seleccionados:
                valores = []
                for fecha in fechas_temp:
                    if "calc" in data[fecha]:
                        puntos = data[fecha]["calc"]
                        for punto in puntos:
                            if punto.get("cota_abs") == profundidad and desplazamiento in punto:
                                valores.append(punto[desplazamiento])
                                break
                        else:
                            valores.append(None)  # Añadir None si no se encuentra la cota

                # Añadir la serie temporal al gráfico
                fig_temporal.add_trace(go.Scatter(x=fechas_temp, y=valores, mode="markers+lines", name=f"{desplazamiento} ({profundidad})"))

        fig_temporal.update_layout(title="Series Temporales", title_x=0.5)

        return fig_temporal

    # Callback to update the slider properties based on fechas_multiselect data
    from datetime import datetime

    # slider

    @app.callback(
        [Output('slider_fechas', 'min'),
         Output('slider_fechas', 'max'),
         Output('slider_fechas', 'marks'),
         Output('slider_fechas', 'value')],
        [Input('fechas_multiselect', 'value')]
    )
    def update_slider_dates(fechas):
        if not fechas:
            return 0, 0, {}, 0

        try:
            # Obtener la lista de fechas del campo 'value' de cada elemento del diccionario
            #fechas_str = [fecha['value'] for fecha in fechas if 'value' in fecha]
            fechas_str = fechas

            # Convertir las fechas a objetos datetime
            fechas_dt = [datetime.fromisoformat(fecha) for fecha in fechas_str]

            # Ordenar las fechas para asegurar que están en orden cronológico
            fechas_dt.sort()

            # Obtener la fecha inicial
            fecha_inicial = fechas_dt[0]

            # Crear el diccionario de marcas donde la clave es el número de días desde la fecha inicial
            marks = {(fecha - fecha_inicial).days: fecha.strftime('%Y-%m-%d') for fecha in fechas_dt}

            # Valor mínimo y máximo del slider
            min_value = 0
            max_value = (fechas_dt[-1] - fecha_inicial).days

            # Establecer el valor inicial como el valor máximo (última fecha)
            value = max_value

            return min_value, max_value, marks, value

        except Exception as e:
            # Manejar cualquier error y devolver valores por defecto
            print(f"Error al convertir las fechas: {e}")
            return 0, 0, {}, 0

    # tooltip para mostrar la fecha en el slider
    @app.callback(
        Output('slider_fecha_tooltip', 'children'),
        [Input('slider_fechas', 'value')],
        [State('fechas_multiselect', 'value')]
    )
    def update_slider_tooltip(value, fechas):
        if not fechas:
            return "No hay fechas disponibles"

        try:
            # Obtener la lista de fechas del campo 'value' de cada elemento del diccionario
            #fechas_str = [fecha['value'] for fecha in fechas if 'value' in fecha]
            fechas_str = fechas

            # Convertir las fechas a objetos datetime
            fechas_dt = [datetime.fromisoformat(fecha) for fecha in fechas_str]

            # Ordenar las fechas para asegurar que están en orden cronológico
            fechas_dt.sort()

            # Obtener la fecha inicial
            fecha_inicial = fechas_dt[0]

            # Calcular la fecha correspondiente al valor del slider
            fecha_seleccionada = fecha_inicial + timedelta(days=value)

            # Buscar la fecha más cercana a la fecha seleccionada
            fecha_cercana = min(fechas_dt, key=lambda x: abs((x - fecha_seleccionada).days))

            return f"Fecha seleccionada: {fecha_cercana}"

        except Exception as e:
            print(f"Error al actualizar el tooltip del slider: {e}")
            return "Error al actualizar la fecha"









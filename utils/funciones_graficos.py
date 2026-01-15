# utils/funciones_graficos.py

import plotly.graph_objs as go
from dash import html, dcc
from datetime import datetime
import pandas as pd
import random

def importar_graficos(selected_file_data, fechas_agg):
    # selected_file_data: es todo el tubo
    # fechas_agg: fechas a agregar

    fig_left = go.Figure()
    fig_right = go.Figure()

    for fecha in fechas_agg:
        data = selected_file_data[fecha]['calc']
        depth = [d['depth'] for d in data] if isinstance(data, list) else data.get('depth', [])
        desp_a = [d['desp_a'] for d in data] if isinstance(data, list) else data.get('desp_a', [])
        desp_b = [d['desp_b'] for d in data] if isinstance(data, list) else data.get('desp_b', [])

        # Gráfico de la izquierda
        fig_left.add_trace(
            go.Scatter(x=desp_a, y=depth, mode='lines+markers', name=f"{fecha} - desp_a"))
        # Gráfico de la derecha
        fig_right.add_trace(
            go.Scatter(x=desp_b, y=depth, mode='lines+markers', name=f"{fecha} - desp_b"))

    # añado la campaña anterior para que se pueda comparar

    def encontrar_fecha_anterior(selected_file_data, fechas_agg):
        # Filtrar las claves que son fechas (excluyendo 'info' y 'umbrales')
        fechas = [clave for clave in selected_file_data.keys() if clave not in ['info', 'umbrales']]

        # Convertir las fechas a objetos datetime para poder compararlas
        fechas_datetime = [datetime.strptime(fecha, '%Y-%m-%dT%H:%M:%S') for fecha in fechas]
        fechas_agg_datetime = [datetime.strptime(fecha, '%Y-%m-%dT%H:%M:%S') for fecha in fechas_agg]

        # Encontrar la fecha más antigua de fechas_agg
        fecha_mas_antigua_agg = min(fechas_agg_datetime)

        # Filtrar fechas anteriores a la más antigua de fechas_agg
        fechas_anteriores = [fecha for fecha, fecha_dt in zip(fechas, fechas_datetime)
                             if fecha_dt < fecha_mas_antigua_agg]

        # Verificar la condición campaign_info.active y encontrar la más reciente
        fechas_validas = []
        for fecha in fechas_anteriores:
            try:
                if selected_file_data[fecha]['campaign_info']['active'] == True:
                    fechas_validas.append(fecha)
            except KeyError:
                # Si la estructura no existe, omitir esta fecha
                continue

        if fechas_validas:
            # Convertir las fechas válidas a datetime para encontrar la más reciente
            fechas_validas_dt = [datetime.strptime(fecha, '%Y-%m-%dT%H:%M:%S') for fecha in fechas_validas]
            indice_max = fechas_validas_dt.index(max(fechas_validas_dt))
            return fechas_validas[indice_max]
        else:
            return None

    fecha_anterior = encontrar_fecha_anterior(selected_file_data, fechas_agg)

    if fecha_anterior:
        # se añade al gráfico
        data = selected_file_data[fecha_anterior]['calc']
        depth = [d['depth'] for d in data] if isinstance(data, list) else data.get('depth', [])
        desp_a = [d['desp_a'] for d in data] if isinstance(data, list) else data.get('desp_a', [])
        desp_b = [d['desp_b'] for d in data] if isinstance(data, list) else data.get('desp_b', [])
        # Gráfico de la izquierda
        fig_left.add_trace(
            go.Scatter(x=desp_a, y=depth, mode='lines', name=f"{fecha_anterior} - anterior",
                       line=dict(
                           color='red',  # Color rojo
                           width=2,  # Grosor de línea 2
                           dash='dash'  # Línea discontinua
                       )
                       ))
        # Gráfico de la derecha
        fig_right.add_trace(
            go.Scatter(x=desp_b, y=depth, mode='lines', name=f"{fecha_anterior} - anterior",
                       line=dict(
                           color='red',  # Color rojo
                           width=2,  # Grosor de línea 2
                           dash='dash'  # Línea discontinua
                       )
                       ))

        # pinto los umbrales
        # Definir una lista de colores
        colores_fijos = ['green', 'orange', 'red']

        # Contador para rastrear cuántas trazas hemos agregado
        contador_trazas = 0

        # Comprobar si existe la clave 'umbrales' y tiene contenido en 'deformadas'
        if ('umbrales' in selected_file_data and 'deformadas' in selected_file_data['umbrales'] and
                selected_file_data['umbrales']['deformadas']):
            # hay umbrales
            # Extraer los datos
            valores = selected_file_data['umbrales']['valores']
            deformadas = selected_file_data['umbrales']['deformadas']
            df = pd.DataFrame(valores)
            grosor = 4

            # Para cada deformada, añadir una traza en la figura correspondiente
            for deformada in deformadas:
                # Determinar en qué figura debe ir la deformada
                if deformada.endswith("_a"):
                    fig = fig_left
                elif deformada.endswith("_b"):
                    fig = fig_right
                else:
                    continue  # Si no termina en _a o _b, no se grafica

                # Determinar el color para esta traza
                if contador_trazas < len(colores_fijos):
                    # Usar un color de la lista fija
                    color = colores_fijos[contador_trazas]
                else:
                    # Generar un color hexadecimal aleatorio
                    color = f'#{random.randint(0, 0xFFFFFF):06x}'

                # Incrementar el contador de trazas
                contador_trazas += 1

                # Agregar la traza a la figura correspondiente
                fig.add_trace(go.Scatter(
                    x=df[deformada],  # Valores de la deformada actual
                    y=df['depth'],  # Lista de profundidades
                    mode="lines",
                    name=f"{deformada}",  # Nombre del ítem de deformadas
                    line=dict(
                        width=grosor,
                        color=color
                    ),
                ))


    # Configurar las propiedades de los ejes
    fig_left.update_layout(
        title="Profundidad vs Desplazamiento A",
        xaxis_title="Desplazamiento A",
        yaxis_title="Profundidad",
        xaxis=dict(range=[-10, 10]),
        yaxis=dict(autorange='reversed'),
        showlegend=False,
        height=800,  # Duplicar la altura
        margin=dict(l=40, r=40, t=40, b=40)  # Ajustar márgenes para mejor visualización
    )
    fig_right.update_layout(
        title="Profundidad vs Desplazamiento B",
        xaxis_title="Desplazamiento B",
        yaxis_title="Profundidad",
        xaxis=dict(range=[-10, 10]),
        yaxis=dict(autorange='reversed'),
        height=800,
        margin=dict(l=40, r=40, t=40, b=40)  # Ajustar márgenes para mejor visualización
    )

    # Crear la disposición de gráficos en una fila
    graphs = html.Div([
        html.Div([dcc.Graph(figure=fig_left)],
                 style={'width': '40%', 'display': 'inline-block', 'vertical-align': 'top'}),
        html.Div([dcc.Graph(figure=fig_right)],
                 style={'width': '40%', 'display': 'inline-block', 'vertical-align': 'top'})
    ])

    return graphs

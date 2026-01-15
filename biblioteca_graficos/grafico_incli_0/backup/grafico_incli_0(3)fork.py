# grafico_incli_0.py
import matplotlib
matplotlib.use('Agg')  # Establecer backend no interactivo antes de importar pyplot
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.colors as mcolors
from matplotlib.ticker import AutoMinorLocator
import io
import base64

# grafico_incli_0.py
import matplotlib.pyplot as plt



import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.colors as mcolors
from matplotlib.ticker import AutoMinorLocator
import io
import base64

# Importar funciones desde el archivo funciones.py
from funciones import (
    calcular_fechas_seleccionadas,
    determinar_fecha_slider,
    generar_info_colores,
    obtener_leyenda_umbrales,
    obtener_color_para_fecha,
    extraer_datos_fecha,
    agregar_umbrales,
    configurar_ejes,
    interpolar_def_tubo
)

def grafico_incli_0(data, parametros):
    """
    Genera un gráfico de inclinometría para visualizar desplazamientos o inclinaciones.

    Args:
        data (dict): Diccionario con todos los datos del tubo, incluyendo campañas y umbrales.
        parametros (dict): Diccionario con parámetros de configuración y visualización.
            - nombre_sensor (str): Nombre del sensor o inclinómetro.
            - sensor (str): Tipo de sensor a visualizar ("desp_a", "desp_b", "incr_dev_abs_a", etc).
            - fecha_inicial (str): Fecha de inicio del rango a considerar (formato ISO).
            - fecha_final (str): Fecha final del rango a considerar (formato ISO).
            - total_camp (int): Total de campañas a mostrar.
            - ultimas_camp (int): Número de últimas campañas a mostrar.
            - cadencia_dias (int): Intervalo en días entre campañas.
            - color_scheme (str): Esquema de colores ("monocromo" o "multicromo").
            - escala_desplazamiento (str): Tipo de escala para gráficos de desplazamiento.
            - escala_incremento (str): Tipo de escala para gráficos incrementales.
            - valor_positivo_desplazamiento (float): Límite superior para escala de desplazamiento.
            - valor_negativo_desplazamiento (float): Límite inferior para escala de desplazamiento.
            - valor_positivo_incremento (float): Valor máximo para escala incremental.
            - valor_negativo_incremento (float): Valor mínimo para escala incremental.
            - eje (str): Unidades del eje vertical ("index", "cota_abs", "depth").
            - orden (bool): Orden ascendente (True) o descendente (False).
            - ancho_cm (float): Ancho del gráfico en centímetros.
            - alto_cm (float): Alto del gráfico en centímetros.
            - dpi (int): Resolución de la imagen en puntos por pulgada.

    Returns:
        str: Imagen del gráfico en formato PNG codificada en base64 (data URL).
    """
    # PASO 1: Extraer parámetros con valores por defecto si no están presentes
    nombre_sensor = parametros.get('nombre_sensor', 'SENSOR')
    sensor = parametros.get('sensor', 'desp_a')
    fecha_inicial = parametros.get('fecha_inicial', None)
    fecha_final = parametros.get('fecha_final', None)
    total_camp = parametros.get('total_camp', 30)
    ultimas_camp = parametros.get('ultimas_camp', 30)
    cadencia_dias = parametros.get('cadencia_dias', 30)
    color_scheme = parametros.get('color_scheme', 'monocromo')
    escala_desplazamiento = parametros.get('escala_desplazamiento', 'manual')
    escala_incremento = parametros.get('escala_incremento', 'manual')
    valor_positivo_desplazamiento = parametros.get('valor_positivo_desplazamiento', 20)
    valor_negativo_desplazamiento = parametros.get('valor_negativo_desplazamiento', -20)
    valor_positivo_incremento = parametros.get('valor_positivo_incremento', 1)
    valor_negativo_incremento = parametros.get('valor_negativo_incremento', -1)
    eje = parametros.get('eje', 'cota_abs')
    orden = parametros.get('orden', True)
    ancho_cm = parametros.get('ancho_cm', 21)
    alto_cm = parametros.get('alto_cm', 29.7)
    dpi = parametros.get('dpi', 100)
    mostrar_leyenda = parametros.get('mostrar_leyenda', True)
    incluir_todos_umbrales = parametros.get('incluir_todos_umbrales', False)
    mostrar_titulo = parametros.get('mostrar_titulo', True)  # Añadir esta línea
    etiqueta_eje_x = parametros.get('etiqueta_eje_x', "")  # También podemos añadir esta

    # PASO 2: Calcular dimensiones en pulgadas para matplotlib (1 pulgada = 2.54 cm)
    ancho_pulgadas = ancho_cm / 2.54
    alto_pulgadas = alto_cm / 2.54

    # PASO 3: Calcular las fechas seleccionadas en base a los parámetros
    fechas_seleccionadas = calcular_fechas_seleccionadas(
        data,
        fecha_inicial,
        fecha_final,
        total_camp,
        ultimas_camp,
        cadencia_dias
    )

    # PASO 4: Determinar la última fecha activa como fecha_slider por defecto
    fecha_slider = determinar_fecha_slider(data, fechas_seleccionadas)

    # PASO 5: Generar información de colores para cada fecha
    fechas_colores = generar_info_colores(fechas_seleccionadas, color_scheme)

    # PASO 6: Preparar diccionario de umbrales (leyenda_umbrales)
    leyenda_umbrales = obtener_leyenda_umbrales(data)

    # PASO 7: Configurar el gráfico
    fig, ax = plt.subplots(figsize=(ancho_pulgadas, alto_pulgadas))

    # PASO 8: Procesar y graficar las series no seleccionadas
    for fecha in fechas_seleccionadas:
        if fecha in data and "calc" in data[fecha] and fecha != fecha_slider:
            # Obtener color y datos
            color = obtener_color_para_fecha(fecha, fechas_colores)
            datos = extraer_datos_fecha(fecha, data, eje)
            if not datos:
                continue

            # Definir parámetros para series no seleccionadas
            grosor = 1.5
            opacidad = 0.7

            # Obtener los datos según el tipo de gráfico
            if sensor == "desp_a":
                x_data = datos['desp_a']
                titulo = "Desplazamiento A"
            elif sensor == "desp_b":
                x_data = datos['desp_b']
                titulo = "Desplazamiento B"
            elif sensor == "incr_dev_abs_a":
                x_data = datos['incr_dev_abs_a']
                titulo = "Incremental A"
            elif sensor == "incr_dev_abs_b":
                x_data = datos['incr_dev_abs_b']
                titulo = "Incremental B"
            elif sensor == "checksum_a":
                x_data = datos['checksum_a']
                titulo = "Checksum A"
            elif sensor == "checksum_b":
                x_data = datos['checksum_b']
                titulo = "Checksum B"
            elif sensor == "desp_total":
                x_data = datos['desp_total']
                titulo = "Desplazamiento Total"

            # Añadir la serie al gráfico
            ax.plot(x_data, datos['eje_Y'], color=color, linewidth=grosor, alpha=opacidad, label=f"{fecha}")

    # PASO 9: Procesar y graficar la serie seleccionada (encima)
    if fecha_slider in fechas_seleccionadas and fecha_slider in data and "calc" in data[fecha_slider]:
        datos = extraer_datos_fecha(fecha_slider, data, eje)
        if datos:
            # Parámetros para la serie seleccionada
            color = 'darkblue'
            grosor = 3
            opacidad = 1.0

            # Obtener los datos según el tipo de gráfico
            if sensor == "desp_a":
                x_data = datos['desp_a']
            elif sensor == "desp_b":
                x_data = datos['desp_b']
            elif sensor == "incr_dev_abs_a":
                x_data = datos['incr_dev_abs_a']
            elif sensor == "incr_dev_abs_b":
                x_data = datos['incr_dev_abs_b']
            elif sensor == "checksum_a":
                x_data = datos['checksum_a']
            elif sensor == "checksum_b":
                x_data = datos['checksum_b']
            elif sensor == "desp_total":
                x_data = datos['desp_total']

            # Añadir la serie seleccionada
            ax.plot(x_data, datos['eje_Y'], color=color, linewidth=grosor, alpha=opacidad, label=f"{fecha_slider}")

    # PASO 10: Añadir los umbrales si están disponibles
    agregar_umbrales(ax, data, leyenda_umbrales, eje, sensor, fecha_slider)

    # PASO 11
    etiqueta_eje_x = parametros.get('etiqueta_eje_x', "Desplazamiento (mm)")  # Por defecto mm
    configurar_ejes(
        ax,
        sensor,
        escala_desplazamiento,
        escala_incremento,
        valor_positivo_desplazamiento,
        valor_negativo_desplazamiento,
        valor_positivo_incremento,
        valor_negativo_incremento,
        eje,
        orden,
        titulo,
        etiqueta_eje_x
    )

    # PASO 12-13: Manejo de leyendas y ajustes finales
    # Asignar títulos según configuración
    if mostrar_titulo:
        plt.suptitle(f"Inclinómetro: {nombre_sensor}", fontsize=14, y=0.99)
        plt.title(titulo, fontsize=12)

    # Asignar etiqueta al eje X si está configurada
    if etiqueta_eje_x:
        ax.set_xlabel(etiqueta_eje_x)

    # Manejo de leyendas
    if mostrar_leyenda:
        try:
            # Obtener todos los elementos existentes de la leyenda
            handles, labels = ax.get_legend_handles_labels()

            # Evitar error si no hay leyenda previa
            if ax.get_legend():
                ax.get_legend().remove()

            # Continuar solo si hay elementos de leyenda
            if handles and labels:
                # Dividir entre fechas y umbrales
                umbral_items = [(h, l) for h, l in zip(handles, labels)
                                if isinstance(h, plt.Line2D) and h.get_linestyle() == '--']
                fecha_items = [(h, l) for h, l in zip(handles, labels)
                               if not (isinstance(h, plt.Line2D) and h.get_linestyle() == '--')]

                # Ordenar fechas de más antigua a más reciente
                fecha_items_ordenados = []
                for h, l in fecha_items:
                    try:
                        # Intentar extraer la fecha del label
                        fecha_str = l.split(' ')[0]
                        fecha_dt = datetime.fromisoformat(fecha_str)
                        fecha_items_ordenados.append((fecha_dt, h, l))
                    except (ValueError, IndexError):
                        # Si falla, mantener el item sin ordenar
                        fecha_items_ordenados.append((datetime.min, h, l))

                # Ordenar por fecha
                fecha_items_ordenados.sort(key=lambda x: x[0])
                fecha_handles = [item[1] for item in fecha_items_ordenados]
                fecha_labels = [item[2] for item in fecha_items_ordenados]

                # Extraer handles y labels de umbrales
                umbral_handles = [item[0] for item in umbral_items]
                umbral_labels = [item[1] for item in umbral_items]

                # Crear la primera leyenda (campañas) en el lateral derecho, FUERA del gráfico
                if fecha_handles:
                    legend1 = ax.legend(fecha_handles, fecha_labels,
                                        loc='upper left',  # Cambiado a 'upper left'
                                        bbox_to_anchor=(1.05, 1.0),  # Posicionado justo a la derecha del gráfico
                                        title="Campañas",
                                        frameon=True,  # Marco visible
                                        fontsize='small')  # Texto más pequeño
                    ax.add_artist(legend1)

                # Crear la segunda leyenda (umbrales) debajo de la primera
                if umbral_handles:
                    legend2 = ax.legend(umbral_handles, umbral_labels,
                                        loc='lower right',  # En el gráfico
                                        title="Umbrales")

                # IMPORTANTE: Ajustar las dimensiones de la figura para dar espacio a la leyenda
                plt.subplots_adjust(right=0.75)  # Reduce el ancho del gráfico al 75% para dejar espacio a la leyenda
        except Exception as e:
            print(f"Error al crear leyendas: {str(e)}")
            # Si algo falla, intentamos al menos mostrar una leyenda básica
            ax.legend(loc='best')
    else:
        # Si no queremos mostrar leyendas, eliminar cualquier leyenda existente
        if ax.get_legend():
            ax.get_legend().remove()

    # PASO 14: Guardar como imagen

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=dpi,
                bbox_inches='tight',  # Asegura que se incluye todo el contenido
                pad_inches=0.5)  # Añade un poco de padding alrededor
    buffer.seek(0)

    plt.close(fig)  # Cerrar la figura explícitamente

    # PASO 15: Codificar en base64 para enviar a través de HTTP
    imagen_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)

    return f"data:image/png;base64,{imagen_base64}"

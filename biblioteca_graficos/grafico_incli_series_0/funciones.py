# funciones del gráfico

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.ticker import AutoMinorLocator
from datetime import datetime, timedelta
import re


def calcular_fechas_seleccionadas(data, fecha_inicial, fecha_final, total_camp, ultimas_camp, cadencia_dias):
    """
    Calcula las fechas a mostrar basadas en los parámetros.

    Args:
        data (dict): Diccionario con los datos del tubo.
        fecha_inicial (str): Fecha de inicio en formato ISO.
        fecha_final (str): Fecha final en formato ISO.
        total_camp (int): Total de campañas a mostrar.
        ultimas_camp (int): Número de últimas campañas a mostrar.
        cadencia_dias (int): Intervalo en días entre campañas.

    Returns:
        list: Lista de fechas seleccionadas.
    """
    # Obtener todas las fechas disponibles (excluyendo claves especiales)
    fechas = [fecha for fecha in data.keys() if fecha != "info" and fecha != "umbrales"]

    # Convertir fechas a objetos datetime y ordenar
    fechas_dt = sorted([datetime.fromisoformat(fecha) for fecha in fechas])

    # Si se proporcionaron fechas de inicio y fin, filtrar por rango
    if fecha_inicial and fecha_final:
        fecha_inicio_dt = datetime.fromisoformat(fecha_inicial)
        fecha_fin_dt = datetime.fromisoformat(fecha_final)
        fechas_dt = [fecha for fecha in fechas_dt if fecha_inicio_dt <= fecha <= fecha_fin_dt]

    # Convertir de nuevo a formato ISO y ordenar de más reciente a más antigua
    fechas = [fecha.isoformat() for fecha in reversed(fechas_dt)]

    # Seleccionar fechas basadas en parámetros
    fechas_seleccionadas = []

    # Añadir las últimas campañas
    if ultimas_camp > 0 and len(fechas) > 0:
        fechas_seleccionadas.extend(fechas[:min(ultimas_camp, len(fechas))])

    # Añadir campañas adicionales basadas en cadencia
    if cadencia_dias > 0 and len(fechas_seleccionadas) < total_camp and len(fechas) > ultimas_camp:
        ultima_fecha = datetime.fromisoformat(fechas_seleccionadas[-1])

        for fecha in fechas[ultimas_camp:]:
            fecha_actual = datetime.fromisoformat(fecha)
            diferencia_dias = (ultima_fecha - fecha_actual).days

            if diferencia_dias >= cadencia_dias:
                fechas_seleccionadas.append(fecha)
                ultima_fecha = fecha_actual

            if len(fechas_seleccionadas) >= total_camp:
                break

    # Limitar al número total especificado
    return fechas_seleccionadas[:total_camp]


def determinar_fecha_slider(data, fechas_seleccionadas):
    """
    Determina la fecha a destacar (por defecto la última fecha activa).

    Args:
        data (dict): Diccionario con los datos del tubo.
        fechas_seleccionadas (list): Lista de fechas seleccionadas.

    Returns:
        str: Fecha a destacar.
    """
    # Si no hay fechas seleccionadas, devolver None
    if not fechas_seleccionadas:
        return None

    # Filtrar fechas que tienen campaign_info.active == True
    fechas_activas = []
    for fecha in fechas_seleccionadas:
        if fecha in data and isinstance(data[fecha], dict):
            # Si tiene la estructura esperada con campaign_info.active
            if 'campaign_info' in data[fecha] and data[fecha]['campaign_info'].get('active', False):
                fechas_activas.append(fecha)

    # Si hay fechas activas, devolver la más reciente
    if fechas_activas:
        return fechas_activas[0]  # Asumiendo que fechas_seleccionadas está ordenada de más reciente a más antigua

    # Si no hay fechas activas, devolver la primera fecha seleccionada (la más reciente)
    return fechas_seleccionadas[0]


def get_color_for_index(index, color_scheme="monocromo", total_colors=10):
    """
    Devuelve un color para un índice determinado según el esquema de colores proporcionado.

    Args:
        index (int): Índice del color (0-based).
        color_scheme (str): Esquema de colores a usar ("monocromo" o "multicromo").
        total_colors (int): Número total de colores en la escala.

    Returns:
        str: Color en formato hexadecimal.
    """
    if color_scheme == "monocromo":
        # Degradado de azul (de claro a oscuro)
        cmap = plt.cm.Blues
        # Normalizar el índice al rango 0.2-0.9 para evitar colores muy claros o muy oscuros
        norm_index = 0.2 + 0.7 * (1 - index / (total_colors - 1 if total_colors > 1 else 1))
        color_rgb = cmap(norm_index)[:3]  # Usar solo RGB, no Alpha
        # Convertir RGB a formato hexadecimal
        color_hex = "#{:02x}{:02x}{:02x}".format(
            int(color_rgb[0] * 255),
            int(color_rgb[1] * 255),
            int(color_rgb[2] * 255)
        )
        return color_hex
    else:  # "multicromo"
        # Usar colores predefinidos para esquema multicolor
        colores_base = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]
        return colores_base[index % len(colores_base)]


def generar_info_colores(fechas_seleccionadas, color_scheme):
    """
    Genera información de colores para cada fecha.

    Args:
        fechas_seleccionadas (list): Lista de fechas seleccionadas.
        color_scheme (str): Esquema de colores a usar.

    Returns:
        list: Lista de diccionarios con información de fechas y colores.
    """
    total_fechas = len(fechas_seleccionadas)
    fechas_colores = []

    for i, fecha in enumerate(fechas_seleccionadas):
        color_hex = get_color_for_index(i, color_scheme, total_fechas)

        fechas_colores.append({
            'value': fecha,
            'label': fecha,
            'style': {'color': color_hex}
        })

    return fechas_colores


def obtener_leyenda_umbrales(data):
    """
    Obtiene el diccionario de leyenda de umbrales.

    Args:
        data (dict): Diccionario con datos del tubo.

    Returns:
        dict: Diccionario con umbrales y sus colores asociados.
    """
    leyenda_umbrales = {}

    # Verificar si existen umbrales
    if 'umbrales' not in data or 'deformadas' not in data['umbrales']:
        return leyenda_umbrales

    # Obtener las deformadas
    deformadas = list(data['umbrales']['deformadas'].keys())

    # Asignar colores predeterminados a cada umbral
    colores_predeterminados = {
        'umbral1_a': 'verde',
        'umbral2_a': 'amarillo',
        'umbral3_a': 'naranja',
        'umbral4_a': 'rojo',
        'umbral1_b': 'verde',
        'umbral2_b': 'amarillo',
        'umbral3_b': 'naranja',
        'umbral4_b': 'rojo'
    }

    # Asignar colores a cada deformada
    for deformada in deformadas:
        if deformada in colores_predeterminados:
            leyenda_umbrales[deformada] = colores_predeterminados[deformada]
        else:
            # Si no hay color predeterminado, asignar uno genérico
            leyenda_umbrales[deformada] = 'gray'

    return leyenda_umbrales


def obtener_color_para_fecha(fecha, fechas_colores):
    """
    Obtiene el color asociado a una fecha desde el diccionario de colores.

    Args:
        fecha (str): Fecha para la que se busca el color.
        fechas_colores (list): Lista de diccionarios con información de colores por fecha.

    Returns:
        str: Color en formato hexadecimal o nombre.
    """
    item_correspondiente = next((item for item in fechas_colores if item['value'] == fecha), None)
    if item_correspondiente:
        return item_correspondiente['style']['color']
    return 'gray'  # Color por defecto si no se encuentra


def extraer_datos_fecha(fecha, data, eje):
    """
    Extrae y procesa los datos de cálculo para una fecha específica.

    Args:
        fecha (str): Fecha de la que extraer datos.
        data (dict): Diccionario con datos del tubo.
        eje (str): Tipo de eje (index, cota_abs, depth).

    Returns:
        dict: Diccionario con los datos extraídos o None si no hay datos.
    """
    if fecha not in data or "calc" not in data[fecha]:
        return None

    calc_data = data[fecha]["calc"]

    # Si el eje es "depth", construimos la lista según la lógica especificada
    # esto es debido a que puede haber recrecimientos del tubo, "depth" sólo vale dentro de las campañas de la misma ref
    if eje == "depth":
        # Extraer todos los valores de cota_abs
        cota_abs = [punto["cota_abs"] for punto in calc_data]

        # Calcular el paso (diferencia entre cotas consecutivas)
        paso = abs(cota_abs[1] - cota_abs[0]) if len(cota_abs) > 1 else 1.0

        # Construir la lista eje_Y como profundidades
        eje_Y = [paso * i for i in range(len(cota_abs))]
    else:
        # Si no es "depth", extraer directamente los valores del eje especificado
        eje_Y = [punto[eje] for punto in calc_data if eje in punto]

    # Crear y devolver diccionario con todos los datos extraídos
    desp_a = [punto.get("desp_a", 0) for punto in calc_data]
    desp_b = [punto.get("desp_b", 0) for punto in calc_data]
    desp_total = [((a ** 2 + b ** 2) ** 0.5) for a, b in zip(desp_a, desp_b)]
    incr_dev_abs_a = [punto.get("incr_dev_abs_a", 0) for punto in calc_data]
    incr_dev_abs_b = [punto.get("incr_dev_abs_b", 0) for punto in calc_data]
    checksum_a = [punto.get("checksum_a", 0) for punto in calc_data]
    checksum_b = [punto.get("checksum_b", 0) for punto in calc_data]

    return {
        'eje_Y': eje_Y,
        'desp_a': desp_a,
        'desp_b': desp_b,
        'desp_total': desp_total,
        'incr_dev_abs_a': incr_dev_abs_a,
        'incr_dev_abs_b': incr_dev_abs_b,
        'checksum_a': checksum_a,
        'checksum_b': checksum_b
    }


def interpolar_def_tubo(cota_tubo, cota_umbral, def_umbral):
    """
    Interpola los valores de deformada para las cotas del tubo.

    Args:
        cota_tubo (list): Lista de cotas del tubo.
        cota_umbral (list): Lista de cotas del umbral.
        def_umbral (list): Lista de valores de deformada del umbral.

    Returns:
        list: Lista interpolada de valores de deformada.
    """
    # Crear array de valores conocidos
    x_conocidos = np.array(cota_umbral)
    y_conocidos = np.array(def_umbral)

    # Crear array de valores a interpolar
    x_interpolar = np.array(cota_tubo)

    # Interpolar valores
    y_interpolados = np.interp(x_interpolar, x_conocidos, y_conocidos)

    return y_interpolados.tolist()


def agregar_umbrales(ax, data, leyenda_umbrales, eje, sensor, fecha_slider):
    """
    Añade líneas de umbral al gráfico.

    Args:
        ax: Eje de matplotlib donde graficar.
        data (dict): Diccionario con datos del tubo.
        leyenda_umbrales (dict): Diccionario con colores para umbrales.
        eje (str): Tipo de eje vertical (index, cota_abs, depth).
        sensor (str): Tipo de sensor a graficar.
        fecha_slider (str): Fecha seleccionada.

    Returns:
        None
    """
    # Diccionario para convertir colores en español a inglés o códigos hex
    colores_ingles = {
        'verde': 'green',
        'amarillo': 'yellow',
        'naranja': 'orange',
        'rojo': 'red',
        'gris': 'gray',
        'azul': 'blue',
        'morado': 'purple'
    }

    # Verificar si existen umbrales
    if not leyenda_umbrales or 'umbrales' not in data or 'valores' not in data['umbrales']:
        return

    valores = data['umbrales']['valores']
    deformadas = list(data['umbrales'].get('deformadas', {}).keys())

    # Convertir valores a DataFrame (simulado con listas)
    df_valores = []
    for valor in valores:
        df_valores.append(valor)

    # Filtrar las deformadas según el tipo de sensor
    deformada_filtro = None
    if sensor == "desp_a":
        deformada_filtro = [d for d in deformadas if d.endswith("_a")]
    elif sensor == "desp_b":
        deformada_filtro = [d for d in deformadas if d.endswith("_b")]
    elif sensor == "desp_total":
        # Para desplazamiento total podríamos mostrar ambos umbrales
        deformada_filtro = deformadas

    # Procesar y añadir cada umbral
    if deformada_filtro and fecha_slider in data and "calc" in data[fecha_slider]:
        for deformada in deformada_filtro:
            # Obtener el color desde la leyenda
            color_espanol = leyenda_umbrales.get(deformada, "gray")

            # Convertir a color inglés o mantenerlo si es un código hexadecimal
            color = colores_ingles.get(color_espanol, color_espanol)

            # Extraer datos necesarios
            cota_umbral = [valor.get('cota_abs') for valor in df_valores]
            def_umbral = [valor.get(deformada, 0) for valor in df_valores]

            # Procesamiento según el tipo de eje
            if eje == "depth" or eje == "index":
                # Interpolar valores para el caso de index o depth
                cota_tubo = [punto["cota_abs"] for punto in data[fecha_slider]['calc']]
                eje_X = interpolar_def_tubo(cota_tubo, cota_umbral, def_umbral)

                # Seleccionar eje Y según el tipo de eje
                if eje == "depth":
                    # Calcular profundidad basada en el paso
                    paso = abs(cota_tubo[1] - cota_tubo[0]) if len(cota_tubo) > 1 else 1.0
                    eje_Y = [paso * i for i in range(len(cota_tubo))]
                elif eje == "index":
                    # Usar la lista de índice
                    eje_Y = [punto["index"] for punto in data[fecha_slider]['calc']]
            else:  # caso de "cota_abs"
                eje_X = def_umbral
                eje_Y = cota_umbral

            # Añadir la línea de umbral
            ax.plot(eje_X, eje_Y, color=color, linewidth=2, linestyle='--', label=deformada)


def configurar_ejes(ax, sensor, escala_desplazamiento, escala_incremento, valor_positivo_desplazamiento,
                    valor_negativo_desplazamiento, valor_positivo_incremento, valor_negativo_incremento,
                    eje, orden, titulo):
    """
    Configura los ejes, límites y formato del gráfico.

    Args:
        ax: Eje de matplotlib donde graficar.
        sensor (str): Tipo de sensor a graficar.
        escala_desplazamiento (str): Tipo de escala para desplazamientos.
        escala_incremento (str): Tipo de escala para incrementos.
        valor_positivo_desplazamiento (float): Límite superior para desplazamiento.
        valor_negativo_desplazamiento (float): Límite inferior para desplazamiento.
        valor_positivo_incremento (float): Valor máximo para incremento.
        valor_negativo_incremento (float): Valor mínimo para incremento.
        eje (str): Tipo de eje vertical (index, cota_abs, depth).
        orden (bool): True para orden ascendente, False para descendente.
        titulo (str): Título del gráfico.

    Returns:
        None
    """
    # Configurar límites en eje x según el tipo de sensor y escala
    if sensor in ["desp_a", "desp_b", "desp_total"] and escala_desplazamiento == "manual":
        ax.set_xlim(valor_negativo_desplazamiento, valor_positivo_desplazamiento)
    elif sensor in ["incr_dev_abs_a", "incr_dev_abs_b"] and escala_incremento == "manual":
        ax.set_xlim(valor_negativo_incremento, valor_positivo_incremento)
    elif sensor in ["checksum_a", "checksum_b"]:
        ax.set_xlim(-1, 1)

    # Configurar título del eje Y según el tipo
    if eje == "index":
        titulo_eje_y = "Índice"
    elif eje == "cota_abs":
        titulo_eje_y = "Cota (m.s.n.m.)"
    elif eje == "depth":
        titulo_eje_y = "Profundidad (m)"

    ax.set_ylabel(titulo_eje_y)

    # Invertir eje Y si el orden no es ascendente
    if not orden:
        ax.invert_yaxis()

    # Configurar estilo del gráfico similar a Plotly
    # Configurar rejilla
    ax.grid(True, linestyle='--', alpha=0.7, color='lightgray')

    # Añadir línea vertical en x=0
    ax.axvline(x=0, color='darkgray', linestyle='-', linewidth=1)

    # Configurar borde y fondo
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('darkgray')
    ax.spines['bottom'].set_color('darkgray')
    ax.set_facecolor('white')

    # Añadir ticks menores
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())

    # Mostrar leyenda con transparencia y borde
    ax.legend(loc='upper right', framealpha=0.7, edgecolor='lightgray')
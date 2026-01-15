# grafico_incli_0.py
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
import numpy as np
from datetime import datetime
from matplotlib.ticker import AutoMinorLocator
import io
import base64

# Importamos funciones necesarias (ajusta las rutas según tu estructura de proyecto)
from utils.funciones_comunes import get_color_for_index
from utils.diccionarios import colores_ingles


def obtener_fecha_desde_slider(slider_value):
    """
    Obtiene la fecha seleccionada desde el valor del slider.
    En esta implementación se espera recibir directamente la fecha ya calculada.

    Args:
        slider_value (str): Valor de la fecha seleccionada en formato string

    Returns:
        str: La misma fecha (se mantiene para compatibilidad con la estructura original)
    """
    return slider_value


def obtener_color_para_fecha(fecha, fechas_colores):
    """
    Obtiene el color para una fecha específica desde la lista de colores.

    Args:
        fecha (str): Fecha para la que se busca el color
        fechas_colores (list): Lista de diccionarios con información de colores por fecha

    Returns:
        str: Color en formato hex o nombre
    """
    # Buscar la fecha en la lista de diccionarios
    for item in fechas_colores:
        if item.get('value') == fecha and 'style' in item:
            return item['style'].get('color', 'blue')
    return 'blue'  # Color por defecto


def extraer_datos_fecha(fecha, data, eje):
    """
    Extrae los datos específicos de una fecha del conjunto completo.

    Args:
        fecha (str): Fecha de la que extraer datos
        data (dict): Datos completos del tubo
        eje (str): Tipo de eje a utilizar ('index', 'cota_abs', 'depth')

    Returns:
        dict: Diccionario con los datos extraídos
    """
    if fecha not in data or "calc" not in data[fecha]:
        return None

    calc_data = data[fecha]["calc"]

    # Extraer datos según el eje seleccionado
    eje_Y = [punto[eje] for punto in calc_data if eje in punto]

    # Extraer diferentes tipos de datos
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
        cota_tubo (list): Lista de cotas del tubo
        cota_umbral (list): Lista de cotas del umbral
        def_umbral (list): Lista de valores de deformada del umbral

    Returns:
        list: Lista interpolada de valores de deformada
    """
    # Crear array de valores conocidos
    x_conocidos = np.array(cota_umbral)
    y_conocidos = np.array(def_umbral)

    # Crear array de valores a interpolar
    x_interpolar = np.array(cota_tubo)

    # Interpolar valores
    y_interpolados = np.interp(x_interpolar, x_conocidos, y_conocidos)

    return y_interpolados.tolist()


def grafico_incli_0(fechas_seleccionadas, fechas_colores, fecha_slider, data,
                    alto_graficos=800, color_scheme="monocromo",
                    escala_desplazamiento="manual", escala_incremento="manual",
                    valor_positivo_desplazamiento=20, valor_negativo_desplazamiento=-20,
                    valor_positivo_incremento=1, valor_negativo_incremento=-1,
                    leyenda_umbrales=None, eje="cota_abs", orden=True, tipo_grafico="desp_a"):
    """
    Genera un gráfico de inclinometría usando matplotlib, similar a los generados con plotly.

    Args:
        fechas_seleccionadas (list): Lista de fechas seleccionadas para mostrar
        fechas_colores (list): Información de colores para cada fecha
        fecha_slider (str): Fecha seleccionada en el slider
        data (dict): Datos completos del tubo
        alto_graficos (int): Altura del gráfico en píxeles
        color_scheme (str): Esquema de colores ("monocromo" o "multicromo")
        escala_desplazamiento (str): Tipo de escala para gráficos de desplazamiento
        escala_incremento (str): Tipo de escala para gráficos incrementales
        valor_positivo_desplazamiento (float): Valor máximo para escala de desplazamiento
        valor_negativo_desplazamiento (float): Valor mínimo para escala de desplazamiento
        valor_positivo_incremento (float): Valor máximo para escala incremental
        valor_negativo_incremento (float): Valor mínimo para escala incremental
        leyenda_umbrales (dict): Datos de configuración de colores para umbrales
        eje (str): Unidades del eje vertical ("index", "cota_abs", "depth")
        orden (bool): Orden ascendente (True) o descendente (False)
        tipo_grafico (str): Tipo de gráfico a generar ("desp_a", "desp_b", "incr_dev_abs_a", etc.)

    Returns:
        bytes: Imagen del gráfico en formato PNG codificada en base64
    """
    # PASO 1: Configurar el gráfico
    fig, ax = plt.subplots(figsize=(10, alto_graficos / 100))  # Convertir píxeles a pulgadas aproximadamente

    # PASO 2: Procesar y graficar las series no seleccionadas
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
            if tipo_grafico == "desp_a":
                x_data = datos['desp_a']
                titulo = "Desplazamiento A"
            elif tipo_grafico == "desp_b":
                x_data = datos['desp_b']
                titulo = "Desplazamiento B"
            elif tipo_grafico == "incr_dev_abs_a":
                x_data = datos['incr_dev_abs_a']
                titulo = "Incremental A"
            elif tipo_grafico == "incr_dev_abs_b":
                x_data = datos['incr_dev_abs_b']
                titulo = "Incremental B"
            elif tipo_grafico == "checksum_a":
                x_data = datos['checksum_a']
                titulo = "Checksum A"
            elif tipo_grafico == "checksum_b":
                x_data = datos['checksum_b']
                titulo = "Checksum B"
            elif tipo_grafico == "desp_total":
                x_data = datos['desp_total']
                titulo = "Desplazamiento Total"

            # Añadir la serie al gráfico
            ax.plot(x_data, datos['eje_Y'], color=color, linewidth=grosor, alpha=opacidad, label=f"{fecha}")

    # PASO 3: Procesar y graficar la serie seleccionada (por encima)
    if fecha_slider in fechas_seleccionadas and fecha_slider in data and "calc" in data[fecha_slider]:
        datos = extraer_datos_fecha(fecha_slider, data, eje)
        if datos:
            # Parámetros para la serie seleccionada
            color = 'darkblue'
            grosor = 3
            opacidad = 1.0

            # Obtener los datos según el tipo de gráfico
            if tipo_grafico == "desp_a":
                x_data = datos['desp_a']
            elif tipo_grafico == "desp_b":
                x_data = datos['desp_b']
            elif tipo_grafico == "incr_dev_abs_a":
                x_data = datos['incr_dev_abs_a']
            elif tipo_grafico == "incr_dev_abs_b":
                x_data = datos['incr_dev_abs_b']
            elif tipo_grafico == "checksum_a":
                x_data = datos['checksum_a']
            elif tipo_grafico == "checksum_b":
                x_data = datos['checksum_b']
            elif tipo_grafico == "desp_total":
                x_data = datos['desp_total']

            # Añadir la serie seleccionada
            ax.plot(x_data, datos['eje_Y'], color=color, linewidth=grosor, alpha=opacidad, label=f"{fecha_slider}")

    # PASO 4: Añadir los umbrales si están disponibles
    if leyenda_umbrales and 'umbrales' in data:
        valores = data['umbrales'].get('valores', [])
        deformadas = list(data['umbrales'].get('deformadas', {}).keys())

        # Convertir valores a DataFrame para facilitar el procesamiento
        df = pd.DataFrame(valores)

        # Filtrar las deformadas según el tipo de gráfico
        deformada_filtro = None
        if tipo_grafico == "desp_a":
            deformada_filtro = [d for d in deformadas if d.endswith("_a")]
        elif tipo_grafico == "desp_b":
            deformada_filtro = [d for d in deformadas if d.endswith("_b")]

        # Procesar y añadir cada umbral
        if deformada_filtro:
            for deformada in deformada_filtro:
                # Obtener el color desde la leyenda
                color_espanol = leyenda_umbrales.get(deformada, "Ninguno")
                if color_espanol == "Ninguno":
                    continue

                # Convertir a color inglés o mantener si es hexadecimal
                color = colores_ingles.get(color_espanol, color_espanol)

                # Procesar los datos según el eje seleccionado
                if eje == "depth" or eje == "index":
                    # Interpolar valores para el caso de index o depth
                    cota_tubo = [punto["cota_abs"] for punto in data[fecha_slider]['calc']]
                    cota_umbral = df['cota_abs'].tolist()
                    def_umbral = df[deformada].tolist()
                    eje_X = interpolar_def_tubo(cota_tubo, cota_umbral, def_umbral)
                else:
                    # Caso de "cota_abs"
                    eje_X = df[deformada].tolist()

                # Seleccionar eje Y según el tipo de eje
                if eje == "depth":
                    # Calcular profundidad basada en el paso
                    paso = abs(cota_tubo[1] - cota_tubo[0])
                    eje_Y = [paso * i for i in range(len(cota_tubo))]
                elif eje == "index":
                    # Usar la lista de índice
                    eje_Y = [punto["index"] for punto in data[fecha_slider]['calc']]
                elif eje == "cota_abs":
                    eje_Y = df['cota_abs'].tolist()

                # Añadir la traza del umbral
                ax.plot(eje_X, eje_Y, color=color, linewidth=2, linestyle='--', label=deformada)

    # PASO 5: Configurar los ejes y límites
    # Configurar límites en eje x según el tipo de gráfico y escala
    if tipo_grafico in ["desp_a", "desp_b", "desp_total"] and escala_desplazamiento == "manual":
        ax.set_xlim(valor_negativo_desplazamiento, valor_positivo_desplazamiento)
    elif tipo_grafico in ["incr_dev_abs_a", "incr_dev_abs_b"] and escala_incremento == "manual":
        ax.set_xlim(valor_negativo_incremento, valor_positivo_incremento)
    elif tipo_grafico in ["checksum_a", "checksum_b"]:
        ax.set_xlim(-1, 1)

    # Configurar título del eje Y según el tipo de eje
    if eje == "index":
        titulo_eje_y = "Índice"
    elif eje == "cota_abs":
        titulo_eje_y = "Cota (m.s.n.m.)"
    elif eje == "depth":
        titulo_eje_y = "Profundidad (m)"

    ax.set_ylabel(titulo_eje_y)
    ax.set_title(titulo)

    # Invertir eje Y si el orden no es ascendente
    if not orden:
        ax.invert_yaxis()

    # PASO 6: Configurar estilo del gráfico similar a Plotly
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

    # PASO 7: Configurar leyenda
    # Mostrar leyenda con transparencia y borde
    ax.legend(loc='upper right', framealpha=0.7, edgecolor='lightgray')

    # PASO 8: Ajustar el diseño y convertir a imagen
    plt.tight_layout()

    # Guardar como imagen en memoria
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)

    # Codificar en base64 para enviar a través de HTTP
    imagen_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)

    return f"data:image/png;base64,{imagen_base64}"
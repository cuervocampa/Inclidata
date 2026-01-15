# grafico_incli_series_0.py (versión con soporte SVG)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
import base64

# Importar funciones necesarias
from funciones import (
    calcular_fechas_seleccionadas,
    determinar_fecha_slider,
    generar_info_colores,
    obtener_color_para_fecha
)


def grafico_incli_series_0(data, parametros):
    """
    Genera una imagen que solo contiene la leyenda de fechas para un gráfico de inclinometría.
    Soporta formatos PNG y SVG.

    Args:
        data (dict): Diccionario con todos los datos del tubo, incluyendo campañas.
        parametros (dict): Diccionario con parámetros de configuración.
            - fecha_inicial (str): Fecha de inicio del rango a considerar (formato ISO).
            - fecha_final (str): Fecha final del rango a considerar (formato ISO).
            - total_camp (int): Total de campañas a mostrar.
            - ultimas_camp (int): Número de últimas campañas a mostrar.
            - cadencia_dias (int): Intervalo en días entre campañas.
            - color_scheme (str): Esquema de colores ("monocromo" o "multicromo").
            - ancho_cm (float): Ancho de la leyenda en centímetros.
            - alto_cm (float): Alto de la leyenda en centímetros.
            - dpi (int): Resolución de la imagen en puntos por pulgada.
            - formato (str): Formato de salida ('png' o 'svg').

    Returns:
        str: Imagen de la leyenda en formato PNG o SVG codificada en base64 (data URL).
    """
    # PASO 1: Extraer parámetros con valores por defecto
    fecha_inicial = parametros.get('fecha_inicial', None)
    fecha_final = parametros.get('fecha_final', None)
    total_camp = parametros.get('total_camp', 30)
    ultimas_camp = parametros.get('ultimas_camp', 30)
    cadencia_dias = parametros.get('cadencia_dias', 30)
    color_scheme = parametros.get('color_scheme', 'monocromo')
    ancho_cm = parametros.get('ancho_cm', 10)  # Ancho predeterminado para leyenda
    alto_cm = parametros.get('alto_cm', 15)  # Alto predeterminado para leyenda
    dpi = parametros.get('dpi', 100)
    formato = parametros.get('formato', 'png')  # ← Nuevo parámetro

    # PASO 2: Calcular dimensiones en pulgadas para matplotlib
    ancho_pulgadas = ancho_cm / 2.54
    alto_pulgadas = alto_cm / 2.54

    # PASO 3: Calcular las fechas seleccionadas
    fechas_seleccionadas = calcular_fechas_seleccionadas(
        data,
        fecha_inicial,
        fecha_final,
        total_camp,
        ultimas_camp,
        cadencia_dias
    )

    # PASO 4: Determinar la fecha destacada (slider)
    fecha_slider = determinar_fecha_slider(data, fechas_seleccionadas)

    # PASO 5: Generar información de colores para cada fecha
    fechas_colores = generar_info_colores(fechas_seleccionadas, color_scheme)

    # PASO 6: Crear figura para la leyenda
    fig = plt.figure(figsize=(ancho_pulgadas, alto_pulgadas))
    ax = fig.add_axes([0, 0, 1, 1])  # [left, bottom, width, height] de 0 a 1
    ax.set_axis_off()  # Ocultar ejes

    # PASO 7: Crear los elementos de la leyenda manualmente
    handles = []

    # Primero agregar la fecha destacada (slider) si existe
    if fecha_slider and fecha_slider in fechas_seleccionadas:
        # Para la fecha destacada usamos un estilo diferente
        patch = mpatches.Patch(color='darkblue', label=f"{fecha_slider} (seleccionada)")
        handles.append(patch)

    # Luego agregar el resto de fechas
    for fecha in fechas_seleccionadas:
        if fecha != fecha_slider:
            color = obtener_color_para_fecha(fecha, fechas_colores)
            patch = mpatches.Patch(color=color, label=fecha)
            handles.append(patch)

    # PASO 8: Crear la leyenda directamente en la figura (no en los axes)
    legend = fig.legend(
        handles=handles,
        loc='upper left',
        fontsize=8,  # Tamaño de letra en puntos
        frameon=True,
        framealpha=0.9,
        edgecolor='lightgray',
        title="Fechas de campaña",
        bbox_to_anchor=(0, 0, 1, 1),  # Usar toda la figura
        bbox_transform=fig.transFigure,  # Importante: usar coordenadas de figura
        mode='expand',
        borderaxespad=0
    )
    # Ajustar el título de la leyenda al mismo tamaño
    legend.get_title().set_fontsize(8)

    # PASO 9: Guardar como imagen en memoria en el formato especificado
    buffer = io.BytesIO()

    # Usar el formato especificado
    if formato.lower() == 'svg':
        plt.savefig(buffer, format='svg', pad_inches=0, bbox_inches=None)
    else:  # Por defecto, usar PNG
        plt.savefig(buffer, format='png', dpi=dpi, pad_inches=0, bbox_inches=None)

    buffer.seek(0)

    # PASO 10: Codificar en base64
    imagen_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)

    # Devolver el data URL con el tipo MIME correcto
    if formato.lower() == 'svg':
        return f"data:image/svg+xml;base64,{imagen_base64}"
    else:
        return f"data:image/png;base64,{imagen_base64}"
# grafico_incli_leyenda_0.py (versión con soporte SVG)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
import base64

# Importar función necesaria
from funciones import obtener_leyenda_umbrales


def grafico_incli_leyenda_0(data, parametros):
    """
    Genera una imagen que solo contiene la leyenda de umbrales para un gráfico de inclinometría.
    Soporta formatos PNG y SVG.
    """
    # PASO 1: Extraer parámetros con valores por defecto
    sensor = parametros.get('sensor', 'desp_a')
    ancho_cm = parametros.get('ancho_cm', 10)
    alto_cm = parametros.get('alto_cm', 10)
    dpi = parametros.get('dpi', 100)
    formato = parametros.get('formato', 'png')  # ← Nuevo parámetro

    # PASO 2: Calcular dimensiones en pulgadas para matplotlib
    ancho_pulgadas = ancho_cm / 2.54
    alto_pulgadas = alto_cm / 2.54

    # PASO 3: Obtener la leyenda de umbrales
    leyenda_umbrales = obtener_leyenda_umbrales(data)

    # PASO 4: Crear figura con tamaño exacto y sin márgenes
    fig = plt.figure(figsize=(ancho_pulgadas, alto_pulgadas))

    # IMPORTANTE: Esta es la clave - crear un solo Axes que ocupe toda la figura
    ax = fig.add_axes([0, 0, 1, 1])  # [left, bottom, width, height] de 0 a 1
    ax.set_axis_off()  # Ocultar ejes

    # PASO 5: Definir mapeo de colores
    colores_ingles = {
        'verde': 'green',
        'amarillo': 'yellow',
        'naranja': 'orange',
        'rojo': 'red',
        'gris': 'gray',
        'azul': 'blue',
        'morado': 'purple'
    }

    # PASO 6: Filtrar las deformadas según el tipo de sensor
    deformadas_filtradas = []
    if sensor == "desp_a":
        deformadas_filtradas = [d for d in leyenda_umbrales.keys() if d.endswith("_a")]
    elif sensor == "desp_b":
        deformadas_filtradas = [d for d in leyenda_umbrales.keys() if d.endswith("_b")]
    elif sensor == "desp_total":
        deformadas_filtradas = list(leyenda_umbrales.keys())

    # PASO 7: Crear los elementos de la leyenda manualmente
    handles = []
    umbral_order = {
        'umbral1': 1,
        'umbral2': 2,
        'umbral3': 3,
        'umbral4': 4
    }

    deformadas_ordenadas = sorted(deformadas_filtradas,
                                  key=lambda x: umbral_order.get(x.split('_')[0], 999))

    for deformada in deformadas_ordenadas:
        color_espanol = leyenda_umbrales.get(deformada, "gris")
        color = colores_ingles.get(color_espanol, color_espanol)
        umbral_numero = deformada.split('_')[0][-1]
        eje = "A" if deformada.endswith("_a") else "B"
        nombre_umbral = f"Umbral {umbral_numero} - Eje {eje}"
        patch = mpatches.Patch(color=color, label=nombre_umbral)
        handles.append(patch)

    # PASO 8: Crear la leyenda directamente en la figura
    if handles:
        # Crear la leyenda directamente en la figura
        legend = fig.legend(
            handles=handles,
            loc='upper left',
            fontsize=8,  # Tamaño de letra fijo en 8 puntos
            frameon=True,
            framealpha=0.9,
            edgecolor='lightgray',
            title="Umbrales",
            bbox_to_anchor=(0, 0, 1, 1),  # Usar todo el espacio disponible
            bbox_transform=fig.transFigure,  # Importante: usar coordenadas de figura
            ncol=1,
            mode='expand',
            borderaxespad=0,
        )

        # Ajustar el tamaño del título de la leyenda también a 8 puntos
        legend.get_title().set_fontsize(8)

        # Ajustar el tamaño de la caja de leyenda al ancho exacto
        legend._legend_box.align = "left"
        legend._legend_box.set_width(ancho_pulgadas)

        # Ajustar espaciado interno de la leyenda para mayor control
        legend._legend_box.sep = 5  # Espacio entre elementos en puntos
        legend.get_frame().set_linewidth(0.5)  # Ancho del borde
    else:
        ax.text(0.5, 0.5, "No hay umbrales disponibles para este sensor",
                ha='center', va='center', fontsize=8)

    # PASO 9: Guardar como imagen en memoria en el formato especificado
    buffer = io.BytesIO()

    # Usar el formato especificado
    if formato.lower() == 'svg':
        plt.savefig(buffer, format='svg', pad_inches=0, bbox_inches=None, transparent=True)
    else:  # Por defecto, usar PNG
        plt.savefig(buffer, format='png', dpi=dpi, pad_inches=0, bbox_inches=None, transparent=True)

    buffer.seek(0)

    # PASO 10: Codificar en base64
    imagen_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)

    # Devolver el data URL con el tipo MIME correcto
    if formato.lower() == 'svg':
        return f"data:image/svg+xml;base64,{imagen_base64}"
    else:
        return f"data:image/png;base64,{imagen_base64}"
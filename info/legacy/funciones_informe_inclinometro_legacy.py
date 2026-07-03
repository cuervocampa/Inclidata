
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import json
import base64
from pathlib import Path
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
import numpy as np

from utils.funciones_graficar import obtener_fecha_desde_slider, obtener_color_para_fecha, extraer_datos_fecha


def generar_informe_inclinometro(plantilla, datos_tubo, parametros):
    """
    Genera un informe PDF para un inclinómetro con sus gráficos correspondientes

    Args:
        plantilla: Diccionario con la estructura de la plantilla JSON
        datos_tubo: Datos del inclinómetro
        parametros: Parámetros de configuración para los gráficos

    Returns:
        bytes: El PDF generado en formato bytes
    """
    # Configuración de buffer para el PDF
    buffer = BytesIO()

    # Determinar orientación y tamaño de página
    orientacion = plantilla.get("configuracion", {}).get("orientacion", "landscape")
    if orientacion == "landscape":
        pagesize = landscape(A4)
    else:
        pagesize = A4

    # Crear canvas de ReportLab
    pdf = canvas.Canvas(buffer, pagesize=pagesize)

    # 1. Dibujar elementos de la plantilla
    dibujar_elementos_plantilla(pdf, plantilla, datos_tubo)

    # 2. Generar gráficos con matplotlib y añadirlos al PDF
    generar_y_añadir_graficos(pdf, datos_tubo, parametros)

    # 3. Finalizar el PDF
    pdf.save()
    buffer.seek(0)

    return buffer.getvalue()


def dibujar_elementos_plantilla(pdf, plantilla, datos_tubo):
    """
    Dibuja los elementos definidos en la plantilla JSON en el PDF
    """
    # Obtener información del inclinómetro para reemplazar placeholders
    info_tubo = datos_tubo.get("info", {})
    nombre_sensor = info_tubo.get("nombre_sensor", "Sin nombre")

    # Recorrer los elementos de la plantilla
    for nombre_elemento, elemento in plantilla.get("elementos", {}).items():
        tipo = elemento.get("tipo")

        if tipo == "rectangulo":
            dibujar_rectangulo(pdf, elemento)
        elif tipo == "texto":
            # Reemplazar placeholders
            if nombre_elemento == "nombre_sensor" or nombre_elemento.endswith("_sensor"):
                if "contenido" in elemento and "texto" in elemento["contenido"]:
                    elemento["contenido"]["texto"] = nombre_sensor

            dibujar_texto(pdf, elemento)
        elif tipo == "imagen":
            dibujar_imagen(pdf, elemento)
        elif tipo == "linea":
            dibujar_linea(pdf, elemento)


def dibujar_rectangulo(pdf, elemento):
    """Dibuja un rectángulo en el PDF"""
    geometria = elemento.get("geometria", {})
    estilo = elemento.get("estilo", {})

    x = geometria.get("x", 0) * cm
    y = geometria.get("y", 0) * cm
    ancho = geometria.get("ancho", 0) * cm
    alto = geometria.get("alto", 0) * cm

    # Convertir y a coordenadas ReportLab (origen en esquina inferior izquierda)
    y = pdf._pagesize[1] - y - alto

    # Configurar color de relleno
    color_relleno = estilo.get("color_relleno", "#FFFFFF")
    r, g, b = hex_a_rgb(color_relleno)
    pdf.setFillColorRGB(r, g, b)

    # Configurar color de borde
    color_borde = estilo.get("color_borde", "#000000")
    r, g, b = hex_a_rgb(color_borde)
    pdf.setStrokeColorRGB(r, g, b)

    # Dibujar rectángulo
    pdf.rect(x, y, ancho, alto, fill=True, stroke=True)


def dibujar_texto(pdf, elemento):
    """Dibuja un texto en el PDF"""
    # Implementación similar a dibujar_rectangulo pero para texto


def dibujar_imagen(pdf, elemento):
    """Dibuja una imagen en el PDF"""
    # Implementación similar para imágenes usando pdf.drawImage


def dibujar_linea(pdf, elemento):
    """Dibuja una línea en el PDF"""
    # Implementación similar para líneas usando pdf.line


def generar_y_añadir_graficos(pdf, datos_tubo, parametros):
    """
    Genera gráficos con matplotlib y los añade al PDF
    """
    # Extraer parámetros
    unidades_eje = parametros.get("unidades_eje", "cota_abs")
    orden_ascendente = parametros.get("orden_ascendente", True)
    color_scheme = parametros.get("color_scheme", "monocromo")

    # Obtener fechas ordenadas
    fechas = sorted([clave for clave in datos_tubo.keys() if clave != "info" and clave != "umbrales"],
                    key=lambda x: datetime.fromisoformat(x))

    # Filtrar fechas según los parámetros
    fechas_filtradas = aplicar_filtro_fechas(
        fechas,
        parametros.get("total_camp", 30),
        parametros.get("ultimas_camp", 30),
        parametros.get("cadencia_dias", 30)
    )

    # Crear gráficos
    buffer_graficos = []

    # 1. Gráfico de desplazamientos vs profundidad (dirección A)
    fig1 = plt.figure(figsize=(8, 6))
    ax1 = fig1.add_subplot(111)
    crear_grafico_desplazamiento(ax1, datos_tubo, fechas_filtradas, 'desp_a', unidades_eje, orden_ascendente,
                                 color_scheme)
    ax1.set_title("Desplazamiento A vs Profundidad")
    buffer_graficos.append(fig_to_buffer(fig1))
    plt.close(fig1)

    # 2. Gráfico de desplazamientos vs profundidad (dirección B)
    fig2 = plt.figure(figsize=(8, 6))
    ax2 = fig2.add_subplot(111)
    crear_grafico_desplazamiento(ax2, datos_tubo, fechas_filtradas, 'desp_b', unidades_eje, orden_ascendente,
                                 color_scheme)
    ax2.set_title("Desplazamiento B vs Profundidad")
    buffer_graficos.append(fig_to_buffer(fig2))
    plt.close(fig2)

    # 3. Gráfico de incrementos vs profundidad
    fig3 = plt.figure(figsize=(8, 6))
    ax3 = fig3.add_subplot(111)
    crear_grafico_incrementos(ax3, datos_tubo, fechas_filtradas, unidades_eje, orden_ascendente, color_scheme)
    ax3.set_title("Incrementos vs Profundidad")
    buffer_graficos.append(fig_to_buffer(fig3))
    plt.close(fig3)

    # 4. Gráfico de evolución temporal
    fig4 = plt.figure(figsize=(8, 6))
    ax4 = fig4.add_subplot(111)
    crear_grafico_temporal(ax4, datos_tubo, fechas, unidades_eje)
    ax4.set_title("Evolución Temporal")
    buffer_graficos.append(fig_to_buffer(fig4))
    plt.close(fig4)

    # Añadir gráficos al PDF
    añadir_graficos_a_pdf(pdf, buffer_graficos)


def crear_grafico_desplazamiento(ax, datos_tubo, fechas, tipo_desp, unidades_eje, orden_ascendente, color_scheme):
    """Crea un gráfico de desplazamiento vs profundidad"""
    # Implementar lógica similar a la existente en graficar.py pero usando matplotlib


def crear_grafico_incrementos(ax, datos_tubo, fechas, unidades_eje, orden_ascendente, color_scheme):
    """Crea un gráfico de incrementos vs profundidad"""
    # Implementar lógica similar


def crear_grafico_temporal(ax, datos_tubo, fechas, unidades_eje):
    """Crea un gráfico de evolución temporal"""
    # Implementar lógica similar


def fig_to_buffer(fig):
    """Convierte una figura de matplotlib a un buffer de bytes"""
    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
    buffer.seek(0)
    return buffer


def añadir_graficos_a_pdf(pdf, buffer_graficos):
    """Añade los gráficos generados al PDF"""
    # Configurar posiciones para los gráficos en el PDF
    posiciones = [
        (2 * cm, 5 * cm, 8 * cm, 6 * cm),  # (x, y, ancho, alto) para el primer gráfico
        (11 * cm, 5 * cm, 8 * cm, 6 * cm),  # para el segundo gráfico
        (2 * cm, 12 * cm, 8 * cm, 6 * cm),  # para el tercer gráfico
        (11 * cm, 12 * cm, 8 * cm, 6 * cm)  # para el cuarto gráfico
    ]

    for i, buffer in enumerate(buffer_graficos):
        if i < len(posiciones):
            x, y, ancho, alto = posiciones[i]
            # Convertir y a coordenadas ReportLab
            y = pdf._pagesize[1] - y - alto

            # Añadir gráfico al PDF
            pdf.drawImage(buffer, x, y, width=ancho, height=alto)


def hex_a_rgb(hex_color):
    """Convierte un color hexadecimal a RGB (valores 0-1)"""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return r / 255.0, g / 255.0, b / 255.0


def aplicar_filtro_fechas(fechas, total_camp, ultimas_camp, cadencia_dias):
    """
    Filtra las fechas según los parámetros de configuración
    """
    # Implementación similar a la existente en graficar.py
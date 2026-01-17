# utils/pdf_generator.py

"""
Módulo para generación de PDF basado en plantillas JSON.
Contiene funciones para dibujar diferentes tipos de elementos
y generar informes PDF completos.
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, cm
from reportlab.platypus import Image
from pathlib import Path
import io
import base64
import os
import tempfile
import math
import json
import importlib.util
import sys
from PIL import Image
import matplotlib.pyplot as plt

from reportlab.graphics import renderPDF
try:
    from svglib.svglib import svg2rlg
except ImportError:
    print("ADVERTENCIA: No se pudo importar svglib. La generación de SVG no estará disponible.")
    # Función de reserva en caso de falta de biblioteca
    def svg2rlg(path):
        raise ImportError("No se ha instalado svglib. Instale con 'pip install svglib'")

# Constantes
A4_PORTRAIT_WIDTH = 595  # Ancho A4 vertical en puntos (21 cm)
A4_PORTRAIT_HEIGHT = 842  # Alto A4 vertical en puntos (29.7 cm)
A4_LANDSCAPE_WIDTH = 842  # Ancho A4 horizontal en puntos (29.7 cm)
A4_LANDSCAPE_HEIGHT = 595  # Alto A4 horizontal en puntos (21 cm)
CM_TO_POINTS = 28.35  # 1 cm = 28.35 puntos
MM_TO_POINTS = 2.835  # 1 mm = 2.835 puntos


def configure_page(pdf, page_config):
    """Configura una página del PDF según la orientación especificada"""
    orientation = page_config.get('orientacion', 'portrait')
    page_size = landscape(A4) if orientation == 'landscape' else A4
    pdf.setPageSize(page_size)
    return page_size


def draw_line(pdf, line_data, page_height):
    """
    Dibuja una línea en el PDF

    Args:
        pdf: Objeto canvas de ReportLab
        line_data: Diccionario con datos de la línea
        page_height: Altura total de la página en puntos
    """
    # Extraer datos
    x1 = line_data["geometria"]["x1"] * CM_TO_POINTS
    y1 = line_data["geometria"]["y1"] * CM_TO_POINTS
    x2 = line_data["geometria"]["x2"] * CM_TO_POINTS
    y2 = line_data["geometria"]["y2"] * CM_TO_POINTS

    # Ajustar coordenadas Y (origen en ReportLab está en la esquina inferior izquierda)
    y1 = page_height - y1
    y2 = page_height - y2

    # Configurar estilo
    pdf.setStrokeColor(line_data["estilo"]["color"])
    pdf.setLineWidth(line_data["estilo"]["grosor"])

    # Dibujar línea
    pdf.line(x1, y1, x2, y2)


def draw_rectangle(pdf, rect_data, page_height):
    """
    Dibuja un rectángulo en el PDF

    Args:
        pdf: Objeto canvas de ReportLab
        rect_data: Diccionario con datos del rectángulo
        page_height: Altura total de la página en puntos
    """
    # Extraer datos
    x = rect_data["geometria"]["x"] * CM_TO_POINTS
    y = rect_data["geometria"]["y"] * CM_TO_POINTS
    ancho = rect_data["geometria"]["ancho"] * CM_TO_POINTS
    alto = rect_data["geometria"]["alto"] * CM_TO_POINTS

    # Ajustar coordenada Y
    y = page_height - y - alto

    # Configurar estilos
    pdf.setStrokeColor(rect_data["estilo"]["color_borde"])
    pdf.setLineWidth(rect_data["estilo"]["grosor_borde"])
    pdf.setFillColor(rect_data["estilo"]["color_relleno"])
    opacidad = rect_data["estilo"]["opacidad"] / 100

    # Dibujar rectángulo
    pdf.saveState()

    # Aplicar opacidad si es menor al 100%
    if opacidad < 1.0:
        pdf.setFillAlpha(opacidad)

    pdf.rect(
        x, y, ancho, alto,
        fill=(opacidad > 0),
        stroke=(rect_data["estilo"]["grosor_borde"] > 0)
    )

    pdf.restoreState()


def draw_text(pdf, text_data, page_height):
    """
    Dibuja un texto en el PDF

    Args:
        pdf: Objeto canvas de ReportLab
        text_data: Diccionario con datos del texto
        page_height: Altura total de la página en puntos
    """
    # Extraer datos
    x = text_data["geometria"]["x"] * CM_TO_POINTS
    y = text_data["geometria"]["y"] * CM_TO_POINTS
    ancho = text_data["geometria"]["ancho"] * CM_TO_POINTS
    alto = text_data["geometria"]["alto"] * CM_TO_POINTS

    # Ajustar coordenada Y
    y = page_height - y - alto

    # Configurar estilos de texto
    font_name = text_data["estilo"]["familia_fuente"]
    font_size = text_data["estilo"]["tamano"]

    # Aplicar negrita/cursiva si es necesario
    if text_data["estilo"]["negrita"] == "bold" and text_data["estilo"]["cursiva"] == "italic":
        font_name = f"{font_name}-BoldItalic"
    elif text_data["estilo"]["negrita"] == "bold":
        font_name = f"{font_name}-Bold"
    elif text_data["estilo"]["cursiva"] == "italic":
        font_name = f"{font_name}-Italic"

    pdf.setFont(font_name, font_size)
    pdf.setFillColor(text_data["estilo"]["color"])

    # Obtener el texto
    texto = text_data["contenido"]["texto"] or ""

    # Aplicar rotación si es necesario
    rotation = text_data["estilo"].get("rotacion", 0)
    if rotation != 0:
        pdf.saveState()
        # Calcular el centro del área de texto
        center_x = x + ancho / 2
        center_y = y + alto / 2
        # Rotar
        pdf.translate(center_x, center_y)
        pdf.rotate(rotation)
        pdf.translate(-center_x, -center_y)

    # Procesar el texto según alineación
    lines = texto.split('\n')

    # Altura de una línea
    line_height = font_size * 1.2

    # Calcular posición vertical inicial según alineación vertical
    if text_data["estilo"]["alineacion_v"] == "top":
        y_pos = y + alto - font_size
    elif text_data["estilo"]["alineacion_v"] == "middle":
        y_pos = y + alto / 2 + (len(lines) * line_height) / 2 - font_size
    else:  # bottom
        y_pos = y + (len(lines) * line_height) - font_size

    # Dibujar cada línea de texto
    for line in lines:
        # Calcular posición horizontal según alineación
        if text_data["estilo"]["alineacion_h"] == "left":
            pdf.drawString(x, y_pos, line)
        elif text_data["estilo"]["alineacion_h"] == "center":
            pdf.drawCentredString(x + ancho / 2, y_pos, line)
        elif text_data["estilo"]["alineacion_h"] == "right":
            pdf.drawRightString(x + ancho, y_pos, line)
        elif text_data["estilo"]["alineacion_h"] == "justify" and line:
            # Implementar justificación básica
            words = line.split()
            if len(words) > 1:
                word_width = pdf.stringWidth(line, font_name, font_size) / len(words)
                space_width = (ancho - pdf.stringWidth(line, font_name, font_size)) / (len(words) - 1)
                x_pos = x
                for word in words:
                    pdf.drawString(x_pos, y_pos, word)
                    x_pos += pdf.stringWidth(word, font_name, font_size) + space_width
            else:
                pdf.drawString(x, y_pos, line)

        # Pasar a la siguiente línea
        y_pos -= line_height

    # Restaurar estado si se aplicó rotación
    if rotation != 0:
        pdf.restoreState()


def draw_image(pdf, image_data, page_height, plantilla_dir=None, biblioteca_path=None):
    """
    Dibuja una imagen en el PDF

    Args:
        pdf: Objeto canvas de ReportLab
        image_data: Diccionario con datos de la imagen
        page_height: Altura total de la página en puntos
        plantilla_dir: Directorio de la plantilla actual (opcional)
        biblioteca_path: Ruta a la biblioteca de plantillas (opcional)
    """
    # Extraer datos
    x = image_data["geometria"]["x"] * CM_TO_POINTS
    y = image_data["geometria"]["y"] * CM_TO_POINTS
    ancho = image_data["geometria"]["ancho"] * CM_TO_POINTS
    alto = image_data["geometria"]["alto"] * CM_TO_POINTS

    # Aplicar reducción
    reduccion = image_data["estilo"].get("reduccion", 0)
    x += reduccion
    y += reduccion
    ancho -= (reduccion * 2)
    alto -= (reduccion * 2)

    # Ajustar coordenada Y
    y = page_height - y - alto

    # Obtener opacidad
    opacidad = image_data["estilo"].get("opacidad", 100) / 100
    preserveAspectRatio = image_data["estilo"].get("mantener_proporcion", True)

    # Buscar la imagen
    imagen_encontrada = False

    # Obtener la ruta de la imagen
    ruta_imagen = image_data["imagen"].get("ruta_nueva", "")

    # CASO 1: Intentar cargar desde ruta
    if ruta_imagen:
        # Construir posibles rutas para encontrar la imagen
        posibles_rutas = []

        # Añadir ruta directa
        posibles_rutas.append(Path(ruta_imagen))

        # Añadir rutas relativas a la plantilla si tenemos el directorio
        if plantilla_dir:
            posibles_rutas.append(plantilla_dir / ruta_imagen)
            posibles_rutas.append(plantilla_dir / "assets" / Path(ruta_imagen).name)

        # Añadir rutas a la biblioteca global
        if biblioteca_path:
            posibles_rutas.append(biblioteca_path / ruta_imagen)
            posibles_rutas.append(biblioteca_path / "assets" / Path(ruta_imagen).name)

        # Añadir rutas relativas al directorio actual
        posibles_rutas.append(Path("assets") / Path(ruta_imagen).name)
        posibles_rutas.append(Path(Path(ruta_imagen).name))

        # Probar cada ruta
        for ruta in posibles_rutas:
            try:
                if ruta.exists():
                    # Configurar transparencia si es necesario
                    if opacidad < 1.0:
                        pdf.saveState()
                        pdf.setFillAlpha(opacidad)

                    # Dibujar imagen
                    pdf.drawImage(
                        str(ruta),
                        x, y,
                        width=ancho,
                        height=alto,
                        preserveAspectRatio=preserveAspectRatio,
                        mask='auto'
                    )

                    if opacidad < 1.0:
                        pdf.restoreState()

                    imagen_encontrada = True
                    break
            except Exception as e:
                continue

    # CASO 2: Intentar cargar desde datos base64
    if not imagen_encontrada and image_data["imagen"].get("datos_temp"):
        try:
            # Extraer datos base64
            img_data = image_data["imagen"]["datos_temp"]
            if "," in img_data:  # Si tiene formato "data:image/png;base64,DATOS"
                img_data = img_data.split(",")[1]

            # Decodificar datos
            img_binary = base64.b64decode(img_data)

            # Crear archivo temporal con la extensión correcta
            ext = image_data["imagen"].get("formato", "png")
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_file:
                temp_file.write(img_binary)
                temp_path = temp_file.name

            # Configurar transparencia si es necesario
            if opacidad < 1.0:
                pdf.saveState()
                pdf.setFillAlpha(opacidad)

            # Dibujar imagen
            pdf.drawImage(
                temp_path,
                x, y,
                width=ancho,
                height=alto,
                preserveAspectRatio=preserveAspectRatio,
                mask='auto'
            )

            if opacidad < 1.0:
                pdf.restoreState()

            # Eliminar el archivo temporal
            os.unlink(temp_path)
            imagen_encontrada = True
        except Exception as e:
            print(f"Error al procesar imagen base64: {str(e)}")

    # Si no se encontró la imagen, dibujar un rectángulo indicativo
    if not imagen_encontrada:
        pdf.setStrokeColor("#999999")
        pdf.setFillColor("#eeeeee")
        pdf.rect(x, y, ancho, alto, fill=True, stroke=True)
        pdf.setFillColor("#666666")
        pdf.setFont("Helvetica", 8)

        if ruta_imagen:
            pdf.drawCentredString(x + ancho / 2, y + alto / 2, "Imagen no encontrada")
            pdf.setFont("Helvetica", 6)
            pdf.drawCentredString(x + ancho / 2, y + alto / 2 - 10, f"Ruta: {Path(ruta_imagen).name}")
        else:
            pdf.drawCentredString(x + ancho / 2, y + alto / 2, "Sin imagen asignada")


def load_module_dynamically(script_path):
    """
    Carga dinámicamente un módulo de Python.

    Args:
        script_path: Ruta completa al archivo Python

    Returns:
        Módulo cargado o None si hubo error
    """
    try:
        module_name = Path(script_path).stem  # Nombre del archivo sin extensión
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if not spec:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"Error al cargar módulo {script_path}: {str(e)}")
        return None


def render_matplotlib_graph(script_path, params, data_source, ancho, alto, formato="png"):
    """
    Renderiza un gráfico usando el script especificado.

    Args:
        script_path: Ruta al script Python que genera el gráfico
        params: Diccionario con parámetros para el script
        data_source: Datos de origen para el gráfico
        formato: Formato de salida del gráfico (png o svg)

    Returns:
        Ruta al archivo temporal del gráfico o None si hubo error
    """
    try:
        # Usar backend no interactivo para evitar errores de GUI
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        print(f"DEBUG: Iniciando renderizado de gráfico con script: {script_path}")
        print(f"DEBUG: Parámetros recibidos: {params.keys()}")

        # Limpiar cualquier figura de matplotlib anterior
        plt.close('all')

        # Añadir directorios al path de Python
        script_dir = os.path.dirname(script_path)
        utils_dir = os.path.join(os.path.dirname(os.path.dirname(script_path)), "utils")

        import sys
        original_path = sys.path.copy()  # Guardar el path original
        sys.path.insert(0, script_dir)
        sys.path.insert(0, utils_dir)  # Añadir carpeta utils

        try:
            # Cargar dinámicamente el módulo
            module = load_module_dynamically(script_path)
            if not module:
                return None

            # Verificar si el módulo tiene la función principal con el mismo nombre
            main_func_name = Path(script_path).stem
            if not hasattr(module, main_func_name):
                print(f"El módulo no contiene la función {main_func_name}")
                return None

            # Obtener la función principal
            main_function = getattr(module, main_func_name)

            # Ejecutar la función con los parámetros y datos
            params['formato'] = formato  # Añadir el formato a los parámetros
            params['alto_cm'] = alto
            params['ancho_cm'] = ancho
            result = main_function(data_source, params)

            # Si el resultado es una URL de datos, convertir a archivo temporal
            if isinstance(result, str) and result.startswith('data:image'):
                try:
                    # Extraer los datos base64
                    img_data = result.split(',')[1]
                    img_binary = base64.b64decode(img_data)

                    # Crear archivo temporal
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{formato}") as temp_file:
                        temp_file.write(img_binary)
                        temp_path = temp_file.name
                        return temp_path
                except Exception as e:
                    print(f"Error al procesar imagen base64: {str(e)}")
                    return None

            # Si no devolvió una imagen, asumir que generó una figura con matplotlib
            # Guardar la figura actual en un archivo temporal con el formato especificado
            temp_path = tempfile.mktemp(suffix=f'.{formato}')

            try:
                if formato.lower() == 'svg':
                    plt.savefig(temp_path, format='svg', bbox_inches='tight')
                else:  # Por defecto usar PNG
                    plt.savefig(temp_path, dpi=300, format='png', bbox_inches='tight')
            except Exception as e:
                print(f"Error al guardar en formato {formato}: {str(e)}")
                # Si falla un formato, intentar con el otro
                formato_alt = "png" if formato.lower() == "svg" else "svg"
                temp_path = tempfile.mktemp(suffix=f'.{formato_alt}')
                plt.savefig(temp_path, format=formato_alt, bbox_inches='tight',
                            dpi=300 if formato_alt == "png" else None)
                print(f"Se usó formato alternativo: {formato_alt}")

            plt.close()
            return temp_path

        finally:
            # Restaurar el path original al finalizar
            sys.path = original_path

    except Exception as e:
        print(f"Error al renderizar gráfico: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def draw_graph(pdf, graph_data, page_height, data_source, biblioteca_graficos_path):
    """
    Dibuja un gráfico generado por un script en el PDF

    Args:
        pdf: Objeto canvas de ReportLab
        graph_data: Diccionario con datos del gráfico
        page_height: Altura total de la página en puntos
        data_source: Datos de origen para el gráfico
        biblioteca_graficos_path: Ruta a la biblioteca de gráficos
    """
    # Extraer datos
    x = graph_data["geometria"]["x"] * CM_TO_POINTS
    y = graph_data["geometria"]["y"] * CM_TO_POINTS
    ancho = graph_data["geometria"]["ancho"] * CM_TO_POINTS
    alto = graph_data["geometria"]["alto"] * CM_TO_POINTS

    # Aplicar reducción
    reduccion = graph_data["estilo"].get("reduccion", 0)
    x += reduccion
    y += reduccion
    ancho -= (reduccion * 2)
    alto -= (reduccion * 2)

    # Ajustar coordenada Y
    y = page_height - y - alto

    # Obtener opacidad
    opacidad = graph_data["estilo"].get("opacidad", 100) / 100

    # Obtener formato de gráfico (directamente de configuracion)
    formato = graph_data["configuracion"].get("formato", "png")

    # Obtener nombre del script
    script_name = graph_data["configuracion"].get("script", "")
    if not script_name:
        # Dibujar un placeholder si no hay script
        pdf.setStrokeColor("#999999")
        pdf.setFillColor("#eeeeee")
        pdf.rect(x, y, ancho, alto, fill=True, stroke=True)
        pdf.setFillColor("#666666")
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(x + ancho / 2, y + alto / 2, "Script no especificado")
        return

    # Asegurarse de que tiene extensión .py
    if not script_name.endswith('.py'):
        script_name += '.py'

    # Buscar el script en la biblioteca de gráficos
    script_basename = Path(script_name).stem
    script_path = biblioteca_graficos_path / script_basename / (script_basename + '.py')

    if not script_path.exists():
        # Dibujar un placeholder si no se encuentra el script
        pdf.setStrokeColor("#999999")
        pdf.setFillColor("#eeeeee")
        pdf.rect(x, y, ancho, alto, fill=True, stroke=True)
        pdf.setFillColor("#666666")
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(x + ancho / 2, y + alto / 2, f"Script no encontrado: {script_name}")
        pdf.setFont("Helvetica", 8)
        pdf.drawCentredString(x + ancho / 2, y + alto / 2 - 15, f"Ubicación buscada: {script_path}")
        return

    # Obtener parámetros del gráfico
    params = graph_data["configuracion"].get("parametros", {})

    # Generar el gráfico
    #temp_graph_path = render_matplotlib_graph(script_path, params, data_source, formato)
    temp_graph_path = render_matplotlib_graph(script_path, params, data_source,
                                              graph_data["geometria"]["ancho"], graph_data["geometria"]["alto"],
                                              formato)

    if temp_graph_path:
        try:
            # Verificar el tipo de archivo generado realmente
            actual_formato = os.path.splitext(temp_graph_path)[1].lower()[1:]

            if actual_formato == 'svg':
                try:
                    # Usar svglib para convertir SVG a elementos ReportLab
                    drawing = svg2rlg(temp_graph_path)

                    # Ajustar tamaño del dibujo al tamaño deseado
                    if drawing.width > 0 and drawing.height > 0:  # Evitar división por cero
                        xscale = ancho / drawing.width
                        yscale = alto / drawing.height
                        drawing.scale(xscale, yscale)

                    # Configurar transparencia si es necesario
                    if opacidad < 1.0:
                        pdf.saveState()
                        pdf.setFillAlpha(opacidad)

                    # Dibujar el SVG
                    renderPDF.draw(drawing, pdf, x, y)

                    if opacidad < 1.0:
                        pdf.restoreState()
                except Exception as svg_error:
                    print(f"Error al procesar SVG: {str(svg_error)}")
                    # Si falla el SVG, intentamos como imagen normal
                    if opacidad < 1.0:
                        pdf.saveState()
                        pdf.setFillAlpha(opacidad)

                    pdf.drawImage(
                        temp_graph_path,
                        x, y,
                        width=ancho,
                        height=alto,
                        preserveAspectRatio=False,
                        mask='auto'
                    )

                    if opacidad < 1.0:
                        pdf.restoreState()
            else:
                # Si es PNG u otro formato, usar el método tradicional
                if opacidad < 1.0:
                    pdf.saveState()
                    pdf.setFillAlpha(opacidad)

                pdf.drawImage(
                    temp_graph_path,
                    x, y,
                    width=ancho,
                    height=alto,
                    preserveAspectRatio=False,
                    mask='auto'
                )

                if opacidad < 1.0:
                    pdf.restoreState()

            # Eliminar el archivo temporal
            try:
                os.unlink(temp_graph_path)
            except:
                print(f"No se pudo eliminar el archivo temporal: {temp_graph_path}")

        except Exception as e:
            # Error al generar gráfico
            print(f"ERROR: Fallo al generar gráfico {script_name}: {str(e)}")
            import traceback
            traceback.print_exc()

            pdf.setStrokeColor("#FF0000")
            pdf.setFillColor("#FFEEEE")
            pdf.rect(x, y, ancho, alto, fill=True, stroke=True)
            pdf.setFillColor("#CC0000")
            pdf.setFont("Helvetica", 10)
            pdf.drawCentredString(x + ancho / 2, y + alto / 2, "Error al generar gráfico")
            pdf.setFont("Helvetica", 6)
            
            # Mostrar mensaje de error más largo y dividido en líneas
            error_msg = str(e)
            chunks = [error_msg[i:i+60] for i in range(0, len(error_msg), 60)]
            y_offset = 15
            for chunk in chunks[:3]:  # Mostrar hasta 3 líneas
                pdf.drawCentredString(x + ancho / 2, y + alto / 2 - y_offset, chunk)
                y_offset += 8
    else:
        # Si no se pudo generar el gráfico, dibujar un placeholder
        pdf.setStrokeColor("#FF0000")
        pdf.setFillColor("#FFEEEE")
        pdf.rect(x, y, ancho, alto, fill=True, stroke=True)
        pdf.setFillColor("#CC0000")
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(x + ancho / 2, y + alto / 2, "Error al generar gráfico")

def generate_pdf_from_template(template_data, data_source, output_buffer=None,
                               biblioteca_path=None, biblioteca_graficos_path=None):
    """
    Genera un PDF completo a partir de una plantilla JSON

    Args:
        template_data: Diccionario con los datos de la plantilla
        data_source: Datos de origen para los gráficos
        output_buffer: Buffer de salida (opcional, si no se proporciona se crea uno)
        biblioteca_path: Ruta base a la biblioteca de plantillas (opcional)
        biblioteca_graficos_path: Ruta a la biblioteca de gráficos (opcional)
    """
    if output_buffer is None:
        output_buffer = io.BytesIO()

    # Crear el PDF
    pdf = canvas.Canvas(output_buffer)

    # Definir rutas de bibliotecas - usar la ruta específica proporcionada o la predeterminada
    if biblioteca_graficos_path is None:
        biblioteca_graficos_path = Path("biblioteca_graficos")

    # Obtener nombre de la plantilla
    nombre_plantilla = template_data.get('configuracion', {}).get('nombre_plantilla', '')
    plantilla_dir = None

    if nombre_plantilla and biblioteca_path:
        plantilla_dir = biblioteca_path / nombre_plantilla

    # Procesar cada página
    primera_pagina = True
    for page_key, page_data in template_data.get('paginas', {}).items():
        # Si no es la primera página, añadir una nueva
        if not primera_pagina:
            pdf.showPage()
        else:
            primera_pagina = False

        # Configurar la página
        page_size = configure_page(pdf, page_data.get('configuracion', {'orientacion': 'portrait'}))
        page_width, page_height = page_size

        # Obtener los elementos y ordenarlos por zIndex
        elementos = page_data.get('elementos', {})
        elementos_ordenados = sorted(
            elementos.items(),
            key=lambda x: x[1]["metadata"].get("zIndex", 0)
        )

        # Dibujar cada elemento
        for nombre, elemento in elementos_ordenados:
            # Verificar si el elemento es visible
            if not elemento["metadata"].get("visible", True):
                continue

            # Dibujar según el tipo de elemento
            if elemento["tipo"] == "linea":
                draw_line(pdf, elemento, page_height)
            elif elemento["tipo"] == "rectangulo":
                draw_rectangle(pdf, elemento, page_height)
            elif elemento["tipo"] == "texto":
                draw_text(pdf, elemento, page_height)
            elif elemento["tipo"] == "imagen":
                draw_image(pdf, elemento, page_height, plantilla_dir, biblioteca_path)
            elif elemento["tipo"] == "grafico":
                draw_graph(pdf, elemento, page_height, data_source, biblioteca_graficos_path)

    # Guardar el PDF
    pdf.save()
    output_buffer.seek(0)

    return output_buffer
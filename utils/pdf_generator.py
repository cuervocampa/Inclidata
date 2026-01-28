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


def get_safe_font_name(family, bold=False, italic=False):
    """
    Mapea nombres de fuentes a fuentes estándar de ReportLab.
    """
    # Mapa de fuentes comunes a estándares
    font_map = {
        "Aptos": "Helvetica",
        "Arial": "Helvetica",
        "Verdana": "Helvetica",
        "Tahoma": "Helvetica",
        "Trebuchet MS": "Helvetica",
        "Segoe UI": "Helvetica",
        "Roboto": "Helvetica",
        "Open Sans": "Helvetica",
        "Lato": "Helvetica",
        "Times New Roman": "Times-Roman",
        "Georgia": "Times-Roman",
        "Garamond": "Times-Roman",
        "Courier New": "Courier",
        "Consolas": "Courier",
    }
    
    # Obtener familia base
    base_font = font_map.get(family, "Helvetica")
    
    # Si la familia ya es una estándar, usarla
    if family in ["Helvetica", "Times-Roman", "Courier", "Symbol", "ZapfDingbats"]:
        base_font = family

    # Construir nombre con sufijos
    font_name = base_font
    
    if bold and italic:
        if base_font == "Times-Roman":
            font_name = "Times-BoldItalic"
        elif base_font == "Courier":
            font_name = "Courier-BoldOblique"
        else: # Helvetica por defecto
            font_name = "Helvetica-BoldOblique"
    elif bold:
        if base_font == "Times-Roman":
            font_name = "Times-Bold"
        elif base_font == "Courier":
            font_name = "Courier-Bold"
        else:
            font_name = "Helvetica-Bold"
    elif italic:
        if base_font == "Times-Roman":
            font_name = "Times-Italic"
        elif base_font == "Courier":
            font_name = "Courier-Oblique"
        else:
            font_name = "Helvetica-Oblique"
            
    return font_name


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


def draw_text(pdf, text_data, page_height, data_source=None):
    """
    Dibuja un texto en el PDF
    
    Args:
        pdf: Objeto canvas de ReportLab
        text_data: Diccionario con datos del texto
        page_height: Altura total de la página en puntos
        data_source: Datos de origen (opcional) para sustitución de variables
    """
    # Extraer datos
    x = text_data["geometria"]["x"] * CM_TO_POINTS
    y = text_data["geometria"]["y"] * CM_TO_POINTS
    ancho = text_data["geometria"]["ancho"] * CM_TO_POINTS
    alto = text_data["geometria"]["alto"] * CM_TO_POINTS

    # Ajustar coordenada Y
    y = page_height - y - alto

    # Configurar estilos de texto
    font_family = text_data["estilo"]["familia_fuente"]
    font_size = text_data["estilo"]["tamano"]
    is_bold = text_data["estilo"]["negrita"] == "bold"
    is_italic = text_data["estilo"]["cursiva"] == "italic"

    font_name = get_safe_font_name(font_family, is_bold, is_italic)

    pdf.setFont(font_name, font_size)
    pdf.setFillColor(text_data["estilo"]["color"])

    # Obtener el texto
    texto = text_data["contenido"]["texto"] or ""
    
    # Sustitución de variables
    if data_source and "$CURRENT" in texto:
        nom_sensor = "Desconocido"
        if "info" in data_source and "nom_sensor" in data_source["info"]:
            nom_sensor = data_source["info"]["nom_sensor"]
        texto = texto.replace("$CURRENT", str(nom_sensor))

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
        
        # DEBUG reducido - solo mostrar nombre del script
        # print(f"DEBUG: Iniciando renderizado de gráfico con script: {script_path}")
        # print(f"DEBUG: Parámetros recibidos: {params.keys()}")

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


def resolve_placeholders(params, data_source):
    """
    Reemplaza marcadores de posición en los parámetros con valores del data_source.
    
    Soporta:
    - $CURRENT -> data_source['info']['nom_sensor']
    - $CURRENT_fecha_seleccionada -> data_source.get('fecha_seleccionada')
    - $CURRENT_ultimas_camp -> data_source.get('ultimas_camp')
    - $CURRENT_fecha_inicial -> data_source.get('fecha_inicial')
    - $CURRENT_fecha_final -> data_source.get('fecha_final')
    """
    if not isinstance(params, dict):
        return params
        
    resolved_params = params.copy()
    
    # Obtener valores del data_source
    nom_sensor = "Desconocido"
    if data_source and "info" in data_source and "nom_sensor" in data_source["info"]:
        nom_sensor = data_source["info"]["nom_sensor"]
    
    # Mapeo de placeholders a valores
    # Usar or "" para manejar None de forma segura
    placeholders = {
        "$CURRENT_fecha_seleccionada": (data_source.get("fecha_seleccionada") or "") if data_source else "",
        "$CURRENT_ultimas_camp": str(data_source.get("ultimas_camp") or 3) if data_source else "3",
        "$CURRENT_fecha_inicial": (data_source.get("fecha_inicial") or "") if data_source else "",
        "$CURRENT_fecha_final": (data_source.get("fecha_final") or "") if data_source else "",
        "$CURRENT": nom_sensor  # Este debe ir al final para no interferir con los otros
    }
    
    for key, value in resolved_params.items():
        if isinstance(value, str):
            # Reemplazar todos los placeholders que aparezcan
            for placeholder, replacement in placeholders.items():
                if placeholder in value:
                    value = value.replace(placeholder, str(replacement) if replacement else "")
            resolved_params[key] = value
        elif isinstance(value, dict):
            # Recursión para diccionarios anidados (como 'celdas')
            resolved_params[key] = resolve_placeholders(value, data_source)
             
    return resolved_params


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
    raw_params = graph_data["configuracion"].get("parametros", {})
    params = resolve_placeholders(raw_params, data_source)

    # Generar el gráfico
    print(f"[PDF] Generando gráfico: {script_name}")
    temp_graph_path = render_matplotlib_graph(script_path, params, data_source,
                                              graph_data["geometria"]["ancho"], graph_data["geometria"]["alto"],
                                              formato)
    if not temp_graph_path:
        print(f"[PDF] ERROR: render_matplotlib_graph retornó None para {script_name}")

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


def draw_table_from_grid(pdf, table_data, page_height, data_source, biblioteca_tablas_path=None):
    """
    Dibuja una tabla basada en la estructura de cuadrícula (niveles/columnas).
    
    Soporta:
    - Niveles estáticos: se dibujan tal como están definidos
    - Niveles autorrelleno: generan múltiples filas basadas en datos del script
    - Sustitución de placeholders: [clave] se reemplaza por valores del script
    - Encabezados dinámicos: fecha_1, fecha_2, fecha_3 se reemplazan por fechas del script
    """
    # Extraer geometría
    x = table_data["geometria"]["x"] * CM_TO_POINTS
    y = table_data["geometria"]["y"] * CM_TO_POINTS
    ancho_maximo = table_data["geometria"]["ancho_maximo"] * CM_TO_POINTS
    alto_maximo = table_data["geometria"]["alto_maximo"] * CM_TO_POINTS
    
    # Extraer niveles
    niveles = table_data.get("cuadricula", {}).get("niveles", [])
    if not niveles:
        return
        
    y_actual = page_height - y
    x_inicial = x
    
    # Obtener script y parámetros si existen
    script_name = table_data.get("configuracion", {}).get("script", "")
    raw_params = table_data.get("configuracion", {}).get("parametros", {})
    params = resolve_placeholders(raw_params, data_source)
    
    # Datos del script (diccionario con encabezados_nivel_1 y filas)
    datos_script = None
    if script_name and biblioteca_tablas_path:
        try:
            # Lógica de carga de script
            script_name_original = script_name
            if not script_name.endswith('.py'):
                script_name = script_name + '.py'
                
            script_path = biblioteca_tablas_path / script_name
            if not script_path.exists():
                script_basename = Path(script_name).stem
                script_path = biblioteca_tablas_path / script_basename / script_name
            
            if script_path.exists():
                module = load_module_dynamically(str(script_path))
                if module:
                    # Buscar la función con el nombre del archivo
                    main_func_name = Path(script_path).stem
                    if hasattr(module, main_func_name):
                        main_function = getattr(module, main_func_name)
                        datos_script = main_function(data_source, params)
            else:
                print(f"Script de tabla no encontrado: {script_path}")
        except Exception as e:
            print(f"Error cargando script de tabla {script_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Extraer datos del script si es un diccionario con estructura esperada
    encabezados_fechas = []
    filas_datos = []
    if datos_script and isinstance(datos_script, dict):
        encabezados_fechas = datos_script.get("encabezados_nivel_1", [])
        filas_datos = datos_script.get("filas", [])
    elif datos_script and isinstance(datos_script, list):
        # Compatibilidad: si el script devuelve lista directamente
        filas_datos = datos_script
    
    # Crear mapeo de fechas para sustitución en nivel 2
    # fecha_1 -> primera fecha, fecha_2 -> segunda, fecha_3 -> tercera
    mapeo_fechas = {}
    for i, fecha in enumerate(encabezados_fechas):
        mapeo_fechas[f"fecha_{i+1}"] = fecha
    
    # Procesar cada nivel
    for nivel in niveles:
        tipo = nivel.get("tipo", "estatico")
        columnas = nivel.get("columnas", [])
        alto_fila = nivel.get("alto_fila", 0.5) * CM_TO_POINTS
        config_dinamica = nivel.get("configuracion_dinamica", {})
        
        # Verificar límite vertical
        if (page_height - y_actual) > alto_maximo:
            break
            
        filas_a_dibujar = []
        
        if tipo == "autorrelleno" and filas_datos:
            # Generar una fila por cada elemento en filas_datos
            sombreado_alterno = config_dinamica.get("sombreado_alterno", False)
            color_par = config_dinamica.get("color_par", "#f8f9fa")
            color_impar = config_dinamica.get("color_impar", "#ffffff")
            
            for fila_idx, dato_fila in enumerate(filas_datos):
                fila_render = []
                
                for col_idx, col in enumerate(columnas):
                    # Copia profunda de la columna
                    col_render = {}
                    col_render["ancho"] = col.get("ancho", 3.0)
                    col_render["formato"] = col.get("formato", {}).copy()
                    col_render["bordes"] = col.get("bordes", {})
                    
                    contenido_plantilla = col.get("contenido", "")
                    
                    # Resolver contenido dinámico
                    contenido_final = contenido_plantilla
                    
                    if isinstance(dato_fila, dict):
                        # Buscar claves entre corchetes [clave]
                        if contenido_plantilla.startswith("[") and contenido_plantilla.endswith("]"):
                            clave = contenido_plantilla[1:-1]
                            
                            # Mapeo de claves de la plantilla a claves del script
                            # [prof] -> prof
                            # [desp_a] -> desp_a_N (donde N depende de la columna)
                            # [desp_b] -> desp_b_N
                            
                            if clave == "prof":
                                contenido_final = str(dato_fila.get("prof", ""))
                            elif clave == "desp_a":
                                # Determinar qué fecha corresponde a esta columna
                                # Columnas: 0=prof, 1=desp_a_1, 2=desp_b_1, 3=desp_a_2, 4=desp_b_2, 5=desp_a_3, 6=desp_b_3
                                # Para 7 columnas: idx 1,3,5 son desp_a; idx 2,4,6 son desp_b
                                fecha_num = (col_idx + 1) // 2  # 1->1, 2->1, 3->2, 4->2, 5->3, 6->3
                                contenido_final = str(dato_fila.get(f"desp_a_{fecha_num}", ""))
                            elif clave == "desp_b" or clave.startswith("desp_b"):
                                fecha_num = (col_idx + 1) // 2
                                contenido_final = str(dato_fila.get(f"desp_b_{fecha_num}", ""))
                            elif clave in dato_fila:
                                contenido_final = str(dato_fila[clave])
                            else:
                                contenido_final = ""
                    
                    col_render["contenido"] = contenido_final
                    
                    # Aplicar sombreado alterno si está configurado
                    if sombreado_alterno:
                        if col_render["formato"].get("color_fondo") == "transparent":
                            col_render["formato"]["color_fondo"] = color_par if fila_idx % 2 == 0 else color_impar
                    
                    fila_render.append(col_render)
                
                filas_a_dibujar.append(fila_render)
        
        elif tipo == "estatico":
            # Para niveles estáticos, sustituir fechas si corresponde
            fila_render = []
            for col in columnas:
                col_render = {}
                col_render["ancho"] = col.get("ancho", 3.0)
                col_render["formato"] = col.get("formato", {}).copy()
                col_render["bordes"] = col.get("bordes", {})
                
                contenido = col.get("contenido", "")
                
                # Sustituir fecha_1, fecha_2, fecha_3 por valores reales
                if contenido in mapeo_fechas:
                    contenido = mapeo_fechas[contenido]
                
                col_render["contenido"] = contenido
                fila_render.append(col_render)
            
            filas_a_dibujar.append(fila_render)
        
        # Si no se generaron filas, usar la definición directa (fallback)
        if not filas_a_dibujar:
            fila_render = []
            for col in columnas:
                col_render = {
                    "ancho": col.get("ancho", 3.0),
                    "formato": col.get("formato", {}),
                    "bordes": col.get("bordes", {}),
                    "contenido": col.get("contenido", "")
                }
                fila_render.append(col_render)
            filas_a_dibujar.append(fila_render)
            
        # Dibujar las filas del nivel
        for fila_cols in filas_a_dibujar:
            y_actual -= alto_fila
            
            # Verificar límite vertical
            if (page_height - y_actual) > alto_maximo:
                break
            
            x_celda = x_inicial
            
            for col in fila_cols:
                ancho = col.get("ancho", 3.0) * CM_TO_POINTS
                
                # Estilos
                formato = col.get("formato", {})
                estilo_fondo = formato.get("color_fondo", "#ffffff")
                estilo_texto = formato.get("color_texto", "#333333")
                negrita = formato.get("negrita", False)
                alineacion = formato.get("alineacion", "center")
                familia = nivel.get("estilo", {}).get("fuente", "Helvetica")
                tamano = nivel.get("estilo", {}).get("tamano", 10)
                
                # Bordes
                bordes = col.get("bordes", {})
                
                # Dibujar fondo
                if estilo_fondo and estilo_fondo != "transparent":
                    pdf.setFillColor(estilo_fondo)
                    pdf.rect(x_celda, y_actual, ancho, alto_fila, fill=True, stroke=False)
                
                # Dibujar bordes
                def dibujar_linea_borde(x1, y1, x2, y2, borde_props):
                    if borde_props.get("activo", True):
                        pdf.setStrokeColor(borde_props.get("color", "#000000"))
                        pdf.setLineWidth(borde_props.get("grosor", 1))
                        pdf.line(x1, y1, x2, y2)

                dibujar_linea_borde(x_celda, y_actual + alto_fila, x_celda + ancho, y_actual + alto_fila, bordes.get("superior", {}))
                dibujar_linea_borde(x_celda, y_actual, x_celda + ancho, y_actual, bordes.get("inferior", {}))
                dibujar_linea_borde(x_celda, y_actual, x_celda, y_actual + alto_fila, bordes.get("izquierdo", {}))
                dibujar_linea_borde(x_celda + ancho, y_actual, x_celda + ancho, y_actual + alto_fila, bordes.get("derecho", {}))
                
                # Contenido con resolución de variables
                texto_raw = col.get("contenido", "")
                texto_final = str(texto_raw)
                
                # Resolver $CURRENT
                if "$CURRENT" in texto_final and data_source:
                    nom_sensor = data_source.get("info", {}).get("nom_sensor", "")
                    texto_final = texto_final.replace("$CURRENT", str(nom_sensor))
                
                # Configurar fuente
                font_name = get_safe_font_name(familia, negrita, False)
                pdf.setFont(font_name, tamano)
                pdf.setFillColor(estilo_texto)
                
                # Posicionamiento texto
                text_y = y_actual + (alto_fila - tamano)/2 + 2

                if alineacion == "left":
                    pdf.drawString(x_celda + 2, text_y, texto_final)
                elif alineacion == "right":
                    pdf.drawRightString(x_celda + ancho - 2, text_y, texto_final)
                else:  # center
                    pdf.drawCentredString(x_celda + ancho/2, text_y, texto_final)
                
                x_celda += ancho


def draw_table(pdf, table_data, page_height, data_source, biblioteca_tablas_path=None):
    """
    Dibuja una tabla en el PDF
    """
    # Detectar si es una tabla basada en cuadrícula (nuevo formato)
    if "cuadricula" in table_data and "niveles" in table_data["cuadricula"] and table_data["cuadricula"]["niveles"]:
        draw_table_from_grid(pdf, table_data, page_height, data_source, biblioteca_tablas_path)
        return

    # Extraer geometría
    x = table_data["geometria"]["x"] * CM_TO_POINTS
    y = table_data["geometria"]["y"] * CM_TO_POINTS
    ancho_maximo = table_data["geometria"]["ancho_maximo"] * CM_TO_POINTS
    alto_maximo = table_data["geometria"]["alto_maximo"] * CM_TO_POINTS
    
    # Extraer estructura
    estructura = table_data.get("estructura", {})
    num_columnas = estructura.get("num_columnas", 5)
    anchos_columnas = estructura.get("anchos_columnas", [])
    alto_fila = estructura.get("alto_fila", 0.5) * CM_TO_POINTS
    mostrar_encabezados = estructura.get("mostrar_encabezados", True)
    alto_encabezado = estructura.get("alto_encabezado", 0.7) * CM_TO_POINTS
    
    # Extraer estilos de bordes
    bordes = table_data.get("estilo", {}).get("bordes", {})
    tipo_borde = bordes.get("tipo", "todos")
    grosor_borde = bordes.get("grosor", 1)
    color_borde = bordes.get("color", "#333333")
    
    # Extraer estilos de sombreado
    sombreado = table_data.get("estilo", {}).get("sombreado", {})
    estilo_sombreado = sombreado.get("estilo", "alternado")
    color_par = sombreado.get("color_par", "#f8f9fa")
    color_impar = sombreado.get("color_impar", "#ffffff")
    color_encabezado = sombreado.get("color_encabezado", "#e9ecef")
    
    # Extraer estilos de texto
    fuente = table_data.get("estilo", {}).get("fuente", "Helvetica")
    tamano_fuente = table_data.get("estilo", {}).get("tamano_fuente", 8)
    color_texto = table_data.get("estilo", {}).get("color_texto", "#333333")
    
    # Obtener datos de la tabla desde el script
    script_name = table_data.get("configuracion", {}).get("script", "")
    raw_params = table_data.get("configuracion", {}).get("parametros", {})
    params = resolve_placeholders(raw_params, data_source)
    
    # Intentar obtener datos del script
    tabla_datos = None
    if script_name and biblioteca_tablas_path:
        try:
            # Buscar el script
            if not script_name.endswith('.py'):
                script_name_py = script_name + '.py'
            else:
                script_name_py = script_name
                
            script_path = biblioteca_tablas_path / script_name_py
            if not script_path.exists():
                # Intentar buscar en subdirectorio
                script_basename = Path(script_name).stem
                script_path = biblioteca_tablas_path / script_basename / script_name_py
            
            if script_path.exists():
                module = load_module_dynamically(str(script_path))
                if module:
                    main_func_name = Path(script_path).stem
                    if hasattr(module, main_func_name):
                        main_function = getattr(module, main_func_name)
                        tabla_datos = main_function(data_source, params)
        except Exception as e:
            print(f"Error al obtener datos de tabla: {str(e)}")
    
    # Si no hay datos, crear datos de ejemplo
    if tabla_datos is None:
        # Generar datos de ejemplo
        encabezados = [f"Col {i+1}" for i in range(num_columnas)]
        filas = []
        for r in range(3):  # 3 filas de ejemplo
            filas.append([f"Dato {r+1}-{c+1}" for c in range(num_columnas)])
        tabla_datos = {"encabezados": encabezados, "filas": filas}
    
    # Calcular anchos de columna
    if not anchos_columnas or len(anchos_columnas) != num_columnas:
        ancho_columna = ancho_maximo / num_columnas
        anchos_columnas_pts = [ancho_columna] * num_columnas
    else:
        anchos_columnas_pts = [a * CM_TO_POINTS for a in anchos_columnas]
    
    # Calcular posiciones Y (ReportLab tiene origen en esquina inferior izquierda)
    y_inicio = page_height - y
    
    # Determinar número de filas
    filas_datos = tabla_datos.get("filas", [])
    encabezados = tabla_datos.get("encabezados", [])
    
    # Dibujar encabezados si está habilitado
    y_actual = y_inicio
    if mostrar_encabezados and encabezados:
        y_actual -= alto_encabezado
        x_actual = x
        
        for col_idx, encabezado in enumerate(encabezados[:num_columnas]):
            ancho_col = anchos_columnas_pts[col_idx] if col_idx < len(anchos_columnas_pts) else anchos_columnas_pts[0]
            
            # Dibujar fondo del encabezado
            if estilo_sombreado != "ninguno":
                pdf.setFillColor(color_encabezado)
                pdf.rect(x_actual, y_actual, ancho_col, alto_encabezado, fill=True, stroke=False)
            
            # Dibujar bordes
            if tipo_borde in ["todos", "exterior"]:
                pdf.setStrokeColor(color_borde)
                pdf.setLineWidth(grosor_borde)
                pdf.rect(x_actual, y_actual, ancho_col, alto_encabezado, fill=False, stroke=True)
            elif tipo_borde == "horizontal":
                pdf.setStrokeColor(color_borde)
                pdf.setLineWidth(grosor_borde)
                pdf.line(x_actual, y_actual, x_actual + ancho_col, y_actual)
                pdf.line(x_actual, y_actual + alto_encabezado, x_actual + ancho_col, y_actual + alto_encabezado)
            
            # Dibujar texto del encabezado
            pdf.setFillColor(color_texto)
            font_name = get_safe_font_name(fuente, bold=True)
            pdf.setFont(font_name, tamano_fuente)
            texto_x = x_actual + ancho_col / 2
            texto_y = y_actual + (alto_encabezado - tamano_fuente) / 2
            pdf.drawCentredString(texto_x, texto_y, str(encabezado)[:30])  # Limitar longitud
            
            x_actual += ancho_col
    
    # Dibujar filas de datos
    font_name_body = get_safe_font_name(fuente)
    pdf.setFont(font_name_body, tamano_fuente)
    for row_idx, fila in enumerate(filas_datos):
        y_actual -= alto_fila
        
        # Verificar si excedemos el alto máximo
        if y_inicio - y_actual > alto_maximo:
            break
        
        x_actual = x
        
        # Determinar color de fondo
        if estilo_sombreado == "alternado":
            bg_color = color_par if row_idx % 2 == 0 else color_impar
        elif estilo_sombreado == "ninguno":
            bg_color = None
        else:
            bg_color = None
        
        for col_idx, celda in enumerate(fila[:num_columnas]):
            ancho_col = anchos_columnas_pts[col_idx] if col_idx < len(anchos_columnas_pts) else anchos_columnas_pts[0]
            
            # Dibujar fondo
            if bg_color:
                pdf.setFillColor(bg_color)
                pdf.rect(x_actual, y_actual, ancho_col, alto_fila, fill=True, stroke=False)
            
            # Dibujar bordes
            if tipo_borde == "todos":
                pdf.setStrokeColor(color_borde)
                pdf.setLineWidth(grosor_borde)
                pdf.rect(x_actual, y_actual, ancho_col, alto_fila, fill=False, stroke=True)
            elif tipo_borde == "horizontal":
                pdf.setStrokeColor(color_borde)
                pdf.setLineWidth(grosor_borde)
                pdf.line(x_actual, y_actual, x_actual + ancho_col, y_actual)
            elif tipo_borde == "exterior":
                pdf.setStrokeColor(color_borde)
                pdf.setLineWidth(grosor_borde)
                # Solo dibujar bordes exteriores
                if col_idx == 0:  # Borde izquierdo
                    pdf.line(x_actual, y_actual, x_actual, y_actual + alto_fila)
                if col_idx == num_columnas - 1:  # Borde derecho
                    pdf.line(x_actual + ancho_col, y_actual, x_actual + ancho_col, y_actual + alto_fila)
                if row_idx == len(filas_datos) - 1:  # Borde inferior
                    pdf.line(x_actual, y_actual, x_actual + ancho_col, y_actual)
            
            # Dibujar texto de la celda
            pdf.setFillColor(color_texto)
            texto_x = x_actual + 2  # Pequeño padding izquierdo
            texto_y = y_actual + (alto_fila - tamano_fuente) / 2
            
            # Truncar texto si es muy largo
            texto_celda = str(celda) if celda is not None else ""
            max_chars = int(ancho_col / (tamano_fuente * 0.6))  # Aproximación
            if len(texto_celda) > max_chars:
                texto_celda = texto_celda[:max_chars-2] + ".."
            
            pdf.drawString(texto_x, texto_y, texto_celda)
            
            x_actual += ancho_col
    
    # Si no hay datos, mostrar mensaje
    if not filas_datos:
        y_centro = y_inicio - alto_maximo / 2
        pdf.setFillColor("#666666")
        pdf.setFont("Helvetica", 10)
        if script_name:
            pdf.drawCentredString(x + ancho_maximo / 2, y_centro, f"Tabla: {script_name} (sin datos)")
        else:
            pdf.drawCentredString(x + ancho_maximo / 2, y_centro, "Tabla sin script asignado")


def draw_multilevel_table(pdf, table_data, page_height, data_source, biblioteca_tablas_path=None):
    """
    Dibuja una tabla multinivel en el PDF con título, encabezados agrupados y subcolumnas.
    
    Args:
        pdf: Objeto canvas de ReportLab
        table_data: Diccionario con datos de la tabla (incluyendo configuración multinivel)
        page_height: Altura total de la página en puntos
        data_source: Datos de origen para la tabla
        biblioteca_tablas_path: Ruta a la biblioteca de scripts de tablas
    """
    # Extraer geometría
    x = table_data["geometria"]["x"] * CM_TO_POINTS
    y = table_data["geometria"]["y"] * CM_TO_POINTS
    ancho_maximo = table_data["geometria"]["ancho_maximo"] * CM_TO_POINTS
    alto_maximo = table_data["geometria"]["alto_maximo"] * CM_TO_POINTS
    
    # Extraer estructura multinivel
    multinivel = table_data.get("multinivel", {})
    titulo_config = multinivel.get("titulo", {})
    columnas_config = multinivel.get("columnas", {})
    subcolumnas_config = multinivel.get("subcolumnas", {})
    indice_config = multinivel.get("indice", {})
    sombreado_config = multinivel.get("sombreado", {})
    bordes_config = multinivel.get("bordes", {})
    tipografia_config = multinivel.get("tipografia", {})
    
    # Configuración de título
    titulo_activo = titulo_config.get("activo", True)
    titulo_texto = titulo_config.get("texto", "")
    titulo_color = titulo_config.get("color_fondo", "#D9EAD3")
    
    # Configuración de columnas (antes llamado grupos)
    num_columnas_ml = columnas_config.get("num_columnas", 5)
    columnas_color = columnas_config.get("color_fondo", "#FFF2CC")
    
    # Configuración de índice
    indice_etiqueta = indice_config.get("etiqueta", "Prof.")
    indice_ancho = indice_config.get("ancho", 2.0) * CM_TO_POINTS
    
    # Configuración de subcolumnas
    subcolumnas_activo = subcolumnas_config.get("activo", True)
    num_subcolumnas = subcolumnas_config.get("num_subcolumnas", 2) if subcolumnas_activo else 1
    etiquetas_subcolumnas = subcolumnas_config.get("etiquetas", ["A", "B"])
    subcolumnas_color = subcolumnas_config.get("color_fondo", "#FCE5CD")
    
    # Patrón de sombreado
    patron_colores = sombreado_config.get("patron", ["#ffffff", "#f8f9fa"])
    
    # Configuración de bordes multinivel (prioridad sobre estilo general)
    tipo_borde = bordes_config.get("tipo", "todos")
    grosor_borde = bordes_config.get("grosor", 1)
    color_borde = bordes_config.get("color", "#333333")
    
    # Tipografía multinivel
    alto_fila = tipografia_config.get("alto_fila", 0.5) * CM_TO_POINTS
    tamano_fuente = tipografia_config.get("tamano_fuente", 8)
    alto_encabezado = 0.7 * CM_TO_POINTS  # Valor por defecto para encabezados
    
    fuente = "Helvetica"
    color_texto = "#333333"
    
    # Obtener datos del script
    script_name = table_data.get("configuracion", {}).get("script", "")
    raw_params = table_data.get("configuracion", {}).get("parametros", {})
    params = resolve_placeholders(raw_params, data_source)
    
    # Intentar obtener datos del script
    tabla_datos = None
    if script_name and biblioteca_tablas_path:
        try:
            if not script_name.endswith('.py'):
                script_name_py = script_name + '.py'
            else:
                script_name_py = script_name
                
            script_path = biblioteca_tablas_path / script_name_py
            if not script_path.exists():
                script_basename = Path(script_name).stem
                script_path = biblioteca_tablas_path / script_basename / script_name_py
            
            if script_path.exists():
                module = load_module_dynamically(str(script_path))
                if module:
                    main_func_name = Path(script_path).stem
                    if hasattr(module, main_func_name):
                        main_function = getattr(module, main_func_name)
                        tabla_datos = main_function(data_source, params)
        except Exception as e:
            print(f"Error al obtener datos de tabla multinivel: {str(e)}")
    
    # Si no hay datos, crear datos de ejemplo
    if tabla_datos is None:
        # Generar datos de ejemplo para tabla multinivel
        etiquetas_grupos = [f"Col {i+1}" for i in range(num_columnas_ml)]
        filas = []
        for r in range(5):  # 5 filas de ejemplo
            fila_datos = {"indice": f"{(r+1)*0.5:.2f}"}
            fila_datos["valores"] = [round(r + i * 0.1, 2) for i in range(num_columnas_ml * num_subcolumnas)]
            filas.append(fila_datos)
        tabla_datos = {"encabezados_nivel_1": etiquetas_grupos, "filas": filas}
    
    # Calcular anchos de columna usando el ancho de índice configurado
    ancho_grupos = ancho_maximo - indice_ancho
    ancho_por_grupo = ancho_grupos / num_columnas_ml
    ancho_por_subcolumna = ancho_por_grupo / num_subcolumnas
    
    # Posición inicial (ReportLab origen en esquina inferior izquierda)
    y_inicio = page_height - y
    y_actual = y_inicio
    
    # ========== DIBUJAR FILA DE TÍTULO ==========
    if titulo_activo and titulo_texto:
        y_actual -= alto_encabezado
        pdf.setFillColor(titulo_color)
        pdf.rect(x, y_actual, ancho_maximo, alto_encabezado, fill=True, stroke=False)
        
        # Borde del título
        if tipo_borde in ["todos", "exterior"]:
            pdf.setStrokeColor(color_borde)
            pdf.setLineWidth(grosor_borde)
            pdf.rect(x, y_actual, ancho_maximo, alto_encabezado, fill=False, stroke=True)
        
        # Texto del título centrado
        pdf.setFillColor(color_texto)
        font_name_title = get_safe_font_name(fuente, bold=True)
        pdf.setFont(font_name_title, tamano_fuente + 1)
        texto_y = y_actual + (alto_encabezado - tamano_fuente) / 2
        pdf.drawCentredString(x + ancho_maximo / 2, texto_y, titulo_texto[:80])
    
    # ========== DIBUJAR ENCABEZADOS NIVEL 1 (COLUMNAS) ==========
    y_actual -= alto_encabezado
    x_actual = x + indice_ancho  # Dejar espacio para columna de índice
    
    # Celda vacía sobre la columna de índice
    pdf.setFillColor(columnas_color)
    pdf.rect(x, y_actual, indice_ancho, alto_encabezado, fill=True, stroke=False)
    if tipo_borde == "todos":
        pdf.setStrokeColor(color_borde)
        pdf.setLineWidth(grosor_borde)
        pdf.rect(x, y_actual, indice_ancho, alto_encabezado, fill=False, stroke=True)
    
    # Obtener etiquetas de columnas (desde script o generadas)
    encabezados_nivel_1 = tabla_datos.get("encabezados_nivel_1", [f"Col {i+1}" for i in range(num_columnas_ml)])
    
    for grupo_idx in range(num_columnas_ml):
        # Fondo del grupo
        pdf.setFillColor(columnas_color)
        pdf.rect(x_actual, y_actual, ancho_por_grupo, alto_encabezado, fill=True, stroke=False)
        
        # Borde del grupo
        if tipo_borde == "todos":
            pdf.setStrokeColor(color_borde)
            pdf.setLineWidth(grosor_borde)
            pdf.rect(x_actual, y_actual, ancho_por_grupo, alto_encabezado, fill=False, stroke=True)
        
        # Texto del grupo centrado
        pdf.setFillColor(color_texto)
        font_name_header = get_safe_font_name(fuente, bold=True)
        pdf.setFont(font_name_header, tamano_fuente)
        texto_y = y_actual + (alto_encabezado - tamano_fuente) / 2
        etiqueta = encabezados_nivel_1[grupo_idx] if grupo_idx < len(encabezados_nivel_1) else f"C{grupo_idx+1}"
        pdf.drawCentredString(x_actual + ancho_por_grupo / 2, texto_y, str(etiqueta)[:15])
        
        x_actual += ancho_por_grupo
    
    # ========== DIBUJAR ENCABEZADOS NIVEL 2 (SUBCOLUMNAS) ==========
    if subcolumnas_activo and num_subcolumnas > 1:
        y_actual -= alto_encabezado * 0.7  # Subcolumnas un poco más bajas
        x_actual = x + indice_ancho
        
        # Etiqueta de columna de índice
        pdf.setFillColor(subcolumnas_color)
        pdf.rect(x, y_actual, indice_ancho, alto_encabezado * 0.7, fill=True, stroke=False)
        if tipo_borde == "todos":
            pdf.setStrokeColor(color_borde)
            pdf.setLineWidth(grosor_borde)
            pdf.rect(x, y_actual, indice_ancho, alto_encabezado * 0.7, fill=False, stroke=True)
        pdf.setFillColor(color_texto)
        font_name_sub = get_safe_font_name(fuente, bold=True)
        pdf.setFont(font_name_sub, tamano_fuente - 1)
        texto_y = y_actual + (alto_encabezado * 0.7 - tamano_fuente) / 2
        pdf.drawCentredString(x + indice_ancho / 2, texto_y, indice_etiqueta)
        
        # Dibujar subcolumnas para cada grupo
        for grupo_idx in range(num_columnas_ml):
            for sub_idx in range(num_subcolumnas):
                # Fondo de subcolumna
                pdf.setFillColor(subcolumnas_color)
                pdf.rect(x_actual, y_actual, ancho_por_subcolumna, alto_encabezado * 0.7, fill=True, stroke=False)
                
                # Borde
                if tipo_borde == "todos":
                    pdf.setStrokeColor(color_borde)
                    pdf.setLineWidth(grosor_borde)
                    pdf.rect(x_actual, y_actual, ancho_por_subcolumna, alto_encabezado * 0.7, fill=False, stroke=True)
                
                # Etiqueta de subcolumna
                pdf.setFillColor(color_texto)
                # Fuente normal para sub
                font_name_sub_normal = get_safe_font_name(fuente)
                pdf.setFont(font_name_sub_normal, tamano_fuente - 1)
                texto_y = y_actual + (alto_encabezado * 0.7 - tamano_fuente) / 2
                etiqueta_sub = etiquetas_subcolumnas[sub_idx] if sub_idx < len(etiquetas_subcolumnas) else chr(65 + sub_idx)
                pdf.drawCentredString(x_actual + ancho_por_subcolumna / 2, texto_y, str(etiqueta_sub))
                
                x_actual += ancho_por_subcolumna
    
    # ========== DIBUJAR FILAS DE DATOS ==========
    filas_datos = tabla_datos.get("filas", [])
    
    font_name_body = get_safe_font_name(fuente)
    pdf.setFont(font_name_body, tamano_fuente)
    for row_idx, fila in enumerate(filas_datos):
        y_actual -= alto_fila
        
        # Verificar límite de altura
        if y_inicio - y_actual > alto_maximo:
            break
        
        x_actual = x
        
        # Color de fondo alternado usando patrón
        color_idx = row_idx % len(patron_colores)
        bg_color = patron_colores[color_idx]
        
        # Columna de índice
        indice = fila.get("indice", fila.get("profundidad", row_idx + 1))
        pdf.setFillColor(bg_color)
        pdf.rect(x_actual, y_actual, indice_ancho, alto_fila, fill=True, stroke=False)
        if tipo_borde == "todos":
            pdf.setStrokeColor(color_borde)
            pdf.setLineWidth(grosor_borde)
            pdf.rect(x_actual, y_actual, indice_ancho, alto_fila, fill=False, stroke=True)
        pdf.setFillColor(color_texto)
        texto_y = y_actual + (alto_fila - tamano_fuente) / 2
        pdf.drawCentredString(x_actual + indice_ancho / 2, texto_y, str(indice))
        
        x_actual += indice_ancho
        
        # Valores de datos
        valores = fila.get("valores", [])
        for val_idx, valor in enumerate(valores):
            if val_idx >= num_columnas_ml * num_subcolumnas:
                break
                
            pdf.setFillColor(bg_color)
            pdf.rect(x_actual, y_actual, ancho_por_subcolumna, alto_fila, fill=True, stroke=False)
            if tipo_borde == "todos":
                pdf.setStrokeColor(color_borde)
                pdf.setLineWidth(grosor_borde)
                pdf.rect(x_actual, y_actual, ancho_por_subcolumna, alto_fila, fill=False, stroke=True)
            
            pdf.setFillColor(color_texto)
            texto_y = y_actual + (alto_fila - tamano_fuente) / 2
            texto_valor = str(valor) if valor is not None else ""
            pdf.drawCentredString(x_actual + ancho_por_subcolumna / 2, texto_y, texto_valor[:10])
            
            x_actual += ancho_por_subcolumna
    
    # Si no hay filas, mostrar mensaje
    if not filas_datos:
        y_centro = y_inicio - alto_maximo / 2
        pdf.setFillColor("#666666")
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(x + ancho_maximo / 2, y_centro, f"Tabla multinivel: {script_name} (sin datos)")


def generate_pdf_from_template(template_data, data_source, output_buffer=None,
                               biblioteca_path=None, biblioteca_graficos_path=None,
                               biblioteca_tablas_path=None):
    """
    Genera un PDF completo a partir de una plantilla JSON

    Args:
        template_data: Diccionario con los datos de la plantilla
        data_source: Datos de origen para los gráficos
        output_buffer: Buffer de salida (opcional, si no se proporciona se crea uno)
        biblioteca_path: Ruta base a la biblioteca de plantillas (opcional)
        biblioteca_graficos_path: Ruta a la biblioteca de gráficos (opcional)
        biblioteca_tablas_path: Ruta a la biblioteca de scripts de tablas (opcional)
    """
    if output_buffer is None:
        output_buffer = io.BytesIO()

    # Crear el PDF
    pdf = canvas.Canvas(output_buffer)

    # Definir rutas de bibliotecas - usar la ruta específica proporcionada o la predeterminada
    if biblioteca_graficos_path is None:
        biblioteca_graficos_path = Path("biblioteca_graficos")
    
    # Ruta a biblioteca de tablas (separada de gráficos)
    if biblioteca_tablas_path is None:
        biblioteca_tablas_path = Path("biblioteca_tablas")

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
                draw_text(pdf, elemento, page_height, data_source)
            elif elemento["tipo"] == "imagen":
                draw_image(pdf, elemento, page_height, plantilla_dir, biblioteca_path)
            elif elemento["tipo"] == "grafico":
                draw_graph(pdf, elemento, page_height, data_source, biblioteca_graficos_path)
            elif elemento["tipo"] == "tabla":
                # Verificar si es tabla multinivel
                tipo_tabla = elemento.get("configuracion", {}).get("tipo_tabla", "simple")
                if tipo_tabla == "multinivel":
                    draw_multilevel_table(pdf, elemento, page_height, data_source, biblioteca_tablas_path)
                else:
                    # Para tablas simples, usamos biblioteca_tablas_path
                    draw_table(pdf, elemento, page_height, data_source, biblioteca_tablas_path)

    # Guardar el PDF
    pdf.save()
    output_buffer.seek(0)

    return output_buffer
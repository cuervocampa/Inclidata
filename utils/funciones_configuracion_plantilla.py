#utils\funciones_configuracion_plantilla

# utils/funciones_configuracion_plantilla.py
from dash import html

# Constantes
A4_PORTRAIT_WIDTH = 595  # Ancho A4 vertical en puntos (21 cm)
A4_PORTRAIT_HEIGHT = 842  # Alto A4 vertical en puntos (29.7 cm)
A4_LANDSCAPE_WIDTH = 842  # Ancho A4 horizontal en puntos (29.7 cm)
A4_LANDSCAPE_HEIGHT = 595  # Alto A4 horizontal en puntos (21 cm)
SCALE_FACTOR = 0.8  # Factor de escala para visualizar en pantalla
CM_TO_POINTS = 28.35  # 1 cm = 28.35 puntos
MM_TO_POINTS = 2.835  # 1 mm = 2.835 puntos


def actualizar_orientacion_y_reglas(orientation):
    """
    Actualiza la orientación del canvas y las reglas según la orientación seleccionada.

    Args:
        orientation (str): Orientación del canvas ('portrait' o 'landscape')

    Returns:
        tuple: Contiene los siguientes elementos:
            - canvas_style (dict): Estilo del canvas
            - horizontal_ruler_style (dict): Estilo de la regla horizontal
            - horizontal_marks (list): Marcas de la regla horizontal
            - vertical_ruler_style (dict): Estilo de la regla vertical
            - vertical_marks (list): Marcas de la regla vertical
    """
    if orientation == "landscape":
        # Orientación horizontal (landscape)
        canvas_width = A4_LANDSCAPE_WIDTH
        canvas_height = A4_LANDSCAPE_HEIGHT

        # Calculamos el número de cm en el ancho (29.7) y alto (21) para A4 apaisado
        width_cm = round(A4_LANDSCAPE_WIDTH / CM_TO_POINTS)
        height_cm = round(A4_LANDSCAPE_HEIGHT / CM_TO_POINTS)
    else:
        # Orientación vertical (portrait)
        canvas_width = A4_PORTRAIT_WIDTH
        canvas_height = A4_PORTRAIT_HEIGHT

        # Calculamos el número de cm en el ancho (21) y alto (29.7) para A4 vertical
        width_cm = round(A4_PORTRAIT_WIDTH / CM_TO_POINTS)
        height_cm = round(A4_PORTRAIT_HEIGHT / CM_TO_POINTS)

    # Regla horizontal - marcas solo en cm, números cada 5 cm
    horizontal_marks = []
    for i in range(width_cm + 1):  # +1 para incluir el 0
        # Cada cm
        tick_height = "8px" if i % 5 == 0 else "5px"
        tick_width = "1px"

        # Añadimos etiqueta numérica cada 5 cm
        label = f"{i}" if i % 5 == 0 and i > 0 else ""
        font_size = "9px" if i % 5 == 0 else "0px"

        horizontal_marks.append(
            html.Div(
                className="ruler-mark",
                style={
                    "position": "absolute",
                    "top": "0px",
                    "left": f"{i * CM_TO_POINTS * SCALE_FACTOR}px",
                    "height": tick_height,
                    "width": tick_width,
                    "backgroundColor": "#555",
                    "fontSize": font_size,
                    "textAlign": "center",
                    "paddingTop": "9px",
                },
                children=label
            )
        )

    # Regla vertical - marcas solo en cm, números cada 5 cm
    vertical_marks = []
    for i in range(height_cm + 1):  # +1 para incluir el 0
        # Cada cm
        tick_width = "8px" if i % 5 == 0 else "5px"
        tick_height = "1px"

        # Añadimos etiqueta numérica cada 5 cm
        label = f"{i}" if i % 5 == 0 and i > 0 else ""
        font_size = "9px" if i % 5 == 0 else "0px"

        vertical_marks.append(
            html.Div(
                className="ruler-mark",
                style={
                    "position": "absolute",
                    "left": "0px",
                    "top": f"{i * CM_TO_POINTS * SCALE_FACTOR}px",
                    "width": tick_width,
                    "height": tick_height,
                    "backgroundColor": "#555",
                    "fontSize": font_size,
                    "textAlign": "right",
                    "paddingRight": "9px",
                    "lineHeight": "8px"
                },
                children=label
            )
        )

    # Estilos actualizados
    canvas_style = {
        "width": f"{canvas_width * SCALE_FACTOR}px",
        "height": f"{canvas_height * SCALE_FACTOR}px",
        "background": "white",
        "border": "1px solid #ccc",
        "position": "relative",
        "boxShadow": "0 4px 8px rgba(0,0,0,0.1)"
    }

    horizontal_ruler_style = {
        "width": f"{canvas_width * SCALE_FACTOR}px",
        "height": "20px",
        "background": "#f5f5f5",
        "position": "relative",
        "borderBottom": "1px solid #ccc"
    }

    vertical_ruler_style = {
        "height": f"{canvas_height * SCALE_FACTOR}px",
        "width": "20px",
        "background": "#f5f5f5",
        "position": "relative",
        "borderRight": "1px solid #ccc"
    }

    return canvas_style, horizontal_ruler_style, horizontal_marks, vertical_ruler_style, vertical_marks
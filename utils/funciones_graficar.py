# utils/funciones_graficar.py

import re
from datetime import datetime
import math
import plotly.graph_objects as go
import numpy as np
import os
import sys
import importlib.util
import traceback
import dash_mantine_components as dmc
from dash import html

# Funciones para graficar


"""
def get_color_for_index__(index, color_scheme="multicromo", total_colors=10):
    
    Devuelve un color para un índice determinado según el esquema de colores proporcionado.
    Args:
        index (int): índice del color.
        color_scheme (str): esquema de colores a usar (por defecto "multicromo").
        total_colors (int): número total de colores.
    Returns:
        str: Color en formato hexadecimal.
    
    if color_scheme == "monocromo":
        # Degradado de azul (de claro a oscuro)
        cmap = plt.get_cmap('Blues', total_colors)
        color_rgb = cmap((total_colors - 1 - index) / (total_colors - 1))[:3]  # Invertir el índice para que los más antiguos sean más claros
        # Convertir RGB a formato hexadecimal
        color_hex = "#%02x%02x%02x" % (int(color_rgb[0] * 255), int(color_rgb[1] * 255), int(color_rgb[2] * 255))
        return color_hex
    else:
        # Multicromo: Usar la paleta existente de Plotly
        return color_palette[index % len(color_palette)]


def get_color_for_index_(index):
    
    Devuelve un color de la paleta de colores de Plotly basado en el índice.
    Args:
        index (int): índice del color.
    Returns:
        str: Color en formato hexadecimal.
    
    # Definir una paleta de colores para las series
    color_palette = pcolors.qualitative.Plotly
    return color_palette[index % len(color_palette)]
"""

def obtener_fecha_desde_slider(slider_value):
    """Extrae la fecha seleccionada del valor mostrado en el slider"""
    patron = r'Fecha seleccionada: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
    resultado = re.search(patron, slider_value)
    if resultado:
        fecha_hora = resultado.group(1)
        dt_obj = datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M:%S")
        return dt_obj.strftime("%Y-%m-%dT%H:%M:%S")
    return None


def obtener_color_para_fecha(fecha, fechas_colores):
    """Obtiene el color asociado a una fecha desde el diccionario de colores"""
    item_correspondiente = next((item for item in fechas_colores if item['value'] == fecha), None)
    if item_correspondiente:
        return item_correspondiente['style']['color']
    return 'gray'  # Color por defecto si no se encuentra


def extraer_datos_fecha(fecha, data, eje):
    """Extrae y procesa los datos de cálculo para una fecha específica"""
    if fecha not in data or "calc" not in data[fecha]:
        return None

    calc_data = data[fecha]["calc"]

    # Si el eje es "depth", construimos la lista según la lógica especificada
    # esto es debido a que puede haber recrecimientos del tubo, "depth" sólo vale dentro de las campañas de la misma ref
    if eje == "depth":
        # Extraer todos los valores de index
        #indices = [punto["index"] for punto in calc_data]
        cota_abs = [punto["cota_abs"] for punto in calc_data]

        paso = abs(cota_abs[1] - cota_abs[0])

        # Construir la lista eje_Y
        eje_Y = []
        for i in range(len(cota_abs)):
            eje_Y.append(paso * i)

    else:
        # Si no es "depth", extraer directamente los valores del eje especificado
        eje_Y = [punto[eje] for punto in calc_data]

    # Extraer el resto de listas de datos
    return {
        'eje_Y': eje_Y,
        'desp_a': [punto["desp_a"] for punto in calc_data],
        'desp_b': [punto["desp_b"] for punto in calc_data],
        'incr_dev_a': [punto["incr_dev_a"] for punto in calc_data],
        'incr_dev_b': [punto["incr_dev_b"] for punto in calc_data],
        'incr_dev_abs_a': [punto["incr_dev_abs_a"] for punto in calc_data],
        'incr_dev_abs_b': [punto["incr_dev_abs_b"] for punto in calc_data],
        'checksum_a': [punto["checksum_a"] for punto in calc_data],
        'checksum_b': [punto["checksum_b"] for punto in calc_data],
        'desp_total': [round(math.sqrt(punto["desp_a"] ** 2 + punto["desp_b"] ** 2), 2) for punto in calc_data]
    }


def add_traza(fig, x_data, y_data, nombre, color, grosor=2, opacidad=0.7, grupo=None):
    """
    Añade una traza a la figura con los parámetros especificados.

    Args:
        fig: Figura a la que añadir la traza
        x_data: Datos para el eje X
        y_data: Datos para el eje Y
        nombre: Nombre de la traza
        color: Color para la traza
        grosor: Grosor de la línea
        opacidad: Opacidad de la traza
        grupo: Grupo de leyenda (opcional)
    """
    grupo_leyenda = grupo if grupo else nombre.split(" - ")[0] if " - " in nombre else nombre

    fig.add_trace(go.Scatter(
        x=x_data,
        y=y_data,
        mode="lines",
        name=nombre,
        line=dict(color=color, width=grosor),
        legendgroup=grupo_leyenda,
        opacity=opacidad
    ))
    return fig


def interpolar_def_tubo(cota_abs_tubo, cota_abs_umbral, def_umbral):
    """
    Interpola, para cada cota de tubo, la deflexión correspondiente
    a partir de la curva (def_umbral vs cota_abs_umbral).

    Parámetros
    ----------
    cota_abs_tubo : list of float
        Lista de cotas absolutas del tubo (puede ser progresión aritmética).
    cota_abs_umbral : list of float
        Lista de cotas absolutas del umbral (monótonamente decreciente).
    def_umbral : list of float
        Lista de deflexiones del umbral, misma longitud que cota_abs_umbral.

    Devuelve
    -------
    def_tubo : list of float
        Lista de deflexiones del tubo interpoladas en cada cota de tubo.
    """
    # Convertir a arrays NumPy
    cota_arr = np.array(cota_abs_umbral)
    def_arr = np.array(def_umbral)

    # Ordenar los puntos por cota ascendente (requisito de np.interp)
    idx = np.argsort(cota_arr)
    cota_sorted = cota_arr[idx]
    def_sorted = def_arr[idx]

    # Interpolar: para cada valor de cota_abs_tubo,
    # hallar la deflexión correspondiente
    def_tubo_arr = np.interp(cota_abs_tubo, cota_sorted, def_sorted)

    # Devolver como lista de Python
    return def_tubo_arr.tolist()


def load_module_dynamically(module_path, module_name):
    """
    Carga dinámicamente un módulo Python desde una ruta específica.

    Args:
        module_path (str): Ruta al archivo Python
        module_name (str): Nombre del módulo

    Returns:
        module: El módulo cargado o None si no se pudo cargar
    """
    try:
        print(f"Intentando cargar módulo {module_name} desde {module_path}")
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None:
            print(f"No se pudo obtener spec para {module_path}")
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        print(f"Módulo {module_name} cargado exitosamente")
        return module
    except Exception as e:
        print(f"Error al cargar el módulo {module_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def cargar_valores_actuales(data, eje, orden, color_scheme, escala_desplazamiento, escala_incremento,
                          valor_positivo_desplazamiento, valor_negativo_desplazamiento,
                          valor_positivo_incremento, valor_negativo_incremento,
                          fecha_inicial, fecha_final, total_camp, ultimas_camp, cadencia_dias,
                            leyenda_umbrales=None ):
    """
    Centraliza la carga de valores actuales de la interfaz para ser usados con $CURRENT
    """
    return {
        'nombre_sensor': data.get("info", {}).get("nombre", "SENSOR-001") if data else "SENSOR-001",
        'sensor': "desp_a",  # Valor por defecto
        'fecha_inicial': fecha_inicial,
        'fecha_final': fecha_final,
        'total_camp': total_camp,
        'ultimas_camp': ultimas_camp,
        'cadencia_dias': cadencia_dias,
        'color_scheme': color_scheme,
        'escala_desplazamiento': escala_desplazamiento,
        'escala_incremento': escala_incremento,
        'valor_positivo_desplazamiento': valor_positivo_desplazamiento,
        'valor_negativo_desplazamiento': valor_negativo_desplazamiento,
        'valor_positivo_incremento': valor_positivo_incremento,
        'valor_negativo_incremento': valor_negativo_incremento,
        'eje': eje,
        'orden': orden,
        'ancho_cm': 21,  # Ancho estándar A4
        'alto_cm': 29.7,  # Alto estándar A4
        'dpi': 100,
        'leyenda_umbrales': leyenda_umbrales if leyenda_umbrales else {}
    }


# Función auxiliar para obtener parámetros por defecto de un script
def obtener_parametros_por_defecto(script_name, current_values):
    """
    Obtiene los parámetros por defecto de un script específico.

    Args:
        script_name (str): Nombre del script (sin extensión .py)
        current_values (dict): Valores actuales de la interfaz

    Returns:
        dict: Parámetros por defecto para el script
    """
    if not script_name:
        return {}

    try:
        # Ruta al script
        script_path = os.path.join("biblioteca_graficos", script_name, f"{script_name}.py")

        if not os.path.exists(script_path):
            print(f"Script no encontrado: {script_path}")
            return {}

        # Añadir el directorio del script al path
        script_dir = os.path.dirname(script_path)
        import sys
        sys.path.insert(0, script_dir)

        try:
            # Cargar el módulo dinámicamente
            import importlib.util
            module_spec = importlib.util.spec_from_file_location(script_name, script_path)

            if module_spec:
                module = importlib.util.module_from_spec(module_spec)
                module_spec.loader.exec_module(module)

                # Buscar función get_default_params
                if hasattr(module, 'get_default_params'):
                    try:
                        parametros_script = module.get_default_params()
                        print(f"Parámetros obtenidos de {script_name}.get_default_params(): {parametros_script}")
                        return parametros_script
                    except Exception as e:
                        print(f"Error al ejecutar get_default_params en {script_name}: {e}")

                # Si no hay función, usar parámetros por defecto estándar
                print(f"No se encontró get_default_params en {script_name}, usando valores $CURRENT")

        finally:
            # Restaurar el path
            if script_dir in sys.path:
                sys.path.remove(script_dir)

    except Exception as e:
        print(f"Error al cargar script {script_name}: {e}")

    # Fallback: parámetros estándar con $CURRENT
    return {
        'nombre_sensor': "$CURRENT",
        'sensor': "$CURRENT",
        'fecha_inicial': "$CURRENT",
        'fecha_final': "$CURRENT",
        'total_camp': "$CURRENT",
        'ultimas_camp': "$CURRENT",
        'cadencia_dias': "$CURRENT",
        'color_scheme': "$CURRENT",
        'escala_desplazamiento': "$CURRENT",
        'escala_incremento': "$CURRENT",
        'valor_positivo_desplazamiento': "$CURRENT",
        'valor_negativo_desplazamiento': "$CURRENT",
        'valor_positivo_incremento': "$CURRENT",
        'valor_negativo_incremento': "$CURRENT",
        'eje': "$CURRENT",
        'orden': "$CURRENT",
        'ancho_cm': 21,
        'alto_cm': 29.7,
        'dpi': 100
    }


# Función auxiliar para generar la sección de un gráfico individual
def generar_seccion_grafico(num_pagina, nombre_elemento, elemento, scripts_disponibles, current_values):
    """
    Genera la sección de configuración para un gráfico individual.

    Args:
        num_pagina (str): Número de página
        nombre_elemento (str): Nombre del elemento
        elemento (dict): Datos del elemento
        scripts_disponibles (list): Lista de scripts disponibles
        current_values (dict): Valores actuales de la interfaz

    Returns:
        list: Componentes de la sección del gráfico
    """
    configuracion = elemento.get("configuracion", {})
    script_valor = configuracion.get("script", "")
    parametros_json = configuracion.get("parametros", {})

    # Eliminar la extensión .py si está presente
    if script_valor.endswith('.py'):
        script_valor_sin_extension = script_valor[:-3]
    else:
        script_valor_sin_extension = script_valor

    # Verificar si el script existe y está en opciones
    script_path = os.path.join("biblioteca_graficos", script_valor_sin_extension, f"{script_valor_sin_extension}.py")
    script_existe = os.path.exists(script_path)
    script_en_opciones = any(d['value'] == script_valor_sin_extension for d in scripts_disponibles)
    valor_selector = script_valor_sin_extension if script_en_opciones else None

    # Generar mensaje de estado
    if script_existe:
        script_status = f"✓ Script encontrado: {script_valor_sin_extension}.py"
        status_color = "green"
    else:
        script_status = f"❌ Script no encontrado: {script_valor_sin_extension}.py"
        status_color = "red"

    # Contenido del accordion
    contenido_acordeon = []

    # Selector de script
    contenido_acordeon.append(
        dmc.Group([
            dmc.Text("Script:", weight="bold", style={"width": "15%"}),
            html.Div([
                dmc.Select(
                    id={"type": "script-grafico", "pagina": num_pagina, "elemento": nombre_elemento},
                    value=valor_selector,
                    data=scripts_disponibles,
                    placeholder="Seleccione un script",
                    style={"width": "100%", "marginBottom": "5px"}
                ),
                dmc.Text(script_status, color=status_color, size="sm")
            ], style={"width": "85%"})
        ], style={"marginBottom": "15px"})
    )

    # Contenedor para parámetros (se actualizará dinámicamente)
    contenido_acordeon.append(
        html.Div(
            id={"type": "parametros-container", "pagina": num_pagina, "elemento": nombre_elemento},
            children=generar_campos_parametros(num_pagina, nombre_elemento, parametros_json, current_values)
        )
    )

    return contenido_acordeon


def generar_campos_parametros(num_pagina, nombre_elemento, parametros_json, current_values):
    """
    Genera los campos de parámetros para un gráfico.

    Args:
        num_pagina (str): Número de página
        nombre_elemento (str): Nombre del elemento
        parametros_json (dict): Parámetros del JSON
        current_values (dict): Valores actuales de la interfaz

    Returns:
        list: Lista de componentes para los parámetros
    """
    if not parametros_json:
        return [
            dmc.Stack([
                dmc.Text("No hay parámetros configurados", color="dimmed", style={"padding": "10px 0"}),
                dmc.Button(
                    "Añadir parámetros por defecto",
                    id={"type": "btn-add-params", "pagina": num_pagina, "elemento": nombre_elemento},
                    variant="outline",
                    size="sm",
                    style={"width": "fit-content"}
                )
            ])
        ]

    campos_parametros = [
        dmc.Text("Parámetros:", weight="bold", style={"marginTop": "10px", "marginBottom": "10px"})
    ]

    for param_nombre, param_valor in parametros_json.items():
        # Aplicar sustitución de $CURRENT
        valor_display = param_valor
        if isinstance(param_valor, str) and param_valor == "$CURRENT" and param_nombre in current_values:
            valor_display = current_values[param_nombre]
            valor_display = str(valor_display)
            estilo_campo = {
                "width": "50%",
                "backgroundColor": "#e3f2fd",
                "border": "1px dashed #90caf9"
            }
        else:
            estilo_campo = {"width": "50%"}
            if isinstance(param_valor, bool):
                valor_display = str(param_valor).lower()
            else:
                valor_display = str(param_valor)

        campos_parametros.append(
            dmc.Group([
                dmc.Text(
                    f"[parametros][{param_nombre}]",
                    style={"width": "50%"}
                ),
                dmc.TextInput(
                    id={"type": "param-grafico", "pagina": num_pagina,
                        "elemento": nombre_elemento, "param": param_nombre},
                    value=valor_display,
                    style=estilo_campo
                )
            ], style={"marginBottom": "8px"})
        )

    return campos_parametros


def hex_to_spanish_color(hex_color):
    """
    Convierte un color hexadecimal a nombre en español.
    Mantiene compatibilidad con el sistema existente.
    """
    # Mapeo de colores hex a nombres españoles
    hex_to_spanish = {
        '#3B82F6': 'azul',
        '#EF4444': 'rojo',
        '#10B981': 'verde',
        '#F59E0B': 'amarillo',
        '#8B5CF6': 'violeta',
        '#EC4899': 'rosa',
        '#06B6D4': 'cian',
        '#84CC16': 'lima',
        '#F97316': 'naranja',
        '#6B7280': 'gris',
        '#DC2626': 'rojo_oscuro',
        '#059669': 'verde_esmeralda',
        '#7C3AED': 'purpura',
        '#DB2777': 'rosa_intenso',
        '#0891B2': 'azul_petroleo'
    }

    return hex_to_spanish.get(hex_color, 'azul')  # Azul por defecto


def spanish_to_plotly_dash(tipo_linea):
    """
    Convierte tipos de línea del JSON a formato Plotly.
    """
    linea_mapping = {
        'solid': 'solid',
        'dashed': 'dash',
        'dotted': 'dot',
        'dashdot': 'dashdot',
        'longdash': 'longdash',
        'longdashdot': 'longdashdot'
    }

    return linea_mapping.get(tipo_linea, 'dash')  # Dash por defecto
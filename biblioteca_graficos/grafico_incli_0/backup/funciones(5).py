# funciones.py - Funciones auxiliares para gráficos de inclinometría
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.ticker import AutoMinorLocator
import io
import base64


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
    if not data:
        return []

    # Obtener todas las fechas disponibles (excluyendo claves especiales)
    fechas = [fecha for fecha in data.keys() if fecha != "info" and fecha != "umbrales"]

    if not fechas:
        return []

    try:
        # Convertir fechas a objetos datetime y ordenar
        fechas_dt = sorted([datetime.fromisoformat(fecha) for fecha in fechas])
    except ValueError as e:
        print(f"Error al convertir fechas: {e}")
        return []

    # Si se proporcionaron fechas de inicio y fin, filtrar por rango
    if fecha_inicial and fecha_final:
        try:
            fecha_inicio_dt = datetime.fromisoformat(fecha_inicial)
            fecha_fin_dt = datetime.fromisoformat(fecha_final)
            fechas_dt = [fecha for fecha in fechas_dt if fecha_inicio_dt <= fecha <= fecha_fin_dt]
        except ValueError as e:
            print(f"Error al procesar rango de fechas: {e}")
            return []

    # Convertir de nuevo a formato ISO y ordenar de más reciente a más antigua
    fechas = [fecha.isoformat() for fecha in reversed(fechas_dt)]

    # Seleccionar fechas basadas en parámetros
    fechas_seleccionadas = []

    # Añadir las últimas campañas
    if ultimas_camp > 0 and len(fechas) > 0:
        fechas_seleccionadas.extend(fechas[:min(ultimas_camp, len(fechas))])

    # Añadir campañas adicionales basadas en cadencia
    if cadencia_dias > 0 and len(fechas_seleccionadas) < total_camp and len(fechas) > ultimas_camp:
        try:
            ultima_fecha = datetime.fromisoformat(fechas_seleccionadas[-1])

            for fecha in fechas[ultimas_camp:]:
                fecha_actual = datetime.fromisoformat(fecha)
                diferencia_dias = (ultima_fecha - fecha_actual).days

                if diferencia_dias >= cadencia_dias:
                    fechas_seleccionadas.append(fecha)
                    ultima_fecha = fecha_actual

                if len(fechas_seleccionadas) >= total_camp:
                    break
        except (ValueError, IndexError) as e:
            print(f"Error al procesar cadencia: {e}")

    # Limitar al número total especificado
    return fechas_seleccionadas[:total_camp]


def determinar_fecha_slider(data, fechas_seleccionadas):
    """
    Determina la fecha a destacar (por defecto la última fecha activa).

    Args:
        data (dict): Diccionario con los datos del tubo.
        fechas_seleccionadas (list): Lista de fechas seleccionadas.

    Returns:
        str: Fecha a destacar o None si no hay fechas válidas.
    """
    # Si no hay fechas seleccionadas, devolver None
    if not fechas_seleccionadas or not data:
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
    # Validación de parámetros
    if total_colors <= 0:
        total_colors = 1
    if index < 0:
        index = 0

    if color_scheme == "monocromo":
        # Degradado de azul (de claro a oscuro) - original
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
        # Usar colores predefinidos para esquema multicolor (originales)
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
    if not fechas_seleccionadas:
        return []

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


def obtener_leyenda_umbrales(data, leyenda_umbrales_interfaz=None):
    """
    Obtiene la leyenda de umbrales desde los datos.

    Args:
        data: Datos del tubo
        leyenda_umbrales_interfaz: Colores configurados en la interfaz (opcional)

    Returns:
        dict: Diccionario con umbrales y sus colores
    """
    # Si se proporcionan colores desde la interfaz, usarlos
    if leyenda_umbrales_interfaz and isinstance(leyenda_umbrales_interfaz, dict):
        return leyenda_umbrales_interfaz

    # Si no, generar colores por defecto (código existente)
    from utils.diccionarios import colores_basicos
    from utils.funciones_comunes import asignar_colores

    umbrales_tubo = list(data.get('umbrales', {}).get('deformadas', {}).keys())
    if not umbrales_tubo:
        return {}

    return asignar_colores(umbrales_tubo, colores_basicos)


def obtener_color_para_fecha(fecha, fechas_colores):
    """
    Obtiene el color asociado a una fecha desde el diccionario de colores.

    Args:
        fecha (str): Fecha para la que se busca el color.
        fechas_colores (list): Lista de diccionarios con información de colores por fecha.

    Returns:
        str: Color en formato hexadecimal o nombre.
    """
    if not fechas_colores or not fecha:
        return 'gray'

    item_correspondiente = next((item for item in fechas_colores if item['value'] == fecha), None)
    if item_correspondiente and 'style' in item_correspondiente and 'color' in item_correspondiente['style']:
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
    if not fecha or not data or fecha not in data or "calc" not in data[fecha]:
        return None

    calc_data = data[fecha]["calc"]

    if not calc_data or not isinstance(calc_data, list):
        return None

    try:
        # Si el eje es "depth", construimos la lista según la lógica especificada
        # esto es debido a que puede haber recrecimientos del tubo, "depth" sólo vale dentro de las campañas de la misma ref
        if eje == "depth":
            # Extraer todos los valores de cota_abs
            cota_abs = [punto["cota_abs"] for punto in calc_data if "cota_abs" in punto]

            if len(cota_abs) < 2:
                # Si no hay suficientes puntos, usar paso por defecto
                paso = 1.0
            else:
                # Calcular el paso (diferencia entre cotas consecutivas)
                paso = abs(cota_abs[1] - cota_abs[0])
                if paso == 0:  # Evitar división por cero
                    paso = 1.0

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
    except (KeyError, TypeError, ValueError) as e:
        print(f"Error al extraer datos de fecha {fecha}: {e}")
        return None


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
    if not cota_tubo or not cota_umbral or not def_umbral:
        return []

    if len(cota_umbral) != len(def_umbral):
        print("Error: Las listas de cotas y deformadas de umbral deben tener la misma longitud")
        return []

    try:
        # Crear array de valores conocidos
        x_conocidos = np.array(cota_umbral)
        y_conocidos = np.array(def_umbral)

        # Crear array de valores a interpolar
        x_interpolar = np.array(cota_tubo)

        # Interpolar valores
        y_interpolados = np.interp(x_interpolar, x_conocidos, y_conocidos)

        return y_interpolados.tolist()
    except Exception as e:
        print(f"Error en interpolación: {e}")
        return []


def agregar_umbrales(ax, data, leyenda_umbrales, eje, sensor, fecha_slider, incluir_todos=False):
    """
    Añade umbrales al gráfico y opcionalmente los incluye en la leyenda aunque no se dibujen.
    """
    # Validar parámetros de entrada
    if not ax or not data or not fecha_slider or fecha_slider not in data:
        print(f"DEBUG: Validación falló - ax: {ax is not None}, data: {data is not None}, fecha_slider: {fecha_slider}")
        return

    # Solo agregar umbrales si hay datos en el json
    if 'umbrales' not in data or 'valores' not in data['umbrales']:
        print("DEBUG: No hay datos de umbrales en el JSON")
        return

    # DEBUG: Imprimir información de umbrales
    print(f"DEBUG: leyenda_umbrales recibida: {leyenda_umbrales}")
    print(f"DEBUG: sensor: {sensor}")
    print(f"DEBUG: eje: {eje}")
    print(f"DEBUG: fecha_slider: {fecha_slider}")

    # Variable para rastrear qué deformadas ya se han mostrado
    deformadas_mostradas = set()

    # Determinar qué deformadas corresponden al sensor actual
    if sensor == "desp_a":
        deformadas = [d for d in leyenda_umbrales.keys() if d.endswith("_a")]
    elif sensor == "desp_b":
        deformadas = [d for d in leyenda_umbrales.keys() if d.endswith("_b")]
    else:
        # Para otros tipos de sensores, no mostrar umbrales
        deformadas = []

    print(f"DEBUG: deformadas filtradas para {sensor}: {deformadas}")

    # Agregar cada deformada al gráfico
    for deformada in deformadas:
        # Registrar esta deformada como mostrada
        deformadas_mostradas.add(deformada)

        # Obtener el color
        color_espanol = leyenda_umbrales.get(deformada, "gray")

        # Si el color es "Ninguno", no se grafica esta serie
        if color_espanol == "Ninguno":
            continue

        # Convertir el color a inglés o mantenerlo si es un código hexadecimal
        from utils.diccionarios import colores_ingles
        color = colores_ingles.get(color_espanol, color_espanol)

        # Establecer parámetros de línea (originales)
        grosor = 2

        try:
            # Extraer datos de umbral y prepararlos para graficar
            valores = data['umbrales']['valores']
            if not valores:
                continue

            df = pd.DataFrame(valores)

            # Verificar que las columnas necesarias existen
            if deformada not in df.columns or 'cota_abs' not in df.columns:
                continue

            # Verificar que hay datos válidos en fecha_slider
            if 'calc' not in data[fecha_slider] or not data[fecha_slider]['calc']:
                continue

            # Definir eje_X y eje_Y aquí, antes de usarlos
            if eje == "depth" or eje == "index":
                # Interpolar para index o depth
                cota_tubo = [punto["cota_abs"] for punto in data[fecha_slider]['calc'] if "cota_abs" in punto]
                if not cota_tubo:
                    continue

                cota_umbral = df['cota_abs'].to_list()
                def_umbral = df[deformada].to_list()
                eje_X = interpolar_def_tubo(cota_tubo, cota_umbral, def_umbral)
                if not eje_X:
                    continue
            else:
                # Caso de "cota_abs"
                eje_X = df[deformada].to_list()

            # Definir eje Y según tipo
            if eje == "depth":
                # Construir profundidad
                cota_tubo = [punto["cota_abs"] for punto in data[fecha_slider]['calc'] if "cota_abs" in punto]
                if len(cota_tubo) < 2:
                    paso = 1.0
                else:
                    paso = abs(cota_tubo[1] - cota_tubo[0])
                    if paso == 0:
                        paso = 1.0
                eje_Y = [paso * i for i in range(len(cota_tubo))]
            elif eje == "index":
                # Lista de índice
                eje_Y = [punto["index"] for punto in data[fecha_slider]['calc'] if "index" in punto]
            elif eje == "cota_abs":
                eje_Y = df['cota_abs'].to_list()

            # Verificar que ambas listas tienen la misma longitud
            if len(eje_X) != len(eje_Y):
                continue

            # Asegurarse de usar líneas discontinuas para los umbrales (sin label para evitar leyenda)
            ax.plot(eje_X, eje_Y, color=color, linestyle='--', linewidth=grosor)
        except Exception as e:
            print(f"Error al procesar umbral {deformada}: {str(e)}")

    # Añadir umbrales solo para la leyenda si es necesario (no aplicable ahora que no hay leyenda)
    if incluir_todos:
        for deformada, color_espanol in leyenda_umbrales.items():
            if deformada not in deformadas_mostradas:
                # Para la leyenda, solo añadimos líneas invisibles (sin label para evitar leyenda)
                ax.plot([], [], color=color_espanol, linestyle='--', linewidth=2)


def configurar_ejes(ax, sensor, escala_desplazamiento, escala_incremento,
                    valor_positivo_desplazamiento, valor_negativo_desplazamiento,
                    valor_positivo_incremento, valor_negativo_incremento,
                    eje, orden, titulo, etiqueta_eje_x=None):
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
        etiqueta_eje_x (str): Etiqueta para el eje X.

    Returns:
        None
    """
    if not ax:
        return

    try:
        # Configurar límites en eje x según el tipo de sensor y escala
        if sensor in ["desp_a", "desp_b", "desp_total"] and escala_desplazamiento == "manual":
            ax.set_xlim(valor_negativo_desplazamiento, valor_positivo_desplazamiento)
        elif sensor in ["incr_dev_abs_a", "incr_dev_abs_b"] and escala_incremento == "manual":
            ax.set_xlim(valor_negativo_incremento, valor_positivo_incremento)
        elif sensor in ["checksum_a", "checksum_b"]:
            # Permitir que matplotlib calcule los límites automáticamente primero
            ax.relim()
            ax.autoscale()

            # Obtener los límites calculados automáticamente
            xlim_actual = ax.get_xlim()

            # Asegurar que los límites incluyan al menos [-1, 1]
            xlim_min = min(xlim_actual[0], -1)
            xlim_max = max(xlim_actual[1], 1)

            # Establecer los límites finales
            ax.set_xlim(xlim_min, xlim_max)

        # Añadir etiqueta al eje X con tipografía mejorada
        if etiqueta_eje_x:
            ax.set_xlabel(etiqueta_eje_x, fontfamily='Arial', fontsize=9, color='#4B5563')

        # Configurar título del eje Y según el tipo
        if eje == "index":
            titulo_eje_y = "Índice"
        elif eje == "cota_abs":
            titulo_eje_y = "Cota (m.s.n.m.)"
        elif eje == "depth":
            titulo_eje_y = "Profundidad (m)"
        else:
            titulo_eje_y = "Y"

        ax.set_ylabel(titulo_eje_y, fontfamily='Arial', fontsize=9, color='#4B5563')

        # Invertir eje Y si el orden no es ascendente
        if not orden:
            ax.invert_yaxis()

        # Configurar estilo moderno y limpio del gráfico
        # Rejilla con intensidad aumentada para mejor visibilidad
        ax.grid(True, linestyle='--', alpha=0.6, color='#E5E7EB', linewidth=0.8)

        # Línea de referencia x=0 más sutil y fina
        ax.axvline(x=0, color='#D1D5DB', linestyle='-', linewidth=0.6)

        # Configurar bordes con mayor intensidad
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#9CA3AF')
        ax.spines['bottom'].set_color('#9CA3AF')
        ax.spines['left'].set_linewidth(1)
        ax.spines['bottom'].set_linewidth(1)
        ax.set_facecolor('white')

        # Añadir ticks menores para mayor precisión visual
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        ax.yaxis.set_minor_locator(AutoMinorLocator())

        # Configurar tipografía moderna para los números de escala
        ax.tick_params(labelsize=8, colors='#6B7280')  # Color más suave para los números
        ax.tick_params(which='minor', length=2, colors='#D1D5DB')  # Ticks menores más sutiles
        ax.tick_params(which='major', length=4, colors='#9CA3AF')  # Ticks mayores moderados

        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontfamily('Arial')
            label.set_color('#6B7280')  # Color consistente y moderno

    except Exception as e:
        print(f"Error al configurar ejes: {e}")
# funciones.py - Funciones auxiliares para gráficos de inclinometría (gráfico evolución temporal)
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
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

    # Convertir de nuevo a formato ISO y ordenar cronológicamente (más antigua a más reciente)
    fechas = [fecha.isoformat() for fecha in fechas_dt]

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
    Función stub para compatibilidad - no se usa en gráficos temporales.
    """
    pass


def configurar_ejes(ax, sensor, escala_desplazamiento, escala_incremento,
                    valor_positivo_desplazamiento, valor_negativo_desplazamiento,
                    valor_positivo_incremento, valor_negativo_incremento,
                    eje, orden, titulo, etiqueta_eje_x=None):
    """
    Configura los ejes, límites y formato del gráfico.
    Función stub para compatibilidad - no se usa en gráficos temporales.
    """
    pass


# FUNCIONES ESPECÍFICAS PARA GRÁFICO TEMPORAL

def seleccionar_profundidades_distribuidas(data, eje, num_profundidades=5):
    """
    Selecciona profundidades distribuidas homogéneamente desde el índice mayor
    hacia índices menores.

    Args:
        data (dict): Diccionario con los datos del tubo.
        eje (str): Tipo de eje (index, cota_abs, depth).
        num_profundidades (int): Número de profundidades a seleccionar.

    Returns:
        list: Lista de profundidades seleccionadas.
    """
    if not data or num_profundidades <= 0:
        return []

    try:
        # Obtener todas las profundidades disponibles de cualquier fecha
        profundidades_set = set()

        for fecha, valor in data.items():
            if fecha not in ["info", "umbrales"] and "calc" in valor:
                for punto in valor["calc"]:
                    if eje in punto:
                        profundidades_set.add(punto[eje])

        if not profundidades_set:
            print("DEBUG: No se encontraron profundidades para el eje especificado")
            return []

        # Convertir a lista y ordenar
        profundidades = sorted(list(profundidades_set))

        print(
            f"DEBUG: Profundidades disponibles: {len(profundidades)} - Rango: {min(profundidades)} a {max(profundidades)}")

        # Si hay menos profundidades disponibles que las solicitadas, usar todas
        if len(profundidades) <= num_profundidades:
            return profundidades

        # Seleccionar profundidades distribuidas homogéneamente
        # Empezar por el índice mayor (última posición) y distribuir hacia atrás
        indices_seleccionados = []

        # Siempre incluir el índice mayor (último elemento)
        indices_seleccionados.append(len(profundidades) - 1)

        # Distribuir los restantes homogéneamente hacia atrás
        if num_profundidades > 1:
            # Calcular el paso para distribuir homogéneamente
            paso = (len(profundidades) - 1) / (num_profundidades - 1)

            for i in range(1, num_profundidades):
                indice = int(len(profundidades) - 1 - i * paso)
                # Asegurar que no se repitan índices y que esté en rango válido
                indice = max(0, min(indice, len(profundidades) - 1))
                if indice not in indices_seleccionados:
                    indices_seleccionados.append(indice)

        # Ordenar los índices para que las profundidades queden en orden
        indices_seleccionados.sort()

        # Seleccionar las profundidades correspondientes
        profundidades_seleccionadas = [profundidades[i] for i in indices_seleccionados]

        print(f"DEBUG: Profundidades seleccionadas: {profundidades_seleccionadas}")

        return profundidades_seleccionadas

    except Exception as e:
        print(f"Error al seleccionar profundidades distribuidas: {e}")
        return []


def extraer_datos_temporales_profundidades(data, fechas_seleccionadas, profundidades, eje, tipo_dato="desp_a"):
    """
    Extrae datos temporales para profundidades específicas.

    Args:
        data (dict): Diccionario con los datos del tubo.
        fechas_seleccionadas (list): Lista de fechas a procesar.
        profundidades (list): Lista de profundidades a extraer.
        eje (str): Tipo de eje (index, cota_abs, depth).
        tipo_dato (str): Tipo de dato a extraer (desp_a, desp_b, desp_total).

    Returns:
        dict: Diccionario con datos temporales por profundidad.
    """
    if not data or not fechas_seleccionadas or not profundidades:
        return {}

    try:
        datos_temporales = {}

        # Inicializar listas para cada profundidad
        for profundidad in profundidades:
            datos_temporales[profundidad] = []

        # Procesar cada fecha en orden cronológico
        fechas_ordenadas = sorted(fechas_seleccionadas, key=lambda x: datetime.fromisoformat(x))

        for fecha in fechas_ordenadas:
            if fecha not in data or "calc" not in data[fecha]:
                # Si no hay datos para esta fecha, añadir None para todas las profundidades
                for profundidad in profundidades:
                    datos_temporales[profundidad].append(None)
                continue

            calc_data = data[fecha]["calc"]

            # Para cada profundidad, buscar el valor correspondiente
            for profundidad in profundidades:
                valor_encontrado = None

                for punto in calc_data:
                    if eje in punto and punto[eje] == profundidad:
                        # Encontramos la profundidad, extraer el dato solicitado
                        if tipo_dato in punto:
                            valor_encontrado = punto[tipo_dato]
                        break

                datos_temporales[profundidad].append(valor_encontrado)

        # Verificar que todas las series tienen la misma longitud
        longitud_esperada = len(fechas_ordenadas)
        for profundidad, valores in datos_temporales.items():
            if len(valores) != longitud_esperada:
                print(
                    f"Warning: La profundidad {profundidad} tiene {len(valores)} valores en lugar de {longitud_esperada}")

        print(f"DEBUG: Datos temporales extraídos para {len(profundidades)} profundidades y {longitud_esperada} fechas")

        return datos_temporales

    except Exception as e:
        print(f"Error al extraer datos temporales: {e}")
        return {}


def configurar_ejes_temporal(ax, fechas_dt, eje, titulo, etiqueta_eje_y="Desplazamiento (mm)", mostrar_leyenda=True):
    """
    Configura los ejes para un gráfico temporal con fechas en formato DD-MM-AA verticales.

    Args:
        ax: Eje de matplotlib donde graficar.
        fechas_dt (list): Lista de objetos datetime.
        eje (str): Tipo de eje vertical usado para la leyenda.
        titulo (str): Título del gráfico.
        etiqueta_eje_y (str): Etiqueta para el eje Y.
        mostrar_leyenda (bool): Si mostrar la leyenda o no.

    Returns:
        None
    """
    if not ax or not fechas_dt:
        return

    try:
        # Configurar formato de fechas en el eje X
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))

        # Si hay muchas fechas, usar un localizador más inteligente
        if len(fechas_dt) > 10:
            # Para muchas fechas, mostrar menos etiquetas
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=max(1, len(fechas_dt) // 8)))
        elif len(fechas_dt) > 5:
            # Para fechas intermedias, mostrar algunas
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=max(1, len(fechas_dt) // 5)))
        else:
            # Para pocas fechas, mostrar todas
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))

        # Rotar etiquetas de fecha para que sean verticales
        plt.xticks(rotation=90)

        # Configurar etiqueta del eje Y
        ax.set_ylabel(etiqueta_eje_y, fontfamily='Arial', fontsize=10, color='#4B5563')

        # Configurar etiqueta del eje X
        ax.set_xlabel('Fecha', fontfamily='Arial', fontsize=10, color='#4B5563')

        # Configurar rejilla
        ax.grid(True, linestyle='--', alpha=0.6, color='#E5E7EB', linewidth=0.8)

        # Línea de referencia y=0
        ax.axhline(y=0, color='#D1D5DB', linestyle='-', linewidth=0.6)

        # Configurar bordes del gráfico
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#9CA3AF')
        ax.spines['bottom'].set_color('#9CA3AF')
        ax.spines['left'].set_linewidth(1)
        ax.spines['bottom'].set_linewidth(1)
        ax.set_facecolor('white')

        # Configurar ticks
        ax.tick_params(labelsize=8, colors='#6B7280')
        ax.tick_params(which='minor', length=2, colors='#D1D5DB')
        ax.tick_params(which='major', length=4, colors='#9CA3AF')

        # Aplicar formato de fuente a las etiquetas
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontfamily('Arial')
            label.set_color('#6B7280')

        # Configurar leyenda si se solicita
        """
        if mostrar_leyenda:
            legend = ax.legend(
                loc='upper center',  # Posición en la parte superior central
                bbox_to_anchor=(0.5, -0.1),  # Ubicar debajo del gráfico
                ncol=min(3, len(ax.get_lines())),  # Máximo 3 columnas
                frameon=True,  # Mostrar marco de la leyenda
                fancybox=True,  # Esquinas redondeadas
                shadow=True,  # Sombra
                fontsize=8,  # Tamaño de fuente
                title=f'Profundidades ({eje})',  # Título de la leyenda
                title_fontsize=9  # Tamaño del título
            )
        

            # Configurar estilo de la leyenda
            legend.get_frame().set_facecolor('white')
            legend.get_frame().set_alpha(0.9)
            legend.get_frame().set_edgecolor('#D1D5DB')
        """

        # Ajustar límites del eje X para dar un poco de margen
        if len(fechas_dt) > 1:
            rango_fechas = fechas_dt[-1] - fechas_dt[0]
            margen = rango_fechas * 0.02  # 2% de margen a cada lado
            ax.set_xlim(fechas_dt[0] - margen, fechas_dt[-1] + margen)

        # Optimizar el espaciado de las etiquetas de fecha
        fig = ax.get_figure()
        fig.autofmt_xdate()

    except Exception as e:
        print(f"Error al configurar ejes temporales: {e}")

# Anotaciones modernas al final de cada serie
def agregar_anotaciones_finales(ax, datos_temporales, profundidades_seleccionadas, fechas_ordenadas, colores_serie, eje,
                                limite_area_datos=None):
    """
    Agrega anotaciones en el área reservada del gráfico (borde derecho interno).
    """
    try:
        if not fechas_ordenadas or not datos_temporales:
            return

        print("DEBUG: === INICIO agregar_anotaciones_finales ===")

        # Recopilar puntos finales
        puntos_finales = []
        # CORRECCIÓN CRÍTICA: Usar limite_area_datos si está disponible
        fecha_final_datos = limite_area_datos if limite_area_datos else fechas_ordenadas[-1]
        print(f"DEBUG: Fecha final de datos (corregida): {fecha_final_datos}")

        for i, profundidad in enumerate(profundidades_seleccionadas):
            if profundidad in datos_temporales:
                valores = datos_temporales[profundidad]

                ultimo_valor = None
                for valor in reversed(valores):
                    if valor is not None:
                        ultimo_valor = valor
                        break

                if ultimo_valor is not None:
                    color = colores_serie[i % len(colores_serie)]

                    if eje == 'cota_abs':
                        etiqueta = f"{profundidad:.1f}"
                    elif eje == 'depth':
                        etiqueta = f"{profundidad:.1f}m"
                    else:
                        etiqueta = f"{int(profundidad)}"

                    puntos_finales.append({
                        'valor_original': ultimo_valor,
                        'profundidad': profundidad,
                        'color': color,
                        'etiqueta': etiqueta
                    })

        if not puntos_finales:
            return

        # Calcular posiciones Y anti-solapamiento
        puntos_finales.sort(key=lambda x: x['valor_original'])

        y_min, y_max = ax.get_ylim()
        separacion_minima = (y_max - y_min) * 0.08

        for i, punto in enumerate(puntos_finales):
            if i == 0:
                punto['y_anotacion'] = punto['valor_original']
            else:
                y_anterior = puntos_finales[i - 1]['y_anotacion']
                if punto['valor_original'] - y_anterior < separacion_minima:
                    punto['y_anotacion'] = y_anterior + separacion_minima
                else:
                    punto['y_anotacion'] = punto['valor_original']

        # Calcular posición X de las anotaciones (en el área reservada)
        x_min, x_max = ax.get_xlim()

        # Posición X: Alineadas con el borde derecho del gráfico (98% para evitar corte)
        x_anotacion = x_min + (x_max - x_min) * 0.98

        print(f"DEBUG: Límites del gráfico: {x_min} a {x_max}")
        print(f"DEBUG: Fecha final de datos: {fecha_final_datos}")
        print(f"DEBUG: Posición X de anotaciones: {x_anotacion}")

        # Dibujar las anotaciones
        for punto in puntos_finales:
            y_original = punto['valor_original']
            y_anotacion = punto['y_anotacion']

            # Línea de conexión si es necesaria
            if abs(y_anotacion - y_original) > separacion_minima * 0.3:
                ax.plot([fecha_final_datos, x_anotacion],
                        [y_original, y_anotacion],
                        color=punto['color'],
                        linewidth=0.8,
                        linestyle='--',
                        alpha=0.6,
                        zorder=90)

            # Anotación en coordenadas absolutas del gráfico
            ax.annotate(
                punto['etiqueta'],
                xy=(fecha_final_datos, y_original),  # Punto de la serie
                xytext=(x_anotacion, y_anotacion),  # Posición en área reservada
                xycoords='data',
                textcoords='data',
                va='center',
                ha='center',
                fontsize=7,
                fontweight='normal',
                color=punto['color'],
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor='white',
                    edgecolor=punto['color'],
                    linewidth=1.0,
                    alpha=0.95
                ),
                arrowprops=dict(
                    arrowstyle='-',
                    color=punto['color'],
                    linewidth=0.8,
                    alpha=0.8,
                    shrinkA=2,
                    shrinkB=2
                ),
                zorder=100
            )

        print(f"DEBUG: {len(puntos_finales)} anotaciones colocadas en área reservada")
        print("DEBUG: === FIN agregar_anotaciones_finales ===")

    except Exception as e:
        print(f"ERROR en anotaciones: {e}")
        import traceback
        traceback.print_exc()
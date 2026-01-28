# funciones.py - Funciones auxiliares para gráficos de inclinometría
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
from matplotlib.ticker import AutoMinorLocator
from scipy import stats
import io
import base64


def calcular_fechas_seleccionadas(data, fecha_inicial, fecha_final, total_camp=None, ultimas_camp=None,
                                  cadencia_dias=None):
    """
    Calcula las fechas entre fecha_inicial y fecha_final.
    Prioriza fechas donde data[fecha]["campaign_info"]["active"] == True
    Si no hay campaign_info, usa todas las fechas disponibles como fallback.

    Args:
        data (dict): Diccionario con los datos del tubo.
        fecha_inicial (str): Fecha de inicio en formato ISO.
        fecha_final (str): Fecha final en formato ISO.
        total_camp (int, optional): Parámetro mantenido por compatibilidad, no se usa.
        ultimas_camp (int, optional): Parámetro mantenido por compatibilidad, no se usa.
        cadencia_dias (int, optional): Parámetro mantenido por compatibilidad, no se usa.

    Returns:
        list: Lista de fechas seleccionadas, ordenadas cronológicamente.
    """
    if not data:
        print("DEBUG: calcular_fechas_seleccionadas - No hay datos disponibles")
        return []

    # Obtener todas las fechas disponibles (excluyendo claves especiales)
    # NOTA: Excluimos claves que pueden venir del data_source pero no son fechas ISO
    claves_especiales = {"info", "umbrales", "fecha_seleccionada", "ultimas_camp", 
                         "fecha_inicial", "fecha_final", "total_camp", "cadencia_dias",
                         "eje", "orden", "color_scheme", "escala_desplazamiento", 
                         "escala_incremento", "sensor", "nombre_sensor", "leyenda_umbrales",
                         "valor_positivo_desplazamiento", "valor_negativo_desplazamiento",
                         "valor_positivo_incremento", "valor_negativo_incremento",
                         "escala_temporal", "valor_positivo_temporal", "valor_negativo_temporal"}
    fechas_disponibles = [fecha for fecha in data.keys() if fecha not in claves_especiales]

    if not fechas_disponibles:
        print("DEBUG: calcular_fechas_seleccionadas - No se encontraron fechas en los datos")
        return []

    print(f"DEBUG: calcular_fechas_seleccionadas - {len(fechas_disponibles)} fechas disponibles en total")

    try:
        # Intentar filtrar fechas activas primero, pero con fallback tolerante
        fechas_activas = []
        fechas_con_campaign_info = 0
        fechas_con_calc = 0

        for fecha in fechas_disponibles:
            try:
                # Verificar que la fecha tenga la estructura esperada
                if fecha in data and isinstance(data[fecha], dict):

                    # Contar fechas con datos de cálculo (requisito mínimo)
                    if 'calc' in data[fecha]:
                        fechas_con_calc += 1

                    # Verificar si existe campaign_info
                    if 'campaign_info' in data[fecha] and isinstance(data[fecha]['campaign_info'], dict):
                        fechas_con_campaign_info += 1
                        # Verificar si está activa
                        if data[fecha]['campaign_info'].get('active', False) == True:
                            fechas_activas.append(fecha)
                    else:
                        # Si no hay campaign_info pero hay calc, incluir como válida (FALLBACK)
                        if 'calc' in data[fecha]:
                            fechas_activas.append(fecha)

            except Exception as e:
                print(f"DEBUG: Error procesando fecha {fecha}: {e}")
                continue

        print(f"DEBUG: calcular_fechas_seleccionadas - {fechas_con_calc} fechas con 'calc'")
        print(f"DEBUG: calcular_fechas_seleccionadas - {fechas_con_campaign_info} fechas con 'campaign_info'")
        print(f"DEBUG: calcular_fechas_seleccionadas - {len(fechas_activas)} fechas consideradas válidas")

        # Si no hay fechas válidas, usar todas las que tengan 'calc' como último fallback
        if not fechas_activas:
            print(
                "DEBUG: calcular_fechas_seleccionadas - No hay fechas válidas, usando fallback con fechas que tengan 'calc'")
            fechas_activas = [f for f in fechas_disponibles if
                              f in data and isinstance(data[f], dict) and 'calc' in data[f]]

        if not fechas_activas:
            print("DEBUG: calcular_fechas_seleccionadas - CRÍTICO: No hay fechas con datos de cálculo")
            return []

        # Convertir fechas a objetos datetime
        fechas_dt_validas = []
        for fecha in fechas_activas:
            try:
                # Manejar diferentes formatos de fecha
                if fecha.endswith('Z'):
                    fecha_dt = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
                elif 'T' in fecha:
                    fecha_dt = datetime.fromisoformat(fecha)
                else:
                    fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')

                fechas_dt_validas.append((fecha_dt, fecha))
            except ValueError:
                try:
                    # Intentar otros formatos comunes
                    if len(fecha) == 10:  # YYYY-MM-DD
                        fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
                    else:  # Formato ISO con tiempo
                        fecha_dt = datetime.fromisoformat(fecha.split('+')[0])  # Quitar timezone si existe
                    fechas_dt_validas.append((fecha_dt, fecha))
                except ValueError:
                    print(f"Warning: No se pudo convertir la fecha {fecha}")
                    continue

        if not fechas_dt_validas:
            print("ERROR: calcular_fechas_seleccionadas - No se pudieron convertir ninguna fecha")
            return []

        print(f"DEBUG: calcular_fechas_seleccionadas - {len(fechas_dt_validas)} fechas convertidas correctamente")

        # Filtrar por rango de fechas si se especificaron
        fechas_filtradas = fechas_dt_validas

        if fecha_inicial and fecha_final:
            try:
                # Manejar diferentes formatos de fecha para los parámetros
                if fecha_inicial.endswith('Z'):
                    fecha_inicio_dt = datetime.fromisoformat(fecha_inicial.replace('Z', '+00:00'))
                elif 'T' in fecha_inicial:
                    fecha_inicio_dt = datetime.fromisoformat(fecha_inicial)
                else:
                    fecha_inicio_dt = datetime.strptime(fecha_inicial, '%Y-%m-%d')

                if fecha_final.endswith('Z'):
                    fecha_fin_dt = datetime.fromisoformat(fecha_final.replace('Z', '+00:00'))
                elif 'T' in fecha_final:
                    fecha_fin_dt = datetime.fromisoformat(fecha_final)
                else:
                    fecha_fin_dt = datetime.strptime(fecha_final, '%Y-%m-%d')

                fechas_filtradas = [
                    (fecha_dt, fecha_str) for fecha_dt, fecha_str in fechas_dt_validas
                    if fecha_inicio_dt <= fecha_dt <= fecha_fin_dt
                ]

                print(
                    f"DEBUG: calcular_fechas_seleccionadas - {len(fechas_filtradas)} fechas en el rango {fecha_inicial} - {fecha_final}")

            except ValueError as e:
                print(f"Warning: Error al procesar rango de fechas: {e}")
                print("DEBUG: calcular_fechas_seleccionadas - Usando todas las fechas válidas sin filtro de rango")
                fechas_filtradas = fechas_dt_validas

        # Si después del filtro no hay fechas, usar todas las fechas válidas
        if not fechas_filtradas:
            print("DEBUG: calcular_fechas_seleccionadas - No hay fechas en el rango, usando todas las fechas válidas")
            fechas_filtradas = fechas_dt_validas

        # Ordenar cronológicamente (más reciente primero para mantener compatibilidad)
        fechas_filtradas.sort(key=lambda x: x[0], reverse=True)

        # Extraer solo las fechas en formato string
        fechas_seleccionadas = [fecha_str for fecha_dt, fecha_str in fechas_filtradas]

        print(f"DEBUG: calcular_fechas_seleccionadas - {len(fechas_seleccionadas)} fechas finalmente seleccionadas")

        if fechas_seleccionadas:
            print(f"DEBUG: calcular_fechas_seleccionadas - Primera fecha: {fechas_seleccionadas[0]}")
            print(f"DEBUG: calcular_fechas_seleccionadas - Última fecha: {fechas_seleccionadas[-1]}")

        return fechas_seleccionadas

    except Exception as e:
        print(f"ERROR: calcular_fechas_seleccionadas - {e}")
        import traceback
        traceback.print_exc()

        # Fallback extremo: devolver las fechas que tengan 'calc'
        print("DEBUG: calcular_fechas_seleccionadas - Usando fallback extremo")
        fechas_con_calc = [f for f in fechas_disponibles if
                           f in data and isinstance(data[f], dict) and 'calc' in data[f]]
        return fechas_con_calc[:10] if len(fechas_con_calc) > 10 else fechas_con_calc


def extraer_datos_fecha(fecha, data, eje):
    """
    Extrae y procesa los datos de cálculo para una fecha específica.
    Ahora extrae TODOS los campos disponibles dinámicamente.

    Args:
        fecha (str): Fecha de la que extraer datos.
        data (dict): Diccionario con datos del tubo.
        eje (str): Tipo de eje (index, cota_abs, depth).

    Returns:
        dict: Diccionario con los datos extraídos o None si no hay datos.
    """
    if not fecha or not data:
        print(f"DEBUG: extraer_datos_fecha - fecha o data son None")
        return None

    if fecha not in data:
        print(f"DEBUG: extraer_datos_fecha - fecha {fecha} no está en data")
        return None

    fecha_data = data[fecha]
    if not isinstance(fecha_data, dict):
        print(f"DEBUG: extraer_datos_fecha - data[{fecha}] no es un diccionario")
        return None

    if "calc" not in fecha_data:
        print(
            f"DEBUG: extraer_datos_fecha - No hay 'calc' en data[{fecha}]. Claves disponibles: {list(fecha_data.keys())}")
        return None

    calc_data = fecha_data["calc"]

    if not calc_data or not isinstance(calc_data, list):
        print(f"DEBUG: extraer_datos_fecha - 'calc' está vacío o no es una lista. Tipo: {type(calc_data)}")
        return None

    print(f"DEBUG: extraer_datos_fecha - {fecha} tiene {len(calc_data)} puntos de cálculo")

    try:
        # Si el eje es "depth", construimos la lista según la lógica especificada
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

        # Verificar que el eje está disponible
        if not eje_Y:
            print(f"DEBUG: extraer_datos_fecha - No se encontraron valores para eje '{eje}' en {fecha}")
            # Mostrar claves disponibles en el primer punto para debug
            if calc_data:
                print(f"DEBUG: extraer_datos_fecha - Claves disponibles en primer punto: {list(calc_data[0].keys())}")
            return None

        # ===== NUEVA LÓGICA: EXTRAER TODOS LOS CAMPOS DINÁMICAMENTE =====

        # Encontrar todos los campos únicos disponibles en los datos
        campos_disponibles = set()
        for punto in calc_data:
            if isinstance(punto, dict):
                campos_disponibles.update(punto.keys())

        # Excluir el eje Y ya que se maneja por separado
        campos_disponibles.discard(eje)
        if eje == "depth":
            campos_disponibles.discard("cota_abs")

        print(f"DEBUG: extraer_datos_fecha - Campos disponibles en {fecha}: {sorted(campos_disponibles)}")

        # Crear diccionario resultado con eje_Y
        resultado = {'eje_Y': eje_Y}

        # Extraer dinámicamente todos los campos disponibles
        for campo in campos_disponibles:
            valores = [punto.get(campo, 0) for punto in calc_data]
            resultado[campo] = valores

            # Contar campos válidos para debug
            campos_validos = sum(1 for punto in calc_data if campo in punto)
            print(f"DEBUG: extraer_datos_fecha - {fecha}: {campos_validos} valores de '{campo}'")

        # También calcular desp_total si tenemos desp_a y desp_b
        if 'desp_a' in resultado and 'desp_b' in resultado:
            desp_total = [((a ** 2 + b ** 2) ** 0.5) for a, b in zip(resultado['desp_a'], resultado['desp_b'])]
            resultado['desp_total'] = desp_total
            print(f"DEBUG: extraer_datos_fecha - {fecha}: Calculado desp_total")

        print(
            f"DEBUG: extraer_datos_fecha - {fecha}: extracción exitosa con {len(eje_Y)} puntos y {len(resultado) - 1} campos de datos")

        return resultado

    except (KeyError, TypeError, ValueError) as e:
        print(f"ERROR: extraer_datos_fecha - Error al extraer datos de fecha {fecha}: {e}")
        import traceback
        traceback.print_exc()
        return None


# ================================
# FUNCIONES ESTADÍSTICAS
# ================================

def calcular_rms(valores):
    """
    Calcula el valor RMS (Root Mean Square) de una lista de valores.
    RMS = sqrt(sum(x^2)/n)

    Args:
        valores (list): Lista de valores numéricos.

    Returns:
        float or None: Valor RMS o None si no hay datos válidos.
    """
    if not valores or len(valores) == 0:
        return None

    # Para checksum, 0 puede ser un valor válido, solo excluir None y NaN
    valores_validos = [v for v in valores if v is not None and not (isinstance(v, float) and np.isnan(v))]
    if not valores_validos:
        return None

    suma_cuadrados = sum(v ** 2 for v in valores_validos)
    rms = np.sqrt(suma_cuadrados / len(valores_validos))
    return rms


def calcular_desviacion_estandar(valores):
    """
    Calcula la desviación estándar de una lista de valores.

    Args:
        valores (list): Lista de valores numéricos.

    Returns:
        float or None: Desviación estándar o None si no hay suficientes datos.
    """
    if not valores or len(valores) == 0:
        return None

    # Para checksum, 0 puede ser un valor válido, solo excluir None y NaN
    valores_validos = [v for v in valores if v is not None and not (isinstance(v, float) and np.isnan(v))]
    if len(valores_validos) < 2:
        return None

    return np.std(valores_validos, ddof=1)  # ddof=1 para desviación estándar muestral


def calcular_iqr(valores):
    """
    Calcula el rango intercuartílico (IQR) de una lista de valores.
    IQR = Q3 - Q1

    Args:
        valores (list): Lista de valores numéricos.

    Returns:
        float or None: Rango intercuartílico o None si no hay suficientes datos.
    """
    if not valores or len(valores) == 0:
        return None

    # Para checksum, 0 puede ser un valor válido, solo excluir None y NaN
    valores_validos = [v for v in valores if v is not None and not (isinstance(v, float) and np.isnan(v))]
    if len(valores_validos) < 4:  # Necesitamos al menos 4 valores para calcular cuartiles
        return None

    q1 = np.percentile(valores_validos, 25)
    q3 = np.percentile(valores_validos, 75)
    return q3 - q1


def calcular_drift(valores, profundidades):
    """
    Calcula la deriva (drift) como la pendiente de la regresión lineal
    de checksum vs profundidad.

    Args:
        valores (list): Lista de valores de checksum.
        profundidades (list): Lista de profundidades correspondientes.

    Returns:
        float or None: Pendiente de la regresión lineal (drift) o None si no hay suficientes datos.
    """
    if not valores or not profundidades or len(valores) != len(profundidades):
        return None

    # Para checksum, 0 puede ser un valor válido, solo excluir None y NaN
    datos_validos = [(p, v) for p, v in zip(profundidades, valores)
                     if v is not None and not (isinstance(v, float) and np.isnan(v))]

    if len(datos_validos) < 2:
        return None

    profundidades_validas = [d[0] for d in datos_validos]
    valores_validos = [d[1] for d in datos_validos]

    try:
        # Realizar regresión lineal
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            profundidades_validas, valores_validos
        )
        return slope
    except:
        return None


def safe_datetime_parse(fecha_str):
    """Función auxiliar para parsear fechas de forma segura"""
    try:
        if 'Z' in fecha_str:
            return datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
        elif 'T' in fecha_str:
            return datetime.fromisoformat(fecha_str)
        else:
            return datetime.strptime(fecha_str, '%Y-%m-%d')
    except ValueError:
        try:
            return datetime.strptime(fecha_str, '%Y-%m-%d')
        except ValueError:
            print(f"Warning: No se pudo parsear fecha {fecha_str}")
            return datetime.min


def extraer_estadisticos_temporales(data, fechas_seleccionadas, eje, tipo_sensor="checksum_a"):
    """
    Extrae estadísticos de cualquier sensor para cada fecha.

    Args:
        data (dict): Diccionario con los datos del tubo.
        fechas_seleccionadas (list): Lista de fechas a procesar.
        eje (str): Tipo de eje para las profundidades (index, cota_abs, depth).
        tipo_sensor (str): Tipo de sensor a analizar (cualquier campo disponible en los datos).

    Returns:
        dict: Diccionario con series temporales de cada estadístico.
    """
    if not data or not fechas_seleccionadas:
        print("DEBUG: extraer_estadisticos_temporales - Sin datos o fechas")
        return {}

    try:
        # Inicializar diccionarios para cada estadístico
        estadisticos = {
            'rms': [],
            'std': [],
            'iqr': [],
            'drift': []
        }

        # Procesar cada fecha en orden cronológico
        fechas_ordenadas = sorted(fechas_seleccionadas, key=safe_datetime_parse)

        print(f"DEBUG: extraer_estadisticos_temporales - Procesando {len(fechas_ordenadas)} fechas para estadísticos")

        fechas_con_datos = 0
        fechas_con_sensor = 0
        sensor_encontrado_en_muestra = False

        for i, fecha in enumerate(fechas_ordenadas):
            print(f"DEBUG: extraer_estadisticos_temporales - Procesando fecha {i + 1}/{len(fechas_ordenadas)}: {fecha}")

            # Extraer datos de la fecha
            datos_fecha = extraer_datos_fecha(fecha, data, eje)

            if datos_fecha:
                fechas_con_datos += 1
                print(
                    f"DEBUG: extraer_estadisticos_temporales - Fecha {fecha} - datos extraídos: {list(datos_fecha.keys())}")

                # Verificar si el sensor solicitado existe en los datos
                if not sensor_encontrado_en_muestra and i == 0:  # Solo verificar en la primera fecha
                    if tipo_sensor not in datos_fecha:
                        campos_disponibles = [k for k in datos_fecha.keys() if k != 'eje_Y']
                        raise ValueError(
                            f"Sensor '{tipo_sensor}' no encontrado. Campos disponibles: {campos_disponibles}")
                    sensor_encontrado_en_muestra = True

                if tipo_sensor in datos_fecha:
                    fechas_con_sensor += 1
                    valores_sensor = datos_fecha[tipo_sensor]
                    profundidades = datos_fecha['eje_Y']

                    # Verificar que hay datos válidos (0 es válido para la mayoría de sensores)
                    valores_validos = [v for v in valores_sensor if
                                       v is not None and not (isinstance(v, float) and np.isnan(v))]
                    print(
                        f"DEBUG: extraer_estadisticos_temporales - Fecha {fecha} - {len(valores_validos)} valores de {tipo_sensor} válidos de {len(valores_sensor)} total")

                    # Calcular cada estadístico
                    rms_val = calcular_rms(valores_sensor)
                    std_val = calcular_desviacion_estandar(valores_sensor)
                    iqr_val = calcular_iqr(valores_sensor)
                    drift_val = calcular_drift(valores_sensor, profundidades)

                    estadisticos['rms'].append(rms_val)
                    estadisticos['std'].append(std_val)
                    estadisticos['iqr'].append(iqr_val)
                    estadisticos['drift'].append(drift_val)

                    print(
                        f"DEBUG: extraer_estadisticos_temporales - Fecha {fecha} - Estadísticos: RMS={rms_val}, STD={std_val}, IQR={iqr_val}, DRIFT={drift_val}")
                else:
                    print(f"DEBUG: extraer_estadisticos_temporales - Fecha {fecha} - No contiene {tipo_sensor}")
                    # Si no hay datos del sensor, añadir None
                    for key in estadisticos:
                        estadisticos[key].append(None)
            else:
                print(f"DEBUG: extraer_estadisticos_temporales - Fecha {fecha} - No se pudieron extraer datos")
                # Si no hay datos, añadir None
                for key in estadisticos:
                    estadisticos[key].append(None)

        print(
            f"DEBUG: extraer_estadisticos_temporales - Resumen - {fechas_con_datos} fechas con datos, {fechas_con_sensor} fechas con {tipo_sensor}")

        # Verificar que al menos hay algunos datos válidos
        total_valores_validos = 0
        for tipo_est, valores in estadisticos.items():
            valores_validos = [v for v in valores if v is not None]
            total_valores_validos += len(valores_validos)
            print(f"DEBUG: extraer_estadisticos_temporales - {tipo_est}: {len(valores_validos)} valores válidos")

        if total_valores_validos == 0:
            print(
                f"ERROR: extraer_estadisticos_temporales - No se encontraron valores válidos para ningún estadístico de {tipo_sensor}")

        print(f"DEBUG: extraer_estadisticos_temporales - Estadísticos calculados para {len(fechas_ordenadas)} fechas")
        return estadisticos

    except Exception as e:
        print(f"ERROR: extraer_estadisticos_temporales - {e}")
        import traceback
        traceback.print_exc()
        return {}


# ================================
# FUNCIONES AUXILIARES PARA GRÁFICOS
# ================================

def configurar_ejes_temporal_compacto(ax, fechas_dt, titulo, etiqueta_eje_y="Valor"):
    """
    Configura los ejes para un gráfico temporal compacto.

    Args:
        ax: Eje de matplotlib.
        fechas_dt (list): Lista de fechas datetime.
        titulo (str): Título del gráfico.
        etiqueta_eje_y (str): Etiqueta del eje Y.
    """
    if not ax or not fechas_dt:
        return

    try:
        # Configurar formato de fechas en el eje X
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%y'))

        # Estrategia automática para mostrar fechas
        rango_fechas = fechas_dt[-1] - fechas_dt[0]
        meses_total = rango_fechas.days / 30.44

        if meses_total <= 3:
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        elif meses_total <= 6:
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        elif meses_total <= 12:
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        elif meses_total <= 24:
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        else:
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))

        # Rotar etiquetas
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)

        # Configurar etiquetas
        ax.set_ylabel(etiqueta_eje_y, fontfamily='Arial', fontsize=9, color='#4B5563')

        # Configurar rejilla
        ax.grid(True, linestyle='--', alpha=0.4, color='#E5E7EB', linewidth=0.6)
        ax.axhline(y=0, color='#D1D5DB', linestyle='-', linewidth=0.5)

        # Configurar bordes
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#9CA3AF')
        ax.spines['bottom'].set_color('#9CA3AF')
        ax.set_facecolor('white')

        # Configurar ticks
        ax.tick_params(labelsize=7, colors='#6B7280')

        # Configurar título con mejor formato
        ax.set_title(titulo, fontsize=12, pad=10, fontweight='bold', color='#374151')

    except Exception as e:
        print(f"Error al configurar ejes: {e}")


def agregar_leyenda_estadisticos(ax, estadisticos_activos):
    """
    Agrega una leyenda personalizada para los estadísticos.

    Args:
        ax: Eje de matplotlib.
        estadisticos_activos (list): Lista de estadísticos a mostrar en la leyenda.
    """
    if not estadisticos_activos:
        return

    # Definir colores y etiquetas para cada estadístico
    info_estadisticos = {
        'rms': {'color': '#1f77b4', 'label': 'RMS', 'linestyle': '-'},
        'std': {'color': '#ff7f0e', 'label': 'Desv. Estándar', 'linestyle': '--'},
        'iqr': {'color': '#2ca02c', 'label': 'IQR', 'linestyle': '-.'},
        'drift': {'color': '#d62728', 'label': 'Deriva', 'linestyle': ':'}
    }

    # Crear elementos de leyenda solo para estadísticos activos
    handles = []
    labels = []

    for est in estadisticos_activos:
        if est in info_estadisticos:
            info = info_estadisticos[est]
            line = plt.Line2D([0], [0], color=info['color'],
                              linewidth=2, linestyle=info['linestyle'])
            handles.append(line)
            labels.append(info['label'])

    # Agregar leyenda
    ax.legend(handles, labels, loc='upper left', frameon=True,
              fancybox=True, shadow=False, fontsize=8)


# ================================
# FUNCIONES ADICIONALES (COMPATIBILIDAD)
# ================================

def determinar_fecha_slider(data, fechas_seleccionadas):
    """Determina la fecha a destacar (por defecto la última fecha activa)."""
    if not fechas_seleccionadas or not data:
        return None
    return fechas_seleccionadas[0]  # Devolver la primera (más reciente)


def get_color_for_index(index, color_scheme="monocromo", total_colors=10):
    """Devuelve un color para un índice determinado según el esquema de colores."""
    # Validación de parámetros
    if total_colors <= 0:
        total_colors = 1
    if index < 0:
        index = 0

    if color_scheme == "monocromo":
        # Degradado de azul (de claro a oscuro)
        cmap = plt.cm.Blues
        norm_index = 0.2 + 0.7 * (1 - index / (total_colors - 1 if total_colors > 1 else 1))
        color_rgb = cmap(norm_index)[:3]
        color_hex = "#{:02x}{:02x}{:02x}".format(
            int(color_rgb[0] * 255),
            int(color_rgb[1] * 255),
            int(color_rgb[2] * 255)
        )
        return color_hex
    else:  # "multicromo"
        colores_base = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]
        return colores_base[index % len(colores_base)]


def generar_info_colores(fechas_seleccionadas, color_scheme):
    """Genera información de colores para cada fecha."""
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
    """Obtiene la leyenda de umbrales desde los datos."""
    if leyenda_umbrales_interfaz and isinstance(leyenda_umbrales_interfaz, dict):
        return leyenda_umbrales_interfaz
    return {}


def obtener_color_para_fecha(fecha, fechas_colores):
    """Obtiene el color asociado a una fecha desde el diccionario de colores."""
    if not fechas_colores or not fecha:
        return 'gray'

    item_correspondiente = next((item for item in fechas_colores if item['value'] == fecha), None)
    if item_correspondiente and 'style' in item_correspondiente and 'color' in item_correspondiente['style']:
        return item_correspondiente['style']['color']
    return 'gray'


def interpolar_def_tubo(cota_tubo, cota_umbral, def_umbral):
    """Interpola los valores de deformada para las cotas del tubo."""
    if not cota_tubo or not cota_umbral or not def_umbral:
        return []

    if len(cota_umbral) != len(def_umbral):
        print("Error: Las listas de cotas y deformadas de umbral deben tener la misma longitud")
        return []

    try:
        x_conocidos = np.array(cota_umbral)
        y_conocidos = np.array(def_umbral)
        x_interpolar = np.array(cota_tubo)
        y_interpolados = np.interp(x_interpolar, x_conocidos, y_conocidos)
        return y_interpolados.tolist()
    except Exception as e:
        print(f"Error en interpolación: {e}")
        return []


def seleccionar_profundidades_distribuidas(data, eje, num_profundidades=5):
    """Selecciona profundidades distribuidas homogéneamente."""
    if not data or num_profundidades <= 0:
        return []

    try:
        # Definir claves especiales que no son fechas
        claves_especiales = {"info", "umbrales", "fecha_seleccionada", "ultimas_camp", 
                             "fecha_inicial", "fecha_final", "total_camp", "cadencia_dias",
                             "eje", "orden", "color_scheme", "escala_desplazamiento", 
                             "escala_incremento", "sensor", "nombre_sensor", "leyenda_umbrales",
                             "valor_positivo_desplazamiento", "valor_negativo_desplazamiento",
                             "valor_positivo_incremento", "valor_negativo_incremento",
                             "escala_temporal", "valor_positivo_temporal", "valor_negativo_temporal"}
        
        profundidades_set = set()

        for fecha, valor in data.items():
            # Filtrar claves especiales y verificar que valor es un diccionario con 'calc'
            if fecha not in claves_especiales and isinstance(valor, dict) and "calc" in valor:
                for punto in valor["calc"]:
                    if eje in punto:
                        profundidades_set.add(punto[eje])

        if not profundidades_set:
            return []

        profundidades = sorted(list(profundidades_set))

        if len(profundidades) <= num_profundidades:
            return profundidades

        # Seleccionar profundidades distribuidas homogéneamente
        indices_seleccionados = []
        indices_seleccionados.append(len(profundidades) - 1)

        if num_profundidades > 1:
            paso = (len(profundidades) - 1) / (num_profundidades - 1)
            for i in range(1, num_profundidades):
                indice = int(len(profundidades) - 1 - i * paso)
                indice = max(0, min(indice, len(profundidades) - 1))
                if indice not in indices_seleccionados:
                    indices_seleccionados.append(indice)

        indices_seleccionados.sort()
        return [profundidades[i] for i in indices_seleccionados]

    except Exception as e:
        print(f"Error al seleccionar profundidades distribuidas: {e}")
        return []


def extraer_datos_temporales_profundidades(data, fechas_seleccionadas, profundidades, eje, tipo_dato="desp_a"):
    """Extrae datos temporales para profundidades específicas."""
    if not data or not fechas_seleccionadas or not profundidades:
        return {}

    try:
        datos_temporales = {}
        for profundidad in profundidades:
            datos_temporales[profundidad] = []

        fechas_ordenadas = sorted(fechas_seleccionadas, key=lambda x: datetime.fromisoformat(x))

        for fecha in fechas_ordenadas:
            if fecha not in data or "calc" not in data[fecha]:
                for profundidad in profundidades:
                    datos_temporales[profundidad].append(None)
                continue

            calc_data = data[fecha]["calc"]

            for profundidad in profundidades:
                valor_encontrado = None
                for punto in calc_data:
                    if eje in punto and punto[eje] == profundidad:
                        if tipo_dato in punto:
                            valor_encontrado = punto[tipo_dato]
                        break
                datos_temporales[profundidad].append(valor_encontrado)

        return datos_temporales

    except Exception as e:
        print(f"Error al extraer datos temporales: {e}")
        return {}


def agregar_anotaciones_finales(ax, datos_temporales, profundidades_seleccionadas, fechas_ordenadas, colores_serie, eje,
                                limite_area_datos=None):
    """Agrega anotaciones en el área reservada del gráfico."""
    try:
        if not fechas_ordenadas or not datos_temporales:
            return

        puntos_finales = []
        fecha_final_datos = limite_area_datos if limite_area_datos else fechas_ordenadas[-1]

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

        # Calcular posición X de las anotaciones
        x_min, x_max = ax.get_xlim()
        x_anotacion = x_min + (x_max - x_min) * 0.98

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

            # Anotación
            ax.annotate(
                punto['etiqueta'],
                xy=(fecha_final_datos, y_original),
                xytext=(x_anotacion, y_anotacion),
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

    except Exception as e:
        print(f"ERROR en anotaciones: {e}")
        import traceback
        traceback.print_exc()
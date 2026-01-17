# grafico_incli_evo_std_chk.py
# Realiza estadísticas del checksum y las representa en evolución temporal
import matplotlib

matplotlib.use('Agg')  # Establecer backend no interactivo antes de importar pyplot
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.colors as mcolors
from matplotlib.ticker import AutoMinorLocator
import matplotlib.dates as mdates
import io
import base64
import sys
import os
import importlib.util


# Función para cargar el módulo funciones local de forma más robusta
def load_local_funciones():
    """Carga el módulo funciones.py del mismo directorio que este script."""
    try:
        # Obtener el directorio actual del script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        funciones_path = os.path.join(current_dir, 'funciones.py')

        print(f"DEBUG: Intentando cargar funciones desde: {funciones_path}")

        if not os.path.exists(funciones_path):
            raise ImportError(f"No se encontró funciones.py en {current_dir}")

        # Crear un nombre único para el módulo
        module_name = f"funciones_evo_tempo_{id(funciones_path)}"

        # Cargar el módulo usando importlib
        spec = importlib.util.spec_from_file_location(module_name, funciones_path)
        if spec is None:
            raise ImportError(f"No se pudo crear spec para {funciones_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        print(f"DEBUG: Módulo funciones cargado exitosamente desde {funciones_path}")
        return module

    except Exception as e:
        print(f"Error cargando módulo funciones local: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback mejorado: Cargar directamente leyendo el archivo y ejecutando
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            funciones_path = os.path.join(current_dir, 'funciones.py')
            
            import types
            funciones = types.ModuleType(f"funciones_fallback_{id(funciones_path)}")
            
            with open(funciones_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            exec(code, funciones.__dict__)
            print(f"DEBUG: Funciones cargado via exec desde {funciones_path}")
            return funciones
        except Exception as e2:
             print(f"Error en fallback de carga: {e2}")
             raise ImportError(f"No se pudo cargar el módulo funciones: {e}\nFallback error: {e2}")


# Cargar el módulo funciones local
print("DEBUG: Iniciando carga del módulo funciones...")
funciones_module = load_local_funciones()

# Importaciones desde el módulo funciones
calcular_fechas_seleccionadas = funciones_module.calcular_fechas_seleccionadas
extraer_estadisticos_temporales = funciones_module.extraer_estadisticos_temporales
configurar_ejes_temporal_compacto = funciones_module.configurar_ejes_temporal_compacto
agregar_leyenda_estadisticos = funciones_module.agregar_leyenda_estadisticos
safe_datetime_parse = funciones_module.safe_datetime_parse
extraer_datos_fecha = funciones_module.extraer_datos_fecha

print("DEBUG: Todas las funciones importadas exitosamente")


def validar_tipo_sensor_disponible(data, tipo_sensor, fechas_seleccionadas):
    """
    Valida que el tipo de sensor esté disponible en los datos.

    Args:
        data (dict): Diccionario con todos los datos del tubo.
        tipo_sensor (str): Tipo de sensor a validar.
        fechas_seleccionadas (list): Lista de fechas válidas.

    Returns:
        bool: True si el sensor está disponible, False en caso contrario.
    """
    if not data or not fechas_seleccionadas:
        return False

    print(f"DEBUG: Validando sensor '{tipo_sensor}'...")

    # Buscar el sensor directamente en los datos RAW (más confiable)
    for fecha in fechas_seleccionadas[:3]:  # Revisar las primeras 3 fechas
        if fecha not in data or 'calc' not in data[fecha]:
            continue

        calc_data = data[fecha]['calc']
        if not calc_data or not isinstance(calc_data, list) or not calc_data:
            continue

        # Verificar en el primer punto de datos
        primer_punto = calc_data[0]
        if isinstance(primer_punto, dict) and tipo_sensor in primer_punto:
            valor = primer_punto[tipo_sensor]
            print(f"DEBUG: Sensor '{tipo_sensor}' encontrado en fecha {fecha} con valor: {valor}")
            return True

    print(f"DEBUG: Sensor '{tipo_sensor}' NO encontrado en los datos RAW")
    return False


def sugerir_sensor_similar(sensor_solicitado, sensores_disponibles):
    """
    Sugiere un sensor similar si el solicitado no existe.

    Args:
        sensor_solicitado (str): Sensor que se pidió originalmente.
        sensores_disponibles (list): Lista de sensores disponibles.

    Returns:
        str or None: Sensor sugerido o None si no hay coincidencias.
    """
    if not sensor_solicitado or not sensores_disponibles:
        return None

    # Mapeo de sensores comunes con sus equivalentes
    mapeo_sensores = {
        'incr_checksum_a': ['checksum_a', 'incr_dev_a', 'incr_dev_abs_a'],
        'incr_checksum_b': ['checksum_b', 'incr_dev_b', 'incr_dev_abs_b'],
        'checksum_incr_a': ['checksum_a', 'incr_dev_a'],
        'checksum_incr_b': ['checksum_b', 'incr_dev_b'],
    }

    # Buscar mapeo directo
    if sensor_solicitado in mapeo_sensores:
        for sugerencia in mapeo_sensores[sensor_solicitado]:
            if sugerencia in sensores_disponibles:
                return sugerencia

    # Buscar por similitud de nombre (contiene palabras clave)
    palabras_clave = sensor_solicitado.lower().split('_')

    for sensor_disponible in sensores_disponibles:
        sensor_lower = sensor_disponible.lower()
        coincidencias = sum(1 for palabra in palabras_clave if palabra in sensor_lower)

        # Si al menos 50% de las palabras coinciden, sugerir
        if coincidencias >= len(palabras_clave) * 0.5:
            return sensor_disponible

    return None


def obtener_sensores_disponibles(data, fechas_seleccionadas):
    """
    Obtiene la lista de sensores disponibles en los datos.

    Args:
        data (dict): Diccionario con todos los datos del tubo.
        fechas_seleccionadas (list): Lista de fechas válidas.

    Returns:
        list: Lista de sensores disponibles.
    """
    sensores_disponibles = set()

    if not data or not fechas_seleccionadas:
        return []

    # DIAGNÓSTICO DETALLADO: Buscar sensores directamente en los datos crudos
    print("DEBUG: === DIAGNÓSTICO DE SENSORES DISPONIBLES ===")

    for fecha in fechas_seleccionadas[:3]:  # Revisar las primeras 3 fechas
        if fecha not in data:
            print(f"DEBUG: Fecha {fecha} no está en data")
            continue

        if 'calc' not in data[fecha]:
            print(f"DEBUG: Fecha {fecha} no tiene 'calc'")
            continue

        calc_data = data[fecha]['calc']
        if not calc_data or not isinstance(calc_data, list):
            print(f"DEBUG: Fecha {fecha} - calc_data está vacío o no es lista")
            continue

        if not calc_data:
            print(f"DEBUG: Fecha {fecha} - calc_data es lista vacía")
            continue

        # Obtener campos del primer punto de datos
        primer_punto = calc_data[0]
        if isinstance(primer_punto, dict):
            campos_raw = list(primer_punto.keys())
            print(f"DEBUG: Fecha {fecha} - Campos RAW del primer punto: {sorted(campos_raw)}")

            # Verificar específicamente los campos de checksum
            checksum_fields = [k for k in campos_raw if 'checksum' in k.lower()]
            print(f"DEBUG: Fecha {fecha} - Campos de checksum encontrados: {checksum_fields}")

            # Agregar todos los campos encontrados
            sensores_disponibles.update(campos_raw)
        else:
            print(f"DEBUG: Fecha {fecha} - primer punto no es diccionario: {type(primer_punto)}")

    # Excluir campos que no son sensores (ejes de coordenadas)
    campos_eje = {'index', 'cota_abs', 'depth'}
    sensores_finales = [s for s in sensores_disponibles if s not in campos_eje]

    print(f"DEBUG: === SENSORES FINALES DETECTADOS ===")
    print(f"DEBUG: Total campos encontrados: {len(sensores_disponibles)}")
    print(f"DEBUG: Sensores finales (sin ejes): {sorted(sensores_finales)}")
    print(f"DEBUG: ========================================")

    return sorted(sensores_finales)


def grafico_incli_evo_std_chk(data, parametros):
    """
    Genera un gráfico de evolución temporal de estadísticos del checksum.

    Args:
        data (dict): Diccionario con todos los datos del tubo.
        parametros (dict): Diccionario con parámetros de configuración.

    Returns:
        str: Imagen del gráfico en formato PNG/SVG codificada en base64.
    """
    try:
        print("DEBUG: Iniciando generación del gráfico de estadísticos del checksum")

        # ========================================
        # 1. EXTRAER Y VALIDAR PARÁMETROS
        # ========================================

        # Parámetros esenciales (desde JSON)
        tipo_checksum = parametros.get('sensor', 'checksum_a')
        mostrar_titulo = parametros.get('mostrar_titulo', True)
        fecha_inicial = parametros.get('fecha_inicial', None)
        fecha_final = parametros.get('fecha_final', None)
        dpi = parametros.get('dpi', 100)

        # Parámetros con valores por defecto (no configurables desde JSON)
        nombre_sensor = parametros.get('nombre_sensor', 'SENSOR')
        eje = parametros.get('eje', 'cota_abs')
        ancho_cm = parametros.get('ancho_cm', 20)
        alto_cm = parametros.get('alto_cm', 15)
        titulo_personalizado = parametros.get('titulo_personalizado', tipo_checksum.upper())
        estadisticos_activos = parametros.get('estadisticos_activos', ['rms', 'std', 'iqr', 'drift'])

        # Validaciones básicas
        if not data:
            raise ValueError("Los datos no pueden estar vacíos")

        print(f"DEBUG: Procesando estadísticos para sensor: {tipo_checksum}")
        print(f"DEBUG: Rango de fechas: {fecha_inicial} - {fecha_final}")

        # ========================================
        # 2. INSPECCIONAR ESTRUCTURA DE DATOS
        # ========================================

        if data:
            fechas_muestra = [k for k in data.keys() if k not in ["info", "umbrales"]][:3]
            print(f"DEBUG: Fechas de muestra disponibles: {fechas_muestra}")
            for fecha in fechas_muestra:
                if isinstance(data[fecha], dict):
                    print(f"DEBUG: Estructura de {fecha}: {list(data[fecha].keys())}")
                    if 'campaign_info' in data[fecha]:
                        print(f"DEBUG: campaign_info de {fecha}: {data[fecha]['campaign_info']}")
                    else:
                        print(f"DEBUG: {fecha} NO tiene campaign_info")

        # ========================================
        # 3. CALCULAR FECHAS SELECCIONADAS
        # ========================================

        fechas_seleccionadas = calcular_fechas_seleccionadas(
            data, fecha_inicial, fecha_final
        )

        if not fechas_seleccionadas:
            # Proporcionar información detallada sobre el problema
            fechas_disponibles = [f for f in data.keys() if f not in ["info", "umbrales"]]
            error_msg = f"No se encontraron fechas válidas. "
            error_msg += f"Fechas disponibles: {len(fechas_disponibles)}. "
            if fechas_disponibles:
                error_msg += f"Ejemplo: {fechas_disponibles[0]}. "
                if fechas_disponibles[0] in data:
                    estructura = list(data[fechas_disponibles[0]].keys())
                    error_msg += f"Estructura: {estructura}. "
            error_msg += f"Rango solicitado: {fecha_inicial} - {fecha_final}"
            raise ValueError(error_msg)

        print(f"DEBUG: {len(fechas_seleccionadas)} fechas seleccionadas")

        # ========================================
        # 4. VALIDAR SENSOR DISPONIBLE
        # ========================================

        # Validar que el sensor existe en los datos (validación dinámica)
        if not validar_tipo_sensor_disponible(data, tipo_checksum, fechas_seleccionadas):
            sensores_disponibles = obtener_sensores_disponibles(data, fechas_seleccionadas)

            # Intentar sugerir un sensor similar
            sensor_sugerido = sugerir_sensor_similar(tipo_checksum, sensores_disponibles)

            if sensor_sugerido:
                print(
                    f"DEBUG: Sensor '{tipo_checksum}' no encontrado, usando sugerencia automática: '{sensor_sugerido}'")
                # Usar el sensor sugerido automáticamente
                tipo_checksum = sensor_sugerido
                titulo_personalizado = parametros.get('titulo_personalizado', tipo_checksum.upper())

                # Validar que la sugerencia funciona
                if not validar_tipo_sensor_disponible(data, tipo_checksum, fechas_seleccionadas):
                    error_msg = f"Sensor '{parametros.get('sensor', 'N/A')}' no encontrado y la sugerencia automática '{sensor_sugerido}' tampoco funciona. "
                    error_msg += f"Sensores disponibles: {sensores_disponibles}"
                    raise ValueError(error_msg)
            else:
                error_msg = f"Sensor '{tipo_checksum}' no encontrado en los datos. "
                error_msg += f"Sensores disponibles: {sensores_disponibles}"
                raise ValueError(error_msg)

        print(f"DEBUG: Sensor '{tipo_checksum}' validado exitosamente")

        # ========================================
        # 5. EXTRAER ESTADÍSTICOS TEMPORALES
        # ========================================

        print(f"DEBUG: Extrayendo estadísticos para {tipo_checksum}")
        estadisticos = extraer_estadisticos_temporales(data, fechas_seleccionadas, eje, tipo_checksum)

        if not estadisticos:
            raise ValueError("No se pudieron calcular estadísticos")

        # Verificar que hay datos válidos en los estadísticos
        datos_validos = False
        for tipo_est, valores in estadisticos.items():
            valores_no_none = [v for v in valores if v is not None]
            if valores_no_none:
                datos_validos = True
                print(f"DEBUG: {tipo_est} tiene {len(valores_no_none)} valores válidos de {len(valores)} total")
            else:
                print(f"DEBUG: {tipo_est} no tiene valores válidos")

        if not datos_validos:
            raise ValueError(f"No se encontraron datos válidos de {tipo_checksum} en las fechas seleccionadas")

        # ========================================
        # 6. CONVERTIR FECHAS A DATETIME
        # ========================================

        # Convertir fechas a datetime ANTES de configurar el gráfico
        fechas_dt = []
        for fecha_str in sorted(fechas_seleccionadas, key=safe_datetime_parse):
            try:
                fecha_dt = safe_datetime_parse(fecha_str)
                if fecha_dt != datetime.min:  # Solo agregar fechas válidas
                    fechas_dt.append(fecha_dt)
            except Exception as e:
                print(f"Warning: Error al convertir fecha {fecha_str}: {e}")
                continue

        if not fechas_dt:
            raise ValueError("No se pudieron convertir las fechas a formato datetime")

        print(f"DEBUG: {len(fechas_dt)} fechas convertidas a datetime correctamente")

        # ========================================
        # 7. CONFIGURAR DIMENSIONES Y GRÁFICO
        # ========================================

        # Calcular dimensiones una sola vez
        ancho_pulgadas = ancho_cm / 2.54
        alto_pulgadas = alto_cm / 2.54

        # Configurar el gráfico con ajustes mejorados
        fig, ax = plt.subplots(figsize=(ancho_pulgadas, alto_pulgadas))
        fig.subplots_adjust(left=0.12, right=0.95, top=0.88, bottom=0.15)

        # ========================================
        # 8. CONFIGURAR EJES
        # ========================================

        etiqueta_y = "Checksum (mm)" if "drift" not in estadisticos_activos else "Valor"
        configurar_ejes_temporal_compacto(ax, fechas_dt, titulo_personalizado, etiqueta_y)

        # ========================================
        # 9. DEFINIR ESTILOS Y GRAFICAR
        # ========================================

        # Definir estilos para cada estadístico
        estilos_estadisticos = {
            'rms': {'color': '#1f77b4', 'linewidth': 2.5, 'linestyle': '-',
                    'marker': 'o', 'markersize': 4, 'alpha': 1.0},
            'std': {'color': '#ff7f0e', 'linewidth': 2.0, 'linestyle': '--',
                    'marker': 's', 'markersize': 4, 'alpha': 0.9},
            'iqr': {'color': '#2ca02c', 'linewidth': 2.0, 'linestyle': '-.',
                    'marker': '^', 'markersize': 4, 'alpha': 0.9},
            'drift': {'color': '#d62728', 'linewidth': 2.0, 'linestyle': ':',
                      'marker': 'D', 'markersize': 4, 'alpha': 0.9}
        }

        # Graficar cada estadístico activo
        series_graficadas = 0
        y_min, y_max = float('inf'), float('-inf')

        for tipo_est in estadisticos_activos:
            if tipo_est in estadisticos and tipo_est in estilos_estadisticos:
                valores = estadisticos[tipo_est]
                estilo = estilos_estadisticos[tipo_est]

                # Filtrar valores None - asegurar que fechas_dt y valores tienen la misma longitud
                datos_validos = []
                for i, (fecha_dt, valor) in enumerate(zip(fechas_dt, valores)):
                    if valor is not None:
                        datos_validos.append((fecha_dt, valor))

                if datos_validos:
                    fechas_validas = [d[0] for d in datos_validos]
                    valores_validos = [d[1] for d in datos_validos]

                    # Actualizar límites Y
                    y_min = min(y_min, min(valores_validos))
                    y_max = max(y_max, max(valores_validos))

                    # Graficar
                    ax.plot(fechas_validas, valores_validos,
                            color=estilo['color'],
                            linewidth=estilo['linewidth'],
                            linestyle=estilo['linestyle'],
                            marker=estilo['marker'],
                            markersize=estilo['markersize'],
                            alpha=estilo['alpha'],
                            label=tipo_est.upper())

                    series_graficadas += 1
                    print(f"DEBUG: Graficado {tipo_est} con {len(valores_validos)} puntos")

        if series_graficadas == 0:
            raise ValueError("No se pudieron graficar estadísticos")

        print(f"DEBUG: {series_graficadas} estadísticos graficados exitosamente")

        # ========================================
        # 10. AJUSTAR LÍMITES Y REFERENCIAS
        # ========================================

        # Ajustar límites Y con margen PRIMERO
        if y_min != float('inf') and y_max != float('-inf'):
            margen = (y_max - y_min) * 0.15  # Margen un poco mayor
            ax.set_ylim(y_min - margen, y_max + margen)

        # Agregar línea de referencia en cero
        ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)

        # Agregar líneas de umbral (opcional) - solo si están dentro del rango visible
        if parametros.get('mostrar_umbral', False):  # Cambiado a False por defecto
            umbral = parametros.get('umbral_checksum', 0.1)  # Reducido a 0.1 mm por defecto

            # Solo mostrar umbral si está dentro del rango de datos
            y_limite_actual = ax.get_ylim()[1]
            if umbral <= y_limite_actual:
                ax.axhline(y=umbral, color='red', linestyle='--', linewidth=1, alpha=0.7)
                ax.axhline(y=-umbral, color='red', linestyle='--', linewidth=1, alpha=0.7)

                # Posicionar el texto del umbral de manera más inteligente
                pos_x = fechas_dt[int(len(fechas_dt) * 0.8)]  # 80% del eje X
                ax.text(pos_x, umbral, f' ±{umbral}mm',
                        color='red', fontsize=8, va='bottom', ha='left')

        # ========================================
        # 11. AGREGAR LEYENDA
        # ========================================

        agregar_leyenda_estadisticos(ax, estadisticos_activos)

        # ========================================
        # 12. GUARDAR Y DEVOLVER IMAGEN
        # ========================================

        # Guardar como imagen
        buffer = io.BytesIO()
        formato = parametros.get('formato', 'png').lower()

        if formato == 'svg':
            plt.savefig(buffer, format='svg', bbox_inches=None, pad_inches=0, facecolor='white')
        else:
            plt.savefig(buffer, format='png', dpi=dpi, bbox_inches=None, pad_inches=0, facecolor='white')

        buffer.seek(0)
        imagen_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close(fig)

        print("DEBUG: Gráfico de estadísticos generado exitosamente")

        # Devolver data URL
        if formato == 'svg':
            return f"data:image/svg+xml;base64,{imagen_base64}"
        else:
            return f"data:image/png;base64,{imagen_base64}"

    except Exception as e:
        error_msg = f"ERROR: Error al generar gráfico de estadísticos: {str(e)}"
        print(error_msg)

        # Proporcionar información adicional de debug
        if 'data' in locals() and data:
            fechas_disponibles = [f for f in data.keys() if f not in ["info", "umbrales"]]
            print(f"DEBUG: Error ocurrió con {len(fechas_disponibles)} fechas disponibles")
            if fechas_disponibles:
                print(f"DEBUG: Ejemplo de fecha: {fechas_disponibles[0]}")
                if fechas_disponibles[0] in data:
                    print(f"DEBUG: Estructura de ejemplo: {list(data[fechas_disponibles[0]].keys())}")

        if 'fig' in locals():
            plt.close(fig)
        raise RuntimeError(error_msg)


# Para pruebas locales
if __name__ == "__main__":
    print("Script de análisis estadístico de checksum cargado correctamente")
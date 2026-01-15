# grafico_incli_0.py
import matplotlib

matplotlib.use('Agg')  # Establecer backend no interactivo antes de importar pyplot
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.colors as mcolors
from matplotlib.ticker import AutoMinorLocator
import io
import base64

# Importar funciones desde el archivo funciones.py
from funciones import (
    calcular_fechas_seleccionadas,
    determinar_fecha_slider,
    generar_info_colores,
    obtener_leyenda_umbrales,
    obtener_color_para_fecha,
    extraer_datos_fecha,
    agregar_umbrales,
    configurar_ejes,
    obtener_datos_sensor
)



def grafico_incli_0(data, parametros):
    """
    Genera un gráfico de inclinometría para visualizar desplazamientos o inclinaciones.

    Args:
        data (dict): Diccionario con todos los datos del tubo, incluyendo campañas y umbrales.
        parametros (dict): Diccionario con parámetros de configuración y visualización.
            - nombre_sensor (str): Nombre del sensor o inclinómetro.
            - sensor (str): Tipo de sensor a visualizar ("desp_a", "desp_b", "incr_dev_abs_a", etc).
            - fecha_inicial (str): Fecha de inicio del rango a considerar (formato ISO).
            - fecha_final (str): Fecha final del rango a considerar (formato ISO).
            - total_camp (int): Total de campañas a mostrar.
            - ultimas_camp (int): Número de últimas campañas a mostrar.
            - cadencia_dias (int): Intervalo en días entre campañas.
            - color_scheme (str): Esquema de colores ("monocromo" o "multicromo").
            - escala_desplazamiento (str): Tipo de escala para gráficos de desplazamiento.
            - escala_incremento (str): Tipo de escala para gráficos incrementales.
            - valor_positivo_desplazamiento (float): Límite superior para escala de desplazamiento.
            - valor_negativo_desplazamiento (float): Límite inferior para escala de desplazamiento.
            - valor_positivo_incremento (float): Valor máximo para escala incremental.
            - valor_negativo_incremento (float): Valor mínimo para escala incremental.
            - eje (str): Unidades del eje vertical ("index", "cota_abs", "depth").
            - orden (bool): Orden ascendente (True) o descendente (False).
            - ancho_cm (float): Ancho del gráfico en centímetros.
            - alto_cm (float): Alto del gráfico en centímetros.
            - dpi (int): Resolución de la imagen en puntos por pulgada.

    Returns:
        str: Imagen del gráfico en formato PNG codificada en base64 (data URL).
    """
    try:
        # PASO 1: Extraer parámetros con valores por defecto si no están presentes
        nombre_sensor = parametros.get('nombre_sensor', 'SENSOR')
        sensor = parametros.get('sensor', 'desp_a')
        fecha_inicial = parametros.get('fecha_inicial', None)
        fecha_final = parametros.get('fecha_final', None)
        total_camp = parametros.get('total_camp', 30)
        ultimas_camp = parametros.get('ultimas_camp', 30)
        cadencia_dias = parametros.get('cadencia_dias', 30)
        color_scheme = parametros.get('color_scheme', 'monocromo')
        escala_desplazamiento = parametros.get('escala_desplazamiento', 'manual')
        escala_incremento = parametros.get('escala_incremento', 'manual')
        valor_positivo_desplazamiento = parametros.get('valor_positivo_desplazamiento', 20)
        valor_negativo_desplazamiento = parametros.get('valor_negativo_desplazamiento', -20)
        valor_positivo_incremento = parametros.get('valor_positivo_incremento', 1)
        valor_negativo_incremento = parametros.get('valor_negativo_incremento', -1)
        eje = parametros.get('eje', 'cota_abs')
        orden = parametros.get('orden', True)
        ancho_cm = parametros.get('ancho_cm', 21)
        alto_cm = parametros.get('alto_cm', 29.7)
        dpi = parametros.get('dpi', 100)
        mostrar_titulo = parametros.get('mostrar_titulo', True)
        etiqueta_eje_x = parametros.get('etiqueta_eje_x', "Desplazamiento (mm)")
        # Obtener el formato del gráfico (png por defecto)
        formato = parametros.get('formato', 'png')

        # Validación de parámetros críticos
        if not data:
            raise ValueError("Los datos no pueden estar vacíos")

        if total_camp <= 0 or ultimas_camp < 0 or cadencia_dias < 0:
            raise ValueError("Los parámetros de campaña deben ser valores positivos")

        # PASO 2: Calcular dimensiones en pulgadas para matplotlib (1 pulgada = 2.54 cm)
        ancho_pulgadas = ancho_cm / 2.54
        alto_pulgadas = alto_cm / 2.54

        # PASO 3: Calcular las fechas seleccionadas en base a los parámetros
        fechas_seleccionadas = calcular_fechas_seleccionadas(
            data,
            fecha_inicial,
            fecha_final,
            total_camp,
            ultimas_camp,
            cadencia_dias
        )

        # Verificar que hay fechas seleccionadas
        if not fechas_seleccionadas:
            raise ValueError("No se encontraron fechas válidas para procesar")

        # PASO 4: Determinar la última fecha activa como fecha_slider por defecto
        fecha_slider = determinar_fecha_slider(data, fechas_seleccionadas)

        # Verificar que fecha_slider es válida
        if not fecha_slider or fecha_slider not in data:
            raise ValueError("No se pudo determinar una fecha válida para destacar")

        # PASO 5: Generar información de colores para cada fecha
        fechas_colores = generar_info_colores(fechas_seleccionadas, color_scheme)

        # PASO 6: Preparar diccionario de umbrales (leyenda_umbrales)
        # Obtener colores configurados en la interfaz desde parámetros
        leyenda_umbrales_interfaz = parametros.get('leyenda_umbrales', {})
        leyenda_umbrales = obtener_leyenda_umbrales(data, leyenda_umbrales_interfaz)

        # PASO 7: Configurar el gráfico
        fig, ax = plt.subplots(figsize=(ancho_pulgadas, alto_pulgadas))

        # Variable para almacenar el título del gráfico
        titulo_grafico = "Desplazamiento"

        # PASO 8: Procesar y graficar las series no seleccionadas
        for fecha in fechas_seleccionadas:
            if fecha in data and "calc" in data[fecha] and fecha != fecha_slider:
                # Obtener color y datos
                color = obtener_color_para_fecha(fecha, fechas_colores)
                datos = extraer_datos_fecha(fecha, data, eje)
                if not datos:
                    continue

                # Definir parámetros para series no seleccionadas
                grosor = 1.5
                opacidad = 0.7

                # Obtener los datos según el tipo de gráfico usando la función auxiliar
                x_data, titulo_grafico = obtener_datos_sensor(datos, sensor)

                # Añadir la serie al gráfico (sin label para evitar leyenda)
                ax.plot(x_data, datos['eje_Y'], color=color, linewidth=grosor, alpha=opacidad)

        # PASO 9: Procesar y graficar la serie seleccionada (encima)
        if fecha_slider in fechas_seleccionadas and fecha_slider in data and "calc" in data[fecha_slider]:
            datos = extraer_datos_fecha(fecha_slider, data, eje)
            if datos:
                # Parámetros para la serie seleccionada
                color = 'darkblue'
                grosor = 3
                opacidad = 1.0

                # Obtener los datos según el tipo de gráfico usando la función auxiliar
                x_data, titulo_grafico = obtener_datos_sensor(datos, sensor)

                # Añadir la serie seleccionada (sin label para evitar leyenda)
                ax.plot(x_data, datos['eje_Y'], color=color, linewidth=grosor, alpha=opacidad)

        # PASO 10: Añadir los umbrales si están disponibles
        if fecha_slider and fecha_slider in data:
            agregar_umbrales(ax, data, leyenda_umbrales, eje, sensor, fecha_slider)

        # PASO 11: Configurar ejes
        configurar_ejes(
            ax,
            sensor,
            escala_desplazamiento,
            escala_incremento,
            valor_positivo_desplazamiento,
            valor_negativo_desplazamiento,
            valor_positivo_incremento,
            valor_negativo_incremento,
            eje,
            orden,
            titulo_grafico,
            etiqueta_eje_x
        )

        # PASO 12: Configurar título pegado al borde superior (SIN leyenda)
        if mostrar_titulo:
            # Solo mostrar el tipo de desplazamiento, pegado al borde superior
            plt.title(titulo_grafico, fontsize=12, pad=2)  # pad=2 para pegarlo al borde

        # Asignar etiqueta al eje X si está configurada
        if etiqueta_eje_x:
            ax.set_xlabel(etiqueta_eje_x)

        # PASO 13: Eliminar cualquier leyenda existente
        if ax.get_legend():
            ax.get_legend().remove()

        # PASO 14: Ajustar layout para ocupar 100% del alto sin distorsiones
        plt.tight_layout(pad=0.1)  # Mínimo padding para evitar recortes

        # PASO 15: Guardar como imagen en el formato especificado SIN gap
        buffer = io.BytesIO()

        # Usar el formato especificado sin padding para eliminar gaps
        if formato.lower() == 'svg':
            plt.savefig(buffer, format='svg', bbox_inches='tight', pad_inches=0)
        else:  # Por defecto, usar PNG
            plt.savefig(buffer, format='png', dpi=dpi, bbox_inches='tight', pad_inches=0)

        buffer.seek(0)

        # PASO 16: Codificar en base64 para enviar a través de HTTP
        imagen_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close(fig)

        # Devolver el data URL con el tipo MIME correcto
        if formato.lower() == 'svg':
            return f"data:image/svg+xml;base64,{imagen_base64}"
        else:
            return f"data:image/png;base64,{imagen_base64}"

    except Exception as e:
        # Manejo de errores: cerrar figura si existe y re-lanzar excepción
        if 'fig' in locals():
            plt.close(fig)
        raise RuntimeError(f"Error al generar gráfico: {str(e)}")
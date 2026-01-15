# grafico_incli_evo_tempo.py
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
        # Fallback: intentar importación normal
        try:
            # Forzar la búsqueda del módulo funciones en el directorio actual
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)

            import funciones
            print(f"DEBUG: Funciones importado usando fallback desde {funciones.__file__}")
            return funciones
        except ImportError:
            raise ImportError(f"No se pudo cargar el módulo funciones: {e}")


# Cargar el módulo funciones local
print("DEBUG: Iniciando carga del módulo funciones...")
funciones_module = load_local_funciones()

# Importar las funciones específicas desde el módulo cargado
calcular_fechas_seleccionadas = funciones_module.calcular_fechas_seleccionadas
determinar_fecha_slider = funciones_module.determinar_fecha_slider
generar_info_colores = funciones_module.generar_info_colores
obtener_leyenda_umbrales = funciones_module.obtener_leyenda_umbrales
obtener_color_para_fecha = funciones_module.obtener_color_para_fecha
extraer_datos_fecha = funciones_module.extraer_datos_fecha
agregar_umbrales = funciones_module.agregar_umbrales
configurar_ejes = funciones_module.configurar_ejes
interpolar_def_tubo = funciones_module.interpolar_def_tubo
seleccionar_profundidades_distribuidas = funciones_module.seleccionar_profundidades_distribuidas
extraer_datos_temporales_profundidades = funciones_module.extraer_datos_temporales_profundidades
agregar_anotaciones_finales = funciones_module.agregar_anotaciones_finales


print("DEBUG: Todas las funciones importadas exitosamente")


def configurar_ejes_temporal_compacto(ax, fechas_dt, eje, titulo, etiqueta_eje_y="Desplazamiento (mm)",
                                      reservar_espacio_anotaciones=True):
    """
    Configura los ejes para un gráfico temporal compacto sin padding.
    NUEVA LÓGICA: Reserva espacio a la derecha para anotaciones.
    """
    if not ax or not fechas_dt:
        return None

    try:
        # Configurar formato de fechas en el eje X con formato mm-aa (ej: 01-24)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%y'))

        # Estrategia automática para mostrar fechas mensuales sin pisarse
        num_fechas = len(fechas_dt)
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

        # Rotar etiquetas para aprovechar mejor el espacio
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)

        # Forzar rotación de todas las etiquetas (incluyendo la primera)
        for label in ax.get_xticklabels():
            label.set_rotation(45)
            label.set_horizontalalignment('right')
        # Configurar etiquetas de ejes con tamaño reducido (SIN título "Fecha")
        ax.set_ylabel(etiqueta_eje_y, fontfamily='Arial', fontsize=9, color='#4B5563')

        # Configurar rejilla más sutil
        ax.grid(True, linestyle='--', alpha=0.4, color='#E5E7EB', linewidth=0.6)
        ax.axhline(y=0, color='#D1D5DB', linestyle='-', linewidth=0.5)

        # Configurar bordes del gráfico
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#9CA3AF')
        ax.spines['bottom'].set_color('#9CA3AF')
        ax.spines['left'].set_linewidth(0.8)
        ax.spines['bottom'].set_linewidth(0.8)
        ax.set_facecolor('white')

        # Configurar ticks más pequeños
        ax.tick_params(labelsize=7, colors='#6B7280')
        ax.tick_params(which='minor', length=1, colors='#D1D5DB')
        ax.tick_params(which='major', length=3, colors='#9CA3AF')

        # LÓGICA DE RESERVA DE ESPACIO MEJORADA
        if len(fechas_dt) > 1:
            fechas_ordenadas = sorted(fechas_dt)

            if reservar_espacio_anotaciones:
                # LÓGICA SIMPLIFICADA Y CLARA
                fecha_inicio = fechas_ordenadas[0]
                fecha_fin_datos = fechas_ordenadas[-1]  # Donde terminan los datos reales

                # Calcular el rango temporal de los datos
                rango_datos = fecha_fin_datos - fecha_inicio

                # Agregar 25% más de espacio para las anotaciones (20% para anotaciones + 5% margen)
                extension_temporal = rango_datos * 0.25
                fecha_fin_total = fecha_fin_datos + extension_temporal

                print(f"DEBUG: === CONFIGURACIÓN DE ESPACIO ===")
                print(f"DEBUG: Inicio: {fecha_inicio}")
                print(f"DEBUG: Fin de datos: {fecha_fin_datos}")
                print(f"DEBUG: Fin total (con espacio): {fecha_fin_total}")
                print(f"DEBUG: Extensión agregada: {extension_temporal}")

                # Establecer límites del gráfico
                ax.set_xlim(fecha_inicio, fecha_fin_total)

                # Retornar donde terminan realmente los datos
                return fecha_fin_datos
            else:
                # Sin reserva de espacio (comportamiento original)
                ax.set_xlim(fechas_ordenadas[0], fechas_ordenadas[-1])
                return fechas_ordenadas[-1]

        # Ajustar límites del eje Y para optimizar el espacio
        ax.margins(x=0.01, y=0.05)


        return None

    except Exception as e:
        print(f"Error al configurar ejes temporales: {e}")
        return None


def grafico_incli_evo_tempo(data, parametros):
    """
    Genera un gráfico de evolución temporal de inclinometría mostrando desplazamientos a lo largo del tiempo
    para múltiples profundidades distribuidas homogéneamente.

    Args:
        data (dict): Diccionario con todos los datos del tubo, incluyendo campañas y umbrales.
        parametros (dict): Diccionario con parámetros de configuración y visualización.
            - nombre_sensor (str): Nombre del sensor o inclinómetro.
            - sensor (str): Tipo de sensor a visualizar ("desp_a", "desp_b", "desp_total").
            - fecha_inicial (str): Fecha de inicio del rango a considerar (formato ISO).
            - fecha_final (str): Fecha final del rango a considerar (formato ISO).
            - total_camp (int): Total de campañas a mostrar.
            - ultimas_camp (int): Número de últimas campañas a mostrar.
            - cadencia_dias (int): Intervalo en días entre campañas.
            - eje (str): Unidades del eje vertical ("index", "cota_abs", "depth").
            - orden (bool): Orden ascendente (True) o descendente (False).
            - ancho_cm (float): Ancho del gráfico en centímetros.
            - alto_cm (float): Alto del gráfico en centímetros.
            - dpi (int): Resolución de la imagen en puntos por pulgada.
            - num_profundidades (int): Número de profundidades a mostrar (por defecto 5).
            - mostrar_titulo (bool): Si mostrar título o no.
            - titulo_personalizado (str): Título personalizado del gráfico.

    Returns:
        str: Imagen del gráfico en formato PNG codificada en base64 (data URL).
    """
    try:
        print("DEBUG: Iniciando generación del gráfico temporal")

        # PASO 1: Extraer parámetros con valores por defecto si no están presentes
        nombre_sensor = parametros.get('nombre_sensor', 'SENSOR')
        sensor = parametros.get('sensor', 'desp_a')
        fecha_inicial = parametros.get('fecha_inicial', None)
        fecha_final = parametros.get('fecha_final', None)
        total_camp = parametros.get('total_camp', 30)
        ultimas_camp = parametros.get('ultimas_camp', 30)
        cadencia_dias = parametros.get('cadencia_dias', 30)
        eje = parametros.get('eje', 'cota_abs')
        orden = parametros.get('orden', True)
        ancho_cm = parametros.get('ancho_cm', 15)
        alto_cm = parametros.get('alto_cm', 20)
        dpi = parametros.get('dpi', 100)
        num_profundidades = parametros.get('num_profundidades', 5)
        mostrar_titulo = parametros.get('mostrar_titulo', True)  # <- CAMBIAR A True
        titulo_personalizado = parametros.get('titulo_personalizado', f'Evo. temp. {sensor.upper()}')
        etiqueta_eje_y = parametros.get('etiqueta_eje_y', "Desplazamiento (mm)")
        formato = parametros.get('formato', 'png')

        print(f"DEBUG: Parámetros extraídos - sensor: {sensor}, eje: {eje}, num_profundidades: {num_profundidades}")

        # Validación de parámetros críticos
        if not data:
            raise ValueError("Los datos no pueden estar vacíos")

        if total_camp <= 0 or ultimas_camp < 0 or cadencia_dias < 0:
            raise ValueError("Los parámetros de campaña deben ser valores positivos")

        if num_profundidades <= 0 or num_profundidades > 10:
            raise ValueError("El número de profundidades debe estar entre 1 y 10")

        # PASO 2: Calcular dimensiones en pulgadas para matplotlib (1 pulgada = 2.54 cm)
        ancho_pulgadas = ancho_cm / 2.54
        alto_pulgadas = alto_cm / 2.54

        # PASO 3: Calcular las fechas seleccionadas en base a los parámetros
        print("DEBUG: Calculando fechas seleccionadas...")
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

        print(f"DEBUG: {len(fechas_seleccionadas)} fechas seleccionadas")

        # PASO 4: Seleccionar profundidades distribuidas homogéneamente
        print("DEBUG: Seleccionando profundidades distribuidas...")
        profundidades_seleccionadas = seleccionar_profundidades_distribuidas(
            data, eje, num_profundidades
        )

        if not profundidades_seleccionadas:
            raise ValueError("No se pudieron seleccionar profundidades válidas")

        # ORDENAR LAS PROFUNDIDADES DE MAYOR A MENOR (índice mayor primero)
        profundidades_seleccionadas = sorted(profundidades_seleccionadas, reverse=True)

        print(
            f"DEBUG: {len(profundidades_seleccionadas)} profundidades seleccionadas (ordenadas mayor a menor): {profundidades_seleccionadas}")

        # PASO 5: Extraer datos temporales para las profundidades seleccionadas
        print("DEBUG: Extrayendo datos temporales...")
        datos_temporales = extraer_datos_temporales_profundidades(
            data, fechas_seleccionadas, profundidades_seleccionadas, eje, sensor
        )

        if not datos_temporales:
            raise ValueError("No se pudieron extraer datos temporales")

        print(f"DEBUG: Datos temporales extraídos para {len(datos_temporales)} profundidades")

        # PASO 6: Configurar el gráfico SIN padding extra
        fig, ax = plt.subplots(figsize=(ancho_pulgadas, alto_pulgadas))

        # Configurar subplots para usar exactamente las dimensiones especificadas
        # Ajustado para dar más espacio al área del gráfico
        fig.subplots_adjust(left=0.15, right=0.95, top=0.95, bottom=0.20)

        # PASO 7: Convertir fechas (MANTENER IGUAL)
        fechas_dt = []
        for fecha_str in fechas_seleccionadas:
            try:
                fecha_dt = datetime.fromisoformat(fecha_str)
                fechas_dt.append(fecha_dt)
            except ValueError:
                print(f"Warning: No se pudo convertir la fecha {fecha_str}")
                continue

        if not fechas_dt:
            raise ValueError("No se pudieron convertir las fechas a formato datetime")

        fechas_dt_sorted = sorted(fechas_dt)
        print(f"DEBUG: {len(fechas_dt_sorted)} fechas convertidas a datetime")

        # NUEVO PASO 8: Configurar ejes PRIMERO (antes de dibujar series)
        print("DEBUG: Configurando ejes y reservando espacio...")
        limite_area_datos = configurar_ejes_temporal_compacto(ax, fechas_dt_sorted, eje, titulo_personalizado,
                                                              etiqueta_eje_y,
                                                              reservar_espacio_anotaciones=True)

        print(f"DEBUG: Límite del área de datos: {limite_area_datos}")

        # NUEVO PASO 9: Graficar series (DESPUÉS de configurar ejes)
        colores_serie = [
            "#4E79A7",  # Azul moderado
            "#F28E2B",  # Naranja apagado
            "#E15759",  # Rojo suave
            "#76B7B2",  # Verde grisáceo
            "#59A14F",  # Verde bosque
            "#EDC948",  # Amarillo mostaza
            "#B07AA1",  # Morado suave
            "#FF9DA7",  # Rosa pálido
            "#9C755F",  # Marrón claro
            "#BAB0AC",  # Gris medio
        ]

        series_graficadas = 0
        for i, profundidad in enumerate(profundidades_seleccionadas):
            if profundidad in datos_temporales:
                valores_originales = datos_temporales[profundidad]

                # Crear las listas de fechas y valores ordenadas cronológicamente
                fechas_valores = list(zip(fechas_seleccionadas, valores_originales))
                fechas_valores_sorted = sorted(fechas_valores, key=lambda x: datetime.fromisoformat(x[0]))

                # Separar fechas y valores ordenados
                fechas_ordenadas = [datetime.fromisoformat(fv[0]) for fv in fechas_valores_sorted]
                valores_ordenados = [fv[1] for fv in fechas_valores_sorted]

                # Verificar que tenemos datos válidos
                if len(valores_ordenados) > 0:
                    color = colores_serie[i % len(colores_serie)]

                    # Graficar la serie temporal
                    ax.plot(fechas_ordenadas, valores_ordenados,
                            color=color,
                            linewidth=1.5,
                            marker=None,  # o marker="o" con markersize=3 y alpha=0.
                            markersize=3,
                            label=f'{eje}: {profundidad}')

                    series_graficadas += 1
                else:
                    print(f"Warning: Descartando profundidad {profundidad} - sin datos válidos")

        print(f"DEBUG: {series_graficadas} series graficadas exitosamente")

        # NUEVO PASO 10: Agregar leyenda DESPUÉS de dibujar las series
        """
        if True:  # mostrar_leyenda
            legend = ax.legend(
                loc='upper left',
                fontsize=7,
                frameon=True,
                fancybox=False,
                shadow=False,
                framealpha=0.9,
                edgecolor='#D1D5DB',
                facecolor='white',
                borderpad=0.3,
                columnspacing=0.5,
                handlelength=1.0,
                handletextpad=0.3,
                labelspacing=0.2
            )
            legend.get_frame().set_linewidth(0.5)
        """

        # NUEVO PASO 11: Agregar anotaciones finales
        agregar_anotaciones_finales(ax, datos_temporales, profundidades_seleccionadas,
                                    fechas_dt_sorted, colores_serie, eje, limite_area_datos)

        # PASO 11a: Configurar título si es necesario (compacto)
        if mostrar_titulo:
            ax.set_title(titulo_personalizado, fontsize=11, pad=8, fontweight='normal')

        # PASO 12: Guardar como imagen en el formato especificado
        buffer = io.BytesIO()

        # Usar el formato especificado con configuración precisa
        if formato.lower() == 'svg':
            plt.savefig(buffer, format='svg',
                        bbox_inches=None,  # No recortar automáticamente
                        pad_inches=0,  # Sin padding adicional
                        facecolor='white')
        else:  # Por defecto, usar PNG
            plt.savefig(buffer, format='png', dpi=dpi,
                        bbox_inches=None,  # No recortar automáticamente
                        pad_inches=0,  # Sin padding adicional
                        facecolor='white')

        buffer.seek(0)

        # PASO 13: Codificar en base64 para enviar a través de HTTP
        imagen_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close(fig)

        print("DEBUG: Gráfico generado exitosamente")

        # Devolver el data URL con el tipo MIME correcto
        if formato.lower() == 'svg':
            return f"data:image/svg+xml;base64,{imagen_base64}"
        else:
            return f"data:image/png;base64,{imagen_base64}"

    except Exception as e:
        # Manejo de errores: cerrar figura si existe y re-lanzar excepción
        print(f"ERROR: Error al generar gráfico temporal: {str(e)}")
        if 'fig' in locals():
            plt.close(fig)
        raise RuntimeError(f"Error al generar gráfico temporal: {str(e)}")
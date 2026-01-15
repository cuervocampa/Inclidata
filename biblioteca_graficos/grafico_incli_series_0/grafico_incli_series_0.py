# grafico_incli_series_0.py (VERSIÓN REESCRITA CON CONTROL ABSOLUTO)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
import base64

import matplotlib.font_manager as fm
fuentes_disponibles = [f.name for f in fm.fontManager.ttflist]
print("Aptos disponible:", "Arial" in fuentes_disponibles)

# Importar funciones necesarias
from funciones import (
    calcular_fechas_seleccionadas,
    determinar_fecha_slider,
    generar_info_colores,
    obtener_color_para_fecha
)


def grafico_incli_series_0(data, parametros):
    """
    Genera una imagen que contiene únicamente una leyenda de fechas para gráfico de inclinometría.
    VERSIÓN REESCRITA: Control absoluto del espacio, layout adaptativo, fuente escalable.

    Args:
        data (dict): Diccionario con todos los datos del tubo, incluyendo campañas.
        parametros (dict): Parámetros de configuración:
            - fecha_inicial (str): Fecha de inicio del rango (formato ISO)
            - fecha_final (str): Fecha final del rango (formato ISO)
            - total_camp (int): Total de campañas a mostrar
            - ultimas_camp (int): Número de últimas campañas a mostrar
            - cadencia_dias (int): Intervalo en días entre campañas
            - color_scheme (str): Esquema de colores ("monocromo" o "multicromo")
            - ancho_cm (float): Ancho total de la imagen en cm
            - alto_cm (float): Alto máximo de la imagen en cm
            - dpi (int): Resolución para PNG (default: 100)
            - formato (str): 'svg' o 'png' (default: 'png')

    Returns:
        str: Data URL de la imagen generada
    """

    # Configurar fuente global para toda la figura
    plt.rcParams['font.family'] = 'Arial'

    # EXTRAER PARÁMETROS
    fecha_inicial = parametros.get('fecha_inicial', None)
    fecha_final = parametros.get('fecha_final', None)
    total_camp = parametros.get('total_camp', 30)
    ultimas_camp = parametros.get('ultimas_camp', 30)
    cadencia_dias = parametros.get('cadencia_dias', 30)
    color_scheme = parametros.get('color_scheme', 'monocromo')
    ancho_cm = parametros.get('ancho_cm', 10)
    alto_cm = parametros.get('alto_cm', 15)
    dpi = parametros.get('dpi', 100)
    formato = parametros.get('formato', 'png').lower()

    print(f"=== CREANDO LEYENDA DE FECHAS ===")
    print(f"Dimensiones objetivo: {ancho_cm} × {alto_cm} cm")
    print(f"Esquema colores: {color_scheme}, Formato: {formato}")

    # OBTENER Y PROCESAR FECHAS
    fechas_seleccionadas = calcular_fechas_seleccionadas(
        data, fecha_inicial, fecha_final, total_camp, ultimas_camp, cadencia_dias
    )

    fecha_slider = determinar_fecha_slider(data, fechas_seleccionadas)
    fechas_colores = generar_info_colores(fechas_seleccionadas, color_scheme)

    print(f"Fechas encontradas: {len(fechas_seleccionadas)}")
    print(f"Fecha destacada: {fecha_slider}")

    # PREPARAR DATOS PARA LEYENDA
    elementos_leyenda = []

    # Primero la fecha destacada (slider) si existe
    if fecha_slider and fecha_slider in fechas_seleccionadas:
        elementos_leyenda.append({
            'fecha': fecha_slider,
            'texto': f"{fecha_slider} (seleccionada)",
            'color': 'darkblue',
            'destacada': True
        })

    # Luego el resto de fechas
    for fecha in fechas_seleccionadas:
        if fecha != fecha_slider:
            color = obtener_color_para_fecha(fecha, fechas_colores)
            elementos_leyenda.append({
                'fecha': fecha,
                'texto': fecha,
                'color': color,
                'destacada': False
            })

    print(f"Elementos de leyenda: {len(elementos_leyenda)}")
    for i, elem in enumerate(elementos_leyenda[:5]):  # Mostrar solo los primeros 5
        print(f"  {i + 1}. {elem['texto']} → {elem['color']}")
    if len(elementos_leyenda) > 5:
        print(f"  ... y {len(elementos_leyenda) - 5} más")

    # CONFIGURAR FIGURA SIN GAPS
    ancho_pulgadas = ancho_cm / 2.54
    alto_pulgadas = alto_cm / 2.54

    fig = plt.figure(figsize=(ancho_pulgadas, alto_pulgadas))
    ax = fig.add_axes([0, 0, 1, 1])  # Ocupar TODA la figura sin márgenes

    ax.set_xlim(0, ancho_cm)
    ax.set_ylim(0, alto_cm)
    ax.set_aspect('equal')
    ax.set_axis_off()

    # Eliminar cualquier margen automático
    plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)

    # 1️⃣ Crea la leyenda sin argumentos inválidos
    #leg = ax.legend(loc='upper left')

    # 2️⃣ Ajusta la alineación vertical de cada etiqueta de texto
    #for txt in leg.get_texts():
    #    txt.set_va('center_baseline')  # 'top', 'center', 'bottom', 'baseline', etc.

    # CREAR CONTENIDO
    if not elementos_leyenda:
        crear_mensaje_vacio_fechas(ax, ancho_cm, alto_cm)
    else:
        crear_leyenda_fechas_adaptiva(ax, elementos_leyenda, ancho_cm, alto_cm)

    # GENERAR IMAGEN
    try:
        buffer = io.BytesIO()

        save_params = {
            'pad_inches': 0, 'bbox_inches': None, 'transparent': True,
            'facecolor': 'none', 'edgecolor': 'none'
        }

        if formato == 'svg':
            plt.savefig(buffer, format='svg', **save_params)
            mime_type = 'image/svg+xml'
        else:
            plt.savefig(buffer, format='png', dpi=dpi, **save_params)
            mime_type = 'image/png'

        buffer.seek(0)
        imagen_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        print(f"✅ Imagen generada: {formato.upper()}, {ancho_cm}×{alto_cm} cm")

        return f"data:{mime_type};base64,{imagen_base64}"

    except Exception as e:
        print(f"❌ Error generando imagen: {e}")
        raise
    finally:
        plt.close(fig)


def crear_mensaje_vacio_fechas(ax, ancho_cm, alto_cm):
    """Crea un mensaje centrado cuando no hay fechas que mostrar."""
    fondo = mpatches.Rectangle(
        (0, 0), ancho_cm, alto_cm,
        facecolor='lightgray', alpha=0.3, edgecolor='gray'
    )
    ax.add_patch(fondo)

    centro_x = ancho_cm / 2
    centro_y = alto_cm / 2
    tamano_fuente = min(ancho_cm * 2, alto_cm * 2.5)

    ax.text(centro_x, centro_y,
            "No hay fechas\ndisponibles",
            fontsize=tamano_fuente, weight='bold',
            ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    print(f"Mensaje vacío fechas: {ancho_cm}×{alto_cm} cm, fuente {tamano_fuente:.1f}pt")


def crear_leyenda_fechas_adaptiva(ax, elementos, ancho_cm, alto_cm):
    """Crea una leyenda de fechas que se adapta al espacio disponible."""

    # CONFIGURACIÓN DE GAPS
    gap_borde = 0.1  # Gap entre elementos y borde
    gap_indicador_texto = 0.1  # Gap entre indicador y texto
    titulo_altura = 0.8  # Altura reservada para título

    # CALCULAR ÁREA ÚTIL
    ancho_util = ancho_cm - (2 * gap_borde)
    alto_util = alto_cm - titulo_altura - gap_borde

    # CALCULAR ELEMENTOS QUE CABEN - MODIFICADO: No usar toda la altura
    altura_min_elemento = 0.25  # Más compacto para fechas

    # CAMBIO: Usar solo el 70% del alto disponible para justificación superior
    alto_disponible_elementos = alto_util * 0.7
    max_elementos = max(1, int(alto_disponible_elementos / altura_min_elemento))
    elementos_mostrar = elementos[:max_elementos]
    elementos_cortados = len(elementos) - len(elementos_mostrar)

    print(f"=== ANÁLISIS FECHAS ===")
    print(f"Área total: {ancho_cm:.1f}×{alto_cm:.1f} cm")
    print(f"Área útil: {ancho_util:.1f}×{alto_util:.1f} cm")
    print(f"Alto para elementos (70%): {alto_disponible_elementos:.1f} cm")
    print(f"Elementos: {len(elementos_mostrar)} de {len(elementos)}")

    # CALCULAR DIMENSIONES POR ELEMENTO
    altura_por_elemento = alto_disponible_elementos / len(elementos_mostrar) if elementos_mostrar else 0

    # ESPECIFICACIÓN DEL ANCHO - AQUÍ SE CONTROLA LA DISTRIBUCIÓN HORIZONTAL
    ancho_indicador = min(0.3, ancho_util * 0.08)  # CAMBIO: 8% del ancho útil o máx 0.3cm (era 12% y 0.4cm)
    alto_indicador = altura_por_elemento * 0.5

    # CALCULAR ESPACIO REAL PARA TEXTO - AQUÍ SE ESPECIFICA EL ANCHO DEL TEXTO
    indicador_x = gap_borde
    texto_x = gap_borde + ancho_indicador + gap_indicador_texto
    ancho_texto = ancho_cm - texto_x - gap_borde  # ← ESTA LÍNEA ESPECIFICA EL ANCHO DEL TEXTO

    print(f"=== DEBUG ESPACIOS FECHAS ===")
    print(f"Indicador: {ancho_indicador:.2f}cm en X={indicador_x:.2f}cm")
    print(f"Texto: inicia en X={texto_x:.2f}cm, ancho disponible: {ancho_texto:.2f}cm")  # ← ANCHO DEL TEXTO
    print(f"Por elemento: alto={altura_por_elemento:.2f}cm")

    # CALCULAR FUENTE Y TEXTOS
    tamaño_fuente, textos_finales = calcular_fuente_y_textos_fechas(
        elementos_mostrar, ancho_texto, altura_por_elemento
    )

    fuente_titulo = min(tamaño_fuente * 1.3, 16)

    print(f"=== FUENTE FECHAS ===")
    print(f"Fuente elementos: {tamaño_fuente:.1f}pt")
    print(f"Fuente título: {fuente_titulo:.1f}pt")

    # CREAR FONDO
    fondo = mpatches.Rectangle(
        (0, 0), ancho_cm, alto_cm,
        facecolor='white', edgecolor='none', linewidth=0.5, alpha=0.9
    )
    ax.add_patch(fondo)

    # CREAR TÍTULO
    titulo_x = ancho_cm / 2
    titulo_y = alto_cm - titulo_altura / 2

    ax.text(titulo_x, titulo_y, "Fecha",  # CAMBIO: "Fechas de campaña" → "Fecha"
            fontsize=fuente_titulo, weight='bold',
            ha='center', va='center')

    # Línea de subrayado
    titulo_ancho = len("Fecha") * fuente_titulo * 0.04  # CAMBIO: Ajustar al nuevo título
    linea_x1 = titulo_x - titulo_ancho / 2
    linea_x2 = titulo_x + titulo_ancho / 2
    linea_y = titulo_y - fuente_titulo * 0.02

    ax.plot([linea_x1, linea_x2], [linea_y, linea_y], color='black', linewidth=0.5)

    # CREAR ELEMENTOS
    for i, (elemento, texto_final) in enumerate(zip(elementos_mostrar, textos_finales)):
        # Calcular posición Y
        elem_y = alto_cm - titulo_altura - (i + 0.5) * altura_por_elemento

        # Crear indicador de color - TODAS LAS FECHAS USAN LÍNEAS IGUALES
        centro_y = elem_y
        if elemento['destacada']:
            # Fecha destacada: línea más gruesa
            ax.plot([indicador_x, indicador_x + ancho_indicador],
                    [centro_y, centro_y],
                    color=elemento['color'], linewidth=4, solid_capstyle='round')
        else:
            # Fecha normal: línea normal
            ax.plot([indicador_x, indicador_x + ancho_indicador],
                    [centro_y, centro_y],
                    color=elemento['color'], linewidth=3, solid_capstyle='round')

        # Crear texto
        peso = 'bold' if elemento['destacada'] else 'normal'
        ax.text(texto_x, elem_y, texto_final,
                fontsize=tamaño_fuente, va='center', ha='left', weight=peso)

        print(f"  {i + 1}. '{texto_final}' ({'DESTACADA' if elemento['destacada'] else 'normal'})")

        # Verificar espacio
        texto_ancho_estimado = len(texto_final) * tamaño_fuente * 0.025
        espacio_usado = texto_x + texto_ancho_estimado
        espacio_sobrante = (ancho_cm - gap_borde) - espacio_usado
        se_sale = espacio_usado > (ancho_cm - gap_borde)

        print(f"      Ancho texto: {texto_ancho_estimado:.2f}cm, sobrante: {espacio_sobrante:.2f}cm")
        if se_sale:
            print(f"      ⚠️ TEXTO SE SALE")

    # CALCULAR ALTO REAL USADO (para justificación superior)
    alto_usado_real = titulo_altura + gap_borde + (len(elementos_mostrar) * altura_por_elemento)

    print(f"=== JUSTIFICACIÓN SUPERIOR ===")
    print(f"Alto total disponible: {alto_cm:.2f}cm")
    print(f"Alto realmente usado: {alto_usado_real:.2f}cm")
    print(f"Espacio sobrante abajo: {alto_cm - alto_usado_real:.2f}cm")
    print(f"Porcentaje usado: {(alto_usado_real / alto_cm) * 100:.1f}%")

    # INDICADOR DE ELEMENTOS CORTADOS
    if elementos_cortados > 0:
        ax.text(ancho_cm - gap_borde, gap_borde,
                f"(+{elementos_cortados} fechas)",
                fontsize=max(6, tamaño_fuente * 0.8),
                ha='right', va='bottom', style='italic', alpha=0.7)
        print(f"  +{elementos_cortados} fechas cortadas")


def calcular_fuente_y_textos_fechas(elementos, ancho_disponible, altura_disponible):
    """Calcula el tamaño de fuente óptimo y trunca textos de fechas si es necesario."""

    # Generar textos originales
    textos_originales = [elem['texto'] for elem in elementos]

    # OPTIMIZACIÓN: Convertir todos los textos a formato compacto para cálculo preciso
    textos_optimizados = [convertir_fecha_formato_compacto(texto) for texto in textos_originales]
    # CAMBIO: Asegurar que el cálculo incluye fecha + hora para dimensionado correcto
    texto_mas_largo = max(textos_optimizados,
                          key=len) if textos_optimizados else "31-12-24 23:59"  # Fecha + hora más larga posible

    print(f"=== CÁLCULO FUENTE FECHAS ===")
    print(f"Textos originales: {len(textos_originales)} elementos")
    print(f"Texto más largo optimizado: '{texto_mas_largo}' ({len(texto_mas_largo)} chars)")
    print(f"Espacio disponible: {ancho_disponible:.2f}cm")

    # Mostrar algunos ejemplos de optimización
    for i, (original, optimizado) in enumerate(zip(textos_originales[:3], textos_optimizados[:3])):
        if original != optimizado:
            print(f"  Ejemplo {i + 1}: '{original}' → '{optimizado}' (-{len(original) - len(optimizado)} chars)")

    # Calcular fuente basada en altura y anchura (usando texto optimizado)
    fuente_por_alto = altura_disponible * 16  # Más generoso para fechas
    factor_char = 0.025 if fuente_por_alto <= 8 else 0.030
    fuente_por_ancho = (ancho_disponible * 0.95) / (len(texto_mas_largo) * factor_char)

    # CAMBIO: Reducir 1 punto el tamaño de fuente para que entren más fechas
    tamaño_fuente = max(6, min(11, min(fuente_por_alto,
                                       fuente_por_ancho) - 1))  # Era min(12, ...) ahora es min(11, ...) - 1

    print(f"Fuente por alto: {fuente_por_alto:.1f}pt")
    print(f"Fuente por ancho: {fuente_por_ancho:.1f}pt (basado en '{texto_mas_largo}')")
    print(f"Fuente final: {tamaño_fuente:.1f}pt (reducida 1 punto para más fechas)")

    # Generar textos finales usando la función optimizada
    textos_finales = []
    for elemento in elementos:
        texto_original = elemento['texto']
        texto_final = truncar_texto_fecha(texto_original, ancho_disponible, tamaño_fuente)
        textos_finales.append(texto_final)

        if texto_final != texto_original:
            print(f"  PROCESADO: '{texto_original}' → '{texto_final}'")

    return tamaño_fuente, textos_finales


def truncar_texto_fecha(texto, ancho_disponible_cm, tamaño_fuente):
    """
    Trunca un texto de fecha optimizando el formato para ahorrar caracteres.
    ESTRATEGIA: Convierte AAAA-MM-DD → DD-MM-AA para ahorrar 2 caracteres.
    """

    # Factor más agresivo para fechas
    if tamaño_fuente <= 8:
        ancho_por_caracter = tamaño_fuente * 0.025
    else:
        ancho_por_caracter = tamaño_fuente * 0.030

    caracteres_que_caben = int((ancho_disponible_cm * 0.95) / ancho_por_caracter)
    caracteres_que_caben = 17 # fuerzo porque no funciona bien

    print(f"    Fecha: '{texto}' → {caracteres_que_caben} chars caben de {len(texto)}")

    # PASO 1: Convertir fecha ISO a formato compacto DD-MM-AA
    texto_optimizado = convertir_fecha_formato_compacto(texto)

    if len(texto_optimizado) <= caracteres_que_caben:
        if texto_optimizado != texto:
            print(f"    ✅ OPTIMIZADO: '{texto}' → '{texto_optimizado}'")
        return texto_optimizado

    # PASO 2: Si aún no cabe, aplicar abreviaciones adicionales
    if caracteres_que_caben <= 3:
        return "..."

    # PASO 3: Abreviar "(seleccionada)" si está presente
    if "(seleccionada)" in texto_optimizado:
        texto_con_sel = texto_optimizado.replace("(seleccionada)", "(sel.)")
        if len(texto_con_sel) <= caracteres_que_caben:
            print(f"    ✅ CON ABREV: '{texto_optimizado}' → '{texto_con_sel}'")
            return texto_con_sel

        # Si aún no cabe, usar símbolo
        texto_con_star = texto_optimizado.replace("(seleccionada)", "(★)")
        if len(texto_con_star) <= caracteres_que_caben:
            print(f"    ✅ CON SÍMBOLO: '{texto_optimizado}' → '{texto_con_star}'")
            return texto_con_star

    # PASO 4: Truncamiento normal como último recurso
    texto_truncado = texto_optimizado[:caracteres_que_caben - 3] + "..."
    print(f"    ❌ TRUNCADO: '{texto_optimizado}' → '{texto_truncado}'")
    return texto_truncado


def convertir_fecha_formato_compacto(texto):
    """
    Convierte fechas del formato ISO al formato compacto con hora.

    Ejemplos:
    - "2024-01-15" → "15-01-24"
    - "2024-01-15 10:30:00" → "15-01-24 10:30"
    - "2024-01-15T14:25:30" → "15-01-24 14:25"
    - "2024-01-15 (seleccionada)" → "15-01-24 (seleccionada)"
    - "2024-01-15 10:30:00 (seleccionada)" → "15-01-24 10:30 (seleccionada)"
    """
    import re

    # Patrón más completo para fechas con hora opcional
    # Captura: AAAA-MM-DD[T o espacio][HH:MM[:SS]] + resto del texto
    patron_fecha_completa = r'(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2})(?::\d{2})?)?'

    def reemplazar_fecha_completa(match):
        año_completo = match.group(1)
        mes = match.group(2)
        dia = match.group(3)
        hora = match.group(4)  # Puede ser None
        minuto = match.group(5)  # Puede ser None

        # Convertir año a 2 dígitos
        año_corto = año_completo[-2:]

        # Formato base DD-MM-AA
        fecha_compacta = f"{dia}-{mes}-{año_corto}"

        # Añadir hora si está presente
        if hora and minuto:
            fecha_compacta += f" {hora}:{minuto}"

        return fecha_compacta

    # Reemplazar todas las fechas encontradas en el texto
    texto_convertido = re.sub(patron_fecha_completa, reemplazar_fecha_completa, texto)

    return texto_convertido
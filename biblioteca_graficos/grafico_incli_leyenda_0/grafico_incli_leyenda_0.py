# grafico_incli_leyenda_0.py (VERSIÓN FINAL SIN ERRORES)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
import base64

# Importar función necesaria
from funciones import obtener_leyenda_umbrales


def grafico_incli_leyenda_0(data, parametros):
    """
    Genera una imagen SVG/PNG que contiene únicamente una leyenda de umbrales.
    VERSIÓN FINAL: Sin errores de variables, cálculo correcto de espacios.

    Args:
        data: Datos de umbrales
        parametros (dict):
            - ancho_cm (float): Ancho total de la imagen en cm
            - alto_cm (float): Alto máximo de la imagen en cm
            - sensor (str): Tipo de sensor ('desp_a', 'desp_b', 'desp_total')
            - dpi (int): Resolución para PNG (default: 100)
            - formato (str): 'svg' o 'png' (default: 'png')

    Returns:
        str: Data URL de la imagen generada
    """

    # EXTRAER PARÁMETROS
    ancho_cm = parametros.get('ancho_cm', 10)
    alto_cm = parametros.get('alto_cm', 6)
    sensor = parametros.get('sensor', 'desp_a')
    dpi = parametros.get('dpi', 100)
    formato = parametros.get('formato', 'png').lower()

    print(f"=== CREANDO LEYENDA ===")
    print(f"Dimensiones objetivo: {ancho_cm} × {alto_cm} cm")
    print(f"Sensor: {sensor}, Formato: {formato}")

    # OBTENER Y FILTRAR DATOS
    leyenda_umbrales = obtener_leyenda_umbrales(data)

    # Filtrar según tipo de sensor
    if sensor == "desp_a":
        elementos = [k for k in leyenda_umbrales.keys() if k.endswith("_a")]
    elif sensor == "desp_b":
        elementos = [k for k in leyenda_umbrales.keys() if k.endswith("_b")]
    else:  # desp_total
        elementos = list(leyenda_umbrales.keys())

    # Ordenar elementos de forma inteligente
    def get_orden(elemento):
        prioridades = {
            'umbral1': 10, 'umbral2': 20, 'umbral3': 30, 'umbral4': 40,
            'Amber': 50, 'Red': 60, 'FASE': 70, 'lineal': 80
        }
        for clave, valor in prioridades.items():
            if elemento.startswith(clave):
                return valor
        return 999

    elementos_ordenados = sorted(elementos, key=get_orden)

    print(f"Elementos encontrados: {len(elementos_ordenados)}")
    for i, elem in enumerate(elementos_ordenados):
        color = leyenda_umbrales.get(elem, 'sin_color')
        print(f"  {i + 1}. {elem} → {color}")

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

    # CONFIGURACIÓN DE COLORES
    mapeo_colores = {
        'verde': 'green', 'amarillo': 'yellow', 'naranja': 'orange',
        'rojo': 'red', 'azul': 'blue', 'morado': 'purple',
        'gris': 'gray', 'negro': 'black', 'blanco': 'white'
    }

    # CREAR CONTENIDO
    if not elementos_ordenados:
        crear_mensaje_vacio(ax, ancho_cm, alto_cm)
    else:
        crear_leyenda_adaptiva(ax, elementos_ordenados, leyenda_umbrales,
                               mapeo_colores, ancho_cm, alto_cm)

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

        print(f"✅ Imagen SIN GAPS: {formato.upper()}, {ancho_cm}×{alto_cm} cm")

        return f"data:{mime_type};base64,{imagen_base64}"

    except Exception as e:
        print(f"❌ Error generando imagen: {e}")
        raise
    finally:
        plt.close(fig)


def crear_mensaje_vacio(ax, ancho_cm, alto_cm):
    """Crea un mensaje centrado cuando no hay elementos que mostrar."""
    fondo = mpatches.Rectangle(
        (0, 0), ancho_cm, alto_cm,
        facecolor='lightgray', alpha=0.3, edgecolor='gray'
    )
    ax.add_patch(fondo)

    centro_x = ancho_cm / 2
    centro_y = alto_cm / 2
    tamano_fuente = min(ancho_cm * 2, alto_cm * 2.5)

    ax.text(centro_x, centro_y,
            "No hay umbrales\ndisponibles",
            fontsize=tamano_fuente, weight='bold',
            ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    print(f"Mensaje vacío: {ancho_cm}×{alto_cm} cm, fuente {tamano_fuente:.1f}pt")


def crear_leyenda_adaptiva(ax, elementos, leyenda_umbrales, mapeo_colores, ancho_cm, alto_cm):
    """Crea una leyenda que se adapta al espacio disponible."""

    # CONFIGURACIÓN DE GAPS
    gap_borde = 0.1  # Gap entre elementos y borde
    gap_icono_texto = 0.1  # Gap entre icono y texto
    titulo_altura = 0.8  # Altura reservada para título

    # CALCULAR ÁREA ÚTIL
    ancho_util = ancho_cm - (2 * gap_borde)
    alto_util = alto_cm - titulo_altura - gap_borde

    # CALCULAR ELEMENTOS QUE CABEN
    altura_min_elemento = 0.3
    max_elementos = max(1, int(alto_util / altura_min_elemento))
    elementos_mostrar = elementos[:max_elementos]
    elementos_cortados = len(elementos) - len(elementos_mostrar)

    print(f"=== ANÁLISIS DE ESPACIO ===")
    print(f"Área total: {ancho_cm:.1f}×{alto_cm:.1f} cm")
    print(f"Área útil: {ancho_util:.1f}×{alto_util:.1f} cm")
    print(f"Elementos: {len(elementos_mostrar)} de {len(elementos)}")

    # CALCULAR DIMENSIONES POR ELEMENTO
    altura_por_elemento = alto_util / len(elementos_mostrar) if elementos_mostrar else 0
    ancho_icono = min(0.5, ancho_util * 0.15)  # 15% del ancho útil o máx 0.5cm
    alto_icono = altura_por_elemento * 0.6

    # CALCULAR ESPACIO REAL PARA TEXTO
    icono_x = gap_borde
    texto_x = gap_borde + ancho_icono + gap_icono_texto
    ancho_texto = ancho_cm - texto_x - gap_borde  # Espacio desde texto_x hasta el final

    print(f"=== DEBUG ESPACIOS ===")
    print(f"Icono: {ancho_icono:.2f}cm en X={icono_x:.2f}cm")
    print(f"Texto: inicia en X={texto_x:.2f}cm, ancho disponible: {ancho_texto:.2f}cm")
    print(f"Por elemento: alto={altura_por_elemento:.2f}cm")

    # CALCULAR FUENTE Y TEXTOS
    tamaño_fuente, textos_finales = calcular_fuente_y_textos(
        elementos_mostrar, ancho_texto, altura_por_elemento
    )

    fuente_titulo = min(tamaño_fuente * 1.3, 16)

    print(f"=== FUENTE CALCULADA ===")
    print(f"Fuente elementos: {tamaño_fuente:.1f}pt")
    print(f"Fuente título: {fuente_titulo:.1f}pt")

    # CREAR FONDO
    fondo = mpatches.Rectangle(
        (0, 0), ancho_cm, alto_cm,
        facecolor='white', edgecolor='black', linewidth=0.5, alpha=0.9
    )
    ax.add_patch(fondo)

    # CREAR TÍTULO
    titulo_x = ancho_cm / 2
    titulo_y = alto_cm - titulo_altura / 2

    ax.text(titulo_x, titulo_y, "Umbrales",
            fontsize=fuente_titulo, weight='bold',
            ha='center', va='center')

    # Línea de subrayado
    titulo_ancho = len("Umbrales") * fuente_titulo * 0.04
    linea_x1 = titulo_x - titulo_ancho / 2
    linea_x2 = titulo_x + titulo_ancho / 2
    linea_y = titulo_y - fuente_titulo * 0.02

    ax.plot([linea_x1, linea_x2], [linea_y, linea_y], color='black', linewidth=0.5)

    # CREAR ELEMENTOS
    for i, (elemento, texto_final) in enumerate(zip(elementos_mostrar, textos_finales)):
        # Obtener color
        color_nombre = leyenda_umbrales.get(elemento, 'gris')
        color_codigo = mapeo_colores.get(color_nombre, 'gray')

        # Calcular posición Y
        elem_y = alto_cm - titulo_altura - (i + 0.5) * altura_por_elemento

        # Crear icono
        icono = mpatches.Rectangle(
            (icono_x, elem_y - alto_icono / 2),
            ancho_icono, alto_icono,
            facecolor=color_codigo, edgecolor='black', linewidth=0.5
        )
        ax.add_patch(icono)

        # Crear texto
        ax.text(texto_x, elem_y, texto_final,
                fontsize=tamaño_fuente, va='center', ha='left')

        print(f"  {i + 1}. '{texto_final}' (de '{generar_nombre_elemento(elemento)}')")

        # Verificar espacio
        texto_ancho_estimado = len(texto_final) * tamaño_fuente * 0.025
        espacio_usado = texto_x + texto_ancho_estimado
        espacio_sobrante = (ancho_cm - gap_borde) - espacio_usado
        se_sale = espacio_usado > (ancho_cm - gap_borde)

        print(f"      Ancho texto: {texto_ancho_estimado:.2f}cm, sobrante: {espacio_sobrante:.2f}cm")
        print(f"      ¿Se sale? {'❌ SÍ' if se_sale else '✅ NO'}")

    # INDICADOR DE ELEMENTOS CORTADOS
    if elementos_cortados > 0:
        ax.text(ancho_cm - gap_borde, gap_borde,
                f"(+{elementos_cortados})",
                fontsize=max(6, tamaño_fuente * 0.8),
                ha='right', va='bottom', style='italic', alpha=0.7)
        print(f"  +{elementos_cortados} elementos cortados")


def calcular_fuente_y_textos(elementos, ancho_disponible, altura_disponible):
    """Calcula el tamaño de fuente óptimo y trunca textos si es necesario."""

    # Generar textos originales
    textos_originales = [generar_nombre_elemento(elem) for elem in elementos]
    texto_mas_largo = max(textos_originales, key=len) if textos_originales else "Texto"

    print(f"=== CÁLCULO DE FUENTE ===")
    print(f"Texto más largo: '{texto_mas_largo}' ({len(texto_mas_largo)} chars)")
    print(f"Espacio disponible: {ancho_disponible:.2f}cm")

    # Calcular fuente basada en altura y anchura
    fuente_por_alto = altura_disponible * 14
    factor_char = 0.025 if fuente_por_alto <= 8 else 0.030
    fuente_por_ancho = (ancho_disponible * 0.95) / (len(texto_mas_largo) * factor_char)

    tamaño_fuente = max(6, min(14, min(fuente_por_alto, fuente_por_ancho)))

    print(f"Fuente por alto: {fuente_por_alto:.1f}pt")
    print(f"Fuente por ancho: {fuente_por_ancho:.1f}pt")
    print(f"Fuente final: {tamaño_fuente:.1f}pt")

    # Generar textos finales
    textos_finales = []
    for texto_original in textos_originales:
        texto_final = truncar_texto_si_necesario(texto_original, ancho_disponible, tamaño_fuente)
        textos_finales.append(texto_final)

        if texto_final != texto_original:
            print(f"  TRUNCADO: '{texto_original}' → '{texto_final}'")

    return tamaño_fuente, textos_finales


def truncar_texto_si_necesario(texto, ancho_disponible_cm, tamaño_fuente):
    """Trunca un texto si no cabe en el ancho disponible."""

    # Factor más agresivo para fuentes pequeñas
    if tamaño_fuente <= 8:
        ancho_por_caracter = tamaño_fuente * 0.025
    else:
        ancho_por_caracter = tamaño_fuente * 0.030

    caracteres_que_caben = int((ancho_disponible_cm * 0.95) / ancho_por_caracter)

    print(f"    '{texto}': {caracteres_que_caben} chars caben de {len(texto)}")

    if len(texto) <= caracteres_que_caben:
        return texto

    if caracteres_que_caben <= 3:
        return "..."

    return texto[:caracteres_que_caben - 3] + "..."


def generar_nombre_elemento(elemento):
    """Genera un nombre legible para mostrar en la leyenda."""
    if '_' not in elemento:
        return elemento

    partes = elemento.split('_')
    if len(partes) < 2:
        return elemento

    nombre_base = partes[0]
    eje = partes[-1].upper()

    if nombre_base.startswith('umbral') and len(nombre_base) > 6:
        numero = nombre_base[6:]
        return f"Umbral {numero} - Eje {eje}"
    elif nombre_base.startswith('lineal') and len(nombre_base) > 6:
        numero = nombre_base[6:]
        return f"Lineal {numero} - Eje {eje}"
    else:
        return f"{nombre_base} - Eje {eje}"
"""Gráfico de evolución temporal Spline L9 v2 — bandas de umbral semáforo desde BD por sensor.

Variante de ``grafico_spline_l9_v1.py`` con soporte de umbrales asimétricos (MAX/MIN
independientes) procedentes de la BD de auscultación (VALOR_PARAM_ALERTA /
NIVEL_TIPO_ALERTA_SENSOR). Los umbrales se inyectan en ``params["data"]["umbrales"]``
por el motor HTML antes de llamar a ``generate()``.

Nuevos parámetros respecto a v1:
  umbrales_origen      : 'off' | 'auto_bd' | 'manual'
  umbrales_modo        : 'auto' | 'envolvente' | 'por_sensor'
  umbrales_niveles     : cadena CSV de niveles a representar (operacion, preavis, atencio)
  umbrales_opacidad    : opacidad del relleno de bandas (0.0–1.0)
  umbrales_show_lines  : bool — dibujar líneas finas en los límites de cada zona
  umbrales_show_labels : bool — etiquetas junto a las líneas (nivel o sensor si divergen)

Los parámetros heredados ``umbral_estable_max``, ``umbral_atencion`` y ``umbral_alerta``
se mantienen para retrocompatibilidad con modo 'manual'.

Cambios v2.1:
  - Líneas y bandas acotadas a [x_min_data, x_max_data] via add_shape (xref='x'),
    sin invadir la zona de etiquetas a la derecha.
  - Color de las líneas siempre por NIVEL (verde/naranja/rojo), no por sensor.
  - Etiquetas de nivel en modo envolvente y etiquetas de sensor en modo por_sensor
    cuando los umbrales divergen (opt-in con umbrales_show_labels, default True).
  - Heurística de fusión en por_sensor: si todos los sensores comparten el mismo
    valor de umbral (tolerancia 1e-9), se dibuja una única línea sin etiqueta.

Cambios v2.2:
  - Líneas de umbral discontinuas por defecto (dash="dash" en _hline).
  - Etiquetas de nivel y de sensor desplazadas a la IZQUIERDA del gráfico
    (x=x_min_data, xanchor="right", xshift=-4) para no solaparse con etiquetas
    de sensor en la zona derecha.
  - Flag umbrales_debug (bool, default False): imprime la tabla de umbrales
    recibida de BD por stderr para diagnóstico; opt-in explícito.
  - Subtítulo de estado global (umbrales_show_status, default True): cuenta
    cuántos sensores están en operación/preaviso/atención y lo muestra sobre
    el gráfico con colores semáforo.
  - Tick de cierre opcional (tick_cierre_show, default False): línea vertical
    gris sutil en la fecha de cierre del informe.
  - Reservado: umbrales_franja_lateral (próxima iteración, sin efecto aún).

Cambios v2.3:
  - Etiquetas de umbral con fondo blanco a la izquierda de cada línea
    (cara MAX solo, opción B; texto: nivel sin distinción máx/mín).
  - Migración completa de envolvente a _hband/_hline (deuda residual saneada).
  - umbrales_show_status desactivado por defecto en plantilla (código preservado).

Cambios v2.4:
  - Etiquetas de umbral en AMBAS caras (máx y mín) — opción C definitiva.
  - Texto incluye distinción "máx"/"mín" para diferenciar caras.
  - umbrales_show_status default a False (subtítulo desactivado por defecto).

Función principal: ``generate(params, figsize) -> str``
"""

from __future__ import annotations

from typing import Any

from utils.script_registry import ParameterMetadata, ScriptMetadata, register_script
from utils.sensor_palette import PALETAS as _PALETAS, asignar_colores_sensores

# ── Registro de metadatos ──────────────────────────────────────────────────────

metadata = ScriptMetadata(
    nombre="grafico_spline_l9_v2",
    tipo="grafico",
    descripcion="Evolución temporal spline v2 — bandas de umbral semáforo desde BD por sensor",
    parametros=[
        ParameterMetadata(
            nombre="sensor",
            tipo="texto",
            requerido=False,
            default="$CURRENT",
            descripcion="Nombre del sensor a mostrar. '$CURRENT' usa el sensor activo.",
        ),
        ParameterMetadata(
            nombre="fecha_inicio",
            tipo="fecha",
            requerido=False,
            default="$CURRENT_fecha_inicial",
            descripcion="Fecha inicio del período (ISO 8601).",
        ),
        ParameterMetadata(
            nombre="fecha_fin",
            tipo="fecha",
            requerido=False,
            default="$CURRENT_fecha_final",
            descripcion="Fecha fin del período (ISO 8601).",
        ),
        ParameterMetadata(
            nombre="show_markers",
            tipo="bool",
            requerido=False,
            default=False,
            descripcion="True = añade puntos en cada lectura.",
        ),
        ParameterMetadata(
            nombre="palette",
            tipo="lista",
            requerido=False,
            default="modern",
            opciones=["modern", "corporate", "vibrant"],
            descripcion="Paleta de colores: modern | corporate | vibrant.",
        ),
        ParameterMetadata(
            nombre="y_min",
            tipo="numero",
            requerido=False,
            default=None,
            descripcion="Límite inferior eje Y. Vacío = autoescala ±10 %.",
        ),
        ParameterMetadata(
            nombre="y_max",
            tipo="numero",
            requerido=False,
            default=None,
            descripcion="Límite superior eje Y. Vacío = autoescala ±10 %.",
        ),
        ParameterMetadata(
            nombre="y_escala_modo",
            tipo="lista",
            requerido=False,
            default="flexible",
            opciones=["auto", "fijo", "flexible"],
            descripcion="Modo de escala del eje Y: auto, fijo (y_min/y_max duros) o flexible (y_min/y_max como ventana mínima; se expande si datos, umbrales o etiquetas la superan).",
        ),
        ParameterMetadata(
            nombre="y_decimals",
            tipo="numero",
            requerido=False,
            default=2,
            descripcion="Decimales en la anotación de valor y en los ticks del eje Y.",
        ),
        ParameterMetadata(
            nombre="x_date_format",
            tipo="texto",
            requerido=False,
            default="%d/%m/%y",
            descripcion="Formato de fecha para el eje X (d3 / strftime).",
        ),
        ParameterMetadata(
            nombre="label_size",
            tipo="numero",
            requerido=False,
            default=10,
            descripcion="Tamaño de fuente de las anotaciones de valor al final de cada línea (pt).",
        ),
        ParameterMetadata(
            nombre="y_axis_title",
            tipo="texto",
            requerido=False,
            default="",
            descripcion="Título del eje Y. Vacío = sin título.",
        ),
        ParameterMetadata(
            nombre="x_axis_title",
            tipo="texto",
            requerido=False,
            default="",
            descripcion="Título del eje X. Vacío = sin título.",
        ),
        ParameterMetadata(
            nombre="umbral_estable_max",
            tipo="numero",
            requerido=False,
            default=None,
            descripcion="(Manual) Límite superior zona estable (verde). Retrocompatibilidad.",
        ),
        ParameterMetadata(
            nombre="umbral_atencion",
            tipo="numero",
            requerido=False,
            default=None,
            descripcion="(Manual) Inicio zona de atención (naranja). Retrocompatibilidad.",
        ),
        ParameterMetadata(
            nombre="umbral_alerta",
            tipo="numero",
            requerido=False,
            default=None,
            descripcion="(Manual) Inicio zona de alerta (rojo). Retrocompatibilidad.",
        ),
        ParameterMetadata(
            nombre="line_width",
            tipo="numero",
            requerido=False,
            default=2,
            descripcion="Grosor de las líneas de las series (px).",
        ),
        ParameterMetadata(
            nombre="smoothing",
            tipo="bool",
            requerido=False,
            default=False,
            descripcion="True = suavizado spline; False = líneas rectas entre puntos.",
        ),
        ParameterMetadata(
            nombre="show_label_box",
            tipo="bool",
            requerido=False,
            default=False,
            descripcion="True = recuadro con borde alrededor del valor final.",
        ),
        ParameterMetadata(
            nombre="show_vgrid",
            tipo="bool",
            requerido=False,
            default=True,
            descripcion="True = muestra rejilla vertical en el eje X.",
        ),
        ParameterMetadata(
            nombre="label_mode",
            tipo="lista",
            requerido=False,
            default="ambos",
            opciones=["nombre", "valor", "ambos", "ninguno"],
            descripcion="Contenido de la etiqueta: nombre_sensor | valor | ambos | ninguno.",
        ),
        ParameterMetadata(
            nombre="label_bgcolor",
            tipo="texto",
            requerido=False,
            default="white",
            descripcion="Fondo de la etiqueta (color CSS o 'transparent').",
        ),
        ParameterMetadata(
            nombre="label_area_pct",
            tipo="numero",
            requerido=False,
            default=20,
            descripcion="% del ancho total reservado para las etiquetas a la derecha (5–40).",
        ),
        ParameterMetadata(
            nombre="show_xaxis",
            tipo="bool",
            requerido=False,
            default=True,
            descripcion="True = muestra el eje horizontal.",
        ),
        ParameterMetadata(
            nombre="show_yaxis_left",
            tipo="bool",
            requerido=False,
            default=True,
            descripcion="True = muestra el eje vertical izquierdo.",
        ),
        ParameterMetadata(
            nombre="show_yaxis_right",
            tipo="bool",
            requerido=False,
            default=False,
            descripcion="True = muestra el eje vertical derecho (spine).",
        ),
        ParameterMetadata(
            nombre="show_legend",
            tipo="bool",
            requerido=False,
            default=True,
            descripcion="True = muestra la leyenda del gráfico.",
        ),
        ParameterMetadata(
            nombre="legend_position",
            tipo="lista",
            requerido=False,
            default="superior",
            opciones=["superior", "inferior", "izquierda", "derecha"],
            descripcion="Posición de la leyenda: superior | inferior | izquierda | derecha.",
        ),
        ParameterMetadata(
            nombre="umbrales_origen",
            tipo="lista",
            requerido=False,
            default="off",
            opciones=["off", "auto_bd", "manual"],
            descripcion="Origen de los umbrales: off (sin umbrales), auto_bd (BD del informe), manual (los 3 umbrales escalares).",
        ),
        ParameterMetadata(
            nombre="umbrales_modo",
            tipo="lista",
            requerido=False,
            default="auto",
            opciones=["auto", "envolvente", "por_sensor"],
            descripcion="auto: bandas si hay 1 sensor, líneas finas por sensor si hay varios; envolvente: una sola banda usando min/max global; por_sensor: una línea por sensor y nivel.",
        ),
        ParameterMetadata(
            nombre="umbrales_niveles",
            tipo="texto",
            requerido=False,
            default="operacion,preavis,atencio",
            descripcion="Niveles a representar (lista CSV). Quitar el que no interese.",
        ),
        ParameterMetadata(
            nombre="umbrales_opacidad",
            tipo="numero",
            requerido=False,
            default=0.10,
            descripcion="Opacidad del relleno de las bandas (0.0–1.0).",
        ),
        ParameterMetadata(
            nombre="umbrales_show_lines",
            tipo="bool",
            requerido=False,
            default=True,
            descripcion="Dibujar líneas finas en los límites de cada zona.",
        ),
        ParameterMetadata(
            nombre="umbrales_show_labels",
            tipo="bool",
            requerido=False,
            default=True,
            descripcion="Etiquetas textuales junto a las líneas de umbral (Operación/Preaviso/Atención o NOM_SENSOR si divergen).",
        ),
        ParameterMetadata(
            nombre="umbrales_debug",
            tipo="bool",
            requerido=False,
            default=False,
            descripcion="Si True, imprime por terminal la tabla de umbrales recibida desde BD para diagnóstico.",
        ),
        ParameterMetadata(
            nombre="umbrales_show_status",
            tipo="bool",
            requerido=False,
            default=False,
            descripcion="Muestra subtítulo con conteo de sensores por zona (operación/preaviso/atención).",
        ),
        ParameterMetadata(
            nombre="tick_cierre_show",
            tipo="bool",
            requerido=False,
            default=False,
            descripcion="Si True, dibuja una línea vertical sutil en la fecha de cierre del informe (fecha_fin).",
        ),
        ParameterMetadata(
            nombre="umbrales_franja_lateral",
            tipo="bool",
            requerido=False,
            default=False,
            descripcion="Reservado — banda vertical de semáforo a la izquierda del eje Y. Sin efecto en v2.2; próxima iteración.",
        ),
    ],
)

# ── PARAMETER_METADATA (ScriptRegistry) ────────────────────────────────────────

PARAMETER_METADATA: list[dict] = [
    {
        "nombre": "sensor",
        "tipo": "texto",
        "requerido": False,
        "default": "$CURRENT",
        "descripcion": {"es": "Nombre del sensor a mostrar. '$CURRENT' usa el sensor activo.", "en": "Sensor name to display. '$CURRENT' uses the active sensor."},
    },
    {
        "nombre": "fecha_inicio",
        "tipo": "fecha",
        "requerido": False,
        "default": "$CURRENT_fecha_inicial",
        "descripcion": {"es": "Fecha inicio del período (ISO 8601).", "en": "Period start date (ISO 8601)."},
    },
    {
        "nombre": "fecha_fin",
        "tipo": "fecha",
        "requerido": False,
        "default": "$CURRENT_fecha_final",
        "descripcion": {"es": "Fecha fin del período (ISO 8601).", "en": "Period end date (ISO 8601)."},
    },
    {
        "nombre": "show_markers",
        "tipo": "bool",
        "requerido": False,
        "default": False,
        "descripcion": {"es": "True = añade puntos en cada lectura (lines+markers).", "en": "True = adds individual data points on each reading (lines+markers)."},
    },
    {
        "nombre": "palette",
        "tipo": "lista",
        "requerido": False,
        "default": "modern",
        "opciones": ["modern", "corporate", "vibrant"],
        "descripcion": {"es": "Paleta: modern | corporate | vibrant.", "en": "Colour palette: modern | corporate | vibrant."},
    },
    {
        "nombre": "y_min",
        "tipo": "numero",
        "requerido": False,
        "default": None,
        "descripcion": {"es": "Límite inferior eje Y. Vacío = autoescala ±10 %.", "en": "Y axis lower limit. Empty = auto-scale ±10%."},
    },
    {
        "nombre": "y_max",
        "tipo": "numero",
        "requerido": False,
        "default": None,
        "descripcion": {"es": "Límite superior eje Y. Vacío = autoescala ±10 %.", "en": "Y axis upper limit. Empty = auto-scale ±10%."},
    },
    {
        "nombre": "y_escala_modo",
        "tipo": "lista",
        "requerido": False,
        "default": "flexible",
        "opciones": ["auto", "fijo", "flexible"],
        "descripcion": {"es": "Modo de escala del eje Y: auto, fijo (y_min/y_max duros) o flexible (y_min/y_max como ventana mínima; se expande si datos, umbrales o etiquetas la superan).", "en": "Y axis scale mode: auto, fijo (hard y_min/y_max) or flexible (y_min/y_max as a minimum window; expands if data, thresholds or labels exceed it)."},
    },
    {
        "nombre": "y_decimals",
        "tipo": "numero",
        "requerido": False,
        "default": 2,
        "descripcion": {"es": "Decimales en la anotación de valor y eje Y.", "en": "Decimal places for value annotations and Y axis ticks."},
    },
    {
        "nombre": "x_date_format",
        "tipo": "texto",
        "requerido": False,
        "default": "%d/%m/%y",
        "descripcion": {"es": "Formato de fecha para el eje X.", "en": "Date format for the X axis."},
    },
    {
        "nombre": "label_size",
        "tipo": "numero",
        "requerido": False,
        "default": 10,
        "descripcion": {"es": "Tamaño de fuente de las anotaciones de valor (pt).", "en": "Font size of the end-of-line value annotations (pt)."},
    },
    {
        "nombre": "y_axis_title",
        "tipo": "texto",
        "requerido": False,
        "default": "",
        "descripcion": {"es": "Título del eje Y.", "en": "Y axis title."},
    },
    {
        "nombre": "x_axis_title",
        "tipo": "texto",
        "requerido": False,
        "default": "",
        "descripcion": {"es": "Título del eje X.", "en": "X axis title."},
    },
    {
        "nombre": "umbral_estable_max",
        "tipo": "numero",
        "requerido": False,
        "default": None,
        "descripcion": {"es": "(Manual) Límite superior zona estable (verde). Retrocompatibilidad.", "en": "(Manual) Upper limit of stable zone (green). Backward compat."},
    },
    {
        "nombre": "umbral_atencion",
        "tipo": "numero",
        "requerido": False,
        "default": None,
        "descripcion": {"es": "(Manual) Inicio zona de atención (naranja). Retrocompatibilidad.", "en": "(Manual) Start of attention zone (orange). Backward compat."},
    },
    {
        "nombre": "umbral_alerta",
        "tipo": "numero",
        "requerido": False,
        "default": None,
        "descripcion": {"es": "(Manual) Inicio zona de alerta (rojo). Retrocompatibilidad.", "en": "(Manual) Start of alert zone (red). Backward compat."},
    },
    {
        "nombre": "line_width",
        "tipo": "numero",
        "requerido": False,
        "default": 2,
        "descripcion": {"es": "Grosor de las líneas de las series (px).", "en": "Width of the series lines (px)."},
    },
    {
        "nombre": "smoothing",
        "tipo": "bool",
        "requerido": False,
        "default": False,
        "descripcion": {"es": "True = suavizado spline; False = líneas rectas.", "en": "True = spline smoothing; False = straight lines between points."},
    },
    {
        "nombre": "show_label_box",
        "tipo": "bool",
        "requerido": False,
        "default": False,
        "descripcion": {"es": "True = recuadro con borde alrededor del valor final.", "en": "True = bordered box around the final value annotation."},
    },
    {
        "nombre": "show_vgrid",
        "tipo": "bool",
        "requerido": False,
        "default": True,
        "descripcion": {"es": "True = muestra rejilla vertical en el eje X.", "en": "True = shows vertical grid on the X axis."},
    },
    {
        "nombre": "label_mode",
        "tipo": "lista",
        "requerido": False,
        "default": "ambos",
        "opciones": ["nombre", "valor", "ambos", "ninguno"],
        "descripcion": {"es": "Contenido etiqueta: nombre_sensor | valor | ambos | ninguno.", "en": "Label content: sensor_name | value | both | none."},
    },
    {
        "nombre": "label_bgcolor",
        "tipo": "texto",
        "requerido": False,
        "default": "white",
        "descripcion": {"es": "Fondo de la etiqueta (color CSS o 'transparent').", "en": "Label background (CSS colour or 'transparent')."},
    },
    {
        "nombre": "label_area_pct",
        "tipo": "numero",
        "requerido": False,
        "default": 20,
        "descripcion": {"es": "% del ancho total reservado para etiquetas a la derecha (5–40).", "en": "% of total width reserved for right-side labels (5–40)."},
    },
    {
        "nombre": "show_xaxis",
        "tipo": "bool",
        "requerido": False,
        "default": True,
        "descripcion": {"es": "True = muestra el eje horizontal (línea inferior del área).", "en": "True = shows the horizontal axis line."},
    },
    {
        "nombre": "show_yaxis_left",
        "tipo": "bool",
        "requerido": False,
        "default": True,
        "descripcion": {"es": "True = muestra el eje vertical izquierdo (con ticks y título).", "en": "True = shows the left vertical axis (with ticks and title)."},
    },
    {
        "nombre": "show_yaxis_right",
        "tipo": "bool",
        "requerido": False,
        "default": False,
        "descripcion": {"es": "True = muestra el eje vertical derecho (spine derecho).", "en": "True = shows the right vertical axis (right spine)."},
    },
    {
        "nombre": "show_legend",
        "tipo": "bool",
        "requerido": False,
        "default": True,
        "descripcion": {"es": "True = muestra la leyenda del gráfico.", "en": "True = shows the chart legend."},
    },
    {
        "nombre": "legend_position",
        "tipo": "lista",
        "requerido": False,
        "default": "superior",
        "opciones": ["superior", "inferior", "izquierda", "derecha"],
        "descripcion": {"es": "Posición de la leyenda: superior | inferior | izquierda | derecha.", "en": "Legend position: top | bottom | left | right."},
    },
    {
        "nombre": "umbrales_origen",
        "tipo": "lista",
        "requerido": False,
        "default": "off",
        "opciones": ["off", "auto_bd", "manual"],
        "descripcion": {"es": "Origen de los umbrales: off (sin umbrales), auto_bd (BD del informe), manual (escalares).", "en": "Threshold source: off (none), auto_bd (from DB), manual (scalar values)."},
    },
    {
        "nombre": "umbrales_modo",
        "tipo": "lista",
        "requerido": False,
        "default": "auto",
        "opciones": ["auto", "envolvente", "por_sensor"],
        "descripcion": {"es": "auto: bandas si 1 sensor, líneas si varios; envolvente: banda global min/max; por_sensor: línea por sensor y nivel.", "en": "auto: bands for 1 sensor, lines for several; envolvente: global min/max band; por_sensor: one line per sensor and level."},
    },
    {
        "nombre": "umbrales_niveles",
        "tipo": "texto",
        "requerido": False,
        "default": "operacion,preavis,atencio",
        "descripcion": {"es": "Niveles a representar (CSV). Valores: operacion, preavis, atencio.", "en": "Levels to display (CSV). Values: operacion, preavis, atencio."},
    },
    {
        "nombre": "umbrales_opacidad",
        "tipo": "numero",
        "requerido": False,
        "default": 0.10,
        "descripcion": {"es": "Opacidad del relleno de las bandas (0.0–1.0).", "en": "Fill opacity for threshold bands (0.0–1.0)."},
    },
    {
        "nombre": "umbrales_show_lines",
        "tipo": "bool",
        "requerido": False,
        "default": True,
        "descripcion": {"es": "Dibujar líneas finas en los límites de cada zona.", "en": "Draw thin boundary lines at each zone limit."},
    },
    {
        "nombre": "umbrales_show_labels",
        "tipo": "bool",
        "requerido": False,
        "default": True,
        "descripcion": {
            "es": "Etiquetas textuales junto a las líneas de umbral (Operación/Preaviso/Atención o NOM_SENSOR si divergen).",
            "en": "Text labels next to threshold lines (Operación/Preaviso/Atención or sensor name when thresholds diverge).",
        },
    },
    {
        "nombre": "umbrales_debug",
        "tipo": "bool",
        "requerido": False,
        "default": False,
        "descripcion": {
            "es": "Si True, imprime por stderr la tabla de umbrales recibida desde BD (diagnóstico).",
            "en": "If True, prints the threshold table received from DB to stderr (diagnostics).",
        },
    },
    {
        "nombre": "umbrales_show_status",
        "tipo": "bool",
        "requerido": False,
        "default": False,
        "descripcion": {
            "es": "Muestra subtítulo con conteo de sensores por zona (operación/preaviso/atención).",
            "en": "Shows a subtitle with sensor counts per zone (operation/pre-warning/warning).",
        },
    },
    {
        "nombre": "tick_cierre_show",
        "tipo": "bool",
        "requerido": False,
        "default": False,
        "descripcion": {
            "es": "Si True, dibuja línea vertical sutil en fecha_fin (cierre del informe).",
            "en": "If True, draws a subtle vertical line at fecha_fin (report closing date).",
        },
    },
    {
        "nombre": "umbrales_franja_lateral",
        "tipo": "bool",
        "requerido": False,
        "default": False,
        "descripcion": {
            "es": "Reservado — banda lateral de semáforo. Sin efecto en v2.2; próxima iteración.",
            "en": "Reserved — lateral traffic-light band. No effect in v2.2; next iteration.",
        },
    },
]

# ── Custom Options Schema (Dispatch Table wizard) ──────────────────────────────

_CUSTOM_OPTIONS_SCHEMA: list[dict] = [
    {
        "id": "show_markers",
        "label": "Mostrar marcadores",
        "tipo": "switch",
        "default": False,
        "descripcion": {"es": "Activa puntos individuales sobre la línea.", "en": "Enables individual data points on the line."},
    },
    {
        "id": "palette",
        "label": "Paleta de colores",
        "tipo": "select",
        "default": "modern",
        "opciones": [
            {"value": "modern",    "label": "Modern (dashboard)"},
            {"value": "corporate", "label": "Corporate (azules)"},
            {"value": "vibrant",   "label": "Vibrant (alta distinción)"},
        ],
        "descripcion": {"es": "Esquema de colores de las series.", "en": "Color scheme for the data series."},
    },
    {
        "id": "y_min",
        "label": "Y mínimo",
        "tipo": "number",
        "default": None,
        "descripcion": {"es": "Límite inferior del eje Y. Vacío = autoescala.", "en": "Lower bound of the Y axis. Empty = auto-scale."},
    },
    {
        "id": "y_max",
        "label": "Y máximo",
        "tipo": "number",
        "default": None,
        "descripcion": {"es": "Límite superior del eje Y. Vacío = autoescala.", "en": "Upper bound of the Y axis. Empty = auto-scale."},
    },
    {
        "id": "y_escala_modo",
        "label": "Modo escala Y",
        "tipo": "select",
        "default": "flexible",
        "opciones": [
            {"value": "auto",     "label": "Auto (autoescala)"},
            {"value": "fijo",     "label": "Fijo (límites duros y_min/y_max)"},
            {"value": "flexible", "label": "Flexible (y_min/y_max como ventana mínima)"},
        ],
        "descripcion": {"es": "Modo de escala del eje Y: auto (autoescala), fijo (y_min/y_max como límites duros) o flexible (y_min/y_max como ventana mínima; se expande si datos, umbrales o etiquetas la superan).", "en": "Y axis scale mode: auto (auto-scale), fijo (y_min/y_max as hard limits) or flexible (y_min/y_max as a minimum window; expands if data, thresholds or labels exceed it)."},
    },
    {
        "id": "y_decimals",
        "label": "Decimales eje Y",
        "tipo": "number",
        "default": 2,
        "descripcion": {"es": "Número de decimales en anotaciones de valor y tick labels.", "en": "Number of decimal places in value annotations and tick labels."},
    },
    {
        "id": "x_date_format",
        "label": "Formato fecha eje X",
        "tipo": "text",
        "default": "%d/%m/%y",
        "descripcion": {"es": "Formato d3/strftime para el eje X.", "en": "d3/strftime format string for the X axis."},
    },
    {
        "id": "label_size",
        "label": "Tamaño valor final (pt)",
        "tipo": "number",
        "default": 10,
        "descripcion": {"es": "Tamaño de fuente de la anotación numérica al final de la línea.", "en": "Font size of the numeric annotation at the end of each line."},
    },
    {
        "id": "y_axis_title",
        "label": "Título eje Y",
        "tipo": "text",
        "default": "",
        "descripcion": {"es": "Texto del título del eje Y. Vacío = sin título.", "en": "Y axis title text. Empty = no title."},
    },
    {
        "id": "x_axis_title",
        "label": "Título eje X",
        "tipo": "text",
        "default": "",
        "descripcion": {"es": "Texto del título del eje X. Vacío = sin título.", "en": "X axis title text. Empty = no title."},
    },
    {
        "id": "umbral_estable_max",
        "label": "Umbral estable (verde) — manual",
        "tipo": "number",
        "default": None,
        "descripcion": {"es": "(Manual) Límite superior zona estable (verde). Solo cuando umbrales_origen=manual.", "en": "(Manual) Upper boundary of the stable zone (green). Only when umbrales_origen=manual."},
    },
    {
        "id": "umbral_atencion",
        "label": "Umbral atención (naranja) — manual",
        "tipo": "number",
        "default": None,
        "descripcion": {"es": "(Manual) Inicio zona de atención (naranja). Solo cuando umbrales_origen=manual.", "en": "(Manual) Start of the attention zone (orange). Only when umbrales_origen=manual."},
    },
    {
        "id": "umbral_alerta",
        "label": "Umbral alerta (rojo) — manual",
        "tipo": "number",
        "default": None,
        "descripcion": {"es": "(Manual) Inicio zona de alerta (rojo). Solo cuando umbrales_origen=manual.", "en": "(Manual) Start of the alert zone (red). Only when umbrales_origen=manual."},
    },
    {
        "id": "line_width",
        "label": "Grosor de línea (px)",
        "tipo": "number",
        "default": 2,
        "descripcion": {"es": "Ancho de trazo de cada serie.", "en": "Stroke width for each series."},
    },
    {
        "id": "smoothing",
        "label": "Suavizado spline",
        "tipo": "switch",
        "default": False,
        "descripcion": {"es": "Activa el suavizado spline de las líneas.", "en": "Enables spline smoothing for the lines."},
    },
    {
        "id": "show_label_box",
        "label": "Marco en valor final",
        "tipo": "switch",
        "default": False,
        "descripcion": {"es": "Muestra recuadro con borde alrededor del valor numérico final.", "en": "Displays a bordered box around the final numeric value annotation."},
    },
    {
        "id": "show_vgrid",
        "label": "Rejilla vertical",
        "tipo": "switch",
        "default": True,
        "descripcion": {"es": "Activa la rejilla vertical en el eje X.", "en": "Enables the vertical grid lines on the X axis."},
    },
    {
        "id": "label_mode",
        "label": "Contenido etiqueta",
        "tipo": "select",
        "default": "ambos",
        "opciones": [
            {"value": "ambos",   "label": "Nombre + Valor"},
            {"value": "nombre",  "label": "Solo nombre"},
            {"value": "valor",   "label": "Solo valor"},
            {"value": "ninguno", "label": "Sin etiqueta"},
        ],
        "descripcion": {"es": "Qué se muestra al final de cada línea.", "en": "What is shown at the end of each line."},
    },
    {
        "id": "label_bgcolor",
        "label": "Fondo etiqueta",
        "tipo": "text",
        "default": "white",
        "descripcion": {"es": "Color de fondo de la etiqueta (p.ej. 'white', '#f0f0f0', 'transparent').", "en": "Label background color (e.g. 'white', '#f0f0f0', 'transparent')."},
    },
    {
        "id": "label_area_pct",
        "label": "Área etiquetas (%)",
        "tipo": "number",
        "default": 20,
        "descripcion": {"es": "% del ancho reservado a la derecha para las etiquetas (5–40).", "en": "% of chart width reserved on the right for labels (5–40)."},
    },
    {
        "id": "show_xaxis",
        "label": "Eje horizontal",
        "tipo": "switch",
        "default": True,
        "descripcion": {"es": "Muestra/oculta la línea del eje X.", "en": "Shows/hides the X axis line."},
    },
    {
        "id": "show_yaxis_left",
        "label": "Eje vertical izquierdo",
        "tipo": "switch",
        "default": True,
        "descripcion": {"es": "Muestra/oculta el eje Y izquierdo.", "en": "Shows/hides the left Y axis."},
    },
    {
        "id": "show_yaxis_right",
        "label": "Eje vertical derecho",
        "tipo": "switch",
        "default": False,
        "descripcion": {"es": "Muestra el spine del eje Y derecho.", "en": "Shows the right Y axis spine."},
    },
    {
        "id": "show_legend",
        "label": "Mostrar leyenda",
        "tipo": "switch",
        "default": True,
        "descripcion": {"es": "Muestra u oculta la leyenda del gráfico.", "en": "Shows or hides the chart legend."},
    },
    {
        "id": "legend_position",
        "label": "Posición leyenda",
        "tipo": "select",
        "default": "superior",
        "opciones": [
            {"value": "superior",  "label": "Superior"},
            {"value": "inferior",  "label": "Inferior"},
            {"value": "izquierda", "label": "Izquierda"},
            {"value": "derecha",   "label": "Derecha"},
        ],
        "descripcion": {"es": "Posición de la leyenda en el gráfico.", "en": "Position of the legend in the chart."},
    },
    {
        "id": "umbrales_origen",
        "label": "Origen umbrales",
        "tipo": "select",
        "default": "off",
        "opciones": [
            {"value": "off",     "label": "Sin umbrales"},
            {"value": "auto_bd", "label": "Automático desde BD"},
            {"value": "manual",  "label": "Manual (escalares)"},
        ],
        "descripcion": {"es": "Origen de los umbrales de semáforo.", "en": "Source for threshold/traffic-light zones."},
    },
    {
        "id": "umbrales_modo",
        "label": "Modo umbrales",
        "tipo": "select",
        "default": "auto",
        "opciones": [
            {"value": "auto",       "label": "Auto (según nº sensores)"},
            {"value": "envolvente", "label": "Envolvente (banda global)"},
            {"value": "por_sensor", "label": "Por sensor (líneas)"},
        ],
        "descripcion": {"es": "Cómo se representan los umbrales cuando hay varios sensores.", "en": "How thresholds are displayed with multiple sensors."},
    },
    {
        "id": "umbrales_niveles",
        "label": "Niveles a representar",
        "tipo": "text",
        "default": "operacion,preavis,atencio",
        "descripcion": {"es": "CSV de niveles: operacion, preavis, atencio. Eliminar los que no interesen.", "en": "CSV of levels: operacion, preavis, atencio. Remove unwanted ones."},
    },
    {
        "id": "umbrales_opacidad",
        "label": "Opacidad bandas",
        "tipo": "number",
        "default": 0.10,
        "descripcion": {"es": "Opacidad del relleno de las bandas de umbral (0.0–1.0).", "en": "Fill opacity for threshold bands (0.0–1.0)."},
    },
    {
        "id": "umbrales_show_lines",
        "label": "Mostrar líneas límite",
        "tipo": "switch",
        "default": True,
        "descripcion": {"es": "Dibuja líneas finas punteadas en los límites de cada zona.", "en": "Draw thin dotted lines at each zone boundary."},
    },
    {
        "id": "umbrales_show_labels",
        "label": "Mostrar etiquetas umbral",
        "tipo": "switch",
        "default": True,
        "descripcion": {
            "es": "Texto del nivel (Operación/Preaviso/Atención) o nombre de sensor cuando difieren.",
            "en": "Level text (Operación/Preaviso/Atención) or sensor name when thresholds differ.",
        },
    },
    {
        "id": "umbrales_debug",
        "label": "Debug umbrales (stderr)",
        "tipo": "switch",
        "default": False,
        "descripcion": {
            "es": "Imprime la tabla de umbrales por stderr para diagnóstico. Actívalo solo en desarrollo.",
            "en": "Prints threshold table to stderr for diagnostics. Enable in development only.",
        },
    },
    {
        "id": "umbrales_show_status",
        "label": "Subtítulo estado sensores",
        "tipo": "switch",
        "default": False,
        "descripcion": {
            "es": "Subtítulo sobre el gráfico con conteo de sensores por zona semáforo.",
            "en": "Subtitle above the chart showing sensor counts per traffic-light zone.",
        },
    },
    {
        "id": "tick_cierre_show",
        "label": "Línea cierre informe",
        "tipo": "switch",
        "default": False,
        "descripcion": {
            "es": "Dibuja una línea vertical sutil en la fecha de cierre del informe (fecha_fin).",
            "en": "Draws a subtle vertical line at the report closing date (fecha_fin).",
        },
    },
    {
        "id": "umbrales_franja_lateral",
        "label": "Franja lateral semáforo (próx.)",
        "tipo": "switch",
        "default": False,
        "descripcion": {
            "es": "Reservado — banda lateral de semáforo. Sin efecto en v2.2; próxima iteración.",
            "en": "Reserved — lateral traffic-light band. No effect in v2.2; next iteration.",
        },
    },
]

# ── Constantes estéticas L9-Standard ──────────────────────────────────────────

_GRID_COLOR  = "#E5E7EB"
_FONT_FAMILY = "Arial, sans-serif"

_LABEL_GAP_FRAC = 0.50

_NIVEL_COLORS: dict[str, str] = {
    "operacion": "#10B981",
    "preavis":   "#F59E0B",
    "atencio":   "#EF4444",
}

_NIVEL_COL_MAP: dict[str, tuple[str, str]] = {
    "operacion": ("MINIMO_OPERACION", "MAXIMO_OPERACION"),
    "preavis":   ("MINIMO_PREAVIS",   "MAXIMO_PREAVIS"),
    "atencio":   ("MINIMO_ATENCIO",   "MAXIMO_ATENCIO"),
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _safe_float(val: Any, default: float | None = None) -> float | None:
    """Convierte a float, devuelve default si None/vacío/token sin resolver."""
    if val is None or str(val).strip().lower() in ("", "none", "null", "auto"):
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_bool(val: Any, default: bool = False) -> bool:
    """Convierte a bool aceptando strings 'true'/'false'."""
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("true", "1", "yes", "si", "sí")


def _ts_iso(ts: "pd.Timestamp") -> str:
    """Devuelve el Timestamp como string ISO compatible con xref='x' de Plotly."""
    return ts.isoformat()


def _html_error(mensaje: str) -> str:
    """Fragmento HTML de error con estética L9."""
    import html as _h  # noqa: PLC0415
    msg = _h.escape(str(mensaje))
    return (
        '<div style="display:flex;align-items:center;justify-content:center;'
        'width:100%;height:100%;background:#FEF2F2;border:1px solid #FCA5A5;'
        'border-radius:6px;font-family:Arial,sans-serif;font-size:9pt;'
        f'color:#DC2626;padding:12px;text-align:center;">Sin datos: {msg}</div>'
    )


# ── Bandas de umbral (modo automático desde BD) ────────────────────────────────

def _draw_thresholds_from_data(
    fig: "go.Figure",
    df_umbrales: "pd.DataFrame",
    modo: str,
    niveles: list[str],
    sensores_color: dict[str, str],
    y_lo: float,
    y_hi: float,
    opacidad: float,
    show_lines: bool,
    x_min_data: "pd.Timestamp",
    x_max_data: "pd.Timestamp",
    umbrales_show_labels: bool = True,
) -> tuple[float, float]:
    """Pinta bandas de umbral asimétricas (MAX / MIN independientes).

    Todas las líneas y bandas se acotan al rango [x_min_data, x_max_data]
    usando add_shape con xref='x', de modo que no invaden la zona de etiquetas.

    modos:
      envolvente: una sola banda global por nivel (min(MIN_*) … max(MAX_*)).
                  Color siempre del nivel. Etiqueta de nivel opcional a la derecha.
      por_sensor: línea por sensor y nivel, color del NIVEL (no del sensor).
                  Heurística de fusión: si todos los valores del grupo son iguales
                  (tolerancia 1e-9) se dibuja una única línea sin etiqueta de sensor.
                  Si divergen, se añade anotación NOM_SENSOR si umbrales_show_labels.
      (auto ya debe estar resuelto a uno de los dos antes de llamar)

    Args:
        x_min_data: Timestamp mínimo de los datos — borde izquierdo de líneas/bandas.
        x_max_data: Timestamp máximo de los datos — borde derecho de líneas/bandas.
        umbrales_show_labels: Si True, añade etiquetas de nivel (envolvente) o de
                              sensor (por_sensor cuando divergen).

    Devuelve (y_lo_ajustado, y_hi_ajustado).
    """
    import pandas as pd  # noqa: PLC0415

    if df_umbrales.empty or not niveles:
        return y_lo, y_hi

    df = df_umbrales.copy()
    for _, (col_min, col_max) in _NIVEL_COL_MAP.items():
        for col in (col_min, col_max):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    new_lo, new_hi = y_lo, y_hi

    _x0 = _ts_iso(x_min_data)
    _x1 = _ts_iso(x_max_data)

    _NIVEL_LABEL = {
        "operacion": "Operación",
        "preavis":   "Preaviso",
        "atencio":   "Atención",
    }

    def _hband(y0: float, y1: float, color: str, op: float) -> None:
        fig.add_shape(
            type="rect",
            xref="x", yref="y",
            x0=_x0, x1=_x1,
            y0=y0, y1=y1,
            fillcolor=color, opacity=op,
            line=dict(width=0),
            layer="below",
        )

    def _hline(y: float, color: str, dash: str = "dash", width: float = 0.7, op: float = 0.55) -> None:
        fig.add_shape(
            type="line",
            xref="x", yref="y",
            x0=_x0, x1=_x1,
            y0=y, y1=y,
            line=dict(color=color, width=width, dash=dash),
            opacity=op,
            layer="above",
        )

    def _label_umbral(y_val: float, nivel: str, cara: str = "") -> None:
        """Etiqueta de nivel con fondo blanco a la izquierda de la línea.

        Dibuja la etiqueta en ambas caras (máx y mín) — opción C definitiva.
        El argumento `cara` ("máx" o "mín") se añade al texto para distinguirlas.
        """
        if not umbrales_show_labels:
            return
        color = _NIVEL_COLORS.get(nivel, "#6B7280")
        texto_base = _NIVEL_LABEL.get(nivel, nivel)
        texto = f"{texto_base} · {cara}" if cara else texto_base
        fig.add_annotation(
            x=x_min_data, y=y_val,
            xref="x", yref="y",
            text=texto,
            showarrow=False,
            xanchor="left", yanchor="middle",
            xshift=2,
            font=dict(size=7, color=color, family=_FONT_FAMILY),
            bgcolor="white",
            bordercolor=color,
            borderwidth=0.5,
            borderpad=2,
            align="left",
        )

    if modo == "envolvente":
        prev_min_vals: float | None = None
        prev_max_vals: float | None = None

        for nivel in ["operacion", "preavis", "atencio"]:
            if nivel not in niveles:
                continue
            col_min, col_max = _NIVEL_COL_MAP[nivel]
            color = _NIVEL_COLORS[nivel]

            mins = df[col_min].dropna() if col_min in df.columns else pd.Series([], dtype=float)
            maxs = df[col_max].dropna() if col_max in df.columns else pd.Series([], dtype=float)

            g_min = float(mins.min()) if not mins.empty else None
            g_max = float(maxs.max()) if not maxs.empty else None

            if nivel == "operacion":
                if g_min is not None and g_max is not None:
                    _hband(g_min, g_max, color, opacidad)
                    if show_lines:
                        _hline(g_min, color)
                        _hline(g_max, color)
                    _label_umbral(g_max, nivel, cara="máx")
                    _label_umbral(g_min, nivel, cara="mín")
                    new_lo = min(new_lo, g_min)
                    new_hi = max(new_hi, g_max)
                elif g_max is not None:
                    if show_lines:
                        _hline(g_max, color)
                    _label_umbral(g_max, nivel, cara="máx")
                    new_hi = max(new_hi, g_max)
                elif g_min is not None:
                    if show_lines:
                        _hline(g_min, color)
                    _label_umbral(g_min, nivel, cara="mín")
                    new_lo = min(new_lo, g_min)
                prev_min_vals = g_min
                prev_max_vals = g_max

            else:
                # Banda inferior: [g_min, prev_min_vals]
                if g_min is not None and prev_min_vals is not None and g_min < prev_min_vals:
                    _hband(g_min, prev_min_vals, color, opacidad)
                    if show_lines:
                        _hline(g_min, color)
                    _label_umbral(g_min, nivel, cara="mín")
                    new_lo = min(new_lo, g_min)
                elif g_min is not None and prev_min_vals is None:
                    if show_lines:
                        _hline(g_min, color)
                    _label_umbral(g_min, nivel, cara="mín")
                    new_lo = min(new_lo, g_min)

                # Banda superior: [prev_max_vals, g_max]
                if g_max is not None and prev_max_vals is not None and g_max > prev_max_vals:
                    _hband(prev_max_vals, g_max, color, opacidad)
                    if show_lines:
                        _hline(g_max, color)
                    _label_umbral(g_max, nivel, cara="máx")
                    new_hi = max(new_hi, g_max)
                elif g_max is not None and prev_max_vals is None:
                    if show_lines:
                        _hline(g_max, color)
                    _label_umbral(g_max, nivel, cara="máx")
                    new_hi = max(new_hi, g_max)

                if g_min is not None:
                    prev_min_vals = min(prev_min_vals, g_min) if prev_min_vals is not None else g_min
                if g_max is not None:
                    prev_max_vals = max(prev_max_vals, g_max) if prev_max_vals is not None else g_max

    elif modo == "por_sensor":
        for nivel in ["operacion", "preavis", "atencio"]:
            if nivel not in niveles:
                continue
            color_nivel = _NIVEL_COLORS[nivel]
            col_min, col_max = _NIVEL_COL_MAP[nivel]

            for col in (col_min, col_max):
                if col not in df.columns:
                    continue
                pairs = [
                    (str(row.get("NOM_SENSOR") or "").strip(), float(row[col]))
                    for _, row in df.iterrows()
                    if not pd.isna(row.get(col))
                ]
                if not pairs:
                    continue

                vals = [v for _, v in pairs]
                if len(vals) > 1 and (max(vals) - min(vals)) < 1e-9:
                    # Fusión: todos idénticos → una sola línea
                    val_unico = vals[0]
                    _hline(val_unico, color_nivel, dash="dash", width=1.0, op=0.85)
                    _label_umbral(val_unico, nivel, cara="máx" if col == col_max else "mín")
                    new_lo = min(new_lo, val_unico)
                    new_hi = max(new_hi, val_unico)
                else:
                    for nom, val in pairs:
                        _hline(val, color_nivel, dash="dash", width=0.8, op=0.65)
                        new_lo = min(new_lo, val)
                        new_hi = max(new_hi, val)
                    if pairs:
                        if col == col_max:
                            y_etiqueta = max(v for _, v in pairs)
                        else:
                            y_etiqueta = min(v for _, v in pairs)
                        _label_umbral(y_etiqueta, nivel, cara="máx" if col == col_max else "mín")

    return new_lo, new_hi


# ── Bandas de umbral legacy (manual) ──────────────────────────────────────────

def _draw_threshold_bands(
    fig: "go.Figure",
    u_estable: float | None,
    u_atencion: float | None,
    u_alerta: float | None,
    y_lo: float,
    y_hi: float,
) -> None:
    """Dibuja bandas de umbral horizontales con opacidad 10 % (L9-Standard §Umbrales).

    Mantenida para retrocompatibilidad. En v2 no se llama desde generate() directamente.

    Zonas:
      Verde   (Estable)  — desde y_lo          hasta u_estable_max.
      Naranja (Atención) — desde u_atencion     hasta u_alerta.
      Rojo    (Alerta)   — desde u_alerta       hasta y_hi.
    """
    if u_estable is not None:
        fig.add_hrect(
            y0=y_lo, y1=u_estable,
            fillcolor="#10B981", opacity=0.10, line_width=0, layer="below",
        )
        fig.add_hline(
            y=u_estable, line_width=0.7, line_dash="dot",
            line_color="#10B981", opacity=0.55, layer="above",
        )

    if u_atencion is not None and u_alerta is not None:
        fig.add_hrect(
            y0=u_atencion, y1=u_alerta,
            fillcolor="#F59E0B", opacity=0.10, line_width=0, layer="below",
        )
        fig.add_hline(
            y=u_atencion, line_width=0.7, line_dash="dot",
            line_color="#F59E0B", opacity=0.55, layer="above",
        )
    elif u_atencion is not None:
        fig.add_hrect(
            y0=u_atencion, y1=y_hi,
            fillcolor="#F59E0B", opacity=0.10, line_width=0, layer="below",
        )
        fig.add_hline(
            y=u_atencion, line_width=0.7, line_dash="dot",
            line_color="#F59E0B", opacity=0.55, layer="above",
        )

    if u_alerta is not None:
        fig.add_hrect(
            y0=u_alerta, y1=y_hi,
            fillcolor="#EF4444", opacity=0.10, line_width=0, layer="below",
        )
        fig.add_hline(
            y=u_alerta, line_width=0.7, line_dash="dot",
            line_color="#EF4444", opacity=0.55, layer="above",
        )


# ── Función principal ──────────────────────────────────────────────────────────

@register_script(metadata)
def generate(params: dict[str, Any], figsize: tuple[float, float]) -> str:
    """Genera el gráfico temporal Spline L9 v2 con bandas de umbral desde BD.

    Novedades respecto a v1:
    - ``umbrales_origen``: 'off' | 'auto_bd' | 'manual'. Con 'auto_bd' el motor
      inyecta los umbrales en params['data']['umbrales'] antes de llamar a generate.
    - ``umbrales_modo``: 'auto' | 'envolvente' | 'por_sensor'. Con 'auto', si hay
      un solo sensor se usan bandas (envolvente) y si hay varios se usan líneas finas.
    - ``umbrales_niveles``: CSV de niveles a representar (operacion, preavis, atencio).
    - ``umbrales_opacidad``: opacidad del relleno.
    - ``umbrales_show_lines``: muestra líneas finas en los límites de cada zona.
    - Los umbrales se dibujan DESPUÉS de construir series_info (para tener colores
      de sensor disponibles) pero ANTES de la anti-colisión (Fase 2), de modo que
      pueden expandir y_lo/y_hi si los umbrales caen fuera del rango de datos.

    Args:
        params:  Dict de parámetros resueltos (ver PARAMETER_METADATA).
        figsize: (ancho_pulgadas, alto_pulgadas) del contenedor destino.

    Returns:
        Fragmento HTML con Plotly.js (CDN) embebido.
    """
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
    except ImportError:
        return (
            "<p style='color:#c0392b;font-family:Arial;font-size:10pt;'>"
            "Error: Plotly no instalado. Ejecuta: <code>pip install plotly</code></p>"
        )

    try:
        import pandas as pd
    except ImportError:
        return _html_error("Pandas no está instalado.")

    # ── Parámetros ────────────────────────────────────────────────────────────
    _val = params.get("sensor")
    sensor = str(_val).strip() if _val else ""
    fecha_ini     = params.get("fecha_inicio")
    fecha_fin_p   = params.get("fecha_fin")
    show_markers  = _safe_bool(params.get("show_markers"), False)
    palette_key   = str(params.get("palette") or "modern").lower()
    colores       = _PALETAS.get(palette_key, _PALETAS["modern"])
    y_min         = _safe_float(params.get("y_min"))
    y_max         = _safe_float(params.get("y_max"))
    # ── Modo de escala vertical: auto | fijo | flexible ──────────────────────
    # Retrocompatibilidad: si y_escala_modo no llega en params, se deriva del
    # estado de y_min/y_max (ambos vacíos → 'auto'; alguno con valor → 'fijo'),
    # de modo que las plantillas existentes mantienen su comportamiento.
    _modo_raw = params.get("y_escala_modo")
    if _modo_raw is None or str(_modo_raw).strip() == "":
        y_escala_modo = "fijo" if (y_min is not None or y_max is not None) else "auto"
    else:
        y_escala_modo = str(_modo_raw).strip().lower()
        if y_escala_modo not in ("auto", "fijo", "flexible"):
            y_escala_modo = "auto"
    # En 'fijo' los límites son duros (lado no expandible). En 'auto' y 'flexible'
    # cada lado puede crecer con datos, umbrales y etiquetas.
    lo_expandible = y_escala_modo != "fijo"
    hi_expandible = y_escala_modo != "fijo"
    _val_dec      = _safe_float(params.get("y_decimals"))
    y_dec         = int(_val_dec if _val_dec is not None else 2)
    x_fmt         = str(params.get("x_date_format") or "%d/%m/%y")
    _val_ls       = _safe_float(params.get("label_size"))
    label_size    = int(_val_ls if _val_ls is not None else 10)
    y_title       = str(params.get("y_axis_title") or "")
    x_title       = str(params.get("x_axis_title") or "")
    u_estable     = _safe_float(params.get("umbral_estable_max"))
    u_atencion    = _safe_float(params.get("umbral_atencion"))
    u_alerta      = _safe_float(params.get("umbral_alerta"))
    _val_lw       = _safe_float(params.get("line_width"))
    line_width    = float(_val_lw) if _val_lw is not None else 2.0
    smoothing     = _safe_bool(params.get("smoothing"), False)
    show_lbl_box  = _safe_bool(params.get("show_label_box"), False)
    show_vgrid       = _safe_bool(params.get("show_vgrid"), True)
    show_xaxis       = _safe_bool(params.get("show_xaxis"), True)
    show_yaxis_left  = _safe_bool(params.get("show_yaxis_left"), True)
    show_yaxis_right = _safe_bool(params.get("show_yaxis_right"), False)
    show_legend      = _safe_bool(params.get("show_legend"), True)
    legend_position  = str(params.get("legend_position") or "superior").lower()
    label_mode    = str(params.get("label_mode") or "ambos").lower()
    label_bgcolor = str(params.get("label_bgcolor") or "white")
    _val_ap       = _safe_float(params.get("label_area_pct"))
    label_area_pct = max(5.0, min(40.0, _val_ap if _val_ap is not None else 20.0))

    # Nuevos parámetros de umbrales
    umbrales_origen      = str(params.get("umbrales_origen") or "off").lower()
    umbrales_modo        = str(params.get("umbrales_modo") or "auto").lower()
    niveles_list         = [
        n.strip()
        for n in str(params.get("umbrales_niveles") or "operacion,preavis,atencio").split(",")
        if n.strip()
    ]
    _val_op = _safe_float(params.get("umbrales_opacidad"))
    umbrales_opacidad    = max(0.0, min(1.0, _val_op if _val_op is not None else 0.10))
    umbrales_show_lines  = _safe_bool(params.get("umbrales_show_lines"), True)
    umbrales_debug       = _safe_bool(params.get("umbrales_debug"), False)
    umbrales_show_status = _safe_bool(params.get("umbrales_show_status"), False)

    # Dimensiones
    width_px  = int(figsize[0] * 96 * 1.0)
    height_px = int(figsize[1] * 96 * 1.0)

    # ── Validación de datos ───────────────────────────────────────────────────
    data_ctx = params.get("data") or {}
    if not data_ctx or "historico" not in data_ctx or not data_ctx["historico"]:
        return _html_error("Sin datos disponibles")

    df = pd.DataFrame(data_ctx["historico"])
    if df.empty:
        return _html_error("Sin datos disponibles")

    df.columns = [c.upper() for c in df.columns]
    faltantes = {"NOM_SENSOR", "FECHA_MEDIDA", "MEDIDA"} - set(df.columns)
    if faltantes:
        return _html_error(
            f"Columnas no encontradas: {', '.join(sorted(faltantes))}. "
            f"Disponibles: {', '.join(df.columns.tolist())}"
        )

    df["FECHA_MEDIDA"] = pd.to_datetime(df["FECHA_MEDIDA"])
    df["MEDIDA"]       = pd.to_numeric(df["MEDIDA"], errors="coerce")

    if sensor:
        sensores_lista = [s.strip() for s in sensor.split(",") if s.strip()]
        if sensores_lista:
            df = df[df["NOM_SENSOR"].str.strip().isin(sensores_lista)]
            if df.empty:
                return _html_error(
                    f"Sin datos para sensor(es): {', '.join(sensores_lista)}"
                )

    if fecha_ini:
        try:
            df = df[df["FECHA_MEDIDA"] >= pd.to_datetime(fecha_ini)]
        except Exception:
            pass
    if fecha_fin_p:
        try:
            df = df[df["FECHA_MEDIDA"] <= pd.to_datetime(fecha_fin_p)]
        except Exception:
            pass

    if df.empty:
        return _html_error("Sin datos en el rango de fechas seleccionado")

    # ── Rangos ────────────────────────────────────────────────────────────────
    x_min_data = df["FECHA_MEDIDA"].min()
    x_max_data = df["FECHA_MEDIDA"].max()
    range_secs = max((x_max_data - x_min_data).total_seconds(), 3600.0)

    y_vals  = df["MEDIDA"].dropna()
    d_min   = float(y_vals.min()) if len(y_vals) else 0.0
    d_max   = float(y_vals.max()) if len(y_vals) else 1.0
    d_range = max(d_max - d_min, 1.0)
    pad     = max(d_range * 0.10, 0.1)
    # Límites iniciales según modo de escala:
    #   fijo     → valor configurado como límite duro.
    #   flexible → ventana mínima garantizada; se expande si datos/umbrales/etiquetas la superan.
    #   auto     → pegado a los datos con holgura del 10 %.
    if y_escala_modo == "fijo":
        y_lo = y_min if y_min is not None else d_min - pad
        y_hi = y_max if y_max is not None else d_max + pad
    elif y_escala_modo == "flexible":
        y_lo = min(y_min, d_min - pad) if y_min is not None else d_min - pad
        y_hi = max(y_max, d_max + pad) if y_max is not None else d_max + pad
    else:  # auto
        y_lo = d_min - pad
        y_hi = d_max + pad

    # ── Fase 1 — Position: trazar series ─────────────────────────────────────
    fig = go.Figure()

    mode       = "lines+markers" if show_markers else "lines"
    line_shape = "spline" if smoothing else "linear"
    series_info: list[dict] = []

    mapa_colores = asignar_colores_sensores(
        [str(n) for n in df["NOM_SENSOR"].unique()],
        palette_key,
    )

    for i, (nom, group) in enumerate(df.groupby("NOM_SENSOR")):
        sub = group.dropna(subset=["MEDIDA"]).sort_values("FECHA_MEDIDA")
        if sub.empty:
            continue
        color = mapa_colores.get(str(nom), colores[i % len(colores)])
        fig.add_trace(go.Scatter(
            x=sub["FECHA_MEDIDA"],
            y=sub["MEDIDA"],
            mode=mode,
            name=str(nom),
            showlegend=True,
            line=dict(color=color, width=line_width, shape=line_shape,
                      smoothing=1.3 if smoothing else 0),
            marker=dict(size=5, color=color, line=dict(width=0)) if show_markers else {},
            hovertemplate=f"<b>{nom}</b><br>%{{x|{x_fmt}}}<br>%{{y:.{y_dec}f}}<extra></extra>",
        ))
        series_info.append({
            "sensor":  str(nom),
            "last_x":  sub["FECHA_MEDIDA"].iloc[-1],
            "last_y":  float(sub["MEDIDA"].iloc[-1]),
            "label_y": float(sub["MEDIDA"].iloc[-1]),
            "color":   color,
        })

    if not series_info:
        return _html_error("Sin series con datos válidos")

    # ── Umbrales — se aplican DESPUÉS de series_info (para colores) y
    #    ANTES de la anti-colisión (Fase 2) porque pueden expandir y_lo/y_hi ──
    if umbrales_origen == "auto_bd":
        df_umbrales = pd.DataFrame(params.get("data", {}).get("umbrales") or [])
    elif umbrales_origen == "manual":
        # Construye df_umbrales de 1 fila asumiendo simetría (MIN_* = -MAX_*)
        row: dict = {}
        if u_estable is not None:
            row["MAXIMO_OPERACION"] = u_estable
            row["MINIMO_OPERACION"] = -u_estable
        if u_atencion is not None:
            row["MAXIMO_PREAVIS"] = u_atencion
            row["MINIMO_PREAVIS"] = -u_atencion
        if u_alerta is not None:
            row["MAXIMO_ATENCIO"] = u_alerta
            row["MINIMO_ATENCIO"] = -u_alerta
        df_umbrales = pd.DataFrame([row]) if row else pd.DataFrame()
    else:
        df_umbrales = pd.DataFrame()

    # Volcado de diagnóstico — solo si flag activo y hay datos
    if umbrales_debug and not df_umbrales.empty:
        try:
            import sys  # noqa: PLC0415
            print("=" * 80, file=sys.stderr)
            print("[grafico_spline_l9_v2] DEBUG — Tabla de umbrales recibida:", file=sys.stderr)
            print(f"  origen: {umbrales_origen} | filas: {len(df_umbrales)}", file=sys.stderr)
            print("-" * 80, file=sys.stderr)
            print(df_umbrales.to_string(index=False, na_rep="NULL"), file=sys.stderr)
            print("=" * 80, file=sys.stderr)
        except Exception:
            pass

    if not df_umbrales.empty:
        modo_efectivo = umbrales_modo
        if modo_efectivo == "auto":
            modo_efectivo = "envolvente" if len(df_umbrales) == 1 else "por_sensor"
        sensores_color = {info["sensor"]: info["color"] for info in series_info}
        y_lo_new, y_hi_new = _draw_thresholds_from_data(
            fig, df_umbrales, modo_efectivo, niveles_list,
            sensores_color, y_lo, y_hi,
            opacidad=umbrales_opacidad,
            show_lines=umbrales_show_lines,
            x_min_data=x_min_data,
            x_max_data=x_max_data,
            umbrales_show_labels=_safe_bool(params.get("umbrales_show_labels"), True),
        )
        if lo_expandible:
            y_lo = y_lo_new
        if hi_expandible:
            y_hi = y_hi_new

        # NOTA: el subtítulo está desactivado por defecto en v2.4 (decisión cliente
        # 2026-05). Para reactivar, poner umbrales_show_status=True en parámetros.
        # Subtítulo de estado global (M9) — cuenta sensores por zona
        if umbrales_show_status:
            df_umb_idx = df_umbrales.copy()
            for col in ("MINIMO_ATENCIO", "MAXIMO_ATENCIO", "MINIMO_PREAVIS",
                        "MAXIMO_PREAVIS", "MINIMO_OPERACION", "MAXIMO_OPERACION"):
                if col in df_umb_idx.columns:
                    df_umb_idx[col] = pd.to_numeric(df_umb_idx[col], errors="coerce")
            if "NOM_SENSOR" in df_umb_idx.columns:
                df_umb_idx = df_umb_idx.set_index("NOM_SENSOR")

            cnt_op, cnt_pre, cnt_ate = 0, 0, 0
            for info in series_info:
                nom = info["sensor"]
                last = info["last_y"]
                if nom not in df_umb_idx.index:
                    continue
                fila = df_umb_idx.loc[nom]

                def _get(col: str) -> float | None:
                    v = fila.get(col) if isinstance(fila, pd.Series) else None
                    try:
                        f = float(v)  # type: ignore[arg-type]
                        return None if pd.isna(f) else f
                    except (TypeError, ValueError):
                        return None

                zona = "operacion"
                if (_get("MINIMO_ATENCIO") is not None and last < _get("MINIMO_ATENCIO")) or \
                   (_get("MAXIMO_ATENCIO") is not None and last > _get("MAXIMO_ATENCIO")):
                    zona = "atencion"
                elif (_get("MINIMO_PREAVIS") is not None and last < _get("MINIMO_PREAVIS")) or \
                     (_get("MAXIMO_PREAVIS") is not None and last > _get("MAXIMO_PREAVIS")) or \
                     (_get("MINIMO_OPERACION") is not None and last < _get("MINIMO_OPERACION")) or \
                     (_get("MAXIMO_OPERACION") is not None and last > _get("MAXIMO_OPERACION")):
                    zona = "preaviso"

                if zona == "operacion":
                    cnt_op += 1
                elif zona == "preaviso":
                    cnt_pre += 1
                else:
                    cnt_ate += 1

            total_cls = cnt_op + cnt_pre + cnt_ate
            if total_cls > 0:
                partes = [
                    f'<span style="color:#10B981">{cnt_op} en operación</span>',
                    f'<span style="color:#F59E0B">{cnt_pre} en preaviso</span>',
                    f'<span style="color:#EF4444">{cnt_ate} en atención</span>',
                ]
                texto_estado = f"{total_cls} sensores · " + " · ".join(partes)
                fig.add_annotation(
                    text=texto_estado,
                    xref="paper", yref="paper",
                    x=0, y=1.06, xanchor="left", yanchor="bottom",
                    showarrow=False,
                    font=dict(size=9, color="#475569", family=_FONT_FAMILY),
                )

    # ── Espacio dinámico para etiquetas (cálculo basado en texto real) ────────
    # Estima el ancho que ocuparán las etiquetas más largas (en píxeles),
    # lo convierte a segundos del eje X y extiende x_axis_right justo lo
    # necesario para que las etiquetas queden pegadas al borde derecho del plot.
    # label_area_pct actúa como CAP superior (límite máximo de área reservada).
    def _texto_etiqueta_estimado(info: dict) -> str:
        """Replica la lógica de construcción de label_text (líneas ~1648-1653)
        SIN las tags HTML <b></b>, para estimar ancho visible real."""
        nom = str(info["sensor"])
        val = f"{info['last_y']:,.{y_dec}f}"
        if label_mode == "nombre":
            return nom
        if label_mode == "valor":
            return val
        return f"{nom} | {val}"

    # Aproximación de ancho de carácter en píxeles para Inter/sans-serif a label_size pt.
    # Factor 0.70: los códigos de sensor son mayúsculas (más anchas) y el valor va
    # en negrita; subimos respecto al 0.60 anterior para no infraestimar el ancho
    # real y evitar el recorte del texto.
    _CHAR_PX_FACTOR   = 0.70
    _max_label_chars  = max(
        (len(_texto_etiqueta_estimado(_i)) for _i in series_info),
        default=20,
    )

    # Ancho efectivo del plot: descontamos los márgenes laterales.
    # NOTA: los valores 40 (l) y 12 (r) deben coincidir con _margins definido
    # más abajo en update_layout. Si se modifican allí, actualizar aquí.
    _plot_width_px    = max(width_px - 40 - 12, 100)
    _secs_per_px      = range_secs / _plot_width_px

    # Gap entre fin de serie e inicio de etiqueta + holgura al borde derecho.
    gap_secs    = range_secs * 0.025
    _buffer_secs = range_secs * 0.02

    # Cap por label_area_pct: límite máximo del área reservada a la derecha.
    _label_frac     = label_area_pct / 100.0
    _extra_secs_cap = range_secs * (_label_frac / max(1.0 - _label_frac, 0.01))

    # ── Auto-ajuste horizontal de fuente (anti-recorte) ──────────────────────
    # Si la etiqueta más larga no cabe dentro del área reservada (label_area_pct),
    # reducimos label_size hasta que quepa (suelo 7 pt). Así el texto nunca se
    # recorta y label_area_pct pasa a controlar también el tamaño de fuente.
    while label_size > 7:
        _w_secs = (_max_label_chars * label_size * _CHAR_PX_FACTOR) * _secs_per_px
        if gap_secs + _w_secs + _buffer_secs <= _extra_secs_cap:
            break
        label_size -= 1

    _char_px_factor   = label_size * _CHAR_PX_FACTOR
    _label_width_px   = _max_label_chars * _char_px_factor
    _label_width_secs = _label_width_px * _secs_per_px

    # Necesidad real (con la fuente ya ajustada): gap + ancho de etiqueta + holgura.
    _extra_secs_need = gap_secs + _label_width_secs + _buffer_secs

    # Mínimo entre lo necesario y el cap (compatibilidad con label_area_pct).
    extra_secs = min(_extra_secs_need, _extra_secs_cap)

    x_axis_left  = x_min_data - pd.Timedelta(seconds=range_secs * 0.01)
    x_axis_right = x_max_data + pd.Timedelta(seconds=extra_secs)
    label_x_ts   = x_max_data + pd.Timedelta(seconds=gap_secs)

    # ── Cambio 1+2 — label_h sensible a nº de líneas + auto-reducción ─────────
    _effective_label_size = label_size
    _effective_label_mode = label_mode
    _n_lines = 1

    for _attempt in range(20):
        _h_factor = 1.6 + (_n_lines * 0.8)
        label_h   = (y_hi - y_lo) * (_effective_label_size / height_px) * _h_factor
        label_gap = label_h * _LABEL_GAP_FRAC
        total_needed = len(series_info) * (label_h + label_gap) - label_gap
        available    = (y_hi - y_lo) * 0.90
        if total_needed <= available:
            break
        if _effective_label_size > 7:
            _effective_label_size -= 1
        elif _n_lines == 2:
            _effective_label_mode = "valor"
            _n_lines = 1
            _effective_label_size = label_size
        else:
            break

    label_size = _effective_label_size
    label_mode = _effective_label_mode

    # ── Fase 2 — Stack: anti-colisión bidireccional centrada ──────────────────
    series_info.sort(key=lambda e: e["last_y"], reverse=True)

    for j in range(1, len(series_info)):
        prev_bottom = series_info[j - 1]["label_y"] - label_h / 2 - label_gap
        if series_info[j]["label_y"] + label_h / 2 > prev_bottom:
            series_info[j]["label_y"] = prev_bottom - label_h / 2

    block_top    = series_info[0]["label_y"] + label_h / 2
    block_bottom = series_info[-1]["label_y"] - label_h / 2
    block_center = (block_top + block_bottom) / 2.0

    original_ys   = [i["last_y"] for i in series_info]
    target_center = (max(original_ys) + min(original_ys)) / 2.0

    shift = target_center - block_center
    max_shift_up   = y_hi - (block_top + shift) - label_h * 0.3
    max_shift_down = (block_bottom + shift) - y_lo + label_h * 0.3
    if shift > 0 and shift > max_shift_up:
        shift = max(0.0, max_shift_up)
    elif shift < 0 and abs(shift) > max_shift_down:
        shift = -max(0.0, max_shift_down)

    for info in series_info:
        info["label_y"] += shift

    # ── Re-anclaje superior (minimiza la expansión inferior del eje) ─────────
    # Si el bloque de etiquetas desborda por abajo, lo subimos hasta que su
    # techo quede justo por debajo de y_hi, en lugar de arrancar en la serie con
    # el último valor más alto. Reduce cuánto hay que ampliar el eje hacia abajo.
    # Solo cuando el suelo es expandible (auto/flexible).
    if lo_expandible and len(series_info) > 1:
        _blk_top    = max(i["label_y"] for i in series_info) + label_h / 2
        _blk_bottom = min(i["label_y"] for i in series_info) - label_h / 2
        _techo      = y_hi - label_h * 0.3
        if _blk_bottom < y_lo and _blk_top < _techo:
            _lift = min(_techo - _blk_top, y_lo - _blk_bottom)
            if _lift > 0:
                for info in series_info:
                    info["label_y"] += _lift

    # ── Expansión dinámica de rango Y post-stacking ───────────────────────────
    if lo_expandible:
        lowest_label = min(i["label_y"] for i in series_info) - label_h
        if lowest_label < y_lo:
            y_lo = lowest_label - label_h * 0.2
    if hi_expandible:
        highest_label = max(i["label_y"] for i in series_info) + label_h
        if highest_label > y_hi:
            y_hi = highest_label + label_h * 0.2

    # ── Clamp/redistribuir etiquetas en rango Y fijado ───────────────────────
    if (not lo_expandible or not hi_expandible) and len(series_info) > 0:
        _m = label_h * 0.15

        _top = series_info[0]["label_y"] + label_h / 2 + _m
        if _top > y_hi:
            _d = _top - y_hi
            for _si in series_info:
                _si["label_y"] -= _d

        _bottom = series_info[-1]["label_y"] - label_h / 2 - _m
        if _bottom < y_lo:
            _d = y_lo - _bottom
            for _si in series_info:
                _si["label_y"] += _d

        _top    = series_info[0]["label_y"]  + label_h / 2 + _m
        _bottom = series_info[-1]["label_y"] - label_h / 2 - _m
        if _top > y_hi or _bottom < y_lo:
            _n     = len(series_info)
            _avail = (y_hi - y_lo) - 2 * _m
            if _n == 1:
                series_info[0]["label_y"] = (y_hi + y_lo) / 2.0
            else:
                _step       = _avail / (_n - 1)
                _top_center = y_hi - _m - label_h / 2
                for _idx, _si in enumerate(series_info):
                    _si["label_y"] = _top_center - _step * _idx

    # ── Fase 3 — Connect: conector degradado + etiqueta exterior ─────────────
    if label_mode != "ninguno":
        for info in series_info:
            nom_text = info["sensor"]
            val_text = f"{info['last_y']:,.{y_dec}f}"
            if label_mode == "nombre":
                label_text = nom_text
            elif label_mode == "valor":
                label_text = f"<b>{val_text}</b>"
            else:
                label_text = f"{nom_text} | <b>{val_text}</b>"

            N_STEPS = 12
            color_hex = info["color"]

            h = color_hex.lstrip("#")
            if len(h) == 6:
                r_c, g_c, b_c = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            else:
                r_c, g_c, b_c = 100, 100, 100

            lx_start = info["last_x"]
            lx_end   = label_x_ts
            ly_start = info["last_y"]
            ly_end   = info["label_y"]
            total_s  = (lx_end - lx_start).total_seconds()

            conn_x, conn_y, conn_colors = [], [], []
            for k in range(N_STEPS + 1):
                t = k / N_STEPS
                alpha = t
                ts_k  = lx_start + pd.Timedelta(seconds=total_s * t)
                y_k   = ly_start + (ly_end - ly_start) * t
                conn_x.append(ts_k)
                conn_y.append(y_k)
                conn_colors.append(f"rgba({r_c},{g_c},{b_c},{alpha:.3f})")

            fig.add_trace(go.Scatter(
                x=conn_x,
                y=conn_y,
                mode="markers",
                showlegend=False,
                hoverinfo="skip",
                marker=dict(
                    color=conn_colors,
                    size=1,
                    symbol="circle",
                    line=dict(width=0),
                ),
            ))

            fig.add_trace(go.Scatter(
                x=[lx_start, lx_end],
                y=[ly_start, ly_end],
                mode="lines",
                showlegend=False,
                hoverinfo="skip",
                line=dict(
                    color=f"rgba({r_c},{g_c},{b_c},0.25)",
                    width=0.2,
                    dash="dot",
                ),
            ))

            fig.add_trace(go.Scatter(
                x=[info["last_x"]],
                y=[info["last_y"]],
                mode="markers",
                showlegend=False,
                hoverinfo="skip",
                marker=dict(
                    color=color_hex,
                    size=4,
                    line=dict(color="white", width=1),
                ),
            ))

            _border  = info["color"] if show_lbl_box else "rgba(0,0,0,0)"
            _bgcol   = label_bgcolor if label_bgcolor else "rgba(0,0,0,0)"
            if _bgcol.lower() in ("transparent", "none", ""):
                _bgcol = "rgba(0,0,0,0)"

            fig.add_annotation(
                x=_ts_iso(label_x_ts),
                y=info["label_y"],
                xref="x",
                yref="y",
                text=label_text,
                showarrow=False,
                xanchor="left",
                yanchor="middle",
                font=dict(size=label_size, color=info["color"], family=_FONT_FAMILY),
                bgcolor=_bgcol,
                bordercolor=_border,
                borderwidth=1 if show_lbl_box else 0,
                borderpad=3,
                align="left",
            )

    # ── Tick de cierre del informe (fecha_fin) ───────────────────────────────
    if _safe_bool(params.get("tick_cierre_show"), False):
        _fc = params.get("fecha_fin")
        if _fc:
            try:
                ts_cierre = pd.to_datetime(_fc)
                if x_min_data <= ts_cierre <= x_max_data:
                    fig.add_shape(
                        type="line", xref="x", yref="paper",
                        x0=ts_cierre, x1=ts_cierre, y0=0, y1=1,
                        line=dict(color="#9CA3AF", width=0.6, dash="dash"),
                        layer="below",
                    )
                    fig.add_annotation(
                        x=ts_cierre, y=1, xref="x", yref="paper",
                        text="Cierre", showarrow=False,
                        xanchor="center", yanchor="bottom",
                        font=dict(size=7, color="#9CA3AF", family=_FONT_FAMILY),
                        yshift=2,
                    )
            except Exception:
                pass

    # ── Layout: estilo informe L9 v2 ─────────────────────────────────────────
    _legend_cfg = {
        "superior": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        "inferior": dict(orientation="h", yanchor="top",    y=-0.15, xanchor="center", x=0.5),
        "derecha":  dict(orientation="v", yanchor="middle", y=0.5,  xanchor="left",   x=1.02),
        "izquierda": dict(orientation="v", yanchor="middle", y=0.5,  xanchor="right",  x=-0.05),
    }
    _leg_pos = _legend_cfg.get(legend_position, _legend_cfg["superior"])
    _margins = {"l": 40, "r": 12, "t": 36, "b": 30}
    if show_legend:
        if legend_position == "inferior":
            _margins["b"] = 50
        elif legend_position == "derecha":
            _margins["r"] = 80
        elif legend_position == "izquierda":
            _margins["l"] = 80
    if umbrales_show_status and not df_umbrales.empty:
        _margins["t"] += 12

    fig.update_layout(
        title=None,
        showlegend=show_legend,
        legend=dict(
            **_leg_pos,
            font=dict(size=9, family=_FONT_FAMILY),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            itemsizing="trace",
        ),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family=_FONT_FAMILY, size=9),
        margin=dict(**_margins),
        width=width_px,
        height=height_px,
        xaxis=dict(
            showgrid=show_vgrid,
            gridcolor=_GRID_COLOR,
            gridwidth=0.5,
            griddash="solid",
            linecolor="#D1D5DB",
            linewidth=1 if show_xaxis else 0,
            showline=show_xaxis,
            mirror=False,
            tickfont=dict(size=8, family=_FONT_FAMILY),
            tickformat=x_fmt,
            range=[_ts_iso(x_axis_left), _ts_iso(x_axis_right)],
            title=dict(text=x_title, font=dict(size=9, family=_FONT_FAMILY), standoff=8),
            ticks="outside" if show_xaxis else "",
            ticklen=3,
            tickcolor="#D1D5DB",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=_GRID_COLOR,
            gridwidth=0.5,
            griddash="solid",
            linecolor="#D1D5DB",
            linewidth=1 if show_yaxis_left else 0,
            showline=show_yaxis_left,
            mirror=show_yaxis_right,
            zeroline=False,
            tickfont=dict(size=8, family=_FONT_FAMILY),
            tickformat=f".{y_dec}f",
            range=[y_lo, y_hi],
            title=dict(text=y_title, font=dict(size=9, family=_FONT_FAMILY), standoff=8),
            ticks="outside" if show_yaxis_left else "",
            ticklen=3,
            tickcolor="#D1D5DB",
        ),
        hovermode="x unified",
    )

    import re as _re  # noqa: PLC0415
    _html = pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=False,
        config={"staticPlot": False, "responsive": True, "displayModeBar": False},
    )
    # Plotly JSON-escapa caracteres no-ASCII (ó → ó). Revertimos para que
    # los caracteres especiales sean legibles en el HTML y en los tests de búsqueda.
    return _re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), _html)

"""Gráfico de evolución temporal Spline L9 v1 — estilo informe con etiquetas externas.

Variante de ``grafico_spline_l9.py`` orientada a informes impresos:
  * Etiquetas al lado derecho del área de trazado con espacio reservado dinámicamente.
  * Conector degradado desde transparente (en el último punto) hasta opaco (en la etiqueta).
  * Modo de etiqueta configurable: nombre_sensor | valor | ambos | ninguno.
  * Fondo de etiqueta configurable para evitar contaminación visual con los ejes.
  * Anti-colisión greedy vertical para etiquetas solapadas.

Función principal: ``generate(params, figsize) -> str``

Arquitectura de 3 fases:
  Fase 1 — Position: trazar series y reservar espacio derecho dinámico.
  Fase 2 — Stack: anti-colisión greedy (vertical) sobre el último punto.
  Fase 3 — Connect: conector degradado + anotación de etiqueta a la derecha.

Parámetros configurables
------------------------
sensor          : str   — nombre de sensor ($CURRENT = sensor activo)
fecha_inicio    : str   — fecha inicio ISO 8601 ($CURRENT_fecha_inicial)
fecha_fin       : str   — fecha fin   ISO 8601 ($CURRENT_fecha_final)
show_markers    : bool  — True = mode='lines+markers'
palette         : str   — 'modern' | 'corporate' | 'vibrant'
y_min, y_max    : float — límites eje Y; None = autoescala ±10 %
y_decimals      : int   — decimales en etiquetas de valor y eje Y
x_date_format   : str   — strftime/d3 para eje X
label_size      : int   — tamaño de fuente de las etiquetas (pt)
label_mode      : str   — 'nombre' | 'valor' | 'ambos' | 'ninguno'
label_bgcolor   : str   — color de fondo de las etiquetas (CSS); 'transparent' = sin fondo
label_area_pct  : float — % del ancho total reservado para las etiquetas (default 20)
y_axis_title    : str   — título eje Y
x_axis_title    : str   — título eje X
umbral_estable_max : float — límite superior zona estable
umbral_atencion    : float — inicio zona atención
umbral_alerta      : float — inicio zona alerta
show_vgrid         : bool  — True = rejilla vertical en el eje X
show_legend        : bool  — True = muestra la leyenda del gráfico
legend_position    : str   — 'superior' | 'inferior' | 'izquierda' | 'derecha'
data            : dict  — payload con clave 'historico' (inyectado por el motor)
"""

from __future__ import annotations

from typing import Any

from utils.script_registry import ParameterMetadata, ScriptMetadata, register_script

# ── Registro de metadatos ──────────────────────────────────────────────────────

metadata = ScriptMetadata(
    nombre="grafico_spline_l9_v1",
    tipo="grafico",
    descripcion="Evolución temporal spline — estilo informe: leyenda superior, valor al final de línea",
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
            descripcion="Límite superior zona estable (verde, 10 % opacidad).",
        ),
        ParameterMetadata(
            nombre="umbral_atencion",
            tipo="numero",
            requerido=False,
            default=None,
            descripcion="Inicio zona de atención (naranja, 10 % opacidad).",
        ),
        ParameterMetadata(
            nombre="umbral_alerta",
            tipo="numero",
            requerido=False,
            default=None,
            descripcion="Inicio zona de alerta (rojo, 10 % opacidad).",
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
            descripcion="Fondo de la etiqueta (color CSS o 'transparent'). Evita contaminación visual.",
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
        "descripcion": {"es": "Límite superior zona estable (verde, 10 % opacidad).", "en": "Upper limit of stable zone (green, 10% opacity)."},
    },
    {
        "nombre": "umbral_atencion",
        "tipo": "numero",
        "requerido": False,
        "default": None,
        "descripcion": {"es": "Inicio zona de atención (naranja, 10 % opacidad).", "en": "Start of attention zone (orange, 10% opacity)."},
    },
    {
        "nombre": "umbral_alerta",
        "tipo": "numero",
        "requerido": False,
        "default": None,
        "descripcion": {"es": "Inicio zona de alerta (rojo, 10 % opacidad).", "en": "Start of alert zone (red, 10% opacity)."},
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
        "label": "Umbral estable (verde)",
        "tipo": "number",
        "default": None,
        "descripcion": {"es": "Límite superior zona estable (verde, 10 % opacidad).", "en": "Upper boundary of the stable zone (green, 10% opacity)."},
    },
    {
        "id": "umbral_atencion",
        "label": "Umbral atención (naranja)",
        "tipo": "number",
        "default": None,
        "descripcion": {"es": "Inicio zona de atención (naranja, 10 % opacidad).", "en": "Start of the attention zone (orange, 10% opacity)."},
    },
    {
        "id": "umbral_alerta",
        "label": "Umbral alerta (rojo)",
        "tipo": "number",
        "default": None,
        "descripcion": {"es": "Inicio zona de alerta (rojo, 10 % opacidad).", "en": "Start of the alert zone (red, 10% opacity)."},
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
]

# ── Paletas ────────────────────────────────────────────────────────────────────

_PALETAS: dict[str, list[str]] = {
    "modern": [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA",
        "#FFA15A", "#19D3F3", "#FF6692", "#B6E880",
    ],
    "corporate": [
        "#1D4E89", "#2874A6", "#5DADE2", "#A9CCE3",
        "#1E8449", "#52BE80", "#784212", "#E59866",
    ],
    "vibrant": [
        "#E63946", "#2A9D8F", "#E9C46A", "#F4A261",
        "#457B9D", "#8338EC", "#FB5607", "#06D6A0",
    ],
}

# ── Constantes estéticas L9-Standard ──────────────────────────────────────────

_GRID_COLOR  = "#E5E7EB"
_FONT_FAMILY = "Arial, sans-serif"

# Anti-colisión: separación mínima entre etiquetas = 50 % de la altura estimada.
_LABEL_GAP_FRAC = 0.50


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


# ── Función principal ──────────────────────────────────────────────────────────

@register_script(metadata)
def generate(params: dict[str, Any], figsize: tuple[float, float]) -> str:
    """Genera el gráfico temporal Spline L9 v1 con etiquetas externas y conector degradado.

    Novedades respecto a la versión anterior:
    - ``label_mode``: controla si la etiqueta muestra nombre, valor, ambos o ninguno.
    - ``label_bgcolor``: fondo de la etiqueta para evitar contaminación visual con ejes y líneas.
    - ``label_area_pct``: % del ancho del gráfico reservado dinámicamente para las etiquetas.
      El eje X se recorta para que las etiquetas quepan sin cortarse.
    - Conector degradado: línea de guía que va de transparente (en el último punto) a opaco
      (en la etiqueta), renderizada mediante un scatter con marcadores de color interpolado.

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
    line_width    = int(_val_lw if _val_lw is not None else 2)
    smoothing     = _safe_bool(params.get("smoothing"), False)
    show_lbl_box  = _safe_bool(params.get("show_label_box"), False)
    show_vgrid       = _safe_bool(params.get("show_vgrid"), True)
    show_xaxis       = _safe_bool(params.get("show_xaxis"), True)
    show_yaxis_left  = _safe_bool(params.get("show_yaxis_left"), True)
    show_yaxis_right = _safe_bool(params.get("show_yaxis_right"), False)
    show_legend      = _safe_bool(params.get("show_legend"), True)
    legend_position  = str(params.get("legend_position") or "superior").lower()
    # Nuevos parámetros de etiqueta
    label_mode    = str(params.get("label_mode") or "ambos").lower()
    label_bgcolor = str(params.get("label_bgcolor") or "white")
    _val_ap       = _safe_float(params.get("label_area_pct"))
    label_area_pct = max(5.0, min(40.0, _val_ap if _val_ap is not None else 20.0))

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

    # Rango Y: autoescala ±10 % o valores explícitos
    y_vals  = df["MEDIDA"].dropna()
    d_min   = float(y_vals.min()) if len(y_vals) else 0.0
    d_max   = float(y_vals.max()) if len(y_vals) else 1.0
    d_range = max(d_max - d_min, 1.0)
    pad     = max(d_range * 0.10, 0.1)
    y_lo    = y_min if y_min is not None else d_min - pad
    y_hi    = y_max if y_max is not None else d_max + pad
    # label_area_pct adaptativo, label_frac, x_axis_right, label_x_ts y label_h
    # se calculan después de la Fase 1 cuando series_info ya está disponible.

    # ── Fase 1 — Position: trazar series ─────────────────────────────────────
    fig = go.Figure()

    _draw_threshold_bands(fig, u_estable, u_atencion, u_alerta, y_lo, y_hi)

    mode       = "lines+markers" if show_markers else "lines"
    line_shape = "spline" if smoothing else "linear"
    series_info: list[dict] = []

    for i, (nom, group) in enumerate(df.groupby("NOM_SENSOR")):
        sub = group.dropna(subset=["MEDIDA"]).sort_values("FECHA_MEDIDA")
        if sub.empty:
            continue
        color = colores[i % len(colores)]
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

    # ── Espacio dinámico para etiquetas (calculado post-Fase 1) ───────────────
    # El área del gráfico ocupa (100 - label_area_pct) % del rango temporal.
    label_frac  = label_area_pct / 100.0
    series_frac = 1.0 - label_frac
    total_visible_secs = range_secs / series_frac
    extra_secs  = total_visible_secs - range_secs

    x_axis_left  = x_min_data - pd.Timedelta(seconds=range_secs * 0.01)
    x_axis_right = x_max_data + pd.Timedelta(seconds=extra_secs)

    gap_secs   = extra_secs * 0.20
    label_x_ts = x_max_data + pd.Timedelta(seconds=gap_secs + extra_secs * 0.05)

    # ── Cambio 1+2 — label_h sensible a nº de líneas + auto-reducción ─────────
    _effective_label_size = label_size
    _effective_label_mode = label_mode
    _n_lines = 1  # Todo se imprime en 1 línea

    for _attempt in range(20):
        _h_factor = 1.6 + (_n_lines * 0.8)   # 1 línea → 2.4, 2 líneas → 3.2
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
            _effective_label_size = label_size  # reiniciar tamaño con 1 línea
        else:
            break  # no se puede reducir más, la expansión Y compensará

    # Actualizar variables que usa la Fase 3
    label_size = _effective_label_size
    label_mode = _effective_label_mode

    # ── Fase 2 — Stack: anti-colisión bidireccional centrada ──────────────────
    series_info.sort(key=lambda e: e["last_y"], reverse=True)

    # Paso 2a: greedy top-down
    for j in range(1, len(series_info)):
        prev_bottom = series_info[j - 1]["label_y"] - label_h / 2 - label_gap
        if series_info[j]["label_y"] + label_h / 2 > prev_bottom:
            series_info[j]["label_y"] = prev_bottom - label_h / 2

    # Paso 2b: centrar el bloque respecto a la mediana de last_y originales
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

    # ── Cambio 4 — Expansión dinámica de rango Y post-stacking ───────────────
    # Solo expande el límite si el usuario NO lo fijó explícitamente.
    if y_min is None:
        lowest_label = min(i["label_y"] for i in series_info) - label_h
        if lowest_label < y_lo:
            y_lo = lowest_label - label_h * 0.2
    if y_max is None:
        highest_label = max(i["label_y"] for i in series_info) + label_h
        if highest_label > y_hi:
            y_hi = highest_label + label_h * 0.2

    # ── Cambio 4b — Clamp/redistribuir etiquetas en rango Y fijado ───────────
    # Cuando y_min o y_max están fijados por el usuario la expansión de arriba
    # está deshabilitada. Si el stacking empujó etiquetas fuera del rango
    # visible Plotly las recortaría silenciosamente.
    # Estrategia en dos pasos:
    #   Paso A — desplazar el bloque completo hacia dentro del rango si
    #            sobresale por un único extremo.
    #   Paso B — si tras el desplazamiento el bloque sigue desbordando
    #            (es más alto que el rango disponible), redistribuir las
    #            etiquetas uniformemente dentro de [y_lo, y_hi].
    if (y_min is not None or y_max is not None) and len(series_info) > 0:
        _m = label_h * 0.15  # margen de seguridad mínimo (15 % de la altura)

        # series_info está ordenado last_y desc → [0] = más alta, [-1] = más baja
        # Paso A: desplazamiento del bloque
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

        # Paso B: redistribución uniforme si el bloque es mayor que el rango
        _top    = series_info[0]["label_y"]  + label_h / 2 + _m
        _bottom = series_info[-1]["label_y"] - label_h / 2 - _m
        if _top > y_hi or _bottom < y_lo:
            _n     = len(series_info)
            _avail = (y_hi - y_lo) - 2 * _m
            if _n == 1:
                series_info[0]["label_y"] = (y_hi + y_lo) / 2.0
            else:
                # Distribuir centros equiespaciados de arriba a abajo
                _step       = _avail / (_n - 1)
                _top_center = y_hi - _m - label_h / 2
                for _idx, _si in enumerate(series_info):
                    _si["label_y"] = _top_center - _step * _idx

    # ── Fase 3 — Connect: conector degradado + etiqueta exterior ─────────────
    if label_mode != "ninguno":
        for info in series_info:
            # — Texto de la etiqueta según label_mode —
            nom_text = info["sensor"]
            val_text = f"{info['last_y']:,.{y_dec}f}"
            if label_mode == "nombre":
                label_text = nom_text
            elif label_mode == "valor":
                label_text = f"<b>{val_text}</b>"
            else:  # "ambos"
                label_text = f"{nom_text} | <b>{val_text}</b>"

            # — Conector degradado mediante scatter multi-punto —
            # Se generan N_STEPS puntos interpolando desde el último dato (transparente)
            # hasta la posición de la etiqueta (opaco). Se usa como trace sin hover.
            N_STEPS = 12
            color_hex = info["color"]

            # Parsear hex → RGB
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
                alpha = t          # 0 = transparente en el punto, 1 = opaco en la etiqueta
                ts_k  = lx_start + pd.Timedelta(seconds=total_s * t)
                y_k   = ly_start + (ly_end - ly_start) * t
                conn_x.append(ts_k)
                conn_y.append(y_k)
                conn_colors.append(f"rgba({r_c},{g_c},{b_c},{alpha:.3f})")

            # Traza el conector como puntos coloreados con markers diminutos
            # unidos por líneas del mismo color (trick: cada segmento es una traza)
            fig.add_trace(go.Scatter(
                x=conn_x,
                y=conn_y,
                mode="markers",
                showlegend=False,
                hoverinfo="skip",
                marker=dict(
                    color=conn_colors,
                    size=1,               # coherente con conector más fino
                    symbol="circle",
                    line=dict(width=0),
                ),
            ))

            # Línea sólida del conector (cubre los gaps entre puntos)
            # Se dibuja con opacidad global moderada y sin interferir con datos
            fig.add_trace(go.Scatter(
                x=[lx_start, lx_end],
                y=[ly_start, ly_end],
                mode="lines",
                showlegend=False,
                hoverinfo="skip",
                line=dict(
                    color=f"rgba({r_c},{g_c},{b_c},0.25)",
                    width=0.2,            # 30 % de 0.6 → conector más fino
                    dash="dot",
                ),
            ))

            # — Marcador en el último punto de la serie —
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

            # — Anotación de etiqueta a la derecha del área de datos —
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
                xanchor="left",           # texto a la derecha del conector
                yanchor="middle",
                font=dict(size=label_size, color=info["color"], family=_FONT_FAMILY),
                bgcolor=_bgcol,
                bordercolor=_border,
                borderwidth=1 if show_lbl_box else 0,
                borderpad=3,
                align="left",
            )

    # ── Layout: estilo informe L9 v1 ─────────────────────────────────────────
    # Margen derecho mínimo: las etiquetas están dentro del dominio x extendido.
    # ── Leyenda: posición configurable ──────────────────────────────────────
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

    return pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=False,
        config={"staticPlot": False, "responsive": True, "displayModeBar": False},
    )


# ── Bandas de umbral ───────────────────────────────────────────────────────────

def _draw_threshold_bands(
    fig: "go.Figure",
    u_estable: float | None,
    u_atencion: float | None,
    u_alerta: float | None,
    y_lo: float,
    y_hi: float,
) -> None:
    """Dibuja bandas de umbral horizontales con opacidad 10 % (L9-Standard §Umbrales).

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
            line_color="#10B981", opacity=0.55, layer="below",
        )

    if u_atencion is not None and u_alerta is not None:
        fig.add_hrect(
            y0=u_atencion, y1=u_alerta,
            fillcolor="#F59E0B", opacity=0.10, line_width=0, layer="below",
        )
        fig.add_hline(
            y=u_atencion, line_width=0.7, line_dash="dot",
            line_color="#F59E0B", opacity=0.55, layer="below",
        )
    elif u_atencion is not None:
        fig.add_hrect(
            y0=u_atencion, y1=y_hi,
            fillcolor="#F59E0B", opacity=0.10, line_width=0, layer="below",
        )
        fig.add_hline(
            y=u_atencion, line_width=0.7, line_dash="dot",
            line_color="#F59E0B", opacity=0.55, layer="below",
        )

    if u_alerta is not None:
        fig.add_hrect(
            y0=u_alerta, y1=y_hi,
            fillcolor="#EF4444", opacity=0.10, line_width=0, layer="below",
        )
        fig.add_hline(
            y=u_alerta, line_width=0.7, line_dash="dot",
            line_color="#EF4444", opacity=0.55, layer="below",
        )

"""Gráfico de evolución temporal Spline L9 — motor HTML/Plotly.

Replica la arquitectura de temporal_1eje_draft_00.py (Matplotlib) adaptada para
Plotly: suavizado spline, etiquetado directo externo sin leyenda, algoritmo
anti-colisión greedy en coordenadas de datos y leader lines con shapes.

Función principal: ``generate(params, figsize) -> str``

Arquitectura de 3 fases (equivalente Plotly de CLAUDE.md §3.2):
  Fase 1 — Position: trazar series, recopilar último punto por serie.
  Fase 2 — Stack: anti-colisión greedy en coordenadas de datos.
  Fase 3 — Connect: shapes (leader lines) + annotations (etiquetas externas).

Parámetros configurables
------------------------
sensor          : str   — nombre de sensor ($CURRENT = sensor activo en Dispatch Table)
fecha_inicio    : str   — fecha inicio ISO 8601 ($CURRENT_fecha_inicial)
fecha_fin       : str   — fecha fin   ISO 8601 ($CURRENT_fecha_final)
show_markers    : bool  — True = mode='lines+markers', False = mode='lines'
palette         : str   — 'modern' | 'corporate' | 'vibrant'
y_min, y_max    : float — límites eje Y; None = autoescala ±10 %
y_decimals      : int   — decimales en etiquetas de series y eje Y
x_date_format   : str   — strftime/d3 para eje X (ej. "%d/%m/%y")
label_size      : int   — tamaño de fuente de etiquetas de serie (pt)
y_axis_title    : str   — título eje Y
x_axis_title    : str   — título eje X
umbral_estable_max : float — límite superior zona estable (verde, desde y_lo)
umbral_atencion    : float — inicio zona atención (naranja)
umbral_alerta      : float — inicio zona alerta (rojo)
data            : dict  — payload con clave 'historico' (inyectado por el motor)
"""

from __future__ import annotations

from typing import Any

from utils.script_registry import ParameterMetadata, ScriptMetadata, register_script

# ── Registro de metadatos ──────────────────────────────────────────────────────

metadata = ScriptMetadata(
    nombre="grafico_spline_l9",
    tipo="grafico",
    descripcion="Evolución temporal spline con etiquetas externas, anti-colisión y umbrales L9",
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
            descripcion="Decimales en etiquetas de series y tick labels eje Y.",
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
            default=11,
            descripcion="Tamaño de fuente de las etiquetas de serie (pt).",
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
            descripcion="Límite superior zona estable (verde). Desde y_lo hasta este valor.",
        ),
        ParameterMetadata(
            nombre="umbral_atencion",
            tipo="numero",
            requerido=False,
            default=None,
            descripcion="Inicio zona de atención (naranja).",
        ),
        ParameterMetadata(
            nombre="umbral_alerta",
            tipo="numero",
            requerido=False,
            default=None,
            descripcion="Inicio zona de alerta (rojo).",
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
            default=True,
            descripcion="True = recuadro blanco con borde en la etiqueta; False = texto flotante sin marco.",
        ),
        ParameterMetadata(
            nombre="show_vgrid",
            tipo="bool",
            requerido=False,
            default=True,
            descripcion="True = muestra rejilla vertical en el eje X.",
        ),
    ],
)

# ── PARAMETER_METADATA (ScriptRegistry) ────────────────────────────────────────
# El registro singleton lee esta lista para exponer los parámetros al Editor Visual.

PARAMETER_METADATA: list[dict] = [
    {
        "nombre": "sensor",
        "tipo": "texto",
        "requerido": False,
        "default": "$CURRENT",
        "descripcion": "Nombre del sensor a mostrar. '$CURRENT' usa el sensor activo.",
    },
    {
        "nombre": "fecha_inicio",
        "tipo": "fecha",
        "requerido": False,
        "default": "$CURRENT_fecha_inicial",
        "descripcion": "Fecha inicio del período (ISO 8601).",
    },
    {
        "nombre": "fecha_fin",
        "tipo": "fecha",
        "requerido": False,
        "default": "$CURRENT_fecha_final",
        "descripcion": "Fecha fin del período (ISO 8601).",
    },
    {
        "nombre": "show_markers",
        "tipo": "bool",
        "requerido": False,
        "default": False,
        "descripcion": "True = añade puntos en cada lectura (lines+markers).",
    },
    {
        "nombre": "palette",
        "tipo": "lista",
        "requerido": False,
        "default": "modern",
        "opciones": ["modern", "corporate", "vibrant"],
        "descripcion": "Paleta: modern (dashboard Plotly) | corporate (azules oscuros) | vibrant (alta distinción).",
    },
    {
        "nombre": "y_min",
        "tipo": "numero",
        "requerido": False,
        "default": None,
        "descripcion": "Límite inferior eje Y. Vacío = autoescala ±10 %.",
    },
    {
        "nombre": "y_max",
        "tipo": "numero",
        "requerido": False,
        "default": None,
        "descripcion": "Límite superior eje Y. Vacío = autoescala ±10 %.",
    },
    {
        "nombre": "y_decimals",
        "tipo": "numero",
        "requerido": False,
        "default": 2,
        "descripcion": "Decimales en etiquetas de series y eje Y.",
    },
    {
        "nombre": "x_date_format",
        "tipo": "texto",
        "requerido": False,
        "default": "%d/%m/%y",
        "descripcion": "Formato de fecha para el eje X (ej. '%d/%m/%y', '%d/%m/%y %H:%M').",
    },
    {
        "nombre": "label_size",
        "tipo": "numero",
        "requerido": False,
        "default": 11,
        "descripcion": "Tamaño de fuente de las etiquetas de serie (pt).",
    },
    {
        "nombre": "y_axis_title",
        "tipo": "texto",
        "requerido": False,
        "default": "",
        "descripcion": "Título del eje Y.",
    },
    {
        "nombre": "x_axis_title",
        "tipo": "texto",
        "requerido": False,
        "default": "",
        "descripcion": "Título del eje X.",
    },
    {
        "nombre": "umbral_estable_max",
        "tipo": "numero",
        "requerido": False,
        "default": None,
        "descripcion": "Límite superior zona estable (verde, 10 % opacidad).",
    },
    {
        "nombre": "umbral_atencion",
        "tipo": "numero",
        "requerido": False,
        "default": None,
        "descripcion": "Inicio zona de atención (naranja, 10 % opacidad).",
    },
    {
        "nombre": "umbral_alerta",
        "tipo": "numero",
        "requerido": False,
        "default": None,
        "descripcion": "Inicio zona de alerta (rojo, 10 % opacidad).",
    },
    {
        "nombre": "line_width",
        "tipo": "numero",
        "requerido": False,
        "default": 2,
        "descripcion": "Grosor de las líneas de las series (px).",
    },
    {
        "nombre": "smoothing",
        "tipo": "bool",
        "requerido": False,
        "default": False,
        "descripcion": "True = suavizado spline; False = líneas rectas.",
    },
    {
        "nombre": "show_label_box",
        "tipo": "bool",
        "requerido": False,
        "default": True,
        "descripcion": "True = recuadro con borde en la etiqueta; False = texto flotante sin marco.",
    },
    {
        "nombre": "show_vgrid",
        "tipo": "bool",
        "requerido": False,
        "default": True,
        "descripcion": "True = muestra rejilla vertical en el eje X.",
    },
]

# ── Custom Options Schema (Dispatch Table wizard) ──────────────────────────────
# Formato consumido por _build_custom_controls() en pages/dispatch_table.py.
# Parámetros estándar (sensor, fecha_inicio, fecha_fin, data) se omiten aquí.

_CUSTOM_OPTIONS_SCHEMA: list[dict] = [
    {
        "id": "show_markers",
        "label": "Mostrar marcadores",
        "tipo": "switch",
        "default": False,
        "descripcion": "Activa puntos individuales sobre la línea spline.",
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
        "descripcion": "Esquema de colores de las series.",
    },
    {
        "id": "y_min",
        "label": "Y mínimo",
        "tipo": "number",
        "default": None,
        "descripcion": "Límite inferior del eje Y. Vacío = autoescala.",
    },
    {
        "id": "y_max",
        "label": "Y máximo",
        "tipo": "number",
        "default": None,
        "descripcion": "Límite superior del eje Y. Vacío = autoescala.",
    },
    {
        "id": "y_decimals",
        "label": "Decimales eje Y",
        "tipo": "number",
        "default": 2,
        "descripcion": "Número de decimales en etiquetas de series y tick labels.",
    },
    {
        "id": "x_date_format",
        "label": "Formato fecha eje X",
        "tipo": "text",
        "default": "%d/%m/%y",
        "descripcion": "Formato d3/strftime para el eje X (ej. '%d/%m/%y %H:%M').",
    },
    {
        "id": "label_size",
        "label": "Tamaño etiquetas (pt)",
        "tipo": "number",
        "default": 11,
        "descripcion": "Tamaño de fuente de las etiquetas de serie externas.",
    },
    {
        "id": "y_axis_title",
        "label": "Título eje Y",
        "tipo": "text",
        "default": "",
        "descripcion": "Texto del título del eje Y. Vacío = sin título.",
    },
    {
        "id": "x_axis_title",
        "label": "Título eje X",
        "tipo": "text",
        "default": "",
        "descripcion": "Texto del título del eje X. Vacío = sin título.",
    },
    {
        "id": "umbral_estable_max",
        "label": "Umbral estable (verde)",
        "tipo": "number",
        "default": None,
        "descripcion": "Límite superior zona estable (verde, 10 % opacidad).",
    },
    {
        "id": "umbral_atencion",
        "label": "Umbral atención (naranja)",
        "tipo": "number",
        "default": None,
        "descripcion": "Inicio zona de atención (naranja, 10 % opacidad).",
    },
    {
        "id": "umbral_alerta",
        "label": "Umbral alerta (rojo)",
        "tipo": "number",
        "default": None,
        "descripcion": "Inicio zona de alerta (rojo, 10 % opacidad).",
    },
    {
        "id": "line_width",
        "label": "Grosor de línea (px)",
        "tipo": "number",
        "default": 2,
        "descripcion": "Ancho de trazo de cada serie.",
    },
    {
        "id": "smoothing",
        "label": "Suavizado spline",
        "tipo": "switch",
        "default": False,
        "descripcion": "Activa el suavizado spline de las líneas (líneas rectas por defecto).",
    },
    {
        "id": "show_label_box",
        "label": "Marco en etiquetas",
        "tipo": "switch",
        "default": True,
        "descripcion": "Muestra el recuadro blanco con borde de color alrededor de cada etiqueta.",
    },
    {
        "id": "show_vgrid",
        "label": "Rejilla vertical",
        "tipo": "switch",
        "default": True,
        "descripcion": "Activa la rejilla vertical en el eje X.",
    },
]

# ── Paletas ────────────────────────────────────────────────────────────────────

_PALETAS: dict[str, list[str]] = {
    # Estilo dashboard Plotly: azules, grises y naranjas suaves
    "modern": [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA",
        "#FFA15A", "#19D3F3", "#FF6692", "#B6E880",
    ],
    # Tonos azul marino y gris oscuro — entorno corporativo
    "corporate": [
        "#1D4E89", "#2874A6", "#5DADE2", "#A9CCE3",
        "#1E8449", "#52BE80", "#784212", "#E59866",
    ],
    # Alta saturación — ideal cuando hay muchos sensores simultáneos
    "vibrant": [
        "#E63946", "#2A9D8F", "#E9C46A", "#F4A261",
        "#457B9D", "#8338EC", "#FB5607", "#06D6A0",
    ],
}

# ── Constantes estéticas L9-Standard ──────────────────────────────────────────

_GRID_COLOR  = "#f1f5f9"   # gris muy tenue para grid horizontal
_FONT_FAMILY = "Arial, sans-serif"

# Separación mínima entre etiquetas = 50 % de la altura estimada de etiqueta.
# 0.50 garantiza espacio en blanco visible entre cajas en gráficos SHM densos.
_LABEL_GAP_FRAC = 0.50

# Holgura derecha del eje X (fracción del rango temporal).
# Las etiquetas se anclan en xref="x" dentro del eje, necesitan espacio extra.
# 0.20 = extensión visible del eje X a la derecha del último dato.
_X_AXIS_PAD = 0.20

# Posición X de las etiquetas en coordenadas del eje (fracción del rango temporal).
# 0.13 sitúa la etiqueta dentro de la extensión del eje, dejando margen al borde.
_X_LABEL_OFFSET = 0.13


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
    """Genera el gráfico temporal Spline L9 y devuelve un fragmento HTML embebible.

    Arquitectura Position → Stack → Connect (equivalente Plotly de CLAUDE.md §3.2):

    Fase 1 — Position
        Traza cada serie con ``line_shape='spline'``. Recoge el último
        punto (last_x, last_y) y lo usa como posición Y natural de la etiqueta.

    Fase 2 — Stack
        Ordena etiquetas de mayor a menor Y. Aplica stacking greedy: si una
        etiqueta solapa a la anterior (usando ``_LABEL_HEIGHT_FRAC`` del rango Y
        como altura estimada), la desplaza hacia abajo hasta eliminar el solapamiento.

    Fase 3 — Connect
        Por cada serie añade:
        - Un ``go.layout.Shape`` (línea discontinua) desde (last_x, last_y)
          hasta (x_label_pos, label_y) — coordenadas de datos (xref='x', yref='y').
        - Una ``go.layout.Annotation`` en (x_label_pos, label_y) con el texto
          «<b>Nombre</b> valor» y caja blanca bordeada.

    El eje X se extiende un ``_X_AXIS_EXTRA`` fracción del rango temporal para
    alojar las etiquetas sin solapar los datos.

    Args:
        params:  Dict de parámetros resueltos (ver PARAMETER_METADATA).
        figsize: (ancho_cm, alto_cm) del contenedor destino, en pulgadas desde el motor.

    Returns:
        Fragmento HTML con Plotly.js (CDN) embebido. Sin ``<html>``/``<body>``.
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
    # Normalizar el campo sensor: elimina saltos de línea y espacios extra,
    # luego convierte en lista para soportar múltiples sensores separados por coma.
    _val = params.get("sensor")
    sensor = str(_val).strip() if _val else ""
    fecha_ini    = params.get("fecha_inicio")
    fecha_fin    = params.get("fecha_fin")
    show_markers = _safe_bool(params.get("show_markers"), False)
    palette_key  = str(params.get("palette") or "modern").lower()
    colores      = _PALETAS.get(palette_key, _PALETAS["modern"])
    y_min        = _safe_float(params.get("y_min"))
    y_max        = _safe_float(params.get("y_max"))
    # Usar is not None en lugar de `or default` para que 0 sea un valor válido.
    _val_dec     = _safe_float(params.get("y_decimals"))
    y_dec        = int(_val_dec if _val_dec is not None else 2)
    x_fmt        = str(params.get("x_date_format") or "%d/%m/%y")
    _val_ls      = _safe_float(params.get("label_size"))
    label_size   = int(_val_ls if _val_ls is not None else 11)
    y_title      = str(params.get("y_axis_title") or "")
    x_title      = str(params.get("x_axis_title") or "")
    u_estable    = _safe_float(params.get("umbral_estable_max"))
    u_atencion   = _safe_float(params.get("umbral_atencion"))
    u_alerta     = _safe_float(params.get("umbral_alerta"))
    _val_lw       = _safe_float(params.get("line_width"))
    line_width    = int(_val_lw if _val_lw is not None else 2)
    smoothing     = _safe_bool(params.get("smoothing"), False)
    show_lbl_box  = _safe_bool(params.get("show_label_box"), True)
    show_vgrid    = _safe_bool(params.get("show_vgrid"), True)

    # 95 % del tamaño nominal: margen de seguridad para evitar desbordamiento por
    # diferencias de conversión px/cm entre el lienzo HTML y el motor de renderizado.
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

    # Filtrar por sensor(es) — soporta lista separada por comas.
    # Vacío o solo comas → no filtra (pinta todos los sensores del historico).
    if sensor:
        sensores_lista = [s.strip() for s in sensor.split(",") if s.strip()]
        if sensores_lista:
            df = df[df["NOM_SENSOR"].str.strip().isin(sensores_lista)]
            if df.empty:
                return _html_error(
                    f"Sin datos para sensor(es): {', '.join(sensores_lista)}"
                )

    # Filtrar por rango de fechas
    if fecha_ini:
        try:
            df = df[df["FECHA_MEDIDA"] >= pd.to_datetime(fecha_ini)]
        except Exception:
            pass
    if fecha_fin:
        try:
            df = df[df["FECHA_MEDIDA"] <= pd.to_datetime(fecha_fin)]
        except Exception:
            pass

    if df.empty:
        return _html_error("Sin datos en el rango de fechas seleccionado")

    # ── Rangos ────────────────────────────────────────────────────────────────
    x_min_data = df["FECHA_MEDIDA"].min()
    x_max_data = df["FECHA_MEDIDA"].max()
    range_secs = max((x_max_data - x_min_data).total_seconds(), 3600.0)

    # Rango del eje X: holgura derecha ampliada para alojar etiquetas dentro del eje.
    # Las etiquetas usan xref="x" ancladas en x_label_pos, dentro del área visible.
    x_axis_right = x_max_data + pd.Timedelta(seconds=range_secs * _X_AXIS_PAD)
    x_label_pos  = x_max_data + pd.Timedelta(seconds=range_secs * _X_LABEL_OFFSET)
    x_axis_left  = x_min_data - pd.Timedelta(seconds=range_secs * 0.02)

    # Rango Y: autoescala ±10 % o valores explícitos
    y_vals  = df["MEDIDA"].dropna()
    d_min   = float(y_vals.min()) if len(y_vals) else 0.0
    d_max   = float(y_vals.max()) if len(y_vals) else 1.0
    d_range = max(d_max - d_min, 1.0)
    pad     = max(d_range * 0.10, 0.1)
    y_lo    = y_min if y_min is not None else d_min - pad
    y_hi    = y_max if y_max is not None else d_max + pad

    # Altura estimada de etiqueta en coordenadas de datos.
    # Escala con label_size y height_px (no renderer disponible en server-side).
    # Factor 2.2 = texto + padding Plotly (borderpad=4 × 2) + borde.
    label_h   = (y_hi - y_lo) * (label_size / height_px) * 2.2
    label_gap = label_h * _LABEL_GAP_FRAC

    # ── Fase 1 — Position: trazar series y recopilar último punto ─────────────
    fig = go.Figure()

    # Bandas de umbral (debajo de las series, opacity 10 %)
    _draw_threshold_bands(fig, u_estable, u_atencion, u_alerta, y_lo, y_hi)

    mode        = "lines+markers" if show_markers else "lines"
    line_shape  = "spline" if smoothing else "linear"
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
            showlegend=False,
            line=dict(color=color, width=line_width, shape=line_shape, smoothing=1.3 if smoothing else 0),
            marker=dict(size=5, color=color, line=dict(width=0)) if show_markers else {},
            hovertemplate=f"<b>{nom}</b><br>%{{x|{x_fmt}}}<br>%{{y:.{y_dec}f}}<extra></extra>",
        ))
        series_info.append({
            "sensor":  str(nom),
            "last_x":  sub["FECHA_MEDIDA"].iloc[-1],
            "last_y":  float(sub["MEDIDA"].iloc[-1]),
            "label_y": float(sub["MEDIDA"].iloc[-1]),  # se ajusta en Fase 2
            "color":   color,
        })

    if not series_info:
        return _html_error("Sin series con datos válidos")

    # ── Fase 2 — Stack: resolver colisiones verticales (greedy, top-down) ─────
    # Equivalente Plotly de CLAUDE.md §12.1.
    # label_h escala con label_size/height_px (heurístico, no hay renderer síncrono).
    series_info.sort(key=lambda e: e["last_y"], reverse=True)
    for j in range(1, len(series_info)):
        prev_bottom = series_info[j - 1]["label_y"] - label_h / 2 - label_gap
        if series_info[j]["label_y"] + label_h / 2 > prev_bottom:
            series_info[j]["label_y"] = prev_bottom - label_h / 2

    # ── Fase 3 — Connect: marcador final + leader lines + anotaciones DENTRO del eje ──
    # Las etiquetas usan xref="x" ancladas en x_label_pos (dentro del eje visible).
    # Formato: «<b>Nombre</b> | 1,234.56»  — barra vertical como separador visual.
    for info in series_info:
        label_val  = f"{info['last_y']:,.2f}"
        label_text = f"<b>{info['sensor']}</b> | {label_val}"

        # Marcador en el último punto (punto de color sobre la línea).
        fig.add_trace(go.Scatter(
            x=[info["last_x"]],
            y=[info["last_y"]],
            mode="markers",
            marker=dict(color=info["color"], size=7, line=dict(width=0)),
            showlegend=False,
            hoverinfo="skip",
        ))

        # Leader line sutil: del último punto de datos a la posición de la etiqueta.
        fig.add_shape(
            type="line",
            x0=_ts_iso(info["last_x"]),
            y0=info["last_y"],
            x1=_ts_iso(x_label_pos),
            y1=info["label_y"],
            xref="x",
            yref="y",
            line=dict(color=info["color"], width=0.5, dash="solid"),
            layer="above",
        )

        # Etiqueta anclada en coordenadas de datos (xref="x") dentro del eje extendido.
        # bgcolor semitransparente y sin borde duro → estética hiper-minimalista.
        _border  = info["color"]              if show_lbl_box else "rgba(0,0,0,0)"
        _bgcolor = "rgba(255,255,255,0.80)"   if show_lbl_box else "rgba(0,0,0,0)"
        fig.add_annotation(
            x=_ts_iso(x_label_pos),
            y=info["label_y"],
            xref="x",
            yref="y",
            text=label_text,
            showarrow=False,
            xanchor="left",
            yanchor="middle",
            font=dict(size=label_size, color=info["color"], family=_FONT_FAMILY),
            bgcolor=_bgcolor,
            bordercolor=_border,
            borderwidth=1,
            borderpad=4,
            align="left",
        )

    # ── Layout: estética L9-Premium ──────────────────────────────────────────
    fig.update_layout(
        showlegend=False,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family=_FONT_FAMILY, size=9),
        # r=40: etiquetas ya no necesitan margen extra (están dentro del eje xref="x").
        margin=dict(l=40, r=40, t=10, b=30),
        width=width_px,
        height=height_px,
        xaxis=dict(
            showgrid=False,                          # sin rejilla vertical
            gridcolor=_GRID_COLOR,
            gridwidth=0.5,
            griddash="solid",
            linecolor="#D1D5DB",
            linewidth=1,
            showline=False,                          # sin borde exterior de recuadro
            mirror=False,
            tickfont=dict(size=8, family=_FONT_FAMILY),
            tickformat=x_fmt,
            range=[_ts_iso(x_axis_left), _ts_iso(x_axis_right)],
            title=dict(text=x_title, font=dict(size=9, family=_FONT_FAMILY), standoff=8),
            ticks="outside",
            ticklen=3,
            tickcolor="#D1D5DB",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=_GRID_COLOR,                   # "#f1f5f9" — rejilla horizontal sutil
            gridwidth=0.5,
            griddash="solid",
            linecolor="#D1D5DB",
            linewidth=1,
            showline=False,                          # sin borde exterior de recuadro
            mirror=False,
            zeroline=True,
            zerolinecolor="#cbd5e1",
            tickfont=dict(size=8, family=_FONT_FAMILY),
            tickformat=f".{y_dec}f",
            range=[y_lo, y_hi],
            title=dict(
                text=y_title,
                font=dict(size=10, color="#94a3b8", family=_FONT_FAMILY),
                standoff=4,
            ),
            ticks="outside",
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

    Añade además una línea discontinua fina en el límite de cada zona.

    Args:
        fig:        Figura Plotly sobre la que dibujar.
        u_estable:  Límite superior zona estable (None = no dibujar).
        u_atencion: Inicio zona atención (None = no dibujar).
        u_alerta:   Inicio zona alerta (None = no dibujar).
        y_lo:       Límite inferior del eje Y.
        y_hi:       Límite superior del eje Y.
    """
    # Zona estable: verde #10B981 — desde y_lo hasta u_estable
    if u_estable is not None:
        fig.add_hrect(
            y0=y_lo, y1=u_estable,
            fillcolor="#10B981", opacity=0.10, line_width=0, layer="below",
        )
        fig.add_hline(
            y=u_estable, line_width=0.7, line_dash="dot",
            line_color="#10B981", opacity=0.55, layer="below",
        )

    # Zona atención: naranja #F59E0B — desde u_atencion hasta u_alerta
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
        # u_alerta no definido: banda va desde u_atencion hasta y_hi
        fig.add_hrect(
            y0=u_atencion, y1=y_hi,
            fillcolor="#F59E0B", opacity=0.10, line_width=0, layer="below",
        )
        fig.add_hline(
            y=u_atencion, line_width=0.7, line_dash="dot",
            line_color="#F59E0B", opacity=0.55, layer="below",
        )

    # Zona alerta: rojo #EF4444 — desde u_alerta hasta y_hi
    if u_alerta is not None:
        fig.add_hrect(
            y0=u_alerta, y1=y_hi,
            fillcolor="#EF4444", opacity=0.10, line_width=0, layer="below",
        )
        fig.add_hline(
            y=u_alerta, line_width=0.7, line_dash="dot",
            line_color="#EF4444", opacity=0.55, layer="below",
        )

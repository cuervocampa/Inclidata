"""Leyenda de campañas inclinométricas — motor HTML puro.

Genera un bloque HTML/CSS con la leyenda de fechas y colores de los perfiles
inclinométricos. Diseñado como elemento visual independiente para plantillas
donde los gráficos de eje A y eje B se renderizan sin leyenda propia.

Para que los colores coincidan con los perfiles, usa los mismos parámetros de
selección de campañas (``total_camp``, ``ultimas_camp``, ``cadencia_dias``,
``color_scheme``) que en ``grafico_inclinometro_v1.py`` del mismo informe.

El renderizado es HTML/CSS puro (sin Plotly): rectángulos de color + etiquetas
de fecha en un contenedor flexbox. Esto produce un fragmento ligero y con
renderizado fiel en PDF (sin dependencias JS).

Función principal: ``generate(params, figsize) -> str``

Parámetros configurables
------------------------
sensor          : str   — nombre del archivo JSON en json_inclis/ (= sensor primario)
total_camp      : int   — total máximo de campañas a mostrar
ultimas_camp    : int   — campañas recientes consecutivas
cadencia_dias   : int   — salto en días para campañas históricas
fecha_inicio    : str   — ISO fecha de inicio del filtro
fecha_fin       : str   — ISO fecha de fin del filtro
color_scheme    : str   — "Viridis" | "Plasma" | "Azules" | "Rojos"
mostrar_umbrales: bool  — añade entradas de umbral al final
orientacion     : str   — "vertical" (columna) | "horizontal" (fila)
titulo          : str   — título de la leyenda; vacío = sin título
font_size       : int   — tamaño de fuente de etiquetas en puntos
"""

from __future__ import annotations

import html as _html_mod
import json
import pathlib
from datetime import datetime
from typing import Any

from utils.script_registry import ParameterMetadata, ScriptMetadata, register_script

# ── Metadata ──────────────────────────────────────────────────────────────────

metadata = ScriptMetadata(
    nombre="grafico_escala_inclis",
    tipo="grafico",
    descripcion="Leyenda de campañas inclinométricas (colores + fechas)",
    parametros=[
        ParameterMetadata(
            nombre="sensor", tipo="texto", requerido=False, default="$CURRENT",
            descripcion="Nombre del sensor (= nombre de archivo JSON en json_inclis/).",
        ),
        ParameterMetadata(
            nombre="total_camp", tipo="numero", requerido=False, default=10,
            descripcion="Total máximo de campañas a mostrar.",
        ),
        ParameterMetadata(
            nombre="ultimas_camp", tipo="numero", requerido=False, default=3,
            descripcion="Campañas recientes consecutivas.",
        ),
        ParameterMetadata(
            nombre="cadencia_dias", tipo="numero", requerido=False, default=15,
            descripcion="Salto en días para campañas históricas.",
        ),
        ParameterMetadata(
            nombre="fecha_inicio", tipo="texto", requerido=False, default="$CURRENT_fecha_inicial",
            descripcion="Fecha de inicio del filtro (ISO).",
        ),
        ParameterMetadata(
            nombre="fecha_fin", tipo="texto", requerido=False, default="$CURRENT_fecha_final",
            descripcion="Fecha de fin del filtro (ISO).",
        ),
        ParameterMetadata(
            nombre="color_scheme", tipo="lista", requerido=False, default="Viridis",
            opciones=["Viridis", "Plasma", "Azules", "Rojos"],
            descripcion="Rampa de color (debe coincidir con el gráfico de perfiles).",
        ),
        ParameterMetadata(
            nombre="mostrar_umbrales", tipo="bool", requerido=False, default=False,
            descripcion="Añade entradas de umbral al final de la leyenda.",
        ),
        ParameterMetadata(
            nombre="orientacion", tipo="lista", requerido=False, default="vertical",
            opciones=["vertical", "horizontal"],
            descripcion="Disposición: vertical (columna) u horizontal (fila).",
        ),
        ParameterMetadata(
            nombre="titulo", tipo="texto", requerido=False, default="Leyenda",
            descripcion="Título de la leyenda. Vacío = sin título.",
        ),
        ParameterMetadata(
            nombre="font_size", tipo="numero", requerido=False, default=8,
            descripcion="Tamaño de fuente de las etiquetas en puntos.",
        ),
        ParameterMetadata(
            nombre="pin_actual", tipo="bool", requerido=False, default=True,
            descripcion="Destaca la campaña actual en una caja al inicio (sólo orientación vertical).",
        ),
        ParameterMetadata(
            nombre="etiqueta_actual", tipo="texto", requerido=False, default="Actual",
            descripcion="Rótulo del pin de la campaña actual.",
        ),
        ParameterMetadata(
            nombre="color_actual", tipo="texto", requerido=False, default="",
            descripcion="Color hex del pin actual. Vacío = último color de la rampa (coherente con el gráfico).",
        ),
        ParameterMetadata(
            nombre="etiqueta_historico", tipo="texto", requerido=False, default="Histórico",
            descripcion="Subtítulo del bloque de campañas históricas. Vacío = sin subtítulo.",
        ),
        ParameterMetadata(
            nombre="bg_pin", tipo="texto", requerido=False, default="#EFF6FF",
            descripcion="Color de fondo de la caja del pin actual (hex).",
        ),
        ParameterMetadata(
            nombre="eje", tipo="lista", requerido=False, default="todos",
            opciones=["todos", "a", "b"],
            descripcion="Filtra umbrales por eje del inclinómetro. 'todos' = sin filtrar.",
        ),
    ],
)

PARAMETER_METADATA: list[dict] = [
    {
        "nombre": "sensor", "tipo": "texto", "requerido": False, "default": "$CURRENT",
        "descripcion": "Nombre del sensor (= nombre de archivo JSON en json_inclis/).",
    },
    {
        "nombre": "total_camp", "tipo": "numero", "requerido": False, "default": 10,
        "descripcion": "Total máximo de campañas a mostrar.",
    },
    {
        "nombre": "ultimas_camp", "tipo": "numero", "requerido": False, "default": 3,
        "descripcion": "Campañas recientes consecutivas.",
    },
    {
        "nombre": "cadencia_dias", "tipo": "numero", "requerido": False, "default": 15,
        "descripcion": "Salto en días para campañas históricas.",
    },
    {
        "nombre": "fecha_inicio", "tipo": "texto", "requerido": False,
        "default": "$CURRENT_fecha_inicial",
        "descripcion": "Fecha de inicio del filtro (ISO).",
    },
    {
        "nombre": "fecha_fin", "tipo": "texto", "requerido": False,
        "default": "$CURRENT_fecha_final",
        "descripcion": "Fecha de fin del filtro (ISO).",
    },
    {
        "nombre": "color_scheme", "tipo": "lista", "requerido": False, "default": "Viridis",
        "opciones": ["Viridis", "Plasma", "Azules", "Rojos"],
        "descripcion": "Rampa de color (debe coincidir con el gráfico de perfiles).",
    },
    {
        "nombre": "mostrar_umbrales", "tipo": "bool", "requerido": False, "default": False,
        "descripcion": "Añade entradas de umbral al final de la leyenda.",
    },
    {
        "nombre": "orientacion", "tipo": "lista", "requerido": False, "default": "vertical",
        "opciones": ["vertical", "horizontal"],
        "descripcion": "Disposición: vertical (columna) u horizontal (fila).",
    },
    {
        "nombre": "titulo", "tipo": "texto", "requerido": False, "default": "Leyenda",
        "descripcion": "Título de la leyenda. Vacío = sin título.",
    },
    {
        "nombre": "font_size", "tipo": "numero", "requerido": False, "default": 8,
        "descripcion": "Tamaño de fuente de las etiquetas en puntos.",
    },
    {
        "nombre": "pin_actual", "tipo": "bool", "requerido": False, "default": True,
        "descripcion": "Destaca la campaña actual en una caja al inicio (sólo orientación vertical).",
    },
    {
        "nombre": "etiqueta_actual", "tipo": "texto", "requerido": False, "default": "Actual",
        "descripcion": "Rótulo del pin de la campaña actual.",
    },
    {
        "nombre": "color_actual", "tipo": "texto", "requerido": False, "default": "",
        "descripcion": "Color hex del pin actual. Vacío = último color de la rampa (coherente con el gráfico).",
    },
    {
        "nombre": "etiqueta_historico", "tipo": "texto", "requerido": False, "default": "Histórico",
        "descripcion": "Subtítulo del bloque de campañas históricas. Vacío = sin subtítulo.",
    },
    {
        "nombre": "bg_pin", "tipo": "texto", "requerido": False, "default": "#EFF6FF",
        "descripcion": "Color de fondo de la caja del pin actual (hex).",
    },
    {
        "nombre": "eje", "tipo": "lista", "requerido": False, "default": "todos",
        "opciones": ["todos", "a", "b"],
        "descripcion": "Filtra umbrales por eje del inclinómetro. 'todos' = sin filtrar.",
    },
]

# ── Schema de controles UI (consumido por dispatch_table._build_custom_controls) ─

_CUSTOM_OPTIONS_SCHEMA: list[dict] = [
    {
        "id": "total_camp",
        "label": "Total campañas",
        "tipo": "number",
        "default": 10,
        "descripcion": {
            "es": "Número máximo de campañas a representar en la leyenda.",
            "en": "Maximum number of campaigns to display in the legend.",
        },
    },
    {
        "id": "ultimas_camp",
        "label": "Campañas recientes",
        "tipo": "number",
        "default": 3,
        "descripcion": {
            "es": "Campañas más recientes consecutivas.",
            "en": "Most recent consecutive campaigns.",
        },
    },
    {
        "id": "cadencia_dias",
        "label": "Cadencia (días)",
        "tipo": "number",
        "default": 15,
        "descripcion": {
            "es": "Separación mínima en días entre campañas históricas.",
            "en": "Minimum day gap between historical campaigns.",
        },
    },
    {
        "id": "color_scheme",
        "label": "Esquema de color",
        "tipo": "select",
        "default": "Viridis",
        "opciones": [
            {"value": "Viridis", "label": "Viridis"},
            {"value": "Plasma",  "label": "Plasma"},
            {"value": "Azules",  "label": "Azules"},
            {"value": "Rojos",   "label": "Rojos"},
        ],
        "descripcion": {
            "es": "Rampa de color. Debe coincidir con la del gráfico de perfiles.",
            "en": "Color ramp. Must match the profile chart's color scheme.",
        },
    },
    {
        "id": "mostrar_umbrales",
        "label": "Mostrar umbrales",
        "tipo": "switch",
        "default": False,
        "descripcion": {
            "es": "Añade entradas de umbral con línea discontinua roja.",
            "en": "Adds threshold entries with a dashed red line.",
        },
    },
    {
        "id": "orientacion",
        "label": "Orientación",
        "tipo": "select",
        "default": "vertical",
        "opciones": [
            {"value": "vertical",   "label": "Vertical"},
            {"value": "horizontal", "label": "Horizontal"},
        ],
        "descripcion": {
            "es": "vertical: entradas apiladas en columna. horizontal: entradas en fila.",
            "en": "vertical: entries stacked in column. horizontal: entries in a row.",
        },
    },
    {
        "id": "titulo",
        "label": "Título",
        "tipo": "text",
        "default": "Leyenda",
        "descripcion": {
            "es": "Texto del título sobre las entradas. Vacío = sin título.",
            "en": "Title text above the entries. Empty = no title.",
        },
    },
    {
        "id": "font_size",
        "label": "Tamaño fuente",
        "tipo": "number",
        "default": 8,
        "descripcion": {
            "es": "Tamaño de fuente de las etiquetas en puntos.",
            "en": "Font size for labels in points.",
        },
    },
    {
        "id": "pin_actual",
        "label": "Pin campaña actual",
        "tipo": "switch",
        "default": True,
        "descripcion": {
            "es": "Destaca la campaña actual en una caja al inicio (sólo orientación vertical).",
            "en": "Highlights the current campaign in a box at the top (vertical orientation only).",
        },
    },
    {
        "id": "etiqueta_actual",
        "label": "Etiqueta pin actual",
        "tipo": "text",
        "default": "Actual",
        "descripcion": {
            "es": "Rótulo del pin de la campaña actual.",
            "en": "Label for the current campaign pin.",
        },
    },
    {
        "id": "color_actual",
        "label": "Color pin actual",
        "tipo": "text",
        "default": "",
        "descripcion": {
            "es": "Color hex del pin actual. Vacío = último color de la rampa.",
            "en": "Hex color for the current campaign pin. Empty = last color of the ramp.",
        },
    },
    {
        "id": "etiqueta_historico",
        "label": "Subtítulo histórico",
        "tipo": "text",
        "default": "Histórico",
        "descripcion": {
            "es": "Subtítulo del bloque de campañas históricas. Vacío = sin subtítulo.",
            "en": "Subtitle for the historical campaigns block. Empty = no subtitle.",
        },
    },
    {
        "id": "bg_pin",
        "label": "Fondo pin actual",
        "tipo": "text",
        "default": "#EFF6FF",
        "descripcion": {
            "es": "Color de fondo de la caja del pin actual (hex).",
            "en": "Background color of the current campaign pin box (hex).",
        },
    },
    {
        "id": "eje",
        "label": "Eje del inclinómetro",
        "tipo": "select",
        "default": "todos",
        "opciones": [
            {"value": "todos",  "label": "Sin filtrar"},
            {"value": "a", "label": "Eje A"},
            {"value": "b", "label": "Eje B"},
        ],
        "descripcion": {
            "es": "Filtra los umbrales del JSON por sufijo de eje (_a o _b). 'todos' = mostrar todos.",
            "en": "Filters JSON thresholds by axis suffix (_a or _b). 'todos' = show all.",
        },
    },
]

# ── Constantes estéticas ───────────────────────────────────────────────────────

_FONT_FAMILY    = "Arial, Helvetica, sans-serif"
_COLOR_UMBRAL   = "#EF4444"
_COLOR_TEXT     = "#374151"
_COLOR_TEXT_DIM = "#6B7280"
_EXCLUIDAS_JSON = frozenset({"info", "umbrales"})


# ── Error helper ──────────────────────────────────────────────────────────────

def _html_error(msg: str) -> str:
    """Placeholder de error estándar — fondo neutro, texto gris."""
    return (
        f'<div style="width:100%;height:100%;display:flex;align-items:center;'
        f'justify-content:center;font-family:{_FONT_FAMILY};'
        f'font-size:10pt;color:{_COLOR_TEXT_DIM};">'
        f'<span>{_html_mod.escape(msg)}</span></div>'
    )


# ── Helpers de datos (idénticos a grafico_inclinometro_v1) ────────────────────

def _parse_iso_date(s: Any) -> datetime | None:
    """Parsea una cadena ISO a datetime; retorna None si falla o es token."""
    if not s or str(s).startswith("$"):
        return None
    try:
        return datetime.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


def _select_campaigns(
    date_keys: list[str],
    total_camp: int,
    ultimas_camp: int,
    cadencia_dias: int,
    fecha_inicio: datetime | None,
    fecha_fin: datetime | None,
) -> list[str]:
    """Selecciona campañas según el algoritmo de IncliData.

    Replica exactamente la lógica de ``grafico_inclinometro_v1._select_campaigns``
    para garantizar que los colores asignados coincidan entre ambos elementos.
    """
    def _parse(k: str) -> datetime:
        try:
            return datetime.fromisoformat(k)
        except ValueError:
            return datetime.min

    filtered = [
        k for k in date_keys
        if (fecha_inicio is None or _parse(k) >= fecha_inicio)
        and (fecha_fin   is None or _parse(k) <= fecha_fin)
    ]
    if not filtered:
        return []

    sorted_newest = sorted(filtered, key=_parse, reverse=True)
    n_recientes   = min(ultimas_camp, total_camp, len(sorted_newest))
    selected      = list(sorted_newest[:n_recientes])

    if len(selected) < total_camp and len(sorted_newest) > n_recientes:
        last_dt = _parse(selected[-1])
        for key in sorted_newest[n_recientes:]:
            if len(selected) >= total_camp:
                break
            key_dt = _parse(key)
            if (last_dt - key_dt).days >= cadencia_dias:
                selected.append(key)
                last_dt = key_dt

    return sorted(selected, key=_parse)   # retorna ordenado de más antigua a más reciente


def _sample_colorscale(scheme: str, n: int) -> list[str]:
    """Extrae ``n`` colores equiespaciados de una rampa secuencial de Plotly.

    Replica exactamente la lógica de ``grafico_inclinometro_v1._sample_colorscale``.
    """
    import plotly.express as px

    _SCHEME_MAP = {
        "Viridis": "Viridis",
        "Plasma":  "Plasma",
        "Azules":  "Blues",
        "Rojos":   "Reds",
    }
    palette_name = _SCHEME_MAP.get(scheme, "Viridis")
    palette: list[str] = getattr(
        px.colors.sequential, palette_name, px.colors.sequential.Viridis
    )
    if n <= 0:
        return []

    _MONO_SCHEMES = {"Azules", "Rojos"}
    start_frac = 0.40 if scheme in _MONO_SCHEMES else 0.0

    if n == 1:
        return [palette[-1]]

    indices = [
        int(round((start_frac + (1.0 - start_frac) * i / (n - 1)) * (len(palette) - 1)))
        for i in range(n)
    ]
    return [palette[idx] for idx in indices]


def _load_data(sensor_name: str) -> dict:
    """Carga el JSON del sensor desde ``json_inclis/``."""
    json_path = pathlib.Path.cwd() / "json_inclis" / f"{sensor_name}.json"
    if not json_path.exists():
        raise FileNotFoundError(str(json_path))
    try:
        with json_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido en {json_path.name}: {exc}") from exc


# ── Renderizado HTML ──────────────────────────────────────────────────────────

def _build_legend_html(
    entries: list[dict],
    titulo: str,
    orientacion: str,
    font_size: int,
    width_px: int,
    height_px: int,
    *,
    pin_actual: bool = True,
    etiqueta_actual: str = "Actual",
    color_actual_override: str = "",
    etiqueta_historico: str = "Histórico",
    bg_pin: str = "#EFF6FF",
) -> str:
    """Construye el HTML/CSS de la leyenda. Si ``pin_actual`` y la
    orientación es vertical, separa la entrada ``is_last`` en una caja
    destacada al inicio del bloque (sin salir de la paleta azul).
    """
    title_html = ""
    if titulo and titulo.strip():
        title_html = (
            f'<div style="font-size:{font_size + 2}pt;font-weight:600;'
            f'color:{_COLOR_TEXT};text-align:center;width:100%;'
            f'padding-bottom:4px;margin-bottom:6px;'
            f'border-bottom:1px solid #E5E7EB;white-space:nowrap;'
            f'overflow:hidden;text-overflow:ellipsis;">'
            f'{_html_mod.escape(titulo.strip())}</div>'
        )

    # Separar entrada actual cuando proceda (sólo en vertical).
    actual_entry: dict | None = None
    if pin_actual and orientacion == "vertical":
        for e in entries:
            if e.get("is_last") and not e.get("is_umbral"):
                actual_entry = e
                break
    historic_entries = [e for e in entries if e is not actual_entry]

    # Bloque pin de "Actual" (si aplica) — paleta azul pura.
    pin_html = ""
    if actual_entry is not None:
        _pin_color  = (color_actual_override or actual_entry["color"]).strip()
        _pin_label  = _html_mod.escape(actual_entry["label"])
        _pin_tag    = _html_mod.escape(etiqueta_actual)
        _line_w_pin = max(20, int(font_size * 3.0))
        pin_html = (
            f'<div style="display:flex;align-items:center;gap:6px;'
            f'padding:5px 8px;margin-bottom:6px;'
            f'background:{bg_pin};'
            f'border:1px solid #DBEAFE;'
            f'border-left:3px solid {_pin_color};'
            f'border-radius:5px;">'
            f'<div style="width:{_line_w_pin}px;height:0;flex-shrink:0;'
            f'border-top:3px solid {_pin_color};"></div>'
            f'<div style="display:flex;flex-direction:column;line-height:1.15;">'
            f'<span style="font-size:{max(6, font_size - 1)}pt;'
            f'color:{_COLOR_TEXT_DIM};font-weight:600;'
            f'text-transform:uppercase;letter-spacing:0.3px;">{_pin_tag}</span>'
            f'<span style="font-size:{font_size + 1}pt;font-weight:700;'
            f'color:{_COLOR_TEXT};">{_pin_label}</span>'
            f'</div></div>'
        )

    subhead_html = ""
    if actual_entry is not None and etiqueta_historico.strip():
        subhead_html = (
            f'<div style="font-size:{max(6, font_size - 1)}pt;'
            f'color:{_COLOR_TEXT_DIM};font-weight:600;'
            f'text-transform:uppercase;letter-spacing:0.3px;'
            f'padding-bottom:3px;margin-bottom:3px;'
            f'border-bottom:1px dashed #E5E7EB;">'
            f'{_html_mod.escape(etiqueta_historico.strip())}</div>'
        )

    flex_dir = "column" if orientacion == "vertical" else "row"
    gap      = "3px"     if orientacion == "vertical" else "4px 14px"
    wrap_css = ""        if orientacion == "vertical" else "flex-wrap:wrap;"
    line_w   = max(18, int(font_size * 2.8))

    items_parts: list[str] = []
    for e in historic_entries:
        label     = _html_mod.escape(e["label"])
        color     = e["color"]
        is_last   = e.get("is_last", False)
        is_umbral = e.get("is_umbral", False)

        if is_umbral:
            line_css = (
                f"width:{line_w}px;height:0;flex-shrink:0;"
                f"border-top:1.5px dashed {color};"
            )
            text_css = (
                f"font-size:{font_size}pt;color:{_COLOR_TEXT_DIM};"
                f"white-space:nowrap;"
            )
        elif is_last:
            line_css = (
                f"width:{line_w}px;height:0;flex-shrink:0;"
                f"border-top:3px solid {color};"
            )
            text_css = (
                f"font-size:{font_size}pt;font-weight:bold;"
                f"color:{_COLOR_TEXT};white-space:nowrap;"
            )
        else:
            line_css = (
                f"width:{line_w}px;height:0;flex-shrink:0;"
                f"border-top:1.5px solid {color};"
            )
            text_css = (
                f"font-size:{font_size}pt;color:{_COLOR_TEXT};"
                f"white-space:nowrap;"
            )

        items_parts.append(
            f'<div style="display:flex;align-items:center;gap:5px;">'
            f'<div style="{line_css}"></div>'
            f'<span style="{text_css}">{label}</span>'
            f'</div>'
        )
    items_html = "".join(items_parts)

    return (
        f'<div style="font-family:{_FONT_FAMILY};padding:6px 8px;'
        f'width:{width_px}px;height:{height_px}px;box-sizing:border-box;'
        f'display:flex;flex-direction:column;justify-content:flex-start;'
        f'overflow:hidden;">'
        f'{title_html}'
        f'{pin_html}'
        f'{subhead_html}'
        f'<div style="display:flex;flex-direction:{flex_dir};{wrap_css}gap:{gap};">'
        f'{items_html}'
        f'</div></div>'
    )


# ── Orquestador principal ─────────────────────────────────────────────────────

@register_script(metadata)
def generate(params: dict[str, Any], figsize: tuple[float, float]) -> str:
    """Genera la leyenda de campañas inclinométricas como HTML puro.

    Selecciona las campañas con el mismo algoritmo que ``grafico_inclinometro_v1``
    y asigna la misma rampa de color, garantizando coherencia visual entre
    ambos elementos de la plantilla.

    Args:
        params:  Parámetros resueltos por el motor.
        figsize: (ancho_pulgadas, alto_pulgadas) del elemento en el layout.

    Returns:
        Fragmento HTML embebible (sin ``<html>`` ni ``<body>``).
    """
    width_px  = max(1, int(figsize[0] * 96))
    height_px = max(1, int(figsize[1] * 96))

    # ── Sensor ────────────────────────────────────────────────────────────────
    sensor_name: str = (
        params.get("sensor")
        or params.get("sensores_1")
        or params.get("sensores 1")
        or params.get("sensores")
        or ""
    )
    if not sensor_name or str(sensor_name).startswith("$"):
        return _html_error("Sensor no configurado.")

    # ── Parámetros de selección ───────────────────────────────────────────────
    total_camp       = int(params.get("total_camp")    or 10)
    ultimas_camp     = int(params.get("ultimas_camp")  or 3)
    cadencia_dias    = int(params.get("cadencia_dias") or 15)
    color_scheme     = str(params.get("color_scheme")  or "Viridis")
    mostrar_umbrales = bool(params.get("mostrar_umbrales") or False)
    orientacion      = str(params.get("orientacion")   or "vertical")
    titulo_raw       = params.get("titulo")
    titulo           = str(titulo_raw) if titulo_raw is not None else "Leyenda"
    font_size        = max(6, int(params.get("font_size") or 8))
    eje              = str(params.get("eje") or "").strip().lower()
    if eje == "todos":
        eje = ""

    pin_actual         = bool(params.get("pin_actual", True))
    _ea_raw            = params.get("etiqueta_actual")
    etiqueta_actual    = str(_ea_raw) if _ea_raw is not None else "Actual"
    _ca_raw            = params.get("color_actual")
    color_actual_param = str(_ca_raw).strip() if _ca_raw else ""
    _eh_raw            = params.get("etiqueta_historico")
    etiqueta_historico = str(_eh_raw) if _eh_raw is not None else "Histórico"
    _bg_raw            = params.get("bg_pin")
    bg_pin             = str(_bg_raw).strip() if _bg_raw else "#EFF6FF"

    fecha_inicio_dt = _parse_iso_date(params.get("fecha_inicio"))
    fecha_fin_dt    = _parse_iso_date(params.get("fecha_fin"))

    # ── Carga del JSON del sensor ─────────────────────────────────────────────
    try:
        data = _load_data(sensor_name)
    except FileNotFoundError:
        fname = f"{sensor_name}.json"
        return _html_error(f"Archivo no encontrado: {fname}")
    except ValueError as exc:
        return _html_error(str(exc))

    # ── Campañas activas ──────────────────────────────────────────────────────
    all_keys = [
        k for k in data
        if k not in _EXCLUIDAS_JSON
        and data[k].get("campaign_info", {}).get("active") is True
    ]
    if not all_keys:
        return _html_error("Sin campañas activas en el JSON del sensor.")

    selected = _select_campaigns(
        all_keys, total_camp, ultimas_camp, cadencia_dias,
        fecha_inicio_dt, fecha_fin_dt,
    )
    if not selected:
        return _html_error("Sin campañas en el rango de fechas indicado.")

    # ── Rampa de color ────────────────────────────────────────────────────────
    try:
        colors = _sample_colorscale(color_scheme, len(selected))
    except Exception:
        colors = [_COLOR_TEXT_DIM] * len(selected)

    # ── Entradas de campañas (oldest-first = same order as inclinometer) ──────
    entries: list[dict] = []
    for i, fecha in enumerate(selected):
        is_last = (i == len(selected) - 1)
        try:
            label = datetime.fromisoformat(fecha).strftime("%d/%m/%Y")
        except ValueError:
            label = fecha[:10]
        entries.append({
            "label":     label,
            "color":     colors[i],
            "is_last":   is_last,
            "is_umbral": False,
        })

    # ── Entradas de umbrales (opcional) ──────────────────────────────────────
    if mostrar_umbrales:
        umbrales_section = data.get("umbrales") or {}
        deformadas       = umbrales_section.get("deformadas") or {}

        # Filtrado por eje (parámetro explícito; vacío = sin filtrar)
        eje_filtro = ""
        if eje == "a":
            eje_filtro = "_a"
        elif eje == "b":
            eje_filtro = "_b"

        if isinstance(deformadas, dict) and deformadas:
            for nombre_umbral, meta in deformadas.items():
                if not isinstance(meta, dict):
                    continue
                nombre_str = str(nombre_umbral)
                if eje_filtro and not nombre_str.endswith(eje_filtro):
                    continue

                color_u = str(meta.get("color") or _COLOR_UMBRAL)

                # Nombre limpio (sin sufijo _a/_b) — coherente con el gráfico
                if nombre_str.endswith(("_a", "_b")):
                    display_name = nombre_str[:-2]
                else:
                    display_name = nombre_str

                entries.append({
                    "label":     display_name,
                    "color":     color_u,
                    "is_last":   False,
                    "is_umbral": True,
                })
        else:
            # Compatibilidad: JSON sin "deformadas" → entrada genérica
            entries.append({
                "label":     "Umbral",
                "color":     _COLOR_UMBRAL,
                "is_last":   False,
                "is_umbral": True,
            })

    return _build_legend_html(
        entries, titulo, orientacion, font_size, width_px, height_px,
        pin_actual=pin_actual,
        etiqueta_actual=etiqueta_actual,
        color_actual_override=color_actual_param,
        etiqueta_historico=etiqueta_historico,
        bg_pin=bg_pin,
    )

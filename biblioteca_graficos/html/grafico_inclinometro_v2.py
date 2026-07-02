"""Gráfico de perfil de deformación inclinométrica — motor HTML/Plotly (v2).

Lee campañas desde archivos JSON locales en ``json_inclis/`` y dibuja los
perfiles de desplazamiento acumulado vs. profundidad o cota absoluta,
replicando la estética visual del módulo original de IncliData.

La selección de campañas replica el algoritmo de IncliData: las primeras
``ultimas_camp`` campañas consecutivas más recientes, luego retrocede con
una cadencia de ``cadencia_dias`` días hasta completar ``total_camp``.
Las campañas se dibujan con una rampa de color configurable; la más reciente
destaca con mayor grosor.

Carga provisional: ``_load_mock_data()`` lee desde JSON local.
Cuando los datos vengan de la BD, bastará con reemplazar esa función;
``_render_plot()`` y ``generate()`` no necesitarán cambios.

Función principal: ``generate(params, figsize) -> str``

Novedades respecto a v1
-----------------------
dtick_x : float — intervalo de las divisiones verticales del eje X (mm).
                  Por defecto 5 mm.  En v1 Plotly lo calculaba automáticamente.

Parámetros configurables
------------------------
sensor          : str   — nombre del archivo JSON (sin extensión) en json_inclis/
variable_x      : str   — campo de 'calc' a graficar en el eje X
variable_y      : str   — "cota_abs" (eje Y normal) o "depth" (invertido)
total_camp      : int   — total máximo de campañas a mostrar
ultimas_camp    : int   — campañas recientes consecutivas
cadencia_dias   : int   — salto en días para campañas históricas
fecha_inicio    : str   — ISO fecha de inicio del filtro
fecha_fin       : str   — ISO fecha de fin del filtro
escala_grafico  : str   — "auto" o "manual"
valor_min_x     : float — límite inferior X (escala manual)
valor_max_x     : float — límite superior X (escala manual)
color_scheme    : str   — "Viridis" | "Plasma" | "Azules" | "Rojos"
mostrar_umbrales: bool  — dibuja perfiles de umbral del JSON
show_markers    : bool  — True = mode='lines+markers'
x_axis_title    : str   — etiqueta eje X
y_axis_title    : str   — etiqueta eje Y
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime
from typing import Any

from utils.script_registry import ParameterMetadata, ScriptMetadata, register_script

# ── Metadata ──────────────────────────────────────────────────────────────────

metadata = ScriptMetadata(
    nombre="grafico_inclinometro_v2",
    tipo="grafico",
    descripcion="Perfil de deformación inclinométrica (IncliData) con subdivisión X configurable",
    parametros=[
        ParameterMetadata(
            nombre="sensor", tipo="texto", requerido=False, default="$CURRENT",
            descripcion="Nombre del sensor (archivo JSON sin extensión en json_inclis/).",
        ),
        ParameterMetadata(
            nombre="variable_x", tipo="lista", requerido=False, default="abs_dev_a",
            opciones=["desp_a", "desp_b", "abs_dev_a", "abs_dev_b",
                      "incr_dev_a", "incr_dev_b", "checksum_a", "checksum_b"],
            descripcion="Campo del dict 'calc' a representar en el eje X.",
        ),
        ParameterMetadata(
            nombre="variable_y", tipo="lista", requerido=False, default="cota_abs",
            opciones=["cota_abs", "depth"],
            descripcion="Variable eje Y: cota_abs (normal) o depth (invertido).",
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
            nombre="escala_grafico", tipo="lista", requerido=False, default="auto",
            opciones=["auto", "manual"],
            descripcion="Escala del eje X: auto o manual.",
        ),
        ParameterMetadata(
            nombre="valor_min_x", tipo="numero", requerido=False, default=-50,
            descripcion="Límite inferior X (solo con escala manual).",
        ),
        ParameterMetadata(
            nombre="valor_max_x", tipo="numero", requerido=False, default=50,
            descripcion="Límite superior X (solo con escala manual).",
        ),
        ParameterMetadata(
            nombre="color_scheme", tipo="lista", requerido=False, default="Viridis",
            opciones=["Viridis", "Plasma", "Azules", "Rojos"],
            descripcion="Rampa de color para las campañas.",
        ),
        ParameterMetadata(
            nombre="mostrar_umbrales", tipo="bool", requerido=False, default=False,
            descripcion="Muestra los perfiles de umbral del JSON.",
        ),
        ParameterMetadata(
            nombre="show_markers", tipo="bool", requerido=False, default=False,
            descripcion="Activa puntos individuales sobre la línea.",
        ),
        ParameterMetadata(
            nombre="show_legend", tipo="bool", requerido=False, default=False,
            descripcion="Muestra la leyenda de campañas en el gráfico.",
        ),
        ParameterMetadata(
            nombre="x_axis_title", tipo="texto", requerido=False, default="Desplazamiento (mm)",
            descripcion="Etiqueta del eje X.",
        ),
        ParameterMetadata(
            nombre="y_axis_title", tipo="texto", requerido=False, default="Cota (m)",
            descripcion="Etiqueta del eje Y.",
        ),
        ParameterMetadata(
            nombre="titulo", tipo="texto", requerido=False, default="",
            descripcion="Título centrado en la parte superior. Vacío = sin título.",
        ),
        ParameterMetadata(
            nombre="destacar_actual", tipo="bool", requerido=False, default=True,
            descripcion="Resalta la campaña más reciente con grosor diferenciado.",
        ),
        ParameterMetadata(
            nombre="color_actual", tipo="texto", requerido=False, default="",
            descripcion="Color hex de la campaña actual. Vacío = último color de la rampa.",
        ),
        ParameterMetadata(
            nombre="width_actual", tipo="numero", requerido=False, default=2.8,
            descripcion="Grosor (px) de la línea de la campaña actual.",
        ),
        ParameterMetadata(
            nombre="width_historico", tipo="numero", requerido=False, default=1.0,
            descripcion="Grosor (px) de las líneas históricas.",
        ),
        ParameterMetadata(
            nombre="opacity_historico", tipo="numero", requerido=False, default=0.40,
            descripcion="Opacidad (0-1) de las líneas históricas.",
        ),
        ParameterMetadata(
            nombre="dtick_x", tipo="numero", requerido=False, default=5,
            descripcion="Intervalo de las divisiones verticales del eje X (mm). 0 = automático.",
        ),
    ],
)

PARAMETER_METADATA: list[dict] = [
    {
        "nombre": "sensor", "tipo": "texto", "requerido": False, "default": "$CURRENT",
        "descripcion": "Nombre del sensor (archivo JSON sin extensión en json_inclis/).",
    },
    {
        "nombre": "variable_x", "tipo": "lista", "requerido": False, "default": "abs_dev_a",
        "opciones": ["desp_a", "desp_b", "abs_dev_a", "abs_dev_b",
                     "incr_dev_a", "incr_dev_b", "checksum_a", "checksum_b"],
        "descripcion": "Campo del dict 'calc' a representar en el eje X.",
    },
    {
        "nombre": "variable_y", "tipo": "lista", "requerido": False, "default": "cota_abs",
        "opciones": ["cota_abs", "depth"],
        "descripcion": "Variable eje Y: cota_abs (normal) o depth (invertido).",
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
        "nombre": "escala_grafico", "tipo": "lista", "requerido": False, "default": "auto",
        "opciones": ["auto", "manual"],
        "descripcion": "Escala del eje X: auto o manual.",
    },
    {
        "nombre": "valor_min_x", "tipo": "numero", "requerido": False, "default": -50,
        "descripcion": "Límite inferior X (solo con escala manual).",
    },
    {
        "nombre": "valor_max_x", "tipo": "numero", "requerido": False, "default": 50,
        "descripcion": "Límite superior X (solo con escala manual).",
    },
    {
        "nombre": "color_scheme", "tipo": "lista", "requerido": False, "default": "Viridis",
        "opciones": ["Viridis", "Plasma", "Azules", "Rojos"],
        "descripcion": "Rampa de color para las campañas.",
    },
    {
        "nombre": "mostrar_umbrales", "tipo": "bool", "requerido": False, "default": False,
        "descripcion": "Muestra los perfiles de umbral del JSON.",
    },
    {
        "nombre": "show_markers", "tipo": "bool", "requerido": False, "default": False,
        "descripcion": "Activa puntos individuales sobre la línea.",
    },
    {
        "nombre": "show_legend", "tipo": "bool", "requerido": False, "default": False,
        "descripcion": "Muestra la leyenda de campañas en el gráfico.",
    },
    {
        "nombre": "x_axis_title", "tipo": "texto", "requerido": False,
        "default": "Desplazamiento (mm)",
        "descripcion": "Etiqueta del eje X.",
    },
    {
        "nombre": "y_axis_title", "tipo": "texto", "requerido": False, "default": "Cota (m)",
        "descripcion": "Etiqueta del eje Y.",
    },
    {
        "nombre": "titulo", "tipo": "texto", "requerido": False, "default": "",
        "descripcion": "Título centrado en la parte superior. Vacío = sin título.",
    },
    {
        "nombre": "destacar_actual", "tipo": "bool", "requerido": False, "default": True,
        "descripcion": "Resalta la campaña más reciente con grosor diferenciado.",
    },
    {
        "nombre": "color_actual", "tipo": "texto", "requerido": False, "default": "",
        "descripcion": "Color hex de la campaña actual. Vacío = último color de la rampa.",
    },
    {
        "nombre": "width_actual", "tipo": "numero", "requerido": False, "default": 2.8,
        "descripcion": "Grosor (px) de la línea de la campaña actual.",
    },
    {
        "nombre": "width_historico", "tipo": "numero", "requerido": False, "default": 1.0,
        "descripcion": "Grosor (px) de las líneas históricas.",
    },
    {
        "nombre": "opacity_historico", "tipo": "numero", "requerido": False, "default": 0.40,
        "descripcion": "Opacidad (0-1) de las líneas históricas.",
    },
    {
        "nombre": "dtick_x", "tipo": "numero", "requerido": False, "default": 5,
        "descripcion": "Intervalo de las divisiones verticales del eje X (mm). 0 = automático.",
    },
]

# ── Schema de controles UI (consumido por dispatch_table._build_custom_controls) ─

_CUSTOM_OPTIONS_SCHEMA: list[dict] = [
    {
        "id": "variable_x",
        "label": "Variable eje X",
        "tipo": "select",
        "default": "abs_dev_a",
        "opciones": [
            {"value": "desp_a",     "label": "desp_a"},
            {"value": "desp_b",     "label": "desp_b"},
            {"value": "abs_dev_a",  "label": "abs_dev_a"},
            {"value": "abs_dev_b",  "label": "abs_dev_b"},
            {"value": "incr_dev_a", "label": "incr_dev_a"},
            {"value": "incr_dev_b", "label": "incr_dev_b"},
            {"value": "checksum_a", "label": "checksum_a"},
            {"value": "checksum_b", "label": "checksum_b"},
        ],
        "descripcion": {
            "es": "Campo del diccionario 'calc' a graficar en el eje X.",
            "en": "Field from 'calc' dict to plot on the X axis.",
        },
    },
    {
        "id": "variable_y",
        "label": "Variable eje Y",
        "tipo": "select",
        "default": "cota_abs",
        "opciones": [
            {"value": "cota_abs", "label": "Cota absoluta (m)"},
            {"value": "depth",    "label": "Profundidad (m, invertido)"},
        ],
        "descripcion": {
            "es": "cota_abs: eje Y normal. depth: eje Y invertido (0 arriba).",
            "en": "cota_abs: normal Y axis. depth: inverted Y axis (0 at top).",
        },
    },
    {
        "id": "total_camp",
        "label": "Total campañas",
        "tipo": "number",
        "default": 10,
        "descripcion": {
            "es": "Número máximo de campañas a representar.",
            "en": "Maximum number of campaigns to display.",
        },
    },
    {
        "id": "ultimas_camp",
        "label": "Campañas recientes",
        "tipo": "number",
        "default": 3,
        "descripcion": {
            "es": "Número de campañas más recientes consecutivas.",
            "en": "Number of most recent consecutive campaigns.",
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
        "id": "escala_grafico",
        "label": "Escala eje X",
        "tipo": "select",
        "default": "auto",
        "opciones": [
            {"value": "auto",   "label": "Automática"},
            {"value": "manual", "label": "Manual"},
        ],
        "descripcion": {
            "es": "auto: Plotly ajusta los límites. manual: usa valor_min_x y valor_max_x.",
            "en": "auto: Plotly adjusts limits. manual: uses valor_min_x and valor_max_x.",
        },
    },
    {
        "id": "valor_min_x",
        "label": "Mín. eje X",
        "tipo": "number",
        "default": -50,
        "descripcion": {
            "es": "Límite inferior del eje X (solo con escala manual).",
            "en": "Lower bound of X axis (manual scale only).",
        },
    },
    {
        "id": "valor_max_x",
        "label": "Máx. eje X",
        "tipo": "number",
        "default": 50,
        "descripcion": {
            "es": "Límite superior del eje X (solo con escala manual).",
            "en": "Upper bound of X axis (manual scale only).",
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
            "es": "Rampa de color aplicada a las campañas (más antigua → más reciente).",
            "en": "Color ramp applied to campaigns (oldest → most recent).",
        },
    },
    {
        "id": "mostrar_umbrales",
        "label": "Mostrar umbrales",
        "tipo": "switch",
        "default": False,
        "descripcion": {
            "es": "Dibuja los perfiles de umbral definidos en el JSON del sensor.",
            "en": "Draws threshold profiles defined in the sensor JSON.",
        },
    },
    {
        "id": "show_markers",
        "label": "Mostrar marcadores",
        "tipo": "switch",
        "default": False,
        "descripcion": {
            "es": "Activa puntos individuales sobre cada línea de perfil.",
            "en": "Enables individual data point markers on each profile line.",
        },
    },
    {
        "id": "show_legend",
        "label": "Mostrar leyenda",
        "tipo": "switch",
        "default": False,
        "descripcion": {
            "es": "Muestra la leyenda de campañas sobre el gráfico.",
            "en": "Shows the campaign legend above the chart.",
        },
    },
    {
        "id": "x_axis_title",
        "label": "Título eje X",
        "tipo": "text",
        "default": "Desplazamiento (mm)",
        "descripcion": {
            "es": "Etiqueta del eje horizontal. Vacío = sin título.",
            "en": "Horizontal axis label. Empty = no title.",
        },
    },
    {
        "id": "y_axis_title",
        "label": "Título eje Y",
        "tipo": "text",
        "default": "Cota (m)",
        "descripcion": {
            "es": "Etiqueta del eje vertical. Vacío = sin título.",
            "en": "Vertical axis label. Empty = no title.",
        },
    },
    {
        "id": "titulo",
        "label": "Título del gráfico",
        "tipo": "text",
        "default": "",
        "descripcion": {
            "es": "Título centrado en la parte superior. Vacío = sin título.",
            "en": "Title centered at the top. Empty = no title.",
        },
    },
    {
        "id": "destacar_actual",
        "label": "Destacar campaña actual",
        "tipo": "switch",
        "default": True,
        "descripcion": {
            "es": "Resalta la campaña más reciente con grosor diferenciado.",
            "en": "Highlights the most recent campaign with differentiated line width.",
        },
    },
    {
        "id": "color_actual",
        "label": "Color campaña actual",
        "tipo": "text",
        "default": "",
        "descripcion": {
            "es": "Color hex de la campaña actual. Vacío = último color de la rampa.",
            "en": "Hex color for the current campaign. Empty = last color of the ramp.",
        },
    },
    {
        "id": "width_actual",
        "label": "Grosor línea actual",
        "tipo": "number",
        "default": 2.8,
        "descripcion": {
            "es": "Grosor (px) de la línea de la campaña actual.",
            "en": "Line width (px) for the current campaign.",
        },
    },
    {
        "id": "width_historico",
        "label": "Grosor líneas históricas",
        "tipo": "number",
        "default": 1.0,
        "descripcion": {
            "es": "Grosor (px) de las líneas históricas.",
            "en": "Line width (px) for historical campaigns.",
        },
    },
    {
        "id": "opacity_historico",
        "label": "Opacidad históricas",
        "tipo": "number",
        "default": 0.40,
        "descripcion": {
            "es": "Opacidad (0-1) de las líneas históricas.",
            "en": "Opacity (0-1) of historical campaign lines.",
        },
    },
    {
        "id": "dtick_x",
        "label": "División eje X (mm)",
        "tipo": "number",
        "default": 5,
        "descripcion": {
            "es": "Intervalo entre líneas verticales del eje X (mm). 0 = automático.",
            "en": "Interval between vertical gridlines on the X axis (mm). 0 = automatic.",
        },
    },
]

# ── Constantes estéticas ───────────────────────────────────────────────────────

_FONT_FAMILY  = "Arial, Helvetica, sans-serif"
_GRID_COLOR   = "#F3F4F6"
_COLOR_UMBRAL = "#EF4444"
_EXCLUIDAS_JSON = {"info", "umbrales"}


# ── Helpers de error ───────────────────────────────────────────────────────────

def _html_error(msg: str) -> str:
    """Placeholder genérico (fondo neutro, texto gris)."""
    return (
        f'<div style="width:100%;height:100%;display:flex;'
        f'align-items:center;justify-content:center;'
        f'font-family:{_FONT_FAMILY};font-size:10pt;color:#6B7280;">'
        f'<span>{msg}</span></div>'
    )


def _html_file_not_found(json_path: pathlib.Path) -> str:
    """Error de archivo no encontrado (fondo rojo claro)."""
    return (
        f'<div style="width:100%;padding:16px;background:#FEF2F2;'
        f'border:1px solid #FCA5A5;border-radius:6px;'
        f'font-family:{_FONT_FAMILY};font-size:10pt;color:#991B1B;">'
        f'<strong>Archivo no encontrado:</strong> {json_path.name}<br>'
        f'<span style="font-size:9pt;color:#B45309;">Ruta buscada: {json_path}</span>'
        f'</div>'
    )


# ── Capa de datos (provisional — JSON local) ──────────────────────────────────

def _load_mock_data(sensor_name: str) -> dict:
    """Carga y parsea el archivo JSON del sensor desde ``json_inclis/``.

    Args:
        sensor_name: Nombre del sensor (= nombre de archivo sin extensión).

    Returns:
        Diccionario con la estructura completa del JSON.

    Raises:
        FileNotFoundError: Si no existe el archivo.
        ValueError: Si el JSON no es válido.
    """
    json_path = pathlib.Path.cwd() / "json_inclis" / f"{sensor_name}.json"
    if not json_path.exists():
        raise FileNotFoundError(str(json_path))
    try:
        with json_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido en {json_path.name}: {exc}") from exc


# ── Helpers de selección de campañas y color ──────────────────────────────────

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

    1. Filtra por rango de fechas.
    2. Toma las ``ultimas_camp`` más recientes de forma consecutiva.
    3. Retrocede con cadencia >= ``cadencia_dias`` días hasta completar
       ``total_camp`` campañas.
    4. Devuelve la lista ordenada de más antigua a más reciente.
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

    n_recientes = min(ultimas_camp, total_camp, len(sorted_newest))
    selected    = list(sorted_newest[:n_recientes])

    if len(selected) < total_camp and len(sorted_newest) > n_recientes:
        last_dt = _parse(selected[-1])
        for key in sorted_newest[n_recientes:]:
            if len(selected) >= total_camp:
                break
            key_dt = _parse(key)
            if (last_dt - key_dt).days >= cadencia_dias:
                selected.append(key)
                last_dt = key_dt

    return sorted(selected, key=_parse)


def _sample_colorscale(scheme: str, n: int) -> list[str]:
    """Extrae ``n`` colores equiespaciados de una rampa secuencial de Plotly."""
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


# ── Capa de umbrales ──────────────────────────────────────────────────────────

def _draw_umbrales(
    fig: Any,
    data: dict,
    variable_x: str,
    variable_y: str,
) -> None:
    """Añade trazas de umbrales al figure según el formato real del JSON.

    Estructura esperada en ``data["umbrales"]``:
      ``deformadas``: dict[nombre_umbral → metadata] con claves
        ``color``, ``tipo_linea``, ``flanco``, ``nivel``.
      ``valores``: tabla unificada (list[dict]) donde cada fila trae
        ``cota_abs``/``depth`` y una columna por umbral con el valor de
        desplazamiento.

    Filtrado por eje:
      El eje del gráfico se infiere del sufijo ``_a``/``_b`` de
      ``variable_x``. Sólo se dibujan umbrales cuyo nombre termine en el
      mismo sufijo. Si ``variable_x`` no tiene sufijo de eje reconocible,
      no se filtra.

    Política de flancos (estricta — refleja literalmente lo declarado):
      ``flanco_positivo`` → curva en X = +valor.
      ``flanco_negativo`` → curva en X = -valor.
      Cualquier otro valor o ausente → ambos lados (espejo).

    Mapeo de tipo_linea (vocabulario JSON → vocabulario Plotly):
      ``dashed`` → ``dash`` ; ``dotted`` → ``dot`` ;
      ``dashdot`` → ``dashdot`` ; ``longdash`` → ``longdash`` ;
      ``solid`` → línea continua (sin dash).

    Args:
        fig:        ``go.Figure`` al que se añaden las trazas.
        data:       Diccionario completo del JSON del sensor.
        variable_x: Nombre del campo X de las campañas (e.g. ``abs_dev_a``).
        variable_y: Nombre del campo Y (``depth`` o ``cota_abs``).
    """
    import plotly.graph_objects as go

    umbrales_section = data.get("umbrales") or {}
    deformadas       = umbrales_section.get("deformadas") or {}
    valores_table    = umbrales_section.get("valores") or []

    if (
        not isinstance(deformadas, dict)
        or not isinstance(valores_table, list)
        or not valores_table
    ):
        return

    # Detección de eje desde variable_x ("desp_a", "abs_dev_b" → "_a"/"_b")
    eje_filtro = ""
    if variable_x.endswith("_a"):
        eje_filtro = "_a"
    elif variable_x.endswith("_b"):
        eje_filtro = "_b"

    _DASH_MAP = {
        "dashed":   "dash",
        "dotted":   "dot",
        "dashdot":  "dashdot",
        "longdash": "longdash",
        "solid":    None,
    }

    label_index = 0
    for nombre_umbral, meta in deformadas.items():
        if not isinstance(meta, dict):
            continue
        nombre_str = str(nombre_umbral)

        # Filtrado por eje
        if eje_filtro and not nombre_str.endswith(eje_filtro):
            continue

        color_u   = str(meta.get("color") or _COLOR_UMBRAL)
        tipo_u    = str(meta.get("tipo_linea") or "dashed").lower()
        flanco    = str(meta.get("flanco") or "").lower()
        line_dash = _DASH_MAP.get(tipo_u, "dash")

        # Lados según flanco (estricto — sólo lo declarado)
        if flanco == "flanco_positivo":
            sides = [1]
        elif flanco == "flanco_negativo":
            sides = [-1]
        else:
            sides = [1, -1]

        # Extracción de pares (valor_umbral, y) desde la tabla unificada
        pairs_u = [
            (row.get(nombre_str), row.get(variable_y))
            for row in valores_table
            if isinstance(row, dict)
            and row.get(nombre_str) is not None
            and row.get(variable_y) is not None
        ]
        if not pairs_u:
            continue
        x_u, y_u = zip(*pairs_u)

        # Nombre limpio para visualización (sin sufijo _a / _b)
        if nombre_str.endswith(("_a", "_b")):
            display_name = nombre_str[:-2]
        else:
            display_name = nombre_str

        for idx, sign in enumerate(sides):
            x_signed = [v * sign for v in x_u]
            line_kwargs: dict = {"width": 2.2, "color": color_u}
            if line_dash:
                line_kwargs["dash"] = line_dash
            fig.add_trace(go.Scatter(
                x=list(x_signed),
                y=list(y_u),
                mode="lines",
                name=display_name,
                showlegend=(idx == 0),  # una sola entrada en leyenda Plotly
                legendgroup=display_name,
                opacity=0.85,
                line=dict(**line_kwargs),
                hovertemplate=(
                    f"<b>{display_name}</b><br>"
                    f"X: %{{x:.2f}}<br>Y: %{{y:.2f}}<extra></extra>"
                ),
            ))

        # Mini-leyenda inline en la esquina superior izquierda del
        # panel. Aprovecha el espacio vacío cuando los umbrales son
        # flanco_positivo (sólo dibujan a la derecha de X=0).
        fig.add_annotation(
            x=0.04,
            y=0.97 - label_index * 0.06,
            xref="paper", yref="paper",
            xanchor="left", yanchor="top",
            text=f"<b>{display_name}</b>",
            showarrow=False,
            font=dict(size=9, color=color_u, family=_FONT_FAMILY),
            bgcolor="rgba(255,255,255,0.75)",
            borderpad=2,
        )
        label_index += 1


# ── Capa de renderizado ────────────────────────────────────────────────────────

def _render_plot(
    data: dict,
    params: dict,
    width_px: int,
    height_px: int,
) -> str:
    """Construye el ``go.Figure`` y retorna el fragmento HTML embebible.

    Args:
        data:      Estructura de campañas tal como la devuelve ``_load_mock_data``.
        params:    Parámetros ya resueltos por el motor.
        width_px:  Ancho de la figura en píxeles.
        height_px: Alto de la figura en píxeles.

    Returns:
        Fragmento HTML con Plotly.js (CDN) listo para incrustar.

    Raises:
        ValueError: Si no hay campañas o la selección queda vacía.
    """
    import plotly.graph_objects as go
    import plotly.io as pio

    # ── Parámetros ────────────────────────────────────────────────────────────
    variable_x       = str(params.get("variable_x") or "abs_dev_a")
    variable_y       = str(params.get("variable_y") or "cota_abs")
    show_markers     = bool(params.get("show_markers") or False)
    show_legend      = bool(params.get("show_legend", False))
    _x_title     = params.get("x_axis_title")
    x_axis_title = str(_x_title) if _x_title is not None else "Desplazamiento (mm)"
    _y_title     = params.get("y_axis_title")
    y_axis_title = str(_y_title) if _y_title is not None else "Cota (m)"
    titulo           = str(params.get("titulo") or "")
    total_camp       = int(params.get("total_camp")    or 10)
    ultimas_camp     = int(params.get("ultimas_camp")  or 3)
    cadencia_dias    = int(params.get("cadencia_dias") or 15)
    escala           = str(params.get("escala_grafico") or "auto")
    color_scheme     = str(params.get("color_scheme")  or "Viridis")
    mostrar_umbrales = bool(params.get("mostrar_umbrales") or False)

    destacar_actual   = bool(params.get("destacar_actual", True))
    _ca_raw           = params.get("color_actual")
    color_actual      = str(_ca_raw).strip() if _ca_raw else ""
    width_actual      = float(params.get("width_actual")    or 2.8)
    width_historico   = float(params.get("width_historico") or 1.0)
    opacity_historico = float(params.get("opacity_historico") or 0.40)

    _dtick_raw = params.get("dtick_x")
    dtick_x = float(_dtick_raw) if _dtick_raw is not None else 5.0

    _vmin = params.get("valor_min_x")
    _vmax = params.get("valor_max_x")
    valor_min_x = float(_vmin) if _vmin is not None else -50.0
    valor_max_x = float(_vmax) if _vmax is not None else  50.0

    fecha_inicio_dt = _parse_iso_date(params.get("fecha_inicio"))
    fecha_fin_dt    = _parse_iso_date(params.get("fecha_fin"))

    mode = "lines+markers" if show_markers else "lines"

    # ── Selección de campañas ─────────────────────────────────────────────────
    all_keys = [
        k for k in data
        if k not in _EXCLUIDAS_JSON
        and data[k].get("campaign_info", {}).get("active") is True
    ]
    if not all_keys:
        raise ValueError("El archivo JSON no contiene campañas de datos.")

    selected = _select_campaigns(
        all_keys, total_camp, ultimas_camp, cadencia_dias,
        fecha_inicio_dt, fecha_fin_dt,
    )
    if not selected:
        raise ValueError("No hay campañas en el rango de fechas indicado.")

    colors = _sample_colorscale(color_scheme, len(selected))

    # ── Figura ────────────────────────────────────────────────────────────────
    fig = go.Figure()
    fig.add_vline(x=0, line_dash="dot", line_color="#D1D5DB", line_width=1, opacity=0.5)

    # ── Umbrales (dibujar primero para que campañas queden encima) ────────────
    if mostrar_umbrales:
        _draw_umbrales(fig, data, variable_x, variable_y)

    for i, fecha in enumerate(selected):
        calc: list[dict] = data[fecha].get("calc", [])
        pairs = [
            (row.get(variable_x), row.get(variable_y))
            for row in calc
            if row.get(variable_x) is not None and row.get(variable_y) is not None
        ]
        if not pairs:
            continue

        x_vals, y_vals = zip(*pairs)
        is_last = (i == len(selected) - 1)

        try:
            label = datetime.fromisoformat(fecha).strftime("%d/%m/%Y")
        except ValueError:
            label = fecha

        # Color y grosor diferenciados para la campaña actual; mantenemos la
        # rampa azul (los rojos quedan reservados para umbrales de alarma).
        if is_last:
            _color = (color_actual or colors[i]) if destacar_actual else colors[i]
            _width = width_actual
            _opacity = 1.0
        else:
            _color = colors[i]
            _width = width_historico
            _opacity = opacity_historico

        fig.add_trace(go.Scatter(
            x=list(x_vals),
            y=list(y_vals),
            mode=mode,
            name=label,
            showlegend=True,
            opacity=_opacity,
            line=dict(width=_width, color=_color),
            hovertemplate=(
                f"<b>{'(actual) ' if is_last else ''}{label}</b><br>"
                f"X: %{{x:.2f}}<br>Y: %{{y:.2f}}<extra></extra>"
            ),
        ))

    # ── Escala manual ─────────────────────────────────────────────────────────
    if escala == "manual":
        fig.update_xaxes(range=[valor_min_x, valor_max_x])

    # ── depth: profundidad 0 en la parte superior ─────────────────────────────
    if variable_y == "depth":
        fig.update_yaxes(autorange="reversed", dtick=5)

    # ── Layout ────────────────────────────────────────────────────────────────
    if titulo and show_legend:
        _margin_t = 75
    elif titulo:
        _margin_t = 50
    elif show_legend:
        _margin_t = 55
    else:
        _margin_t = 28

    fig.update_layout(
        width=width_px,
        height=height_px,
        margin=dict(l=55, r=40, t=_margin_t, b=45),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family=_FONT_FAMILY, size=9, color="#374151"),
        title=dict(
            text=titulo,
            x=0.5,
            xanchor="center",
            font=dict(family=_FONT_FAMILY, size=13, color="#374151"),
            pad=dict(b=4),
        ) if titulo else dict(text=""),
        showlegend=show_legend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=9, family=_FONT_FAMILY),
        ),
        xaxis=dict(
            title=dict(text=x_axis_title, font=dict(size=9)),
            showgrid=True,
            gridcolor=_GRID_COLOR,
            gridwidth=1,
            linecolor="#D1D5DB",
            linewidth=1,
            tickfont=dict(size=8, color="#6B7280"),
            showline=True,
            mirror=False,
            zeroline=False,
            **(dict(dtick=dtick_x) if dtick_x > 0 else {}),
        ),
        yaxis=dict(
            title=dict(text=y_axis_title, font=dict(size=9)),
            showgrid=True,
            gridcolor=_GRID_COLOR,
            gridwidth=1,
            linecolor="#D1D5DB",
            linewidth=1,
            tickfont=dict(size=8, color="#6B7280"),
            showline=True,
            mirror=False,
            zeroline=False,
        ),
        hovermode="closest",
    )

    return pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=False,
        config={"staticPlot": False, "displayModeBar": False, "responsive": True},
    )


# ── Orquestador principal ─────────────────────────────────────────────────────

@register_script(metadata)
def generate(params: dict[str, Any], figsize: tuple[float, float]) -> str:
    """Genera el perfil de deformación inclinométrica y devuelve un fragmento HTML.

    Resolución del sensor:
      El motor (``html_engine._resolve_params``) reemplaza ``$CURRENT`` por el
      valor de ``context["sensores_1"]`` antes de llamar a ``generate``, por lo
      que ``params["sensor"]`` debería llegar resuelto.

    Args:
        params:  Parámetros resueltos por el motor.
        figsize: (ancho_pulgadas, alto_pulgadas) del elemento en el layout.

    Returns:
        Fragmento HTML con Plotly.js (CDN) embebido, listo para incrustar.
    """
    try:
        import plotly.graph_objects  # noqa: F401
        import plotly.io              # noqa: F401
    except ImportError:
        return _html_error("Plotly no instalado: pip install plotly")

    # ── Resolución del nombre del sensor ──────────────────────────────────────
    sensor_name: str = (
        params.get("sensor")
        or params.get("sensores_1")
        or params.get("sensores 1")   # clave con espacio (contexto legacy)
        or params.get("sensores1")
        or params.get("sensores")
        or ""
    )
    if not sensor_name or str(sensor_name).startswith("$"):
        return _html_error(
            "Sensor no configurado. Asigna un sensor primario en la Dispatch Table."
        )

    width_px  = int(figsize[0] * 96)
    height_px = int(figsize[1] * 96)

    # ── Carga de datos ────────────────────────────────────────────────────────
    try:
        data = _load_mock_data(sensor_name)
    except FileNotFoundError as exc:
        return _html_file_not_found(pathlib.Path(str(exc)))
    except ValueError as exc:
        return _html_error(f"Error al leer JSON: {exc}")

    # ── Renderizado ───────────────────────────────────────────────────────────
    try:
        return _render_plot(data, params, width_px, height_px)
    except ValueError as exc:
        return _html_error(str(exc))
    except Exception as exc:  # noqa: BLE001
        return _html_error(f"Error al renderizar gráfico: {exc}")

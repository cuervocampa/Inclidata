"""Gráfico de perfil de deformación inclinométrica — motor HTML/Plotly.

Lee campañas desde archivos JSON locales en ``json_inclis/`` y dibuja los
perfiles de desplazamiento acumulado vs. profundidad o cota absoluta,
replicando la estética visual del módulo antiguo de IncliData.

Las campañas históricas se dibujan en azul tenue (steelblue, opacity=0.4).
La campaña más reciente se resalta en azul oscuro (#1d4e89, grosor=3).

Carga provisional: ``_load_mock_data()`` lee desde JSON local.
Cuando los datos vengan de la BD, bastará con reemplazar esa función;
``_render_plot()`` y ``generate()`` no necesitarán cambios.

Función principal: ``generate(params, figsize) -> str``

Parámetros configurables
------------------------
sensor       : str  — nombre del archivo JSON (sin extensión) en json_inclis/
                      Resuelto automáticamente desde sensores_1/sensores por el motor.
eje_medida   : str  — "A" → abs_dev_a  |  "B" → abs_dev_b
variable_y   : str  — "cota_abs" (eje Y normal) o "depth" (eje Y invertido)
show_markers : bool — True = mode='lines+markers'
x_axis_title : str  — etiqueta eje X
y_axis_title : str  — etiqueta eje Y
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime
from typing import Any

from utils.script_registry import ParameterMetadata, ScriptMetadata, register_script

# ── Metadata ──────────────────────────────────────────────────────────────────

metadata = ScriptMetadata(
    nombre="grafico_inclinometro_v1",
    tipo="grafico",
    descripcion="Perfil de deformación inclinométrica (IncliData) desde JSON local",
    parametros=[
        ParameterMetadata(
            nombre="sensor",
            tipo="texto",
            requerido=False,
            default="$CURRENT",
            descripcion="Nombre del sensor (archivo JSON sin extensión en json_inclis/).",
        ),
        ParameterMetadata(
            nombre="eje_medida",
            tipo="lista",
            requerido=False,
            default="A",
            opciones=["A", "B"],
            descripcion="Eje inclinométrico: A (abs_dev_a) o B (abs_dev_b).",
        ),
        ParameterMetadata(
            nombre="variable_y",
            tipo="lista",
            requerido=False,
            default="cota_abs",
            opciones=["cota_abs", "depth"],
            descripcion="Variable eje Y: cota_abs (normal) o depth (invertido).",
        ),
        ParameterMetadata(
            nombre="show_markers",
            tipo="bool",
            requerido=False,
            default=False,
            descripcion="Activa puntos individuales sobre la línea.",
        ),
        ParameterMetadata(
            nombre="x_axis_title",
            tipo="texto",
            requerido=False,
            default="Desplazamiento (mm)",
            descripcion="Etiqueta del eje X.",
        ),
        ParameterMetadata(
            nombre="y_axis_title",
            tipo="texto",
            requerido=False,
            default="Cota (m)",
            descripcion="Etiqueta del eje Y.",
        ),
    ],
)

PARAMETER_METADATA: list[dict] = [
    {
        "nombre": "sensor",
        "tipo": "texto",
        "requerido": False,
        "default": "$CURRENT",
        "descripcion": "Nombre del sensor (archivo JSON sin extensión en json_inclis/).",
    },
    {
        "nombre": "eje_medida",
        "tipo": "lista",
        "requerido": False,
        "default": "A",
        "opciones": ["A", "B"],
        "descripcion": "Eje inclinométrico: A (abs_dev_a) o B (abs_dev_b).",
    },
    {
        "nombre": "variable_y",
        "tipo": "lista",
        "requerido": False,
        "default": "cota_abs",
        "opciones": ["cota_abs", "depth"],
        "descripcion": "Variable eje Y: cota_abs (normal) o depth (invertido).",
    },
    {
        "nombre": "show_markers",
        "tipo": "bool",
        "requerido": False,
        "default": False,
        "descripcion": "Activa puntos individuales sobre la línea.",
    },
    {
        "nombre": "x_axis_title",
        "tipo": "texto",
        "requerido": False,
        "default": "Desplazamiento (mm)",
        "descripcion": "Etiqueta del eje X.",
    },
    {
        "nombre": "y_axis_title",
        "tipo": "texto",
        "requerido": False,
        "default": "Cota (m)",
        "descripcion": "Etiqueta del eje Y.",
    },
]

# ── Schema de controles UI (consumido por dispatch_table._build_custom_controls) ─
# El parámetro "sensor" queda excluido: el wizard lo gestiona mediante el
# selector de sensor primario (sensores_1) de la Dispatch Table.

_CUSTOM_OPTIONS_SCHEMA: list[dict] = [
    {
        "id": "eje_medida",
        "label": "Eje de medida",
        "tipo": "select",
        "default": "A",
        "opciones": [
            {"value": "A", "label": "Eje A (abs_dev_a)"},
            {"value": "B", "label": "Eje B (abs_dev_b)"},
        ],
        "descripcion": {
            "es": "Componente del inclinómetro a representar.",
            "en": "Inclinometer axis to display.",
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
]

# ── Constantes estéticas ───────────────────────────────────────────────────────

_FONT_FAMILY = "Arial, Helvetica, sans-serif"
_COLOR_HISTORICO = "steelblue"
_COLOR_ACTUAL = "#1d4e89"
_GRID_COLOR = "#F3F4F6"
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
    """Error de archivo no encontrado (fondo rojo claro #FEF2F2, borde #FCA5A5)."""
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
        sensor_name: Nombre del sensor, que debe coincidir con el nombre de
                     archivo (sin extensión) dentro de ``json_inclis/``.

    Returns:
        Diccionario con la estructura completa del JSON (incluye campañas,
        ``"info"`` y ``"umbrales"``).

    Raises:
        FileNotFoundError: Si no existe ``json_inclis/{sensor_name}.json``.
        ValueError: Si el archivo existe pero no es JSON válido.
    """
    json_path = pathlib.Path.cwd() / "json_inclis" / f"{sensor_name}.json"
    if not json_path.exists():
        raise FileNotFoundError(str(json_path))
    try:
        with json_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido en {json_path.name}: {exc}") from exc


# ── Capa de renderizado (independiente del origen de datos) ───────────────────

def _render_plot(
    data: dict,
    params: dict,
    width_px: int,
    height_px: int,
) -> str:
    """Construye el ``go.Figure`` y retorna el fragmento HTML embebible.

    No sabe de dónde vienen los datos — únicamente transforma ``data``
    (estructura de campañas) en una figura Plotly.

    Args:
        data:      Diccionario de campañas tal como lo devuelve ``_load_mock_data``.
        params:    Parámetros ya resueltos (eje_medida, variable_y, show_markers…).
        width_px:  Ancho de la figura en píxeles.
        height_px: Alto de la figura en píxeles.

    Returns:
        Fragmento HTML con Plotly.js (CDN) listo para incrustar.

    Raises:
        ImportError: Si Plotly no está instalado (capturada en ``generate``).
        ValueError: Si no hay campañas o la campaña actual carece de datos calc.
    """
    import plotly.graph_objects as go
    import plotly.io as pio

    eje_medida = str(params.get("eje_medida") or "A").upper()
    variable_y = str(params.get("variable_y") or "cota_abs")
    show_markers = bool(params.get("show_markers") or False)
    x_axis_title = str(params.get("x_axis_title") or "Desplazamiento (mm)")
    y_axis_title = str(params.get("y_axis_title") or "Cota (m)")

    # Ordenar campañas cronológicamente
    def _parse_dt(key: str) -> datetime:
        try:
            return datetime.fromisoformat(key)
        except ValueError:
            return datetime.min

    date_keys = sorted(
        [k for k in data if k not in _EXCLUIDAS_JSON],
        key=_parse_dt,
    )
    if not date_keys:
        raise ValueError("El archivo JSON no contiene campañas de datos.")

    x_field = "abs_dev_a" if eje_medida == "A" else "abs_dev_b"
    mode = "lines+markers" if show_markers else "lines"

    fig = go.Figure()
    fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)

    # Series históricas (todas salvo la última)
    for fecha in date_keys[:-1]:
        calc: list[dict] = data[fecha].get("calc", [])
        pairs = [
            (row.get(x_field), row.get(variable_y))
            for row in calc
            if row.get(x_field) is not None and row.get(variable_y) is not None
        ]
        if not pairs:
            continue

        x_vals, y_vals = zip(*pairs)
        try:
            label = datetime.fromisoformat(fecha).strftime("%d/%m/%Y")
        except ValueError:
            label = fecha

        fig.add_trace(go.Scatter(
            x=list(x_vals),
            y=list(y_vals),
            mode=mode,
            name=label,
            showlegend=False,
            opacity=0.4,
            line=dict(width=1.5, color=_COLOR_HISTORICO),
            hovertemplate=f"<b>{label}</b><br>X: %{{x:.2f}}<br>Y: %{{y:.2f}}<extra></extra>",
        ))

    # Campaña actual (última fecha cronológica)
    ultima = date_keys[-1]
    calc_u: list[dict] = data[ultima].get("calc", [])
    pairs_u = [
        (row.get(x_field), row.get(variable_y))
        for row in calc_u
        if row.get(x_field) is not None and row.get(variable_y) is not None
    ]
    if not pairs_u:
        raise ValueError("La campaña más reciente no contiene datos calculados (campo 'calc' vacío).")

    x_vals_u, y_vals_u = zip(*pairs_u)
    try:
        label_u = datetime.fromisoformat(ultima).strftime("%d/%m/%Y")
    except ValueError:
        label_u = ultima

    fig.add_trace(go.Scatter(
        x=list(x_vals_u),
        y=list(y_vals_u),
        mode=mode,
        name=f"{label_u} (actual)",
        showlegend=True,
        opacity=1.0,
        line=dict(width=3, color=_COLOR_ACTUAL),
        hovertemplate=f"<b>{label_u} (actual)</b><br>X: %{{x:.2f}}<br>Y: %{{y:.2f}}<extra></extra>",
    ))

    # depth: profundidad 0 en la parte superior
    if variable_y == "depth":
        fig.update_yaxes(autorange="reversed")

    fig.update_layout(
        width=width_px,
        height=height_px,
        margin=dict(l=55, r=40, t=60, b=45),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family=_FONT_FAMILY, size=9, color="#374151"),
        showlegend=True,
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
        include_plotlyjs="cdn",
        config={"staticPlot": False, "displayModeBar": False, "responsive": True},
    )


# ── Orquestador principal ─────────────────────────────────────────────────────

@register_script(metadata)
def generate(params: dict[str, Any], figsize: tuple[float, float]) -> str:
    """Genera el perfil de deformación inclinométrica y devuelve un fragmento HTML.

    Orquesta ``_load_mock_data`` y ``_render_plot``, convirtiendo cualquier
    excepción en un placeholder visual de error.

    Resolución del sensor:
      El motor (``html_engine._resolve_params``) reemplaza ``$CURRENT`` por el
      valor de ``context["sensores_1"]`` antes de llamar a ``generate``, por lo
      que ``params["sensor"]`` debería llegar resuelto. Como salvaguarda, se
      comprueban también ``params["sensores_1"]`` y ``params["sensores"]`` para
      cubrir el caso en que la política estricta del motor deje el valor en None
      (elemento registrado en ``mapeo_parametros`` pero ``sensor`` no mapeado
      explícitamente).

    Args:
        params:  Parámetros resueltos por el motor.
        figsize: (ancho_pulgadas, alto_pulgadas) del elemento en el layout.

    Returns:
        Fragmento HTML con Plotly.js (CDN) embebido, listo para incrustar.
    """
    try:
        import plotly.graph_objects  # noqa: F401 — validación de instalación
        import plotly.io  # noqa: F401
    except ImportError:
        return _html_error("Plotly no instalado: pip install plotly")

    # ── Resolución del nombre del sensor ──────────────────────────────────────
    # Orden de prioridad: clave canónica resuelta → alias alternativos → error.
    sensor_name: str = (
        params.get("sensor")
        or params.get("sensores_1")
        or params.get("sensores")
        or ""
    )
    # Descartar el token literal si el motor no pudo resolverlo.
    if not sensor_name or sensor_name.startswith("$CURRENT"):
        return _html_error(
            "Sensor no configurado. Asigna un sensor primario en la Dispatch Table."
        )

    width_px = int(figsize[0] * 96)
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

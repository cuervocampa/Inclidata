"""KPI Cards de asentamiento — diseño L9-Modern Insights.

Genera tres tarjetas KPI en fila usando las clases CSS institucionales
``.kpi-card`` definidas en el motor HTML:

- **Cota** — valor de asentamiento actual (mm).
- **Tendencia** — velocidad reciente (mm/mes) con indicador de dirección.
- **Estado** — nivel de alerta (NORMAL / ATENCIÓ / PREAVÍS / NOTIFICACIÓ).

Función principal: ``generate(params, figsize) -> str``

Parámetros
----------
cota_actual : float, opcional
    Asentamiento acumulado actual en mm (default: 0).
tendencia_mm_mes : float, opcional
    Velocidad de asentamiento en mm/mes; positivo = hundimiento (default: 0).
umbral_atencion : float, opcional
    Umbral de Atención en mm (default: 10).
umbral_preaviso : float, opcional
    Umbral de Preavís en mm (default: 25).
umbral_notificacio : float, opcional
    Umbral de Notificació en mm (default: 40).
nombre_sensor : str, opcional
    ID del sensor para el subtítulo de la tarjeta Cota.
"""

from __future__ import annotations
from typing import Any
import html as _html_std


PARAMETER_METADATA: list[dict] = [
    {"nombre": "cota_actual",        "tipo": "numero", "requerido": False, "default": 0},
    {"nombre": "tendencia_mm_mes",   "tipo": "numero", "requerido": False, "default": 0},
    {"nombre": "umbral_atencion",    "tipo": "numero", "requerido": False, "default": 10},
    {"nombre": "umbral_preaviso",    "tipo": "numero", "requerido": False, "default": 25},
    {"nombre": "umbral_notificacio", "tipo": "numero", "requerido": False, "default": 40},
    {"nombre": "nombre_sensor",      "tipo": "texto",  "requerido": False},
]


# ── Helpers internos ──────────────────────────────────────────────────────────

def _safe_float(val: Any, default: float = 0.0) -> float:
    """Convierte a float ignorando strings de token no resueltos."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _estado(cota: float, u_aten: float, u_prev: float, u_noti: float) -> tuple[str, str, str]:
    """Calcula la etiqueta, color de texto y color de badge para el estado."""
    if cota >= u_noti:
        return "NOTIFICACIÓ", "#991B1B", "#FEE2E2"
    if cota >= u_prev:
        return "PREAVÍS",     "#DC2626", "#FEE2E2"
    if cota >= u_aten:
        return "ATENCIÓ",     "#D97706", "#FEF3C7"
    return "NORMAL",          "#059669", "#D1FAE5"


def _tendencia_icon(mm_mes: float) -> str:
    """Devuelve un carácter unicode indicador de dirección."""
    if mm_mes > 0.5:
        return "▲"
    if mm_mes < -0.5:
        return "▼"
    return "▶"


def _kpi_card(title: str, value_html: str, subtitle: str = "") -> str:
    """Genera el HTML de una tarjeta KPI individual usando las clases L9."""
    sub = f'<div class="kpi-subtitle">{_html_std.escape(subtitle)}</div>' if subtitle else ""
    return (
        f'<div class="kpi-card" style="flex:1;min-width:0;">'
        f'<div class="kpi-title">{_html_std.escape(title)}</div>'
        f'<div class="kpi-value">{value_html}</div>'
        f'{sub}'
        f'</div>'
    )


# ── Función principal ─────────────────────────────────────────────────────────

def generate(params: dict[str, Any], figsize: tuple[float, float]) -> str:
    """Genera las 3 tarjetas KPI y devuelve el fragmento HTML completo.

    El contenedor usa ``display:flex`` para distribuir las tarjetas en fila.
    Las clases CSS (``.kpi-card``, ``.kpi-title``, etc.) deben estar definidas
    en el documento padre — el motor HTML las inyecta automáticamente.

    Args:
        params:  Parámetros de configuración (ver ``PARAMETER_METADATA``).
        figsize: ``(ancho_pulgadas, alto_pulgadas)`` del contenedor (no usado
                 directamente — las tarjetas ocupan el 100 % disponible).

    Returns:
        Fragmento HTML con las 3 tarjetas en flex-row.
    """
    cota     = _safe_float(params.get("cota_actual"),        0.0)
    tend     = _safe_float(params.get("tendencia_mm_mes"),   0.0)
    u_aten   = _safe_float(params.get("umbral_atencion"),    10.0)
    u_prev   = _safe_float(params.get("umbral_preaviso"),    25.0)
    u_noti   = _safe_float(params.get("umbral_notificacio"), 40.0)
    sensor   = _html_std.escape(str(params.get("nombre_sensor") or ""))

    # ── Tarjeta 1: Cota ───────────────────────────────────────────────────────
    cota_fmt = f"{cota:.1f}"
    card_cota = _kpi_card(
        title="Cota actual",
        value_html=(
            f'<span style="font-size:23pt;font-weight:700;color:#111827;">{_html_std.escape(cota_fmt)}</span>'
            f'<span class="kpi-unit">mm</span>'
        ),
        subtitle=sensor if sensor else "Asentamiento acumulado",
    )

    # ── Tarjeta 2: Tendencia ──────────────────────────────────────────────────
    icon          = _tendencia_icon(tend)
    tend_color    = "#DC2626" if tend > 1.0 else ("#D97706" if tend > 0.3 else "#059669")
    tend_fmt      = f"{abs(tend):.2f}"
    card_tendencia = _kpi_card(
        title="Tendencia",
        value_html=(
            f'<span style="font-size:23pt;font-weight:700;color:{tend_color};">'
            f'{icon} {_html_std.escape(tend_fmt)}</span>'
            f'<span class="kpi-unit">mm/mes</span>'
        ),
        subtitle="Velocidad reciente",
    )

    # ── Tarjeta 3: Estado ─────────────────────────────────────────────────────
    label, text_color, bg_color = _estado(cota, u_aten, u_prev, u_noti)
    card_estado = _kpi_card(
        title="Estado",
        value_html=(
            f'<span class="kpi-badge" style="background:{bg_color};color:{text_color};">'
            f'{_html_std.escape(label)}</span>'
        ),
        subtitle=f"Umbral atenció: {u_aten:.0f} mm",
    )

    # ── Contenedor en fila ────────────────────────────────────────────────────
    return (
        '<div style="display:flex;flex-direction:row;gap:0.5cm;'
        'width:100%;height:100%;align-items:stretch;'
        'padding:0.2cm 0;box-sizing:border-box;">'
        + card_cota
        + card_tendencia
        + card_estado
        + "</div>"
    )

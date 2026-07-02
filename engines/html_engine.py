"""Motor HTML/Playwright — generación de informes PDF via renderizado web.

Convierte la plantilla JSON en un documento HTML con elementos posicionados
absolutamente (unidades CSS ``cm``) y usa Playwright (Chromium headless) para
generar el PDF final con ``print_background=True``.

Características:
- Gráficos Plotly interactivos (renderizados estáticamente en PDF).
- Tipografía web avanzada (web fonts, CSS completo).
- Soporte nativo de orientaciones mixtas por página (CSS ``@page`` named pages).

Requiere::

    pip install playwright plotly
    playwright install chromium

Scripts de gráficos:
    Deben estar en ``biblioteca_graficos/html/`` y exponer una función
    ``generate(params: dict, figsize: tuple) -> str`` que devuelva un
    fragmento HTML embebible (sin ``<html>`` ni ``<body>``).

Clase principal::

    HTMLEngine(BaseReportEngine)
"""

import base64
import html as _html_std
import importlib.util
import inspect
import json
import logging
import re as _re
import sys
import tempfile
import threading
import time
from datetime import datetime as _dt, timezone
from pathlib import Path
from typing import Any

from engines.base import BaseReportEngine
from utils.cell_function_registry import get_function as _get_cell_fn
from utils.template_service import _encontrar_json_plantilla, cargar_plantilla

logger = logging.getLogger(__name__)

_PROJECT_ROOT    = Path(__file__).parent.parent
_GRAFICOS_ROOT   = _PROJECT_ROOT / "biblioteca_graficos"   # raíz — para rutas con namespace
_GRAFICOS_HTML   = _GRAFICOS_ROOT / "html"                 # primario para el motor HTML
_GRAFICOS_LEGACY = _GRAFICOS_ROOT                          # fallback: scripts sin subcarpeta
_TABLAS_HTML     = _PROJECT_ROOT / "biblioteca_tablas" / "html"  # tablas HTML
_TABLAS_ROOT     = _PROJECT_ROOT / "biblioteca_tablas"           # raíz de tablas

# Mapeo de tokens $CURRENT_* a claves del context del informe
_CURRENT_TOKEN_MAP: dict[str, str] = {
    "$CURRENT_fecha_fin":          "fecha_final",
    "$CURRENT_fecha_final":        "fecha_final",
    "$CURRENT_fecha_inicial":      "fecha_inicial",
    "$CURRENT_fecha_seleccionada": "fecha_seleccionada",
    "$CURRENT_ultimas_camp":       "ultimas_camp",
    "$CURRENT":                    "sensor",
}

# Parámetros primarios de contexto que son dinámicos por diseño ($CURRENT).
# custom_chart_settings nunca debe sobrescribirlos: su valor correcto siempre
# viene de _resolve_params → _ctx_lookup en el momento del render.
_DYNAMIC_CTX_PARAMS: frozenset[str] = frozenset({
    "sensor", "sensores", "sensores_1",
    "fecha_inicio", "fecha_fin", "fecha_inicial", "fecha_final",
    "fecha_seleccionada",
})

# ── Estilos institucionales L9-Modern Insights ────────────────────────────────
# Incluidos en el <head> de todo documento generado por el motor HTML.
# Los scripts de biblioteca_graficos/html/ y biblioteca_tablas/html/ pueden
# usar estas clases libremente sin redefinirlas.
_L9_STYLES_CSS = """
/* ── L9-Modern Insights — Institutional Design System ─── */
.header-clean {
  height: 80px; background: white; border-bottom: 2px solid #E5E7EB;
  display: flex; align-items: center; padding: 0 24px;
  font-family: Arial, sans-serif;
}
.kpi-card {
  background: white; border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.09), 0 1px 2px rgba(0,0,0,0.06);
  padding: 12px 18px 10px; display: flex; flex-direction: column; gap: 3px;
}
.kpi-title {
  font-size: 8pt; color: #6B7280; font-weight: 600;
  font-family: Arial, sans-serif; text-transform: uppercase; letter-spacing: .05em;
}
.kpi-value {
  font-size: 23pt; font-weight: 700; color: #111827;
  font-family: Arial, sans-serif; line-height: 1.1;
}
.kpi-unit  { font-size: 11pt; font-weight: 400; color: #6B7280; margin-left: 2px; }
.kpi-subtitle { font-size: 7.5pt; color: #9CA3AF; font-family: Arial, sans-serif; }
.kpi-badge {
  display: inline-block; padding: 2px 8px; border-radius: 99px;
  font-size: 7.5pt; font-weight: 700; font-family: Arial, sans-serif;
}
.modern-table {
  width: 100%; border-collapse: collapse;
  font-family: Arial, sans-serif; font-size: 9pt;
}
.modern-table th {
  border-bottom: 2px solid #E5E7EB; padding: 8px 12px;
  text-align: left; font-weight: 600; color: #374151;
  background: transparent; white-space: nowrap;
}
.modern-table td { border-bottom: 1px solid #F3F4F6; padding: 6px 12px; color: #374151; }
.modern-table tr:last-child td { border-bottom: none; }
.modern-table .numeric {
  font-family: 'Courier New', Courier, monospace; text-align: right; font-size: 8.5pt;
}
.alert-orange { color: #D97706; font-weight: 600; }
.alert-red    { color: #DC2626; font-weight: 700; }
.footer-ute {
  background: #F3F4F6; padding: 6px 20px;
  display: flex; align-items: center; justify-content: space-between;
  border-top: 1px solid #E5E7EB; width: 100%; height: 100%; box-sizing: border-box;
}
.footer-ute img { height: 22px; filter: grayscale(100%) opacity(60%); }
.footer-text { font-size: 7pt; color: #9CA3AF; font-family: Arial, sans-serif; }
"""

# Dimensiones A4 en cm
_A4_PORTRAIT_W  = 21.0
_A4_PORTRAIT_H  = 29.7
_A4_LANDSCAPE_W = 29.7
_A4_LANDSCAPE_H = 21.0

# Conversión cm → px (96 dpi: 1 in = 96 px, 1 in = 2.54 cm)
_CM_TO_PX = 37.8

# ── Log de ejecución por hilo ─────────────────────────────────────────────────

_tl = threading.local()


def _emit_log(hito: str, **data: object) -> None:
    """Añade una entrada al log del hilo actual. No-op si no hay log activo."""
    log: list | None = getattr(_tl, "execution_log", None)
    if log is not None:
        log.append({"hito": hito, "ts": _dt.now(timezone.utc).isoformat(), **data})


# ── Helpers de dimensión ──────────────────────────────────────────────────────

def _page_dims(page_data: dict) -> tuple[float, float]:
    """Devuelve ``(ancho_cm, alto_cm)`` según la orientación de la página."""
    ori = (page_data.get("configuracion") or {}).get("orientacion", "portrait")
    if ori == "landscape":
        return _A4_LANDSCAPE_W, _A4_LANDSCAPE_H
    return _A4_PORTRAIT_W, _A4_PORTRAIT_H


# ── Resolución de assets ──────────────────────────────────────────────────────

def _to_file_uri(path: Path) -> str:
    """Convierte un ``Path`` absoluto a URI ``file:///`` para Chromium."""
    return path.resolve().as_uri()


def _resolve_asset(ruta: str | None, plantilla_dir: Path) -> str | None:
    """Resuelve una ruta de asset relativa a una URI ``file:///`` absoluta.

    Prueba en orden:
    1. ``plantilla_dir / ruta`` (canónica: ``assets/logo.png``).
    2. ``ruta`` como ruta absoluta del sistema.

    Devuelve ``None`` y registra un *warning* si no se encuentra el archivo.
    No bloquea el renderizado — el llamador muestra un *placeholder*.
    """
    if not ruta:
        return None
    candidate = plantilla_dir / ruta
    if candidate.is_file():
        return _to_file_uri(candidate)
    abs_path = Path(ruta)
    if abs_path.is_absolute() and abs_path.is_file():
        return _to_file_uri(abs_path)
    logger.warning("[HTML] Asset no encontrado: '%s' (base: %s)", ruta, plantilla_dir)
    return None


# ── Token y CSS helpers ───────────────────────────────────────────────────────

def _normalize_context(context: dict) -> dict:
    """Añade alias planos al contexto para que ``{{token}}`` funcione en textos.

    Reglas:
    - ``nombre_sensor`` → ``context["sensores_1"]`` o ``context["info"]["nom_sensor"]``
      (solo si la clave no existe ya a nivel raíz).
    - Cualquier otro valor ya presente en el contexto permanece sin modificación.
    """
    extra: dict = {}
    if "nombre_sensor" not in context:
        extra["nombre_sensor"] = (
            context.get("sensores_1")
            or (context.get("info") or {}).get("nom_sensor")
            or ""
        )
    if extra:
        return {**context, **extra}
    return context


def _resolve_tokens(text: str, context: dict) -> str:
    """Reemplaza tokens ``{{key}}`` en el texto con valores del contexto.

    Además de los tokens normales ``{{key}}``, resuelve los tokens dinámicos
    ``{{$CURRENT}}``, ``{{$CURRENT_fecha_fin}}``, etc. via ``_ctx_lookup``.
    """
    for k, v in context.items():
        if isinstance(v, (str, int, float)):
            text = text.replace(f"{{{{{k}}}}}", str(v))
    for token, ctx_key in _CURRENT_TOKEN_MAP.items():
        placeholder = f"{{{{{token}}}}}"
        if placeholder in text:
            val = _ctx_lookup(ctx_key, context)
            if val is not None:
                text = text.replace(placeholder, str(val))
    return text


def _css_color(color: str | None, default: str = "transparent") -> str:
    """Devuelve un color CSS válido o ``default`` si es nulo/vacío."""
    if not color or color.lower() in ("", "none", "transparent"):
        return default
    return color


def _opacity(estilo: dict) -> float:
    """Normaliza la opacidad al rango 0.0–1.0."""
    raw = estilo.get("opacidad", estilo.get("opacity", 100))
    val = float(raw if raw is not None else 100)
    return val / 100.0 if val > 1.0 else val


# ── Renderizadores de elementos HTML ─────────────────────────────────────────

def _elem_rect(elem: dict) -> str:
    """Genera el HTML de un elemento ``rectangulo``."""
    geo = elem.get("geometria") or {}
    est = elem.get("estilo") or {}
    x, y = float(geo.get("x", 0)), float(geo.get("y", 0))
    w, h = float(geo.get("ancho", 1)), float(geo.get("alto", 1))
    bg      = _css_color(
        est.get("color_relleno") or est.get("color_fondo")
        or est.get("backgroundColor") or est.get("background_color")
    )
    bc      = _css_color(
        est.get("color_borde") or est.get("borderColor")
        or est.get("border_color"), "transparent"
    )
    bw      = float(
        est.get("grosor_borde") or est.get("borderWidth")
        or est.get("border_width") or 0
    )
    radius  = float(est.get("radio_borde") or est.get("border_radius") or 0)
    opacity = _opacity(est)
    border  = f"{bw}pt solid {bc}" if bw > 0 else "none"
    return (
        f'<div style="position:absolute;left:{x}cm;top:{y}cm;'
        f'width:{w}cm;height:{h}cm;background:{bg};border:{border};'
        f'border-radius:{radius}pt;opacity:{opacity};box-sizing:border-box;"></div>'
    )


def _elem_linea(elem: dict) -> str:
    """Genera el HTML de un elemento ``linea`` o ``linea_horizontal``.

    Soporta dos modelos:
    - Nuevo (configuracion.x1/y1/x2/y2): coordenadas absolutas de inicio y fin.
    - Legado (geometria.ancho/alto): vector desde (x,y), mantenido por compatibilidad.
    """
    import math as _m  # noqa: PLC0415
    geo = elem.get("geometria") or {}
    est = elem.get("estilo") or {}
    cfg = elem.get("configuracion") or {}

    # ── Coordenadas ──────────────────────────────────────────────────────────
    if "x1" in cfg and "x2" in cfg:
        x1 = float(cfg["x1"]); y1 = float(cfg["y1"])
        x2 = float(cfg["x2"]); y2 = float(cfg["y2"])
        dx = x2 - x1; dy = y2 - y1
        ox, oy = x1, y1
    else:
        ox = float(geo.get("x", 0)); oy = float(geo.get("y", 0))
        dx = float(geo.get("ancho", 5)); dy = float(geo.get("alto", 0))

    # ── Estilo ───────────────────────────────────────────────────────────────
    color   = _css_color(cfg.get("color") or est.get("color_borde") or est.get("color"), "#000000")
    bw      = float(cfg.get("grosor") or est.get("grosor_borde") or est.get("border_width") or 1)
    opacity = _opacity(est)

    estilo_linea = cfg.get("estilo_linea", "solida")
    dash_map = {
        "discontinua": "8 4",
        "punteada":    "2 3",
    }
    dash = dash_map.get(estilo_linea)

    # ── Render ───────────────────────────────────────────────────────────────
    length = _m.hypot(dx, dy) or abs(dx) or 1
    angle  = _m.degrees(_m.atan2(dy, dx)) if (dx or dy) else 0

    if dash:
        svg_h = max(bw + 2, 4)
        return (
            f'<div style="position:absolute;left:{ox}cm;top:{oy}cm;'
            f'width:{length:.4f}cm;height:{svg_h}px;overflow:visible;'
            f'transform-origin:0 50%;transform:rotate({angle:.4f}deg);opacity:{opacity};">'
            f'<svg width="100%" height="{svg_h}" xmlns="http://www.w3.org/2000/svg" overflow="visible">'
            f'<line x1="0" y1="{svg_h/2:.1f}" x2="100%" y2="{svg_h/2:.1f}" '
            f'stroke="{color}" stroke-width="{bw}" stroke-dasharray="{dash}" />'
            f'</svg></div>'
        )

    return (
        f'<div style="position:absolute;left:{ox}cm;top:{oy}cm;'
        f'width:{length:.4f}cm;height:0;'
        f'border-top:{bw}pt solid {color};opacity:{opacity};'
        f'transform-origin:0 50%;transform:rotate({angle:.4f}deg);"></div>'
    )


def _elem_texto(elem: dict, context: dict) -> str:
    """Genera el HTML de un elemento ``texto`` con resolución de tokens."""
    geo = elem.get("geometria") or {}
    est = elem.get("estilo") or {}
    con = elem.get("contenido") or {}
    x, y = float(geo.get("x", 0)), float(geo.get("y", 0))
    w, h = float(geo.get("ancho", 5)), float(geo.get("alto", 1))

    raw_text = str(con.get("texto") or con.get("text") or est.get("label") or "")

    # Override si el elemento es editable y hay valor en el contexto
    elem_id = elem.get("id", "")
    if elem.get("editable") and elem_id:
        _modo_cfg = (context.get("textos_editables_modo") or {}).get(elem_id) or {}
        if _modo_cfg.get("modo") == "columna" and _modo_cfg.get("col"):
            _col_val = context.get(_modo_cfg["col"], "")
            if isinstance(_col_val, (list, tuple)):
                _col_val = ", ".join(str(x) for x in _col_val)
            raw_text = str(_col_val)
        else:
            texto_override = context.get("textos_editables", {}).get(elem_id)
            if texto_override is not None:
                raw_text = texto_override

    # Inyectar token→columna para tokens {{param}} mapeados en dispatch table
    _tok_map = (context.get("texto_param_mapping") or {}).get(elem_id, {})
    _ctx_texto = (
        {**context, **{tok: context.get(col, "") for tok, col in _tok_map.items() if col}}
        if _tok_map else context
    )
    text     = _resolve_tokens(raw_text, _ctx_texto)
    escaped  = _html_std.escape(text).replace("\n", "<br>")

    fs      = float(est.get("tamano") or est.get("font_size") or est.get("fontSize") or 10)
    color   = _css_color(est.get("font_color") or est.get("color"), "#000000")
    family  = est.get("font_family") or est.get("fontFamily") or "Arial, sans-serif"
    weight  = est.get("font_weight") or est.get("fontWeight") or "normal"
    align   = est.get("text_align") or est.get("textAlign") or "left"
    bg      = _css_color(est.get("background_color") or est.get("color_fondo"))
    opacity = _opacity(est)
    return (
        f'<div style="position:absolute;left:{x}cm;top:{y}cm;width:{w}cm;height:{h}cm;'
        f'font-size:{fs}pt;color:{color};font-family:{family};font-weight:{weight};'
        f'text-align:{align};background:{bg};opacity:{opacity};overflow:hidden;'
        f'display:flex;align-items:center;box-sizing:border-box;padding:2px;">'
        f'{escaped}</div>'
    )


def _elem_imagen(elem: dict, plantilla_dir: Path) -> str:
    """Genera el HTML de un elemento ``imagen`` con ruta file:/// absoluta."""
    geo = elem.get("geometria") or {}
    img = elem.get("imagen") or {}
    img_cfg = elem.get("imagen_config") or {}
    x, y = float(geo.get("x", 0)), float(geo.get("y", 0))
    w, h = float(geo.get("ancho", 5)), float(geo.get("alto", 3))

    posicion = img_cfg.get("posicion", "center")
    ajuste   = img_cfg.get("ajuste", "contain")
    _pos_map = {
        "center": "center", "top": "top center", "bottom": "bottom center",
        "left": "center left", "right": "center right",
    }
    object_position = _pos_map.get(posicion, "center")

    ruta = (
        img.get("ruta_nueva")
        or img.get("ruta")
        or (elem.get("contenido") or {}).get("src")
    )
    file_uri = _resolve_asset(ruta, plantilla_dir)

    if not file_uri:
        safe_ruta = _html_std.escape(ruta or "")
        return (
            f'<div style="position:absolute;left:{x}cm;top:{y}cm;width:{w}cm;height:{h}cm;'
            f'border:1px dashed #bbb;display:flex;align-items:center;justify-content:center;'
            f'font-size:7pt;color:#bbb;">[imagen: {safe_ruta}]</div>'
        )
    return (
        f'<img style="position:absolute;left:{x}cm;top:{y}cm;'
        f'width:{w}cm;height:{h}cm;object-fit:{ajuste};object-position:{object_position};" src="{file_uri}" alt="">'
    )


_IMAGES_DIR = _PROJECT_ROOT / "images"


def _elem_imagen_dinamica(elem: dict, context: dict, plantilla_dir: Path) -> str:
    """Genera el HTML de un elemento imagen en modo dinámico.

    Lee el nombre de archivo desde ``context["imagenes_dinamicas"][elem_id]``
    y busca el archivo en ``images/``. Si no existe renderiza un marco
    de advertencia sin lanzar excepción.
    """
    import html as _html_std2
    geo = elem.get("geometria") or {}
    img_cfg = elem.get("imagen_config") or {}
    elem_id = elem.get("id") or ""

    x = float(geo.get("x", 0))
    y = float(geo.get("y", 0))
    w = float(geo.get("ancho", 5))
    h = float(geo.get("alto", 3))

    _overrides = (context.get("imagen_config_overrides") or {}).get(elem_id, {})
    if _overrides:
        marco = {**img_cfg.get("marco", {}), **{
            k: _overrides[k] for k in ("borde_ancho", "borde_color", "borde_radio", "fondo")
            if k in _overrides
        }}
        posicion = _overrides.get("posicion") or img_cfg.get("posicion", "center")
        ajuste   = _overrides.get("ajuste")   or img_cfg.get("ajuste", "contain")
    else:
        marco    = img_cfg.get("marco") or {}
        posicion = img_cfg.get("posicion", "center")
        ajuste   = img_cfg.get("ajuste", "contain")

    borde_ancho = float(marco.get("borde_ancho", 0))
    borde_color = marco.get("borde_color", "#e2e8f0")
    borde_radio = float(marco.get("borde_radio", 0))
    fondo       = marco.get("fondo", "transparent")

    border_css = (
        f"{borde_ancho}pt solid {borde_color}" if borde_ancho > 0 else "none"
    )

    # Posición CSS: mapear a object-position
    _pos_map = {
        "center": "center", "top": "top center", "bottom": "bottom center",
        "left": "center left", "right": "center right",
    }
    object_position = _pos_map.get(posicion, "center")

    base_style = (
        f"position:absolute;left:{x}cm;top:{y}cm;width:{w}cm;height:{h}cm;"
        f"border:{border_css};border-radius:{borde_radio}pt;"
        f"background:{fondo};overflow:hidden;"
        f"display:flex;align-items:center;justify-content:center;"
    )

    nombre_imagen: str = (
        (context.get("imagenes_dinamicas") or {}).get(elem_id) or ""
    )
    if not nombre_imagen:
        return (
            f'<div style="{base_style}font-size:7pt;color:#aaa;">'
            f'[Sin imagen asignada]</div>'
        )

    img_path = _IMAGES_DIR / nombre_imagen
    if not img_path.is_file():
        logger.warning("[HTML] Imagen dinámica no encontrada: %s", img_path)
        safe = _html_std2.escape(nombre_imagen)
        return (
            f'<div style="{base_style}font-size:7pt;color:#e53;">'
            f'[Imagen no encontrada: {safe}]</div>'
        )

    file_uri = img_path.as_uri()
    return (
        f'<div style="{base_style}">'
        f'<img src="{file_uri}" '
        f'style="width:100%;height:100%;object-fit:{ajuste};'
        f'object-position:{object_position};" alt="">'
        f'</div>'
    )


def _elem_sinoptico(elem: dict, context: dict, plantilla_dir: Path) -> str:
    """Genera el HTML de un elemento ``sinoptico``.

    Marco + imagen de fondo (estática o dinámica) + etiquetas de texto/sensor
    posicionadas en coordenadas locales normalizadas 0-1.

    Contrato de datos del elemento::

        sinoptico_config = {
            "imagen": {"modo": str, "opacidad_fondo": float, "posicion": str, "ajuste": str},
            "marco":  {"borde_ancho": float, "borde_color": str, "borde_radio": float, "fondo": str},
            "sensores":        str,    # CSV de sensores; "$CURRENT" se resuelve del context
            "paleta_sensores": str,    # "modern" | "corporate" | "vibrant"
            "paleta_alarma":   str,    # "semaforo" | "semaforo_morado"
        }

    El context puede aportar (canal de etiquetas)::

        context["sinopticos"][elem_id] = {
            "etiquetas": [
                {"id": str, "tipo": "texto",  "x": float, "y": float,
                 "contenido": str, "formato": {"tamano", "color", "negrita", "fondo", "borde_color"}},
                {"id": str, "tipo": "sensor", "x": float, "y": float,
                 "sensor": str, "mostrar": list, "funcion_valor": str,
                 "decimales": int, "formato": {...}},
            ],
        }

    Los overrides de campos secundarios (opacidad_fondo, posicion, ajuste,
    paleta_sensores, paleta_alarma) usan el canal genérico compartido::

        context["custom_chart_settings"][elem_id] = {"campo": valor, ...}

    Si no hay entrada en context, renderiza solo marco + imagen (estado válido
    previo a la configuración desde el modal del dispatch).

    Las etiquetas usan ``transform:translate(-50%,-50%)`` (ancla CENTRADA);
    el editor JS del modal usa la misma ancla para coherencia visual PDF=preview.

    Regla de falsy: solo ``None`` indica ausencia.
    ``False``, ``0`` y ``""`` son valores válidos (relevante en ``opacidad_fondo=0``).
    """
    geo     = elem.get("geometria") or {}
    sin_cfg = elem.get("sinoptico_config") or {}
    img_cfg = sin_cfg.get("imagen") or {}
    marco   = sin_cfg.get("marco") or {}
    elem_id = elem.get("id") or ""

    x = float(geo.get("x", 0))
    y = float(geo.get("y", 0))
    w = float(geo.get("ancho", 15))
    h = float(geo.get("alto", 10))

    # ── Overrides vía custom_chart_settings (canal genérico compartido con gráficos/tablas/mapas) ──
    entrada    = (context.get("sinopticos") or {}).get(elem_id) or {}
    _overrides = ((context.get("custom_chart_settings") or {}).get(elem_id) or {})

    # Merge selectivo campo a campo — "campo in _overrides", nunca truthiness
    _opacidad_raw   = img_cfg.get("opacidad_fondo")
    opacidad_fondo  = (
        float(_overrides["opacidad_fondo"]) if "opacidad_fondo" in _overrides
        else (float(_opacidad_raw) if _opacidad_raw is not None else 1.0)
    )
    posicion        = _overrides["posicion"]        if "posicion"        in _overrides else img_cfg.get("posicion", "center")
    ajuste          = _overrides["ajuste"]          if "ajuste"          in _overrides else img_cfg.get("ajuste", "contain")
    paleta_sensores = _overrides["paleta_sensores"] if "paleta_sensores" in _overrides else str(sin_cfg.get("paleta_sensores") or "modern")
    paleta_alarma   = _overrides["paleta_alarma"]   if "paleta_alarma"   in _overrides else str(sin_cfg.get("paleta_alarma")   or "semaforo")

    # ── Marco (contenedor principal) ─────────────────────────────────────────
    borde_ancho = float(marco.get("borde_ancho", 0))
    borde_color = marco.get("borde_color", "#e2e8f0")
    borde_radio = float(marco.get("borde_radio", 0))
    fondo       = marco.get("fondo", "transparent")
    border_css  = f"{borde_ancho}pt solid {borde_color}" if borde_ancho > 0 else "none"

    contenedor_style = (
        f"position:absolute;left:{x}cm;top:{y}cm;width:{w}cm;height:{h}cm;"
        f"border:{border_css};border-radius:{borde_radio}pt;"
        f"background:{fondo};overflow:hidden;"
    )

    # ── Imagen de fondo (z-index 0, posición absoluta inset:0) ───────────────
    _pos_map = {
        "center": "center", "top": "top center", "bottom": "bottom center",
        "left": "center left", "right": "center right",
    }
    object_position = _pos_map.get(posicion, "center")
    img_style_base = (
        f"position:absolute;inset:0;width:100%;height:100%;"
        f"object-fit:{ajuste};object-position:{object_position};"
        f"opacity:{opacidad_fondo};"
    )

    modo = img_cfg.get("modo", "estatica")
    if modo == "dinamica":
        nombre_imagen: str = (context.get("imagenes_dinamicas") or {}).get(elem_id) or ""
        if not nombre_imagen:
            img_html = (
                '<div style="position:absolute;inset:0;display:flex;align-items:center;'
                'justify-content:center;font-size:7pt;color:#aaa;">'
                '[Sin imagen asignada]</div>'
            )
        else:
            img_path = _IMAGES_DIR / nombre_imagen
            if not img_path.is_file():
                logger.warning("[HTML] _elem_sinoptico: imagen dinámica no encontrada: %s", img_path)
                safe = _html_std.escape(nombre_imagen)
                img_html = (
                    f'<div style="position:absolute;inset:0;display:flex;align-items:center;'
                    f'justify-content:center;font-size:7pt;color:#e53;">'
                    f'[Imagen no encontrada: {safe}]</div>'
                )
            else:
                if context.get("_inline_images"):
                    try:
                        _img_data = img_path.read_bytes()
                        if len(_img_data) > 10 * 1024 * 1024:
                            logger.warning(
                                "[HTML] _elem_sinoptico: imagen '%s' > 10 MB, se mantiene file://",
                                img_path.name,
                            )
                            _img_src = img_path.as_uri()
                        else:
                            import base64 as _b64  # noqa: PLC0415
                            _sfx = img_path.suffix.lower()
                            _mime_map = {
                                ".png": "image/png", ".jpg": "image/jpeg",
                                ".jpeg": "image/jpeg", ".gif": "image/gif",
                                ".webp": "image/webp", ".svg": "image/svg+xml",
                            }
                            _mime = _mime_map.get(_sfx, "image/png")
                            _img_src = "data:{};base64,{}".format(
                                _mime, _b64.b64encode(_img_data).decode()
                            )
                    except Exception:
                        logger.warning(
                            "[HTML] _elem_sinoptico: no se pudo inlinear '%s', usando file://",
                            img_path.name,
                        )
                        _img_src = img_path.as_uri()
                else:
                    _img_src = img_path.as_uri()
                img_html = f'<img id="sinoptico-bg-img" src="{_img_src}" style="{img_style_base}" alt="">'
    else:
        # Modo estático: ruta desde sinoptico_config.imagen o contenido.src
        ruta = (
            img_cfg.get("ruta_nueva")
            or img_cfg.get("ruta")
            or (elem.get("contenido") or {}).get("src")
        )
        file_uri = _resolve_asset(ruta, plantilla_dir)
        if not file_uri:
            img_html = (
                '<div style="position:absolute;inset:0;display:flex;align-items:center;'
                'justify-content:center;font-size:7pt;color:#bbb;">'
                '[Sinóptico: sin imagen]</div>'
            )
        else:
            if context.get("_inline_images") and file_uri.startswith("file:"):
                try:
                    import urllib.parse as _urlp, base64 as _b64  # noqa: PLC0415
                    _fpath = Path(_urlp.unquote(_urlp.urlparse(file_uri).path))
                    if _fpath.is_file():
                        _img_data = _fpath.read_bytes()
                        if len(_img_data) <= 10 * 1024 * 1024:
                            _sfx = _fpath.suffix.lower()
                            _mime_map = {
                                ".png": "image/png", ".jpg": "image/jpeg",
                                ".jpeg": "image/jpeg", ".gif": "image/gif",
                                ".webp": "image/webp", ".svg": "image/svg+xml",
                            }
                            _mime = _mime_map.get(_sfx, "image/png")
                            file_uri = "data:{};base64,{}".format(
                                _mime, _b64.b64encode(_img_data).decode()
                            )
                        else:
                            logger.warning(
                                "[HTML] _elem_sinoptico: imagen estática > 10 MB, se mantiene file://",
                            )
                except Exception:
                    logger.warning(
                        "[HTML] _elem_sinoptico: no se pudo inlinear imagen estática '%s'", file_uri,
                    )
            img_html = f'<img id="sinoptico-bg-img" src="{file_uri}" style="{img_style_base}" alt="">'

    # ── Resolución de sensores ────────────────────────────────────────────────
    params_sens  = _resolve_params({"sensores": sin_cfg.get("sensores")}, context, elem_id=elem_id)
    sensores_raw = params_sens.get("sensores") or ""
    lista_sensores: list[str] = [
        t.strip() for t in _re.split(r"[,;\r\n]+", str(sensores_raw)) if t.strip()
    ]

    from utils.sensor_palette import asignar_colores_sensores  # noqa: PLC0415
    mapa_colores: dict[str, str] = (
        asignar_colores_sensores(lista_sensores, paleta_sensores) if lista_sensores else {}
    )

    # ── Datos de sensor (solo si hay etiquetas tipo "sensor") ─────────────────
    etiquetas: list[dict] = entrada.get("etiquetas") or []
    historico: list[dict] = []
    ultimos_valores: dict[str, float | None] = {}
    ultima_fecha_por_sensor: dict[str, str] = {}
    umbrales_por_sensor: dict[str, dict] = {}

    # Sensores adicionales de etiquetas vector (pueden no estar en lista_sensores del sinóptico)
    _sensores_vector_extra: list[str] = []
    for _ev in etiquetas:
        if _ev.get("tipo") == "vector":
            for _campo in ("sensor_x", "sensor_y"):
                _sn_v = str(_ev.get(_campo) or "").strip()
                if _sn_v and _sn_v not in lista_sensores and _sn_v not in _sensores_vector_extra:
                    _sensores_vector_extra.append(_sn_v)

    primeros_valores: dict[str, float | None] = {}
    hay_etiquetas_sensor = any(e.get("tipo") in ("sensor", "vector") for e in etiquetas)
    if hay_etiquetas_sensor:
        try:
            from core.data_fetcher import fetch_temporal_data, fetch_umbrales_sensores  # noqa: PLC0415
            from utils.gis_client import _orm_server_to_config  # noqa: PLC0415
            import pandas as _pd  # noqa: PLC0415
            _orm_server = context.get("_server")
            if _orm_server is not None:
                _server_cfg  = _orm_server_to_config(_orm_server)
                sensores_csv = ",".join(lista_sensores + _sensores_vector_extra)
                fecha_ini    = context.get("fecha_inicio") or context.get("fecha_inicial") or ""
                fecha_fin    = context.get("fecha_fin")    or context.get("fecha_final")    or ""
                _result      = fetch_temporal_data(_server_cfg, sensores_csv, fecha_ini, fecha_fin)
                historico    = _result.get("historico") or []
                if historico:
                    _df_hist = _pd.DataFrame(historico)
                    if "NOM_SENSOR" in _df_hist.columns and "MEDIDA" in _df_hist.columns:
                        for _sn, _grp in _df_hist.groupby("NOM_SENSOR"):
                            try:
                                ultimos_valores[str(_sn)] = float(_grp["MEDIDA"].iloc[-1])
                            except (ValueError, TypeError, IndexError):
                                ultimos_valores[str(_sn)] = None
                            try:
                                primeros_valores[str(_sn)] = float(_grp["MEDIDA"].iloc[0])
                            except (ValueError, TypeError, IndexError):
                                primeros_valores[str(_sn)] = None
                    if "NOM_SENSOR" in _df_hist.columns and "FECHA" in _df_hist.columns:
                        for _sn, _grp in _df_hist.groupby("NOM_SENSOR"):
                            try:
                                ultima_fecha_por_sensor[str(_sn)] = str(_grp["FECHA"].iloc[-1])
                            except (ValueError, TypeError, IndexError):
                                ultima_fecha_por_sensor[str(_sn)] = ""
                _df_umb = fetch_umbrales_sensores(_server_cfg, lista_sensores)
                if not _df_umb.empty and "NOM_SENSOR" in _df_umb.columns:
                    for _, _fila in _df_umb.iterrows():
                        umbrales_por_sensor[str(_fila["NOM_SENSOR"])] = _fila.to_dict()
            else:
                logger.warning(
                    "[HTML] _elem_sinoptico: etiquetas sensor activas pero "
                    "context['_server'] vacío; datos de sensor deshabilitados para elem=%s",
                    elem_id,
                )
        except Exception:
            logger.exception(
                "[HTML] _elem_sinoptico: fallo obteniendo histórico/umbrales; "
                "se continúa sin datos de sensor"
            )

    from utils.alarma_sensor import evaluar_nivel_alarma  # noqa: PLC0415
    from utils.alarma_palette import color_para_nivel    # noqa: PLC0415

    # ── Mapa de fuentes tipográficas (compartido texto / forma-texto) ────────
    _FF_MAP_SIN: dict[str, str] = {
        "arial":     "Arial, sans-serif",
        "helvetica": '"Helvetica Neue", Helvetica, Arial, sans-serif',
        "verdana":   "Verdana, Geneva, sans-serif",
        "tahoma":    "Tahoma, Geneva, sans-serif",
        "calibri":   "Calibri, Candara, Segoe, 'Segoe UI', Optima, Arial, sans-serif",
        "trebuchet": '"Trebuchet MS", Helvetica, sans-serif',
        "georgia":   'Georgia, "Times New Roman", Times, serif',
        "times":     '"Times New Roman", Times, serif',
        "courier":   '"Courier New", Courier, monospace',
        "sans":      "Helvetica, Arial, sans-serif",
        "serif":     'Georgia, "Times New Roman", serif',
        "mono":      '"Courier New", monospace',
    }

    # ── Render de etiquetas (z-index 1, encima de imagen) ─────────────────────
    etiquetas_html_parts: list[str] = []
    vector_svg_parts: list[str] = []
    for etiqueta in etiquetas:
        tipo_et = etiqueta.get("tipo")
        ex      = float(etiqueta.get("x", 0))
        ey      = float(etiqueta.get("y", 0))
        fmt     = etiqueta.get("formato") or {}
        pos_style = (
            f"position:absolute;left:{ex * 100:.2f}%;top:{ey * 100:.2f}%;"
            f"transform:translate(-50%,-50%);z-index:1;"
        )

        if tipo_et == "texto":
            et_id      = _html_std.escape(str(etiqueta.get("id") or ""))
            contenido  = _html_std.escape(str(etiqueta.get("contenido") or ""))
            font_size  = fmt.get("tamano", 9)
            color      = fmt.get("color", "#1e293b")
            weight     = "bold" if fmt.get("negrita") else "normal"
            bg         = fmt.get("fondo") or "transparent"
            _borde_flag = fmt.get("borde")
            _borde_col_et = fmt.get("borde_color") or "#cbd5e1"
            if _borde_flag is not None:
                borde_et = f"1px solid {_borde_col_et}" if _borde_flag else "none"
            else:
                borde_et = f"1px solid {_borde_col_et}" if fmt.get("borde_color") else "none"
            font_family_t = _FF_MAP_SIN.get(str(fmt.get("fuente") or "sans"), "Helvetica, Arial, sans-serif")
            font_style_t  = "italic" if fmt.get("cursiva") else "normal"
            et_style = (
                f"{pos_style}font-size:{font_size}pt;color:{color};"
                f"font-weight:{weight};font-style:{font_style_t};"
                f"font-family:{font_family_t};background:{bg};border:{borde_et};"
                f"white-space:nowrap;"
            )
            etiquetas_html_parts.append(
                f'<div data-etiqueta-id="{et_id}" data-x="{ex}" data-y="{ey}"'
                f' data-tipo="texto" style="{et_style}">{contenido}</div>'
            )

        elif tipo_et == "sensor":
            et_id     = _html_std.escape(str(etiqueta.get("id") or ""))
            sensor    = str(etiqueta.get("sensor") or "")
            mostrar   = etiqueta.get("mostrar") or ["nombre", "valor"]
            fn_nombre = etiqueta.get("funcion_valor") or "ultimo_dato"
            decimales = int(etiqueta.get("decimales") or 2)
            font_size = fmt.get("tamano", 9)

            # Extended formato flags — None means default True (backward compat)
            _fmt_banda  = fmt.get("banda")
            _fmt_valor  = fmt.get("valor")
            _fmt_umbral = fmt.get("umbral")
            _fmt_borde  = fmt.get("borde")
            show_banda  = _fmt_banda  if _fmt_banda  is not None else True
            show_valor  = _fmt_valor  if _fmt_valor  is not None else True
            show_umbral = _fmt_umbral if _fmt_umbral is not None else True
            show_borde  = _fmt_borde  if _fmt_borde  is not None else True
            borde_color_et = fmt.get("borde_color") or "#cbd5e1"

            color_identitario = mapa_colores.get(sensor, "#94a3b8")

            _banda = ""
            if show_banda:
                _banda = (
                    f'<span style="display:inline-block;width:4px;align-self:stretch;'
                    f'background:{color_identitario};border-radius:2px 0 0 2px;flex-shrink:0;"></span>'
                )

            _nombre_html = ""
            if "nombre" in mostrar:
                _nombre_html = (
                    f'<span style="color:#1e293b;font-size:{font_size}pt;">'
                    f'{_html_std.escape(sensor)}</span>'
                )

            _valor_html = ""
            if "valor" in mostrar and show_valor:
                _val_raw = ultimos_valores.get(sensor)
                if _val_raw is None:
                    _valor_str   = "—"
                    _valor_color = "#94a3b8"
                else:
                    try:
                        func_mod = _get_cell_fn(fn_nombre)
                        _val_result = func_mod.evaluate(
                            {
                                "sensor": sensor,
                                "fecha_limite": context.get("fecha_fin") or "",
                                "decimales": decimales,
                            },
                            {"historico": historico},
                            context,
                        )
                        _valor_str = _html_std.escape(str(_val_result))
                    except Exception as _exc:
                        logger.warning(
                            "[HTML] _elem_sinoptico: error ejecutando '%s' para sensor '%s': %s",
                            fn_nombre, sensor, _exc,
                        )
                        _valor_str = "—"
                    if show_umbral:
                        _nivel_val   = evaluar_nivel_alarma(_val_raw, umbrales_por_sensor.get(sensor))
                        _valor_color = color_para_nivel(_nivel_val, paleta_alarma)
                    else:
                        _valor_color = "#1e293b"
                _valor_html = (
                    f'<span style="color:{_valor_color};font-size:{font_size}pt;font-weight:600;">'
                    f'{_valor_str}</span>'
                )

            _fecha_html = ""
            if "fecha" in mostrar:
                _fecha_str = ultima_fecha_por_sensor.get(sensor, "")
                if _fecha_str:
                    _fecha_html = (
                        f'<span style="color:#64748b;font-size:{max(7, font_size - 1)}pt;">'
                        f'{_html_std.escape(str(_fecha_str))}</span>'
                    )

            _border_css = f"1px solid {borde_color_et}" if show_borde else "none"
            et_style = (
                f"{pos_style}"
                f"background:white;border:{_border_css};border-radius:3px;"
                f"padding:1px 6px 1px 0;"
                f"display:inline-flex;align-items:center;gap:5px;"
                f"font-family:Arial,sans-serif;white-space:nowrap;"
            )
            _inner = _banda + _nombre_html + _valor_html + _fecha_html
            etiquetas_html_parts.append(
                f'<div data-etiqueta-id="{et_id}" data-x="{ex}" data-y="{ey}"'
                f' data-tipo="sensor" style="{et_style}">{_inner}</div>'
            )

        elif tipo_et == "componente":
            from utils.sinoptico_componentes import get_componente as _get_comp, render_componente as _render_comp  # noqa: PLC0415
            comp_id  = str(etiqueta.get("componente") or "")
            comp_def = _get_comp(comp_id)
            if comp_def is None:
                logger.warning(
                    "[HTML] _elem_sinoptico: componente SVG desconocido '%s', omitido", comp_id
                )
            else:
                et_id     = _html_std.escape(str(etiqueta.get("id") or ""))
                rotacion  = int(etiqueta.get("rotacion") or 0)
                escala_cm = float(etiqueta.get("escala_cm") or comp_def.get("ancho_def_cm") or 2.0)
                params    = dict(etiqueta.get("params") or {})
                svg_html  = _render_comp(comp_id, params)
                if svg_html is None:
                    logger.warning(
                        "[HTML] _elem_sinoptico: render devolvió None para '%s', omitido", comp_id
                    )
                else:
                    comp_style = (
                        f"position:absolute;left:{ex * 100:.2f}%;top:{ey * 100:.2f}%;"
                        f"transform:translate(-50%,-50%) rotate({rotacion}deg);"
                        f"z-index:1;width:{escala_cm}cm;"
                    )
                    etiquetas_html_parts.append(
                        f'<div data-etiqueta-id="{et_id}" data-x="{ex}" data-y="{ey}"'
                        f' data-tipo="componente"'
                        f' data-componente="{_html_std.escape(comp_id)}"'
                        f' style="{comp_style}">'
                        + svg_html
                        + "</div>"
                    )

        elif tipo_et == "vector":
            import math as _math  # noqa: PLC0415
            et_id    = _html_std.escape(str(etiqueta.get("id") or ""))
            sensor_x = str(etiqueta.get("sensor_x") or "").strip()
            sensor_y = str(etiqueta.get("sensor_y") or "").strip()
            if not sensor_x or not sensor_y:
                logger.warning(
                    "[HTML] _elem_sinoptico: vector '%s' sin sensor_x/sensor_y completos, omitido",
                    et_id,
                )
            else:
                vx_0 = primeros_valores.get(sensor_x)
                vx_1 = ultimos_valores.get(sensor_x)
                vy_0 = primeros_valores.get(sensor_y)
                vy_1 = ultimos_valores.get(sensor_y)
                if any(v is None for v in (vx_0, vx_1, vy_0, vy_1)):
                    logger.warning(
                        "[HTML] _elem_sinoptico: vector '%s' sin datos completos "
                        "(sensor_x='%s', sensor_y='%s'), omitido",
                        et_id, sensor_x, sensor_y,
                    )
                else:
                    vx         = float(vx_1) - float(vx_0)  # type: ignore[arg-type]
                    vy         = float(vy_1) - float(vy_0)  # type: ignore[arg-type]
                    escala     = float(etiqueta.get("escala") or 1.0)
                    color      = str(etiqueta.get("color") or "#dc2626")
                    _mostrar   = etiqueta.get("mostrar_modulo")
                    mostrar_modulo = _mostrar if _mostrar is not None else True
                    decimales  = int(etiqueta.get("decimales") or 2)
                    safe_color = _html_std.escape(color)

                    x1 = ex * w
                    y1 = ey * h
                    x2 = x1 + vx * escala
                    y2 = y1 - vy * escala  # eje Y invertido: vy>0 → arriba

                    dx, dy    = x2 - x1, y2 - y1
                    angle_rad = _math.atan2(dy, dx)
                    half_ang  = _math.radians(25)
                    arr_size  = 0.12
                    bx1 = x2 - arr_size * _math.cos(angle_rad + half_ang)
                    by1 = y2 - arr_size * _math.sin(angle_rad + half_ang)
                    bx2 = x2 - arr_size * _math.cos(angle_rad - half_ang)
                    by2 = y2 - arr_size * _math.sin(angle_rad - half_ang)

                    g_parts = [
                        f'<circle cx="{x1:.4f}" cy="{y1:.4f}" r="0.06" fill="{safe_color}"/>',
                        f'<line x1="{x1:.4f}" y1="{y1:.4f}" x2="{x2:.4f}" y2="{y2:.4f}"'
                        f' stroke="{safe_color}" stroke-width="0.05"/>',
                        f'<path d="M {x2:.4f} {y2:.4f} L {bx1:.4f} {by1:.4f}'
                        f' L {bx2:.4f} {by2:.4f} Z" fill="{safe_color}"/>',
                    ]
                    if mostrar_modulo:
                        modulo     = _math.hypot(vx, vy)
                        label_text = f"{modulo:.{decimales}f}"
                        tx = x2 + 0.15 * _math.cos(angle_rad)
                        ty = y2 + 0.15 * _math.sin(angle_rad)
                        g_parts.append(
                            f'<text x="{tx:.4f}" y="{ty:.4f}" font-size="0.25"'
                            f' fill="{safe_color}" paint-order="stroke"'
                            f' stroke="white" stroke-width="0.08"'
                            f' dominant-baseline="middle" text-anchor="start"'
                            f'>{_html_std.escape(label_text)}</text>'
                        )
                    vector_svg_parts.append(
                        f'<g data-etiqueta-id="{et_id}" data-tipo="vector"'
                        f' data-x="{ex}" data-y="{ey}">'
                        + "".join(g_parts)
                        + "</g>"
                    )

        elif tipo_et == "forma":
            et_id      = _html_std.escape(str(etiqueta.get("id") or ""))
            forma      = str(etiqueta.get("forma") or "rect")
            ancho_cm_f = max(0.05, min(30.0, float(etiqueta.get("ancho_cm") or 2.0)))
            alto_cm_f  = max(0.05, min(30.0, float(etiqueta.get("alto_cm") or 1.2)))
            rotacion_f = int(etiqueta.get("rotacion") or 0) % 360
            contenido_f = _html_std.escape(str(etiqueta.get("contenido") or ""))
            estilo_f   = etiqueta.get("estilo") or {}
            stroke     = str(estilo_f.get("stroke") or "#1e293b")
            grosor_pt  = max(0.25, min(10.0, float(estilo_f.get("grosor_pt") or 1.0)))
            fill       = str(estilo_f.get("fill") or "none")
            fill_modo  = str(estilo_f.get("fill_modo") or "")
            discontinua = bool(estilo_f.get("discontinua") or False)
            tamano_f   = max(5, min(36, int(estilo_f.get("tamano") or 9)))

            dash_css = "dashed" if discontinua else "solid"
            if fill_modo:
                _fc = str(estilo_f.get("fill_color") or "#3b82f6")
                _fo = max(0, min(100, int(estilo_f.get("fill_opacidad") or 30)))
                if fill_modo == "solido":
                    fill_css = _fc
                elif fill_modo == "translucido":
                    _hx = _fc.lstrip("#")
                    if len(_hx) == 3:
                        _hx = _hx[0] * 2 + _hx[1] * 2 + _hx[2] * 2
                    try:
                        _cr, _cg, _cb = int(_hx[0:2], 16), int(_hx[2:4], 16), int(_hx[4:6], 16)
                        fill_css = f"rgba({_cr},{_cg},{_cb},{_fo / 100:.2f})"
                    except (ValueError, IndexError):
                        fill_css = _fc
                else:
                    fill_css = "transparent"
            else:
                fill_css = "transparent" if fill == "none" else fill

            pos_no_tr = f"position:absolute;left:{ex * 100:.2f}%;top:{ey * 100:.2f}%;z-index:1;"
            forma_wrap_style = (
                f"{pos_no_tr}"
                f"transform:translate(-50%,-50%) rotate({rotacion_f}deg);"
            )

            if forma == "rect":
                inner_f = (
                    f'<div style="width:{ancho_cm_f}cm;height:{alto_cm_f}cm;'
                    f'border:{grosor_pt}pt {dash_css} {stroke};background:{fill_css};">'
                    f'</div>'
                )
            elif forma == "elipse":
                inner_f = (
                    f'<div style="width:{ancho_cm_f}cm;height:{alto_cm_f}cm;'
                    f'border:{grosor_pt}pt {dash_css} {stroke};background:{fill_css};'
                    f'border-radius:50%;"></div>'
                )
            elif forma == "linea":
                inner_f = (
                    f'<div style="width:{ancho_cm_f}cm;height:0;'
                    f'border-top:{grosor_pt}pt {dash_css} {stroke};"></div>'
                )
            elif forma == "flecha":
                inner_f = (
                    f'<div style="position:relative;width:{ancho_cm_f}cm;height:0.4cm;">'
                    f'<div style="position:absolute;top:50%;left:0;right:0.28cm;height:0;'
                    f'border-top:{grosor_pt}pt {dash_css} {stroke};transform:translateY(-50%);"></div>'
                    f'<div style="position:absolute;right:0;top:50%;'
                    f'transform:translate(0,-50%);width:0;height:0;'
                    f'border-left:0.28cm solid {stroke};'
                    f'border-top:0.14cm solid transparent;'
                    f'border-bottom:0.14cm solid transparent;"></div>'
                    f'</div>'
                )
            elif forma == "texto":
                font_fam_f = _FF_MAP_SIN.get(str(estilo_f.get("fuente") or "sans"), "Helvetica, Arial, sans-serif")
                font_sty_f = "italic" if estilo_f.get("cursiva") else "normal"
                font_wgt_f = "700" if estilo_f.get("negrita") else "400"
                _fondo_modo_f  = str(estilo_f.get("fondo_modo") or "none")
                _fondo_color_f = str(estilo_f.get("fondo_color") or "transparent")
                _borde_f       = bool(estilo_f.get("borde") or False)
                _borde_color_f = str(estilo_f.get("borde_color") or "#cbd5e1")
                bg_f     = _fondo_color_f if _fondo_modo_f == "solido" else "transparent"
                border_f = f"1px solid {_borde_color_f}" if _borde_f else "none"
                inner_f = (
                    f'<div style="font-size:{tamano_f}pt;color:{stroke};'
                    f'white-space:nowrap;font-family:{font_fam_f};'
                    f'font-style:{font_sty_f};font-weight:{font_wgt_f};'
                    f'background:{bg_f};border:{border_f};padding:1px 3px;">'
                    f'{contenido_f}</div>'
                )
            else:
                inner_f = ""

            if inner_f:
                etiquetas_html_parts.append(
                    f'<div data-etiqueta-id="{et_id}" data-x="{ex}" data-y="{ey}"'
                    f' data-tipo="forma" data-forma="{_html_std.escape(forma)}"'
                    f' style="{forma_wrap_style}">'
                    + inner_f
                    + '</div>'
                )

        else:
            logger.debug(
                "[HTML] _elem_sinoptico: tipo de etiqueta desconocido '%s', omitido", tipo_et
            )

    _safe_elem_id = _html_std.escape(elem_id)
    _vector_svg = ""
    if vector_svg_parts:
        _vector_svg = (
            f'<svg style="position:absolute;inset:0;width:100%;height:100%;'
            f'pointer-events:none;z-index:2;" '
            f'viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">'
            + "".join(vector_svg_parts)
            + "</svg>"
        )
    return (
        f'<div class="sinoptico-marco" data-sinoptico-id="{_safe_elem_id}" style="{contenedor_style}">'
        + img_html
        + "\n".join(etiquetas_html_parts)
        + _vector_svg
        + "</div>"
    )


def _elem_grafico(elem: dict, context: dict) -> str:
    """Ejecuta el script de gráfico y devuelve el fragmento HTML resultante.

    Si el script falla o no devuelve resultado, renderiza un *placeholder* y
    continúa — no bloquea la generación del informe.
    """
    geo = elem.get("geometria") or {}
    cfg = elem.get("configuracion") or {}
    x, y = float(geo.get("x", 0)), float(geo.get("y", 0))
    w, h = float(geo.get("ancho", 15)), float(geo.get("alto", 8))
    script_name = cfg.get("script") or ""

    if not script_name:
        return ""

    figsize   = (w / 2.54, h / 2.54)           # cm → pulgadas (compatibilidad)
    elem_id   = elem.get("id") or ""
    params    = _resolve_params(dict(cfg.get("parametros") or {}), context, elem_id=elem_id)
    # Inyectar sensor si no fue resuelto (plantilla omite "sensor":"$CURRENT" en
    # parametros pero params_clasificacion lo declara como primario).
    if not params.get("sensor") and (cfg.get("params_clasificacion") or {}).get("sensor"):
        params["sensor"] = _ctx_lookup("sensor", context)
    if params.get("sensor"):
        params["sensor"] = _normalizar_lista_sensores(params["sensor"])
    logger.warning(
        "[HTML][DBG] _elem_grafico | script=%s elem=%s sensor=%r sensores_1_ctx=%r",
        script_name, elem_id, params.get("sensor"), context.get("sensores_1"),
    )
    _custom   = (context.get("custom_chart_settings") or {}).get(elem_id, {})
    if _custom:
        # Filtrar: no sobrescribir tokens $CURRENT ya resueltos ni parámetros
        # primarios de contexto (sensor/fechas) que son dinámicos por diseño.
        _custom_clean = {
            k: v for k, v in _custom.items()
            if v is not None
            and not (isinstance(v, str) and v.startswith("$"))
            and k not in _DYNAMIC_CTX_PARAMS
        }
        if _custom_clean:
            params = {**params, **_custom_clean}

    chart_html = _run_script(script_name, params, figsize, context, elem_id)

    if not chart_html:
        safe_name = _html_std.escape(script_name)
        return (
            f'<div style="position:absolute;left:{x}cm;top:{y}cm;width:{w}cm;height:{h}cm;'
            f'border:1px dashed #e59;display:flex;align-items:center;justify-content:center;'
            f'font-size:7pt;color:#e59;">[error gráfico: {safe_name}]</div>'
        )
    return (
        f'<div style="position:absolute;left:{x}cm;top:{y}cm;'
        f'width:{w}cm;height:{h}cm;overflow:hidden;'
        f'border:1px solid #e2e8f0;border-radius:8px;">'
        f'{chart_html}</div>'
    )


# ── Tablas ────────────────────────────────────────────────────────────────────

def _build_html_table_from_data(result: dict, w: float, h: float) -> str:
    """Construye el fragmento HTML de una tabla a partir del dict del script.

    Aplica bandas de cebra y clase ``.numeric`` a columnas de tipo numérico.
    Usa las clases CSS ``.modern-table`` del design system institucional.
    """
    import html as _html_escape  # noqa: PLC0415

    titulo    = result.get("titulo", "")
    headers   = result.get("headers", [])
    rows      = result.get("rows", [])
    col_types = result.get("col_types", [])
    footer    = result.get("footer", "")

    th_cells = "".join(
        f"<th>{_html_escape.escape(str(hdr))}</th>" for hdr in headers
    )

    tbody_rows: list[str] = []
    for i, row in enumerate(rows):
        stripe = "background:#F9FAFB;" if i % 2 == 1 else ""
        tds: list[str] = []
        for j, val in enumerate(row):
            col_type = col_types[j] if j < len(col_types) else "text"
            cls = ' class="numeric"' if col_type == "numeric" else ""
            sty = f' style="{stripe}"' if stripe else ""
            tds.append(f"<td{cls}{sty}>{_html_escape.escape(str(val))}</td>")
        tbody_rows.append(f"<tr>{''.join(tds)}</tr>")

    parts: list[str] = [
        '<div style="width:100%;height:100%;overflow:auto;font-family:Arial,sans-serif;">'
    ]
    if titulo:
        parts.append(
            f'<div style="font-size:10pt;font-weight:600;color:#374151;'
            f'margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #E5E7EB;">'
            f'{_html_escape.escape(titulo)}</div>'
        )
    parts.append(
        f'<table class="modern-table">'
        f'<thead><tr>{th_cells}</tr></thead>'
        f'<tbody>{"".join(tbody_rows)}</tbody>'
        f'</table>'
    )
    if footer:
        parts.append(
            f'<div style="margin-top:6px;font-size:7pt;color:#9CA3AF;">'
            f'{_html_escape.escape(footer)}</div>'
        )
    parts.append("</div>")
    return "".join(parts)


_CUAD_TOKEN_RE = _re.compile(r"\{\{(\w+)\}\}")


def _build_html_cuadricula(
    niveles_estaticos: list[dict] | dict | None,
    nivel_autorelleno: dict,
    rows: list[dict],
    wrap: bool = True,
    computed_header_rows: list[dict] | None = None,
    override_row_height_cm: float | None = None,
    override_font_size_pt: float | None = None,
    *,
    mapa_colores_ancla: dict[str, str] | None = None,
    columna_ancla: int | None = None,
    colores_alarma_por_sensor: dict[str, str] | None = None,
    columna_ultimo_dato: int | None = None,
) -> str:
    """Construye el HTML de tabla basado en la cuadricula del elemento del editor.

    ``niveles_estaticos`` puede ser una lista de niveles, un dict único (retrocompat.)
    o None.  Cada nivel genera un ``<tr>`` adicional en el ``<thead>``.
    ``computed_header_rows`` es una lista paralela de dicts ``{str(col_index): valor}``
    con los valores calculados de las columnas de función de cada nivel estático.

    El nivel ``autorrelleno`` provee las plantillas de celda con tokens ``{{clave}}``.
    Por cada dict en ``rows``, genera un ``<tr>`` sustituyendo los tokens por los
    valores del dict.

    Reglas de estilo especiales:
    - Celda cuyo valor empieza por ``↗`` o ``↘`` → color azul (#2563eb).
    - Celda cuyo valor empieza por ``→`` → color azul neutro (#2563eb).
    - Primera columna → texto en negrita y color oscuro (#334155).
    - Bandas de cebra según ``configuracion_dinamica`` del nivel autorrelleno.

    Args:
        override_row_height_cm: Altura explícita de cada fila de datos en cm
            (para auto-fit cuando las filas no caben en el contenedor).
        override_font_size_pt: Tamaño de fuente explícito en pt para las celdas
            de datos (para auto-fit proporcional).
    """
    import html as _e  # noqa: PLC0415

    # Normalizar niveles_estaticos a lista
    if isinstance(niveles_estaticos, dict):
        _niveles_est: list[dict] = [niveles_estaticos]
    elif niveles_estaticos:
        _niveles_est = list(niveles_estaticos)
    else:
        _niveles_est = []

    _computed_rows: list[dict] = list(computed_header_rows) if computed_header_rows else []

    cfg_din     = nivel_autorelleno.get("configuracion_dinamica") or {}
    zebra       = bool(cfg_din.get("sombreado_alterno", True))
    color_par   = str(cfg_din.get("color_par",   "#ffffff"))
    color_impar = str(cfg_din.get("color_impar", "#f8fafc"))
    auto_cols   = nivel_autorelleno.get("columnas") or []

    # ── Encabezado: un <tr> por nivel estático ────────────────────────────────
    # data_row_h se usa también más abajo para los <td>
    data_row_h: float = (
        override_row_height_cm
        if override_row_height_cm
        else float(nivel_autorelleno.get("alto_fila") or 0.5)
    )
    n_auto_cols = len(auto_cols)
    header_html = ""
    if _niveles_est:
        all_tr: list[str] = []
        for ni, nivel_est in enumerate(_niveles_est):
            chr_row  = _computed_rows[ni] if ni < len(_computed_rows) else None
            th_row_h = float(nivel_est.get("alto_fila") or 0.5)
            th_parts: list[str] = []
            colspan_sum = 0
            for ci, c in enumerate(nivel_est.get("columnas") or []):
                fmt     = c.get("formato") or {}
                align   = fmt.get("alineacion", "left")
                colspan = max(1, int(c.get("colspan") or 1))
                colspan_sum += colspan
                # width solo en celdas de span=1; con colspan el body define los anchos
                width_css = f"width:{c.get('ancho', 25)}%;" if colspan == 1 else ""
                font_sz = fmt.get("tamano") or fmt.get("size")
                th_sty = (
                    f"{width_css}"
                    "background:#f8fafc;"
                    f"text-align:{align};"
                    "font-weight:600;"
                    "color:#475569;"
                    "border-bottom:2px solid #e2e8f0;"
                    f"height:{th_row_h:.3f}cm;"
                    f"line-height:{th_row_h:.3f}cm;"
                    "padding:0 6px;"
                    "overflow:hidden;"
                    + (f"font-size:{font_sz}pt;" if font_sz else "")
                )
                if fmt.get("ajustar_texto"):
                    th_sty += "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                # Petición 1bis: las celdas con `contenido_ref` también consumen
                # su valor desde `chr_row` (rellenado por _elem_tabla a partir
                # del contexto del informe). Si no hay valor resuelto, cae al
                # `contenido` literal igual que las celdas legacy.
                _tiene_funcion       = (c.get("origen") or {}).get("tipo") == "funcion"
                _tiene_contenido_ref = isinstance(c.get("contenido_ref"), dict)
                if (_tiene_funcion or _tiene_contenido_ref) and chr_row is not None:
                    cell_text = str(chr_row.get(str(ci)) or c.get("contenido", ""))
                else:
                    cell_text = str(c.get("contenido", ""))
                colspan_attr = f' colspan="{colspan}"' if colspan > 1 else ""
                th_parts.append(f'<th{colspan_attr} style="{th_sty}">{_e.escape(cell_text)}</th>')
            if n_auto_cols and colspan_sum != n_auto_cols:
                logger.warning(
                    "[HTML] cuadricula: nivel estático %d tiene colspan_sum=%d pero "
                    "autorrelleno tiene %d columnas — revisar colspan en la plantilla",
                    ni, colspan_sum, n_auto_cols,
                )
            all_tr.append(f'<tr style="height:{th_row_h:.3f}cm;">{"".join(th_parts)}</tr>')
        header_html = f'<thead>{"".join(all_tr)}</thead>'

    # ── Filas de datos ────────────────────────────────────────────────────────
    n_rows = len(rows)
    tbody_parts: list[str] = []
    for i, row_data in enumerate(rows):
        bg = color_impar if (zebra and i % 2 == 1) else color_par
        is_last = (i == n_rows - 1)
        tds: list[str] = []
        for j, col in enumerate(auto_cols):
            origen = col.get("origen") or {}
            fmt    = col.get("formato") or {}

            if origen.get("tipo") == "funcion":
                # Columnas de función: usar valor calculado directamente
                raw = str(row_data.get(str(j), ""))
                fmt_fecha = fmt.get("formato_fecha")
                if fmt_fecha and raw:
                    _FMT_PARSE = (
                        "%Y-%m-%d %H:%M:%S.%f",
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d %H:%M",
                        "%Y-%m-%d",
                    )
                    for _fp in _FMT_PARSE:
                        try:
                            raw = _dt.strptime(raw.strip(), _fp).strftime(fmt_fecha)
                            break
                        except ValueError:
                            continue
            else:
                # Columnas fijas: usar contenido como plantilla mustache
                template = str(col.get("contenido") or "")
                raw = _CUAD_TOKEN_RE.sub(
                    lambda m, rd=row_data: str(rd.get(m.group(1), "")),
                    template,
                )
            cell_html = _e.escape(raw)

            # Formato de decimales padded (opt-in): si la columna declara
            # formato_decimales en su fmt, reemplazar la representación numérica por
            # f"{v:.Nf}" para garantizar N decimales fijos. Solo aplica si raw es
            # parseable como float. No toca celdas no numéricas ni la salida de
            # funciones que ya devuelven string formateado (incremento con flechas).
            _fmt_dec = fmt.get("formato_decimales")
            if _fmt_dec is not None:
                try:
                    _v_num = float(raw)
                    _ndec = int(_fmt_dec)
                    cell_html = f"{_v_num:.{_ndec}f}"
                except (ValueError, TypeError):
                    pass

            # Estilos base de columna
            align = fmt.get("alineacion", "left")
            # Primera columna → negrita y color oscuro
            if j == 0:
                bold      = "font-weight:600;"
                col_color = "color:#334155;"
            else:
                bold      = "font-weight:600;" if fmt.get("negrita") else ""
                col_color = ""
            font_sz = override_font_size_pt if override_font_size_pt else fmt.get("tamano")
            sty = (
                f"width:{col.get('ancho', 25)}%;"
                f"height:{data_row_h:.3f}cm;"
                f"line-height:{data_row_h:.3f}cm;"
                f"background:{bg};"
                f"text-align:{align};"
                f"{bold}{col_color}"
                + ("" if is_last else "border-bottom:1px solid #e2e8f0;")
                + "padding:0 6px;"
                + "overflow:hidden;"
                + (f"font-size:{font_sz}pt;" if font_sz else "")
            )
            if fmt.get("ajustar_texto"):
                sty += "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"

            # Detección de celda de tendencia (↗/↘/→) → siempre azul
            stripped  = raw.strip()
            extra_cls = ""
            color_css = ""
            if stripped.startswith("↗") or stripped.startswith("↘"):
                extra_cls = ' class="numeric"'
                color_css = "color:#2563eb;font-weight:500;"
            elif stripped.startswith("→"):
                extra_cls = ' class="numeric"'
                color_css = "color:#2563eb;font-weight:500;"

            # Color por sensor en la columna ancla (opt-in): barra vertical del color
            # del sensor pegada al borde izquierdo de la celda (border-left del td),
            # ocupa toda la altura de la fila como si fuera una columna estrecha sin
            # encabezado. Sin caja, sin sombra. El texto del sensor queda en negro.
            if (
                mapa_colores_ancla
                and columna_ancla is not None
                and j == columna_ancla
            ):
                sensor_nom = str(row_data.get("sensor") or row_data.get(str(columna_ancla)) or "")
                color_sensor = mapa_colores_ancla.get(sensor_nom)
                if color_sensor:
                    sty += f"border-left:4px solid {color_sensor};padding-left:8px;"

            # Pastilla de alarma (opt-in) a la derecha del valor de "Última".
            # Círculo de 8px del color del nivel de alarma calculado en el flujo
            # principal. Solo se aplica cuando colores_alarma_por_sensor está poblado
            # y la columna actual coincide con la de la función ultimo_dato.
            if (
                colores_alarma_por_sensor
                and columna_ultimo_dato is not None
                and j == columna_ultimo_dato
            ):
                sensor_nom_alarma = str(row_data.get("sensor") or row_data.get(str(columna_ancla)) or "")
                color_alarma = colores_alarma_por_sensor.get(sensor_nom_alarma)
                if color_alarma:
                    cell_html += (
                        f'<span style="display:inline-block;width:8px;height:8px;'
                        f'background:{color_alarma};border-radius:50%;'
                        f'margin-left:8px;vertical-align:middle;"></span>'
                    )

            tds.append(
                f"<td{extra_cls} style=\"{sty}{color_css}\">{cell_html}</td>"
            )
        tbody_parts.append(f'<tr style="height:{data_row_h:.3f}cm;">{"".join(tds)}</tr>')

    table_html = (
        '<table class="modern-table" style="width:100%;border-collapse:collapse;'
        'border-spacing:0;">'
        f"{header_html}"
        f"<tbody>{''.join(tbody_parts)}</tbody>"
        "</table>"
    )
    if not wrap:
        return table_html
    return (
        '<div style="width:100%;height:100%;overflow:auto;font-family:Arial,sans-serif;">'
        '<div style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">'
        + table_html
        + "</div></div>"
    )


def _run_tabla_script(
    script_name: str,
    params: dict,
    context: dict,
    elem_id: str = "",
) -> dict | None:
    """Importa un script de tabla y llama a ``generate(data, params, context)``.

    Resolución de ruta (en orden):
    1. Ruta con namespace (``"html/tabla_pernos.py"``) → ``biblioteca_tablas/<ruta>``.
    2. Nombre plano → ``biblioteca_tablas/html/``, luego ``biblioteca_tablas/``.

    Returns:
        Dict ``{"headers": [...], "rows": [...], ...}`` o ``None`` si el script falla.
    """
    if not script_name.endswith(".py"):
        script_name += ".py"

    if "/" in script_name or "\\" in script_name:
        script_path = _TABLAS_ROOT / script_name
    else:
        script_path = _TABLAS_HTML / script_name
        if not script_path.is_file():
            script_path = _TABLAS_ROOT / script_name

    if not script_path.is_file():
        logger.warning("[HTML] Script de tabla no encontrado: %s", script_name)
        return None

    module_name = f"_html_tabla_{script_path.stem}"
    sys.modules.pop(module_name, None)

    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except Exception as exc:
        logger.exception("[HTML] Error cargando script de tabla '%s': %s", script_name, exc)
        _emit_log("TABLA_ERROR", script=script_name, elem_id=elem_id, error=f"load: {exc}")
        return None

    generate_fn = getattr(module, "generate", None)
    if generate_fn is None:
        logger.warning("[HTML] Script de tabla '%s' no define generate()", script_name)
        return None

    # Inyectar custom settings por instancia de elemento
    _custom = (context.get("custom_chart_settings") or {}).get(elem_id, {})
    if _custom:
        params = {**params, **_custom}

    # Obtener datos si hace falta
    data: dict = {}
    ctx_data = context.get("data") or {}
    if ctx_data.get("historico"):
        data = ctx_data
    elif context.get("server_id"):
        data = _fetch_script_data(params, context)

    try:
        result = generate_fn(data, params, context)
    except Exception as exc:
        logger.exception("[HTML] Error ejecutando script de tabla '%s': %s", script_name, exc)
        _emit_log("TABLA_ERROR", script=script_name, elem_id=elem_id, error=str(exc))
        return None

    if isinstance(result, dict):
        _emit_log("TABLA_OK", script=script_name, elem_id=elem_id,
                  n_rows=len(result.get("rows") or []))
        return result
    logger.warning("[HTML] Script de tabla '%s' devolvió %s (se espera dict)",
                   script_name, type(result).__name__)
    return None


def _resolve_param_value(
    pv: Any,
    row_data: dict[str, Any],
    columna_ancla: int,
    context: dict,
) -> Any:
    """Resuelve un valor de parámetro de función de celda al valor concreto.

    Soporta el modelo nuevo (``ref: ancla/contexto/literal``) y mantiene
    retrocompatibilidad con el modelo anterior (``ref: celda``).

    Args:
        pv:            Valor raw del parámetro (puede ser dict ref o literal).
        row_data:      Dict de la fila en construcción (valores ya calculados).
        columna_ancla: Índice de la columna ancla de la tabla.
        context:       Contexto global del informe.

    Returns:
        Valor resuelto listo para pasar a ``func.evaluate()``.
    """
    if not isinstance(pv, dict):
        return pv
    ref = pv.get("ref")
    if ref == "ancla":
        return row_data.get(str(columna_ancla), "")
    if ref == "celda":  # retrocompatibilidad: tratar como ancla si columna == ancla, sino leer la col
        col_ref = pv.get("columna", 0)
        return row_data.get(str(col_ref), "")
    if ref == "contexto":
        clave: str = pv.get("clave", "")
        ctx_key = _CURRENT_TOKEN_MAP.get(clave, clave)
        # $CURRENT tokens: row_data lleva el sensor iterado actual (tiene prioridad)
        if ctx_key in row_data:
            return row_data[ctx_key]
        val = _ctx_lookup(ctx_key, context)
        if val is None or val == "":
            # Fallback: si el contexto no resuelve, usar el valor_plantilla declarado
            # en el propio dict (default del generador para secundarios mapeables,
            # p.ej. clave_a → "desp_a"). Permite que la tabla renderice aunque el
            # usuario no haya abierto el modal de Formato.
            vp = pv.get("valor_plantilla")
            if vp is not None:
                return vp
        return val
    if ref == "literal":
        return pv.get("valor", "")
    return pv


def _eval_static_to_context(
    niveles_stat: list[dict],
    context: dict,
) -> list[dict]:
    """Evalúa funciones de los niveles estáticos e inyecta sus resultados en context.

    Cada columna del nivel estático que defina ``"context_key": "clave"`` escribe
    su valor calculado en ``context["clave"]``, haciéndolo accesible a los parámetros
    del nivel autorrelleno via ``{"ref": "contexto", "clave": "clave"}``.

    Se llama desde el modo autorrelleno de ``_elem_tabla`` **antes** de generar las
    filas de datos, para que las fechas de campaña u otros valores del encabezado
    estén disponibles al resolver los parámetros de las funciones de autorrelleno.

    Args:
        niveles_stat: Lista de niveles de tipo ``estatico`` de la cuadrícula.
        context:      Contexto global del informe (modificado en lugar).

    Returns:
        Lista de ``row_data`` computados (uno por nivel estático), listos para
        usarse como valores de encabezado en ``_build_html_cuadricula``.
    """
    computed: list[dict] = []
    for ns in niveles_stat:
        rows = _generate_static_fn_row(ns, context)
        computed.append(rows[0] if rows else {})

    # Log para verificar las claves inyectadas en contexto
    injected = {
        col.get("context_key"): context.get(col.get("context_key"))
        for ns in niveles_stat
        for col in (ns.get("columnas") or [])
        if col.get("context_key")
    }
    if injected:
        logger.info(
            "[HTML] _eval_static_to_context: inyectadas %d claves → %s",
            len(injected),
            {k: str(v)[:30] for k, v in injected.items()},
        )

    return computed


def _generate_rows_from_cells(
    nivel_auto: dict,
    context: dict,
    columna_ancla: int = 0,
) -> list[dict]:
    """Genera filas celda a celda a partir de la lista de sensores del contexto.

    Itera sobre ``context["sensores_1"]`` (CSV) y, para cada sensor, evalúa cada
    columna del nivel autorrelleno.  Soporta dos modos:

    **Modo estándar:** cada función devuelve un escalar → una fila por sensor.

    **Modo expansión (multi-fila):** alguna función devuelve una lista (ej.
    ``columna_incli_json``).  En ese caso se generan N filas por sensor (una por
    elemento de la lista), usando el mínimo de longitudes si varias funciones
    devuelven listas.  Los valores escalares se replican en todas las filas.

    Columnas de ancla con función propia (``origen.tipo == "funcion"``) se evalúan
    normalmente y pueden retornar listas (ej. columna de profundidad).  Columnas de
    ancla sin función mantienen el nombre del sensor.

    Args:
        nivel_auto:    Dict del nivel ``autorrelleno`` de la cuadrícula.
        context:       Contexto global del informe.
        columna_ancla: Índice de la columna que identifica el sensor de la fila.

    Returns:
        Lista de dicts ``{str(j): valor, ..., "sensor": sensor}`` listos para
        ``_build_html_cuadricula``.
    """
    columnas: list[dict] = nivel_auto.get("columnas") or []
    rows: list[dict] = []

    # ── Determinar lista de sensores a iterar ────────────────────────────────
    if columna_ancla < 0:
        # Modo sin_ancla: una única pasada. Las funciones resuelven el sensor
        # directamente desde context vía {ref:contexto,clave:$CURRENT}.
        # Usamos el primer valor de sensores_1 como etiqueta para row["sensor"].
        _src     = context.get("_fuente_ancla") or "sensores_1"
        _raw     = _normalizar_lista_sensores(context.get(_src) or "").split(",")[0].strip()
        sensores = [_raw or context.get("sensor") or ""]
    else:
        fuente_ancla: str = context.get("_fuente_ancla") or "sensores_1"
        sensores_str: str = _normalizar_lista_sensores(context.get(fuente_ancla) or "")
        sensores = [s.strip() for s in sensores_str.split(",") if s.strip()]

    for sensor in sensores:
        # row_base: dict mínimo con el sensor como etiqueta (sin clave ancla cuando
        # columna_ancla < 0, ya que no hay columna de sensor en ese modo).
        if columna_ancla < 0:
            row_base: dict[str, Any] = {"sensor": sensor}
        else:
            row_base = {"sensor": sensor, str(columna_ancla): sensor}
        row_data: dict[str, Any] = dict(row_base)

        for j, col in enumerate(columnas):
            origen = col.get("origen") or {}
            tipo_origen = origen.get("tipo") or "fijo"

            # Ancla sin función: fijar al nombre del sensor (solo en modo con ancla)
            if columna_ancla >= 0 and j == columna_ancla and tipo_origen != "funcion":
                row_data[str(j)] = sensor
                continue

            if tipo_origen == "funcion":
                func_name: str = origen.get("funcion") or ""
                try:
                    func_mod = _get_cell_fn(func_name)
                    raw_params: dict = origen.get("parametros") or {}
                    resolved: dict[str, Any] = {
                        pk: _resolve_param_value(pv, row_data, columna_ancla, context)
                        for pk, pv in raw_params.items()
                    }
                    valor: Any = func_mod.evaluate(
                        resolved,
                        data=context.get("data", {}),
                        context=context,
                    )
                except Exception as exc:
                    logger.warning(
                        "[HTML] Error en función de celda '%s' (col %d): %s",
                        func_name, j, exc,
                    )
                    valor = ""
                row_data[str(j)] = valor
            else:
                row_data[str(j)] = ""  # fijo: template de contenido se resuelve en render

        # ── Modo expansión: alguna función devolvió una lista ──────────────────
        lists = {k: v for k, v in row_data.items() if isinstance(v, list)}
        if lists:
            # Determinamos la longitud máxima entre las listas que no estén vacías
            non_empty_lens = [len(v) for v in lists.values() if len(v) > 0]
            n = max(non_empty_lens) if non_empty_lens else 0
            
            for i in range(n):
                expanded: dict[str, Any] = dict(row_base)
                for k, v in row_data.items():
                    if isinstance(v, list):
                        # Extraer con seguridad; si la lista está vacía o es más corta, rellenar con ""
                        expanded[k] = v[i] if i < len(v) else ""
                    else:
                        expanded[k] = v
                rows.append(expanded)
        else:
            rows.append(row_data)

    return rows


def _generate_placeholder_rows(
    nivel_auto: dict,
    columna_ancla: int = 0,
    n_filas: int = 3,
) -> list[dict]:
    """Genera filas placeholder para visualizar la estructura de la tabla en maquetación.

    No ejecuta funciones de celda ni accede a datos reales. Cada celda muestra
    una etiqueta descriptiva del origen configurado:

    - Columna ancla: ``SENSOR-N``
    - Función con parámetro ``{ ref: "ancla" }``: ``[func(ancla)]``
    - Función con parámetro ``{ ref: "contexto", clave: "..." }``: ``[func($TOKEN)]``
    - Función sin parámetros reconocidos: ``[func]``
    - Fija: contenido literal o ``Col N``

    Se usa exclusivamente cuando ``context["is_maquetacion"]`` es ``True``.

    Args:
        nivel_auto:    Dict del nivel ``autorrelleno`` de la cuadrícula del elemento.
        columna_ancla: Índice de la columna ancla (default 0).
        n_filas:       Número de filas de ejemplo a generar (por defecto 3).

    Returns:
        Lista de dicts ``{str(j): texto_placeholder, "sensor": "SENSOR-N"}``
        listos para ``_build_html_cuadricula``.
    """
    columnas: list[dict] = nivel_auto.get("columnas") or []
    rows: list[dict] = []

    def _param_hint(parametros: dict) -> str:
        """Devuelve una pista legible del primer parámetro significativo."""
        for pv in parametros.values():
            if not isinstance(pv, dict):
                continue
            ref = pv.get("ref")
            if ref == "ancla":
                return "ancla"
            if ref == "contexto":
                clave = pv.get("clave") or ""
                # Mostrar solo la parte después de $CURRENT_ para brevedad
                token = clave.replace("$CURRENT_", "$") if clave.startswith("$CURRENT_") else clave
                return token
        return ""

    for i in range(n_filas):
        sensor_label = f"SENSOR-{i + 1}"
        row_data: dict[str, Any] = {"sensor": sensor_label}
        for j, col in enumerate(columnas):
            if j == columna_ancla:
                row_data[str(j)] = sensor_label
                continue
            origen = col.get("origen") or {}
            tipo_origen = origen.get("tipo") or "fijo"
            if tipo_origen == "funcion":
                func_name = origen.get("funcion") or f"fn_{j}"
                hint = _param_hint(origen.get("parametros") or {})
                row_data[str(j)] = f"[{func_name}({hint})]" if hint else f"[{func_name}]"
            else:
                contenido = str(col.get("contenido") or "").strip()
                row_data[str(j)] = contenido if contenido else f"Col {j}"
        rows.append(row_data)

    return rows


def _generate_static_fn_row(
    nivel_stat: dict,
    context: dict,
) -> list[dict]:
    """Genera la fila única de una tabla con nivel estático que contiene funciones de celda.

    Evalúa cada columna de función del nivel estático usando el contexto global del
    informe (sin iteración de sensores). Las columnas sin origen de función usan su
    ``contenido`` literal.

    Args:
        nivel_stat: Dict del nivel ``estatico`` de la cuadrícula.
        context:    Contexto global del informe.

    Returns:
        Lista con un único dict ``{str(j): valor, ...}`` listo para
        ``_build_html_cuadricula``.
    """
    columnas: list[dict] = nivel_stat.get("columnas") or []
    row_data: dict[str, Any] = {}

    for j, col in enumerate(columnas):
        origen = col.get("origen") or {}
        tipo_origen = origen.get("tipo") or "fijo"

        if tipo_origen == "funcion":
            func_name: str = origen.get("funcion") or ""
            try:
                func_mod = _get_cell_fn(func_name)
                raw_params: dict = origen.get("parametros") or {}
                resolved: dict[str, Any] = {
                    pk: _resolve_param_value(pv, row_data, 0, context)
                    for pk, pv in raw_params.items()
                }
                logger.warning(
                    "[DEBUG-STATIC-FN] col=%d func=%s params_resueltos=%s",
                    j, func_name, resolved,
                )
                valor: Any = func_mod.evaluate(
                    resolved,
                    data=context.get("data", {}),
                    context=context,
                )
                logger.warning(
                    "[DEBUG-STATIC-FN] col=%d func=%s valor=%r",
                    j, func_name, valor,
                )
            except Exception as exc:
                logger.warning(
                    "[DEBUG-STATIC-FN] col=%d func=%s ERROR: %s",
                    j, func_name, exc,
                )
                valor = ""
            row_data[str(j)] = valor
        else:
            row_data[str(j)] = col.get("contenido") or ""

        # Inyectar en context si la columna define context_key
        context_key = col.get("context_key")
        if context_key:
            context[context_key] = row_data[str(j)]

    return [row_data]


def _elem_tabla(elem: dict, context: dict) -> str:
    """Ejecuta el script de tabla y devuelve el fragmento HTML posicionado.

    Llama a ``_run_tabla_script()`` para tablas legacy o a
    ``_generate_rows_from_cells()`` para tablas celda a celda.  Si no hay script
    ni nivel autorrelleno, devuelve cadena vacía.  Si el script falla, renderiza
    un placeholder sin bloquear la generación del informe.
    """
    import html as _html_escape  # noqa: PLC0415

    geo = elem.get("geometria") or {}
    cfg = elem.get("configuracion") or {}
    x, y = float(geo.get("x", 0)), float(geo.get("y", 0))
    w, h = float(geo.get("ancho", 15)), float(geo.get("alto", 8))
    script_name = cfg.get("script") or ""

    cuadricula  = elem.get("cuadricula") or {}
    niveles     = cuadricula.get("niveles") or []
    nivel_auto  = next((n for n in niveles if n.get("tipo") == "autorrelleno"), None)
    niveles_stat = [n for n in niveles if n.get("tipo") == "estatico"]
    nivel_stat   = niveles_stat[0] if niveles_stat else None  # backward-compat alias

    nivel_stat_has_fns = any(
        (c.get("origen") or {}).get("tipo") == "funcion"
        for ns in niveles_stat
        for c in (ns.get("columnas") or [])
    )

    if not script_name and not nivel_auto and not nivel_stat_has_fns:
        return ""

    elem_id = elem.get("id") or ""

    if script_name:
        # ── MODO LEGACY: script monolítico ────────────────────────────────────
        params = _resolve_params(dict(cfg.get("parametros") or {}), context, elem_id=elem_id)
        result = _run_tabla_script(script_name, params, context, elem_id)

        if not result:
            safe_name = _html_escape.escape(script_name)
            return (
                f'<div style="position:absolute;left:{x}cm;top:{y}cm;width:{w}cm;height:{h}cm;'
                f'border:1px dashed #a5c;display:flex;align-items:center;justify-content:center;'
                f'font-size:7pt;color:#a5c;">[error tabla: {safe_name}]</div>'
            )

        result_rows = result.get("rows") or []
        use_cuadricula = (
            nivel_auto is not None
            and result_rows
            and isinstance(result_rows[0], dict)
        )
        tabla_html = (
            _build_html_cuadricula(niveles_stat, nivel_auto, result_rows)
            if use_cuadricula
            else _build_html_table_from_data(result, w, h)
        )
    elif nivel_auto:
        # ── MODO CELDA A CELDA (autorrelleno) ────────────────────────────────
        sin_ancla: bool = bool(cuadricula.get("sin_ancla"))
        columna_ancla: int = -1 if sin_ancla else int(cuadricula.get("columna_ancla") or 0)
        # Resolver fuente_ancla: si es $CURRENT, buscar en mapeo_parametros
        fa_token: str = cuadricula.get("fuente_ancla") or ""
        if fa_token.startswith("$CURRENT"):
            _mapeo = context.get("mapeo_parametros", {}).get(elem_id, {})
            resolved_field: str = _mapeo.get("sensor") or "sensores_1"
        else:
            resolved_field = fa_token or "sensores_1"
        context["_fuente_ancla"] = resolved_field

        # Evaluar niveles estáticos → inyecta valores en context (context_key)
        # y devuelve los row_data computados para mostrar en el encabezado.
        computed_header_rows = _eval_static_to_context(niveles_stat, context)

        # Inyectar custom_settings del elemento en el contexto antes del autorrelleno.
        # Los valores configurados por el usuario en el modal de Formato del dispatch
        # (o defaults pre-cargados por _build_initial_wizard_values) se vuelcan como
        # claves de contexto para que _resolve_param_value los encuentre al resolver
        # ref:"contexto". Análogo a context_key de _eval_static_to_context pero a
        # nivel de elemento. Tokens $... y valores None se omiten.
        _elem_custom = (context.get("custom_chart_settings") or {}).get(elem_id) or {}
        for _ck, _cv in _elem_custom.items():
            if _cv is None:
                continue
            if isinstance(_cv, str) and _cv.startswith("$"):
                continue
            context[_ck] = _cv

        # ── Petición 1bis: resolver contenido_ref en cabeceras estáticas ────
        # Para cada celda del nivel estático con `contenido_ref` (campo paralelo
        # a `contenido` introducido en Petición 1bis), resolvemos su valor
        # contra el contexto y lo escribimos en computed_header_rows[ni][str(ci)].
        # Así _build_html_cuadricula lo lee por la rama de `chr_row` igual que
        # las cabeceras dinámicas (fechas de campaña) del nivel 1. La inyección
        # de custom_chart_settings ya ocurrió arriba, por lo que _ctx_lookup
        # encuentra los valores guardados por el usuario en el modal de Formato.
        # Si no hay valor en contexto, cae al `valor_plantilla` declarado por
        # el generador. Tokens $... y None se omiten igual que en la inyección.
        #
        # Nota: NO comprobamos si `_chr[str(_ci)]` ya tiene contenido porque
        # `_generate_static_fn_row` rellena `row_data[str(j)]` con el `contenido`
        # literal para TODAS las columnas (no solo las de función). Si una celda
        # declara `contenido_ref`, su valor resuelto siempre tiene prioridad
        # sobre el literal del `contenido`.
        for _ni, _nivel_est in enumerate(niveles_stat):
            if _ni >= len(computed_header_rows):
                continue
            _chr = computed_header_rows[_ni]
            if _chr is None:
                continue
            for _ci, _col in enumerate(_nivel_est.get("columnas") or []):
                _cref = _col.get("contenido_ref")
                if not isinstance(_cref, dict) or _cref.get("ref") != "contexto":
                    continue
                _ctx_clave = _cref.get("clave")
                _resuelto = _ctx_lookup(_ctx_clave, context) if _ctx_clave else None
                if _resuelto is None or (isinstance(_resuelto, str) and _resuelto.startswith("$")):
                    _resuelto = _cref.get("valor_plantilla")
                if _resuelto is not None:
                    _chr[str(_ci)] = _resuelto

        mapa_colores_tabla: dict[str, str] = {}
        colores_alarma_tabla: dict[str, str] = {}
        columna_ultimo_dato_idx: int | None = None

        if context.get("is_maquetacion"):
            result_rows = _generate_placeholder_rows(nivel_auto, columna_ancla)
        else:
            # Asegurar datos disponibles para funciones de celda basadas en historico
            if not context.get("data", {}).get("historico"):
                if context.get("server_id"):
                    fetched = _fetch_script_data(
                        {"sensor": context.get(resolved_field) or ""},
                        context,
                    )
                    if fetched:
                        context["data"] = fetched
                        logger.info(
                            "[HTML] Celda-a-celda: datos cargados (%d registros históricos)",
                            len(fetched.get("historico") or []),
                        )
            # Inyectar delta_horas al contexto para que las funciones *_delta lo lean.
            # Se usa una clave con prefijo "_current_" para no contaminar otros
            # elementos del informe; se limpia tras renderizar la tabla.
            _delta_ovf = (context.get("custom_chart_settings") or {}).get(elem_id) or {}
            _delta_horas_raw = _delta_ovf.get("delta_horas") or cuadricula.get("delta_horas") or "20"
            try:
                _delta_horas_val = float(_delta_horas_raw)
            except (TypeError, ValueError):
                _delta_horas_val = 20.0
            context["_current_delta_horas"] = _delta_horas_val
            result_rows = _generate_rows_from_cells(nivel_auto, context, columna_ancla)

        # ── Auto-ajuste / paginación de overflow ─────────────────────────────
        _custom_ovf   = (context.get("custom_chart_settings") or {}).get(elem_id, {})
        overflow_mode: str = _custom_ovf.get("overflow") or cuadricula.get("overflow") or "truncar"

        # Resolución de flags de coloreado/orden con prioridad:
        # custom_chart_settings (BD informe) > cuadricula (plantilla) > default motor
        def _resolver_flag_bool(clave: str, default: bool = False) -> bool:
            val = _custom_ovf.get(clave)
            if val is None:
                val = cuadricula.get(clave)
            if val is None:
                return default
            if isinstance(val, bool):
                return val
            return str(val).lower() in ("true", "1", "yes", "si", "sí")

        def _resolver_flag_str(clave: str, default: str) -> str:
            val = _custom_ovf.get(clave)
            if val is None:
                val = cuadricula.get(clave)
            return str(val) if val else default

        orden_ultimo      = _resolver_flag_bool("orden_filas_por_ultimo_dato")
        colorear_ancla    = _resolver_flag_bool("colorear_ancla_por_sensor")
        paleta_ancla      = _resolver_flag_str("palette_ancla", "modern")
        mostrar_alarma    = _resolver_flag_bool("mostrar_estado_alarma", default=False)
        paleta_alarma_tabla = _resolver_flag_str("paleta_alarma", "semaforo")

        if not context.get("is_maquetacion"):
            # ── Ordenación opcional por última lectura (descendente) ─────────────
            if orden_ultimo:
                columnas_auto = nivel_auto.get("columnas") or []
                col_ultimo: int | None = next(
                    (
                        j for j, c in enumerate(columnas_auto)
                        if (c.get("origen") or {}).get("funcion") == "ultimo_dato"
                    ),
                    None,
                )
                if col_ultimo is not None:
                    def _key_orden(rd: dict, _col: int = col_ultimo) -> tuple:
                        v = rd.get(str(_col))
                        try:
                            return (0, -float(v))
                        except (TypeError, ValueError):
                            return (1, 0.0)
                    result_rows = sorted(result_rows, key=_key_orden)
                    logger.info(
                        "[HTML] tabla %s: filas ordenadas por col %d (ultimo_dato) DESC",
                        elem_id, col_ultimo,
                    )

            # ── Coloreado opcional de la columna ancla por sensor ────────────────
            if colorear_ancla and columna_ancla >= 0:
                from utils.sensor_palette import asignar_colores_sensores  # noqa: PLC0415
                sensores_unicos = [
                    str(rd.get("sensor") or rd.get(str(columna_ancla)) or "")
                    for rd in result_rows
                ]
                mapa_colores_tabla = asignar_colores_sensores(
                    sensores_unicos,
                    paleta_ancla,
                )

            # ── Estado de alarma opcional en la columna ultimo_dato ───────────────
            if mostrar_alarma and result_rows:
                columnas_auto_alarma = nivel_auto.get("columnas") or []
                columna_ultimo_dato_idx = next(
                    (
                        j for j, c in enumerate(columnas_auto_alarma)
                        if (c.get("origen") or {}).get("funcion") == "ultimo_dato"
                    ),
                    None,
                )
                if columna_ultimo_dato_idx is not None:
                    try:
                        from core.data_fetcher import fetch_umbrales_sensores  # noqa: PLC0415
                        from utils.gis_client import _orm_server_to_config  # noqa: PLC0415
                        from utils.alarma_sensor import evaluar_nivel_alarma  # noqa: PLC0415
                        from utils.alarma_palette import color_para_nivel    # noqa: PLC0415

                        _orm_server_t = context.get("_server")
                        if _orm_server_t is not None:
                            _server_cfg_t = _orm_server_to_config(_orm_server_t)
                            _sensores_t = [
                                str(rd.get("sensor") or rd.get(str(columna_ancla)) or "")
                                for rd in result_rows
                            ]
                            _df_umb_t = fetch_umbrales_sensores(_server_cfg_t, _sensores_t)
                            _umbrales_t: dict[str, dict] = {}
                            if not _df_umb_t.empty and "NOM_SENSOR" in _df_umb_t.columns:
                                for _, _fila_t in _df_umb_t.iterrows():
                                    _umbrales_t[str(_fila_t["NOM_SENSOR"])] = _fila_t.to_dict()

                            for _rd in result_rows:
                                _sn = str(_rd.get("sensor") or _rd.get(str(columna_ancla)) or "")
                                try:
                                    _last_v = float(_rd.get(str(columna_ultimo_dato_idx)))
                                except (TypeError, ValueError):
                                    continue
                                _nivel_t = evaluar_nivel_alarma(_last_v, _umbrales_t.get(_sn))
                                colores_alarma_tabla[_sn] = color_para_nivel(_nivel_t, paleta_alarma_tabla)

                            logger.info(
                                "[HTML] tabla %s: alarma calculada para %d sensores",
                                elem_id, len(colores_alarma_tabla),
                            )
                        else:
                            logger.warning(
                                "[HTML] tabla %s: mostrar_estado_alarma activo pero context['_server'] vacío; se omite",
                                elem_id,
                            )
                    except Exception:
                        logger.exception(
                            "[HTML] tabla %s: fallo obteniendo umbrales para alarma; se continúa sin pastillas",
                            elem_id,
                        )
        override_row_h: float | None = None
        override_font:  float | None = None

        if result_rows and not context.get("is_maquetacion"):
            default_row_h = float(nivel_auto.get("alto_fila") or 0.5)
            default_font  = float((nivel_auto.get("estilo") or {}).get("tamano") or 10)
            static_h      = sum(float(ns.get("alto_fila") or 0.5) for ns in niveles_stat)
            avail_h       = h - static_h
            n_rows        = len(result_rows)

            if avail_h > 0 and default_row_h > 0 and n_rows * default_row_h > avail_h:
                if overflow_mode == "paginar":
                    # Dividir: primera página recibe lo que cabe; el resto se encola
                    # para páginas de continuación generadas por _build_html.
                    max_rows_page1 = max(1, int(avail_h / default_row_h) - 1)
                    rows_remaining = result_rows[max_rows_page1:]
                    result_rows    = result_rows[:max_rows_page1]
                    if rows_remaining:
                        # Recopilar elementos con "grupo" definido que deben repetirse
                        # en las páginas de continuación (encabezado, pie, etc.).
                        _page_elems = context.get("_current_page_elementos") or {}
                        _repeat_elems = [
                            (ek, ed) for ek, ed in _page_elems.items()
                            if (ed.get("grupo") or {}).get("nombre")
                            and (ed.get("metadata") or {}).get("visible", True)
                        ]
                        ovf_q = context.setdefault("_tabla_overflow_queue", [])
                        ovf_q.append({
                            "elem_id":             elem_id,
                            "niveles_stat":        niveles_stat,
                            "nivel_auto":          nivel_auto,
                            "computed_header_rows": computed_header_rows,
                            "remaining_rows":      rows_remaining,
                            "geo":                 geo,
                            "page_w_cm":           context.get("_current_page_w_cm", 21.0),
                            "page_h_cm":           context.get("_current_page_h_cm", 29.7),
                            "page_class":          context.get("_current_page_class", "page-portrait"),
                            "default_row_h":       default_row_h,
                            "static_h":            static_h,
                            "repeat_elements":     _repeat_elems,
                        })
                        logger.info(
                            "[HTML] Overflow paginar: %d filas en pág1, %d a pág(s) extra",
                            len(result_rows), len(rows_remaining),
                        )
                else:
                    # Modo "truncar" (default): reducir fuente/alto; si sigue sin caber
                    # cortar filas y añadir indicador "… (+N filas)".
                    _MIN_ROW_H = 0.25
                    _MIN_FONT  = 6.0
                    adjusted_h    = avail_h / n_rows
                    ratio         = adjusted_h / default_row_h
                    adjusted_font = max(_MIN_FONT, round(default_font * ratio, 1))
                    adjusted_h    = max(_MIN_ROW_H, adjusted_h)

                    if n_rows * _MIN_ROW_H > avail_h:
                        max_rows     = max(1, int(avail_h / _MIN_ROW_H))
                        overflow_cnt = n_rows - (max_rows - 1)
                        result_rows  = result_rows[: max_rows - 1]
                        n_cols       = len(nivel_auto.get("columnas") or [])
                        overflow_row: dict[str, Any] = {str(jj): "" for jj in range(n_cols)}
                        overflow_row[str(max(0, columna_ancla))] = f"… (+{overflow_cnt} filas)"
                        overflow_row["sensor"] = ""
                        result_rows.append(overflow_row)
                        adjusted_h    = _MIN_ROW_H
                        adjusted_font = _MIN_FONT

                    override_row_h = adjusted_h
                    override_font  = adjusted_font
                    logger.info(
                        "[HTML] Auto-fit truncar: %d filas → row_h=%.3fcm font=%.1fpt avail=%.2fcm",
                        n_rows, adjusted_h, adjusted_font, avail_h,
                    )

        tabla_html = _build_html_cuadricula(
            niveles_stat, nivel_auto, result_rows,
            computed_header_rows=computed_header_rows,
            override_row_height_cm=override_row_h,
            override_font_size_pt=override_font,
            mapa_colores_ancla=mapa_colores_tabla or None,
            columna_ancla=columna_ancla,
            colores_alarma_por_sensor=colores_alarma_tabla or None,
            columna_ultimo_dato=columna_ultimo_dato_idx,
        )
        # Limpieza: el delta_horas inyectado solo aplica a esta tabla.
        context.pop("_current_delta_horas", None)
    else:
        # ── MODO FILA(S) ESTÁTICA(S) CON FUNCIONES ───────────────────────────
        logger.warning(
            "[DEBUG-STATIC-FN] elem_id=%s: %d nivel(es) estático(s) detectados",
            elem_id, len(niveles_stat),
        )
        # Use 3 placeholder rows for a single level (matches previous behaviour);
        # 1 row per level when there are multiple levels (each level is a header row).
        n_filas_mock = 3 if len(niveles_stat) == 1 else 1
        level_tables: list[str] = []
        for ns in niveles_stat:
            if context.get("is_maquetacion"):
                ns_rows = _generate_placeholder_rows(ns, 0, n_filas=n_filas_mock)
            else:
                ns_rows = _generate_static_fn_row(ns, context)
            level_tables.append(_build_html_cuadricula(None, ns, ns_rows, wrap=False))
        tabla_html = (
            '<div style="width:100%;height:100%;overflow:auto;font-family:Arial,sans-serif;">'
            '<div style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">'
            + "".join(level_tables)
            + "</div></div>"
        )

    return (
        f'<div style="position:absolute;left:{x}cm;top:{y}cm;'
        f'width:{w}cm;height:{h}cm;overflow:hidden;">'
        f'{tabla_html}</div>'
    )


# ── Mapa GIS ─────────────────────────────────────────────────────────────────

def _mapa_placeholder(container_style: str, mensaje: str) -> str:
    """Div de sustitución cuando no hay datos o falla la petición GIS."""
    style = (
        f"{container_style}"
        "display:flex;align-items:center;justify-content:center;"
        "color:#94a3b8;font-family:Arial,sans-serif;font-size:11px;"
    )
    return f'<div style="{style}">🗺 {mensaje}</div>'


def _elem_mapa_folium(
    elem: dict,
    context: dict,
    df,
    container_style: str,
    ancho: float,
    alto: float,
    mapa_cfg_override: dict | None = None,
) -> str:
    """Genera imagen PNG de un mapa Folium via Playwright screenshot.

    Transforma coordenadas EPSG:25831 → EPSG:4326 y renderiza un mapa
    cartográfico con marcadores de sensores. Devuelve placeholder si
    Folium, pyproj o Playwright no están disponibles.
    """
    try:
        import folium  # noqa: PLC0415
        from pyproj import Transformer  # noqa: PLC0415
    except ImportError:
        logger.warning("[HTML] _elem_mapa_folium: folium/pyproj no instalados")
        return _mapa_placeholder(container_style, "folium/pyproj no instalados")

    mapa_cfg    = mapa_cfg_override if mapa_cfg_override is not None else (elem.get("mapa_config") or {})
    folium_cfg  = mapa_cfg.get("folium") or {}
    tile_layer  = folium_cfg.get("tile_layer", "cartodb")
    zoom_padding = float(folium_cfg.get("zoom_padding", 50))
    paleta_sensores = folium_cfg.get("palette")  # None | "modern" | "corporate" | "vibrant"
    if paleta_sensores in (None, "", "ninguna", "null"):
        paleta_sensores = None
    anticolision_raw  = folium_cfg.get("algoritmo_anticolision", False)
    usar_anticolision = (
        anticolision_raw is True
        or str(anticolision_raw).lower() == "true"
    )
    escala_imagen = int(folium_cfg.get("escala_imagen", 1))
    escala_imagen = max(1, min(3, escala_imagen))
    grosor_leader   = float(folium_cfg.get("grosor_leader", 2.0))
    opacidad_leader = float(folium_cfg.get("opacidad_leader", 0.75))
    leader_dashed   = bool(folium_cfg.get("leader_dashed", False))
    opacidad_fondo  = float(folium_cfg.get("opacidad_fondo", 1.0))
    debug_cuadricula = bool(folium_cfg.get("debug_cuadricula", False))
    radio_marcador = int(folium_cfg.get("radio_marcador", 4))  # px base del CircleMarker
    w_px_int = int(round(ancho * _CM_TO_PX * escala_imagen))
    h_px_int = int(round(alto  * _CM_TO_PX * escala_imagen))
    dist_min_marcador = int(folium_cfg.get("dist_min_marcador", 50))
    dist_min_marcador = max(20, min(200, dist_min_marcador))
    dist_base_min = int(folium_cfg.get("dist_base_min", 60))
    dist_base_min = max(30, min(250, dist_base_min))
    margen_marker = int(folium_cfg.get("margen_marker", 20))
    margen_marker = max(8, min(80, margen_marker))

    # ── Flags opcionales: etiqueta extendida y color marcador por alarma ──────
    mostrar_valor_etiqueta = bool(folium_cfg.get("mostrar_valor_etiqueta", False))
    color_marcador_alarma  = bool(folium_cfg.get("color_marcador_por_alarma", True))
    paleta_alarma          = str(folium_cfg.get("paleta_alarma") or "semaforo")
    color_valor_por_alarma = bool(folium_cfg.get("color_valor_por_alarma", True))

    try:
        transformer = Transformer.from_crs("EPSG:25831", "EPSG:4326", always_xy=True)
        lons, lats = transformer.transform(df["X"].tolist(), df["Y"].tolist())
        nom_sensores = df["NOM_SENSOR"].tolist()

        # Bounds con padding proporcional al rango de coordenadas
        lat_pad = zoom_padding * 0.000009   # ~1 m en lat ≈ 1e-5 grados
        lon_pad = zoom_padding * 0.000012   # ~1 m en lon ≈ 1.2e-5 grados (latitud 40°)
        lat_min = min(lats) - lat_pad
        lat_max = max(lats) + lat_pad
        lon_min = min(lons) - lon_pad
        lon_max = max(lons) + lon_pad

        m = folium.Map(
            tiles=None,
            control_scale=False,
            zoom_control=False,
            attributionControl=False,
        )
        m.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]])

        if tile_layer == "esri":
            folium.TileLayer(
                tiles=(
                    "https://server.arcgisonline.com/ArcGIS/rest/services/"
                    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
                ),
                attr=" ",
                name="Esri",
                control=False,
                opacity=opacidad_fondo,
            ).add_to(m)
        else:
            folium.TileLayer(
                "CartoDB positron",
                name="CartoDB",
                attr=" ",
                control=False,
                opacity=opacidad_fondo,
            ).add_to(m)

        from utils.sensor_palette import asignar_colores_sensores  # noqa: PLC0415
        mapa_colores: dict[str, str] = (
            asignar_colores_sensores([str(n) for n in nom_sensores], paleta_sensores)
            if paleta_sensores else {}
        )

        # ── Fetch opcional de último valor + umbrales para semáforo de alarma ─────
        ultimos_valores: dict[str, float | None] = {}
        umbrales_por_sensor: dict[str, dict] = {}

        if mostrar_valor_etiqueta or color_marcador_alarma or color_valor_por_alarma:
            try:
                from core.data_fetcher import fetch_temporal_data, fetch_umbrales_sensores  # noqa: PLC0415
                from utils.gis_client import _orm_server_to_config  # noqa: PLC0415
                _orm_server = context.get("_server")
                if _orm_server is not None:
                    _server_cfg = _orm_server_to_config(_orm_server)
                    _sensores_lista = [str(s) for s in nom_sensores]

                    # Histórico para sacar last_y
                    sensores_csv = ",".join(_sensores_lista)
                    fecha_ini = context.get("fecha_inicio") or context.get("fecha_inicial") or ""
                    fecha_fin = context.get("fecha_fin")    or context.get("fecha_final")    or ""
                    _result = fetch_temporal_data(_server_cfg, sensores_csv, fecha_ini, fecha_fin)
                    _historico = _result.get("historico") or []
                    import pandas as _pd  # noqa: PLC0415
                    if _historico:
                        _df_hist = _pd.DataFrame(_historico)
                        if "NOM_SENSOR" in _df_hist.columns and "MEDIDA" in _df_hist.columns:
                            for _sn, _grp in _df_hist.groupby("NOM_SENSOR"):
                                try:
                                    ultimos_valores[str(_sn)] = float(_grp["MEDIDA"].iloc[-1])
                                except (ValueError, TypeError, IndexError):
                                    ultimos_valores[str(_sn)] = None

                    # Umbrales (si va a colorear marcador o el valor de la etiqueta)
                    if color_marcador_alarma or color_valor_por_alarma:
                        _df_umb = fetch_umbrales_sensores(_server_cfg, _sensores_lista)
                        if not _df_umb.empty and "NOM_SENSOR" in _df_umb.columns:
                            for _, _fila in _df_umb.iterrows():
                                umbrales_por_sensor[str(_fila["NOM_SENSOR"])] = _fila.to_dict()
                else:
                    logger.warning(
                        "[HTML] _elem_mapa_folium: alarma/etiqueta activadas pero "
                        "context['_server'] vacío; features deshabilitadas para elem=%s",
                        elem.get("id"),
                    )
            except Exception:
                logger.exception(
                    "[HTML] _elem_mapa_folium: fallo obteniendo histórico/umbrales; "
                    "se continúa sin las features"
                )

        # ── Pre-cálculo de niveles de alarma y textos extendidos ─────────────
        from utils.alarma_sensor import evaluar_nivel_alarma  # noqa: PLC0415
        from utils.alarma_palette import color_para_nivel    # noqa: PLC0415

        textos_etiqueta: dict[str, str] = {}
        colores_marcador: dict[str, str] = {}
        niveles_alarma: dict[str, int] = {}
        colores_valor_alarma: dict[str, str | None] = {}

        for _nom in nom_sensores:
            _key = str(_nom)
            _last = ultimos_valores.get(_key)

            # Texto de etiqueta: nombre [+ valor con 2 decimales si flag activo]
            if mostrar_valor_etiqueta and _last is not None:
                textos_etiqueta[_key] = f"{_nom}  {_last:+.2f}"
            else:
                textos_etiqueta[_key] = str(_nom)

            # Nivel de alarma y color de marcador
            if color_marcador_alarma:
                _nivel = evaluar_nivel_alarma(_last, umbrales_por_sensor.get(_key))
                niveles_alarma[_key] = _nivel
                colores_marcador[_key] = color_para_nivel(_nivel, paleta_alarma)
            else:
                colores_marcador[_key] = "#16a34a"  # verde por defecto (legacy)

            # Color del valor de la etiqueta según nivel de alarma (opt-in independiente)
            if color_valor_por_alarma and mostrar_valor_etiqueta and _last is not None:
                # Reutiliza el nivel ya calculado si color_marcador_alarma está activo;
                # si no, lo calcula ahora (evita doble cómputo cuando ambos flags están on).
                if color_marcador_alarma:
                    _nivel_v = niveles_alarma.get(_key, 0)
                else:
                    _nivel_v = evaluar_nivel_alarma(_last, umbrales_por_sensor.get(_key))
                colores_valor_alarma[_key] = color_para_nivel(_nivel_v, paleta_alarma)
            else:
                colores_valor_alarma[_key] = None

        # ── Marcadores de sensores (CircleMarker — siempre) ───────────────────
        for lon, lat, nom in zip(lons, lats, nom_sensores):
            _color_marker = colores_marcador.get(str(nom), "#16a34a")
            folium.CircleMarker(
                location=[lat, lon],
                radius=radio_marcador * escala_imagen,
                color=_color_marker,
                fill=True,
                fill_color=_color_marker,
                fill_opacity=0.8,
            ).add_to(m)

        # ── Pre-formatear HTML de etiqueta por sensor ────────────────────────
        # Texto plano cuando no hay coloreado del valor (comportamiento legacy).
        # Dos spans cuando color_valor_por_alarma está activo y hay valor: el
        # nombre hereda el color del div externo; el valor lo sobreescribe con
        # el color de alarma. Misma fuente/tamaño/peso → bbox JS sin cambios.
        etiquetas_html: dict[str, str] = {}
        for _nom in nom_sensores:
            _key = str(_nom)
            _color_v = colores_valor_alarma.get(_key)
            _texto = textos_etiqueta.get(_key, _key)
            if _color_v and "  " in _texto:
                # Separa "nombre  valor" en dos partes (doble espacio = separador)
                _nombre_parte, _valor_parte = _texto.split("  ", 1)
                etiquetas_html[_key] = (
                    f'<span>{_nombre_parte}</span>'
                    f'<span style="color:{_color_v};">  {_valor_parte}</span>'
                )
            else:
                etiquetas_html[_key] = _texto  # plano (sin spans)

        # ── Etiquetas: modo simple (DivIcon offset fijo) o JS post-render ────
        if usar_anticolision:
            logger.info("[HTML] _elem_mapa_folium: anti-colisión JS activado")
            # Inyectar datos de sensores como JSON global
            sensores_json = json.dumps(
                [
                    {
                        "lat": lat,
                        "lon": lon,
                        "texto": textos_etiqueta.get(str(nom), str(nom)),
                        "html":  etiquetas_html.get(str(nom), str(nom)),
                        "color": mapa_colores.get(str(nom), "#1e293b"),
                    }
                    for lon, lat, nom in zip(lons, lats, nom_sensores)
                ],
                ensure_ascii=False,
            )
            # Inyectar configuración de leaders antes del script de anticolisión
            config_leader_js = (
                "<script>window.__configLeader = {"
                f"\"weight\": {grosor_leader}, "
                f"\"opacity\": {opacidad_leader}, "
                f"\"dashed\": {str(leader_dashed).lower()}, "
                f"\"gridDebug\": {str(debug_cuadricula).lower()}"
                "};</script>"
            )
            m.get_root().html.add_child(folium.Element(config_leader_js))
            # Leer el script JS de anticolisión
            _js_path = Path(__file__).resolve().parent.parent / "utils" / "mapa_anticolision.js"
            _js_code = _js_path.read_text(encoding="utf-8")
            # Datos de sensores: envolver en {% raw %} para que Jinja2 no interprete
            # llaves {} del JSON como variables de template
            m.get_root().html.add_child(folium.Element(
                '{% raw %}<script>'
                'window.__sensoresData = ' + sensores_json + ';'
                'window.__anticolisionEnabled = true;'
                'window.__distMinMarcador = ' + str(dist_min_marcador) + ';'
                'window.__distBaseMin = ' + str(dist_base_min) + ';'
                'window.__margenMarker = ' + str(margen_marker) + ';'
                '</script>{% endraw %}'
            ))
            # Script de anticolisión: también en {% raw %} por seguridad
            m.get_root().html.add_child(folium.Element(
                '{% raw %}<script>' + _js_code + '</script>{% endraw %}'
            ))
        else:
            # Modo simple: DivIcon con offset fijo, sin sombreado
            for lon, lat, nom in zip(lons, lats, nom_sensores):
                color_etiqueta = mapa_colores.get(str(nom), "#1e293b")
                folium.Marker(
                    location=[lat, lon],
                    icon=folium.DivIcon(
                        html=(
                            f'<div style="font-size:{9 * escala_imagen}px;color:{color_etiqueta};'
                            f'white-space:nowrap;'
                            f'margin-left:-15px;margin-top:10px;">'
                            f'{etiquetas_html.get(str(nom), str(nom))}</div>'
                        ),
                        icon_size=(200, 20),
                        icon_anchor=(0, 0),
                    ),
                ).add_to(m)

        html_content = m.get_root().render()
    except Exception as exc:  # noqa: BLE001
        logger.error("[HTML] _elem_mapa_folium: error construyendo mapa: %s", exc)
        return _mapa_placeholder(container_style, "Error construyendo mapa Folium")

    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(
                    viewport={"width": w_px_int, "height": h_px_int},
                    device_scale_factor=escala_imagen,
                )
                page.set_content(html_content, wait_until="domcontentloaded")
                # Esperar tiles con timeout tolerante (no bloquear si ESRI tarda)
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:  # noqa: BLE001
                    logger.warning(
                        "[HTML] _elem_mapa_folium: tiles no terminaron de cargar en 8s, continuando"
                    )
                if usar_anticolision:
                    # Esperar a que el script JS de anticolisión termine y señalice con #__anticolision_done
                    try:
                        page.wait_for_selector("#__anticolision_done", timeout=12000)
                    except Exception:  # noqa: BLE001
                        logger.warning(
                            "[HTML] _elem_mapa_folium: timeout esperando anticolisión JS, "
                            "usando screenshot tal cual"
                        )
                    # Pequeña pausa extra para que Leaflet pinte los marcadores recién añadidos
                    page.wait_for_timeout(500)
                else:
                    page.wait_for_timeout(1500)
                png_bytes = page.screenshot(type="png", full_page=False)
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001
        logger.error("[HTML] _elem_mapa_folium: error Playwright: %s", exc)
        return _mapa_placeholder(container_style, "Error renderizando mapa")

    b64 = base64.b64encode(png_bytes).decode("ascii")

    raw_pos    = mapa_cfg.get("posicion_imagen", "center")
    posicion   = raw_pos.get("valor", "center") if isinstance(raw_pos, dict) else (raw_pos or "center")
    _pos_map   = {
        "center": "center center", "top": "center top",
        "bottom": "center bottom", "left": "left center", "right": "right center",
    }
    obj_pos    = _pos_map.get(posicion, "center center")
    raw_ajuste = mapa_cfg.get("ajuste", "cover")
    ajuste     = raw_ajuste.get("valor", "cover") if isinstance(raw_ajuste, dict) else (raw_ajuste or "cover")

    return (
        f'<div style="{container_style}">'
        f'<img src="data:image/png;base64,{b64}" '
        f'style="width:100%;height:100%;'
        f'object-fit:{ajuste};object-position:{obj_pos};" />'
        f'</div>'
    )


def _elem_mapa(elem: dict, context: dict) -> str:
    """Genera el HTML de un elemento ``mapa``.

    Soporta dos fuentes (``mapa_config.fuente``):
    - ``"gis"`` (por defecto): imagen PNG desde la API gis2png (TunnelData).
    - ``"folium"``: mapa cartográfico generado con Folium + Playwright.

    Si cualquier paso falla, devuelve un placeholder sin lanzar excepción
    que aborte el informe completo.
    """
    from utils.gis_client import (  # noqa: PLC0415
        GisClient, GisRequest, calcular_area, sensores_a_csv, _orm_server_to_config,
    )
    from core.data_fetcher import fetch_sensor_coords  # noqa: PLC0415

    geo      = elem.get("geometria") or {}
    est      = elem.get("estilo") or {}
    mapa_cfg = elem.get("mapa_config") or {}
    elem_id  = elem.get("id") or ""

    # ── Overrides del wizard (mapa_config_overrides + custom_chart_settings) ────
    _gis_fields    = {"operacion", "obra", "sistema", "capas", "padding", "ancho_minimo"}
    _folium_fields = {"tile_layer", "algoritmo_anticolision", "zoom_padding", "escala_imagen", "dist_min_marcador", "dist_base_min", "margen_marker", "palette", "mostrar_valor_etiqueta", "color_marcador_por_alarma", "paleta_alarma", "color_valor_por_alarma", "grosor_leader", "opacidad_leader", "leader_dashed", "opacidad_fondo", "debug_cuadricula"}
    _common_fields = {"posicion_imagen", "ajuste"}
    _overrides = {
        **(context.get("mapa_config_overrides") or {}).get(elem_id, {}),
        **(context.get("custom_chart_settings") or {}).get(elem_id, {}),
    }
    if _overrides:
        for _k, _v in _overrides.items():
            if _k in _gis_fields:
                mapa_cfg = {**mapa_cfg, "gis": {**(mapa_cfg.get("gis") or {}), _k: _v}}
            elif _k in _folium_fields:
                mapa_cfg = {**mapa_cfg, "folium": {**(mapa_cfg.get("folium") or {}), _k: _v}}
            elif _k in _common_fields:
                mapa_cfg = {**mapa_cfg, _k: _v}

    x     = float(geo.get("x", 0))
    y     = float(geo.get("y", 0))
    ancho = float(geo.get("ancho", 10))
    alto  = float(geo.get("alto", 8))

    w_px = int(round(ancho * _CM_TO_PX))
    h_px = int(round(alto  * _CM_TO_PX))

    # ── CSS del contenedor ────────────────────────────────────────────────────
    grosor_borde  = float(est.get("grosor_borde") or est.get("border_width") or 0)
    color_borde   = _css_color(est.get("color_borde") or est.get("border_color"), "transparent")
    color_relleno = _css_color(est.get("color_relleno") or est.get("background"), "transparent")
    border_radius = float(est.get("border_radius") or est.get("radio_borde") or 0)
    border_css    = f"{grosor_borde}px solid {color_borde}" if grosor_borde > 0 else "none"

    container_style = (
        f"position:absolute;left:{x}cm;top:{y}cm;"
        f"width:{ancho}cm;height:{alto}cm;"
        f"overflow:hidden;box-sizing:border-box;"
        f"border:{border_css};"
        f"background:{color_relleno};"
        f"border-radius:{border_radius}px;"
    )

    # ── Diagnóstico inicial ───────────────────────────────────────────────────
    _emit_log(
        "MAPA_START", elem_id=elem_id,
        sensores_raw=context.get("sensores_1") or context.get("sensores"),
        server_present=("_server" in context),
        server_type=type(context.get("_server")).__name__,
        server_id_en_context=context.get("server_id"),
        mapa_cfg=mapa_cfg,
    )

    # ── Sensores del contexto ─────────────────────────────────────────────────
    sensores_raw = context.get("sensores_1") or context.get("sensores", [])
    if isinstance(sensores_raw, str):
        sensores_raw = [
            s.strip()
            for s in sensores_raw.replace("\n", ",").split(",")
            if s.strip()
        ]
    sensores = list(sensores_raw)

    if not sensores:
        _emit_log(
            "MAPA_ERROR", elem_id=elem_id, motivo="sin_sensores",
            sensores_1=context.get("sensores_1"),
            sensores=context.get("sensores"),
        )
        return _mapa_placeholder(container_style, "Sin sensores configurados")

    # ── Servidor ──────────────────────────────────────────────────────────────
    server = context.get("_server")
    if server is None:
        _emit_log(
            "MAPA_ERROR", elem_id=elem_id, motivo="server_none",
            context_keys=list(context.keys()),
            server_id_en_context=context.get("server_id"),
        )
        logger.error(
            "[HTML] _elem_mapa: _server es None. "
            "context keys: %s | server_id: %r | _server type: %s",
            list(context.keys()),
            context.get("server_id"),
            type(context.get("_server")).__name__,
        )
        return _mapa_placeholder(container_style, "Servidor no disponible")

    # ── Coordenadas X, Y desde la BD ─────────────────────────────────────────
    try:
        df = fetch_sensor_coords(_orm_server_to_config(server), sensores)
    except Exception as exc:  # noqa: BLE001
        _emit_log(
            "MAPA_ERROR", elem_id=elem_id, motivo="coords_error",
            server_nombre=getattr(server, "nombre", None),
            server_host=getattr(server, "host", None),
            sensores=sensores, error=str(exc),
        )
        logger.error(
            "[HTML] _elem_mapa: error coordenadas | server=%r host=%r sensores=%r | %s",
            getattr(server, "nombre", None), getattr(server, "host", None),
            sensores, exc,
        )
        return _mapa_placeholder(container_style, "Error al obtener coordenadas")

    if df.empty:
        _emit_log(
            "MAPA_ERROR", elem_id=elem_id, motivo="coords_vacias",
            server_nombre=getattr(server, "nombre", None),
            sensores=sensores,
        )
        logger.warning(
            "[HTML] _elem_mapa: sin coordenadas | server=%r sensores=%r",
            getattr(server, "nombre", None), sensores,
        )
        return _mapa_placeholder(container_style, "Sin coordenadas para los sensores")

    # ── Fuente del mapa ───────────────────────────────────────────────────────
    fuente = mapa_cfg.get("fuente", "gis")
    if fuente == "folium":
        return _elem_mapa_folium(elem, context, df, container_style, ancho, alto, mapa_cfg_override=mapa_cfg)

    # ── Rama GIS ─────────────────────────────────────────────────────────────
    def _unref(raw, default):
        """Desempaqueta un valor que puede ser escalar o {ref, valor} del wizard."""
        if isinstance(raw, dict):
            return raw.get("valor", default)
        return raw if raw is not None else default

    gis_cfg   = mapa_cfg.get("gis") or {}

    operacion = _unref(
        gis_cfg.get("operacion") or mapa_cfg.get("operacion"), "planoarea"
    ) or "planoarea"
    obra      = _unref(gis_cfg.get("obra")    or mapa_cfg.get("obra"),    None) or None
    sistema   = _unref(gis_cfg.get("sistema") or mapa_cfg.get("sistema"), None) or None
    capas     = _unref(gis_cfg.get("capas")   or mapa_cfg.get("capas"),   None) or None
    padding   = float(_unref(
        gis_cfg.get("padding") or mapa_cfg.get("padding"), 50
    ) or 50)

    raw_minimo = gis_cfg.get("ancho_minimo") or mapa_cfg.get("ancho_minimo", 200)
    ancho_min  = float(_unref(raw_minimo, 200) or 200)

    try:
        area = calcular_area(df["X"].tolist(), df["Y"].tolist(), padding, ancho_min)
    except Exception as exc:  # noqa: BLE001
        _emit_log(
            "MAPA_ERROR", elem_id=elem_id, motivo="area_error",
            xs=df["X"].tolist(), ys=df["Y"].tolist(), error=str(exc),
        )
        logger.error("[HTML] _elem_mapa: error calculando área GIS: %s", exc)
        return _mapa_placeholder(container_style, "Error calculando área del mapa")

    sensor_csv     = sensores_a_csv(df["NOM_SENSOR"].tolist())
    gis_url_server = getattr(server, "url_gis", None)

    req = GisRequest(
        operacion=operacion,
        sensor=sensor_csv,
        area=area,
        size=f"w:{w_px}xh:{h_px}",
        obra=obra or None,
        sistema=sistema or None,
        capas=capas or None,
    )

    gis_client   = GisClient.from_server(server)
    url_completa = gis_client.get_url(req)
    _emit_log(
        "MAPA_GIS_REQUEST", elem_id=elem_id,
        server_nombre=getattr(server, "nombre", None),
        gis_url=gis_url_server,
        operacion=operacion,
        obra_valor=obra,
        sensor_csv=sensor_csv,
        area=area,
        size=f"w:{w_px}xh:{h_px}",
        sistema=sistema,
        capas=capas,
        url_completa=url_completa,
    )
    logger.info(
        "[HTML] _elem_mapa: request GIS | server=%r | obra=%r | url=%s",
        getattr(server, "nombre", None), obra, url_completa,
    )

    # ── Petición a la API GIS, codificación base64 ────────────────────────────
    tmp_path: str | None = None
    try:
        tmp_path = gis_client.save_temp(req)
        with open(tmp_path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
    except Exception as exc:  # noqa: BLE001
        _emit_log(
            "MAPA_ERROR", elem_id=elem_id, motivo="api_error",
            url_intentada=getattr(exc, "url", None),
            error=str(exc),
        )
        logger.error(
            "[HTML] _elem_mapa: error API GIS | server=%r gis_url=%r | %s",
            getattr(server, "nombre", None), gis_url_server, exc,
        )
        return _mapa_placeholder(container_style, "Error obteniendo imagen del mapa")
    finally:
        if tmp_path and Path(tmp_path).exists():
            try:
                Path(tmp_path).unlink()
            except OSError:
                pass

    # ── object-position / ajuste ──────────────────────────────────────────────
    raw_pos  = mapa_cfg.get("posicion_imagen", "center")
    posicion = raw_pos.get("valor", "center") if isinstance(raw_pos, dict) else (raw_pos or "center")
    _pos_map = {
        "center": "center center",
        "top":    "center top",
        "bottom": "center bottom",
        "left":   "left center",
        "right":  "right center",
    }
    obj_pos = _pos_map.get(posicion, "center center")

    raw_ajuste = mapa_cfg.get("ajuste", "cover")
    ajuste = raw_ajuste.get("valor", "cover") if isinstance(raw_ajuste, dict) else (raw_ajuste or "cover")

    _emit_log(
        "MAPA_OK", elem_id=elem_id,
        server_nombre=getattr(server, "nombre", None),
        sensores_encontrados=len(df),
        area=area,
        size=f"{w_px}x{h_px}",
    )

    return (
        f'<div style="{container_style}">'
        f'<img src="data:image/png;base64,{b64}" '
        f'style="width:100%;height:100%;'
        f'object-fit:{ajuste};object-position:{obj_pos};" />'
        f'</div>'
    )


# ── Caption / descripción de elementos complejos ─────────────────────────────

def _elem_caption_html(elem: dict, context: dict) -> str:
    """Devuelve un div absolutamente posicionado con la descripción del elemento.

    Lee ``configuracion.descripcion`` (grafico/tabla) o ``mapa_config.descripcion``
    (mapa), resuelve tokens y genera un div debajo del elemento principal.
    Devuelve cadena vacía si no hay descripción.
    """
    tipo = elem.get("tipo", "")
    if tipo == "grafico":
        desc_raw: str = (elem.get("configuracion") or {}).get("descripcion") or ""
    elif tipo == "mapa":
        desc_raw = (elem.get("mapa_config") or {}).get("descripcion") or ""
    else:
        return ""
    # Override desde wizard (custom_chart_settings[elem_id]["descripcion"] tiene prioridad)
    elem_id = elem.get("id", "")
    _wizard_desc = (context.get("custom_chart_settings") or {}).get(elem_id, {}).get("descripcion") or ""
    desc_raw = _wizard_desc or desc_raw
    if not desc_raw:
        return ""
    desc = _resolve_tokens(desc_raw, context)
    geo  = elem.get("geometria") or {}
    x    = float(geo.get("x", 0))
    y    = float(geo.get("y", 0))
    h    = float(geo.get("alto", 8))
    w    = float(geo.get("ancho", 15))
    return (
        f'<div style="position:absolute;left:{x}cm;top:{y + h}cm;'
        f'width:{w}cm;font-size:8pt;color:#666;text-align:center;padding-top:4px;">'
        f'{_html_std.escape(desc)}</div>'
    )


# ── Ejecución de scripts de gráficos ─────────────────────────────────────────

def _run_script(
    script_name: str,
    params: dict,
    figsize: tuple,
    context: dict,
    elem_id: str = "",
) -> str | None:
    """Importa un script de gráfico HTML y llama a su función ``generate()``.

    Soporta:
    - Rutas con namespace: ``"html/grafico_base_plotly.py"`` → resuelve
      directamente desde ``biblioteca_graficos/``.
    - Nombre plano legacy: ``"grafico.py"`` → busca en ``html/`` primero,
      luego en la raíz de ``biblioteca_graficos/``.

    El módulo se recarga en cada llamada (sin caché) para garantizar código
    actualizado durante el desarrollo.

    Returns:
        Cadena HTML lista para embebir, o ``None`` si el script falla.
    """
    if not script_name.endswith(".py"):
        script_name += ".py"

    if "/" in script_name or "\\" in script_name:
        # Ruta con namespace: resolver directamente desde la raíz de graficos
        script_path = _GRAFICOS_ROOT / script_name
        if not script_path.is_file():
            logger.warning("[HTML] Script no encontrado (namespace): %s", script_name)
            return None
    else:
        # Nombre plano: buscar en graficos/html/, luego tablas/html/, luego raíz
        script_path = _GRAFICOS_HTML / script_name
        if not script_path.is_file():
            script_path = _TABLAS_HTML / script_name
        if not script_path.is_file():
            script_path = _GRAFICOS_LEGACY / script_name
        if not script_path.is_file():
            logger.warning("[HTML] Script no encontrado: %s", script_name)
            return None

    module_name = f"_html_grafico_{script_path.stem}"
    sys.modules.pop(module_name, None)

    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except Exception as exc:
        logger.exception("[HTML] Error cargando script '%s': %s", script_name, exc)
        _emit_log("SCRIPT_ERROR", script=script_name, elem_id=elem_id, error=f"load: {exc}")
        return None

    generate_fn = getattr(module, "generate", None)
    if generate_fn is None:
        logger.warning("[HTML] Script '%s' no define generate()", script_name)
        _emit_log("SCRIPT_ERROR", script=script_name, elem_id=elem_id, error="no define generate()")
        return None

    # ── Aplicar custom_chart_settings del contexto ───────────────────────────
    # Se aplica aquí (en lugar de solo en _elem_grafico) para que funcione
    # también cuando _run_script se llama directamente
    # (ej. render_preview_graficos).
    _custom_settings = (context.get("custom_chart_settings") or {}).get(elem_id, {})
    if _custom_settings:
        # Filtrar: no sobrescribir tokens $CURRENT ya resueltos ni parámetros
        # primarios de contexto (sensor/fechas) que son dinámicos por diseño.
        _custom_clean = {
            k: v for k, v in _custom_settings.items()
            if v is not None
            and not (isinstance(v, str) and v.startswith("$"))
            and k not in _DYNAMIC_CTX_PARAMS
        }
        if _custom_clean:
            params = {**params, **_custom_clean}

    # ── Detección de firma y obtención de datos ────────────────────────────
    # Firma legacy ``generate(data, parametros)``: primer parámetro llamado "data".
    #   → Obtener datos del servidor y pasar como primer argumento.
    # Firma nueva  ``generate(params, figsize)``: scripts HTML modernos.
    #   → Inyectar datos fetched en params["data"] SOLO si el template declaró
    #     explícitamente un parámetro "data". Scripts que leen de ficheros locales
    #     (inclinómetros, etc.) NO declaran "data" y no deben provocar una consulta
    #     SQL innecesaria aunque el contexto tenga server_id.
    param_names = list(inspect.signature(generate_fn).parameters.keys())
    try:
        if param_names and param_names[0] == "data":
            # Estilo antiguo: pasar data dict como primer argumento
            data = _fetch_script_data(params, context)
            result = generate_fn(data, params)
        else:
            # Estilo moderno HTML: inyectar datos en params["data"] si hace falta.
            # Orden de prioridad para evitar consultas duplicadas al servidor:
            #   1. params["data"]  — ya resuelto por _resolve_params ($CURRENT_data)
            #   2. context["data"] — inyectado por el job runner o preview
            #   3. fetch desde server_id — SOLO cuando el template declaró "data"
            if "data" in params and not params.get("data"):
                ctx_data = context.get("data") or {}
                if ctx_data.get("historico"):
                    params = {**params, "data": ctx_data}
                elif context.get("server_id"):
                    params = {**params, "data": _fetch_script_data(params, context)}

            # Fetch condicional de umbrales (solo si el script lo declara y el usuario lo activó)
            _umbrales_origen = str(params.get("umbrales_origen") or "off").lower()
            if _umbrales_origen == "auto_bd":
                try:
                    from core.data_fetcher import fetch_umbrales_sensores  # noqa: PLC0415
                    from utils.gis_client import _orm_server_to_config  # noqa: PLC0415
                    _sensor_param = str(params.get("sensor") or "").strip()
                    _sensores = [s.strip() for s in _sensor_param.split(",") if s.strip()]
                    if _sensores:
                        _orm_server = context.get("_server")
                        if _orm_server:
                            _server_cfg = _orm_server_to_config(_orm_server)
                            _df_umb = fetch_umbrales_sensores(_server_cfg, _sensores)
                            data_dict = dict(params.get("data") or {})
                            data_dict.setdefault("umbrales", _df_umb.to_dict(orient="records"))
                            params = {**params, "data": data_dict}
                        else:
                            logger.warning(
                                "umbrales auto_bd solicitado pero context['_server'] vacío; se omite (elem=%s)",
                                elem_id,
                            )
                except Exception:
                    logger.exception(
                        "Fallo al obtener umbrales para gráfico %s; se continúa sin umbrales", elem_id
                    )

            logger.warning(
                "[HTML][DBG] _run_script pre-generate | script=%s elem_id=%s sensor=%r params_keys=%s",
                script_name, elem_id,
                params.get("sensor") or params.get("sensores_1") or params.get("sensores"),
                list(params.keys()),
            )
            result = generate_fn(params, figsize)
    except PermissionError:
        raise
    except Exception as exc:
        logger.exception("[HTML] Error ejecutando '%s': %s", script_name, exc)
        _emit_log("SCRIPT_ERROR", script=script_name, elem_id=elem_id, error=str(exc))
        return None

    if isinstance(result, str):
        _emit_log("SCRIPT_OK", script=script_name, elem_id=elem_id, html_len=len(result))
        return result
    logger.warning("[HTML] Script '%s' devolvió %s (se espera str)", script_name, type(result).__name__)
    _emit_log("SCRIPT_ERROR", script=script_name, elem_id=elem_id,
              error=f"tipo inesperado: {type(result).__name__}")
    return None


# ── Resolución de parámetros ($CURRENT) ──────────────────────────────────────

def _resolve_params(
    params_raw: dict,
    context: dict,
    elem_id: str | None = None,
) -> dict:
    """Reemplaza tokens ``$CURRENT`` y ``$CURRENT_*`` con valores del contexto.

    Soporta ``mapeo_parametros`` anidado por elemento, inyecta ``context["data"]``
    si no está presente, y sanitiza parámetros numéricos (listas/tuplas → primer
    elemento → float).
    """
    mapeo: dict = context.get("mapeo_parametros") or {}
    elem_mapeo: dict = {}
    if elem_id:
        candidate = mapeo.get(elem_id)
        if isinstance(candidate, dict):
            elem_mapeo = candidate

    resolved: dict = {}
    for k, v in params_raw.items():
        is_current = v == "$CURRENT" or (
            isinstance(v, str) and v.startswith("$CURRENT_")
        )
        if is_current:
            if k in elem_mapeo:
                col_key = elem_mapeo[k]
                if col_key:
                    # Normalizar clave: "sensores 1" → "sensores_1".
                    # Doble intento: primero con guion bajo, luego con la clave
                    # original (el contexto puede almacenarla con espacio).
                    col_key_norm = col_key.strip().replace(" ", "_") if isinstance(col_key, str) else col_key
                    val = context.get(col_key_norm)
                    if val is None and isinstance(col_key, str):
                        val = context.get(col_key.strip())
                    # Retrocompatible: si el valor del contexto es él mismo un
                    # token $CURRENT (e.g. sensores_1="$CURRENT"), delegarlo al
                    # lookup semántico en lugar de usarlo literalmente.
                    if isinstance(val, str) and (val == "$CURRENT" or val.startswith("$CURRENT_")):
                        val = _ctx_lookup(k, context)
                    resolved[k] = val
                else:
                    # Sin mapeo explícito → resolución semántica
                    resolved[k] = _ctx_lookup(k, context)
            elif k in mapeo and not isinstance(mapeo.get(k), dict):
                col_key = mapeo[k]
                resolved[k] = context.get(col_key)
            elif elem_id and elem_id in mapeo:
                # Elemento con wizard configurado pero este param ausente del mapeo →
                # política estricta: no hacer fallback al contexto global.
                resolved[k] = None
            else:
                resolved[k] = _ctx_lookup(k, context)
        elif isinstance(v, dict) and "ref" in v:
            # Valor almacenado como referencia de columna estructurada:
            # {"ref": "primario", "label": "sensores 1", "valor": "sensores 1"}.
            # Extraer la clave de columna y buscar en el contexto con doble intento.
            col_ref = str(v.get("valor") or v.get("label") or "").strip()
            if col_ref:
                col_norm = col_ref.replace(" ", "_")
                val = context.get(col_norm)
                if val is None:
                    val = context.get(col_ref)
                resolved[k] = val
            else:
                resolved[k] = None
        else:
            resolved[k] = v

    # Inyectar params del mapeo wizard que NO aparecen en params_raw.
    # Sucede cuando la plantilla omite "sensor": "$CURRENT" en parametros pero el
    # wizard sí tiene el mapeo configurado → la resolución debe ocurrir igualmente.
    # Si el context lookup devuelve None (p.ej. el valor es una opción fija como
    # "abs_dev_a" y no una columna de BD), se usa col_key como valor literal para
    # que parámetros con opciones fijas fluyan directamente al script.
    for k, col_key in elem_mapeo.items():
        if k in resolved:
            continue
        if col_key:
            col_key_norm = col_key.strip().replace(" ", "_") if isinstance(col_key, str) else col_key
            val = context.get(col_key_norm)
            if val is None and isinstance(col_key, str):
                val = context.get(col_key.strip())
            # Retrocompatible: si el valor almacenado en context es él mismo un
            # token $CURRENT, delegar al lookup semántico en lugar de propagarlo.
            if isinstance(val, str) and (val == "$CURRENT" or val.startswith("$CURRENT_")):
                val = _ctx_lookup(k, context)
            # Fallback literal: si la clave no existe en el contexto, tratar el
            # propio col_key como el valor (parámetros de opción fija como variable_x).
            resolved[k] = val if val is not None else col_key
        else:
            resolved[k] = _ctx_lookup(k, context)

    if "data" not in resolved:
        resolved["data"] = context.get("data") or {}

    # Sanitizar parámetros numéricos: listas/tuplas → primer elemento → float.
    # Incluye y_decimals y label_size para evitar que valores 0 se conviertan
    # en el default por el patrón `or N`.
    for num_key in ("dpi", "total_camp", "ultimas_camp", "cadencia", "escala",
                    "y_decimals", "label_size"):
        if num_key not in resolved:
            continue
        val = resolved[num_key]
        if isinstance(val, (list, tuple)):
            val = val[0] if val else None
        if val is not None:
            try:
                resolved[num_key] = float(val)
            except (ValueError, TypeError):
                pass

    return resolved


def _ctx_lookup(param_name: str, context: dict) -> Any:
    """Busca el valor canónico de un parámetro ``$CURRENT`` en el contexto."""
    if param_name == "nombre_sensor":
        return (context.get("info") or {}).get("nom_sensor") or ""
    if param_name == "total_camp":
        return context.get("total_camp") or context.get("ultimas_camp") or 10
    # Omitir valores que sean ellos mismos tokens $CURRENT (stored retrocompatible).
    if param_name in ("sensor", "sensores", "sensores_1"):
        def _not_token(v: Any) -> Any:
            return v if (v and not (isinstance(v, str) and v.startswith("$CURRENT"))) else None
        return (
            _not_token(context.get("sensores_1"))
            or _not_token(context.get("sensores 1"))   # clave con espacio (legacy DB)
            or _not_token(context.get("sensor"))
            or (context.get("info") or {}).get("nom_sensor")
            or ""
        )
    if param_name in ("fecha_inicial", "fecha_inicio"):
        return context.get("fecha_inicio") or context.get("fecha_inicial")
    if param_name in ("fecha_final", "fecha_fin"):
        return context.get("fecha_fin") or context.get("fecha_final")
    return context.get(param_name)


# ── Obtención de datos del servidor ───────────────────────────────────────────

def _normalizar_lista_sensores(raw: Any) -> str:
    """Normaliza una cadena de sensores a CSV canónico.

    Acepta separadores mixtos (coma, salto de línea ``\\n``/``\\r``, punto y
    coma, espacios) y devuelve los tokens unidos por coma, sin duplicar
    separadores ni dejar tokens vacíos. El wizard de dispatch puede recibir
    listas pegadas desde Excel o un textarea que incluyen newlines; los
    consumidores aguas abajo (``fetch_temporal_data`` y
    ``_generate_rows_from_cells``) hacen ``split(",")``, por lo que la
    normalización debe ocurrir en el motor antes de cualquier consumo.

    Es idempotente: una cadena ya bien formada se devuelve igual (sin
    espacios sobrantes alrededor de los tokens).
    """
    if not raw:
        return ""
    tokens = _re.split(r"[\n\r,;]+", str(raw))
    return ",".join(t.strip() for t in tokens if t.strip())


def _fetch_script_data(params: dict, context: dict) -> dict:
    """Obtiene el histórico de un servidor para scripts HTML que requieren datos reales.

    Usa ``context["_server"]`` (ORM Server ya resuelto) para obtener credenciales
    de forma segura via Fernet. Si no está disponible, realiza la búsqueda en BD
    por ``context["server_id"]`` (nombre string o ID numérico).

    Retorna dict vacío si no hay servidor configurado, si el servidor no existe,
    o si la consulta falla — el script de gráfico mostrará su propio mensaje de error.
    """
    from utils.gis_client import _orm_server_to_config  # noqa: PLC0415
    from core.data_fetcher import fetch_temporal_data    # noqa: PLC0415

    orm_server = context.get("_server")
    if orm_server is None:
        server_ref = context.get("server_id")
        if not server_ref:
            return {}
        try:
            from models.server import Server as _Server   # noqa: PLC0415
            from models.database import get_session as _gs  # noqa: PLC0415
            with _gs() as session:
                if isinstance(server_ref, str) and not server_ref.isdigit():
                    from sqlmodel import select as _sel  # noqa: PLC0415
                    orm_server = session.exec(
                        _sel(_Server).where(_Server.nombre == server_ref)
                    ).first()
                else:
                    orm_server = session.get(_Server, int(server_ref))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[HTML] _fetch_script_data: error resolviendo servidor '%s': %s", server_ref, exc)
            return {}
        if orm_server is None:
            logger.warning("[HTML] _fetch_script_data: servidor '%s' no encontrado en BD", server_ref)
            return {}

    server = _orm_server_to_config(orm_server)

    try:
        sensores_raw = _normalizar_lista_sensores(
            params.get("sensor") or params.get("sensores_1") or ""
        )
        fecha_ini = (
            params.get("fecha_inicio")
            or params.get("fecha_inicial")
            or context.get("fecha_inicio")
            or context.get("fecha_inicial")
            or ""
        )
        fecha_fin = (
            params.get("fecha_fin")
            or params.get("fecha_final")
            or context.get("fecha_fin")
            or context.get("fecha_final")
            or ""
        )
        t0 = time.perf_counter()
        result = fetch_temporal_data(server, sensores_raw, fecha_ini, fecha_fin)
        elapsed = round(time.perf_counter() - t0, 3)
        n_filas = len(result.get("historico") or [])
        logger.info("[HTML] Datos: %s | %d filas en %.3fs", server.nombre, n_filas, elapsed)
        _emit_log("DATA_FETCH", server=server.nombre, sensores=sensores_raw,
                  filas=n_filas, tiempo_s=elapsed)
        return result
    except PermissionError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("[HTML] _fetch_script_data: error obteniendo datos: %s", exc)
        return {}


def _get_plotly_js_tag() -> str:
    """Obtiene el tag <script> para Plotly.js local.
    Si el archivo no existe en assets/plotly.js, lo crea importando de plotly.offline.
    """
    plotly_js_path = _PROJECT_ROOT / "assets" / "plotly.js"
    if not plotly_js_path.is_file():
        logger.info("[HTML] 'assets/plotly.js' no encontrado. Extrayendo desde la librería python plotly...")
        try:
            import plotly.offline as po
            js_content = po.get_plotlyjs()
            plotly_js_path.write_text(js_content, encoding="utf-8")
            logger.info("[HTML] 'assets/plotly.js' guardado con éxito (%d bytes).", len(js_content))
        except Exception as exc:
            logger.exception("[HTML] Error al extraer/guardar Plotly.js local: %s", exc)
            # Fallback a CDN por seguridad si algo falla
            return '<script src="https://cdn.plot.ly/plotly-2.29.1.min.js"></script>'
            
    file_uri = _to_file_uri(plotly_js_path)
    return f'<script src="{file_uri}"></script>'


# ── Constructor del documento HTML ────────────────────────────────────────────

def _render_elementos_seccion(
    elementos: dict,
    norm_context: dict,
    plantilla_dir,
) -> list[str]:
    """Renderiza los elementos de un encabezado o pie de sección.

    Soporta en v1: texto, imagen (estática/dinámica), rectángulo y línea.
    Ordena por ``zIndex`` igual que el bucle principal de página para que el
    orden de apilado coincida con el resto del documento.
    """
    partes: list[str] = []
    orden = sorted(
        elementos.items(),
        key=lambda kv: (kv[1].get("metadata") or {}).get("zIndex", 0),
    )
    for _k, elem in orden:
        if not (elem.get("metadata") or {}).get("visible", True):
            continue
        tipo = elem.get("tipo")
        try:
            if tipo == "rectangulo":
                partes.append(_elem_rect(elem))
            elif tipo in ("linea", "linea_horizontal"):
                partes.append(_elem_linea(elem))
            elif tipo == "texto":
                partes.append(_elem_texto(elem, norm_context))
            elif tipo == "imagen":
                img_cfg = elem.get("imagen_config") or {}
                if img_cfg.get("modo") == "dinamica":
                    partes.append(_elem_imagen_dinamica(elem, norm_context, plantilla_dir))
                else:
                    partes.append(_elem_imagen(elem, plantilla_dir))
            else:
                logger.debug(
                    "[HTML] Tipo no soportado en sección encabezado/pie: '%s'", tipo
                )
        except Exception as exc:
            logger.warning(
                "[HTML] Error renderizando elemento de sección '%s': %s",
                elem.get("id", _k), exc,
            )
    return partes


def _seccion_html_para_pagina(
    secciones,
    seccion_id,
    norm_context: dict,
    plantilla_dir,
) -> str:
    """Devuelve el HTML del encabezado + pie de la sección referenciada por la página.

    Devuelve cadena vacía si la página no tiene sección o la sección no existe
    en el pool de secciones reutilizables.
    """
    if not seccion_id or not secciones:
        return ""
    sec = secciones.get(seccion_id)
    if not isinstance(sec, dict):
        return ""
    partes: list[str] = []
    enc_elems = (sec.get("encabezado") or {}).get("elementos") or {}
    pie_elems = (sec.get("pie") or {}).get("elementos") or {}
    partes += _render_elementos_seccion(enc_elems, norm_context, plantilla_dir)
    partes += _render_elementos_seccion(pie_elems, norm_context, plantilla_dir)
    return "\n".join(partes)


def _build_html(
    paginas: dict,
    context: dict,
    plantilla_dir: Path,
    secciones: dict | None = None,
) -> str:
    """Construye el documento HTML completo a partir del JSON de páginas.

    Cada página se convierte en un ``<div class="page">`` con elementos
    posicionados absolutamente en unidades ``cm``. Se usan *CSS named pages*
    (``@page pp`` / ``@page lp``) para soportar orientaciones mixtas sin que
    Playwright fuerce una orientación global.

    Args:
        paginas:      Dict ``{page_key: page_data}`` de la plantilla JSON.
        context:      Contexto de ejecución para resolución de tokens.
        plantilla_dir: Directorio raíz de la plantilla (para resolver assets).
        secciones:    Dict ``plantilla["secciones"]`` (pool de secciones
                      reutilizables con encabezado/pie por página). Si es
                      ``None``, el comportamiento es idéntico al previo a la
                      introducción de secciones (sin encabezado/pie compartido).

    Returns:
        Cadena con el documento HTML completo.
    """
    pages_html: list[str] = []

    for n, page_key in enumerate(sorted(paginas.keys(), key=lambda k: int(k))):
        # Crear una copia aislada del contexto para cada página, para evitar la contaminación mutable
        page_context = dict(context)
        page_data  = paginas[page_key]
        w_cm, h_cm = _page_dims(page_data)
        ori        = (page_data.get("configuracion") or {}).get("orientacion", "portrait")
        page_class = "page-landscape" if ori == "landscape" else "page-portrait"
        seccion_id = (page_data.get("configuracion") or {}).get("seccion")

        _emit_log("HTML_RENDER", pagina=n + 1, orientacion=ori, w_cm=w_cm, h_cm=h_cm)

        # Exponer dimensiones de la página para que _elem_tabla pueda almacenarlas
        # en el overflow_queue (modo paginar).
        page_context["_current_page_w_cm"]  = w_cm
        page_context["_current_page_h_cm"]  = h_cm
        page_context["_current_page_class"] = page_class

        # Normalizar contexto una vez por página (añade aliases planos para {{tokens}})
        norm_context = _normalize_context(page_context)

        # Render del encabezado/pie de sección (una sola vez por página). La
        # misma cadena se reutiliza en las páginas de continuación de tablas
        # para que hereden el encabezado/pie de la página de origen.
        seccion_html = _seccion_html_para_pagina(
            secciones, seccion_id, norm_context, plantilla_dir
        )

        # Ordenar elementos por zIndex
        elementos = page_data.get("elementos") or {}
        # Exponer el dict de elementos en norm_context para que _elem_tabla pueda
        # recopilar los elementos con "grupo" que deben repetirse en páginas overflow.
        norm_context["_current_page_elementos"] = elementos
        orden = sorted(
            elementos.items(),
            key=lambda kv: (kv[1].get("metadata") or {}).get("zIndex", 0),
        )

        elems_html: list[str] = []
        for _key, elem in orden:
            if not (elem.get("metadata") or {}).get("visible", True):
                continue
            tipo = elem.get("tipo")
            try:
                if tipo == "rectangulo":
                    elems_html.append(_elem_rect(elem))
                elif tipo in ("linea", "linea_horizontal"):
                    elems_html.append(_elem_linea(elem))
                elif tipo == "texto":
                    elems_html.append(_elem_texto(elem, norm_context))
                elif tipo == "imagen":
                    img_cfg = elem.get("imagen_config") or {}
                    if img_cfg.get("modo") == "dinamica":
                        elems_html.append(_elem_imagen_dinamica(elem, norm_context, plantilla_dir))
                    else:
                        elems_html.append(_elem_imagen(elem, plantilla_dir))
                elif tipo == "grafico":
                    elems_html.append(_elem_grafico(elem, norm_context))
                    elems_html.append(_elem_caption_html(elem, norm_context))
                elif tipo == "tabla":
                    elems_html.append(_elem_tabla(elem, norm_context))
                    elems_html.append(_elem_caption_html(elem, norm_context))
                elif tipo == "mapa":
                    elems_html.append(_elem_mapa(elem, norm_context))
                    elems_html.append(_elem_caption_html(elem, norm_context))
                elif tipo == "sinoptico":
                    elems_html.append(_elem_sinoptico(elem, norm_context, plantilla_dir))
                    elems_html.append(_elem_caption_html(elem, norm_context))
                else:
                    logger.debug("[HTML] Tipo de elemento desconocido: '%s'", tipo)
            except Exception as exc:
                elem_id = elem.get("id") or _key
                logger.warning("[HTML] Error renderizando elemento '%s': %s", elem_id, exc)

        # Si algún elemento generó overflow paginado, esta página no puede ser
        # la última (hay páginas de continuación por venir).
        # norm_context es donde _elem_tabla escribe (puede ser copia de context).
        has_overflow    = bool(norm_context.get("_tabla_overflow_queue"))
        last_templ_page = n == len(paginas) - 1
        break_after = (
            "page-break-after:avoid;"
            if last_templ_page and not has_overflow
            else "page-break-after:always;"
        )
        pages_html.append(
            f'<div class="page {page_class}" '
            f'style="position:relative;width:{w_cm}cm;height:{h_cm}cm;'
            f'overflow:hidden;background:white;{break_after}">\n'
            + "\n".join(elems_html)
            + "\n" + seccion_html
            + "\n</div>"
        )

        # ── Páginas de continuación para tablas con overflow="paginar" ─────────
        overflow_queue: list[dict] = list(norm_context.get("_tabla_overflow_queue") or [])
        norm_context["_tabla_overflow_queue"] = []  # resetear antes de procesar
        for ovf_idx, ovf in enumerate(overflow_queue):
            is_last_ovf   = ovf_idx == len(overflow_queue) - 1
            remaining     = ovf["remaining_rows"]
            geo           = ovf["geo"]
            ox            = float(geo.get("x", 0))
            oy            = float(geo.get("y", 0))
            ow            = float(geo.get("ancho", 15))
            ovf_page_w    = ovf["page_w_cm"]
            ovf_page_h    = ovf["page_h_cm"]
            ovf_page_cls  = ovf["page_class"]
            static_h      = ovf["static_h"]
            default_row_h = ovf["default_row_h"]

            # Cuántas filas caben en una página de continuación (mismo alto que la
            # tabla original, descontando los encabezados que se repiten).
            avail_h_cont  = float(geo.get("alto", ovf_page_h - oy - 0.5)) - static_h
            max_rows_cont = max(1, int(avail_h_cont / default_row_h) - 1)

            # Renderizar elementos de grupo (encabezado/pie) una vez por ovf entry
            # Ordenar por zIndex antes de renderizar para que los elementos con
            # zIndex alto (textos, logos) queden encima del fondo (rectángulo zIndex=1).
            _repeat_raw = ovf.get("repeat_elements") or []
            repeat_sorted = sorted(
                _repeat_raw,
                key=lambda kv: (kv[1].get("metadata") or {}).get("zIndex", 0),
            )
            logger.info(
                "[HTML] Overflow repeat_elements: %d elementos, tipos+zIndex: %s",
                len(repeat_sorted),
                [(relem.get("tipo"), (relem.get("metadata") or {}).get("zIndex"))
                 for _, relem in repeat_sorted],
            )
            repeat_parts: list[str] = []
            for _rk, relem in repeat_sorted:
                if not (relem.get("metadata") or {}).get("visible", True):
                    continue
                rtipo = relem.get("tipo")
                try:
                    if rtipo == "rectangulo":
                        repeat_parts.append(_elem_rect(relem))
                    elif rtipo in ("linea", "linea_horizontal"):
                        repeat_parts.append(_elem_linea(relem))
                    elif rtipo == "texto":
                        repeat_parts.append(_elem_texto(relem, norm_context))
                    elif rtipo == "imagen":
                        img_cfg = relem.get("imagen_config") or {}
                        if img_cfg.get("modo") == "dinamica":
                            repeat_parts.append(
                                _elem_imagen_dinamica(relem, norm_context, plantilla_dir)
                            )
                        else:
                            repeat_parts.append(_elem_imagen(relem, plantilla_dir))
                except Exception as _exc:
                    logger.error(
                        "[HTML] Overflow repeat elem %s (tipo=%s): %s",
                        _rk, rtipo, _exc, exc_info=True,
                    )
            repeat_html = "\n".join(repeat_parts)

            while remaining:
                chunk     = remaining[:max_rows_cont]
                remaining = remaining[max_rows_cont:]

                tabla_html = _build_html_cuadricula(
                    ovf["niveles_stat"], ovf["nivel_auto"], chunk,
                    computed_header_rows=ovf["computed_header_rows"],
                )
                cont_h = static_h + len(chunk) * default_row_h
                tabla_div = (
                    f'<div style="position:absolute;left:{ox}cm;top:{oy}cm;'
                    f'width:{ow}cm;height:{cont_h:.3f}cm;overflow:hidden;">'
                    f"{tabla_html}</div>"
                )

                is_last_chunk = is_last_ovf and not remaining
                page_break = (
                    "page-break-after:avoid;"
                    if is_last_chunk
                    else "page-break-after:always;"
                )
                pages_html.append(
                    f'<div class="page {ovf_page_cls}" '
                    f'style="position:relative;width:{ovf_page_w}cm;'
                    f'height:{ovf_page_h}cm;overflow:hidden;background:white;{page_break}">\n'
                    f"{repeat_html}\n{tabla_div}\n{seccion_html}\n</div>"
                )
                logger.info(
                    "[HTML] Overflow page: elem_id=%s chunk=%d restantes=%d",
                    ovf.get("elem_id", "?"), len(chunk), len(remaining),
                )

    # Numeración: {{pagina}}/{{total_paginas}} (y alias EN {{page}}/{{total_pages}})
    # se dejaron literales durante el render por página; se sustituyen aquí,
    # una vez conocido el total real (incluyendo páginas de continuación).
    _total_pag = len(pages_html)
    pages_render: list[str] = []
    for _i, _ph in enumerate(pages_html):
        _num = str(_i + 1)
        _ph = _ph.replace("{{pagina}}", _num).replace("{{page}}", _num)
        _ph = _ph.replace("{{total_paginas}}", str(_total_pag)).replace("{{total_pages}}", str(_total_pag))
        pages_render.append(_ph)

    plotly_js_tag = _get_plotly_js_tag()
    return (
        "<!DOCTYPE html>\n<html>\n<head>\n"
        '<meta charset="utf-8">\n'
        '<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">\n'
        f"{plotly_js_tag}\n"
        "<style>\n"
        "* { box-sizing: border-box; margin: 0; padding: 0; }\n"
        "body { background: white; }\n"
        "@page { margin: 0; }\n"
        "@page pp { size: 210mm 297mm; margin: 0; }\n"
        "@page lp { size: 297mm 210mm; margin: 0; }\n"
        ".page-portrait  { page: pp; }\n"
        ".page-landscape { page: lp; }\n"
        + _L9_STYLES_CSS
        + "</style>\n"
        "</head>\n<body>\n"
        + "\n".join(pages_render)
        + "\n</body>\n</html>"
    )


# ── Renderizado Playwright ────────────────────────────────────────────────────

def _playwright_pdf(html_path: str, output_path: str) -> None:
    """Renderiza el archivo HTML a PDF usando Playwright (Chromium headless).

    Usa ``wait_until='networkidle'`` para garantizar que Plotly y cualquier
    recurso pesado se carguen antes de capturar el PDF.

    Usa ``prefer_css_page_size=True`` para respetar las dimensiones declaradas
    en las reglas ``@page`` del HTML, lo que permite orientaciones mixtas.

    Args:
        html_path:   Ruta absoluta al archivo HTML temporal.
        output_path: Ruta absoluta de salida del PDF.

    Raises:
        ImportError:  Si ``playwright`` no está instalado.
        RuntimeError: Si Chromium falla o supera el timeout.
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "Playwright no está instalado. Ejecuta:\n"
            "  pip install playwright && playwright install chromium"
        ) from exc

    file_uri = Path(html_path).resolve().as_uri()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page    = browser.new_page()
            page.goto(file_uri, wait_until="networkidle", timeout=60_000)
            # Tiempo extra para que Plotly complete la inicialización JS tras networkidle.
            # Las bibliotecas de gráficos con bundled JS (include_plotlyjs=True) ejecutan
            # código síncrono pesado después de que la red queda idle.
            page.wait_for_timeout(3000)
            page.pdf(
                path=output_path,
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            browser.close()
    except Exception as exc:
        raise RuntimeError(f"Playwright falló al generar el PDF: {exc}") from exc


# ── Motor principal ───────────────────────────────────────────────────────────

class HTMLEngine(BaseReportEngine):
    """Motor HTML/Playwright: genera PDFs renderizando el template como página web.

    Implementa ``BaseReportEngine``. Los scripts de gráficos se buscan en
    ``biblioteca_graficos/html/`` (rutas con namespace) o en la raíz de
    ``biblioteca_graficos/`` como fallback legacy.

    Requiere::

        pip install playwright plotly
        playwright install chromium
    """

    def __init__(self, server=None) -> None:
        super().__init__(server=server)

    def render(
        self,
        context: dict,
        nombre_plantilla: str,
        output_path: str,
    ) -> list:
        """Genera el PDF HTML y devuelve el log de ejecución.

        Flujo:
        1. Localiza la plantilla con búsqueda con namespace.
        2. Construye el documento HTML con assets en ``file:///``.
        3. Escribe el HTML a un archivo temporal.
        4. Playwright (Chromium) renderiza el HTML a PDF.
        5. Elimina el archivo temporal.

        Raises:
            PlantillaNoEncontrada: Si la plantilla no existe.
            ImportError:           Si Playwright no está instalado.
            RuntimeError:          Si Chromium falla o timeout.
        """
        _tl.execution_log = []
        tmp_path: str | None = None
        try:
            t0 = time.perf_counter()

            # 1. Localizar plantilla
            json_path = _encontrar_json_plantilla(nombre_plantilla)
            if json_path is None:
                from utils.template_service import PlantillaNoEncontrada  # noqa: PLC0415
                raise PlantillaNoEncontrada(
                    f"Plantilla '{nombre_plantilla}' no encontrada."
                )
            plantilla_dir = json_path.parent

            # 2. Cargar JSON y construir HTML
            template = cargar_plantilla(nombre_plantilla)
            paginas  = template.get("paginas") or {}
            _emit_log("HTML_LOAD", plantilla=nombre_plantilla, n_paginas=len(paginas))
            logger.info("[HTML] Renderizando '%s' (%d páginas)", nombre_plantilla, len(paginas))

            # Inyectar ORM Server en context para elementos que lo necesitan (p.ej. mapa).
            # Prioridad 1: self._server (pasado por el job runner vía BaseReportEngine).
            # Prioridad 2: resolver server_ref desde context["server_id"] que puede ser:
            #   a) nombre string (ej. "Tunneldata_L9") — caso dispatch
            #   b) ID numérico como string (ej. "1") — caso job runner legacy
            logger.debug(
                "[HTML] Resolviendo _server | self._server=%s | context.server_id=%r",
                type(self._server).__name__, context.get("server_id"),
            )
            if self._server is not None:
                context["_server"] = self._server
                logger.info(
                    "[HTML] _server desde self._server: %r",
                    getattr(self._server, "nombre", str(self._server)),
                )

            if "_server" not in context or context["_server"] is None:
                from models.server import Server          # noqa: PLC0415
                from models.database import get_session  # noqa: PLC0415
                from sqlmodel import select as _select   # noqa: PLC0415

                server_ref = context.get("server_id")
                if server_ref is not None:
                    logger.info("[HTML] Buscando servidor por ref=%r en BD SQLite", server_ref)
                    try:
                        with get_session() as session:
                            srv: Server | None = None
                            # Prioridad: nombre string no-numérico (caso dispatch)
                            if isinstance(server_ref, str) and not server_ref.isdigit():
                                srv = session.exec(
                                    _select(Server).where(Server.nombre == server_ref)
                                ).first()
                                if srv is None:
                                    logger.warning(
                                        "[HTML] _server: ningún servidor con nombre=%r en BD.",
                                        server_ref,
                                    )
                                    _emit_log("SERVER_NOT_FOUND", server_ref=server_ref,
                                              motivo="nombre_no_encontrado")
                            else:
                                # Fallback: ID numérico
                                srv = session.get(Server, int(server_ref))
                                if srv is None:
                                    logger.warning(
                                        "[HTML] _server: server_id=%r no encontrado en BD.",
                                        server_ref,
                                    )
                                    _emit_log("SERVER_NOT_FOUND", server_ref=server_ref,
                                              motivo="id_no_encontrado")

                            if srv is not None:
                                logger.info(
                                    "[HTML] _server resuelto: id=%r nombre=%r host=%r url_gis=%r",
                                    srv.id, srv.nombre, srv.host,
                                    getattr(srv, "url_gis", "SIN_CAMPO"),
                                )
                            context["_server"] = srv
                    except Exception as exc:
                        logger.error(
                            "[HTML] Error resolviendo server_ref=%r: %s", server_ref, exc
                        )
                        context["_server"] = None
                else:
                    logger.debug(
                        "[HTML] No hay server_id en context; _server no inyectado. "
                        "context keys: %s",
                        list(context.keys()),
                    )

            html_doc = _build_html(
                paginas, context, plantilla_dir,
                secciones=template.get("secciones"),
            )

            # 3. Escribir HTML temporal
            with tempfile.NamedTemporaryFile(
                suffix=".html", mode="w", encoding="utf-8", delete=False
            ) as tmp:
                tmp.write(html_doc)
                tmp_path = tmp.name

            # 4. Playwright → PDF
            ruta_final = str(Path(output_path).resolve())
            _playwright_pdf(tmp_path, ruta_final)

            elapsed = time.perf_counter() - t0
            _emit_log("HTML_DONE", output=ruta_final, elapsed_s=round(elapsed, 2))
            logger.info("[HTML] PDF generado en %.2fs: %s", elapsed, ruta_final)

        except (ImportError, RuntimeError) as exc:
            _emit_log("HTML_ERROR", error=str(exc))
            logger.error("[HTML] %s", exc)
            raise
        except Exception as exc:
            _emit_log("HTML_ERROR", error=str(exc))
            logger.error("[HTML] Error inesperado: %s", exc)
            raise
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)
            result_log = list(getattr(_tl, "execution_log", []) or [])
            _tl.execution_log = None
            if not result_log:
                result_log = [{
                    "hito": "LOG_VACIO",
                    "ts": _dt.now(timezone.utc).isoformat(),
                    "aviso": "_tl.execution_log estaba vacío al finalizar render()",
                }]

        return result_log

    def render_from_state(
        self,
        context: dict,
        editor_state: dict,
        output_path: str,
    ) -> list:
        """Genera un PDF efímero desde el estado en memoria del editor visual.

        Construye el HTML directamente desde el estado sin necesitar la plantilla
        guardada en disco. Assets referenciados por ruta relativa no estarán
        disponibles (placeholder mostrado).
        """
        _tl.execution_log = []
        tmp_html: str | None = None
        try:
            t0 = time.perf_counter()
            paginas      = editor_state.get("paginas") or {}
            plantilla_dir = Path(tempfile.gettempdir())
            html_doc     = _build_html(
                paginas, context, plantilla_dir,
                secciones=editor_state.get("secciones"),
            )
            with tempfile.NamedTemporaryFile(
                suffix=".html", mode="w", encoding="utf-8", delete=False
            ) as tmp:
                tmp.write(html_doc)
                tmp_html = tmp.name
            ruta_final = str(Path(output_path).resolve())
            _playwright_pdf(tmp_html, ruta_final)
            elapsed = time.perf_counter() - t0
            _emit_log("HTML_DONE", output=ruta_final, elapsed_s=round(elapsed, 2))
            logger.info("[HTML] render_from_state generado en %.2fs: %s", elapsed, ruta_final)
        except Exception as exc:
            _emit_log("HTML_ERROR", error=str(exc))
            logger.error("[HTML] render_from_state error: %s", exc)
            raise
        finally:
            if tmp_html:
                Path(tmp_html).unlink(missing_ok=True)
            result_log = list(getattr(_tl, "execution_log", []) or [])
            _tl.execution_log = None
            if not result_log:
                result_log = [{
                    "hito": "LOG_VACIO",
                    "ts": _dt.now(timezone.utc).isoformat(),
                    "aviso": "_tl.execution_log estaba vacío al finalizar render_from_state()",
                }]
        return result_log

    def render_preview_html_from_state(
        self,
        editor_state: dict,
        context: dict,
    ) -> str:
        """Devuelve el HTML crudo generado desde el estado del editor (sin Playwright)."""
        paginas      = editor_state.get("paginas") or {}
        plantilla_dir = Path(tempfile.gettempdir())
        return _build_html(
            paginas, context, plantilla_dir,
            secciones=editor_state.get("secciones"),
        )

    def render_preview_png(
        self,
        context: dict,
        nombre_plantilla: str,
        width_px: int = 800,
    ) -> bytes:
        """Genera una vista previa PNG de la primera página usando Playwright screenshot.

        Raises:
            ImportError: Si Playwright no está instalado.
        """
        try:
            from playwright.sync_api import sync_playwright  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "Playwright no está instalado. Ejecuta:\n"
                "  pip install playwright && playwright install chromium"
            ) from exc

        json_path = _encontrar_json_plantilla(nombre_plantilla)
        if json_path is None:
            from utils.template_service import PlantillaNoEncontrada  # noqa: PLC0415
            raise PlantillaNoEncontrada(f"Plantilla '{nombre_plantilla}' no encontrada.")
        plantilla_dir = json_path.parent

        template     = cargar_plantilla(nombre_plantilla)
        first_key    = sorted((template.get("paginas") or {}).keys(), key=lambda k: int(k))[0]
        paginas_prev = {first_key: template["paginas"][first_key]}
        html_doc     = _build_html(
            paginas_prev, context, plantilla_dir,
            secciones=template.get("secciones"),
        )

        with tempfile.NamedTemporaryFile(
            suffix=".html", mode="w", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write(html_doc)
            tmp_path = tmp.name

        try:
            file_uri = Path(tmp_path).resolve().as_uri()
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page    = browser.new_page(
                    viewport={"width": width_px, "height": int(width_px * 1.414)}
                )
                page.goto(file_uri, wait_until="networkidle", timeout=30_000)
                png_bytes = page.screenshot(full_page=True)
                browser.close()
            return png_bytes
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def render_preview_graficos(
        self,
        context: dict,
        nombre_plantilla: str,
    ) -> list[dict]:
        """Genera metadatos de gráficos y tablas sin ejecutar Playwright.

        Ejecuta cada script de gráfico o renderiza cada tabla celda a celda e
        indica si devolvió HTML o falló.  El campo ``result`` contiene el HTML
        codificado en base64 como data URL (``data:text/html;base64,...``) para
        consumo en el editor visual.
        """
        import base64  # noqa: PLC0415

        template   = cargar_plantilla(nombre_plantilla)
        resultados: list[dict] = []
        index      = 0

        for page_data in template.get("paginas", {}).values():
            for elem_id, elem in page_data.get("elementos", {}).items():
                elem_tipo = elem.get("tipo")
                if elem_tipo not in ("grafico", "tabla"):
                    continue
                geo    = elem.get("geometria") or {}
                w      = float(geo.get("ancho", 15))
                h      = float(geo.get("alto", 8))
                entry: dict = {
                    "index": index, "element_id": elem_id,
                    "script": None, "result": None, "error": None,
                }

                if elem_tipo == "tabla":
                    entry["script"] = "tabla-celda"
                    try:
                        tabla_fragment = _elem_tabla(elem, context)
                        if tabla_fragment:
                            full_html = (
                                f'<html><body style="margin:0;padding:0;'
                                f'position:relative;width:{w}cm;height:{h}cm;">'
                                f'{tabla_fragment}</body></html>'
                            )
                            encoded = base64.b64encode(full_html.encode()).decode()
                            entry["result"] = f"data:text/html;base64,{encoded}"
                        else:
                            entry["error"] = "Tabla sin nivel autorrelleno"
                    except Exception as exc:
                        entry["error"] = str(exc)
                else:
                    cfg         = elem.get("configuracion") or {}
                    script_name = cfg.get("script") or ""
                    params      = _resolve_params(dict(cfg.get("parametros") or {}), context, elem_id=elem_id)
                    figsize     = (w / 2.54, h / 2.54)
                    entry["script"] = script_name
                    if not script_name:
                        entry["error"] = "Sin script asignado"
                    else:
                        try:
                            html_result = _run_script(script_name, params, figsize, context, elem_id)
                            if html_result:
                                encoded = base64.b64encode(html_result.encode()).decode()
                                entry["result"] = f"data:text/html;base64,{encoded}"
                            else:
                                entry["error"] = "El script no devolvió HTML"
                        except Exception as exc:
                            entry["error"] = str(exc)

                resultados.append(entry)
                index += 1

        return resultados

"""Función de celda: extrae una columna completa del array ``calc`` de una campaña
de inclinómetro almacenada en ``json_inclis/``.

Por cada profundidad del array ``calc`` de la campaña indicada, devuelve el valor
del campo ``clave`` redondeado a ``decimales`` decimales (default 2).  El resultado
es una **lista**, lo que activa el modo de expansión multi-fila del motor HTML
(``_generate_rows_from_cells``): se genera una fila por profundidad, en lugar de
una fila por sensor.

Si la campaña no existe o no está activa devuelve una lista vacía.

Uso típico en la cuadrícula de la plantilla (nivel autorrelleno)::

    "origen": {
        "tipo": "funcion",
        "funcion": "columna_incli_json",
        "parametros": {
            "sensor": {"ref": "contexto", "clave": "$CURRENT"},
            "fecha":  {"ref": "contexto", "clave": "fecha_ultima"},
            "clave":  {"ref": "literal",  "valor": "desp_a"},
            "decimales": {"ref": "literal", "valor": 2}
        }
    }

La clave ``fecha_ultima`` (o ``fecha_penultima`` / ``fecha_antepenultima``) debe
haberse inyectado en el contexto previamente desde las columnas del nivel estático
que definen ``"context_key": "fecha_ultima"`` y usan funciones ``ultima_lect_incli``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_JSON_INCLIS_DIR = Path(__file__).resolve().parent.parent.parent / "json_inclis"

# Caché de JSONs ya cargados: {sensor_stem: datos_dict}
_json_cache: dict[str, dict] = {}

# ─────────────────────────────────────────────────────────────────────────────
CELL_FUNCTION_METADATA: dict[str, Any] = {
    "nombre": "columna_incli_json",
    "devuelve": "lista",
    "descripcion": (
        "Devuelve la lista de valores del campo ``clave`` del array calc para una "
        "campaña de inclinómetro JSON. Un elemento por profundidad. "
        "Activa el modo expansión multi-fila del motor cuando se usa en autorrelleno. "
        "Devuelve [] si la campaña no existe o no está activa."
    ),
    "parametros": [
        {
            "nombre": "sensor",
            "tipo": "texto",
            "descripcion": (
                "Stem del JSON en json_inclis/. "
                "Usar ref:contexto clave:$CURRENT para el sensor del informe."
            ),
        },
        {
            "nombre": "fecha",
            "tipo": "texto",
            "descripcion": (
                "Fecha ISO exacta de la campaña (clave en el JSON). "
                "Ej: '2023-11-09T04:34:02'. Usar ref:contexto con la clave inyectada "
                "desde el nivel estático (p.ej. 'fecha_ultima')."
            ),
        },
        {
            "nombre": "clave",
            "tipo": "texto",
            "descripcion": (
                "Campo del objeto calc a extraer. "
                "Ej: 'depth', 'desp_a', 'desp_b', 'abs_dev_a', 'abs_dev_b'."
            ),
        },
        {
            "nombre": "decimales",
            "tipo": "numero",
            "descripcion": "Decimales para redondear valores numéricos (default 2).",
        },
    ],
}

# ─────────────────────────────────────────────────────────────────────────────


def _load_sensor_json(sensor: str) -> dict:
    """Carga (con caché en memoria) el JSON del sensor. Devuelve {} si no existe."""
    if sensor in _json_cache:
        return _json_cache[sensor]

    ruta = _JSON_INCLIS_DIR / f"{sensor}.json"
    if not ruta.is_file():
        logger.warning("[columna_incli_json] Archivo no encontrado: %s", ruta)
        _json_cache[sensor] = {}
        return {}

    try:
        with ruta.open(encoding="utf-8") as f:
            datos = json.load(f)
    except Exception as exc:
        logger.warning("[columna_incli_json] Error leyendo %s: %s", ruta, exc)
        datos = {}

    _json_cache[sensor] = datos
    return datos


def evaluate(
    params: dict[str, Any],
    data: dict[str, Any],
    context: dict[str, Any],
) -> list:
    """Devuelve la columna de valores ``clave`` del array calc para la campaña ``fecha``.

    Args:
        params:
            - ``sensor``    (str): Nombre del sensor / stem del JSON en json_inclis/.
            - ``fecha``     (str): Fecha ISO exacta de la campaña (clave en el JSON).
            - ``clave``     (str): Campo a extraer de cada entrada del array calc.
            - ``decimales`` (int, opcional): Precisión del redondeo. Default 2.
        data:    No se utiliza (los datos se leen del JSON local).
        context: No se utiliza directamente; la resolución de parámetros ya ocurrió
                 antes de llamar a evaluate().

    Returns:
        Lista con un valor por profundidad. Valores numéricos redondeados a
        ``decimales`` decimales. Cadena vacía para entradas sin el campo.
        Lista vacía si la campaña no existe, no está activa o ``sensor``/``fecha``
        son vacíos.
    """
    sensor: str = str(params.get("sensor") or "").strip()
    fecha: str = str(params.get("fecha") or "").strip()
    clave: str = str(params.get("clave") or "").strip()
    try:
        decimales: int = int(params.get("decimales") or 2)
    except (TypeError, ValueError):
        decimales = 2

    if not sensor or not clave:
        logger.warning(
            "[columna_incli_json] Parámetros incompletos: sensor=%r clave=%r",
            sensor, clave,
        )
        return []

    datos = _load_sensor_json(sensor)
    if not datos:
        return []

    # Fallback inteligente para la clave 'depth' (profundidad)
    # Las profundidades son físicas y estáticas para un tubo. Si la fecha provista
    # está vacía o no corresponde a una campaña activa, buscamos la primera campaña
    # activa disponible en el JSON para poder poblar la columna de profundidad.
    usar_fallback = False
    if not fecha:
        usar_fallback = True
    else:
        bloque = datos.get(fecha)
        if not isinstance(bloque, dict) or not bloque.get("campaign_info", {}).get("active", False):
            usar_fallback = True

    if usar_fallback and clave == "depth":
        for k, v in datos.items():
            if isinstance(v, dict) and v.get("campaign_info", {}).get("active", False):
                fecha = k
                break

    if not fecha:
        logger.warning(
            "[columna_incli_json] Parámetros incompletos o sin campaña de fallback activa: sensor=%r fecha=%r clave=%r",
            sensor, fecha, clave,
        )
        return []

    bloque = datos.get(fecha)
    if not isinstance(bloque, dict):
        logger.warning(
            "[columna_incli_json] sensor=%s: campaña '%s' no encontrada", sensor, fecha,
        )
        return []

    campaign_info = bloque.get("campaign_info") or {}
    if not campaign_info.get("active", False):
        logger.warning(
            "[columna_incli_json] sensor=%s campaña=%s: no está activa", sensor, fecha,
        )
        return []

    calc: list[dict] = bloque.get("calc") or []
    resultado: list = []
    for entry in calc:
        val = entry.get(clave)
        if val is None:
            resultado.append("")
            continue
        try:
            resultado.append(round(float(val), decimales))
        except (TypeError, ValueError):
            resultado.append(str(val))

    return resultado

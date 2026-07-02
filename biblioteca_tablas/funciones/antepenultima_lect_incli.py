"""Función de celda: fecha de la antepenúltima lectura activa de un inclinómetro JSON.

Devuelve la fecha ISO de la tercera campaña más reciente cuya clave sea ≤ fecha_fin
y tenga campaign_info.active=true. Devuelve None si no existen al menos 3 campañas.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_JSON_INCLIS_DIR = Path(__file__).resolve().parent.parent.parent / "json_inclis"

# ─────────────────────────────────────────────────────────────────────────────
CELL_FUNCTION_METADATA: dict[str, Any] = {
    "nombre": "antepenultima_lect_incli",
    "devuelve": "texto",
    "descripcion": (
        "Fecha (ISO) de la antepenúltima campaña activa del inclinómetro con fecha "
        "igual o anterior a fecha_fin. Devuelve None si hay menos de 3 campañas."
    ),
    "parametros": [
        {
            "nombre": "sensor",
            "tipo": "texto",
            "descripcion": (
                "Nombre del sensor (stem del JSON en json_inclis/). "
                "Puede ser ref:ancla, ref:literal o ref:contexto. "
                "Ej: 'Avda_America_IN75_SISGEO'."
            ),
        },
        {
            "nombre": "fecha_fin",
            "tipo": "texto",
            "descripcion": (
                "Fecha tope del informe en formato YYYY-MM-DD o ISO completo. "
                "Solo se incluyen campañas con clave ≤ fecha_fin."
            ),
        },
    ],
}

# ─────────────────────────────────────────────────────────────────────────────

def _cargar_campanas_activas(sensor: str, fecha_fin: str) -> list[str]:
    """Devuelve lista de fechas ISO de campañas activas ≤ fecha_fin, ordenadas."""
    ruta = _JSON_INCLIS_DIR / f"{sensor}.json"
    if not ruta.is_file():
        logger.warning("[antepenultima_lect_incli] Archivo no encontrado: %s", ruta)
        return []

    try:
        with ruta.open(encoding="utf-8") as f:
            datos = json.load(f)
    except Exception as exc:
        logger.warning("[antepenultima_lect_incli] Error leyendo %s: %s", ruta, exc)
        return []

    claves_ignoradas = {"info", "umbrales"}
    campanas: list[str] = []

    for clave, bloque in datos.items():
        if clave in claves_ignoradas:
            continue
        if not isinstance(bloque, dict):
            continue
        campaign_info = bloque.get("campaign_info") or {}
        if not campaign_info.get("active", False):
            continue
        clave_fecha = clave[:10]
        if fecha_fin and clave_fecha > str(fecha_fin)[:10]:
            continue
        campanas.append(clave)

    return sorted(campanas)


def evaluate(
    params: dict[str, Any],
    data: dict[str, Any],
    context: dict[str, Any],
) -> str | None:
    """Devuelve la fecha ISO de la antepenúltima campaña activa ≤ fecha_fin.

    Args:
        params:
            - ``sensor``    (str): Nombre del sensor / stem del JSON en json_inclis/.
            - ``fecha_fin`` (str): Fecha tope en formato YYYY-MM-DD o ISO completo.
        data:    No se utiliza.
        context: Fallback para ``fecha_fin`` si no está en ``params``.

    Returns:
        Fecha ISO (str) de la antepenúltima campaña activa, o ``None`` si hay <3.
    """
    sensor: str = params.get("sensor") or ""
    fecha_fin: str = (
        params.get("fecha_fin")
        or context.get("fecha_fin")
        or context.get("fecha_final")
        or ""
    )

    if not sensor:
        return None

    campanas = _cargar_campanas_activas(sensor, fecha_fin)
    return campanas[-3] if len(campanas) >= 3 else None

"""Función de celda: fecha de la última lectura activa de un inclinómetro JSON.

Recorre el JSON del sensor (carpeta json_inclis/) y devuelve la fecha ISO de la
campaña más reciente cuya clave sea ≤ fecha_fin y tenga campaign_info.active=true.
Devuelve None si no existe ninguna campaña que cumpla las condiciones.
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
    "nombre": "ultima_lect_incli",
    "devuelve": "texto",
    "descripcion": (
        "Fecha (ISO) de la última campaña activa del inclinómetro con fecha "
        "igual o anterior a fecha_fin. Devuelve None si no existe."
    ),
    "parametros": [
        {
            "nombre": "sensor",
            "tipo": "texto",
            "descripcion": (
                "Nombre del sensor (stem del JSON en json_inclis/). "
                "Puede ser ref:ancla (columna ancla), ref:literal (nombre fijo) "
                "o ref:contexto (token del informe). Ej: 'Avda_America_IN75_SISGEO'."
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
        logger.warning("[ultima_lect_incli] Archivo no encontrado: %s", ruta)
        return []

    try:
        with ruta.open(encoding="utf-8") as f:
            datos = json.load(f)
    except Exception as exc:
        logger.warning("[ultima_lect_incli] Error leyendo %s: %s", ruta, exc)
        return []

    # Las claves ISO son campañas; 'info' y 'umbrales' se descartan
    claves_ignoradas = {"info", "umbrales"}
    campanas: list[str] = []

    for clave, bloque in datos.items():
        if clave in claves_ignoradas:
            continue
        if not isinstance(bloque, dict):
            continue
        # Verificar active=true
        campaign_info = bloque.get("campaign_info") or {}
        if not campaign_info.get("active", False):
            continue
        # Filtrar por fecha_fin (comparación lexicográfica sobre ISO-8601)
        clave_fecha = clave[:10]  # YYYY-MM-DD del timestamp ISO
        if fecha_fin and clave_fecha > str(fecha_fin)[:10]:
            continue
        campanas.append(clave)

    return sorted(campanas)  # orden cronológico ascendente


def evaluate(
    params: dict[str, Any],
    data: dict[str, Any],
    context: dict[str, Any],
) -> str | None:
    """Devuelve la fecha ISO de la última campaña activa ≤ fecha_fin.

    Args:
        params:
            - ``sensor``    (str): Nombre del sensor / stem del JSON en json_inclis/.
            - ``fecha_fin`` (str): Fecha tope en formato YYYY-MM-DD o ISO completo.
        data:    No se utiliza (los datos se leen directamente del JSON de inclinómetros).
        context: Contexto del informe. Si ``fecha_fin`` no está en ``params``,
                 se busca como fallback en ``context['fecha_fin']``.

    Returns:
        Fecha ISO (str) de la última campaña activa, o ``None`` si no existe.
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
    return campanas[-1] if campanas else None

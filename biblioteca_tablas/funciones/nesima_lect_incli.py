"""Función de celda: fecha de la n-ésima lectura activa de un inclinómetro JSON.

Devuelve la fecha ISO de la campaña en la posición ``posicion`` (1 = más antigua
disponible dentro de las últimas ``max_lecturas`` campañas) contando de izquierda
a derecha en orden cronológico.

Comportamiento de llenado:
  Se toman las últimas ``max_lecturas`` campañas activas (≤ fecha_fin) ordenadas
  cronológicamente (más antigua primero).  ``posicion=1`` devuelve la más antigua
  de ese grupo;  ``posicion=max_lecturas`` la más reciente.

  Si hay menos campañas disponibles que ``posicion``, devuelve ``None`` (columna
  vacía), lo que produce huecos **a la derecha** de las columnas con datos.

  Ejemplo con max_lecturas=6 y solo 3 campañas disponibles:
    posicion=1 → 3ª desde el final (más antigua de las 3)
    posicion=2 → 2ª desde el final
    posicion=3 → última (más reciente)
    posicion=4..6 → None  (columnas vacías a la derecha)
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
    "nombre": "nesima_lect_incli",
    "devuelve": "texto",
    "descripcion": (
        "Fecha (ISO) de la n-ésima lectura activa del inclinómetro (contando "
        "de izquierda a derecha, más antigua primero, dentro de las últimas "
        "max_lecturas campañas). Devuelve None si la posición excede las "
        "campañas disponibles."
    ),
    "parametros": [
        {
            "nombre": "sensor",
            "tipo": "texto",
            "descripcion": (
                "Nombre del sensor (stem del JSON en json_inclis/). "
                "Puede ser ref:ancla, ref:literal o ref:contexto."
            ),
        },
        {
            "nombre": "posicion",
            "tipo": "numero",
            "descripcion": (
                "Posición de la lectura (1 = más antigua disponible dentro del "
                "grupo de max_lecturas, max_lecturas = más reciente). "
                "Valores fuera de rango devuelven None."
            ),
        },
        {
            "nombre": "max_lecturas",
            "tipo": "numero",
            "descripcion": (
                "Número máximo de lecturas a considerar (por defecto 6). "
                "Se toman las últimas max_lecturas campañas activas."
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
        logger.warning("[nesima_lect_incli] Archivo no encontrado: %s", ruta)
        return []

    try:
        with ruta.open(encoding="utf-8") as f:
            datos = json.load(f)
    except Exception as exc:
        logger.warning("[nesima_lect_incli] Error leyendo %s: %s", ruta, exc)
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

    return sorted(campanas)  # orden cronológico ascendente


def evaluate(
    params: dict[str, Any],
    data: dict[str, Any],
    context: dict[str, Any],
) -> str | None:
    """Devuelve la fecha ISO de la n-ésima lectura activa.

    Se toman las últimas ``max_lecturas`` campañas activas ≤ fecha_fin,
    ordenadas cronológicamente (más antigua primero = posición 1).

    Args:
        params:
            - ``sensor``       (str): Nombre del sensor / stem del JSON.
            - ``posicion``     (int): 1 = más antigua del grupo, N = más reciente.
            - ``max_lecturas`` (int): Máximo de campañas a considerar (default 6).
            - ``fecha_fin``    (str): Fecha tope (YYYY-MM-DD o ISO completo).
        data:    No se utiliza.
        context: Fallback para ``fecha_fin`` si no está en ``params``.

    Returns:
        Fecha ISO (str) o ``None`` si la posición excede las campañas disponibles.
    """
    sensor: str = params.get("sensor") or ""
    posicion: int = int(params.get("posicion") or 1)
    max_lecturas: int = int(params.get("max_lecturas") or 6)
    fecha_fin: str = (
        params.get("fecha_fin")
        or context.get("fecha_fin")
        or context.get("fecha_final")
        or ""
    )

    if not sensor:
        return None

    campanas = _cargar_campanas_activas(sensor, fecha_fin)

    # Tomar las últimas max_lecturas campañas (ya están en orden cronológico)
    ultimas = campanas[-max_lecturas:] if len(campanas) > max_lecturas else campanas

    # posicion=1 → índice 0 (más antigua del grupo)
    idx = posicion - 1
    return ultimas[idx] if 0 <= idx < len(ultimas) else None

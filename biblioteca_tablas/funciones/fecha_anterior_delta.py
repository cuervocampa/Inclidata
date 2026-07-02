"""Función de celda: fecha de la lectura útil anterior con delta horario mínimo.

A diferencia de fecha_anterior, esta función exige que la lectura devuelta esté
separada al menos ``delta_horas`` de la última lectura válida del sensor.
``delta_horas`` puede venir como parámetro explícito o leerse del contexto
(clave ``_current_delta_horas``) con fallback a 20.
"""
from typing import Any

from utils.lectura_delta import buscar_lectura_anterior_con_delta

CELL_FUNCTION_METADATA: dict[str, Any] = {
    "nombre": "fecha_anterior_delta",
    "devuelve": "texto",
    "descripcion": (
        "Fecha ISO de la última lectura válida del sensor que esté al menos "
        "delta_horas antes que la más reciente."
    ),
    "parametros": [
        {"nombre": "sensor",       "tipo": "ref_celda", "descripcion": "Sensor (columna ancla)"},
        {"nombre": "fecha_limite", "tipo": "texto",     "descripcion": "Fecha tope del rango (YYYY-MM-DD o ISO)"},
        {"nombre": "delta_horas",  "tipo": "numero",    "descripcion": "Horas mínimas de separación (default 20)"},
    ],
}


def evaluate(
    params: dict[str, Any],
    data: dict[str, Any],
    context: dict[str, Any],
) -> str:
    sensor: str = params.get("sensor") or ""
    fecha_limite: str = params.get("fecha_limite") or ""
    delta_horas_raw = params.get("delta_horas")
    if delta_horas_raw is None:
        delta_horas_raw = context.get("_current_delta_horas")
    try:
        delta_horas = float(delta_horas_raw) if delta_horas_raw is not None else 20.0
    except (TypeError, ValueError):
        delta_horas = 20.0

    historico: list[dict] = data.get("historico") or []
    res = buscar_lectura_anterior_con_delta(historico, sensor, fecha_limite, delta_horas)
    return res[0] if res else ""

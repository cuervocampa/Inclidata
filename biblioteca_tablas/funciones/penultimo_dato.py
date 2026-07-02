"""Función de celda: valor numérico de la penúltima lectura válida de un sensor."""

import math
from typing import Any

CELL_FUNCTION_METADATA: dict[str, Any] = {
    "nombre": "penultimo_dato",
    "devuelve": "numero",
    "descripcion": "Devuelve el valor numérico de la penúltima lectura válida del sensor, redondeado.",
    "parametros": [
        {"nombre": "sensor",       "tipo": "ref_celda", "descripcion": "Sensor (columna ancla)"},
        {"nombre": "fecha_limite", "tipo": "texto",    "descripcion": "Fecha tope del rango (YYYY-MM-DD)"},
        {"nombre": "decimales",    "tipo": "numero", "descripcion": "Decimales para redondear (default 3)"},
    ],
}


def _filtrar_lecturas(
    historico: list[dict],
    sensor: str,
    fecha_limite: str,
) -> list[tuple[str, float]]:
    """Devuelve lista de (fecha, valor) válidos, ordenados cronológicamente."""
    resultado = []
    for reg in historico:
        if reg.get("NOM_SENSOR") != sensor:
            continue
        val = reg.get("VALOR")
        if val is None:
            val = reg.get("MEDIDA")
        if val is None:
            continue
        try:
            val_f = float(val)
        except (ValueError, TypeError):
            continue
        if math.isnan(val_f):
            continue
        fecha_reg = reg.get("FECHA") or reg.get("fecha") or reg.get("FECHA_LECTURA") or reg.get("FECHA_MEDIDA") or ""
        if fecha_limite and fecha_reg and str(fecha_reg) > str(fecha_limite):
            continue
        resultado.append((str(fecha_reg), val_f))
    return resultado


def evaluate(
    params: dict[str, Any],
    data: dict[str, Any],
    context: dict[str, Any],
) -> float | str:
    """Devuelve el valor de la penúltima lectura válida del sensor antes de ``fecha_limite``.

    Args:
        params:  ``{"sensor": str, "fecha_limite": str, "decimales": int (opcional)}``.
        data:    Datos en memoria; usa ``data["historico"]`` como lista de dicts.
        context: Contexto global del informe (no utilizado).

    Returns:
        Penúltimo valor redondeado, o cadena vacía si hay <2 lecturas.
    """
    sensor: str = params.get("sensor", "")
    fecha_limite: str = params.get("fecha_limite") or ""
    decimales: int = int(params.get("decimales") or 3)
    historico: list[dict] = data.get("historico") or []

    lecturas = _filtrar_lecturas(historico, sensor, fecha_limite)

    if len(lecturas) >= 2:
        return round(lecturas[-2][1], decimales)
    return ""

"""Función de celda: fecha de la penúltima lectura válida de un sensor."""

import math
from datetime import datetime
from typing import Any

CELL_FUNCTION_METADATA: dict[str, Any] = {
    "nombre": "fecha_anterior",
    "devuelve": "texto",
    "descripcion": "Devuelve la fecha de la penúltima lectura válida del sensor.",
    "parametros": [
        {"nombre": "sensor",       "tipo": "ref_celda", "descripcion": "Sensor (columna ancla)"},
        {"nombre": "fecha_limite", "tipo": "texto",     "descripcion": "Fecha tope del rango (YYYY-MM-DD)"},
    ],
}

_FMT_PARSE = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
)


def _formatear(fecha_str: str, formato_salida: str) -> str:
    """Convierte ``fecha_str`` al ``formato_salida``; devuelve el original si falla."""
    for fmt in _FMT_PARSE:
        try:
            return datetime.strptime(fecha_str.strip(), fmt).strftime(formato_salida)
        except ValueError:
            continue
    return fecha_str


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
) -> str:
    """Devuelve la fecha de la penúltima lectura válida del sensor antes de ``fecha_limite``.

    Args:
        params:  ``{"sensor": str, "fecha_limite": str, "formato_salida": str (opcional)}``.
        data:    Datos en memoria; usa ``data["historico"]`` como lista de dicts.
        context: Contexto global del informe (no utilizado).

    Returns:
        Fecha formateada de la penúltima lectura, o cadena vacía si hay <2 lecturas.
    """
    sensor: str = params.get("sensor", "")
    fecha_limite: str = params.get("fecha_limite") or ""
    historico: list[dict] = data.get("historico") or []

    lecturas = _filtrar_lecturas(historico, sensor, fecha_limite)

    if len(lecturas) >= 2:
        return lecturas[-2][0]
    return ""

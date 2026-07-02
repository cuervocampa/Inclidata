"""Función de celda: diferencia entre el último y el penúltimo dato de un sensor."""

from typing import Any

CELL_FUNCTION_METADATA: dict[str, Any] = {
    "nombre": "incremento",
    "devuelve": "numero",
    "descripcion": "Calcula valor_actual - valor_anterior a partir de dos columnas de la misma fila.",
    "parametros": [
        {"nombre": "valor_actual",   "tipo": "ref_celda", "descripcion": "Columna con el último dato"},
        {"nombre": "valor_anterior", "tipo": "ref_celda", "descripcion": "Columna con el penúltimo dato"},
        {"nombre": "decimales",      "tipo": "numero",    "descripcion": "Decimales para redondear (default 3)"},
    ],
}


def evaluate(
    params: dict[str, Any],
    data: dict[str, Any],
    context: dict[str, Any],
) -> float | str:
    """Resta ``valor_actual - valor_anterior`` usando valores ya resueltos de otras columnas.

    No accede a ``data["historico"]``. Los valores llegan resueltos por el motor
    mediante ref_celda desde columnas anteriores de la misma fila.

    Args:
        params:  ``{"valor_actual": float|str, "valor_anterior": float|str, "decimales": int}``.
        data:    No utilizado.
        context: No utilizado.

    Returns:
        Diferencia redondeada, o cadena vacía si alguno de los valores no es numérico.
    """
    decimales: int = int(params.get("decimales") or 3)

    try:
        actual = float(params.get("valor_actual", ""))
        anterior = float(params.get("valor_anterior", ""))
    except (ValueError, TypeError):
        return ""

    diff = round(actual - anterior, decimales)
    if diff > 0:
        return f"↗ +{diff}"
    elif diff < 0:
        return f"↘ {diff}"
    else:
        return f"→ {diff}"

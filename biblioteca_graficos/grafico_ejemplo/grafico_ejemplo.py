"""
grafico_ejemplo.py
==================
Script de ejemplo que ilustra el uso del decorador @register_script.

Genera un gráfico de barras simple a partir de datos de sensor.
"""

from __future__ import annotations

import io
import base64

from utils.script_registry import register_script, ScriptMetadata, ParameterMetadata

metadata = ScriptMetadata(
    nombre="grafico_ejemplo",
    tipo="grafico",
    descripcion="Gráfico de ejemplo: barras de desplazamiento por profundidad.",
    parametros=[
        ParameterMetadata(
            nombre="sensor",
            tipo="str",
            default="",
            descripcion="Nombre del sensor a representar (p. ej. 'INC-01').",
        ),
        ParameterMetadata(
            nombre="fecha_inicial",
            tipo="str",
            default="$CURRENT",
            descripcion="Fecha inicial del rango (YYYY-MM-DD). Usa '$CURRENT' para el valor del selector.",
        ),
        ParameterMetadata(
            nombre="escala_desplazamiento",
            tipo="float",
            default=10.0,
            descripcion="Escala máxima del eje de desplazamiento (mm).",
        ),
    ],
)


@register_script(metadata)
def grafico_ejemplo(data: dict, parametros: dict) -> str:
    """
    Genera un gráfico de barras simple.

    Args:
        data: Datos de la base de datos (tubos, campañas, etc.)
        parametros: Parámetros configurados en el editor (ver ``metadata.parametros``).

    Returns:
        Data URI de la imagen PNG generada (``data:image/png;base64,...``).
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return ""

    sensor = parametros.get("sensor", "N/A")
    escala = float(parametros.get("escala_desplazamiento", 10.0))

    # Datos sintéticos de ejemplo
    profundidades = list(range(0, 20, 2))
    desplazamientos = [i * 0.3 for i in range(len(profundidades))]

    fig, ax = plt.subplots(figsize=(4, 6))
    ax.barh(profundidades, desplazamientos, height=1.5, color="#4f8ef7", alpha=0.8)
    ax.set_xlim(0, max(escala, max(desplazamientos) + 1))
    ax.set_xlabel("Desplazamiento (mm)")
    ax.set_ylabel("Profundidad (m)")
    ax.set_title(f"Sensor: {sensor}")
    ax.invert_yaxis()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=96)
    plt.close(fig)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"

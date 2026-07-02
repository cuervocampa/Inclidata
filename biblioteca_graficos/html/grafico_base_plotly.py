"""Gráfico base Plotly — línea spline con bandas de umbral.

Genera un gráfico de serie temporal con línea suavizada (spline) y bandas
de fondo al 10 % de opacidad para los tres niveles de umbral de alerta:
Atención (naranja), Preavís (rojo) y Notificació (rojo intenso).

Función principal: ``generate(params, figsize) -> str``

Parámetros
----------
sensor / nombre_sensor : str
    Nombre del sensor. Aparece en título y leyenda.
n_puntos : int, opcional
    Puntos sintéticos de demostración (default: 60).
titulo : str, opcional
    Título del gráfico.
color : str, opcional
    Color de la línea (default: ``"#1c7ed6"``).
umbral_atencion : float, opcional
    Límite inferior de la zona naranja (default: 10).
umbral_preaviso : float, opcional
    Límite inferior de la zona roja (default: 25).
umbral_notificacio : float, opcional
    Límite superior: por encima inicia zona rojo intenso (default: 40).
"""

from __future__ import annotations
from typing import Any


PARAMETER_METADATA: list[dict] = [
    {"nombre": "sensor",             "tipo": "texto",   "requerido": False},
    {"nombre": "n_puntos",           "tipo": "numero",  "requerido": False, "default": 60},
    {"nombre": "titulo",             "tipo": "texto",   "requerido": False},
    {"nombre": "color",              "tipo": "texto",   "requerido": False, "default": "#1c7ed6"},
    {"nombre": "umbral_atencion",    "tipo": "numero",  "requerido": False, "default": 10},
    {"nombre": "umbral_preaviso",    "tipo": "numero",  "requerido": False, "default": 25},
    {"nombre": "umbral_notificacio", "tipo": "numero",  "requerido": False, "default": 40},
]


def generate(params: dict[str, Any], figsize: tuple[float, float]) -> str:
    """Genera la figura Plotly y devuelve un fragmento HTML autocontenido.

    La línea usa ``line_shape='spline'`` para suavizado cúbico.
    Las bandas de umbral se añaden con ``add_hrect`` a 10 % de opacidad para
    no interferir visualmente con los datos.

    Args:
        params:  Parámetros de configuración.
        figsize: ``(ancho_pulgadas, alto_pulgadas)`` del contenedor destino.

    Returns:
        Fragmento HTML con Plotly.js embebido (sin ``<html>``/``<body>``).
    """
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
    except ImportError:
        return (
            "<p style='color:#c0392b;font-family:Arial;font-size:10pt;'>"
            "Error: Plotly no está instalado. Ejecuta: <code>pip install plotly</code></p>"
        )

    # ── Parámetros ────────────────────────────────────────────────────────────
    sensor   = str(params.get("sensor") or params.get("nombre_sensor") or "Sensor")
    color    = str(params.get("color") or "#1c7ed6")
    n_puntos = int(params.get("n_puntos") or 60)
    titulo   = str(params.get("titulo") or f"Evolución temporal — {sensor}")

    u_aten   = float(params.get("umbral_atencion",    10))
    u_prev   = float(params.get("umbral_preaviso",    25))
    u_noti   = float(params.get("umbral_notificacio", 40))

    width_px  = int(figsize[0] * 96)
    height_px = int(figsize[1] * 96)

    # ── Datos sintéticos de demostración ─────────────────────────────────────
    # Genera una trayectoria que atraviesa las zonas de umbral para mostrar
    # las bandas de fondo de forma significativa.
    try:
        import numpy as np
        rng     = np.random.default_rng(seed=7)
        steps   = rng.normal(0.5, 0.8, n_puntos)       # tendencia positiva leve
        y_vals  = list(np.cumsum(steps).round(3))
        x_vals  = list(range(n_puntos))
    except ImportError:
        import random
        random.seed(7)
        y_vals = [0.0]
        for _ in range(n_puntos - 1):
            y_vals.append(round(y_vals[-1] + random.gauss(0.5, 0.8), 3))
        x_vals = list(range(n_puntos))

    y_min = min(y_vals)
    y_max = max(y_vals)
    y_pad = (y_max - y_min) * 0.08 or 2.0
    axis_y0 = min(y_min - y_pad, 0)
    axis_y1 = max(y_max + y_pad, u_noti * 1.1)

    # ── Figura ────────────────────────────────────────────────────────────────
    fig = go.Figure()

    # Bandas de umbral (debajo de la serie: layer='below')
    # Zona Atención: naranja 10 %
    fig.add_hrect(
        y0=u_aten, y1=u_prev,
        fillcolor="#F59E0B", opacity=0.10, line_width=0, layer="below",
        annotation_text="Atenció", annotation_position="top right",
        annotation_font=dict(size=7, color="#D97706"),
    )
    # Zona Preavís: rojo suave 10 %
    fig.add_hrect(
        y0=u_prev, y1=u_noti,
        fillcolor="#EF4444", opacity=0.10, line_width=0, layer="below",
        annotation_text="Preavís", annotation_position="top right",
        annotation_font=dict(size=7, color="#DC2626"),
    )
    # Zona Notificació: rojo intenso 10 %
    fig.add_hrect(
        y0=u_noti, y1=axis_y1 * 1.05,
        fillcolor="#991B1B", opacity=0.10, line_width=0, layer="below",
        annotation_text="Notificació", annotation_position="top right",
        annotation_font=dict(size=7, color="#991B1B"),
    )

    # Líneas de umbral finas
    for y_val, lcolor in [(u_aten, "#F59E0B"), (u_prev, "#EF4444"), (u_noti, "#991B1B")]:
        fig.add_hline(y=y_val, line_width=0.7, line_dash="dot", line_color=lcolor, opacity=0.6)

    # Serie principal con línea spline
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=y_vals,
        mode="lines",
        name=sensor,
        line=dict(color=color, width=2, shape="spline", smoothing=1.2),
        fill="tozeroy",
        fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.07)",
    ))

    fig.update_layout(
        title=dict(text=titulo, font=dict(size=11, family="Arial, sans-serif"), x=0.0, xanchor="left"),
        margin=dict(l=45, r=30, t=38, b=32),
        paper_bgcolor="white",
        plot_bgcolor="#FAFAFA",
        font=dict(family="Arial, sans-serif", size=9),
        xaxis=dict(
            showgrid=True, gridcolor="#EEEEEE", linecolor="#D1D5DB",
            tickfont=dict(size=8), title=dict(text="Muestra", font=dict(size=8)),
        ),
        yaxis=dict(
            showgrid=True, gridcolor="#EEEEEE", linecolor="#D1D5DB",
            tickfont=dict(size=8), title=dict(text="Asentamiento (mm)", font=dict(size=8)),
            range=[axis_y0, axis_y1],
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, font=dict(size=8)),
        showlegend=True,
        width=width_px,
        height=height_px,
    )

    return pio.to_html(
        fig,
        include_plotlyjs=False,
        full_html=False,
        config={"staticPlot": True},
    )

"""
utils/dev_logging.py
====================
Herramientas de diagnóstico para desarrollo. No se importan en producción.

Activa el monkey-patch de callbacks con DEBUG_CALLBACKS=1 en el entorno:

    DEBUG_CALLBACKS=1 python app.py
"""
from __future__ import annotations

import functools
import json
import logging
import os
import traceback

import plotly.utils

logger = logging.getLogger("callback_errors")


def apply_callback_logging(app) -> None:
    """Envuelve todos los callbacks registrados para capturar errores y valores inválidos."""
    if not os.getenv("DEBUG_CALLBACKS"):
        return

    for cb_id, cb_list in app.callback_map.items():
        original = cb_list.get("callback")
        if not (original and callable(original)):
            continue

        @functools.wraps(original)
        def _wrapper(*args, _orig=original, _name=cb_id, **kwargs):
            try:
                res = _orig(*args, **kwargs)
            except Exception:
                logger.error(f"[{_name}] EXCEPTION:\n{traceback.format_exc()}")
                raise

            try:
                j_str = json.dumps(res, cls=plotly.utils.PlotlyJSONEncoder)
                if "NaN" in j_str or "Infinity" in j_str:
                    logger.error(f"[{_name}] devuelve NaN/Infinity que rompe Dash")
            except Exception:
                pass

            return res

        cb_list["callback"] = _wrapper

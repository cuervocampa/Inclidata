"""Registro de funciones de celda para tablas dinámicas.

Las funciones están ubicadas en ``biblioteca_tablas/funciones/``.
Cada módulo debe exponer:
- ``CELL_FUNCTION_METADATA: dict`` — metadatos descriptivos.
- ``evaluate(params, data, context)`` — lógica de evaluación.
"""

import importlib.util
import logging
from pathlib import Path
from types import ModuleType
from typing import Any

logger = logging.getLogger(__name__)

_FUNCIONES_DIR = Path(__file__).parent.parent / "biblioteca_tablas" / "funciones"
_cache: dict[str, ModuleType] = {}


def get_function(name: str) -> ModuleType:
    """Carga y devuelve el módulo de la función de celda indicada.

    El módulo se cachea tras la primera carga. Lanza ``ValueError`` si no
    se encuentra el archivo o ``ImportError`` si el módulo no puede cargarse.

    Args:
        name: Nombre de la función (sin extensión), ej. ``"ultima_lectura"``.

    Returns:
        Módulo Python con al menos ``evaluate(params, data, context)``.
    """
    if name in _cache:
        return _cache[name]

    module_path = _FUNCIONES_DIR / f"{name}.py"
    if not module_path.is_file():
        raise ValueError(f"Función de celda no encontrada: '{name}' ({module_path})")

    spec = importlib.util.spec_from_file_location(f"cell_fn.{name}", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo crear spec para '{name}'")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except Exception as exc:
        raise ImportError(f"Error cargando función de celda '{name}': {exc}") from exc

    _cache[name] = module
    return module


def list_functions() -> list[dict[str, Any]]:
    """Devuelve los metadatos de todas las funciones de celda disponibles.

    Returns:
        Lista de dicts ``CELL_FUNCTION_METADATA`` de cada módulo encontrado.
    """
    result: list[dict[str, Any]] = []
    for path in sorted(_FUNCIONES_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            mod = get_function(path.stem)
            meta = getattr(mod, "CELL_FUNCTION_METADATA", {"nombre": path.stem})
            result.append(meta)
        except Exception as exc:
            logger.warning("[CellRegistry] No se pudo cargar '%s': %s", path.stem, exc)
    return result


_metadata_cache: list[dict[str, Any]] | None = None


def list_cell_functions_metadata() -> list[dict[str, Any]]:
    """Devuelve metadatos estructurados de todas las funciones de celda disponibles.

    Extrae y normaliza los campos necesarios para la UI del editor visual
    (selectores de función por celda). El resultado se cachea en memoria.

    Returns:
        Lista de dicts con las claves ``nombre``, ``descripcion``, ``devuelve``
        y ``parametros`` de cada función registrada.
    """
    global _metadata_cache
    if _metadata_cache is not None:
        return _metadata_cache

    result: list[dict[str, Any]] = []
    for meta in list_functions():
        result.append({
            "nombre":      meta.get("nombre", ""),
            "descripcion": meta.get("descripcion", ""),
            "devuelve":    meta.get("devuelve", ""),
            "parametros":  meta.get("parametros", []),
        })

    _metadata_cache = result
    return _metadata_cache

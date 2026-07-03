"""
utils/template_service.py
==========================
Servicio de gestión de plantillas — backend puro, sin dependencias de Dash.

API pública
-----------
Listado:
  listar_plantillas_disponibles()      -> list[dict]
  listar_scripts_graficos()            -> list[str]          (nombres .py)
  listar_scripts_tablas()              -> list[str]          (nombres .py)
  listar_metadata_graficos()           -> dict[str, dict]    (metadatos por nombre)
  listar_metadata_tablas()             -> dict[str, dict]    (metadatos por nombre)

Carga:
  cargar_plantilla(nombre)             -> dict   (JSON raw)
  _encontrar_json_plantilla(nombre)    -> Path | None

Excepciones propias:
  PlantillaNoEncontrada  (FileNotFoundError)
  PlantillaInvalida      (ValueError)

Funciones del editor visual (guardar_plantilla, fusionar_grupo_en_plantilla, etc.)
archivadas en info/legacy/template_service_editor_funcs.py — el editor se eliminó
de IncliData en v2.0; las plantillas se crean en Maketator.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from utils.script_registry import (
    discover_scripts,
    get_graficos_metadata,
    get_tablas_metadata,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rutas base
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
PLANTILLAS_DIR = BASE_DIR / "biblioteca_plantillas"
GRAFICOS_DIR = BASE_DIR / "biblioteca_graficos"
TABLAS_DIR = BASE_DIR / "biblioteca_tablas"


# ---------------------------------------------------------------------------
# Excepciones propias
# ---------------------------------------------------------------------------

class PlantillaNoEncontrada(FileNotFoundError):
    """Se lanza cuando el archivo JSON de una plantilla no existe en disco."""


class PlantillaInvalida(ValueError):
    """Se lanza cuando el JSON de una plantilla tiene una estructura inválida."""


# ---------------------------------------------------------------------------
# Listado de recursos disponibles
# ---------------------------------------------------------------------------

def listar_plantillas_disponibles() -> list[dict]:
    """
    Lista las plantillas presentes en biblioteca_plantillas/.

    Returns:
        Lista de dicts ``{"label": nombre, "value": nombre}``, ordenada
        alfabéticamente por nombre.
    """
    if not PLANTILLAS_DIR.exists():
        return []

    resultado = []
    for item in PLANTILLAS_DIR.iterdir():
        if item.is_dir() and (item / f"{item.name}.json").exists():
            resultado.append({"label": item.name, "value": item.name})

    return sorted(resultado, key=lambda d: d["label"])


def _ensure_registry() -> None:
    """Llama a discover_scripts() si el registro aún no tiene entradas."""
    from utils.script_registry import get_all_metadata
    if not get_all_metadata():
        discover_scripts()


def listar_scripts_graficos() -> list[str]:
    """
    Lista los scripts de gráficos disponibles.

    Returns:
        Lista de nombres de archivo ``"{nombre}.py"`` ordenada alfabéticamente.
    """
    _ensure_registry()
    return sorted(f"{nombre}.py" for nombre in get_graficos_metadata())


def listar_scripts_tablas() -> list[str]:
    """
    Lista los scripts de tablas disponibles.

    Returns:
        Lista de nombres de archivo ``"{nombre}.py"`` ordenada alfabéticamente.
    """
    _ensure_registry()
    return sorted(f"{nombre}.py" for nombre in get_tablas_metadata())


def listar_metadata_graficos() -> dict[str, dict]:
    """
    Devuelve los metadatos de todos los scripts de gráficos.

    Returns:
        Dict ``{nombre_script: ScriptMetadata.model_dump()}`` ordenado por nombre.
    """
    _ensure_registry()
    return {
        nombre: meta.model_dump()
        for nombre, meta in sorted(get_graficos_metadata().items())
    }


def listar_metadata_tablas() -> dict[str, dict]:
    """
    Devuelve los metadatos de todos los scripts de tablas.

    Returns:
        Dict ``{nombre_script: ScriptMetadata.model_dump()}`` ordenado por nombre.
    """
    _ensure_registry()
    return {
        nombre: meta.model_dump()
        for nombre, meta in sorted(get_tablas_metadata().items())
    }


# ---------------------------------------------------------------------------
# Resolución de rutas de plantillas
# ---------------------------------------------------------------------------

# Trasplantado de Maketator (fase 3) — requerido por engines/html_engine.py
def _encontrar_json_plantilla(nombre: str, engine: str | None = None) -> Path | None:
    """Localiza el archivo JSON de una plantilla dado su nombre o ruta con namespace.

    Estrategia de búsqueda (en orden de prioridad):

    1. Si ``nombre`` contiene ``/``: ruta relativa desde ``PLANTILLAS_DIR``.
    2. Si se pasa ``engine``: prioriza ``PLANTILLAS_DIR/{engine}/{nombre}/{nombre}.json``.
    3. Ruta canónica legacy: ``{PLANTILLAS_DIR}/{nombre}/{nombre}.json``.
    4. Búsqueda recursiva global como último recurso.

    Args:
        nombre: Nombre sin extensión o ruta relativa con namespace (ej. ``"html/temporal_test_03"``).
        engine: Motor opcional (``"html"``…) para priorizar la búsqueda.

    Returns:
        ``Path`` al JSON encontrado, o ``None`` si no existe.
    """
    if "/" in nombre:
        stem = Path(nombre).name
        direct = PLANTILLAS_DIR / nombre / f"{stem}.json"
        if direct.is_file():
            return direct
        subdir = PLANTILLAS_DIR / nombre
        if subdir.is_dir():
            hits = list(subdir.rglob(f"{stem}.json"))
            if hits:
                return hits[0]
            any_hits = sorted(subdir.glob("*.json"))
            if any_hits:
                log.warning(
                    "_encontrar_json_plantilla: la carpeta '%s' no contiene '%s.json'; "
                    "usando '%s' como alternativa.",
                    subdir, stem, any_hits[0].name,
                )
                return any_hits[0]
        hits = list(PLANTILLAS_DIR.rglob(f"{stem}.json"))
        return hits[0] if hits else None

    if engine:
        engine_dir = PLANTILLAS_DIR / engine
        if engine_dir.is_dir():
            engine_canonical = engine_dir / nombre / f"{nombre}.json"
            if engine_canonical.is_file():
                return engine_canonical
            engine_hits = list(engine_dir.rglob(f"{nombre}.json"))
            if engine_hits:
                return engine_hits[0]

    legacy = PLANTILLAS_DIR / nombre / f"{nombre}.json"
    if legacy.is_file():
        return legacy

    matches = list(PLANTILLAS_DIR.rglob(f"{nombre}.json"))
    return matches[0] if matches else None


# ---------------------------------------------------------------------------
# Carga de plantillas
# ---------------------------------------------------------------------------

# Cuerpo trasplantado de Maketator (fase 3): devuelve dict crudo del JSON.
def cargar_plantilla(nombre: str) -> dict:
    """Carga y devuelve el JSON de una plantilla dado su nombre (stem).

    Args:
        nombre: Nombre del archivo sin extensión (ej. ``"temporal_test_03"``).

    Returns:
        Diccionario con la estructura completa de la plantilla.

    Raises:
        PlantillaNoEncontrada: si no se encuentra el JSON.
        PlantillaInvalida: si el JSON tiene errores de sintaxis.
    """
    json_path = _encontrar_json_plantilla(nombre)
    if json_path is None:
        raise PlantillaNoEncontrada(f"Plantilla '{nombre}' no encontrada en {PLANTILLAS_DIR}.")
    try:
        with json_path.open(encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise PlantillaInvalida(f"JSON inválido en plantilla '{nombre}': {exc}") from exc

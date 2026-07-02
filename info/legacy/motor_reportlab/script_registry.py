"""
utils/script_registry.py
=========================
Registro centralizado de capacidades para los scripts dinámicos de gráficos y tablas.

Uso básico en un script
-----------------------
    from utils.script_registry import register_script, ScriptMetadata, ParameterMetadata

    metadata = ScriptMetadata(
        nombre="mi_grafico",
        tipo="grafico",
        descripcion="Descripción del gráfico.",
        parametros=[
            ParameterMetadata(nombre="sensor", tipo="str", descripcion="Sensor a graficar"),
            ParameterMetadata(nombre="fecha_inicial", tipo="str", default="$CURRENT"),
        ],
    )

    @register_script(metadata)
    def mi_grafico(data, parametros):
        ...

API pública
-----------
  register_script(metadata)          → decorador (registra al importar el módulo)
  discover_scripts()                 → descubre e importa todos los scripts de las carpetas
  get_all_metadata()                 → dict[str, ScriptMetadata]   (clave = nombre sin .py)
  get_graficos_metadata()            → dict[str, ScriptMetadata]
  get_tablas_metadata()              → dict[str, ScriptMetadata]
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
GRAFICOS_DIR = BASE_DIR / "biblioteca_graficos"
TABLAS_DIR = BASE_DIR / "biblioteca_tablas"


# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------

class ParameterMetadata(BaseModel):
    """Metadatos de un parámetro de script."""

    nombre: str
    tipo: str = "str"
    default: Any = None
    descripcion: str = ""


class ScriptMetadata(BaseModel):
    """Metadatos completos de un script dinámico."""

    nombre: str
    tipo: str                              # "grafico" | "tabla"
    descripcion: str = ""
    parametros: list[ParameterMetadata] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Registro global
# ---------------------------------------------------------------------------

class ScriptRegistry:
    """Registro singleton de scripts dinámicos."""

    _instance: ScriptRegistry | None = None
    _registry: dict[str, ScriptMetadata]

    def __new__(cls) -> ScriptRegistry:
        if cls._instance is None:
            obj = super().__new__(cls)
            obj._registry = {}
            cls._instance = obj
        return cls._instance

    def register(self, metadata: ScriptMetadata) -> None:
        """Registra los metadatos de un script. Sobreescribe si ya existe."""
        self._registry[metadata.nombre] = metadata
        log.debug("Script registrado: %s (%s)", metadata.nombre, metadata.tipo)

    def get_all(self) -> dict[str, ScriptMetadata]:
        return dict(self._registry)

    def get_by_tipo(self, tipo: str) -> dict[str, ScriptMetadata]:
        return {k: v for k, v in self._registry.items() if v.tipo == tipo}

    def reset(self) -> None:
        """Limpia el registro (útil en tests)."""
        self._registry.clear()


_registry = ScriptRegistry()


# ---------------------------------------------------------------------------
# Decorador
# ---------------------------------------------------------------------------

def register_script(metadata: ScriptMetadata) -> Callable:
    """
    Decorador que registra un script en el registro global al ser importado.

    Uso::

        @register_script(ScriptMetadata(nombre="mi_script", tipo="grafico", ...))
        def mi_script(data, parametros):
            ...
    """
    def decorator(fn: Callable) -> Callable:
        _registry.register(metadata)
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Descubrimiento automático
# ---------------------------------------------------------------------------

def _import_script_module(script_path: Path) -> bool:
    """
    Importa dinámicamente un archivo .py para activar sus decoradores.

    Returns:
        True si se importó correctamente, False en caso de error.
    """
    module_name = f"_script_registry_{script_path.stem}"
    if module_name in sys.modules:
        return True  # ya importado

    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        log.warning("No se pudo crear spec para %s", script_path)
        return False

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return True
    except Exception:
        log.warning("Error al importar script %s — se omite.", script_path, exc_info=True)
        del sys.modules[module_name]
        return False


def _fallback_metadata(script_path: Path, tipo: str) -> ScriptMetadata:
    """
    Genera metadatos mínimos para scripts sin decorador @register_script.
    """
    nombre = script_path.stem
    return ScriptMetadata(
        nombre=nombre,
        tipo=tipo,
        descripcion=f"Script {tipo} '{nombre}' (sin metadatos declarados).",
        parametros=[],
    )


def discover_scripts() -> None:
    """
    Recorre ``biblioteca_graficos/`` y ``biblioteca_tablas/``, importa cada
    script ``{nombre}/{nombre}.py`` para activar los decoradores y genera
    metadatos de respaldo para los scripts que no los tengan.

    Es idempotente: llamadas repetidas no duplican entradas.
    """
    carpetas: list[tuple[Path, str]] = [
        (GRAFICOS_DIR, "grafico"),
        (TABLAS_DIR, "tabla"),
    ]

    for carpeta, tipo in carpetas:
        if not carpeta.exists():
            continue

        for item in sorted(carpeta.iterdir()):
            if not item.is_dir():
                continue
            script_path = item / f"{item.name}.py"
            if not script_path.exists():
                continue

            nombre = item.name
            ya_registrado = nombre in _registry.get_all()
            importado = _import_script_module(script_path)

            # Si después de importar sigue sin estar registrado → fallback
            if importado and nombre not in _registry.get_all():
                _registry.register(_fallback_metadata(script_path, tipo))
            elif not importado and not ya_registrado:
                _registry.register(_fallback_metadata(script_path, tipo))


# ---------------------------------------------------------------------------
# Getters de conveniencia
# ---------------------------------------------------------------------------

def get_all_metadata() -> dict[str, ScriptMetadata]:
    """Devuelve todos los scripts registrados."""
    return _registry.get_all()


def get_graficos_metadata() -> dict[str, ScriptMetadata]:
    """Devuelve sólo los scripts de tipo 'grafico'."""
    return _registry.get_by_tipo("grafico")


def get_tablas_metadata() -> dict[str, ScriptMetadata]:
    """Devuelve sólo los scripts de tipo 'tabla'."""
    return _registry.get_by_tipo("tabla")

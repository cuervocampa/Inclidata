"""
utils/report_engine.py
======================
Capa superior de generación de informes PDF.

Trabaja con objetos Pydantic (Plantilla), usa el ScriptRegistry para
descubrir y ejecutar scripts, pre-computa todo el contenido dinámico
y delega el renderizado final a pdf_generator.py.

API pública
-----------
  resolve_template(plantilla, context)              -> Plantilla
  generate_report_pdf(nombre, context, output_path) -> bool
"""

from __future__ import annotations

import base64
import importlib.util
import logging
import sys
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from info.legacy.template_models import (
    Elemento,
    Plantilla,
    TipoElemento,
)
from utils.script_registry import discover_scripts, get_all_metadata
from utils.template_service import cargar_plantilla

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rutas base
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
PLANTILLAS_DIR = BASE_DIR / "biblioteca_plantillas"
GRAFICOS_DIR = BASE_DIR / "biblioteca_graficos"
TABLAS_DIR = BASE_DIR / "biblioteca_tablas"

# ---------------------------------------------------------------------------
# Tokens de contexto
# ---------------------------------------------------------------------------

_CONTEXT_KEYS: dict[str, Callable[[dict], str]] = {
    "$CURRENT_fecha_seleccionada": lambda ctx: str(ctx.get("fecha_seleccionada") or ""),
    "$CURRENT_ultimas_camp":       lambda ctx: str(ctx.get("ultimas_camp") or ""),
    "$CURRENT_fecha_inicial":      lambda ctx: str(ctx.get("fecha_inicial") or ""),
    "$CURRENT_fecha_final":        lambda ctx: str(ctx.get("fecha_final") or ""),
    # $CURRENT debe ir al final para no interferir con las claves más largas
    "$CURRENT":                    lambda ctx: str(
        ctx.get("info", {}).get("nom_sensor", "") if isinstance(ctx.get("info"), dict) else ""
    ),
}

# Valores de relleno para generación de maquetación (sin datos reales).
# Se usan cuando un token $CURRENT no puede resolverse desde el contexto real.
DUMMY_CONTEXT: dict[str, str] = {
    "$CURRENT":                    "SENSOR_PRUEBA",
    "$CURRENT_fecha_seleccionada": "2026-01-31",
    "$CURRENT_ultimas_camp":       "3",
    "$CURRENT_fecha_inicial":      "2026-01-01",
    "$CURRENT_fecha_final":        "2026-01-31",
}


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _ensure_registry() -> None:
    """Llama a discover_scripts() si el registro aún no tiene entradas."""
    if not get_all_metadata():
        discover_scripts()


def _merge_dummy_context(context: dict) -> dict:
    """
    Devuelve una copia del contexto con las claves faltantes rellenadas
    desde DUMMY_CONTEXT (valores de prueba para maquetación).

    Esto garantiza que los scripts siempre reciban valores válidos
    aunque el usuario no haya completado el formulario de contexto.
    """
    info_orig = context.get("info") or {}
    merged: dict = {
        "info": {
            "nom_sensor": info_orig.get("nom_sensor") or DUMMY_CONTEXT["$CURRENT"],
            **{k: v for k, v in info_orig.items() if k != "nom_sensor"},
        },
        "fecha_seleccionada": context.get("fecha_seleccionada") or DUMMY_CONTEXT["$CURRENT_fecha_seleccionada"],
        "fecha_inicial":      context.get("fecha_inicial")      or DUMMY_CONTEXT["$CURRENT_fecha_inicial"],
        "fecha_final":        context.get("fecha_final")        or DUMMY_CONTEXT["$CURRENT_fecha_final"],
        "ultimas_camp":       context.get("ultimas_camp")       or int(DUMMY_CONTEXT["$CURRENT_ultimas_camp"]),
    }
    # Conservar cualquier otra clave del contexto original
    for k, v in context.items():
        if k not in merged:
            merged[k] = v
    return merged


def _resolve_params(params: Any, context: dict) -> Any:
    """
    Recorre recursivamente el dict de parámetros y sustituye tokens $CURRENT*.
    Si el valor resuelto es vacío (contexto parcial), usa DUMMY_CONTEXT como respaldo.
    """
    if isinstance(params, str):
        for token, fn in _CONTEXT_KEYS.items():
            if token in params:
                resolved = fn(context)
                if not resolved:
                    resolved = DUMMY_CONTEXT.get(token, "[DATO MUESTRA]")
                params = params.replace(token, resolved)
        return params
    if isinstance(params, dict):
        return {k: _resolve_params(v, context) for k, v in params.items()}
    if isinstance(params, list):
        return [_resolve_params(v, context) for v in params]
    return params


def _load_script_fn(script_path: Path, fn_name: str) -> Optional[Callable]:
    """
    Carga el módulo desde *script_path* y devuelve el atributo *fn_name*,
    o None si falla.
    """
    module_name = f"_re_{script_path.stem}"
    # Reusar el módulo si ya fue cargado previamente
    if module_name in sys.modules:
        return getattr(sys.modules[module_name], fn_name, None)

    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        log.warning("No se pudo crear spec para %s", script_path)
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except Exception:
        log.warning("Error al importar %s", script_path, exc_info=True)
        del sys.modules[module_name]
        return None

    return getattr(module, fn_name, None)


def _make_error_image(width_cm: float, height_cm: float, msg: str) -> str:
    """
    Genera un PNG con fondo rosado y mensaje de error en rojo.
    Devuelve data URI ``data:image/png;base64,...``.
    Si matplotlib falla, devuelve un PNG mínimo 1×1 hard-coded.
    """
    _MINIMAL_PNG = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
    )
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import io

        dpi = 96
        fig, ax = plt.subplots(figsize=(width_cm / 2.54, height_cm / 2.54), dpi=dpi)
        ax.set_facecolor("#ffe0e0")
        fig.patch.set_facecolor("#ffe0e0")
        ax.text(
            0.5, 0.5, f"Error:\n{msg}",
            ha="center", va="center", color="red",
            fontsize=8, wrap=True,
            transform=ax.transAxes,
        )
        ax.axis("off")

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode()
        return f"data:image/png;base64,{encoded}"
    except Exception:
        log.warning("_make_error_image: matplotlib falló, usando PNG mínimo.")
        return _MINIMAL_PNG


def _make_placeholder_image(width_cm: float, height_cm: float, script_name: str) -> str:
    """
    Genera un PNG de maquetación: fondo gris muy claro, borde negro fino
    y el nombre del script centrado en gris oscuro.
    Devuelve data URI ``data:image/png;base64,...``.
    """
    _MINIMAL_PNG = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
    )
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import io

        dpi = 96
        fig, ax = plt.subplots(figsize=(width_cm / 2.54, height_cm / 2.54), dpi=dpi)
        fig.patch.set_facecolor("#f5f5f5")
        ax.set_facecolor("#f5f5f5")
        for spine in ax.spines.values():
            spine.set_edgecolor("#000000")
            spine.set_linewidth(1.0)
            spine.set_visible(True)
        ax.set_xticks([])
        ax.set_yticks([])
        label = f"□  {script_name}"
        ax.text(
            0.5, 0.5, label,
            ha="center", va="center", color="#555555",
            fontsize=max(6, min(10, width_cm * 1.2)),
            transform=ax.transAxes,
        )

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=dpi)
        plt.close(fig)
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode()
        return f"data:image/png;base64,{encoded}"
    except Exception:
        log.warning("_make_placeholder_image: matplotlib falló, usando PNG mínimo.")
        return _MINIMAL_PNG


def _execute_graph(elem: Elemento, context: dict, graficos_dir: Path) -> None:
    """
    Ejecuta el script de gráfico y almacena el data URI en elem.contenido.src.
    Si falla, almacena una imagen de error.
    """
    cfg = elem.configuracion
    script_stem = Path(cfg.script).stem
    script_path = graficos_dir / script_stem / f"{script_stem}.py"

    ancho_cm = elem.geometria.ancho
    alto_cm = elem.geometria.alto

    fn = _load_script_fn(script_path, script_stem)
    if fn is None:
        log.warning("Función '%s' no encontrada en %s", script_stem, script_path)
        elem.contenido.src = _make_error_image(
            ancho_cm, alto_cm, f"Script no encontrado: {cfg.script}"
        )
        return

    # Si estamos en modo maquetación, mostramos un placeholder limpio
    if context.get("is_maquetacion"):
        elem.contenido.src = _make_placeholder_image(
            ancho_cm, alto_cm, script_stem
        )
        return

    try:
        result = fn(context, cfg.parametros)
        if isinstance(result, str) and result.startswith("data:"):
            elem.contenido.src = result
        else:
            log.warning(
                "El script %s no devolvió un data URI válido (tipo=%s).",
                script_stem, type(result).__name__,
            )
            elem.contenido.src = _make_error_image(
                ancho_cm, alto_cm, f"Resultado inválido de {cfg.script}"
            )
    except Exception:
        log.exception("Error ejecutando script de gráfico '%s'.", script_stem)
        elem.contenido.src = _make_error_image(
            ancho_cm, alto_cm, f"Error en {cfg.script}"
        )


def _execute_table(elem: Elemento, context: dict, tablas_dir: Path) -> None:
    """
    Ejecuta el script de tabla y almacena el resultado en
    elem.configuracion.datos_ejecutados.
    Si falla, deja datos_ejecutados en None.
    """
    cfg = elem.configuracion
    script_stem = Path(cfg.script).stem
    script_path = tablas_dir / script_stem / f"{script_stem}.py"

    fn = _load_script_fn(script_path, script_stem)
    if fn is None:
        log.warning("Función '%s' no encontrada en %s", script_stem, script_path)
        return

    # Si estamos en modo maquetación parcial/total, simulamos celdas dummy sin acceder a BD
    if context.get("is_maquetacion"):
        cfg.datos_ejecutados = {
            "celdas": {
                "00": {"valor": "Dato 1"},
                "01": {"valor": "Dato 2"},
                "10": {"valor": "Dato 3"},
                "11": {"valor": "Dato 4"}
            }
        }
        return

    try:
        result = fn(context, cfg.parametros)
        if isinstance(result, dict):
            cfg.datos_ejecutados = result
        else:
            log.warning(
                "El script %s no devolvió un dict (tipo=%s).",
                script_stem, type(result).__name__,
            )
    except Exception:
        log.exception("Error ejecutando script de tabla '%s'.", script_stem)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def resolve_template(plantilla: Plantilla, context: Dict[str, Any]) -> Plantilla:
    """
    Resuelve tokens $CURRENT y pre-computa el contenido dinámico de todos
    los elementos de tipo gráfico y tabla.

    Args:
        plantilla: Objeto Plantilla cargado desde disco (unidades en cm).
        context:   Dict con datos de contexto (info, fecha_seleccionada, etc.).

    Returns:
        Copia profunda de la plantilla con contenido pre-computado:
          - Gráficos: ``elem.contenido.src`` = data URI.
          - Tablas:   ``elem.configuracion.datos_ejecutados`` = dict de datos.
    """
    copia = plantilla.model_copy(deep=True)
    _ensure_registry()

    # Completar el contexto con valores dummy para claves ausentes.
    # Esto permite la generación de maquetación incluso con context={}.
    effective_ctx = _merge_dummy_context(context)

    for pagina in copia.paginas.values():
        for elem in pagina.elementos.values():
            if elem.tipo not in (TipoElemento.GRAFICO, TipoElemento.TABLA):
                continue
            if not elem.configuracion or not elem.configuracion.script:
                continue

            # Resolver tokens en parámetros usando el contexto efectivo
            elem.configuracion.parametros = _resolve_params(
                elem.configuracion.parametros, effective_ctx
            )

            if elem.tipo == TipoElemento.GRAFICO:
                _execute_graph(elem, effective_ctx, GRAFICOS_DIR)
            else:
                _execute_table(elem, effective_ctx, TABLAS_DIR)

    return copia


def _plantilla_to_pdf_dict(plantilla: Plantilla) -> dict:
    """
    Serializa la Plantilla a un dict compatible con pdf_generator.

    Post-procesa:
      - Tablas con datos_ejecutados → inyecta ``_datos_precalculados`` en el dict.
      - Gráficos: contenido.src ya lleva el data URI; draw_graph() lo detecta.
    """
    data = plantilla.model_dump(mode="python", exclude_none=False)

    for pagina in data.get("paginas", {}).values():
        for elem_dict in pagina.get("elementos", {}).values():
            if elem_dict.get("tipo") != "tabla":
                continue
            cfg = elem_dict.get("configuracion") or {}
            # datos_ejecutados tiene exclude=True → no aparece en model_dump
            # Lo recuperamos directamente desde el modelo
            pass

    # Recuperar datos_ejecutados desde los objetos Pydantic originales
    for pid, pagina_model in plantilla.paginas.items():
        for eid, elem_model in pagina_model.elementos.items():
            if elem_model.tipo != TipoElemento.TABLA:
                continue
            if not (elem_model.configuracion and elem_model.configuracion.datos_ejecutados):
                continue
            # Inyectar en el dict serializado
            elem_dict = data["paginas"][pid]["elementos"][eid]
            elem_dict["_datos_precalculados"] = elem_model.configuracion.datos_ejecutados

    return data


def generate_report_pdf_from_state(
    editor_state: Dict[str, Any],
    context: Dict[str, Any],
    output_path: Path,
) -> bool:
    """
    Genera un PDF directamente desde el estado del editor React,
    sin necesidad de que la plantilla esté guardada en disco.

    Útil para previsualizar la maquetación durante la edición.
    """
    import copy
    from info.legacy.template_service_editor_funcs import _convertir_anchos_pct_a_cm
    from utils.asset_manager import get_asset_data_uri
    from utils.pdf_generator import generate_pdf_from_template

    data = copy.deepcopy(editor_state)

    # Eliminar campos de runtime
    for campo in ("chartScripts", "tableScripts", "action", "scriptMetadata"):
        data.pop(campo, None)

    # Convertir anchos de columna % (editor) → cm (modelo)
    _convertir_anchos_pct_a_cm(data)

    # Validar con Pydantic (normaliza estilos, geometría, etc.)
    plantilla = Plantilla.model_validate(data)

    # Resolver imágenes desde el estado del editor:
    # datos_temp y contenido.src ya llevan data URIs; asset_id se resuelve desde el almacén.
    for pagina in plantilla.paginas.values():
        for elem in pagina.elementos.values():
            if elem.tipo != TipoElemento.IMAGEN or not elem.imagen:
                continue
            src_ok = elem.contenido.src and elem.contenido.src.startswith("data:")
            if not src_ok and elem.imagen.datos_temp:
                elem.contenido.src = elem.imagen.datos_temp
            if not src_ok and elem.imagen.asset_id:
                uri = get_asset_data_uri(elem.imagen.asset_id)
                if uri:
                    elem.contenido.src = uri

    resolved = resolve_template(plantilla, context)
    template_dict = _plantilla_to_pdf_dict(resolved)

    buf = BytesIO()
    generate_pdf_from_template(
        template_dict,
        context,
        output_buffer=buf,
        biblioteca_path=PLANTILLAS_DIR,
        biblioteca_graficos_path=GRAFICOS_DIR,
        biblioteca_tablas_path=TABLAS_DIR,
    )

    output_path.write_bytes(buf.getvalue())
    log.info("Maquetación PDF generada: %s (%d bytes)", output_path, len(buf.getvalue()))
    return True


def generate_report_pdf(
    nombre_plantilla: str,
    context: Dict[str, Any],
    output_path: Path,
) -> bool:
    """
    Genera un informe PDF completo para la plantilla indicada.

    Flujo:
      1. Carga la plantilla desde disco (Plantilla Pydantic, unidades en cm).
      2. Resuelve tokens y pre-computa contenido dinámico (resolve_template).
      3. Serializa a dict para pdf_generator (_plantilla_to_pdf_dict).
      4. Llama a generate_pdf_from_template() y escribe el resultado.

    Args:
        nombre_plantilla: Nombre de la plantilla (carpeta en biblioteca_plantillas/).
        context:          Dict con datos de contexto (info, fecha_seleccionada, etc.).
        output_path:      Ruta donde escribir el PDF generado.

    Returns:
        True si la generación fue exitosa.

    Raises:
        PlantillaNoEncontrada: Si la plantilla no existe en disco.
        PlantillaInvalida:     Si el JSON es inválido.
        Exception:             Cualquier error durante la generación del PDF.
    """
    from utils.pdf_generator import generate_pdf_from_template  # importación local para evitar ciclos

    # 1. Cargar
    plantilla = cargar_plantilla(nombre_plantilla)

    # 2. Resolver y pre-computar
    resolved = resolve_template(plantilla, context)

    # 3. Serializar
    template_dict = _plantilla_to_pdf_dict(resolved)

    # 4. Generar PDF
    buf = BytesIO()
    generate_pdf_from_template(
        template_dict,
        context,
        output_buffer=buf,
        biblioteca_path=PLANTILLAS_DIR / nombre_plantilla,
        biblioteca_graficos_path=GRAFICOS_DIR,
        biblioteca_tablas_path=TABLAS_DIR,
    )

    output_path.write_bytes(buf.getvalue())
    log.info("Informe PDF generado: %s (%d bytes)", output_path, len(buf.getvalue()))
    return True

"""Enrutador de motores de generación de informes.

Lee el campo ``engine`` de la plantilla JSON (por defecto ``"html"``)
e instancia el motor correcto para ejecutar el render.

Para añadir un motor nuevo:
1. Crea ``engines/mi_motor.py`` con una clase que herede de ``BaseReportEngine``.
2. Implementa el método ``render()`` y opcionalmente los demás métodos de la base.
3. Registra el motor en ``_ENGINES`` de este módulo.

API pública (compatible con importaciones existentes en el proyecto):
    generate_report_pdf(nombre_plantilla, context, output_path)
    generate_report_pdf_from_state(editor_state, context, output_path)
    render_preview_png(nombre_plantilla, context, width_px=800)
    render_preview_graficos(nombre_plantilla, context)
"""

import importlib
import logging

from utils.template_service import cargar_plantilla

logger = logging.getLogger(__name__)

# ── Registro de motores ────────────────────────────────────────────────────────
# Formato: {nombre_clave: "módulo.ClassName"}
# El nombre_clave coincide con el valor del campo ``engine`` en la plantilla JSON.
_ENGINES: dict[str, str] = {
    "html":      "engines.html_engine.HTMLEngine",
}

_DEFAULT_ENGINE = "html"


# ── Factory ───────────────────────────────────────────────────────────────────

def _get_engine(nombre_plantilla: str | None = None, server=None):
    """Instancia el motor correcto según el campo ``engine`` de la plantilla.

    Pasos:
    1. Si se pasa ``nombre_plantilla``, carga la plantilla y lee ``template["engine"]``.
    2. Si el campo no existe o la plantilla no se puede cargar, usa ``"html"``.
    3. Instancia la clase registrada en ``_ENGINES`` pasando el ORM ``Server``.

    Args:
        nombre_plantilla: Nombre de carpeta de plantilla en ``biblioteca_plantillas/``.
                          ``None`` para usar el motor por defecto.
        server:           Instancia ORM ``Server`` (opcional). Se pasa al motor para
                          que lo use en elementos que requieren acceso directo a la BD
                          del servidor (p.ej. el elemento ``mapa``).

    Returns:
        Instancia del motor correcto.
    """
    engine_name = _DEFAULT_ENGINE
    if nombre_plantilla:
        try:
            template = cargar_plantilla(nombre_plantilla)
            engine_name = template.get("engine", _DEFAULT_ENGINE)
        except Exception:
            pass

    if engine_name not in _ENGINES:
        logger.warning(
            "Motor '%s' no registrado en _ENGINES; usando '%s' por defecto.",
            engine_name,
            _DEFAULT_ENGINE,
        )
        engine_name = _DEFAULT_ENGINE

    module_path, cls_name = _ENGINES[engine_name].rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, cls_name)
    return cls(server=server)


# ── API pública ────────────────────────────────────────────────────────────────

def generate_report_pdf(
    nombre_plantilla: str,
    context: dict,
    output_path: str,
    server=None,
) -> list:
    """Genera el PDF completo a partir de la plantilla y el contexto de ejecución.

    Delega al motor declarado en ``template["engine"]`` (por defecto ``html``).

    Args:
        nombre_plantilla: Carpeta dentro de ``biblioteca_plantillas/``.
        context:          Diccionario de ejecución (zona, fechas, sensor, data…).
        output_path:      Ruta donde guardar el archivo generado.
        server:           Instancia ORM ``Server`` opcional. Requerido para elementos
                          que acceden directamente a la BD del servidor (p.ej. ``mapa``).

    Returns:
        Lista de hitos de ejecución.
    """
    return _get_engine(nombre_plantilla, server=server).render(
        context, nombre_plantilla, output_path
    )


def generate_report_pdf_from_state(
    editor_state: dict,
    context: dict,
    output_path: str,
) -> list:
    """Genera un informe efímero directamente desde el estado en memoria del editor.

    A diferencia de ``generate_report_pdf``, no necesita que la plantilla esté
    guardada en ``biblioteca_plantillas/``. El motor se selecciona leyendo
    ``editor_state["configuracion"]["engine"]`` (por defecto ``"html"``).

    Args:
        editor_state: Estado del editor (prop ``value`` / ``data`` del componente).
        context:      Diccionario de ejecución.
        output_path:  Ruta de salida (``str`` o ``Path``).

    Returns:
        Lista de hitos de ejecución.
    """
    engine_name = (editor_state.get("configuracion") or {}).get("engine", _DEFAULT_ENGINE)
    if engine_name not in _ENGINES:
        engine_name = _DEFAULT_ENGINE
    module_path, cls_name = _ENGINES[engine_name].rsplit(".", 1)
    module = importlib.import_module(module_path)
    engine = getattr(module, cls_name)()
    return engine.render_from_state(context, editor_state, output_path)


def generate_preview_html_from_state(
    editor_state: dict,
    context: dict,
) -> str | None:
    """Genera el HTML crudo desde el estado del editor sin ejecutar Playwright.

    Solo aplica cuando el motor de la plantilla es ``"html"``.

    Args:
        editor_state: Estado del editor.
        context:      Contexto de ejecución.

    Returns:
        Cadena HTML o ``None`` si el motor no es ``"html"``.
    """
    engine_name = (editor_state.get("configuracion") or {}).get("engine", _DEFAULT_ENGINE)
    if engine_name != "html":
        return None
    module_path, cls_name = _ENGINES["html"].rsplit(".", 1)
    module = importlib.import_module(module_path)
    engine = getattr(module, cls_name)()
    return engine.render_preview_html_from_state(editor_state, context)


def render_preview_png(
    nombre_plantilla: str,
    context: dict,
    width_px: int = 800,
) -> bytes:
    """Genera una vista previa PNG de la primera página del informe.

    Args:
        nombre_plantilla: Nombre de la carpeta de plantilla.
        context:          Contexto de ejecución.
        width_px:         Ancho aproximado de la imagen resultante en píxeles.

    Returns:
        Bytes del PNG generado.
    """
    return _get_engine(nombre_plantilla).render_preview_png(
        context, nombre_plantilla, width_px
    )


def render_preview_graficos(
    nombre_plantilla: str,
    context: dict,
) -> list[dict]:
    """Genera previsualizaciones de todos los elementos ``grafico`` de la plantilla.

    Args:
        nombre_plantilla: Nombre de la carpeta de plantilla.
        context:          Contexto de ejecución.

    Returns:
        Lista de dicts con claves ``index``, ``element_id``, ``script``,
        ``result`` (data URL o ``None``) y ``error`` (mensaje o ``None``).
    """
    return _get_engine(nombre_plantilla).render_preview_graficos(context, nombre_plantilla)

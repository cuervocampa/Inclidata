"""
utils/template_service.py
==========================
Servicio de gestión de plantillas — backend puro, sin dependencias de Dash.

Centraliza la lógica de carga, guardado, conversión y fusión de plantillas
que antes estaba dispersa en pages/editor_visual.py. Usa los modelos Pydantic
de models/template_models.py para garantizar la integridad de los datos.

API pública
-----------
Listado:
  listar_plantillas_disponibles()      -> list[dict]
  listar_scripts_graficos()            -> list[str]          (nombres .py)
  listar_scripts_tablas()              -> list[str]          (nombres .py)
  listar_metadata_graficos()           -> dict[str, dict]    (metadatos por nombre)
  listar_metadata_tablas()             -> dict[str, dict]    (metadatos por nombre)

Carga:
  cargar_plantilla(nombre)             -> Plantilla
  cargar_plantilla_para_editor(nombre) -> dict    ← listo para el componente React

Guardado:
  guardar_plantilla(datos, nombre=None) -> bool

Grupos:
  fusionar_grupo_en_plantilla(datos_grupo, editor_state) -> tuple[dict, int]

Excepciones propias:
  PlantillaNoEncontrada  (FileNotFoundError)
  PlantillaInvalida      (ValueError)

Convenciones de unidades
------------------------
  Disco       → anchos de columna en cm.
  Editor React → anchos de columna en %.

  cargar_plantilla*  convierte  cm  → %  antes de devolver.
  guardar_plantilla  convierte  %   → cm  antes de escribir.
"""

from __future__ import annotations

import base64
import copy
import json
import logging
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any

from models.template_models import (
    Elemento,
    Plantilla,
    TipoElemento,
)
from utils.asset_manager import (
    get_asset_data_uri,
    get_asset_path,
    register_asset,
    track_usage,
)
from utils.script_registry import (
    ScriptMetadata,
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

    Una plantilla es válida si existe la carpeta Y el archivo JSON
    con el mismo nombre dentro de ella.

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

    Usa el ScriptRegistry: importa dinámicamente los scripts para activar
    sus decoradores @register_script y genera metadatos mínimos para los
    que no tienen decorador.

    Returns:
        Lista de nombres de archivo ``"{nombre}.py"`` ordenada alfabéticamente.
    """
    _ensure_registry()
    return sorted(f"{nombre}.py" for nombre in get_graficos_metadata())


def listar_scripts_tablas() -> list[str]:
    """
    Lista los scripts de tablas disponibles.

    Usa el ScriptRegistry: importa dinámicamente los scripts para activar
    sus decoradores @register_script y genera metadatos mínimos para los
    que no tienen decorador.

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
# Helpers privados — resolución de imágenes
# ---------------------------------------------------------------------------

def _inyectar_imagenes(plantilla: Plantilla) -> None:
    """
    Inyecta data URIs desde el almacén centralizado en los elementos de imagen.

    Para cada elemento de tipo 'imagen' con ``asset_id``:
      - Resuelve el data URI vía ``get_asset_data_uri()``.
      - Lo escribe en ``imagen.datos_temp`` (leído por React antes que ``contenido.src``).
      - Lo escribe también en ``contenido.src`` para compatibilidad.

    Opera en-place sobre el objeto ``Plantilla``.
    """
    for pagina in plantilla.paginas.values():
        for elem in pagina.elementos.values():
            if elem.tipo != TipoElemento.IMAGEN or not elem.imagen:
                continue

            aid = elem.imagen.asset_id
            if not aid:
                continue

            uri = get_asset_data_uri(aid)
            if uri:
                elem.imagen.datos_temp = uri
                elem.contenido.src = uri
            else:
                log.warning(
                    "asset_id '%s' no encontrado en el almacén centralizado.", aid
                )


# ---------------------------------------------------------------------------
# Helpers privados — persistencia de assets
# ---------------------------------------------------------------------------

def _extraer_assets_a_carpeta(data: dict, carpeta_destino: Path) -> None:
    """
    Extrae imágenes embebidas (base64) del dict de plantilla a
    ``{carpeta_destino}/assets/``.

    Prioridad por elemento:
      1. ``contenido.src``  con data URI → decodificar y guardar.
      2. ``imagen.asset_id`` presente    → copiar desde el almacén centralizado.
      3. ``imagen.datos_temp`` data URI  → decodificar y guardar.

    Actualiza ``imagen.ruta_nueva`` y ``imagen.nombre_archivo`` si guarda algo.

    Funciona tanto con estructura de plantilla (``paginas.*.elementos``)
    como de grupo (``elementos``).
    """
    assets_dir = carpeta_destino / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    imagen_elems: list[dict] = []
    if "paginas" in data:
        for page in data.get("paginas", {}).values():
            for elem in page.get("elementos", {}).values():
                if elem.get("tipo") == "imagen":
                    imagen_elems.append(elem)
    else:
        for elem in data.get("elementos", {}).values():
            if elem.get("tipo") == "imagen":
                imagen_elems.append(elem)

    for elem in imagen_elems:
        img = elem.get("imagen") or {}
        contenido = elem.get("contenido") or {}
        src = contenido.get("src") or ""
        nombre_archivo = img.get("nombre_archivo") or f"{elem.get('id', 'img')}.png"
        guardado = False

        # 1. contenido.src con data URI
        if src.startswith("data:"):
            try:
                _, encoded = src.split(",", 1)
                dest = assets_dir / nombre_archivo
                dest.write_bytes(base64.b64decode(encoded))
                guardado = True
            except Exception:
                log.exception("Error guardando asset desde contenido.src (%s).", nombre_archivo)

        # 2. asset_id → copiar desde almacén centralizado
        if not guardado and img.get("asset_id"):
            asset_path = get_asset_path(img["asset_id"])
            if asset_path and asset_path.exists():
                shutil.copy2(asset_path, assets_dir / nombre_archivo)
                guardado = True

        # 3. datos_temp con data URI
        if not guardado:
            datos_temp = img.get("datos_temp") or ""
            if datos_temp.startswith("data:"):
                try:
                    _, encoded = datos_temp.split(",", 1)
                    dest = assets_dir / nombre_archivo
                    dest.write_bytes(base64.b64decode(encoded))
                    guardado = True
                except Exception:
                    log.exception(
                        "Error guardando asset desde datos_temp (%s).", nombre_archivo
                    )

        if guardado:
            img["ruta_nueva"] = f"assets/{nombre_archivo}"
            img["nombre_archivo"] = nombre_archivo
            elem["imagen"] = img


def _registrar_y_limpiar_assets(data: dict, nombre_plantilla: str) -> None:
    """
    Recorre todos los elementos de imagen del dict:

    - Si ``contenido.src`` es un data URI:
        → registra en el almacén centralizado.
        → asigna ``imagen.asset_id``.
        → limpia ``contenido.src = None`` y elimina ``imagen.datos_temp``.
    - Si ya tiene ``asset_id``:
        → solo registra el uso (track_usage).

    Opera en-place sobre el dict.
    """
    for page in data.get("paginas", {}).values():
        for elem_id, elem in page.get("elementos", {}).items():
            if elem.get("tipo") != "imagen":
                continue

            contenido = elem.setdefault("contenido", {})
            img = elem.setdefault("imagen", {})
            src = contenido.get("src") or ""

            if src.startswith("data:"):
                nombre_archivo = img.get("nombre_archivo") or f"{elem_id}.png"
                try:
                    asset_id = register_asset(src, nombre_archivo)
                    track_usage(asset_id, nombre_plantilla)
                    img["asset_id"] = asset_id
                    contenido["src"] = None
                    img.pop("datos_temp", None)
                    log.debug("Asset registrado: %s → %s", nombre_archivo, asset_id)
                except Exception:
                    log.exception(
                        "Error registrando asset '%s' al guardar plantilla '%s'.",
                        nombre_archivo, nombre_plantilla,
                    )
            elif img.get("asset_id"):
                track_usage(img["asset_id"], nombre_plantilla)


def _convertir_anchos_pct_a_cm(data: dict) -> None:
    """
    Convierte los anchos de columna de cuadrícula de % (editor) a cm (disco).

    Equivale a ``Plantilla.convertir_anchos_a_cm()`` pero opera directamente
    sobre el dict raw del editor, evitando round-trips por el modelo Pydantic.
    """
    for page in data.get("paginas", {}).values():
        for elem in page.get("elementos", {}).values():
            if elem.get("tipo") != "tabla":
                continue
            cuadricula = elem.get("cuadricula")
            if not cuadricula:
                continue
            ancho_total_cm = elem.get("geometria", {}).get("ancho", 10)
            for nivel in cuadricula.get("niveles", []):
                columnas = nivel.get("columnas", [])
                for col in columnas:
                    pct = col.get("ancho", 0)
                    col["ancho"] = round((pct / 100.0) * ancho_total_cm, 2)


# ---------------------------------------------------------------------------
# Carga de plantillas
# ---------------------------------------------------------------------------

def cargar_plantilla(nombre: str) -> Plantilla:
    """
    Carga una plantilla desde disco y la devuelve como objeto ``Plantilla``.

    Pasos:
      1. Lee ``biblioteca_plantillas/{nombre}/{nombre}.json``.
      2. Valida y normaliza con ``Plantilla.model_validate()``:
           - Estructura plana (sin ``paginas``) → estructura paginada.
           - Estilos antiguos (color_relleno, opacidad 0-100…) → nuevos nombres.
           - Geometría de tablas (ancho_maximo/alto_maximo → ancho/alto).
      3. Inyecta data URIs de imágenes desde el almacén de assets.
      4. Convierte anchos de columna de cm → % para el editor React.

    Args:
        nombre: Nombre de la plantilla (= nombre de la carpeta y del archivo JSON).

    Returns:
        Objeto ``Plantilla`` listo para usar o para serializar al editor.

    Raises:
        PlantillaNoEncontrada: Si el archivo JSON no existe.
        PlantillaInvalida:     Si el JSON no tiene la estructura esperada.
    """
    ruta_json = PLANTILLAS_DIR / nombre / f"{nombre}.json"
    if not ruta_json.exists():
        raise PlantillaNoEncontrada(
            f"Plantilla '{nombre}' no encontrada en {ruta_json}"
        )

    try:
        with open(ruta_json, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise PlantillaInvalida(
            f"JSON inválido en plantilla '{nombre}': {exc}"
        ) from exc

    # Garantizar configuración mínima antes de model_validate
    if "configuracion" not in data or "nombre_plantilla" not in data.get("configuracion", {}):
        data.setdefault("configuracion", {})
        data["configuracion"].setdefault("nombre_plantilla", nombre)
        data["configuracion"].setdefault(
            "num_paginas", len(data.get("paginas", {})) or 1
        )

    try:
        plantilla = Plantilla.model_validate(data)
    except Exception as exc:
        raise PlantillaInvalida(
            f"Error validando plantilla '{nombre}': {exc}"
        ) from exc

    # Inyectar data URIs para que el editor React pueda mostrar las imágenes.
    # Los anchos de columna se mantienen en cm en el modelo (formato disco);
    # la conversión a % ocurre en to_editor_dict() para evitar doble conversión.
    _inyectar_imagenes(plantilla)

    log.info(
        "Plantilla '%s' cargada: %d página(s).",
        nombre, len(plantilla.paginas),
    )
    return plantilla


def cargar_plantilla_para_editor(nombre: str) -> dict:
    """
    Carga una plantilla y devuelve el dict listo para el componente React.

    Equivale a ``cargar_plantilla(nombre).to_editor_dict()`` más la inyección
    de ``chartScripts`` y ``tableScripts`` disponibles en el sistema.

    Args:
        nombre: Nombre de la plantilla.

    Returns:
        Dict serializable a JSON con la estructura que espera ``dce.Editor``.

    Raises:
        PlantillaNoEncontrada, PlantillaInvalida: igual que ``cargar_plantilla``.
    """
    plantilla = cargar_plantilla(nombre)
    payload = plantilla.to_editor_dict()
    payload["chartScripts"] = listar_scripts_graficos()
    payload["tableScripts"] = listar_scripts_tablas()
    payload["scriptMetadata"] = {
        **listar_metadata_graficos(),
        **listar_metadata_tablas(),
    }
    return payload


# ---------------------------------------------------------------------------
# Guardado de plantillas
# ---------------------------------------------------------------------------

def guardar_plantilla(datos: dict, nombre: str | None = None) -> bool:
    """
    Guarda una plantilla en disco a partir del dict del editor React.

    Pasos:
      1. Copia profunda del dict (no muta el argumento).
      2. Elimina campos de runtime: ``chartScripts``, ``tableScripts``, ``action``.
      3. Determina y asigna el nombre en ``configuracion.nombre_plantilla``.
      4. Extrae imágenes embebidas (base64) a ``{plantilla}/assets/``.
      5. Convierte anchos de columna % → cm.
      6. Registra las imágenes en el almacén centralizado y limpia los base64.
      7. Escribe el JSON de forma atómica (write tmp → rename).

    Args:
        datos:  Dict con el estado del editor (``visual-editor.value``).
        nombre: Nombre bajo el que guardar. Si es ``None``, se usa
                ``datos["configuracion"]["nombre_plantilla"]``.

    Returns:
        ``True`` si el guardado fue exitoso.

    Raises:
        PlantillaInvalida: Si no se puede determinar el nombre o la estructura
                           es irrecuperable.
        OSError:           Si falla la escritura en disco.
    """
    data = copy.deepcopy(datos)

    # Eliminar campos de runtime que no deben persistir en disco
    for campo in ("chartScripts", "tableScripts", "action"):
        data.pop(campo, None)

    # Determinar nombre
    nombre = nombre or data.get("configuracion", {}).get("nombre_plantilla", "")
    if not nombre:
        raise PlantillaInvalida(
            "No se puede guardar la plantilla: falta el nombre. "
            "Proporciona el argumento 'nombre' o asegúrate de que "
            "'configuracion.nombre_plantilla' está definido."
        )

    # Asignar nombre definitivo en la configuración
    data.setdefault("configuracion", {})["nombre_plantilla"] = nombre

    dest_dir = PLANTILLAS_DIR / nombre
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Paso 1: extraer imágenes a {plantilla}/assets/
    _extraer_assets_a_carpeta(data, dest_dir)

    # Paso 2: convertir anchos de columna % → cm
    _convertir_anchos_pct_a_cm(data)

    # Paso 3: registrar en almacén centralizado y limpiar base64
    _registrar_y_limpiar_assets(data, nombre)

    # Paso 4: escritura atómica (tmp → rename evita archivos parciales)
    json_path = dest_dir / f"{nombre}.json"
    tmp_path = json_path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp_path.replace(json_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    log.info("Plantilla '%s' guardada en %s.", nombre, json_path)
    return True


# ---------------------------------------------------------------------------
# Fusión de grupos en el estado del editor
# ---------------------------------------------------------------------------

def fusionar_grupo_en_plantilla(
    datos_grupo: dict,
    editor_state: dict | None,
) -> tuple[dict, int]:
    """
    Fusiona los elementos de un grupo en la página activa del editor.

    Aplica el mismo mapeo de estilos que ``cargar_plantilla`` (vía
    ``Elemento.model_validate``) y añade un sufijo UUID corto a cada ID
    para evitar colisiones con elementos ya presentes.

    Args:
        datos_grupo:  Dict del grupo con clave ``"elementos": {id: elem, ...}``.
        editor_state: Estado actual del editor (``visual-editor.value``).
                      Si es ``None`` o vacío, se crea una plantilla vacía.

    Returns:
        Tupla ``(editor_state_actualizado, num_elementos_fusionados)``.

    Raises:
        PlantillaInvalida: Si ``datos_grupo`` no contiene la clave ``"elementos"``.
    """
    if "elementos" not in datos_grupo:
        raise PlantillaInvalida(
            "El diccionario de grupo no contiene la clave 'elementos'."
        )

    # Estado vacío por defecto
    if not editor_state:
        editor_state = {
            "paginas": {
                "1": {
                    "elementos": {},
                    "configuracion": {"orientacion": "portrait"},
                }
            },
            "pagina_actual": "1",
            "configuracion": {
                "nombre_plantilla": "Nueva Plantilla Visual",
                "num_paginas": 1,
            },
        }

    pagina_actual = editor_state.get("pagina_actual", "1")

    # Garantizar que la página actual existe
    editor_state.setdefault("paginas", {})\
                .setdefault(pagina_actual, {
                    "elementos": {},
                    "configuracion": {"orientacion": "portrait"},
                })
    editor_state["paginas"][pagina_actual].setdefault("elementos", {})

    elems_actuales: dict = editor_state["paginas"][pagina_actual]["elementos"]
    sufijo = str(uuid.uuid4())[:4]
    count = 0

    for id_orig, props in datos_grupo["elementos"].items():
        nuevo_id = f"{id_orig}_{sufijo}"
        # model_validate aplica toda la normalización de estilos y geometría
        try:
            elem_model = Elemento.model_validate({**props, "id": nuevo_id})
        except Exception:
            log.exception(
                "Error validando elemento '%s' del grupo al fusionar; se omite.",
                id_orig,
            )
            continue

        # Resolver imagen si tiene asset_id
        if elem_model.tipo == TipoElemento.IMAGEN and elem_model.imagen:
            aid = elem_model.imagen.asset_id
            if aid:
                uri = get_asset_data_uri(aid)
                if uri:
                    elem_model.imagen.datos_temp = uri
                    elem_model.contenido.src = uri

        # Serializar a dict para el editor (columnas en %, si aplica)
        elems_actuales[nuevo_id] = elem_model.to_editor_dict()
        count += 1

    editor_state["paginas"][pagina_actual]["elementos"] = elems_actuales
    log.info(
        "Fusionados %d elementos del grupo en página '%s'.", count, pagina_actual
    )
    return editor_state, count


# ---------------------------------------------------------------------------
# Importar grupo desde archivo (JSON o ZIP)
# ---------------------------------------------------------------------------

def importar_grupo_desde_bytes(
    contenido_bytes: bytes,
    filename: str,
) -> dict:
    """
    Decodifica un archivo de grupo (.json o .zip) y devuelve su dict.

    Para archivos ZIP:
      - Extrae el primer ``.json`` encontrado.
      - Registra los assets encontrados en ``assets/`` en el almacén
        centralizado e inyecta ``asset_id`` y ``datos_temp`` en los
        elementos que los referencien por nombre de archivo.

    Args:
        contenido_bytes: Bytes del archivo (raw, no base64).
        filename:        Nombre del archivo subido.

    Returns:
        Dict con la estructura de grupo: ``{"elementos": {...}, ...}``.

    Raises:
        PlantillaInvalida: Si el ZIP no contiene JSON o el JSON es inválido.
    """
    if filename.lower().endswith(".zip"):
        datos_grupo = _extraer_grupo_de_zip(contenido_bytes)
    else:
        try:
            datos_grupo = json.loads(contenido_bytes.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise PlantillaInvalida(
                f"El archivo '{filename}' no es un JSON válido: {exc}"
            ) from exc

    if "elementos" not in datos_grupo:
        raise PlantillaInvalida(
            f"El archivo '{filename}' no contiene la clave 'elementos'."
        )

    return datos_grupo


def _extraer_grupo_de_zip(zip_bytes: bytes) -> dict:
    """
    Extrae un grupo desde un ZIP: lee el JSON principal y registra los assets.

    Returns:
        Dict del grupo con ``asset_id`` y ``datos_temp`` inyectados en los
        elementos de imagen que correspondan.

    Raises:
        PlantillaInvalida: Si el ZIP no contiene ningún archivo .json.
    """
    with zipfile.ZipFile(__import__("io").BytesIO(zip_bytes), "r") as zf:
        json_files = [n for n in zf.namelist() if n.endswith(".json")]
        if not json_files:
            raise PlantillaInvalida("El ZIP no contiene ningún archivo .json.")

        try:
            datos_grupo: dict = json.loads(zf.read(json_files[0]).decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise PlantillaInvalida(f"JSON inválido dentro del ZIP: {exc}") from exc

        # Registrar assets del ZIP en el almacén centralizado
        asset_files = [
            n for n in zf.namelist()
            if "/assets/" in n and not n.endswith("/")
        ]
        for asset_name in asset_files:
            asset_basename = Path(asset_name).name
            asset_bytes = zf.read(asset_name)
            data_uri = (
                "data:application/octet-stream;base64,"
                + base64.b64encode(asset_bytes).decode()
            )
            try:
                asset_id = register_asset(data_uri, asset_basename)
            except Exception:
                log.exception("Error registrando asset '%s' del ZIP.", asset_basename)
                continue

            # Inyectar asset_id y datos_temp en elementos que usen este archivo
            for elem in datos_grupo.get("elementos", {}).values():
                img = elem.get("imagen") or {}
                if img.get("nombre_archivo") == asset_basename:
                    img["asset_id"] = asset_id
                    img["datos_temp"] = data_uri
                    elem["imagen"] = img

    return datos_grupo

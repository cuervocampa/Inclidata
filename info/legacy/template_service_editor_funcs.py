"""
info/legacy/template_service_editor_funcs.py
=============================================
Funciones del editor visual archivadas desde utils/template_service.py.
El editor (pages/editor_visual.py + dce.Editor React) fue eliminado de IncliData
en la migración al motor HTML (v2.0). Las plantillas se crean en Maketator.

Archivado en: 2026-07-03 (consolidación motor HTML, tag v2.0-motor-html)
Recuperable en: tag v1.0-pre-poda-reportlab o rama archive/full-editor-reportlab

Funciones archivadas:
  - _inyectar_imagenes(plantilla)
  - _extraer_assets_a_carpeta(data, carpeta_destino)
  - _registrar_y_limpiar_assets(data, nombre_plantilla)
  - _convertir_anchos_pct_a_cm(data)
  - cargar_plantilla_para_editor(nombre) -> dict
  - guardar_plantilla(datos, nombre=None) -> bool
  - fusionar_grupo_en_plantilla(datos_grupo, editor_state) -> tuple[dict, int]
  - importar_grupo_desde_bytes(contenido_bytes, filename) -> dict
  - _extraer_grupo_de_zip(zip_bytes) -> dict
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

from info.legacy.template_models import (
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
from utils.template_service import (
    PlantillaNoEncontrada,
    PlantillaInvalida,
    PLANTILLAS_DIR,
    cargar_plantilla,
    listar_scripts_graficos,
    listar_scripts_tablas,
    listar_metadata_graficos,
    listar_metadata_tablas,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers privados — resolución de imágenes
# ---------------------------------------------------------------------------

def _inyectar_imagenes(plantilla: Plantilla) -> None:
    """
    Inyecta data URIs desde el almacén centralizado en los elementos de imagen.
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

        if src.startswith("data:"):
            try:
                _, encoded = src.split(",", 1)
                dest = assets_dir / nombre_archivo
                dest.write_bytes(base64.b64decode(encoded))
                guardado = True
            except Exception:
                log.exception("Error guardando asset desde contenido.src (%s).", nombre_archivo)

        if not guardado and img.get("asset_id"):
            asset_path = get_asset_path(img["asset_id"])
            if asset_path and asset_path.exists():
                shutil.copy2(asset_path, assets_dir / nombre_archivo)
                guardado = True

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
    Registra imágenes en el almacén centralizado y limpia los base64 del dict.
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
# Carga para el editor React
# ---------------------------------------------------------------------------

def cargar_plantilla_para_editor(nombre: str) -> dict:
    """
    Carga una plantilla y devuelve el dict listo para el componente React dce.Editor.
    MUERTA desde fase 3: esperaba el retorno Pydantic antiguo.
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
    MUERTA desde la eliminación del editor visual.
    """
    data = copy.deepcopy(datos)

    for campo in ("chartScripts", "tableScripts", "action"):
        data.pop(campo, None)

    nombre = nombre or data.get("configuracion", {}).get("nombre_plantilla", "")
    if not nombre:
        raise PlantillaInvalida(
            "No se puede guardar la plantilla: falta el nombre."
        )

    data.setdefault("configuracion", {})["nombre_plantilla"] = nombre

    dest_dir = PLANTILLAS_DIR / nombre
    dest_dir.mkdir(parents=True, exist_ok=True)

    _extraer_assets_a_carpeta(data, dest_dir)
    _convertir_anchos_pct_a_cm(data)
    _registrar_y_limpiar_assets(data, nombre)

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
    MUERTA desde la eliminación del editor visual.
    """
    if "elementos" not in datos_grupo:
        raise PlantillaInvalida(
            "El diccionario de grupo no contiene la clave 'elementos'."
        )

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
        try:
            elem_model = Elemento.model_validate({**props, "id": nuevo_id})
        except Exception:
            log.exception(
                "Error validando elemento '%s' del grupo al fusionar; se omite.",
                id_orig,
            )
            continue

        if elem_model.tipo == TipoElemento.IMAGEN and elem_model.imagen:
            aid = elem_model.imagen.asset_id
            if aid:
                uri = get_asset_data_uri(aid)
                if uri:
                    elem_model.imagen.datos_temp = uri
                    elem_model.contenido.src = uri

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
    MUERTA desde la eliminación del editor visual.
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
    """
    with zipfile.ZipFile(__import__("io").BytesIO(zip_bytes), "r") as zf:
        json_files = [n for n in zf.namelist() if n.endswith(".json")]
        if not json_files:
            raise PlantillaInvalida("El ZIP no contiene ningún archivo .json.")

        try:
            datos_grupo: dict = json.loads(zf.read(json_files[0]).decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise PlantillaInvalida(f"JSON inválido dentro del ZIP: {exc}") from exc

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

            for elem in datos_grupo.get("elementos", {}).values():
                img = elem.get("imagen") or {}
                if img.get("nombre_archivo") == asset_basename:
                    img["asset_id"] = asset_id
                    img["datos_temp"] = data_uri
                    elem["imagen"] = img

    return datos_grupo

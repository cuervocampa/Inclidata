"""
Almacén centralizado de assets con deduplicación por hash MD5.

Los archivos se almacenan en biblioteca_plantillas/_assets/{id}.{ext}
donde {id} son los 8 primeros caracteres del hash MD5 del archivo.

Un registry.json mantiene el índice: asset_id → {filename, ext, usages}.
"""

import hashlib
import json
import base64
import mimetypes
import tempfile
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "biblioteca_plantillas" / "_assets"
REGISTRY_PATH = ASSETS_DIR / "registry.json"

# Extensiones de imagen soportadas
_MIME_TO_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/svg+xml": "svg",
    "image/webp": "webp",
    "application/pdf": "pdf",
}

_EXT_TO_MIME = {v: k for k, v in _MIME_TO_EXT.items()}
_EXT_TO_MIME["jpeg"] = "image/jpeg"


# ---------------------------------------------------------------------------
# Registry I/O
# ---------------------------------------------------------------------------

def load_registry() -> dict:
    """Carga el registro de assets. Retorna dict vacío si no existe."""
    if not REGISTRY_PATH.exists():
        return {}
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_registry(registry: dict) -> None:
    """Guarda el registro de forma atómica (write-to-tmp + rename)."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = REGISTRY_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    tmp_path.replace(REGISTRY_PATH)


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def _compute_md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _parse_data_uri(data_uri: str) -> tuple[bytes, str]:
    """Extrae bytes y extensión de un data URI."""
    # data:image/png;base64,iVBOR...
    header, encoded = data_uri.split(",", 1)
    mime = header.split(":")[1].split(";")[0]
    ext = _MIME_TO_EXT.get(mime, "png")
    return base64.b64decode(encoded), ext


def _guess_ext(filename: str) -> str:
    """Infiere extensión a partir de un nombre de archivo."""
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext in ("jpg", "jpeg"):
        return "jpg"
    return ext or "png"


def register_asset(source, original_filename: str = "") -> str:
    """
    Registra un asset en el almacén centralizado.

    Args:
        source: data URI string, bytes, o Path del archivo.
        original_filename: nombre original (para metadata).

    Returns:
        asset_id (8 chars del MD5).
    """
    if isinstance(source, str) and source.startswith("data:"):
        data, ext = _parse_data_uri(source)
    elif isinstance(source, bytes):
        ext = _guess_ext(original_filename)
        data = source
    elif isinstance(source, Path) or (isinstance(source, str) and not source.startswith("data:")):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Asset no encontrado: {path}")
        data = path.read_bytes()
        ext = _guess_ext(path.name)
        if not original_filename:
            original_filename = path.name
    else:
        raise TypeError(f"Tipo de source no soportado: {type(source)}")

    md5_full = _compute_md5(data)
    asset_id = md5_full[:8]

    # Escribir archivo si no existe
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    asset_path = ASSETS_DIR / f"{asset_id}.{ext}"
    if not asset_path.exists():
        asset_path.write_bytes(data)

    # Actualizar registro
    registry = load_registry()
    if asset_id not in registry:
        registry[asset_id] = {
            "filename": original_filename or f"{asset_id}.{ext}",
            "ext": ext,
            "md5": md5_full,
            "usages": [],
        }
    save_registry(registry)

    return asset_id


def get_asset_path(asset_id: str) -> Path | None:
    """Devuelve la ruta al archivo del asset, o None si no existe."""
    registry = load_registry()
    info = registry.get(asset_id)
    if not info:
        return None
    path = ASSETS_DIR / f"{asset_id}.{info['ext']}"
    return path if path.exists() else None


def get_asset_data_uri(asset_id: str) -> str:
    """Devuelve un data URI (data:image/...;base64,...) para el asset."""
    path = get_asset_path(asset_id)
    if not path:
        return ""
    registry = load_registry()
    ext = registry[asset_id]["ext"]
    mime = _EXT_TO_MIME.get(ext, "image/png")
    data_b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{data_b64}"


# ---------------------------------------------------------------------------
# Resolución de imagen (prioridad: asset_id → datos_temp → ruta_nueva)
# ---------------------------------------------------------------------------

def _search_image_file(ruta_nueva: str, template_name: str) -> Path | None:
    """Busca una imagen por ruta_nueva en varias ubicaciones."""
    if not ruta_nueva:
        return None

    nombre_archivo = Path(ruta_nueva).name
    plantillas_dir = BASE_DIR / "biblioteca_plantillas"

    posibles = [
        Path(ruta_nueva),
    ]
    if template_name:
        posibles.append(plantillas_dir / template_name / ruta_nueva)
        posibles.append(plantillas_dir / template_name / "assets" / nombre_archivo)
    posibles.append(BASE_DIR / ruta_nueva)
    posibles.append(BASE_DIR / "assets" / nombre_archivo)

    for p in posibles:
        if p.exists():
            return p
    return None


def resolve_image_element(element: dict, template_name: str) -> str:
    """
    Resuelve la imagen de un elemento para mostrar en HTML (data URI).

    Prioridad: asset_id → datos_temp → ruta_nueva (búsqueda multi-path)
    """
    img = element.get("imagen", {})

    # 1. asset_id
    aid = img.get("asset_id")
    if aid:
        uri = get_asset_data_uri(aid)
        if uri:
            return uri

    # 2. datos_temp
    datos = img.get("datos_temp", "")
    if datos:
        return datos

    # 3. ruta_nueva — leer archivo y convertir a data URI
    ruta_nueva = img.get("ruta_nueva", "")
    path = _search_image_file(ruta_nueva, template_name)
    if path:
        ext = path.suffix.lstrip(".").lower()
        if ext in ("jpg", "jpeg"):
            ext = "jpg"
        mime = _EXT_TO_MIME.get(ext, "image/png")
        data_b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
        return f"data:{mime};base64,{data_b64}"

    return ""


def resolve_image_path(element: dict, template_name: str) -> Path | None:
    """
    Resuelve la imagen de un elemento para PDF (ruta al archivo).

    Prioridad: asset_id → ruta_nueva → datos_temp (crea tempfile, caller limpia).
    """
    img = element.get("imagen", {})

    # 1. asset_id
    aid = img.get("asset_id")
    if aid:
        p = get_asset_path(aid)
        if p:
            return p

    # 2. ruta_nueva
    ruta_nueva = img.get("ruta_nueva", "")
    path = _search_image_file(ruta_nueva, template_name)
    if path:
        return path

    # 3. datos_temp — crear tempfile
    datos = img.get("datos_temp", "")
    if datos:
        try:
            data, ext = _parse_data_uri(datos) if datos.startswith("data:") else (base64.b64decode(datos), img.get("formato", "png"))
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
            tf.write(data)
            tf.close()
            return Path(tf.name)
        except Exception as e:
            print(f"[asset_manager] Error creando tempfile desde datos_temp: {e}")

    return None


# ---------------------------------------------------------------------------
# Tracking de uso
# ---------------------------------------------------------------------------

def track_usage(asset_id: str, template_name: str) -> None:
    """Registra que un asset es usado por una plantilla."""
    registry = load_registry()
    info = registry.get(asset_id)
    if not info:
        return
    usages = info.setdefault("usages", [])
    if template_name and template_name not in usages:
        usages.append(template_name)
        save_registry(registry)


def untrack_usage(asset_id: str, template_name: str) -> None:
    """Elimina el registro de uso de un asset por una plantilla."""
    registry = load_registry()
    info = registry.get(asset_id)
    if not info:
        return
    usages = info.get("usages", [])
    if template_name in usages:
        usages.remove(template_name)
        save_registry(registry)

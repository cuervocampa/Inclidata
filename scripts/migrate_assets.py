#!/usr/bin/env python3
"""
Migración one-shot: mueve imágenes de carpetas assets/ por plantilla/grupo
al almacén centralizado _assets/ con deduplicación por MD5.

Uso:
    python scripts/migrate_assets.py             # ejecutar migración
    python scripts/migrate_assets.py --dry-run   # solo preview, sin cambios

Idempotente: si un elemento ya tiene asset_id, se salta.
"""

import argparse
import json
import sys
from pathlib import Path

# Añadir raíz del proyecto al path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.asset_manager import register_asset, track_usage, load_registry

PLANTILLAS_DIR = ROOT / "biblioteca_plantillas"
GRUPOS_DIR = ROOT / "biblioteca_grupos"


def _process_elementos(elementos: dict, assets_dir: Path, template_name: str,
                       dry_run: bool, stats: dict) -> bool:
    """Procesa elementos de una plantilla/grupo. Retorna True si hubo cambios."""
    changed = False
    for elem_id, elem in elementos.items():
        if elem.get("tipo") != "imagen":
            continue
        img = elem.get("imagen", {})
        if img.get("asset_id"):
            stats["skipped"] += 1
            continue

        # Buscar archivo de imagen
        ruta_nueva = img.get("ruta_nueva", "")
        nombre_archivo = img.get("nombre_archivo", "")
        file_path = None

        if nombre_archivo and assets_dir.exists():
            candidate = assets_dir / nombre_archivo
            if candidate.exists():
                file_path = candidate

        if not file_path and ruta_nueva:
            # Intentar ruta relativa
            for base in [assets_dir.parent, ROOT]:
                candidate = base / ruta_nueva
                if candidate.exists():
                    file_path = candidate
                    break
            if not file_path:
                candidate = assets_dir / Path(ruta_nueva).name
                if candidate.exists():
                    file_path = candidate

        if not file_path:
            print(f"  SKIP {elem_id}: archivo no encontrado "
                  f"(nombre_archivo={nombre_archivo}, ruta_nueva={ruta_nueva})")
            stats["not_found"] += 1
            continue

        if dry_run:
            import hashlib
            md5 = hashlib.md5(file_path.read_bytes()).hexdigest()[:8]
            ext = file_path.suffix.lstrip(".").lower()
            print(f"  [DRY-RUN] {elem_id}: {file_path.name} → asset_id={md5} ({md5}.{ext})")
            stats["would_migrate"] += 1
        else:
            asset_id = register_asset(file_path, original_filename=file_path.name)
            track_usage(asset_id, template_name)
            img["asset_id"] = asset_id
            # Limpiar datos_temp (no debe persistir en disco)
            img.pop("datos_temp", None)
            changed = True
            stats["migrated"] += 1
            print(f"  {elem_id}: {file_path.name} → asset_id={asset_id}")

    return changed


def migrate_directory(base_dir: Path, dry_run: bool, stats: dict):
    """Migra todas las plantillas/grupos en un directorio."""
    if not base_dir.exists():
        return

    for item in sorted(base_dir.iterdir()):
        if not item.is_dir() or item.name.startswith("_"):
            continue
        json_file = item / f"{item.name}.json"
        if not json_file.exists():
            continue

        print(f"\n{'[DRY-RUN] ' if dry_run else ''}Procesando: {item.name}")

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ERROR leyendo JSON: {e}")
            continue

        assets_dir = item / "assets"
        changed = False

        # Estructura con páginas
        if "paginas" in data:
            for page_id, page in data["paginas"].items():
                elems = page.get("elementos", {})
                if _process_elementos(elems, assets_dir, item.name, dry_run, stats):
                    changed = True
        # Estructura plana (grupos o plantillas legacy)
        elif "elementos" in data:
            if _process_elementos(data["elementos"], assets_dir, item.name, dry_run, stats):
                changed = True

        if changed and not dry_run:
            json_string = json.dumps(data, indent=2, ensure_ascii=False)
            with open(json_file, "w", encoding="utf-8") as f:
                f.write(json_string)
            print(f"  JSON actualizado: {json_file.name}")


def main():
    parser = argparse.ArgumentParser(description="Migrar assets a almacén centralizado")
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo mostrar lo que se haría, sin cambios")
    args = parser.parse_args()

    stats = {"migrated": 0, "would_migrate": 0, "skipped": 0, "not_found": 0}

    print("=" * 60)
    print("Migración de assets a almacén centralizado (_assets/)")
    if args.dry_run:
        print("MODO: DRY-RUN (sin cambios)")
    print("=" * 60)

    print(f"\n--- Plantillas ({PLANTILLAS_DIR}) ---")
    migrate_directory(PLANTILLAS_DIR, args.dry_run, stats)

    print(f"\n--- Grupos ({GRUPOS_DIR}) ---")
    migrate_directory(GRUPOS_DIR, args.dry_run, stats)

    print("\n" + "=" * 60)
    print("Resumen:")
    if args.dry_run:
        print(f"  Se migrarían: {stats['would_migrate']}")
    else:
        print(f"  Migrados: {stats['migrated']}")
    print(f"  Saltados (ya tienen asset_id): {stats['skipped']}")
    print(f"  No encontrados: {stats['not_found']}")

    if not args.dry_run:
        registry = load_registry()
        print(f"  Assets únicos en _assets/: {len(registry)}")

    print("=" * 60)


if __name__ == "__main__":
    main()

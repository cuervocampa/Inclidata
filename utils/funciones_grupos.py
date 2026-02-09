import os
import json
import shutil
from pathlib import Path

from utils.asset_manager import register_asset, track_usage

# Ruta base de los grupos usando pathlib para mayor seguridad
BASE_DIR = Path(__file__).resolve().parent.parent
GRUPOS_DIR = BASE_DIR / "biblioteca_grupos"

def listar_grupos_disponibles():
    """
    Retorna una lista de diccionarios [{'label': nombre, 'value': nombre}] 
    de grupos disponibles en la biblioteca.
    """
    print(f"DEBUG: Buscando grupos en: {GRUPOS_DIR}")
    
    if not GRUPOS_DIR.exists():
        print(f"DEBUG: La carpeta {GRUPOS_DIR} no existe. Creándola...")
        try:
            GRUPOS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"DEBUG: Error creando directorio de grupos: {e}")
        return []
    
    grupos = []
    try:
        for elemento in GRUPOS_DIR.iterdir():
            if elemento.is_dir():
                nombre = elemento.name
                json_file = elemento / f"{nombre}.json"
                
                # Validamos que tenga el json descriptor
                if json_file.exists():
                    # print(f"DEBUG: Grupo encontrado: {nombre}")
                    grupos.append({'label': nombre, 'value': nombre})
                else:
                    print(f"DEBUG: Directorio {nombre} ignorado (falta {nombre}.json)")
    except Exception as e:
        print(f"DEBUG: Error listando grupos: {e}")
        
    return grupos

def leer_datos_grupo(nombre_grupo):
    """
    Lee el JSON de definición de un grupo y retorna su contenido (diccionario).
    Devuelve None si hay error.
    """
    ruta_json = GRUPOS_DIR / nombre_grupo / f"{nombre_grupo}.json"
    try:
        with open(ruta_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"Error leyendo datos del grupo {nombre_grupo}: {e}")
        return None

def copiar_assets_grupo(nombre_grupo, ruta_plantilla_destino):
    """
    DEPRECADA: Los assets ahora se gestionan de forma centralizada en _assets/.
    Se mantiene la firma por compatibilidad, pero no realiza ninguna copia.
    """
    print(f"[DEPRECADO] copiar_assets_grupo() llamada para '{nombre_grupo}' — "
          f"los assets se gestionan ahora desde _assets/")

def guardar_nuevo_grupo(nombre_grupo, descripcion, elementos_seleccionados, ruta_assets_origen_app):
    """
    Crea un nuevo grupo con los elementos seleccionados.
    
    Args:
        nombre_grupo (str): Nombre del nuevo grupo (será el nombre de la carpeta).
        descripcion (str): Descripción.
        elementos_seleccionados (dict): Diccionario de elementos {id: datos}.
        ruta_assets_origen_app (Path): Ruta 'assets' desde donde copiar las imágenes si existen.
        
    Returns:
        bool, str: (Éxito, Mensaje)
    """
    try:
        # 1. Crear directorios
        # Sanitizar nombre (básico)
        safe_name = "".join([c for c in nombre_grupo if c.isalnum() or c in (' ', '_', '-')]).strip().replace(' ', '_')
        if not safe_name:
            return False, "Nombre de grupo inválido"
            
        repo_grupo = GRUPOS_DIR / safe_name
        if repo_grupo.exists():
            return False, f"Ya existe un grupo llamado '{safe_name}'"
            
        repo_grupo.mkdir(parents=True)

        # 2. Procesar elementos y registrar assets
        elementos_exportar = {}

        for elem_id, datos in elementos_seleccionados.items():
            # Copia profunda para no modificar el original
            nuevo_dato = json.loads(json.dumps(datos))

            # Gestionar imágenes → registrar en almacén centralizado
            if nuevo_dato.get('tipo') == 'imagen' and 'imagen' in nuevo_dato:
                img = nuevo_dato['imagen']

                # Si ya tiene asset_id, solo tracking
                if img.get('asset_id'):
                    track_usage(img['asset_id'], safe_name)
                else:
                    # Intentar registrar desde datos_temp o archivo
                    nombre_archivo = img.get('nombre_archivo', '')
                    datos_temp = img.get('datos_temp', '')

                    if datos_temp:
                        asset_id = register_asset(datos_temp, nombre_archivo)
                        track_usage(asset_id, safe_name)
                        img['asset_id'] = asset_id
                        img.pop('datos_temp', None)
                    elif nombre_archivo and ruta_assets_origen_app:
                        source_file = Path(ruta_assets_origen_app) / nombre_archivo
                        if source_file.exists():
                            asset_id = register_asset(source_file, nombre_archivo)
                            track_usage(asset_id, safe_name)
                            img['asset_id'] = asset_id
                        else:
                            print(f"Advertencia: No se encontró asset original {source_file}")

            # Añadir etiqueta de grupo
            nuevo_dato['grupo'] = {
                'nombre': safe_name,
                'color': '#cccccc'
            }

            elementos_exportar[elem_id] = nuevo_dato

        # 3. Crear JSON
        info_grupo = {
            "nombre": safe_name,
            "descripcion": descripcion,
            "elementos": elementos_exportar
        }
        
        with open(repo_grupo / f"{safe_name}.json", 'w', encoding='utf-8') as f:
            json.dump(info_grupo, f, indent=4, ensure_ascii=False)
            
        return True, f"Grupo '{safe_name}' creado exitosamente"
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"Error creando grupo: {str(e)}"

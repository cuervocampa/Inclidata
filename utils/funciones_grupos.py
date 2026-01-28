import os
import json
import shutil
from pathlib import Path

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
    Copia el contenido de la carpeta 'assets' del grupo a la carpeta 'assets' 
    de la plantilla destino.
    """
    ruta_assets_origen = GRUPOS_DIR / nombre_grupo / "assets"
    ruta_assets_destino = Path(ruta_plantilla_destino) / "assets"

    if not ruta_assets_origen.exists():
        # El grupo no tiene assets, no pasa nada
        return

    # Asegurar que existe destino/assets
    if not ruta_assets_destino.exists():
        ruta_assets_destino.mkdir(parents=True, exist_ok=True)

    # Copiar archivos
    try:
        for item in ruta_assets_origen.iterdir():
            if item.is_file():
                destino = ruta_assets_destino / item.name
                shutil.copy2(item, destino)
                print(f"Asset copiado: {item.name}")
    except Exception as e:
        print(f"Error copiando assets del grupo {nombre_grupo}: {e}")

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
        assets_grupo = repo_grupo / "assets"
        assets_grupo.mkdir()
        
        # 2. Procesar elementos y copiar assets
        elementos_exportar = {}
        assets_vistos = set()
        
        for elem_id, datos in elementos_seleccionados.items():
            # Copia profunda para no modificar el original
            nuevo_dato = json.loads(json.dumps(datos))
            
            # Limpiar ID para el JSON del grupo (quitar sufijos raros si queremos, o dejar tal cual)
            # Para portabilidad, mejor usaremos las claves originales como claves en el json del grupo
            # O generamos claves genéricas 'elemento_1', 'elemento_2' si los IDs son muy sucios.
            # Dejaremos los IDs originales de momento.
            
            # Gestionar imágenes
            if nuevo_dato.get('tipo') == 'imagen' and 'imagen' in nuevo_dato:
                ruta_actual = nuevo_dato['imagen'].get('ruta_nueva', '')
                nombre_archivo = nuevo_dato['imagen'].get('nombre_archivo', '')
                
                # Si apunta a assets, intentamos copiarlo
                # Si apunta a assets, intentamos copiarlo y generar Base64
                if ruta_actual and nombre_archivo:
                    source_file = Path(ruta_assets_origen_app) / nombre_archivo
                    dest_file = assets_grupo / nombre_archivo
                    
                    if source_file.exists():
                        shutil.copy2(source_file, dest_file)
                        # Asegurar que la ruta en el JSON del grupo sea relativa standard
                        nuevo_dato['imagen']['ruta_nueva'] = f"assets/{nombre_archivo}"
                        
                        # GENERAR BASE64 PARA PORTABILIDAD (datos_temp)
                        try:
                            import base64
                            with open(dest_file, "rb") as image_file:
                                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                                # Detectar mime type básico
                                ext = os.path.splitext(nombre_archivo)[1].lower()
                                mime = "image/png" if ext == ".png" else ("image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png")
                                # Guardar en el JSON
                                nuevo_dato['imagen']['datos_temp'] = f"data:{mime};base64,{encoded_string}"
                        except Exception as e_b64:
                            print(f"Error generando Base64 para el grupo: {e_b64}")
                            
                    else:
                        print(f"Advertencia: No se encontró asset original {source_file}")
            
            # Añadir etiqueta de grupo
            nuevo_dato['grupo'] = {
                'nombre': safe_name,
                'color': '#cccccc' # Color por defecto
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

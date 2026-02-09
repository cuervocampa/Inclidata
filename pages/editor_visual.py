import dash
from dash import html, dcc, Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import dash_component_editor as dce
import base64
import io
import json
import shutil
import uuid
import zipfile
from pathlib import Path

from utils.funciones_grupos import listar_grupos_disponibles, leer_datos_grupo, guardar_nuevo_grupo
from utils.asset_manager import (
    register_asset, get_asset_data_uri, get_asset_path, track_usage,
    resolve_image_element,
)

# Rutas base
BASE_DIR = Path(__file__).resolve().parent.parent
PLANTILLAS_DIR = BASE_DIR / "biblioteca_plantillas"


def listar_plantillas_disponibles():
    """Lista plantillas disponibles en biblioteca_plantillas/."""
    if not PLANTILLAS_DIR.exists():
        return []
    plantillas = []
    for item in PLANTILLAS_DIR.iterdir():
        if item.is_dir():
            json_file = item / f"{item.name}.json"
            if json_file.exists():
                plantillas.append({"label": item.name, "value": item.name})
    return plantillas


def _convertir_elemento(elem_id, elem):
    """
    Convierte un elemento del formato viejo (editor_plantilla) al formato
    que espera el componente React del editor visual.

    Mapping principal:
      estilo: color_relleno→backgroundColor, color_borde→borderColor,
              grosor_borde→borderWidth, opacidad(0-100)→opacity(0-1),
              familia_fuente→fontFamily, negrita→fontWeight, cursiva→fontStyle,
              alineacion_h→textAlign
      contenido: se crea si no existe; imagen.datos_temp/ruta_nueva→contenido.src
      geometria: ancho_maximo→ancho, alto_maximo→alto (tablas)
      metadata.grupo: grupo.nombre (top-level) → metadata.grupo
      id: se añade desde la clave del dict
    """
    nuevo = json.loads(json.dumps(elem))  # deep copy
    nuevo['id'] = elem_id
    tipo = elem.get('tipo', '')

    # --- estilo ---
    old_s = elem.get('estilo', {})
    # Detectar si ya está en formato nuevo (tiene backgroundColor)
    if 'backgroundColor' not in old_s and 'color_relleno' not in old_s and tipo == 'rectangulo':
        # No tiene ninguno, proveer defaults
        pass

    opacidad_raw = old_s.get('opacidad', old_s.get('opacity'))
    if opacidad_raw is not None and opacidad_raw > 1:
        opacity = opacidad_raw / 100.0
    elif opacidad_raw is not None:
        opacity = opacidad_raw
    else:
        opacity = 1

    nuevo['estilo'] = {
        'backgroundColor': old_s.get('color_relleno', old_s.get('backgroundColor',
                           '#e2e8f0' if tipo == 'rectangulo' else 'transparent')),
        'borderColor': old_s.get('color_borde', old_s.get('borderColor', '#cbd5e1')),
        'borderWidth': old_s.get('grosor_borde', old_s.get('borderWidth',
                       1 if tipo == 'rectangulo' else 0)),
        'opacity': opacity,
        'color': old_s.get('color', '#000000'),
        'tamano': old_s.get('tamano', 14),
        'fontFamily': old_s.get('familia_fuente', old_s.get('fontFamily', 'sans-serif')),
        'fontWeight': old_s.get('negrita', old_s.get('fontWeight', 'normal')),
        'fontStyle': old_s.get('cursiva', old_s.get('fontStyle', 'normal')),
        'textAlign': old_s.get('alineacion_h', old_s.get('textAlign', 'left')),
    }

    # --- contenido ---
    if tipo == 'texto':
        old_c = elem.get('contenido', {})
        if isinstance(old_c, dict):
            nuevo['contenido'] = {'texto': old_c.get('texto', ''), 'src': None}
        else:
            nuevo['contenido'] = {'texto': '', 'src': None}
    elif tipo == 'imagen':
        img = elem.get('imagen', {})
        # Prioridad: asset_id → datos_temp → ruta_nueva
        aid = img.get('asset_id')
        if aid:
            src = get_asset_data_uri(aid)
        else:
            src = img.get('datos_temp', '') or img.get('ruta_nueva', '')
        nuevo['contenido'] = {'src': src, 'texto': None}
    else:
        # rectangulo, linea, grafico, tabla — ensure contenido exists
        nuevo['contenido'] = {'texto': None, 'src': None}

    # --- geometria (normalizar tabla: ancho_maximo/alto_maximo) ---
    geo = elem.get('geometria', {})
    nuevo['geometria'] = {
        'x': geo.get('x', 0),
        'y': geo.get('y', 0),
        'ancho': geo.get('ancho', geo.get('ancho_maximo', 10)),
        'alto': geo.get('alto', geo.get('alto_maximo', 5)),
    }

    # --- metadata ---
    old_m = elem.get('metadata', {})
    grupo_obj = elem.get('grupo')
    grupo_str = grupo_obj.get('nombre') if isinstance(grupo_obj, dict) else old_m.get('grupo')
    nuevo['metadata'] = {
        'zIndex': old_m.get('zIndex', 0),
        'visible': old_m.get('visible', True),
        'grupo': grupo_str,
    }

    return nuevo


def _convertir_plantilla(data_json):
    """Convierte todos los elementos de una plantilla al formato del editor visual."""
    for page_id, page in data_json.get('paginas', {}).items():
        old_elems = page.get('elementos', {})
        new_elems = {}
        for elem_id, elem in old_elems.items():
            new_elems[elem_id] = _convertir_elemento(elem_id, elem)
        page['elementos'] = new_elems
    return data_json


def _extraer_assets_a_carpeta(data, carpeta_destino):
    """Extrae las imágenes de los elementos a {carpeta_destino}/assets/.

    Para cada elemento de tipo 'imagen':
      1. Si tiene contenido.src con data URI → decodifica y guarda archivo.
      2. Si tiene imagen.asset_id → copia desde almacén centralizado.
      3. Si tiene imagen.datos_temp con data URI → decodifica y guarda archivo.
      4. Actualiza imagen.ruta_nueva = 'assets/{nombre_archivo}'.

    Funciona tanto con estructura de plantilla (paginas.*.elementos)
    como de grupo (elementos).
    """
    assets_dir = Path(carpeta_destino) / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Recopilar todos los elementos de imagen
    imagen_elems = []
    if 'paginas' in data:
        for page in data.get('paginas', {}).values():
            for elem in page.get('elementos', {}).values():
                if elem.get('tipo') == 'imagen':
                    imagen_elems.append(elem)
    else:
        for elem in data.get('elementos', {}).values():
            if elem.get('tipo') == 'imagen':
                imagen_elems.append(elem)

    for elem in imagen_elems:
        img = elem.get('imagen', {})
        contenido = elem.get('contenido', {})
        src = contenido.get('src', '') or ''
        nombre_archivo = img.get('nombre_archivo', f"{elem.get('id', 'img')}.png")

        guardado = False

        # 1. contenido.src con data URI
        if src.startswith('data:'):
            try:
                header, encoded = src.split(',', 1)
                img_bytes = base64.b64decode(encoded)
                dest = assets_dir / nombre_archivo
                dest.write_bytes(img_bytes)
                guardado = True
            except Exception as e:
                print(f"[assets] Error guardando desde contenido.src: {e}")

        # 2. asset_id → copiar desde almacén centralizado
        if not guardado and img.get('asset_id'):
            asset_path = get_asset_path(img['asset_id'])
            if asset_path and asset_path.exists():
                dest = assets_dir / nombre_archivo
                shutil.copy2(asset_path, dest)
                guardado = True

        # 3. datos_temp con data URI
        if not guardado and img.get('datos_temp', ''):
            datos_temp = img['datos_temp']
            if datos_temp.startswith('data:'):
                try:
                    header, encoded = datos_temp.split(',', 1)
                    img_bytes = base64.b64decode(encoded)
                    dest = assets_dir / nombre_archivo
                    dest.write_bytes(img_bytes)
                    guardado = True
                except Exception as e:
                    print(f"[assets] Error guardando desde datos_temp: {e}")

        # Actualizar ruta relativa
        if guardado:
            img['ruta_nueva'] = f"assets/{nombre_archivo}"
            img['nombre_archivo'] = nombre_archivo
            elem['imagen'] = img


def _fusionar_grupo_en_estado(datos_grupo, editor_state):
    """Fusiona los elementos de un grupo en la página actual del editor_state.
    Retorna (editor_state_actualizado, count_elementos)."""
    if not editor_state:
        editor_state = {
            "paginas": {
                "1": {
                    "elementos": {},
                    "configuracion": {"orientacion": "portrait"}
                }
            },
            "pagina_actual": "1",
            "configuracion": {
                "nombre_plantilla": "Nueva Plantilla Visual",
                "num_paginas": 1
            }
        }

    pagina_actual = editor_state.get('pagina_actual', "1")

    if pagina_actual not in editor_state.get('paginas', {}):
        editor_state.setdefault('paginas', {})[pagina_actual] = {
            'elementos': {}, 'configuracion': {'orientacion': 'portrait'}
        }

    if 'elementos' not in editor_state['paginas'][pagina_actual]:
        editor_state['paginas'][pagina_actual]['elementos'] = {}

    elems_actuales = editor_state['paginas'][pagina_actual]['elementos']
    sufijo = str(uuid.uuid4())[:4]

    count = 0
    for id_elem, props in datos_grupo['elementos'].items():
        nuevo_id = f"{id_elem}_{sufijo}"
        elem_convertido = _convertir_elemento(nuevo_id, props)
        elems_actuales[nuevo_id] = elem_convertido
        count += 1

    editor_state['paginas'][pagina_actual]['elementos'] = elems_actuales
    return editor_state, count


def layout():
    plantillas = listar_plantillas_disponibles()
    grupos = listar_grupos_disponibles()

    return dmc.MantineProvider(
        theme={"colorScheme": "light"},
        children=html.Div([
            # Header — solo botones, sin dropdowns
            dmc.Paper(
                p="md",
                withBorder=True,
                shadow="sm",
                style={"marginBottom": "20px"},
                children=dmc.Group([
                    dmc.Title("Editor Visual", order=2),
                    dmc.Group([
                        dcc.Upload(
                            id="ev-upload-grupo",
                            children=dmc.Button(
                                "Importar Grupo",
                                leftSection=DashIconify(icon="mdi:package-variant-closed"),
                                variant="outline",
                                color="grape",
                            ),
                            accept=".json,.zip",
                        ),
                        dmc.Button(
                            "Exportar Grupo",
                            id="btn-exportar-grupo",
                            leftSection=DashIconify(icon="mdi:download"),
                            variant="outline",
                            color="indigo",
                        ),
                        dmc.Divider(orientation="vertical", style={"height": "24px"}),
                        dmc.Button(
                            "Cargar Plantilla",
                            id="btn-cargar-plantilla",
                            leftSection=DashIconify(icon="mdi:folder-open"),
                            variant="outline",
                            color="blue",
                        ),
                        dmc.Button(
                            "Guardar Plantilla",
                            id="btn-guardar-plantilla",
                            leftSection=DashIconify(icon="mdi:content-save-outline"),
                            variant="outline",
                            color="teal",
                        ),
                        dmc.Button(
                            "Guardar Cambios",
                            id="btn-save-visual",
                            leftSection=DashIconify(icon="mdi:content-save"),
                            color="green",
                        ),
                        dmc.Button(
                            "Generar PDF",
                            id="btn-generate-pdf-visual",
                            leftSection=DashIconify(icon="mdi:file-pdf-box"),
                            color="red",
                            disabled=True,
                        ),
                    ]),
                ], justify="space-between")
            ),

            # Componente React
            html.Div(
                dce.Editor(
                    id='visual-editor',
                    data={
                        "paginas": {
                            "1": {
                                "elementos": {},
                                "configuracion": {"orientacion": "portrait"}
                            }
                        },
                        "pagina_actual": "1",
                        "configuracion": {
                            "nombre_plantilla": "Nueva Plantilla Visual",
                            "num_paginas": 1
                        }
                    }
                ),
                style={"height": "calc(100vh - 100px)", "width": "100%"}
            ),

            # Feedback + Downloads
            html.Div(id="save-feedback-visual"),
            dcc.Download(id="ev-download-grupo"),

            # Stores
            dcc.Store(id="ev-pending-action", data=None),

            # Modal: Guardar Plantilla
            dmc.Modal(
                id="modal-guardar-plantilla",
                title="Guardar Plantilla",
                children=[
                    dmc.TextInput(
                        id="input-nombre-plantilla-guardar",
                        label="Nombre de la plantilla",
                        placeholder="Ej: Mi_plantilla",
                        required=True,
                    ),
                    dmc.Group(
                        [
                            dmc.Button(
                                "Guardar",
                                id="btn-confirmar-guardar-plantilla",
                                leftSection=DashIconify(icon="mdi:content-save"),
                                color="teal",
                            ),
                        ],
                        justify="flex-end",
                        style={"marginTop": "15px"},
                    ),
                ],
            ),

            # Modal: Cargar Plantilla
            dmc.Modal(
                id="modal-cargar-plantilla",
                title="Cargar Plantilla",
                children=[
                    dmc.Select(
                        id="modal-select-plantilla",
                        label="Seleccionar plantilla",
                        placeholder="Buscar plantilla...",
                        data=plantillas,
                        searchable=True,
                        style={"marginBottom": "15px"},
                    ),
                    dmc.Group(
                        [
                            dmc.Button(
                                "Cargar",
                                id="btn-confirmar-cargar-plantilla",
                                color="blue",
                            ),
                        ],
                        justify="flex-end",
                    ),
                ],
            ),

            # Modal: Exportar Grupo
            dmc.Modal(
                id="modal-exportar-grupo",
                title="Exportar Grupo",
                children=[
                    dmc.Select(
                        id="modal-select-grupo-export",
                        label="Seleccionar grupo",
                        placeholder="Buscar grupo...",
                        data=grupos,
                        searchable=True,
                        style={"marginBottom": "15px"},
                    ),
                    dmc.Group(
                        [
                            dmc.Button(
                                "Descargar",
                                id="btn-confirmar-exportar-grupo",
                                leftSection=DashIconify(icon="mdi:download"),
                                color="indigo",
                            ),
                        ],
                        justify="flex-end",
                    ),
                ],
            ),

            # Modal: Crear Grupo
            dmc.Modal(
                id="modal-crear-grupo",
                title="Crear nuevo grupo",
                children=[
                    dmc.TextInput(
                        id="input-nombre-grupo",
                        label="Nombre del grupo",
                        placeholder="Ej: Encabezado principal",
                        required=True,
                    ),
                    dmc.Textarea(
                        id="input-desc-grupo",
                        label="Descripción",
                        placeholder="Descripción opcional...",
                        autosize=True,
                        minRows=2,
                        style={"marginTop": "10px"},
                    ),
                    dmc.Group(
                        [
                            dmc.Button(
                                "Crear",
                                id="btn-confirmar-crear-grupo",
                                color="blue",
                            ),
                        ],
                        justify="flex-end",
                        style={"marginTop": "15px"},
                    ),
                ],
            ),
        ], style={"padding": "20px", "height": "100vh", "backgroundColor": "#f8f9fa"})
    )


def register_callbacks(app):

    # ── Abrir modales ────────────────────────────────────────────────
    @app.callback(
        Output("modal-cargar-plantilla", "opened"),
        Input("btn-cargar-plantilla", "n_clicks"),
        prevent_initial_call=True
    )
    def abrir_modal_cargar_plantilla(n):
        return True if n else dash.no_update

    @app.callback(
        Output("modal-exportar-grupo", "opened"),
        Input("btn-exportar-grupo", "n_clicks"),
        prevent_initial_call=True
    )
    def abrir_modal_exportar_grupo(n):
        return True if n else dash.no_update

    # ── Cargar plantilla (desde modal) ───────────────────────────────
    @app.callback(
        Output("visual-editor", "data"),
        Output("modal-cargar-plantilla", "opened", allow_duplicate=True),
        Output("save-feedback-visual", "children", allow_duplicate=True),
        Input("btn-confirmar-cargar-plantilla", "n_clicks"),
        State("modal-select-plantilla", "value"),
        prevent_initial_call=True
    )
    def cargar_plantilla(n_clicks, nombre_plantilla):
        if not n_clicks or not nombre_plantilla:
            return dash.no_update, dash.no_update, dash.no_update

        ruta_json = PLANTILLAS_DIR / nombre_plantilla / f"{nombre_plantilla}.json"
        if not ruta_json.exists():
            print(f"[editor_visual] Plantilla no encontrada: {ruta_json}")
            return dash.no_update, False, dmc.Notification(
                title="Error",
                message=f"Plantilla '{nombre_plantilla}' no encontrada.",
                color="red", action="show"
            )

        try:
            with open(ruta_json, 'r', encoding='utf-8') as f:
                data_json = json.load(f)

            # Normalizar estructura plana (sin 'paginas') a estructura con páginas
            if "paginas" not in data_json and "elementos" in data_json:
                elems = data_json.pop("elementos", {})
                page_config = {"orientacion": data_json.get("configuracion", {}).get("orientacion", "portrait")}
                data_json["paginas"] = {
                    "1": {
                        "elementos": elems,
                        "configuracion": page_config
                    }
                }
                if "pagina_actual" not in data_json:
                    data_json["pagina_actual"] = "1"

            # Asegurar configuracion de plantilla a nivel raíz
            if "configuracion" not in data_json or "nombre_plantilla" not in data_json.get("configuracion", {}):
                data_json.setdefault("configuracion", {})
                data_json["configuracion"].setdefault("nombre_plantilla", nombre_plantilla)
                data_json["configuracion"].setdefault("num_paginas", len(data_json.get("paginas", {})))

            _convertir_plantilla(data_json)

            print(f"[editor_visual] Plantilla '{nombre_plantilla}' cargada OK — "
                  f"{len(data_json.get('paginas', {}))} páginas")
            return data_json, False, dmc.Notification(
                title="Plantilla cargada",
                message=f"'{nombre_plantilla}' cargada correctamente.",
                color="green", action="show"
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[editor_visual] Error cargando plantilla '{nombre_plantilla}': {e}")
            return dash.no_update, False, dmc.Notification(
                title="Error",
                message=f"Error cargando plantilla: {e}",
                color="red", action="show"
            )

    # ── Importar grupo desde archivo JSON ────────────────────────────
    @app.callback(
        Output("visual-editor", "data", allow_duplicate=True),
        Output("save-feedback-visual", "children", allow_duplicate=True),
        Input("ev-upload-grupo", "contents"),
        State("ev-upload-grupo", "filename"),
        State("visual-editor", "value"),
        prevent_initial_call=True
    )
    def importar_grupo_archivo(contents, filename, editor_state):
        if not contents:
            return dash.no_update, dash.no_update

        try:
            content_type, content_string = contents.split(',', 1)
            decoded = base64.b64decode(content_string)

            if filename and filename.lower().endswith('.zip'):
                # Extraer JSON + assets del ZIP
                datos_grupo = None
                with zipfile.ZipFile(io.BytesIO(decoded), 'r') as zf:
                    # Buscar el .json dentro del ZIP
                    json_files = [n for n in zf.namelist() if n.endswith('.json')]
                    if not json_files:
                        raise ValueError("El ZIP no contiene ningún archivo .json")
                    datos_grupo = json.loads(zf.read(json_files[0]).decode('utf-8'))

                    # Extraer assets al almacén centralizado
                    asset_files = [n for n in zf.namelist()
                                   if '/assets/' in n and not n.endswith('/')]
                    for asset_name in asset_files:
                        asset_basename = Path(asset_name).name
                        asset_data = zf.read(asset_name)
                        # Registrar en almacén centralizado
                        data_uri = (
                            "data:application/octet-stream;base64,"
                            + base64.b64encode(asset_data).decode()
                        )
                        asset_id = register_asset(data_uri, asset_basename)
                        # Actualizar asset_id en elementos que referencien este archivo
                        for elem in datos_grupo.get('elementos', {}).values():
                            img = elem.get('imagen', {})
                            if img.get('nombre_archivo') == asset_basename:
                                img['asset_id'] = asset_id
                                img['datos_temp'] = data_uri
            else:
                datos_grupo = json.loads(decoded.decode('utf-8'))
        except Exception as e:
            print(f"[editor_visual] Error decodificando archivo '{filename}': {e}")
            return dash.no_update, dmc.Notification(
                title="Error",
                message=f"No se pudo leer el archivo: {e}",
                color="red", action="show"
            )

        if 'elementos' not in datos_grupo:
            return dash.no_update, dmc.Notification(
                title="Error",
                message=f"El archivo '{filename}' no contiene la clave 'elementos'.",
                color="red", action="show"
            )

        editor_state, count = _fusionar_grupo_en_estado(datos_grupo, editor_state)
        pagina_actual = editor_state.get('pagina_actual', '1')
        print(f"[editor_visual] Grupo importado desde '{filename}' — {count} elementos en página {pagina_actual}")
        return editor_state, dmc.Notification(
            title="Grupo importado",
            message=f"{count} elementos importados desde '{filename}'.",
            color="green", action="show"
        )

    # ── Exportar grupo (desde modal) — ZIP con JSON + assets ────────
    @app.callback(
        Output("ev-download-grupo", "data"),
        Output("modal-exportar-grupo", "opened", allow_duplicate=True),
        Input("btn-confirmar-exportar-grupo", "n_clicks"),
        State("modal-select-grupo-export", "value"),
        prevent_initial_call=True
    )
    def exportar_grupo(n_clicks, nombre_grupo):
        if not n_clicks or not nombre_grupo:
            return dash.no_update, dash.no_update

        from utils.funciones_grupos import GRUPOS_DIR
        grupo_dir = GRUPOS_DIR / nombre_grupo
        json_path = grupo_dir / f"{nombre_grupo}.json"

        if not json_path.exists():
            return dash.no_update, False

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            # JSON
            zf.write(json_path, f"{nombre_grupo}/{nombre_grupo}.json")
            # assets/
            assets_dir = grupo_dir / "assets"
            if assets_dir.is_dir():
                for asset_file in assets_dir.iterdir():
                    if asset_file.is_file():
                        zf.write(asset_file, f"{nombre_grupo}/assets/{asset_file.name}")

        print(f"[editor_visual] Exportando grupo '{nombre_grupo}' como ZIP")
        return dcc.send_bytes(
            buf.getvalue(),
            filename=f"{nombre_grupo}.zip"
        ), False

    # ── Guardar Plantilla — abrir modal ─────────────────────────────
    @app.callback(
        Output("modal-guardar-plantilla", "opened"),
        Output("input-nombre-plantilla-guardar", "value"),
        Input("btn-guardar-plantilla", "n_clicks"),
        State("visual-editor", "value"),
        prevent_initial_call=True
    )
    def abrir_modal_guardar_plantilla(n, editor_state):
        if not n:
            return dash.no_update, dash.no_update
        nombre_actual = ""
        if editor_state:
            nombre_actual = editor_state.get("configuracion", {}).get("nombre_plantilla", "")
        return True, nombre_actual

    # ── Guardar Plantilla — confirmar ────────────────────────────────
    @app.callback(
        Output("modal-guardar-plantilla", "opened", allow_duplicate=True),
        Output("save-feedback-visual", "children", allow_duplicate=True),
        Output("modal-select-plantilla", "data"),
        Input("btn-confirmar-guardar-plantilla", "n_clicks"),
        State("input-nombre-plantilla-guardar", "value"),
        State("visual-editor", "value"),
        prevent_initial_call=True
    )
    def confirmar_guardar_plantilla(n_clicks, nombre, editor_state):
        if not n_clicks or not nombre or not editor_state:
            return dash.no_update, dash.no_update, dash.no_update

        try:
            import copy
            data = copy.deepcopy(editor_state)
            data.setdefault("configuracion", {})["nombre_plantilla"] = nombre

            dest_dir = PLANTILLAS_DIR / nombre
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Extraer imágenes a {plantilla}/assets/
            _extraer_assets_a_carpeta(data, dest_dir)

            # Registrar en almacén centralizado y limpiar base64
            for page_id, page in data.get("paginas", {}).items():
                for elem_id, elem in page.get("elementos", {}).items():
                    if elem.get("tipo") != "imagen":
                        continue
                    contenido = elem.get("contenido", {})
                    img = elem.get("imagen", {})
                    src = contenido.get("src", "") or ""

                    if src.startswith("data:"):
                        nombre_archivo = img.get("nombre_archivo", f"{elem_id}.png")
                        asset_id = register_asset(src, nombre_archivo)
                        track_usage(asset_id, nombre)
                        img["asset_id"] = asset_id
                        contenido["src"] = None
                        img.pop("datos_temp", None)
                    elif img.get("asset_id"):
                        track_usage(img["asset_id"], nombre)

                    elem["imagen"] = img
                    elem["contenido"] = contenido

            json_path = dest_dir / f"{nombre}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"[editor_visual] Plantilla '{nombre}' guardada en {json_path}")
            nuevas_plantillas = listar_plantillas_disponibles()
            return False, dmc.Notification(
                title="Plantilla guardada",
                message=f"'{nombre}' guardada con assets correctamente.",
                color="green", action="show"
            ), nuevas_plantillas
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, dmc.Notification(
                title="Error",
                message=f"Error al guardar: {e}",
                color="red", action="show"
            ), dash.no_update

    # ── Detectar acción create_group desde React ─────────────────────
    @app.callback(
        Output("modal-crear-grupo", "opened"),
        Output("ev-pending-action", "data"),
        Input("visual-editor", "value"),
        prevent_initial_call=True
    )
    def detectar_accion_crear_grupo(editor_state):
        if not editor_state or not isinstance(editor_state, dict):
            return dash.no_update, dash.no_update

        action = editor_state.get('action')
        if action and action.get('type') == 'create_group':
            element_ids = action.get('elementIds', [])
            return True, {'elementIds': element_ids}

        return dash.no_update, dash.no_update

    # ── Confirmar creación de grupo ──────────────────────────────────
    @app.callback(
        Output("modal-crear-grupo", "opened", allow_duplicate=True),
        Output("save-feedback-visual", "children", allow_duplicate=True),
        Output("modal-select-grupo-export", "data"),
        Input("btn-confirmar-crear-grupo", "n_clicks"),
        State("input-nombre-grupo", "value"),
        State("input-desc-grupo", "value"),
        State("ev-pending-action", "data"),
        State("visual-editor", "value"),
        prevent_initial_call=True
    )
    def confirmar_crear_grupo(n_clicks, nombre, descripcion, pending, editor_state):
        if not n_clicks or not nombre or not pending:
            return dash.no_update, dash.no_update, dash.no_update

        element_ids = pending.get('elementIds', [])
        if not element_ids or not editor_state:
            return False, dmc.Notification(
                title="Error",
                message="No hay elementos seleccionados.",
                color="red", action="show"
            ), dash.no_update

        pagina_actual = editor_state.get('pagina_actual', '1')
        pagina = editor_state.get('paginas', {}).get(pagina_actual, {})
        elementos = pagina.get('elementos', {})

        elementos_seleccionados = {eid: elementos[eid] for eid in element_ids if eid in elementos}

        if not elementos_seleccionados:
            return False, dmc.Notification(
                title="Error",
                message="No se encontraron los elementos seleccionados.",
                color="red", action="show"
            ), dash.no_update

        exito, mensaje = guardar_nuevo_grupo(
            nombre,
            descripcion or "",
            elementos_seleccionados,
            PLANTILLAS_DIR / "_assets"
        )

        if exito:
            nuevos_grupos = listar_grupos_disponibles()
            return False, dmc.Notification(
                title="Grupo creado",
                message=mensaje,
                color="green", action="show"
            ), nuevos_grupos
        else:
            return False, dmc.Notification(
                title="Error",
                message=mensaje,
                color="red", action="show"
            ), dash.no_update

    # ── Guardar Cambios (a biblioteca) ───────────────────────────────
    @app.callback(
        Output("save-feedback-visual", "children"),
        Input("btn-save-visual", "n_clicks"),
        Input("visual-editor", "value"),
        prevent_initial_call=True
    )
    def save_template(n_clicks, editor_state):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger_id != "btn-save-visual":
            return dash.no_update

        if not editor_state:
            return dmc.Notification(
                title="Error",
                message="No hay datos para guardar.",
                color="red",
                action="show"
            )

        try:
            import copy
            data = copy.deepcopy(editor_state)
            nombre = data.get("configuracion", {}).get("nombre_plantilla", "")
            if not nombre:
                return dmc.Notification(
                    title="Error",
                    message="La plantilla no tiene nombre.",
                    color="red",
                    action="show"
                )

            dest_dir = PLANTILLAS_DIR / nombre
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Extraer imágenes a {plantilla}/assets/ y registrar en almacén
            _extraer_assets_a_carpeta(data, dest_dir)

            # Registrar en almacén centralizado y limpiar base64 del JSON
            for page_id, page in data.get("paginas", {}).items():
                for elem_id, elem in page.get("elementos", {}).items():
                    if elem.get("tipo") != "imagen":
                        continue
                    contenido = elem.get("contenido", {})
                    img = elem.get("imagen", {})
                    src = contenido.get("src", "") or ""

                    if src.startswith("data:"):
                        nombre_archivo = img.get("nombre_archivo", f"{elem_id}.png")
                        asset_id = register_asset(src, nombre_archivo)
                        track_usage(asset_id, nombre)
                        img["asset_id"] = asset_id
                        contenido["src"] = None
                        img.pop("datos_temp", None)
                    elif img.get("asset_id"):
                        track_usage(img["asset_id"], nombre)

                    elem["imagen"] = img
                    elem["contenido"] = contenido

            # Guardar JSON
            json_path = dest_dir / f"{nombre}.json"

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"[editor_visual] Plantilla '{nombre}' guardada en {json_path}")
            return dmc.Notification(
                title="Guardado",
                message=f"Plantilla '{nombre}' guardada correctamente.",
                color="green",
                action="show"
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return dmc.Notification(
                title="Error",
                message=f"Error al guardar: {str(e)}",
                color="red",
                action="show"
            )

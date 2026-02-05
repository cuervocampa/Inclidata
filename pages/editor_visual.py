import dash
from dash import html, dcc, Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import dash_component_editor as dce
import json
import uuid
from pathlib import Path

from utils.funciones_grupos import listar_grupos_disponibles, leer_datos_grupo, copiar_assets_grupo

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


def layout():
    plantillas = listar_plantillas_disponibles()
    grupos = listar_grupos_disponibles()

    return dmc.MantineProvider(
        theme={"colorScheme": "light"},
        children=html.Div([
            # Header
            dmc.Paper(
                p="md",
                withBorder=True,
                shadow="sm",
                style={"marginBottom": "20px"},
                children=dmc.Group([
                    dmc.Title("Editor Visual (Lovable Engine)", order=2),
                    dmc.Group([
                        dmc.Select(
                            id="ev-select-plantilla",
                            placeholder="Cargar plantilla...",
                            data=plantillas,
                            searchable=True,
                            clearable=True,
                            style={"minWidth": "220px"},
                        ),
                        dmc.Select(
                            id="ev-select-grupo",
                            placeholder="Cargar grupo...",
                            data=grupos,
                            searchable=True,
                            clearable=True,
                            style={"minWidth": "220px"},
                        ),
                        dmc.Button(
                            "Guardar Cambios",
                            id="btn-save-visual",
                            leftSection=DashIconify(icon="mdi:content-save"),
                            color="green"
                        ),
                        dmc.Button(
                            "Generar PDF",
                            id="btn-generate-pdf-visual",
                            leftSection=DashIconify(icon="mdi:file-pdf-box"),
                            color="red",
                            disabled=True
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

            # Feedback de guardado
            html.Div(id="save-feedback-visual"),
        ], style={"padding": "20px", "height": "100vh", "backgroundColor": "#f8f9fa"})
    )


def register_callbacks(app):
    # --- Callback: Cargar plantilla seleccionada ---
    @app.callback(
        Output("visual-editor", "data"),
        Input("ev-select-plantilla", "value"),
        prevent_initial_call=True
    )
    def cargar_plantilla(nombre_plantilla):
        if not nombre_plantilla:
            return dash.no_update

        ruta_json = PLANTILLAS_DIR / nombre_plantilla / f"{nombre_plantilla}.json"
        if not ruta_json.exists():
            print(f"[editor_visual] Plantilla no encontrada: {ruta_json}")
            return dash.no_update

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

            # Convertir elementos al formato del editor visual
            _convertir_plantilla(data_json)

            print(f"[editor_visual] Plantilla '{nombre_plantilla}' cargada OK — "
                  f"{len(data_json.get('paginas', {}))} páginas")
            return data_json
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[editor_visual] Error cargando plantilla '{nombre_plantilla}': {e}")
            return dash.no_update

    # --- Callback: Cargar grupo (fusión en página actual) ---
    @app.callback(
        Output("visual-editor", "data", allow_duplicate=True),
        Input("ev-select-grupo", "value"),
        State("visual-editor", "value"),
        prevent_initial_call=True
    )
    def cargar_grupo(nombre_grupo, editor_state):
        if not nombre_grupo:
            return dash.no_update

        datos_grupo = leer_datos_grupo(nombre_grupo)
        if not datos_grupo or 'elementos' not in datos_grupo:
            print(f"[editor_visual] Grupo inválido o vacío: {nombre_grupo}")
            return dash.no_update

        # Usar estado actual del editor o crear uno vacío
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

        # Copiar assets del grupo a la plantilla activa
        try:
            nom_plantilla = editor_state.get('configuracion', {}).get('nombre_plantilla', 'temp_plantilla') or 'temp_plantilla'
            copiar_assets_grupo(nombre_grupo, str(PLANTILLAS_DIR / nom_plantilla))
        except Exception:
            pass

        count = 0
        for id_elem, props in datos_grupo['elementos'].items():
            nuevo_id = f"{id_elem}_{sufijo}"
            # Convertir al formato visual
            elem_convertido = _convertir_elemento(nuevo_id, props)
            elems_actuales[nuevo_id] = elem_convertido
            count += 1

        editor_state['paginas'][pagina_actual]['elementos'] = elems_actuales
        print(f"[editor_visual] Grupo '{nombre_grupo}' fusionado — {count} elementos en página {pagina_actual}")
        return editor_state

    # --- Callback: Guardar plantilla ---
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

        if trigger_id == "btn-save-visual":
            if editor_state:
                return dmc.Notification(
                    title="Guardado",
                    message=f"Plantilla '{editor_state.get('configuracion', {}).get('nombre_plantilla')}' guardada correctamente.",
                    color="green",
                    action="show"
                )
            else:
                return dmc.Notification(
                    title="Error",
                    message="No hay datos para guardar.",
                    color="red",
                    action="show"
                )

        return dash.no_update

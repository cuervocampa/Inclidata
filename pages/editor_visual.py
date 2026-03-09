import dash
from dash import html, dcc, Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import dash_component_editor as dce
import base64
import io
import zipfile
from pathlib import Path

from utils.funciones_grupos import listar_grupos_disponibles, leer_datos_grupo, guardar_nuevo_grupo
from utils.asset_manager import ASSETS_DIR
from utils.template_service import (
    listar_plantillas_disponibles, listar_scripts_graficos, listar_scripts_tablas,
    cargar_plantilla_para_editor, guardar_plantilla,
    fusionar_grupo_en_plantilla, importar_grupo_desde_bytes,
    PlantillaNoEncontrada, PlantillaInvalida,
)


# ---------------------------------------------------------------------------
# Helpers: detección de tokens $CURRENT en la plantilla activa
# ---------------------------------------------------------------------------

_TOKEN_LABELS = {
    "$CURRENT_fecha_seleccionada": "Fecha Seleccionada",
    "$CURRENT_ultimas_camp":       "Nº Últimas Campañas",
    "$CURRENT_fecha_inicial":      "Fecha Inicial",
    "$CURRENT_fecha_final":        "Fecha Final",
    "$CURRENT":                    "Nombre del Sensor (ID)",
}


def _detectar_tokens_usados(editor_state: dict) -> set:
    """Escanea los parametros de todos los scripts en el editor_state buscando tokens $CURRENT*."""
    tokens = set()
    known = list(_TOKEN_LABELS.keys())

    def scan(v):
        if isinstance(v, str):
            for t in known:
                if t in v:
                    tokens.add(t)
        elif isinstance(v, dict):
            for x in v.values():
                scan(x)
        elif isinstance(v, list):
            for x in v:
                scan(x)

    if not isinstance(editor_state, dict):
        return tokens
    for pagina in editor_state.get("paginas", {}).values():
        for elem in pagina.get("elementos", {}).values():
            cfg = elem.get("configuracion") or {}
            scan(cfg.get("parametros") or {})
    return tokens


def _render_tokens_info(tokens: set):
    """Devuelve un componente DMC mostrando los tokens detectados."""
    if not tokens:
        return dmc.Alert(
            "No se detectaron parámetros dinámicos ($CURRENT) en la plantilla. "
            "Puedes rellenar los campos igualmente.",
            color="gray",
            variant="light",
            icon=DashIconify(icon="mdi:information-outline", width=18),
            style={"marginBottom": "12px"},
        )
    labels = [_TOKEN_LABELS.get(t, t) for t in sorted(tokens)]
    return dmc.Alert(
        dmc.Stack([
            dmc.Text("Parámetros detectados en la plantilla:", size="sm", fw=600),
            dmc.Group(
                [dmc.Badge(lbl, color="blue", variant="light") for lbl in labels],
                gap="xs",
            ),
        ], gap="xs"),
        color="blue",
        variant="light",
        icon=DashIconify(icon="mdi:auto-fix", width=18),
        style={"marginBottom": "12px"},
    )


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
                        },
                        "chartScripts": listar_scripts_graficos(),
                        "tableScripts": listar_scripts_tablas()
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

            # Modal: Generar PDF
            dmc.Modal(
                id="modal-generar-pdf",
                title=dmc.Group([
                    DashIconify(icon="mdi:file-pdf-box", width=22, color="#e03131"),
                    dmc.Text("Generar Informe PDF", fw=600),
                ], gap="xs"),
                size="lg",
                children=[
                    # Zona de deteción de tokens (se rellena en callback)
                    html.Div(id="div-ctx-tokens-info"),

                    # Inputs de contexto
                    dmc.SimpleGrid(
                        cols=2,
                        spacing="md",
                        children=[
                            dmc.TextInput(
                                id="input-ctx-sensor",
                                label="Sensor / ID",
                                placeholder="Ej: INCL-A1",
                                leftSection=DashIconify(icon="mdi:antenna", width=16),
                            ),
                            dmc.TextInput(
                                id="input-ctx-fecha-sel",
                                label="Fecha seleccionada",
                                placeholder="YYYY-MM-DD",
                                leftSection=DashIconify(icon="mdi:calendar-check", width=16),
                            ),
                            dmc.TextInput(
                                id="input-ctx-fecha-ini",
                                label="Fecha inicial",
                                placeholder="YYYY-MM-DD",
                                leftSection=DashIconify(icon="mdi:calendar-start", width=16),
                            ),
                            dmc.TextInput(
                                id="input-ctx-fecha-fin",
                                label="Fecha final",
                                placeholder="YYYY-MM-DD",
                                leftSection=DashIconify(icon="mdi:calendar-end", width=16),
                            ),
                        ],
                    ),
                    dmc.NumberInput(
                        id="input-ctx-ultimas-camp",
                        label="Nº últimas campañas",
                        value=3,
                        min=1,
                        max=100,
                        step=1,
                        style={"marginTop": "10px", "width": "200px"},
                    ),
                    # dcc.Loading envuelve los botones + dcc.Download:
                    # detecta automáticamente cuándo el callback está corriendo
                    # y muestra un overlay mientras se genera el PDF.
                    dcc.Loading(
                        type="circle",
                        delay_show=100,
                        overlay_style={
                            "borderRadius": "8px",
                            "background": "rgba(255,255,255,0.80)",
                        },
                        children=[
                            dmc.Group(
                                [
                                    dmc.Button(
                                        "Generar maquetación PDF",
                                        id="btn-maquetacion-pdf",
                                        leftSection=DashIconify(icon="mdi:file-pdf-box"),
                                        color="red",
                                    ),
                                ],
                                justify="flex-end",
                                gap="sm",
                                style={"marginTop": "20px"},
                            ),
                            # dcc.Download DENTRO del Loading para activar el spinner
                            dcc.Download(id="dcc-download-pdf"),
                        ],
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

        try:
            payload = cargar_plantilla_para_editor(nombre_plantilla)
            print(f"[editor_visual] Plantilla '{nombre_plantilla}' cargada OK — "
                  f"{len(payload.get('paginas', {}))} páginas")
            return payload, False, dmc.Notification(
                title="Plantilla cargada",
                message=f"'{nombre_plantilla}' cargada correctamente.",
                color="green", action="show"
            )
        except PlantillaNoEncontrada:
            return dash.no_update, False, dmc.Notification(
                title="Error",
                message=f"Plantilla '{nombre_plantilla}' no encontrada.",
                color="red", action="show"
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
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
            _, content_string = contents.split(',', 1)
            raw_bytes = base64.b64decode(content_string)
            datos_grupo = importar_grupo_desde_bytes(raw_bytes, filename)
            editor_state, count = fusionar_grupo_en_plantilla(datos_grupo, editor_state)
            editor_state["chartScripts"] = listar_scripts_graficos()
            editor_state["tableScripts"] = listar_scripts_tablas()
            pagina_actual = editor_state.get('pagina_actual', '1')
            print(f"[editor_visual] Grupo '{filename}' importado — {count} elementos en página {pagina_actual}")
            return editor_state, dmc.Notification(
                title="Grupo importado",
                message=f"{count} elementos importados desde '{filename}'.",
                color="green", action="show"
            )
        except PlantillaInvalida as e:
            return dash.no_update, dmc.Notification(
                title="Error",
                message=str(e),
                color="red", action="show"
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return dash.no_update, dmc.Notification(
                title="Error",
                message=f"No se pudo procesar el archivo: {e}",
                color="red", action="show"
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
            guardar_plantilla(editor_state, nombre=nombre)
            print(f"[editor_visual] Plantilla '{nombre}' guardada OK")
            nuevas_plantillas = listar_plantillas_disponibles()
            return False, dmc.Notification(
                title="Plantilla guardada",
                message=f"'{nombre}' guardada correctamente.",
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
            ASSETS_DIR
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

    # ── Generar PDF — abrir modal + detectar tokens ─────────────────────────
    @app.callback(
        Output("modal-generar-pdf", "opened"),
        Output("div-ctx-tokens-info", "children"),
        Input("btn-generate-pdf-visual", "n_clicks"),
        State("visual-editor", "value"),
        prevent_initial_call=True,
    )
    def abrir_modal_generar_pdf(n, editor_state):
        if not n:
            return dash.no_update, dash.no_update
        tokens = _detectar_tokens_usados(editor_state or {})
        return True, _render_tokens_info(tokens)

    # ── Generar PDF — confirmar (con datos o maquetación) ──────────────────────
    @app.callback(
        Output("dcc-download-pdf", "data"),
        Output("modal-generar-pdf", "opened", allow_duplicate=True),
        Output("save-feedback-visual", "children", allow_duplicate=True),
        Input("btn-maquetacion-pdf", "n_clicks"),
        State("visual-editor", "value"),
        State("visual-editor", "data"),
        prevent_initial_call=True,
    )
    def confirmar_generar_pdf(n_maq, editor_value, editor_data):
        editor_state = editor_value or editor_data
        if not n_maq or not editor_state:
            return dash.no_update, dash.no_update, dash.no_update

        nombre = (editor_state.get("configuracion") or {}).get("nombre_plantilla") or "maquetacion"
        context = {"is_maquetacion": True}

        try:
            import tempfile
            from pathlib import Path as _Path
            from utils.report_engine import generate_report_pdf_from_state

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = _Path(tmp.name)

            print(f"[editor_visual] Generando maquetación PDF: '{nombre}'...")
            generate_report_pdf_from_state(editor_state, context, tmp_path)
            pdf_bytes = tmp_path.read_bytes()
            tmp_path.unlink(missing_ok=True)

            filename = f"{nombre}_maquetacion.pdf"
            print(f"[editor_visual] Maquetación generada: '{filename}' ({len(pdf_bytes):,} bytes)")
            return (
                dcc.send_bytes(pdf_bytes, filename=filename),
                False,
                dmc.Notification(
                    title="Maquetación generada",
                    message=f"'{filename}' listo para descargar.",
                    color="green", action="show",
                ),
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return dash.no_update, False, dmc.Notification(
                title="Error al generar PDF",
                message=str(e)[:300],
                color="red", action="show",
            )

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
            guardar_plantilla(editor_state)
            nombre = editor_state.get("configuracion", {}).get("nombre_plantilla", "")
            print(f"[editor_visual] Plantilla '{nombre}' guardada OK")
            return dmc.Notification(
                title="Guardado",
                message=f"Plantilla '{nombre}' guardada correctamente.",
                color="green",
                action="show"
            )
        except PlantillaInvalida as e:
            return dmc.Notification(
                title="Error",
                message=str(e),
                color="red",
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



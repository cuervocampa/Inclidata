import json
import os
import dash
from dash.exceptions import PreventUpdate
from dash import dcc, html, Input, Output, State, callback_context, ALL, no_update
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_mantine_components import (
    Paper, Text, Group, Button, Alert, Space, Divider, Select, NumberInput, Checkbox,
    Card, CardSection, Stack, Grid)
from dash_iconify import DashIconify
import base64
from utils.diccionarios import importadores
from utils.funciones_comunes import calcular_incrementos, buscar_referencia, buscar_ant_referencia, evaluar_umbrales
from utils.funciones_graficos import importar_graficos
from utils.funciones_importar import import_RST, import_Sisgeo, import_soil_dux, insertar_camp, es_fecha_isoformat, \
    default_value, parse_alarm_val
import pprint
from datetime import datetime
import re


# Ruta al directorio 'data'
data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))

if not os.path.exists(data_path):
    raise FileNotFoundError(f"El directorio {data_path} no existe. Verifica la estructura de tu proyecto.")


# ── Constantes de estilo para contenedores de pasos ─────────────────────────
_STEP_BASE = {
    'background': 'var(--id-card-bg)',
    'border': '1px solid var(--id-border)',
    'borderRadius': '8px',
    'padding': '1.25rem',
    'marginBottom': '1rem',
}
STEP_ACTIVE_STYLE    = {**_STEP_BASE}
STEP_COMPLETED_STYLE = {**_STEP_BASE, 'opacity': 0.55, 'pointerEvents': 'none'}
STEP_HIDDEN_STYLE    = {'display': 'none'}
STEP_ENTERING_STYLE  = {**_STEP_BASE, 'animation': 'import-step-fadein 0.35s ease'}


def _step_title(icon, label):
    """Encabezado visual de cada bloque de paso."""
    return Group([
        DashIconify(icon=icon, width=16, style={"color": "var(--id-primary)"}),
        Text(label, fw=600, size="sm", style={"color": "var(--id-text-primary)"}),
    ], gap="xs", mb=12)


# ── Helpers para tabla de campañas existentes ────────────────────────────────

def _fmt_correction(val):
    """'✓' if truthy, '✗' if falsy, '—' if None (not set)."""
    if val is None:
        return '—'
    return '✓' if val else '✗'


def _build_campaign_rows(tubo):
    """Extract per-campaign summary rows from tubo JSON for display table."""
    skip_keys = {'info', 'umbrales'}
    rows = []
    for fecha in sorted(tubo.keys()):
        if fecha in skip_keys:
            continue
        data = tubo[fecha]
        ci  = data.get('campaign_info', {})
        ir  = data.get('info_readout', {})
        raw = data.get('raw', [])

        # Equipment serial — first token before comma (RST format)
        probe = str(ir.get('probe_serial', ir.get('reel_serial', '—')))
        if ',' in probe:
            probe = probe.split(',')[0].strip()
        if not probe or probe in ('None', ''):
            probe = '—'

        # Profundidad máxima desde raw
        if raw:
            prof = f"{max((r.get('depth', 0) for r in raw), default=0):.1f}"
        else:
            prof = '—'

        rows.append({
            'fecha':       fecha,
            'referencia':  ci.get('reference', False),
            'activa':      ci.get('active', True),
            'cuarentena':  ci.get('quarentine', False),
            'importador':  ci.get('importador', '—') or '—',
            'equipo':      probe,
            'profundidad': prof,
            'bias':        _fmt_correction(data.get('bias')),
            'spike':       _fmt_correction(data.get('spike')),
        })
    return rows


def _render_campaign_table(rows, search=''):
    """Render a dmc.Table with campaign rows, filtered by search string."""
    if search:
        sl = search.lower()
        rows = [r for r in rows if
                sl in r['fecha'].lower() or
                sl in r['importador'].lower() or
                sl in r['equipo'].lower()]

    if not rows:
        return dmc.Text(
            "No se encontraron campañas.",
            c="dimmed", size="sm", ta="center", mt=12
        )

    return dmc.Table(
        striped=True,
        highlightOnHover=True,
        withTableBorder=True,
        withColumnBorders=False,
        stickyHeader=True,
        fz='xs',
        data={
            'head': [
                'Fecha', 'Ref.', 'Activa', 'Cuar.',
                'Importador', 'Equipo', 'Prof. (m)', 'Bias', 'Spike'
            ],
            'body': [
                [
                    r['fecha'],
                    'Sí' if r['referencia'] else 'No',
                    'Sí' if r['activa']     else 'No',
                    'Sí' if r['cuarentena'] else 'No',
                    r['importador'],
                    r['equipo'],
                    r['profundidad'],
                    r['bias'],
                    r['spike'],
                ]
                for r in rows
            ],
        },
        style={'minWidth': '560px'},
    )


# ── Layout ───────────────────────────────────────────────────────────────────
def layout():
    return html.Div([
        # Stores de datos
        dcc.Store(id='tubo', storage_type='memory'),
        dcc.Store(id='camp_added', storage_type='memory'),
        dcc.Store(id='campanas-tabla-store', storage_type='memory'),

        # ── Stepper horizontal fijado en el top ───────────────────────────────
        html.Div([
            dmc.Stepper(
                id='import-stepper',
                active=0,
                orientation='horizontal',
                allowNextStepsSelect=False,
                children=[
                    dmc.StepperStep(label="Archivo base",   description="JSON del inclinómetro"),
                    dmc.StepperStep(label="Configurar",     description="Importador y parámetros"),
                    dmc.StepperStep(label="Subir archivos", description="Archivos de medición"),
                    dmc.StepperStep(label="Revisar",        description="Verificar campañas"),
                    dmc.StepperStep(label="Confirmar",      description="Importación completada"),
                ]
            )
        ], className='import-stepper-header'),

        # ── Área de contenido acumulativa ─────────────────────────────────────
        html.Div([

            # Paso 1 — siempre visible
            html.Div([
                _step_title("lucide:file-search", "Paso 1 · Seleccionar archivo base"),
                html.Div([
                    Select(
                        id='import-file-dropdown',
                        data=[
                            {"label": file, "value": file}
                            for file in sorted(os.listdir(data_path))
                            if os.path.isfile(os.path.join(data_path, file))
                        ],
                        placeholder="Selecciona un archivo...",
                        style={'width': '100%', 'marginBottom': '15px'},
                        searchable=True,
                        clearable=True,
                        leftSection=DashIconify(icon="lucide:file-search", width=14)
                    ),
                    Button(
                        "Continuar",
                        id='import-first-button',
                        className='id-btn',
                        color="blue",
                        leftSection=DashIconify(icon="lucide:arrow-right", width=14)
                    ),
                ], style={'maxWidth': '600px'}),
                html.Div(id='step-1-error', style={'marginTop': '0.75rem'}),
            ], id='step-container-1', style=STEP_ACTIVE_STYLE),

            # Paso 2 — oculto inicialmente
            html.Div([
                _step_title("lucide:settings-2", "Paso 2 · Configurar importador"),
                html.Div(id='step-2-error', style={'marginBottom': '0.5rem'}),
                html.Div(id='import-step-2'),
            ], id='step-container-2', style=STEP_HIDDEN_STYLE),

            # Paso 3 — oculto inicialmente
            html.Div([
                _step_title("lucide:upload-cloud", "Paso 3 · Subir archivos de campaña"),
                html.Div(id='step-3-error', style={'marginBottom': '0.5rem'}),
                html.Div(id='import-step-3'),
            ], id='step-container-3', style=STEP_HIDDEN_STYLE),

            # Paso 4 — oculto inicialmente
            html.Div([
                _step_title("lucide:table-2", "Paso 4 · Revisar campañas"),
                html.Div(id='step-4-error', style={'marginBottom': '0.5rem'}),
                html.Div(id='import-step-4'),
            ], id='step-container-4', style=STEP_HIDDEN_STYLE),

            # Paso 5 — oculto inicialmente
            html.Div([
                _step_title("lucide:check-circle-2", "Paso 5 · Confirmación"),
                html.Div(id='import-step-5'),
            ], id='step-container-5', style=STEP_HIDDEN_STYLE),

        ], style={'paddingTop': '110px'}),
    ])


# ── Callbacks ─────────────────────────────────────────────────────────────────
def register_callbacks(app):

    # ── Paso 1 → 2 ───────────────────────────────────────────────────────────
    @app.callback(
        [Output('step-1-error', 'children'),
         Output('import-step-2', 'children'),
         Output('tubo', 'data'),
         Output('import-stepper', 'active'),
         Output('step-container-1', 'style'),
         Output('step-container-2', 'style'),
         Output('campanas-tabla-store', 'data')],
        Input('import-first-button', 'n_clicks'),
        State('import-file-dropdown', 'value'),
        prevent_initial_call=True
    )
    def display_dropdown_input(n_clicks, selected_files):
        print(f"Paso 1 — Continuar: {n_clicks}, archivo: {selected_files}")

        if not (n_clicks and n_clicks > 0):
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update

        if not selected_files:
            err = Alert(
                title="Selecciona un archivo",
                c="yellow",
                icon=DashIconify(icon="lucide:alert-triangle"),
                children=[Text("Debes seleccionar un archivo JSON antes de continuar.")]
            )
            return err, no_update, no_update, no_update, no_update, no_update, no_update

        # Leer y validar el JSON
        file_path = os.path.join(data_path, selected_files)
        try:
            with open(file_path, 'r') as json_file:
                tempo_tubo = json.load(json_file)
        except json.JSONDecodeError:
            err = Alert(
                title="Error de formato JSON",
                c="red",
                icon=DashIconify(icon="lucide:alert-circle"),
                children=[Text("Error al leer el archivo JSON: formato incorrecto. Corrige el archivo antes de continuar.")]
            )
            return err, no_update, no_update, no_update, no_update, no_update, no_update

        campaign_info = default_value(tempo_tubo)
        if not campaign_info:
            err = Alert(
                title="Error de información",
                c="red",
                icon=DashIconify(icon="lucide:alert-circle"),
                children=[Text("No se pudo obtener información de la campaña seleccionada.")]
            )
            return err, no_update, no_update, no_update, no_update, no_update, no_update

        default_importador_value = campaign_info.get('importador', None)
        last_index_0 = campaign_info.get('index_0', None)

        # ── Construir filas para la tabla de campañas ────────────────────────
        campaign_rows = _build_campaign_rows(tempo_tubo)

        # ── Info compacta del inclinómetro ───────────────────────────────────
        def _info_row(label, value):
            return dmc.Grid([
                dmc.GridCol(span=5, children=[
                    Text(label + ':', size='xs', c='dimmed')
                ]),
                dmc.GridCol(span=7, children=[
                    Text(str(value) if value is not None else '—', size='xs', fw=500)
                ]),
            ], gutter='xs', mb=2)

        latest_camp = campaign_info.get('latest_campaign')
        latest_ref  = campaign_info.get('latest_reference')

        info_card = html.Div([
            Group([
                DashIconify(icon="lucide:info", width=14, style={"color": "var(--id-primary)"}),
                Text("Inclinómetro", fw=600, size="sm", style={"color": "var(--id-text-primary)"}),
            ], gap="xs", mb=8),
            _info_row('Cota 1000',     campaign_info.get('cota_1000', '—')),
            _info_row('Adquisición',   campaign_info.get('adquisicion', '—')),
            _info_row('Disposición',   campaign_info.get('disposicion', '—')),
            _info_row('Sentido',       campaign_info.get('sentido_calculo', '—')),
            _info_row('Últ. campaña',  latest_camp or 'Ninguna'),
            _info_row('Últ. referencia', latest_ref or 'Ninguna'),
            _info_row('Campañas',      len(campaign_rows)),
        ], className='id-card', style={'padding': '0.75rem', 'marginBottom': '1rem'})

        # ── Columna izquierda: info + controles ──────────────────────────────
        left_col = dmc.GridCol(span=5, children=[
            info_card,

            Select(
                id='import-importador',
                data=[{"label": key, "value": value} for key, value in importadores.items()],
                placeholder='Selecciona un importador',
                value=default_importador_value if default_importador_value in importadores.values() else None,
                style={'marginBottom': '15px'},
                searchable=True,
                clearable=False,
                leftSection=DashIconify(icon="lucide:database", width=14)
            ),

            dmc.Grid(
                children=[
                    dmc.GridCol(span=5, children=[
                        dmc.NumberInput(
                            id='index_0-input',
                            value=last_index_0 if last_index_0 is not None else 1000,
                            label="Index_0",
                            description="Posición de referencia absoluta",
                            min=0,
                            step=1,
                            style={"width": "100%"}
                        )
                    ]),
                    dmc.GridCol(span=7, children=[
                        dmc.Text(
                            "Modifica si hay cambios respecto a la última campaña (por defecto 1000)",
                            c="dimmed", size="xs", mt=25
                        )
                    ])
                ],
                gutter="xs", mb=15
            ),

            Checkbox(
                id="importar-checkbox-reference",
                label="Es referencia",
                checked=campaign_info.get('latest_campaign') is None,
                mb=15
            ),

            Button(
                "Continuar",
                id='import-second-button',
                className='id-btn',
                color="blue",
                leftSection=DashIconify(icon="lucide:arrow-right", width=14)
            )
        ])

        # ── Columna derecha: tabla de campañas existentes ────────────────────
        right_col = dmc.GridCol(span=7, children=[
            html.Div([
                Group([
                    DashIconify(icon="lucide:table-2", width=14, style={"color": "var(--id-primary)"}),
                    Text("Campañas existentes", fw=600, size="sm",
                         style={"color": "var(--id-text-primary)"}),
                ], gap="xs", mb=8),

                dmc.TextInput(
                    id='import-campaign-search',
                    placeholder='Buscar por fecha, importador o equipo...',
                    leftSection=DashIconify(icon="lucide:search", width=14),
                    size='sm',
                    mb=8,
                ),

                dmc.ScrollArea(
                    h=360,
                    type='auto',
                    children=html.Div(
                        id='import-campaign-table-wrapper',
                        children=_render_campaign_table(campaign_rows)
                    )
                ),

                Text(
                    f"{len(campaign_rows)} campaña{'s' if len(campaign_rows) != 1 else ''}",
                    size='xs', c='dimmed', mt=6
                ),
            ], className='id-card', style={'padding': '0.75rem'})
        ])

        step2_content = dmc.Grid([left_col, right_col], gutter='md')

        return (
            None,
            step2_content,
            tempo_tubo,
            1,
            STEP_COMPLETED_STYLE,
            STEP_ENTERING_STYLE,
            campaign_rows,
        )

    # ── Filtro de búsqueda en tabla de campañas ───────────────────────────────
    @app.callback(
        Output('import-campaign-table-wrapper', 'children'),
        Input('import-campaign-search', 'value'),
        State('campanas-tabla-store', 'data'),
        prevent_initial_call=True
    )
    def filter_campaign_table(search, rows):
        if rows is None:
            raise PreventUpdate
        return _render_campaign_table(rows, search or '')

    # ── Paso 2 → 3 ───────────────────────────────────────────────────────────
    @app.callback(
        [Output('step-2-error', 'children'),
         Output('import-step-3', 'children', allow_duplicate=True),
         Output('import-stepper', 'active', allow_duplicate=True),
         Output('step-container-2', 'style', allow_duplicate=True),
         Output('step-container-3', 'style')],
        Input('import-second-button', 'n_clicks'),
        State('import-importador', 'value'),
        prevent_initial_call=True
    )
    def display_upload_section(n_clicks, importador_value):
        print(f"Paso 2 — Continuar: {n_clicks}")

        if not (n_clicks and n_clicks > 0):
            return no_update, no_update, no_update, no_update, no_update

        if not importador_value:
            err = Alert(
                title="Importador no seleccionado",
                c="yellow",
                icon=DashIconify(icon="lucide:alert-triangle"),
                children=[Text("Selecciona un importador para continuar")]
            )
            return err, no_update, no_update, no_update, no_update

        step3_content = html.Div([
            dcc.Upload(
                id='import-file-upload',
                multiple=True,
                className='id-upload-area',
                style={'width': '100%', 'marginBottom': '1rem'},
                children=html.Div(
                    [
                        DashIconify(icon="lucide:upload", width=20, className='id-upload-icon'),
                        html.Span("Arrastra archivos aquí o haz clic para seleccionar",
                                  className='id-upload-text')
                    ],
                    style={'display': 'flex', 'alignItems': 'center',
                           'justifyContent': 'center', 'height': '100%', 'gap': '0.5rem'}
                )
            ),

            html.Div([
                Group([
                    DashIconify(icon="lucide:files", width=16, style={"color": "var(--id-primary)"}),
                    Text("Archivos seleccionados", fw=600, size="sm",
                         style={"color": "var(--id-text-primary)"}),
                ], gap="xs", mb=8),
                html.Div(id='import-uploaded-files-list', style={'minHeight': '40px'})
            ], className='id-card', style={'padding': '0.75rem', 'marginBottom': '1rem'}),

            Button(
                "Continuar",
                id='import-third-button',
                className='id-btn',
                color="blue",
                leftSection=DashIconify(icon="lucide:arrow-right", width=14),
                mt=5
            )
        ], style={'maxWidth': '700px'})

        return None, step3_content, 2, STEP_COMPLETED_STYLE, STEP_ENTERING_STYLE

    # ── Actualizar lista de archivos subidos ─────────────────────────────────
    @app.callback(
        Output('import-uploaded-files-list', 'children'),
        Input('import-file-upload', 'filename')
    )
    def update_uploaded_files_list(uploaded_files):
        if uploaded_files:
            if isinstance(uploaded_files, str):
                uploaded_files = [uploaded_files]
            file_items = [
                Group([
                    DashIconify(icon="lucide:file", width=14, style={"color": "var(--id-primary)"}),
                    Text(file, size="sm"),
                ], gap="xs", mb=4)
                for file in uploaded_files
            ]
            return Stack(children=file_items)
        return Text("No se han seleccionado archivos.", c="dimmed", fs="italic", size="sm")

    # ── Paso 3 → 4 ───────────────────────────────────────────────────────────
    @app.callback(
        [Output('step-3-error', 'children'),
         Output('import-step-4', 'children'),
         Output('camp_added', 'data'),
         Output('import-stepper', 'active', allow_duplicate=True),
         Output('step-container-3', 'style', allow_duplicate=True),
         Output('step-container-4', 'style')],
        Input('import-third-button', 'n_clicks'),
        [State('import-importador', 'value'),
         State('import-file-upload', 'contents'),
         State('import-file-upload', 'filename'),
         State('tubo', 'data'),
         State('index_0-input', 'value'),
         State('importar-checkbox-reference', 'checked')],
        prevent_initial_call=True
    )
    def execute_function_third(n_clicks, selected_value, uploaded_contents, uploaded_files,
                               tubo, index_0, checkbox_ref_value):
        print(f"Paso 3 — Continuar: {n_clicks}, importador: {selected_value}")

        if not (n_clicks and n_clicks > 0):
            return no_update, no_update, no_update, no_update, no_update, no_update

        if uploaded_contents is None:
            err = Alert(
                title="Error de carga",
                c="red",
                icon=DashIconify(icon="lucide:alert-circle"),
                children=[Text("No se ha seleccionado ningún archivo para procesar.")]
            )
            return err, no_update, None, no_update, no_update, no_update

        try:
            if isinstance(uploaded_files, str):
                uploaded_files = [uploaded_files]
            if isinstance(uploaded_contents, str):
                uploaded_contents = [uploaded_contents]

            input_files = []
            for content, filename in zip(uploaded_contents, uploaded_files):
                content_type, content_string = content.split(',')
                decoded = base64.b64decode(content_string)
                lines = decoded.decode('utf-8').splitlines()
                input_files.append({'filename': filename, 'lines': lines})

            cota = tubo['info']['cota_1000']

            try:
                index_0 = int(float(index_0)) if index_0 is not None else 1000
            except (ValueError, TypeError):
                index_0 = 1000

            if selected_value == 'RST':
                result = import_RST(input_files, index_0, cota)
            elif selected_value == 'Sisgeo':
                result = import_Sisgeo(input_files, index_0, cota)
            elif selected_value == 'Soil (dux)':
                result = import_soil_dux(input_files, index_0, cota)
            else:
                err = Alert(
                    title="Importador no reconocido",
                    c="red",
                    icon=DashIconify(icon="lucide:alert-circle"),
                    children=[Text("El importador seleccionado no está implementado.")]
                )
                return err, no_update, None, no_update, no_update, no_update

            # ── Advertencia de fechas duplicadas ─────────────────────────────
            existing_dates = set(k for k in tubo.keys() if es_fecha_isoformat(k)) if tubo else set()
            new_dates      = [k for k in result.keys() if es_fecha_isoformat(k)]
            duplicate_dates = sorted([d for d in new_dates if d in existing_dates])

            dup_warning = None
            if duplicate_dates:
                shown = duplicate_dates[:8]
                extra = len(duplicate_dates) - len(shown)
                items = [dmc.ListItem(d) for d in shown]
                if extra > 0:
                    items.append(dmc.ListItem(f"… y {extra} más"))
                dup_warning = Alert(
                    title="Advertencia: fechas duplicadas",
                    c="yellow",
                    icon=DashIconify(icon="lucide:alert-triangle"),
                    children=[
                        Text(
                            "Las siguientes campañas ya existen en el archivo y serán sobrescritas:",
                            size="sm", mb=6
                        ),
                        dmc.List(size="sm", children=items),
                    ],
                    mb=10,
                )

            # Validación cronológica
            try:
                earliest_ref_date = None
                if tubo:
                    for date_str, camp_data in tubo.items():
                        if date_str in ["info", "umbrales"]:
                            continue
                        if isinstance(camp_data, dict) and camp_data.get('campaign_info', {}).get('reference', False):
                            try:
                                dt = datetime.fromisoformat(date_str)
                                if earliest_ref_date is None or dt < earliest_ref_date:
                                    earliest_ref_date = dt
                            except ValueError:
                                pass

                if earliest_ref_date:
                    conflict_dates = []
                    for new_date_str in result.keys():
                        if new_date_str in ["info", "umbrales"]:
                            continue
                        try:
                            new_dt = datetime.fromisoformat(new_date_str)
                            if new_dt < earliest_ref_date:
                                conflict_dates.append(new_date_str)
                        except ValueError:
                            pass

                    if conflict_dates:
                        conflict_dates.sort()
                        err = Alert(
                            title="Error Cronológico Crítico",
                            c="red",
                            icon=DashIconify(icon="lucide:timer-off"),
                            children=[
                                Text("No se permite importar campañas anteriores a la primera referencia existente.", fw=700),
                                Text(f"Primera referencia actual: {earliest_ref_date.isoformat()}", size="sm", mt=5),
                                Divider(my=10),
                                Text("Campañas conflictivas detectadas:", fw=500),
                                dmc.List(size="sm", children=[dmc.ListItem(d) for d in conflict_dates[:5]]),
                                Text("... y otras más." if len(conflict_dates) > 5 else "", size="xs", c="dimmed")
                            ]
                        )
                        return err, no_update, None, no_update, no_update, no_update
            except Exception as e:
                print(f"Error en validación de fechas: {e}")

            fechas_agg = sorted([clave for clave in result.keys() if es_fecha_isoformat(clave)])

            for campaign_date, campaign_data in result.items():
                if campaign_date != "info":
                    if tubo is None:
                        tubo = {}
                    else:
                        tubo[campaign_date] = campaign_data

            print('Fechas agregadas: ', fechas_agg)

            if not fechas_agg:
                raise Exception("No se encontraron datos válidos (fechas) tras importar. Compruebe que el archivo coincide con el formato esperado y que se detectaron las cabeceras correctamente.")

            primera_fecha = fechas_agg[0]
            for fecha in fechas_agg:
                tubo[fecha]["campaign_info"]["active"] = True
                if checkbox_ref_value == True and fecha == primera_fecha:
                    tubo[fecha]["campaign_info"]["reference"] = True
                else:
                    tubo[fecha]["campaign_info"]["reference"] = False

                fecha_referencia = buscar_referencia(tubo, fecha)
                calcular_incrementos(tubo, fecha, fecha_referencia)

            camp_added = {clave: tubo[clave] for clave in fechas_agg if clave in tubo}

            umbrales = tubo.get('umbrales', {'deformadas': {}, 'valores': []})
            if umbrales.get('deformadas') and umbrales.get('valores'):
                eval_por_fecha = {fecha: evaluar_umbrales(tubo[fecha]['calc'], umbrales) for fecha in fechas_agg}
            else:
                eval_por_fecha = {fecha: None for fecha in fechas_agg}

            print("eval_por_fecha:", eval_por_fecha)

            graphs = importar_graficos(tubo, fechas_agg)

            # Cabecera de la tabla de configuración
            header = Grid([
                dmc.GridCol(span=2, children=[Text("Fecha Original", fw=700, size="sm")]),
                dmc.GridCol(span=1, children=[Text("Fecha TunnelData", fw=700, size="sm")]),
                dmc.GridCol(span=1, children=[Text("Hora TunnelData", fw=700, size="sm")]),
                dmc.GridCol(span=1, children=[Text("Activa", fw=700, size="sm")]),
                dmc.GridCol(span=1, children=[Text("Cuarentena", fw=700, size="sm")]),
                dmc.GridCol(span=4, children=[Text("Alarm", fw=700, size="sm")]),
                dmc.GridCol(span=2, children=[Text("Subir Campaña", fw=700, size="sm")])
            ], gutter="xs", mb=10, ta="center")

            campaign_config_rows = []
            for i, fecha in enumerate(fechas_agg):
                campaign_config_rows.append(
                    Grid([
                        dmc.GridCol(span=2, children=[Text(fecha, size="sm", fw=500)]),
                        dmc.GridCol(span=1, children=[
                            dmc.TextInput(
                                id={'type': 'date-input', 'index': i},
                                value=datetime.strptime(fecha, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d"),
                                placeholder="YYYY-MM-DD", size="sm", style={"width": "100%"}
                            )
                        ]),
                        dmc.GridCol(span=1, children=[
                            dmc.TimeInput(
                                id={'type': 'time-input', 'index': i},
                                value=datetime.strptime(fecha.split('T')[1], "%H:%M:%S").strftime("%H:%M:%S"),
                                size="sm", style={"width": "100%"}
                            )
                        ]),
                        dmc.GridCol(span=1, children=[
                            Select(
                                id={'type': 'active-dropdown', 'index': i},
                                data=[{"label": "Activo", "value": "true"},
                                      {"label": "Inactivo", "value": "false"}],
                                value="true", size="sm", style={"width": "100%"}
                            )
                        ]),
                        dmc.GridCol(span=1, children=[
                            Select(
                                id={'type': 'quarentine-dropdown', 'index': i},
                                data=[{"label": "En cuarentena", "value": "true"},
                                      {"label": "Normal", "value": "false"}],
                                value="false", size="sm", style={"width": "100%"}
                            )
                        ]),
                        dmc.GridCol(span=4, children=[
                            dmc.TextInput(
                                id={'type': 'alarm-input', 'index': i},
                                value=str(eval_por_fecha[fecha]),
                                size="sm", style={"width": "100%"}, disabled=True
                            )
                        ]),
                        dmc.GridCol(span=2, children=[
                            Select(
                                id={'type': 'upload-dropdown', 'index': i},
                                data=[{"label": "Subir", "value": "true"},
                                      {"label": "Ignorar", "value": "false"}],
                                value="true", size="sm", style={"width": "100%"}
                            )
                        ])
                    ], gutter="xs", mb=10, ta="center")
                )

            step4_content = html.Div([
                html.Div([
                    Group([
                        DashIconify(icon="lucide:bar-chart-3", width=16, style={"color": "var(--id-primary)"}),
                        Text("Visualización de campañas", fw=600, size="sm",
                             style={"color": "var(--id-text-primary)"}),
                    ], gap="xs", mb=8),
                    graphs
                ], className='id-graph-card', style={'marginBottom': '1rem'}),

                html.Div([
                    Group([
                        DashIconify(icon="lucide:table", width=16, style={"color": "var(--id-primary)"}),
                        Text("Configuración de campañas", fw=600, size="sm",
                             style={"color": "var(--id-text-primary)"}),
                    ], gap="xs", mb=8),
                    Divider(mb=10),
                    header,
                    Divider(mb=10),
                    Stack(children=campaign_config_rows)
                ], className='id-card', style={'padding': '1rem', 'marginBottom': '1rem'}),

                Button(
                    "Guardar campañas",
                    id='import-fourth-button',
                    className='id-btn',
                    color="blue",
                    leftSection=DashIconify(icon="lucide:save", width=14),
                    mt=5
                )
            ])

            return dup_warning, step4_content, camp_added, 3, STEP_COMPLETED_STYLE, STEP_ENTERING_STYLE

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error: {type(e).__name__}: {e}")
            res_e = str(e) if str(e) else "Error desconocido o mensaje vacío"
            err = Alert(
                title="Error al procesar archivos",
                c="red",
                icon=DashIconify(icon="lucide:alert-circle"),
                children=[
                    Text(f"Tipo: {type(e).__name__}", fw=700),
                    Text(f"Detalle: {res_e}", mb=10),
                    Text("Traza del error:", size="sm", fw=500),
                    dmc.Code(error_trace, block=True, style={"maxHeight": "200px", "overflowY": "auto"})
                ]
            )
            return err, no_update, None, no_update, no_update, no_update

    # ── Paso 4 → 5: Guardar campañas ─────────────────────────────────────────
    @app.callback(
        [Output('step-4-error', 'children'),
         Output('import-step-5', 'children'),
         Output('import-stepper', 'active', allow_duplicate=True),
         Output('step-container-4', 'style', allow_duplicate=True),
         Output('step-container-5', 'style')],
        Input('import-fourth-button', 'n_clicks'),
        [State({'type': 'date-input', 'index': ALL}, 'value'),
         State({'type': 'time-input', 'index': ALL}, 'value'),
         State({'type': 'active-dropdown', 'index': ALL}, 'value'),
         State({'type': 'quarentine-dropdown', 'index': ALL}, 'value'),
         State({'type': 'upload-dropdown', 'index': ALL}, 'value'),
         State({'type': 'alarm-input', 'index': ALL}, 'value'),
         State('camp_added', 'data'),
         State('import-file-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_campaign_settings(
        n_clicks,
        dates, times, active_values, quarentine_values,
        upload_values, alarm_values,
        camp_added, selected_filename
    ):
        print(f"Paso 4 — Guardar campañas: {n_clicks}")

        if n_clicks is None:
            raise PreventUpdate

        if not (n_clicks and dates and times and camp_added):
            return no_update, no_update, no_update, no_update, no_update

        # Reformatear fechas
        camp_added_formateado = {}
        for i, fecha in enumerate(camp_added.keys()):
            try:
                fecha_hora_str = f"{dates[i]}T{times[i]}"
                fecha_hora = datetime.strptime(fecha_hora_str, "%Y-%m-%dT%H:%M:%S")
                fecha_hora_fmt = fecha_hora.strftime("%Y-%m-%dT%H:%M:%S")
                camp_added_formateado[fecha_hora_fmt] = camp_added[fecha]
            except Exception as e:
                err = Alert(
                    title="Error al formatear fechas",
                    c="red",
                    icon=DashIconify(icon="lucide:alert-circle"),
                    children=[Text(f"Error al procesar la fecha {fecha}: {e}")]
                )
                return err, no_update, no_update, no_update, no_update

        # Asignar alarmas
        for i, fecha in enumerate(camp_added_formateado.keys()):
            camp_added_formateado[fecha]['campaign_info']['alarm'] = parse_alarm_val(alarm_values[i])

        # Opciones de active/quarentine/upload
        opciones_seleccionadas = {}
        for i, fecha in enumerate(camp_added_formateado.keys()):
            opciones_seleccionadas[fecha] = {
                'Active':     active_values[i] == "true",
                'Quarentine': quarentine_values[i] == "true",
                'Upload':     upload_values[i] == "true"
            }

        fechas_agg = [f for f, opt in opciones_seleccionadas.items() if opt['Upload']]

        for fecha, opt in opciones_seleccionadas.items():
            if fecha in camp_added_formateado and 'campaign_info' in camp_added_formateado[fecha]:
                ci = camp_added_formateado[fecha]['campaign_info']
                ci['active']     = opt['Active']
                ci['quarentine'] = opt['Quarentine']
            else:
                print(f"Error: No se encontró 'campaign_info' para {fecha}.")

        insertar_camp(camp_added_formateado, fechas_agg, selected_filename, data_path)

        success_content = html.Div([
            Group([
                DashIconify(icon="lucide:check-circle", width=24,
                            style={"color": "var(--id-primary)"}),
                dmc.Title("Importación completada", order=4,
                          style={"color": "var(--id-text-primary)"}),
            ], gap="xs", mb=12),
            Text(f"Se han guardado {len(fechas_agg)} campaña(s) correctamente.",
                 size="sm", mb=8),
            html.Pre(
                "Fechas guardadas:\n" + "\n".join(fechas_agg),
                style={'whiteSpace': 'pre-wrap', 'fontSize': '0.85rem',
                       'color': 'var(--id-text-muted)', 'margin': 0}
            )
        ])

        return None, success_content, 4, STEP_COMPLETED_STYLE, STEP_ENTERING_STYLE

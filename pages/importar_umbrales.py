# pages/importar_umbrales.py
from dash import html, dcc, callback
from dash.dependencies import Input, Output, State, ALL
import dash_mantine_components as dmc
import base64, json, io
import pandas as pd
import numpy as np
from pathlib import Path
from dash_iconify import DashIconify
from dash_mantine_components import NumberInput


def round_numbers_in_dict(obj, decimals=2):
    if isinstance(obj, dict):
        return {k: round_numbers_in_dict(v, decimals) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [round_numbers_in_dict(item, decimals) for item in obj]
    elif isinstance(obj, (float, np.float64, np.float32)):
        return round(float(obj), decimals)
    else:
        return obj


def layout():
    return dmc.MantineProvider(
        theme={"colorScheme": "light"},
        children=dmc.Container([
            dmc.Title("Insertar Umbrales en JSON", order=1, mb=20),
            dcc.Store(id='i-stored-json-data', storage_type='memory'),
            dcc.Store(id='i-json-data-umbrales', storage_type='memory'),
            dcc.Store(id='i-original-json-path', storage_type='memory'),
            dcc.Store(id='i-deformadas-list', storage_type='memory'),

            # Paso 1: Cargar JSON
            dmc.Paper(p="md", withBorder=True, shadow="sm", radius="md", mb=20, children=[
                dmc.Text("Paso 1: Carga el archivo JSON base", fw=500, mb=10),
                dcc.Upload(
                    id='upload-json',
                    children=dmc.Button(
                        "Seleccionar archivo JSON",
                        leftSection=DashIconify(icon="fa-solid:file-upload"),
                        variant="outline"
                    ),
                    multiple=False, accept='.json'
                ),
                dmc.Alert(id='i-json-info', title="", c="blue", hide=True)
            ]),

            # Paso 2: Cargar Excel
            dmc.Paper(p="md", withBorder=True, shadow="sm", radius="md", mb=20, children=[
                dmc.Text("Paso 2: Carga el archivo Excel con umbrales", fw=500, mb=10),
                dcc.Upload(
                    id='i-upload-excel',  # control disabled at button level
                    children=dmc.Button(
                        "Seleccionar archivo Excel",
                        id='i-excel-upload-button',
                        leftSection=DashIconify(icon="fa6-solid:file-excel"),
                        variant="outline",
                        disabled=True  # starts disabled until JSON loaded
                    ),
                    multiple=False, accept='.xlsx'
                ),
                dmc.Alert(id='i-excel-info', title="", c="blue", hide=True)
            ]),

            # Paso 3: Configurar tipo de flanco y renombrar cada deformada
            dmc.Paper(p="md", withBorder=True, shadow="sm", radius="md", mb=20, children=[
                dmc.Text("Paso 3: Configurar propiedades de cada deformada", fw=500, mb=10),
                dmc.LoadingOverlay(
                    html.Div(id='i-flancos-container', children=[])
                ),
                dmc.Button(
                    "Confirmar configuración", id='i-confirm-flancos', disabled=True,
                    c='blue', leftSection=DashIconify(icon="mdi:check-bold"), mt=10
                ),
                dmc.Alert(id='i-flancos-status', title="", c="blue", hide=True)
            ]),

            # Paso 4: Guardar cambios
            dmc.Paper(p="md", withBorder=True, shadow="sm", radius="md", mb=20, children=[
                dmc.Text("Paso 4: Guardar cambios en el archivo JSON original", fw=500, mb=10),
                dmc.Button(
                    "Guardar cambios", id='i-save-json', disabled=True,
                    c='blue', leftSection=DashIconify(icon="fa6-solid:floppy-disk")
                ),
                dmc.Alert(id='i-save-status', title="", c="blue", hide=True)
            ]),

            # Vista previa
            dmc.Paper(p="md", withBorder=True, shadow="sm", radius="md", children=[
                dmc.Text("Vista previa de umbrales", fw=500, mb=10),
                dmc.Divider(mb=10),
                dmc.LoadingOverlay(
                    dmc.Prism(id='i-umbrales-output', language="json", withLineNumbers=True, noCopy=True, children="{}")
                )
            ])
        ], fluid=True)
    )


def register_callbacks(app):
    @callback(
        [Output('i-json-info', 'children'), Output('i-json-info', 'hide'),
         Output('i-excel-upload-button', 'disabled'),
         Output('i-stored-json-data', 'data'), Output('i-original-json-path', 'data')],
        Input('upload-json', 'contents'), State('upload-json', 'filename'),
        prevent_initial_call=True
    )
    def load_json(contents, filename):
        if not contents:
            return "", True, True, {}, ""
        try:
            _, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            datos_json = json.loads(decoded)
            if not isinstance(datos_json, dict):
                raise ValueError("El archivo JSON no contiene un objeto válido")
            return (f"Archivo JSON cargado: {filename}", False, False, datos_json, filename)
        except Exception as e:
            return (f"Error: {e}", False, True, {}, "")

    @callback(
        [Output('i-excel-info', 'children'), Output('i-excel-info', 'hide'),
         Output('i-flancos-container', 'children'), Output('i-confirm-flancos', 'disabled'),
         Output('i-deformadas-list', 'data')],
        Input('i-upload-excel', 'contents'), State('i-upload-excel', 'filename'),
        prevent_initial_call=True
    )
    def load_excel(contents, filename):
        if not contents:
            return "", True, [], True, []
        try:
            _, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            df = pd.read_excel(io.BytesIO(decoded))
            if df.empty:
                raise ValueError("El archivo Excel está vacío")
            deformadas = [col for col in df.columns if col not in ["cota_abs", "depth"]]
            if not deformadas:
                raise ValueError("No se encontraron columnas de deformadas en el Excel")

            # Paleta de colores modernos
            colores_modernos = [
                {"value": "#3B82F6", "label": "Azul"},
                {"value": "#EF4444", "label": "Rojo"},
                {"value": "#10B981", "label": "Verde"},
                {"value": "#F59E0B", "label": "Ámbar"},
                {"value": "#8B5CF6", "label": "Violeta"},
                {"value": "#EC4899", "label": "Rosa"},
                {"value": "#06B6D4", "label": "Cian"},
                {"value": "#84CC16", "label": "Lima"},
                {"value": "#F97316", "label": "Naranja"},
                {"value": "#6B7280", "label": "Gris"},
                {"value": "#DC2626", "label": "Rojo Oscuro"},
                {"value": "#059669", "label": "Verde Esmeralda"},
                {"value": "#7C3AED", "label": "Púrpura"},
                {"value": "#DB2777", "label": "Rosa Intenso"},
                {"value": "#0891B2", "label": "Azul Petróleo"}
            ]

            # Tipos de línea
            tipos_linea = [
                {"value": "solid", "label": "Sólida"},
                {"value": "dashed", "label": "Discontinua"},
                {"value": "dotted", "label": "Punteada"},
                {"value": "dashdot", "label": "Punto-raya"},
                {"value": "longdash", "label": "Raya larga"},
                {"value": "longdashdot", "label": "Raya larga-punto"}
            ]

            selectors = []
            for i, deformada in enumerate(deformadas):
                # Asignar color por defecto basado en el índice, línea discontinua por defecto
                color_default = colores_modernos[i % len(colores_modernos)]["value"]
                tipo_linea_default = "dashed"  # Por defecto línea discontinua

                selectors.append(
                    dmc.Paper(
                        p="md",
                        withBorder=True,
                        shadow="xs",
                        radius="sm",
                        mb=15,
                        children=[
                            dmc.Text(f"Configuración para: {deformada}", fw=600, size="sm", mb=10),
                            dmc.SimpleGrid(
                                cols=3,
                                gap="1",
                                breakpoints=[
                                    {"maxWidth": 1200, "cols": 2, "spacing": "sm"},
                                    {"maxWidth": 768, "cols": 1, "spacing": "xs"}
                                ],
                                children=[
                                    # Primera fila
                                    dmc.TextInput(
                                        id={"type": "deformada-name-input", "index": deformada},
                                        label="Nuevo nombre:",
                                        value=deformada,
                                        size="sm"
                                    ),
                                    dmc.Select(
                                        id={"type": "flanco-selector", "index": deformada},
                                        label="Tipo de flanco:",
                                        data=[
                                            {"value": "flanco_positivo", "label": "Flanco Positivo"},
                                            {"value": "flanco_negativo", "label": "Flanco Negativo"},
                                            {"value": "sin_flanco", "label": "Sin Flanco"}
                                        ],
                                        value="flanco_positivo",
                                        size="sm"
                                    ),
                                    NumberInput(
                                        id={"type": "nivel-input", "index": deformada},
                                        label="Nivel:",
                                        min=0,
                                        step=1,
                                        value=0,
                                        size="sm"
                                    ),
                                    # Segunda fila
                                    dmc.Select(
                                        id={"type": "color-selector", "index": deformada},
                                        label="Color:",
                                        data=colores_modernos,
                                        value=color_default,
                                        size="sm"
                                    ),
                                    dmc.Select(
                                        id={"type": "linetype-selector", "index": deformada},
                                        label="Tipo de línea:",
                                        data=tipos_linea,
                                        value=tipo_linea_default,
                                        size="sm"
                                    ),
                                    # Espacio vacío para mantener la grid
                                    html.Div()
                                ]
                            )
                        ]
                    )
                )

            return (
            f"Excel procesado: {filename}. Se encontraron {len(deformadas)} deformadas.", False, selectors, False,
            deformadas)
        except Exception as e:
            return (f"Error: {e}", False, [], True, [])

    @callback(
        [Output('i-flancos-status', 'children'),
         Output('i-flancos-status', 'hide'),
         Output('i-umbrales-output', 'children'),
         Output('i-save-json', 'disabled'),
         Output('i-json-data-umbrales', 'data')],
        Input('i-confirm-flancos', 'n_clicks'),
        State({'type': 'deformada-name-input', 'index': ALL}, 'value'),
        State({'type': 'flanco-selector', 'index': ALL}, 'value'),
        State({'type': 'nivel-input', 'index': ALL}, 'value'),
        State({'type': 'color-selector', 'index': ALL}, 'value'),
        State({'type': 'linetype-selector', 'index': ALL}, 'value'),
        State('i-stored-json-data', 'data'),
        State('i-deformadas-list', 'data'),
        State('i-upload-excel', 'contents'),
        prevent_initial_call=True
    )
    def process_flancos(n_clicks, name_values, flanco_values, nivel_values, color_values, linetype_values, datos_json,
                        deformadas, excel_contents):
        if not n_clicks or not excel_contents:
            return "", True, "{}", True, {}
        try:
            _, content_string = excel_contents.split(',')
            decoded = base64.b64decode(content_string)
            df = pd.read_excel(io.BytesIO(decoded))
            for col in df.select_dtypes(include=['float64', 'float32']).columns:
                df[col] = df[col].round(2)
            registros = df.to_dict(orient='records')
            registros_redondeados = round_numbers_in_dict(registros)
            name_map = {deformadas[i]: name_values[i] for i in range(len(deformadas))}

            # Construir dict de deformadas con todas las propiedades
            deformadas_dict = {
                name_map[deformadas[i]]: {
                    "flanco": flanco_values[i],
                    "nivel": nivel_values[i],
                    "color": color_values[i],
                    "tipo_linea": linetype_values[i]
                }
                for i in range(len(deformadas))
            }

            registros_renombrados = [
                {name_map.get(k, k): v for k, v in rec.items()} for rec in registros_redondeados
            ]

            # Montar objeto umbrales
            umbrales = {
                "deformadas": deformadas_dict,
                "valores": registros_renombrados
            }
            datos_json_mod = datos_json.copy()
            datos_json_mod['umbrales'] = umbrales

            return ("Configuración confirmada con éxito", False, json.dumps(umbrales, indent=2), False, datos_json_mod)
        except Exception as e:
            return (f"Error: {e}", False, "{}", True, {})

    @callback(
        [Output('i-save-status', 'children'), Output('i-save-status', 'color'), Output('i-save-status', 'hide')],
        Input('i-save-json', 'n_clicks'), State('i-json-data-umbrales', 'data'), State('i-original-json-path', 'data'),
        prevent_initial_call=True
    )
    def save_json(n_clicks, datos_json, filename):
        if not filename:
            return ("Error: No se encontró la ruta del archivo", "red", False)
        try:
            ruta_script = Path(__file__).resolve().parent.parent
            ruta_data = ruta_script / "data"
            ruta_json = ruta_data / filename
            with open(ruta_json, 'w', encoding='utf-8') as f:
                json.dump(datos_json, f, ensure_ascii=False, indent=4,
                          default=lambda o: o.item() if hasattr(o, 'item') else str(o))
            return ("Archivo JSON guardado con éxito", "green", False)
        except Exception as e:
            return (f"Error al guardar: {e}", "red", False)
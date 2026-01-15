from dash import html, dcc, callback
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
import base64, json, io
import pandas as pd
import numpy as np
from pathlib import Path
from dash_iconify import DashIconify



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

            # Paso 1: Cargar JSON
            dmc.Paper(p="md", withBorder=True, shadow="sm", radius="md", mb=20, children=[
                dmc.Text("Paso 1: Carga el archivo JSON base", fw=500, mb=10),
                dcc.Upload(
                    id='upload-json',
                    children=dmc.Button("Seleccionar archivo JSON", leftSection=DashIconify(icon="fa-solid:file-upload"), variant="outline"),
                    multiple=False, accept='.json',
                ),
                dmc.Alert(id='i-json-info', title="", c="blue", hide=True),
            ]),

            # Paso 2: Cargar Excel
            dmc.Paper(p="md", withBorder=True, shadow="sm", radius="md", mb=20, children=[
                dmc.Text("Paso 2: Carga el archivo Excel con umbrales", fw=500, mb=10),
                dcc.Upload(
                    id='i-upload-excel',
                    children=dmc.Button("Seleccionar archivo Excel", leftSection=DashIconify(icon="fa6-solid:file-excel"),
                                        variant="outline", disabled=True, id="i-excel-upload-button"),
                    multiple=False, accept='.xlsx',
                ),
                dmc.Alert(id='i-excel-info', title="", c="blue", hide=True),
            ]),

            # Paso 3: Guardar cambios
            dmc.Paper(p="md", withBorder=True, shadow="sm", radius="md", mb=20, children=[
                dmc.Text("Paso 3: Guardar cambios en el archivo JSON original", fw=500, mb=10),
                dmc.Button("Guardar cambios", id='i-save-json', disabled=True, c='blue', leftSection=DashIconify(icon="fa6-solid:floppy-disk")),
                dmc.Alert(id='i-save-status', title="", c="blue", hide=True),
            ]),

            # Vista previa
            dmc.Paper(p="md", withBorder=True, shadow="sm", radius="md", children=[
                dmc.Text("Vista previa de umbrales", fw=500, mb=10),
                dmc.Divider(mb=10),
                dmc.LoadingOverlay(
                    dmc.Prism(id='i-umbrales-output', language="json", withLineNumbers=True, noCopy=True, children="{}"),
                ),
            ]),
        ], fluid=True)
    )


def register_callbacks(app):

    @callback(
        [Output('i-json-info', 'children'),
         Output('i-json-info', 'hide'),
         Output('i-excel-upload-button', 'disabled'),
         Output('i-stored-json-data', 'data'),
         Output('i-original-json-path', 'data')],
        Input('upload-json', 'contents'),
        [State('upload-json', 'filename')],
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

            return f"Archivo JSON cargado: {filename}", False, False, datos_json, filename
        except Exception as e:
            return f"Error: {str(e)}", False, True, {}, ""


    @callback(
        [Output('i-excel-info', 'children'),
         Output('i-excel-info', 'hide'),
         Output('i-umbrales-output', 'children'),
         Output('i-save-json', 'disabled'),
         Output('i-json-data-umbrales', 'data')],
        Input('i-upload-excel', 'contents'),
        [State('i-upload-excel', 'filename'),
         State('i-stored-json-data', 'data')],
        prevent_initial_call=True
    )
    def load_excel(contents, filename,datos_json):
        if not contents:
            return "", True, "{}", True, {}

        try:
            _, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            df = pd.read_excel(io.BytesIO(decoded))

            if df.empty:
                raise ValueError("El archivo Excel está vacío")

            for col in df.select_dtypes(include=['float64', 'float32']).columns:
                df[col] = df[col].round(2)

            umbrales_data = df.to_dict(orient='records')
            umbrales_rounded = round_numbers_in_dict(umbrales_data)

            deformadas = [key for key in umbrales_data[0].keys() if
                          key not in ["cota_abs", "depth"]] if umbrales_data else []

            umbrales = {
                "deformadas": deformadas,
                "valores": umbrales_rounded
            }

            datos_json_mod = datos_json.copy()
            datos_json_mod['umbrales'] = umbrales

            return f"Excel procesado: {filename}", False, json.dumps(umbrales,indent=2), False, datos_json_mod
        except Exception as e:
            return f"Error: {str(e)}", False, "{}", True, {}

    @callback(
        [Output('i-save-status', 'children'),
         Output('i-save-status', 'color'),
         Output('i-save-status', 'hide')],
        Input('i-save-json', 'n_clicks'),
        [State('i-json-data-umbrales', 'data'),
         State('i-original-json-path', 'data')],
        prevent_initial_call=True
    )
    def save_json(n_clicks, datos_json, filename):
        if not filename:
            return "Error: No se encontró la ruta del archivo", "red", False
        try:
            # Definir la ruta del archivo JSON original
            ruta_script = Path(__file__).resolve().parent.parent  # Sube un nivel desde 'pages'
            ruta_data = ruta_script / "data"  # Ahora apunta a 'IncliData/data'
            ruta_json = ruta_data / filename

            # Sobrescribir el archivo JSON
            with open(ruta_json, "w", encoding="utf-8") as f:
                json.dump(datos_json, f, ensure_ascii=False, indent=4,
                          default=lambda o: o.item() if hasattr(o, 'item') else o)

            return "Archivo JSON guardado con éxito", "green", False
        except Exception as e:
            return f"Error al guardar: {str(e)}", "red", False

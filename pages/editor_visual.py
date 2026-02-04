import dash
from dash import html, dcc, callback, Input, Output
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import dash_component_editor as dce
import json



layout = dmc.MantineProvider(
    theme={"colorScheme": "light"},
    children=html.Div([
        # Header simplificado
        dmc.Paper(
            p="md", 
            withBorder=True, 
            shadow="sm", 
            style={"marginBottom": "20px"},
            children=dmc.Group([
                 dmc.Title("Editor Visual (Lovable Engine)", order=2),
                 dmc.Group([
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
                     )
                 ])
            ], justify="space-between")
        ),
        
        # Componente React
        html.Div(
            dce.Editor(
                id='visual-editor',
                data={
                    # Datos iniciales opcionales
                    "paginas": {
                        "1": {
                            "elementos": {},
                            "configuracion": { "orientacion": "portrait" }
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
        html.Div(id="save-feedback-visual")
    ], style={"padding": "20px", "height": "100vh", "backgroundColor": "#f8f9fa"})
)

@callback(
    Output("save-feedback-visual", "children"),
    Input("btn-save-visual", "n_clicks"),
    Input("visual-editor", "value"), # Recibe el estado completo del editor
    prevent_initial_call=True
)
def save_template(n_clicks, editor_state):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
        
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "btn-save-visual":
        if editor_state:
            # Aquí iría la lógica de guardado en disco
            # Por ahora solo mostramos un mensaje
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

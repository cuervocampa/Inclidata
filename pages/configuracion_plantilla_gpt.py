#/pages/configuracion_plantilla_gpt.py
from dash import html, dcc, callback, callback_context
from dash.dependencies import Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm


def layout():
    return dmc.MantineProvider(
        theme={"colorScheme": "light"},
        children=dmc.Container([
            dmc.Title("Edición de Plantilla", order=1, mb=20),
            # Store general para elementos en canvas
            dcc.Store(id='ep-stored-elements', storage_type='memory'),
            # Store específico para líneas
            dcc.Store(id='store-lineas', storage_type='memory'),

            # Configuración superior
            dmc.Paper(p='md', withBorder=True, shadow='sm', radius='md', mb=20, children=[
                dmc.Grid([
                    dmc.Col([dmc.TextInput(id='ep-template-name', label='Nombre de la plantilla:', placeholder='Nombre...')], span=6),
                    dmc.Col([dmc.TextInput(id='ep-inclinometer', label='Inclinómetro:', placeholder='ID...')], span=6),
                ], gutter='md'),
                dmc.Space(h=10),
                dmc.RadioGroup(
                    id='ep-orientation', label='Orientación:', name='orientation', value='vertical',
                    wrapperProps={'style': {'display': 'flex', 'gap': '1rem'}},
                    children=[dmc.Radio(value='vertical', label='Vertical'), dmc.Radio(value='horizontal', label='Horizontal')]
                ),
                dmc.Space(h=10),
                dmc.Group([
                    dmc.Button("Añadir línea", id='add-line', leftSection=DashIconify(icon='mdi:vector-line'), variant='outline'),
                    dmc.Button("Añadir rectángulo", id='add-rect', leftSection=DashIconify(icon='mdi:square-outline'), variant='outline'),
                    dmc.Button("Añadir gráfico", id='add-graph', leftSection=DashIconify(icon='mdi:chart-line'), variant='outline'),
                    dmc.Button("Añadir tabla", id='add-table', leftSection=DashIconify(icon='mdi:table'), variant='outline'),
                    dmc.Button("Imprimir PDF", id='print-pdf', leftSection=DashIconify(icon='mdi:printer'), c='blue')
                ], spacing='md')
            ]),

            # Canvas con reglas adaptables
            html.Div(id='canvas-container', style={'position': 'relative', 'width': '100%', 'maxWidth': '800px', 'margin': 'auto'}, children=[
                html.Div(id='h-ruler', style={'position': 'absolute', 'top': 0, 'left': 0, 'right': 0, 'height': '20px', 'backgroundColor': '#f5f5f5', 'borderBottom': '1px solid #000'}),
                html.Div(id='v-ruler', style={'position': 'absolute', 'top': 0, 'bottom': 0, 'left': 0, 'width': '20px', 'backgroundColor': '#f5f5f5', 'borderRight': '1px solid #000'}),
                html.Div(id='template-canvas', style={'aspectRatio': '210 / 297', 'width': '100%', 'border': '1px solid #000', 'backgroundColor': '#fff', 'position': 'relative', 'top': '20px', 'left': '20px'})
            ]),

            # Drawer para configuración de Línea con formulario y almacenamiento
            dmc.Drawer(
                id='drawer-line', title='Configurar Línea', opened=False,
                position='top', size='xl', children=[
                    dmc.Stack([
                        dcc.Input(id='line-x1', type='number', placeholder='X1', style={'width': '100%'}),
                        dcc.Input(id='line-y1', type='number', placeholder='Y1', style={'width': '100%'}),
                        dcc.Input(id='line-x2', type='number', placeholder='X2', style={'width': '100%'}),
                        dcc.Input(id='line-y2', type='number', placeholder='Y2', style={'width': '100%'}),
                        dcc.Input(id='line-grosor', type='number', placeholder='Grosor', style={'width': '100%'}),
                        dcc.Input(id='line-color', type='text', placeholder='Color (hex o nombre)', style={'width': '100%'}),
                        dcc.Input(id='line-nombre', type='text', placeholder='Nombre de la línea', style={'width': '100%'}),
                        html.Button("Crear línea", id='btn-create-line', style={'marginTop': '10px'})
                    ], spacing='sm')
                ]
            ),

            # Drawers para otros elementos
            dmc.Drawer(id='drawer-rect', title='Configurar Rectángulo', opened=False, size='xl', position='top'),
            dmc.Drawer(id='drawer-graph', title='Configurar Gráfico', opened=False, size='xl', position='top'),
            dmc.Drawer(id='drawer-table', title='Configurar Tabla', opened=False, size='xl', position='top'),

            dcc.Download(id='download-pdf')
        ], fluid=True)
    )


def register_callbacks(app):
    @callback(
        Output('template-canvas', 'style'),
        Output('h-ruler', 'children'),
        Output('v-ruler', 'children'),
        Input('ep-orientation', 'value')
    )
    def update_orientation(orientation):
        if orientation == 'horizontal':
            width_cm, height_cm = 29.7, 21.0
        else:
            width_cm, height_cm = 21.0, 29.7
        canvas_style = {
            'aspectRatio': '297 / 210' if orientation == 'horizontal' else '210 / 297',
            'width': '100%', 'border': '1px solid #000', 'backgroundColor': '#fff',
            'position': 'relative', 'top': '20px', 'left': '20px'
        }
        # Reglas
        h_marks = []
        for i in range(int(width_cm) + 1):
            h_marks.append(html.Div(style={'position': 'absolute', 'left': f'{(i/width_cm)*100:.2f}%', 'height': '10px', 'borderLeft': '1px solid #000', 'top': 0}))
        for i in range(0, int(width_cm) + 1, 5):
            h_marks.append(html.Div(f"{i}cm", style={'position': 'absolute', 'left': f'{(i/width_cm)*100:.2f}%', 'top': '10px', 'fontSize': '8px'}))
        v_marks = []
        for i in range(int(height_cm) + 1):
            v_marks.append(html.Div(style={'position': 'absolute', 'top': f'{(i/height_cm)*100:.2f}%', 'width': '10px', 'borderTop': '1px solid #000', 'left': 0}))
        for i in range(0, int(height_cm) + 1, 5):
            v_marks.append(html.Div(f"{i}cm", style={'position': 'absolute', 'top': f'{(i/height_cm)*100:.2f}%', 'left': '10px', 'fontSize': '8px'}))
        return canvas_style, h_marks, v_marks

    # Toggle drawers
    @callback(Output('drawer-line', 'opened'), [Input('add-line', 'n_clicks'), Input('drawer-line', 'onClose')], prevent_initial_call=True)
    def toggle_line(n_add, on_close): ctx = callback_context.triggered[0]['prop_id']; return ctx.startswith('add-line')
    @callback(Output('drawer-rect', 'opened'), [Input('add-rect', 'n_clicks'), Input('drawer-rect', 'onClose')], prevent_initial_call=True)
    def toggle_rect(n_add, on_close): ctx = callback_context.triggered[0]['prop_id']; return ctx.startswith('add-rect')
    @callback(Output('drawer-graph', 'opened'), [Input('add-graph', 'n_clicks'), Input('drawer-graph', 'onClose')], prevent_initial_call=True)
    def toggle_graph(n_add, on_close): ctx = callback_context.triggered[0]['prop_id']; return ctx.startswith('add-graph')
    @callback(Output('drawer-table', 'opened'), [Input('add-table', 'n_clicks'), Input('drawer-table', 'onClose')], prevent_initial_call=True)
    def toggle_table(n_add, on_close): ctx = callback_context.triggered[0]['prop_id']; return ctx.startswith('add-table')

    # Crear línea: almacenar en store-lineas
    @callback(
        Output('store-lineas', 'data'),
        Input('btn-create-line', 'n_clicks'),
        State('store-lineas', 'data'),
        State('line-x1', 'value'), State('line-y1', 'value'),
        State('line-x2', 'value'), State('line-y2', 'value'),
        State('line-grosor', 'value'), State('line-color', 'value'), State('line-nombre', 'value'),
        prevent_initial_call=True
    )
    def create_line(n, existing, x1, y1, x2, y2, grosor, color, nombre):
        lines = existing or []
        lines.append({ 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'grosor': grosor, 'color': color, 'nombre': nombre })
        return lines

    @callback(Output('download-pdf', 'data'), Input('print-pdf', 'n_clicks'), State('ep-template-name', 'value'), State('ep-inclinometer', 'value'), State('store-lineas', 'data'), prevent_initial_call=True)
    def generate_pdf(n_clicks, tpl_name, inclinometer, lines):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        # TODO: renderizar líneas y otros elementos en PDF
        c.showPage(); c.save(); buffer.seek(0)
        return dcc.send_bytes(buffer.read(), filename=f"{tpl_name or 'plantilla'}.pdf")

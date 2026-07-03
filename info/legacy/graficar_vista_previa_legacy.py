"""
info/legacy/graficar_vista_previa_legacy.py
============================================
Callbacks de Vista Previa archivados desde pages/graficar.py.

Eran dos mini-motores de renderizado basados en ReportLab / matplotlib:
  - imprimir_pdf:              renderizaba una "vista previa" del informe via ReportLab.
  - generar_vista_previa_graficos: generaba un HTML con los gráficos embebidos como base64.

Ambos usaban el contrato antiguo de los scripts (función con firma data+parámetros → img base64).
Los scripts HTML de Maketator tienen otro contrato (Playwright → PDF), por lo que son incompatibles.

También se archiva:
  - actualizar_script_en_json: helper huérfano (no tenía @app.callback ni caller).
  - clientside_callback de descargar-vista-previa-html: ligado exclusivamente a generar_vista_previa_graficos.

Archivado en: 2026-07-03 (consolidación motor HTML, tag v2.0-motor-html)
Recuperable en: tag v1.0-pre-poda-reportlab o rama archive/full-editor-reportlab
"""

# ---------------------------------------------------------------------------
# Bloque 1 — imprimir_pdf (decorador comentado)
# ---------------------------------------------------------------------------
# Vista Previa deshabilitada: era un mini-motor ReportLab; los scripts HTML de Maketator
# tienen otro contrato (punto de entrada, datos y salida). Reactivable en el futuro via render del motor.
# @app.callback(
#     Output("contenedor-grafico-informe", "children", allow_duplicate=True),
#     [Input("btn-generar-preview", "n_clicks")],
#     [State("fechas_multiselect", "value"),
#      State("fechas_multiselect", "data"),
#      State("slider_fecha_tooltip", "children"),
#      State("graficar-tubo", "data"),
#      State("alto_graficos_slider", "value"),
#      State("color_scheme_selector", "value"),
#      State("escala_graficos_desplazamiento", "value"),
#      State("escala_graficos_incremento", "value"),
#      State("valor_positivo_desplazamiento", "value"),
#      State("valor_negativo_desplazamiento", "value"),
#      State("valor_positivo_incremento", "value"),
#      State("valor_negativo_incremento", "value"),
#      State("leyenda_umbrales", "data"),
#      State("unidades_eje", "value"),
#      State("orden", "value"),
#      State("date_range_picker", "start_date"),
#      State("date_range_picker", "end_date"),
#      State({"type": "script-grafico", "pagina": ALL, "elemento": ALL}, "value"),
#      State({"type": "param-grafico", "pagina": ALL, "elemento": ALL, "param": ALL}, "value"),
#      State({"type": "param-grafico", "pagina": ALL, "elemento": ALL, "param": ALL}, "id"),
#      State("plantilla-json-data", "data"),
#      State("total_camp", "value"),
#      State("ultimas_camp", "value"),
#      State("cadencia_dias", "value")],
#     prevent_initial_call=True
# )
def imprimir_pdf(n_clicks, fechas_seleccionadas, fechas_colores, slider_value,
                 data, alto_graficos, color_scheme, escala_desplazamiento,
                 escala_incremento, valor_positivo_desplazamiento,
                 valor_negativo_desplazamiento, valor_positivo_incremento,
                 valor_negativo_incremento, leyenda_umbrales, eje, orden,
                 fecha_inicial, fecha_final, scripts, param_values, param_ids, plantilla_json,
                 total_camp, ultimas_camp, cadencia_dias):
    """
    Genera una vista previa del gráfico para el informe PDF mostrando los parámetros que se utilizarán.
    """
    if not n_clicks or not plantilla_json:
        return []

    resultados = []

    fecha_slider = slider_value.split(": ")[1] if ": " in slider_value else (
        fechas_seleccionadas[0] if fechas_seleccionadas else None
    )

    current_values = cargar_valores_actuales(
        data, eje, orden, color_scheme, escala_desplazamiento, escala_incremento,
        valor_positivo_desplazamiento, valor_negativo_desplazamiento,
        valor_positivo_incremento, valor_negativo_incremento,
        fecha_inicial, fecha_final, total_camp, ultimas_camp, cadencia_dias,
        leyenda_umbrales
    )

    graficos_encontrados = 0

    if "paginas" in plantilla_json:
        for num_pagina, pagina in plantilla_json.get("paginas", {}).items():
            for nombre_elemento, elemento in pagina.get("elementos", {}).items():
                if elemento.get("tipo") == "grafico":
                    graficos_encontrados += 1

                    configuracion = elemento.get("configuracion", {})
                    script_valor = configuracion.get("script", "")
                    parametros_json = configuracion.get("parametros", {})

                    parametros_procesados = {}
                    for param, valor in parametros_json.items():
                        if isinstance(valor, str) and valor == "$CURRENT" and param in current_values:
                            parametros_procesados[param] = current_values[param]
                        else:
                            parametros_procesados[param] = valor

                    parametros_especificos = {}
                    for i, param_id in enumerate(param_ids):
                        if (param_id["pagina"] == num_pagina and
                                param_id["elemento"] == nombre_elemento):
                            param_nombre = param_id["param"]
                            valor = param_values[i]
                            parametros_especificos[param_nombre] = valor

                    parametros_default = current_values
                    parametros_combinados = {**parametros_default, **parametros_procesados,
                                             **parametros_especificos}

                    if script_valor.endswith('.py'):
                        script_valor_sin_extension = script_valor[:-3]
                    else:
                        script_valor_sin_extension = script_valor

                    parametros_especificos = {}
                    for i, param_id in enumerate(param_ids):
                        if (param_id["pagina"] == num_pagina and
                                param_id["elemento"] == nombre_elemento):
                            param_nombre = param_id["param"]
                            valor = param_values[i]
                            try:
                                if valor.lower() == "true":
                                    valor = True
                                elif valor.lower() == "false":
                                    valor = False
                                elif valor.replace('.', '', 1).isdigit() or (
                                        valor[0] == '-' and valor[1:].replace('.', '', 1).isdigit()):
                                    valor = float(valor)
                                    if valor.is_integer():
                                        valor = int(valor)
                            except (AttributeError, ValueError):
                                pass
                            parametros_especificos[param_nombre] = valor

                    parametros_combinados = {**parametros_default, **parametros_json, **parametros_especificos}

                    import os
                    from pathlib import Path
                    script_path = str(Path("biblioteca_graficos") / f"{script_valor_sin_extension}.py")
                    script_existe = os.path.exists(script_path)

                    resultados.append(
                        dmc.Alert(
                            "La vista previa se ha generado y abierta en una nueva pestaña.",
                            title="Vista previa generada",
                            c="green",
                            icon=[DashIconify(icon="mdi:check-circle")],
                            style={"marginBottom": "20px"}
                        )
                    )

    if graficos_encontrados == 0:
        resultados.append(
            dmc.Alert(
                "No se encontraron gráficos configurables en esta plantilla",
                c="yellow",
                title="Sin gráficos"
            )
        )

    return resultados


# ---------------------------------------------------------------------------
# Helper huérfano — actualizar_script_en_json
# (no tenía @app.callback, no tenía callers; adjunto por contexto)
# ---------------------------------------------------------------------------

def actualizar_script_en_json(valores_script, ids_script, plantilla_json):
    """
    Actualiza el script en el JSON de la plantilla cuando se cambia el selector.
    """
    if not ctx.triggered or not plantilla_json:
        return dash.no_update

    plantilla_modificada = copy.deepcopy(plantilla_json)

    for i, valor in enumerate(valores_script):
        pagina = ids_script[i]["pagina"]
        elemento = ids_script[i]["elemento"]

        if valor and not valor.endswith('.py'):
            valor = f"{valor}.py"

        try:
            plantilla_modificada["paginas"][pagina]["elementos"][elemento]["configuracion"]["script"] = valor
        except KeyError:
            print(f"Error: No se pudo actualizar el script para pagina={pagina}, elemento={elemento}")

    return plantilla_modificada


# ---------------------------------------------------------------------------
# Bloque 2 — generar_vista_previa_graficos (decorador comentado)
# ---------------------------------------------------------------------------
# @app.callback(
#     Output("descargar-vista-previa-html", "data"),
#     Input("btn-generar-preview", "n_clicks"),
#     [State("fechas_multiselect", "value"),
#      State("fechas_multiselect", "data"),
#      State("slider_fecha_tooltip", "children"),
#      State("graficar-tubo", "data"),
#      State("alto_graficos_slider", "value"),
#      State("color_scheme_selector", "value"),
#      State("escala_graficos_desplazamiento", "value"),
#      State("escala_graficos_incremento", "value"),
#      State("valor_positivo_desplazamiento", "value"),
#      State("valor_negativo_desplazamiento", "value"),
#      State("valor_positivo_incremento", "value"),
#      State("valor_negativo_incremento", "value"),
#      State("leyenda_umbrales", "data"),
#      State("unidades_eje", "value"),
#      State("orden", "value"),
#      State("date_range_picker", "start_date"),
#      State("date_range_picker", "end_date"),
#      State({"type": "script-grafico", "pagina": ALL, "elemento": ALL}, "value"),
#      State({"type": "param-grafico", "pagina": ALL, "elemento": ALL, "param": ALL}, "value"),
#      State({"type": "param-grafico", "pagina": ALL, "elemento": ALL, "param": ALL}, "id"),
#      State("plantilla-json-data", "data"),
#      State("total_camp", "value"),
#      State("ultimas_camp", "value"),
#      State("cadencia_dias", "value")],
#     prevent_initial_call=True
# )
def generar_vista_previa_graficos(n_clicks, fechas_seleccionadas, fechas_colores, slider_value,
                                  data, alto_graficos, color_scheme, escala_desplazamiento,
                                  escala_incremento, valor_positivo_desplazamiento,
                                  valor_negativo_desplazamiento, valor_positivo_incremento,
                                  valor_negativo_incremento, leyenda_umbrales, eje, orden,
                                  fecha_inicial, fecha_final, scripts, param_values, param_ids, plantilla_json,
                                  total_camp, ultimas_camp, cadencia_dias):
    """
    Genera una vista previa de todos los gráficos en la plantilla y los muestra en una nueva ventana.
    """
    if not n_clicks or not plantilla_json:
        return dash.no_update

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from datetime import datetime
    import importlib.util
    import json as _json
    import os
    from pathlib import Path

    fecha_slider = slider_value.split(": ")[1] if ": " in slider_value else (
        fechas_seleccionadas[0] if fechas_seleccionadas else None
    )

    current_values = cargar_valores_actuales(
        data, eje, orden, color_scheme, escala_desplazamiento, escala_incremento,
        valor_positivo_desplazamiento, valor_negativo_desplazamiento,
        valor_positivo_incremento, valor_negativo_incremento,
        fecha_inicial, fecha_final, total_camp, ultimas_camp, cadencia_dias,
        leyenda_umbrales
    )

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Vista Previa de Gráficos - {fecha_slider}</title>
    <meta charset="UTF-8">
</head>
<body>
    <h1>Vista Previa de Gráficos</h1>
    <p>Fecha: <strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong></p>
"""

    graficos_encontrados = 0

    if "paginas" in plantilla_json:
        for num_pagina, pagina in plantilla_json.get("paginas", {}).items():
            for nombre_elemento, elemento in pagina.get("elementos", {}).items():
                if elemento.get("tipo") == "grafico":
                    graficos_encontrados += 1
                    configuracion = elemento.get("configuracion", {})
                    script_valor = configuracion.get("script", "")
                    parametros_json_elem = configuracion.get("parametros", {})

                    parametros_procesados = {}
                    for param, valor in parametros_json_elem.items():
                        if isinstance(valor, str) and valor == "$CURRENT" and param in current_values:
                            parametros_procesados[param] = current_values[param]
                        else:
                            parametros_procesados[param] = valor

                    parametros_especificos = {}
                    for i, param_id in enumerate(param_ids):
                        if (param_id["pagina"] == num_pagina and
                                param_id["elemento"] == nombre_elemento):
                            param_nombre = param_id["param"]
                            valor = param_values[i]
                            try:
                                if isinstance(valor, str):
                                    if valor.lower() == "true":
                                        valor = True
                                    elif valor.lower() == "false":
                                        valor = False
                                    elif valor.replace('.', '', 1).isdigit() or (
                                            valor[0] == '-' and valor[1:].replace('.', '', 1).isdigit()):
                                        valor = float(valor)
                                        if valor.is_integer():
                                            valor = int(valor)
                            except (AttributeError, ValueError):
                                pass
                            parametros_especificos[param_nombre] = valor

                    parametros_combinados = {**current_values, **parametros_procesados, **parametros_especificos}

                    script_valor_sin_extension = script_valor[:-3] if script_valor.endswith('.py') else script_valor
                    script_path = str(Path("biblioteca_graficos") / f"{script_valor_sin_extension}.py")
                    script_fn_name = Path(script_valor_sin_extension).name

                    html_content += f"<h2>{nombre_elemento} (p.{num_pagina}) — script: {script_valor}</h2>"

                    if os.path.exists(script_path):
                        try:
                            import sys
                            script_dir = os.path.dirname(script_path)
                            sys.path.insert(0, script_dir)
                            try:
                                spec = importlib.util.spec_from_file_location(script_fn_name, script_path)
                                if spec:
                                    mod = importlib.util.module_from_spec(spec)
                                    spec.loader.exec_module(mod)
                                    if hasattr(mod, script_fn_name):
                                        data_url = getattr(mod, script_fn_name)(data, parametros_combinados)
                                        if data_url and data_url.startswith("data:image"):
                                            html_content += f'<img src="{data_url}" />'
                            finally:
                                if script_dir in sys.path:
                                    sys.path.remove(script_dir)
                        except Exception as exc:
                            import traceback
                            html_content += f"<pre>Error: {traceback.format_exc()}</pre>"
                    else:
                        html_content += f"<p>Script no encontrado: {script_path}</p>"

    if graficos_encontrados == 0:
        html_content += "<p>No se encontraron gráficos configurables.</p>"

    html_content += "</body></html>"

    return {
        'content': html_content,
        'filename': 'vista_previa_graficos.html',
        'type': 'text/html',
        'base64': False
    }


# ---------------------------------------------------------------------------
# clientside_callback — abrir vista previa en nueva pestaña
# (ligado exclusivamente a generar_vista_previa_graficos)
# ---------------------------------------------------------------------------
# app.clientside_callback(
#     """
#     function(data) {
#         if (data && data.filename === 'vista_previa_graficos.html') {
#             var blob = new Blob([data.content], {type: 'text/html'});
#             var url = URL.createObjectURL(blob);
#             window.open(url, '_blank');
#         }
#         return '';
#     }
#     """,
#     Output("debug-output-dummy", "children", allow_duplicate=True),
#     Input("descargar-vista-previa-html", "data"),
#     prevent_initial_call=True
# )

# Estudio: IncliData como Impresor Independiente de PDF
_Fecha: 2026-07-01 | READ-ONLY study — no code was modified_

---

## Resumen Ejecutivo

IncliData posee **dos capas claramente separables**: (a) un editor visual React (`dash_component_editor`) con toda la lógica de creación/edición de plantillas y (b) un motor de renderizado PDF (`report_engine.py` → `pdf_generator.py`) que opera de forma autónoma sobre un JSON de plantilla y un dict de contexto. La eliminación del editor afecta a `pages/editor_plantilla.py`, `pages/editor_visual.py`, `biblioteca_grupos/`, `funciones_grupos.py` y el bundle JS compilado. El motor de renderizado (`generate_report_pdf` en `report_engine.py:462`) **no tiene dependencias directas del editor**; lee una plantilla desde disco y produce un PDF sin pasar por ningún estado React. La única obra pendiente antes de poder operar como impresor independiente es definir el mecanismo de ingesta de la plantilla JSON externa (Maketator → disco local) y el mapeo del contexto de ejecución.

---

## 1. Superficie de Creación/Edición (ELIMINAR)

| Archivo | Función / Callback | Línea | Solo-creación / Mixto |
|---|---|---|---|
| `app.py` | `render_page_content` — registra ruta `/editor_plantilla` y `/editor-visual` | 172–182 | Mixto (routing) |
| `app.py` | `editor_plantilla.register_callbacks(app)` | 196 | Solo-creación |
| `app.py` | `editor_visual.register_callbacks(app)` | 197 | Solo-creación |
| `app.py` | NAV_ITEMS — entradas "Editor plantillas" y "Editor Visual" en sidebar | 92–93 | Solo-creación (UI) |
| `pages/editor_plantilla.py` | `layout()` (re-exportada de `editor_plantilla_layout.py`) | 38 | Solo-creación |
| `pages/editor_plantilla.py` | `register_callbacks(app)` + todos sus callbacks internos | 40–fin | Solo-creación |
| `pages/editor_visual.py` | `layout()` — renderiza `dce.Editor` React + modales guardar/cargar/grupo | 87–376 | Solo-creación |
| `pages/editor_visual.py` | `abrir_modal_cargar_plantilla` | 387–388 | Solo-creación |
| `pages/editor_visual.py` | `cargar_plantilla` (callback, no la función de `template_service`) | 399–433 | Mixto (carga + estado editor) |
| `pages/editor_visual.py` | `importar_grupo_archivo` | 436–475 | Solo-creación |
| `pages/editor_visual.py` | `exportar_grupo` | 478–511 | Solo-creación |
| `pages/editor_visual.py` | `abrir_modal_guardar_plantilla` | 513–527 | Solo-creación |
| `pages/editor_visual.py` | `confirmar_guardar_plantilla` — llama a `guardar_plantilla()` | 530–559 | Solo-creación (ESCRITURA) |
| `pages/editor_visual.py` | `detectar_accion_crear_grupo` | 562–577 | Solo-creación |
| `pages/editor_visual.py` | `confirmar_crear_grupo` — llama a `guardar_nuevo_grupo()` | 580–635 | Solo-creación (ESCRITURA) |
| `pages/editor_visual.py` | `abrir_modal_generar_pdf` | 638–649 | Mixto (abre flujo de impresión) |
| `pages/editor_visual.py` | `confirmar_generar_pdf` — llama `generate_report_pdf_from_state()` | 651–700 | Mixto (único trigger PDF hoy) |
| `pages/editor_visual.py` | `save_template` — llama a `guardar_plantilla()` | 702–752 | Solo-creación (ESCRITURA) |
| `utils/template_service.py` | `guardar_plantilla(datos, nombre)` | 459–527 | Solo-creación (ESCRITURA) |
| `utils/template_service.py` | `fusionar_grupo_en_plantilla(datos_grupo, editor_state)` | 534–620 | Solo-creación |
| `utils/template_service.py` | `importar_grupo_desde_bytes(contenido_bytes, filename)` | 627–665 | Solo-creación |
| `utils/template_service.py` | `_extraer_grupo_de_zip(zip_bytes)` | 668–715 | Solo-creación |
| `utils/template_service.py` | `_extraer_assets_a_carpeta(data, carpeta_destino)` | 225–296 | Solo-creación (ESCRITURA) |
| `utils/template_service.py` | `_registrar_y_limpiar_assets(data, nombre_plantilla)` | 298–336 | Solo-creación (ESCRITURA) |
| `utils/template_service.py` | `_convertir_anchos_pct_a_cm(data)` | 338–357 | Solo-creación (conversión al guardar) |
| `utils/funciones_grupos.py` | `guardar_nuevo_grupo(...)` | 68–188 | Solo-creación (ESCRITURA) |
| `utils/funciones_grupos.py` | `copiar_assets_grupo(...)` (deprecada) | 60–66 | Solo-creación |
| `utils/asset_manager.py` | `register_asset(source, original_filename)` | 85–132 | Solo-creación (ESCRITURA) |
| `utils/asset_manager.py` | `save_registry(registry)` | 51–57 | Solo-creación (ESCRITURA) |
| `utils/asset_manager.py` | `track_usage(asset_id, template_name)` | 258–267 | Solo-creación |
| `utils/asset_manager.py` | `untrack_usage(asset_id, template_name)` | 270–279 | Solo-creación |
| `models/template_models.py` | `Plantilla.to_editor_dict()` | 689–703 | Solo-editor |
| `models/template_models.py` | `Plantilla.limpiar_base64()` | 705–713 | Solo-editor (pre-guardado) |
| `models/template_models.py` | `Plantilla.convertir_anchos_a_cm()` | 715–727 | Solo-editor (pre-guardado) |
| `models/template_models.py` | `Plantilla.convertir_anchos_a_pct()` | 729–741 | Solo-editor |
| `models/template_models.py` | `Elemento.to_editor_dict()` | 529–550 | Solo-editor |
| `models/template_models.py` | `Elemento.limpiar_base64()` | 552–563 | Solo-editor |
| `models/template_models.py` | `NivelCuadricula.columnas_a_pct(ancho_total_cm)` | 367–387 | Solo-editor |
| `models/template_models.py` | `NivelCuadricula.columnas_a_cm(ancho_total_cm)` | 389–405 | Solo-editor (pre-guardado) |
| `models/template_models.py` | `ConfiguracionPlantilla.chartScripts` / `tableScripts` (campos `exclude=True`) | 618–619 | Solo-editor |
| `models/template_models.py` | `Plantilla.chartScripts` / `tableScripts` (campos `exclude=True`) | 664–665 | Solo-editor |
| `models/template_models.py` | `ImagenAsset.datos_temp` | 267–272 | Solo-editor (runtime) |
| `pages/editor_plantilla_layout.py` | Todo el módulo (canvas legado, reglas, botones de guardado/descarga) | 1–fin | Solo-creación |
| `utils/funciones_configuracion_plantilla.py` | `actualizar_orientacion_y_reglas(orientation)` | 16–fin | Solo-creación (canvas legado) |

---

## 2. Superficie de Consumo/Renderizado (CONSERVAR)

| Eslabón | Archivo | Función | Línea |
|---|---|---|---|
| Ingesta de plantilla | `utils/template_service.py` | `cargar_plantilla(nombre)` | 364–425 |
| Listado de plantillas | `utils/template_service.py` | `listar_plantillas_disponibles()` | 100–119 |
| Descubrimiento de scripts | `utils/template_service.py` | `listar_scripts_graficos()` / `listar_scripts_tablas()` / `listar_metadata_*()` | 129–184 |
| Resolución de tokens | `utils/report_engine.py` | `_resolve_params(params, context)` | 107–124 |
| Pre-computo contenido | `utils/report_engine.py` | `resolve_template(plantilla, context)` | 328–366 |
| Ejecución scripts gráficos | `utils/report_engine.py` | `_execute_graph(elem, context, graficos_dir)` | 238–281 |
| Ejecución scripts tablas | `utils/report_engine.py` | `_execute_table(elem, context, tablas_dir)` | 284–321 |
| Serialización a dict PDF | `utils/report_engine.py` | `_plantilla_to_pdf_dict(plantilla)` | 369–399 |
| Punto de entrada principal | `utils/report_engine.py` | `generate_report_pdf(nombre, context, output_path)` | 462–513 |
| Punto de entrada desde estado | `utils/report_engine.py` | `generate_report_pdf_from_state(editor_state, context, output_path)` | 402–459 |
| Renderizado PDF ReportLab | `utils/pdf_generator.py` | `generate_pdf_from_template(template_data, data_source, ...)` | 1606–1700 |
| Dibujo de elementos | `utils/pdf_generator.py` | `draw_line`, `draw_rectangle`, `draw_text`, `draw_image`, `draw_graph`, `draw_table`, `draw_multilevel_table` | 111–1605 |
| Resolución de imágenes (lectura) | `utils/asset_manager.py` | `get_asset_path(asset_id)` | 135–142 |
| Resolución de imágenes (lectura) | `utils/asset_manager.py` | `get_asset_data_uri(asset_id)` | 145–154 |
| Resolución de imágenes (lectura) | `utils/asset_manager.py` | `resolve_image_element(element, template_name)` | 184–215 |
| Resolución de imágenes (lectura) | `utils/asset_manager.py` | `resolve_image_path(element, template_name)` | 218–251 |
| Resolución de imágenes (búsqueda) | `utils/asset_manager.py` | `_search_image_file(ruta_nueva, template_name)` | 161–181 |
| Registro de scripts | `utils/script_registry.py` | `discover_scripts()` | 172–204 |
| Registro de scripts | `utils/script_registry.py` | `get_all_metadata()` / `get_graficos_metadata()` / `get_tablas_metadata()` | 211–223 |
| Validación Pydantic | `models/template_models.py` | `Plantilla.model_validate(data)` — valida y normaliza JSON de disco | (clase completa) |
| Normalización estilos | `models/template_models.py` | `Estilo.normalizar_nombres()` (validador `mode="before"`) | 134–185 |
| Normalización geometría | `models/template_models.py` | `Geometria.normalizar_tablas()` (validador `mode="before"`) | 68–78 |
| Normalización elemento | `models/template_models.py` | `Elemento.normalizar_formato_antiguo()` (validador `mode="before"`) | 490–527 |
| Scripts de gráficos | `biblioteca_graficos/grafico_incli_*/` | funciones `grafico_incli_*()` | varios |
| Script de tabla | `biblioteca_tablas/tabla_datos_inc/tabla_datos_inc.py` | función principal | — |
| Trigger PDF desde graficar | `pages/graficar.py` | `generar_informe_pdf(...)` — llama `pdf_generator` directamente | 1719–1884 |

---

## 3. Costuras de Acoplamiento

### 3.1 `utils/template_service.py`: ¿mezcla carga y guardado?

**Sí, mezcla funciones.** El módulo contiene en el mismo archivo:

- **Carga (conservar):** `cargar_plantilla()` (línea 364), `cargar_plantilla_para_editor()` (línea 428), todas las funciones `listar_*()` (líneas 100–184), `_inyectar_imagenes()` (línea 191).
- **Guardado/escritura (eliminar):** `guardar_plantilla()` (línea 459), `_extraer_assets_a_carpeta()` (línea 225), `_registrar_y_limpiar_assets()` (línea 298), `_convertir_anchos_pct_a_cm()` (línea 338).
- **Grupos/editor (eliminar):** `fusionar_grupo_en_plantilla()` (línea 534), `importar_grupo_desde_bytes()` (línea 627), `_extraer_grupo_de_zip()` (línea 668).

**Corte propuesto:** Separar `template_service.py` en `template_loader.py` (solo lectura) y conservar `guardar_plantilla` y funciones de grupo solo mientras se mantenga el editor. `cargar_plantilla_para_editor()` (línea 428) también es solo-editor porque inyecta `chartScripts`/`tableScripts`; `cargar_plantilla()` (línea 364) es pura consumo.

### 3.2 `utils/report_engine.py`: ¿depende del estado del editor?

**Solo parcialmente.** `generate_report_pdf()` (línea 462) llama a `cargar_plantilla()` de `template_service` y no toca el estado del editor. `generate_report_pdf_from_state()` (línea 402) acepta `editor_state` (dict del componente React), pero internamente convierte los `%` a `cm` con `_convertir_anchos_pct_a_cm()` y valida con `Plantilla.model_validate()`. Esta segunda función puede eliminarse junto con el editor, o reutilizarse para ingesta de JSON externo si Maketator entrega en formato porcentaje.

**Dependencia clave:** `report_engine.py:32` importa `cargar_plantilla` de `template_service`; este import sobrevive a la eliminación del editor.

### 3.3 `utils/asset_manager.py`: ¿mezcla registro y resolución?

**Sí, claramente.** El módulo tiene dos mitades:

- **Escritura/registro (eliminar con editor):** `register_asset()` (línea 85), `save_registry()` (línea 51), `track_usage()` (línea 258), `untrack_usage()` (línea 270).
- **Lectura/resolución (conservar siempre):** `load_registry()` (línea 40), `get_asset_path()` (línea 135), `get_asset_data_uri()` (línea 145), `resolve_image_element()` (línea 184), `resolve_image_path()` (línea 218), `_search_image_file()` (línea 161).

Las funciones de lectura son imprescindibles durante el render; las de escritura solo se usan al guardar plantillas desde el editor. El archivo puede mantenerse completo (sin modificar) ya que eliminar las funciones de escritura no es urgente y no afecta al render.

### 3.4 `models/template_models.py`: ¿arrastra lógica solo-editor?

**Sí, hay métodos solo-editor.** Los modelos Pydantic son usados tanto por el editor como por el motor de render. Los métodos solo-editor son identificables:

- **Solo-editor (pueden eliminarse/ignorarse):** `to_editor_dict()` en `Elemento` (línea 529), `Pagina` (línea 596), `Plantilla` (línea 689); `limpiar_base64()` en `Elemento` (línea 552) y `Plantilla` (línea 705); `convertir_anchos_a_cm()` (línea 715) y `convertir_anchos_a_pct()` (línea 729) en `Plantilla`; `columnas_a_pct()` (línea 367) y `columnas_a_cm()` (línea 389) en `NivelCuadricula`.
- **Campos de runtime solo-editor:** `ImagenAsset.datos_temp` (línea 267), `ConfiguracionElemento.datos_ejecutados` (línea 439, campo con `exclude=True`), `chartScripts`/`tableScripts` en `Plantilla` y `ConfiguracionPlantilla` (líneas 618–665).
- **Indispensables para el render:** Todos los validadores `model_validator` (`normalizar_nombres`, `normalizar_tablas`, `normalizar_formato_antiguo`, `inyectar_ids_elementos`, `normalizar_estructura_plana`) y la estructura de campos (`Geometria`, `Estilo`, `Contenido`, `Metadata`, `Elemento`, `Pagina`, `Plantilla`).

**Decisión:** Los métodos solo-editor no causan daño si se dejan en el modelo. Solo eliminarlos si se busca simplificación extrema.

### 3.5 `app.py`: ¿acopla arranque a páginas del editor?

**Sí.** Las líneas 17–26 importan `editor_plantilla` y `editor_visual`; las líneas 196–197 registran sus callbacks; las líneas 92–93 en `NAV_ITEMS` los enlazan en el sidebar; la línea 179–180 en `render_page_content` mapea sus rutas. Si se eliminan esos módulos, hay que limpiar estas 4 zonas de `app.py`. El resto del arranque (importar, correcciones, graficar, importar_umbrales) es independiente.

---

## 4. Contrato de Plantilla de Entrada (desde Maketator)

### 4.1 Esquema JSON exacto que espera IncliData

Basado en `models/template_models.py` y el archivo real `biblioteca_plantillas/INCL_AR/INCL_AR.json`:

```json
{
  "configuracion": {
    "nombre_plantilla": "string",
    "num_paginas": 1
  },
  "pagina_actual": "1",
  "paginas": {
    "1": {
      "configuracion": { "orientacion": "portrait | landscape" },
      "elementos": {
        "{id_unico}": {
          "tipo": "texto | rectangulo | linea | grafico | tabla | imagen",
          "geometria": {
            "x": float,      // cm desde borde izquierdo
            "y": float,      // cm desde borde superior
            "ancho": float,  // cm
            "alto": float    // cm
          },
          "estilo": {
            "backgroundColor": "string hex | transparent",
            "borderColor": "string hex",
            "borderWidth": float,
            "opacity": float,   // 0.0–1.0
            "color": "string hex",
            "tamano": float,
            "fontFamily": "string",
            "fontWeight": "normal | bold",
            "fontStyle": "normal | italic",
            "textAlign": "left | center | right"
          },
          "metadata": {
            "zIndex": int,
            "visible": true | false,
            "grupo": "string | null"
          },
          "contenido": {
            "texto": "string | null",
            "src": null   // SIEMPRE null en disco; imágenes usan asset_id
          },
          // Para tipo="imagen":
          "imagen": {
            "asset_id": "string (8 chars MD5)",
            "ruta_nueva": "assets/nombre.png",
            "nombre_archivo": "nombre.png",
            "formato": "png | jpg | svg"
          },
          // Para tipo="grafico" o "tabla":
          "configuracion": {
            "script": "nombre_script.py",
            "formato": "png | svg",
            "parametros": {
              "sensor": "$CURRENT",
              "fecha_inicial": "$CURRENT_fecha_inicial"
            }
          },
          // Para tipo="tabla":
          "cuadricula": {
            "niveles": [
              {
                "tipo": "estatico | autorrelleno",
                "alto_fila": float,   // cm
                "columnas": [
                  {
                    "ancho": float,   // cm (en disco; % solo en el editor React)
                    "contenido": "string",
                    "formato": { "color_fondo": "hex", "color_texto": "hex", "alineacion": "string" },
                    "bordes": {
                      "superior": { "activo": bool, "grosor": float, "color": "hex" }
                    }
                  }
                ]
              }
            ]
          }
        }
      }
    }
  }
}
```

**Tokens soportados** (resueltos en `report_engine.py:49–58`):
- `$CURRENT` → `context["info"]["nom_sensor"]`
- `$CURRENT_fecha_seleccionada` → `context["fecha_seleccionada"]`
- `$CURRENT_ultimas_camp` → `context["ultimas_camp"]`
- `$CURRENT_fecha_inicial` → `context["fecha_inicial"]`
- `$CURRENT_fecha_final` → `context["fecha_final"]`

**Imagen de referencia real** (del JSON `INCL_AR.json` en disco): los elementos usan `"src": null` y `"asset_id"` para imágenes ya registradas; el almacén está en `biblioteca_plantillas/_assets/registry.json`.

### 4.2 Contraste con `_migracion/CONTRATO_motor_maketador.md`

El contrato de Maketator (`_migracion/CONTRATO_motor_maketador.md`) describe una versión más evolucionada con:

1. **Campo `"engine": "html"`** en la raíz del JSON — no existe en el esquema IncliData actual (IncliData usa ReportLab, no HTML/Playwright).
2. **`params_clasificacion`** dentro de `configuracion` — metadata del editor, no existe en IncliData.
3. **`"secciones": {}`** para encabezados/pies — no existe en IncliData.
4. **`context["sensor"]`** como clave primaria del sensor — IncliData usa `context["info"]["nom_sensor"]`.
5. **Motor único en Maketator: HTML/Playwright** — IncliData usa ReportLab/Matplotlib.
6. **Rutas de scripts:** Maketator usa `biblioteca_graficos/html/` y `biblioteca_tablas/funciones/`; IncliData usa `biblioteca_graficos/{nombre}/{nombre}.py` y `biblioteca_tablas/{nombre}/{nombre}.py`.

**Conclusión:** Los esquemas son **incompatibles directamente**. Si IncliData importa plantillas de Maketator, se necesita una capa de conversión de esquema, o bien Maketator debe emitir el esquema de IncliData.

### 4.3 Cómo llega físicamente una plantilla al render hoy

**Vía 1 — Editor Visual (hoy el único camino real):**
1. Usuario edita en `dce.Editor` (React) → `visual-editor.value` (dcc.Store).
2. Click "Guardar Cambios" → `save_template` callback (`editor_visual.py:709`) → `guardar_plantilla()` (`template_service.py:459`) escribe `biblioteca_plantillas/{nombre}/{nombre}.json`.
3. Click "Generar PDF" → `confirmar_generar_pdf` callback (`editor_visual.py:661`) → `generate_report_pdf_from_state()` (`report_engine.py:402`).

**Vía 2 — Desde graficar.py:**
1. Usuario selecciona plantilla en `graficar.py` (dropdown de plantillas).
2. `generar_informe_pdf` callback (`graficar.py:1719`) llama directamente a `pdf_generator.generate_pdf_from_template()`.
3. **No pasa por `report_engine.py`** — accede a `pdf_generator.py` directamente.

### 4.4 Mecanismo de ingesta necesario (HUECO A RESOLVER)

Actualmente **no existe ningún mecanismo de ingesta de plantilla externa** que no sea el editor visual. Para operar como impresor independiente se necesita una de estas opciones:

- **Opción A (más simple):** Copiar el JSON de Maketator a `biblioteca_plantillas/{nombre}/{nombre}.json` manualmente o mediante un script CLI. El render funciona sin cambios: `generate_report_pdf(nombre, context, output_path)`.
- **Opción B:** Añadir un endpoint HTTP (Flask) o una nueva página Dash de "Importar Plantilla" que reciba el JSON y lo deposite en disco con el nombre correcto.
- **Opción C:** `generate_report_pdf_from_state()` (`report_engine.py:402`) acepta el dict directamente sin pasar por disco — válida para invocación programática.

**Bloqueante crítico:** si la plantilla viene de Maketator con su esquema (campo `engine`, rutas de scripts diferentes, etc.), se necesita un convertidor de esquema antes de pasarla a `Plantilla.model_validate()`.

---

## 5. Flujo de Impresión Independiente

### 5.1 Cómo se dispara hoy la generación del PDF

**Vía editor_visual (ruta principal actual):**

```
Usuario click "Generar PDF" (btn-generate-pdf-visual, editor_visual.py:145)
  → abrir_modal_generar_pdf() [editor_visual.py:638] abre modal
  → Usuario click "Generar maquetación PDF" (btn-maquetacion-pdf, editor_visual.py:326)
  → confirmar_generar_pdf() [editor_visual.py:651]
      - Lee editor_state desde visual-editor.value O visual-editor.data
      - Llama generate_report_pdf_from_state(editor_state, context, tmp_path)
          [report_engine.py:402]
          - Llama _convertir_anchos_pct_a_cm(data)  [template_service.py:338]
          - Llama Plantilla.model_validate(data)
          - Llama resolve_template(plantilla, context) [report_engine.py:328]
          - Llama _plantilla_to_pdf_dict(resolved) [report_engine.py:369]
          - Llama generate_pdf_from_template(...) [pdf_generator.py:1606]
      - Output → dcc.Download("dcc-download-pdf") [editor_visual.py:337]
```

**Vía graficar (ruta alternativa ya existente):**

```
Usuario click "btn-generar-informe-pdf" (graficar.py:1694)
  → generar_informe_pdf() [graficar.py:1719]
      - Lee plantilla-json-data (dcc.Store con JSON de plantilla cargado previamente)
      - Lee graficar-tubo (datos del sensor cargado)
      - Reemplaza tokens $CURRENT manualmente (sin usar report_engine)
      - Llama generate_pdf_from_template() [pdf_generator.py:1606] DIRECTAMENTE
      - Output → dcc.Download("descargar-informe-pdf") [graficar_layout.py:600]
```

### 5.2 ¿Existe vía sin editor? (bloqueantes identificados)

**Sí, existe y es limpia:** `generate_report_pdf(nombre_plantilla, context, output_path)` en `report_engine.py:462` no requiere el editor. Lee la plantilla desde disco y produce el PDF. Es invocable directamente desde Python o desde un callback Dash nuevo.

**Bloqueantes para operación completamente independiente:**

1. **No hay página/ruta Dash para seleccionar plantilla externa + lanzar render** sin el editor.
2. **La plantilla debe existir en `biblioteca_plantillas/{nombre}/`** — no hay API de ingesta.
3. **El contexto de ejecución** (sensor, fechas) debe construirse desde los datos de IncliData; hoy se construye en `graficar.py:1782–1805` como `current_values` con los valores de los controles UI.
4. **Resolución de imágenes:** `resolve_image_path()` (`asset_manager.py:218`) busca en `biblioteca_plantillas/_assets/` por `asset_id`; si la plantilla viene de Maketator con rutas distintas, los assets deben estar disponibles localmente.
5. **Incompatibilidad de esquema de scripts:** `report_engine.py` busca scripts en `biblioteca_graficos/{stem}/{stem}.py`; si la plantilla Maketator apunta a `biblioteca_graficos/html/grafico_inclinometro_v2.py`, el path resuelto no existirá.

---

## 6. Huérfanos Tras la Eliminación

### Dependencias JS/React (bundle compilado)

- **`dash_component_editor_src/`** — directorio completo con fuentes TypeScript/React, `node_modules/` (~2,000+ paquetes), `package.json` con dependencias: `@dnd-kit/core`, `zustand`, `react-hook-form`, `@tanstack/react-query`, `framer-motion`, todo Radix UI.
- **`dash_component_editor_src/dash_component_editor/dash_component_editor.min.js`** — bundle compilado; único artefacto que consume la app Python en runtime.
- **`dash_component_editor_src/dash_component_editor/__init__.py`**, `Editor.py`, `_imports_.py` — wrapper Python del componente React.
- **Import en `editor_visual.py:5`:** `import dash_component_editor as dce`.

### `biblioteca_grupos/`

- 4 grupos actuales: `grupo_encab_hor_L9`, `grupo_encab_vert_L9`, `grupo_encab_vert_L9_minimalista`, `tabla_inclis_L9_3camp`.
- Toda la lógica en `utils/funciones_grupos.py` (listar, leer, copiar, guardar grupos).
- Referencias desde `editor_visual.py:11` y `editor_plantilla.py:17`.

### Funciones de import/export de grupos

- `utils/funciones_grupos.py` — completo (4 funciones públicas).
- `utils/template_service.py:fusionar_grupo_en_plantilla()`, `importar_grupo_desde_bytes()`, `_extraer_grupo_de_zip()`.
- Callbacks en `editor_visual.py`: `importar_grupo_archivo()`, `exportar_grupo()`, `detectar_accion_crear_grupo()`, `confirmar_crear_grupo()`.

### Métodos Pydantic solo-editor

En `models/template_models.py`: `to_editor_dict()` (3 clases), `limpiar_base64()` (2 clases), `convertir_anchos_a_cm()`, `convertir_anchos_a_pct()`, `columnas_a_pct()`, `columnas_a_cm()`. Ninguno es llamado por `report_engine.py` o `pdf_generator.py`.

### Rutas/sidebar del editor

- `app.py:NAV_ITEMS` líneas 92–93: "Editor plantillas" `/editor_plantilla` y "Editor Visual" `/editor-visual`.
- `app.py:render_page_content()` líneas 179–180: mapeo de rutas.
- `app.py:196–197`: `register_callbacks` de ambos editores.
- `app.py:17–26`: imports de `editor_plantilla` y `editor_visual`.

### Candidatos de `requirements.txt` a revisar tras la eliminación

| Paquete | Motivo de revisión |
|---|---|
| `reportlab` | **CONSERVAR** — motor de render PDF actual |
| `svglib` | **CONSERVAR** — usado en `pdf_generator.py:29–35` para gráficos SVG |
| `Pillow` | **CONSERVAR** — usado en `pdf_generator.py:23` |
| `matplotlib` | **CONSERVAR** — usado en scripts gráficos y error images en `report_engine.py` |
| `icecream` | **Revisar** — solo en `graficar.py:9`; puede eliminarse si se limpia esa página |
| `dash-ag-grid` | **Revisar** — no detectado en los archivos core del render; verificar si lo usa alguna página |
| `openpyxl` / `XlsxWriter` | **Revisar** — probablemente solo en exportación de datos de graficar.py, no en render PDF |
| `pywin32` | **Revisar** — Windows-only, solo si se usa en algún script específico |

---

## 7. Decisiones Abiertas para el Asesor

1. **Esquema de plantilla unificado:** ¿IncliData adopta el esquema de Maketator (con campo `engine`, `secciones`, rutas `html/`) o Maketator emite el esquema de IncliData (ReportLab/Matplotlib, rutas `biblioteca_graficos/{stem}/{stem}.py`)? Esta es la decisión más bloqueante.

2. **Motor de render a largo plazo:** El contrato Maketator declara "Motor único activo: HTML/Playwright" y que ReportLab fue archivado en junio 2026. ¿Se migra IncliData a HTML/Playwright o mantiene ReportLab?

3. **Mecanismo de ingesta de plantilla:** ¿Drop de archivo JSON en carpeta (Opción A), API REST (Opción B), o invocación programática directa (Opción C) con `generate_report_pdf_from_state()`?

4. **Integración de datos del sensor:** ¿IncliData deposita sus JSONs procesados en `json_inclis/` (Opción a del contrato) o se pasan en `context["data"]` con modificación de 4 scripts de lectura (Opción b)?

5. **Qué hacer con `graficar.py`:** Hoy tiene su propia vía de generación PDF (`generar_informe_pdf` en línea 1719) que bypasea `report_engine.py` y llama a `pdf_generator.py` directamente. ¿Se consolidan ambas vías en `report_engine.py`?

6. **Assets de imágenes en plantillas externas:** Si la plantilla viene de Maketator, ¿cómo se transfieren/referencian los assets (logos, imágenes corporativas)? El sistema actual depende de `biblioteca_plantillas/_assets/registry.json`.

7. **`cargar_plantilla_para_editor()`** en `template_service.py:428` inyecta `chartScripts`/`tableScripts`; la función pura para render es `cargar_plantilla()`. ¿Se elimina la primera o se reutiliza para poblar un selector de plantillas en la nueva UI?

8. **Cuándo eliminar `pages/editor_plantilla.py`:** El editor legado (canvas Dash) es funcionalmente redundante con el editor visual React. ¿Se elimina en el mismo PR que el editor visual o en un paso previo independiente?

---

## Verificación

- `git status` (tras crear este archivo): solo `info/ESTUDIO_impresion_independiente.md` debe aparecer como nuevo fichero no rastreado (ningún otro archivo fue modificado).
- Nº de líneas del informe: ~330
- Nº de archivos clasificados en "creación/edición" (Sección 1): **34 entradas** en 12 archivos distintos.
- Nº de eslabones en "consumo/renderizado" (Sección 2): **24 entradas** en 6 archivos distintos.
- Confirmación de que la sección de contrato cita código real:
  - `report_engine.py:49–58` — definición de `_CONTEXT_KEYS` con tokens `$CURRENT*`.
  - `report_engine.py:462` — `generate_report_pdf(nombre_plantilla, context, output_path)`.
  - `template_service.py:364` — `cargar_plantilla(nombre)`.
  - `template_service.py:459` — `guardar_plantilla(datos, nombre)`.
  - `pdf_generator.py:1606` — `generate_pdf_from_template(template_data, data_source, ...)`.
  - `asset_manager.py:85` — `register_asset(source, original_filename)`.
  - `asset_manager.py:218` — `resolve_image_path(element, template_name)`.
  - `models/template_models.py:689` — `Plantilla.to_editor_dict()`.
  - `editor_visual.py:651` — `confirmar_generar_pdf()` (único trigger PDF en editor visual).
  - `graficar.py:1719` — `generar_informe_pdf()` (segunda vía de generación PDF).

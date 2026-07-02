# 🏗️ Descripción General y Arquitectura

**IncliData** es una aplicación web para procesamiento, visualización y generación de informes PDF de datos de instrumentación geotécnica (principalmente inclinómetros).

**Stack Tecnológico:**
- **Frontend/UI:** Dash 4.x + Dash Mantine Components (DMC v2) + Dash Bootstrap Components + Dash AG Grid
- **Componente React custom:** `dash_component_editor` — editor visual de plantillas con drag-and-drop (DnD Kit, React Hook Form, Tailwind CSS). Fuente en `dash_component_editor_src/`, compilado en el paquete instalado `dash_component_editor`.
- **Visualización:** Plotly (interactivo en UI), Matplotlib (figuras para PDF)
- **Datos:** Pandas 2.x (pin <3.0), NumPy, SciPy
- **Generación PDF:** ReportLab + svglib (renderizado de plantillas JSON → PDF)
- **Validación:** Pydantic v2 (modelos en `models/`)
- **ORM:** SQLAlchemy (declarado en requirements, sin uso activo visible)
- **Testing:** pytest

**Flujo principal:**
```
Importar JSON/CSV (pages/importar) 
  → Corregir datos (pages/correcciones) 
    → Graficar (pages/graficar)
      → Diseñar plantilla (pages/editor_visual + pages/editor_plantilla)
        → Generar PDF (utils/report_engine → utils/pdf_generator)
```

**Data binding en plantillas:** el token `$CURRENT` inyecta valores de la UI en los parámetros de los scripts de gráficos/tablas en tiempo de renderizado.

---

# 📁 Estructura Principal del Proyecto

```
app.py                        Punto de entrada. Inicializa Dash, define sidebar, enrutado y registra callbacks.
inclidata.py                  Archivo residual (solo contiene un comentario de estructura). No usar.

pages/
  info.py                          Página de bienvenida/información.
  importar.py                      Importación de datos (JSON de fabricantes: RST, SISGEO, Soil_dux).
  graficar.py (2922 líneas)        Callbacks de visualización interactiva. Layout en graficar_layout.py.
  graficar_layout.py (618 l.)      Layout de la página Graficar (componentes Dash, sin lógica).
  correcciones.py (2059 l.)        Callbacks de corrección de datos: bias, spikes, etc.
  correcciones_layout.py (573 l.)  Layout de la página Correcciones.
  importar_umbrales.py             Importación de umbrales de alerta desde Excel.
  editor_plantilla.py (4522 l.)    Callbacks del editor de plantillas JSON (legado, reemplazando con editor_visual).
  editor_plantilla_layout.py (2289 l.) Layout del editor de plantillas (2281 líneas de UI).
  editor_visual.py                 Editor visual moderno con el componente React dce.Editor.
  configuraciones.py               Stub vacío (funcionalidad futura).
  spikes.json                      Configuración de spikes para correcciones.py (ruta relativa intencional).

utils/
  pdf_generator.py (1697 l.)  Motor de renderizado ReportLab. Dibuja cada tipo de elemento (texto, rect, grafico, tabla, imagen).
  report_engine.py            Capa superior: recibe Plantilla (Pydantic), resuelve scripts dinámicos, llama a pdf_generator.
  template_service.py         Servicio backend puro: carga, guarda y convierte plantillas. Gestiona unidades cm ↔ %.
  script_registry.py          Registro/descubrimiento de scripts de gráficos y tablas (@register_script).
  asset_manager.py            Gestión centralizada de imágenes: registry.json, base64 ↔ archivo en _assets/.
  funciones_importar.py       Parsers por fabricante (RST, SISGEO, Soil_dux).
  funciones_graficar.py       Lógica de construcción de figuras Plotly.
  funciones_correcciones.py   Algoritmos de corrección (bias, detección de spikes).
  funciones_grupos.py         Agrupación/selección de sensores.
  funciones_comunes.py        Utilidades compartidas entre páginas.
  funciones_configuracion_plantilla.py  Helpers de configuración de plantillas.
  funciones_graficos.py       Helpers para gráficos (usados por biblioteca_graficos).
  funciones_informe_inclinometro.py  Generación de datos de informe.
  diccionarios.py             Constantes y mapeos (24 líneas).
  rutas.py                    Centraliza rutas del sistema de archivos.
  dev_logging.py              Monkey-patch de logging de callbacks (activar con DEBUG_CALLBACKS=1). Extraído de app.py.

models/
  template_models.py (741 l.) Modelos Pydantic v2 para plantillas: Plantilla, Elemento, TipoElemento, Columna.
                               Cubre la conversión cm ↔ % de anchos de columna.

biblioteca_graficos/
  grafico_incli_0/            Perfil de inclinómetro (gráfico principal).
  grafico_incli_evo_tempo/    Evolución temporal de lecturas.
  grafico_incli_evo_std_chk/  Evolución estándar con chequeo.
  grafico_incli_series_0/     Series temporales de sensores.
  grafico_incli_leyenda_0/    Leyenda flotante para gráficos.
  grafico_ejemplo/            Placeholder de ejemplo (no productivo).

biblioteca_tablas/
  tabla_datos_inc/            Tabla de datos de inclinómetro (para PDF).
  ejemplo_tabla_kk/           Placeholder de ejemplo (no productivo).

biblioteca_plantillas/
  _assets/                    Imágenes centralizadas (registry.json + archivos por hash).
  encabezado_0/, encabezado_1/  Plantillas de encabezado.
  INCL_AR/, Incli_L9_BCN/     Plantillas de producción.
  kk/, kk_1/, kk_03/, INCL_AR_kk_2/, INCL_AR_prueba_kk_01/  Plantillas de prueba/sandbox.
  Rozmarin_test/              Plantilla de pruebas del proyecto Rozmarin.

assets/                       CSS global (custom.css, styles.css) e imágenes estáticas de la UI.
data/                         Datos de ejemplo e instrumentos (JSON por inclinómetro + plantillas base).
tests/                        Tests pytest (conftest, test_funciones_comunes/correcciones/importar).
scripts/
  migrate_assets.py           Script de migración one-shot para el sistema de assets.
dash_component_editor_src/    Fuente TypeScript/React del componente dce.Editor.
```

---

# 🗑️ Candidatos a Eliminación

| Archivo / Carpeta | Motivo |
|---|---|
| `inclidata.py` | Solo contiene un comentario de arquitectura. Sin código ejecutable. |
| `debug_import.py` | Script de debug para importar `dash_component_editor`. Ya no necesario. |
| `reproduce_issue.py` | Script de reproducción de bug. Residual. |
| `debug_bias.json` | Datos de debug de algoritmo de bias. Residual. |
| `debug_spikes.json` | Datos de debug de detección de spikes. Residual. |
| `tmp_all_callbacks.txt` | Volcado temporal de callbacks. Residual. |
| `tmp_callbacks.txt` | Volcado temporal de callbacks. Residual. |
| `error_callbacks.log` | Log de errores (14 KB). Debe estar en `.gitignore`. |
| `dash_errors.log` | Log de errores de Dash. Debe estar en `.gitignore`. |
| `correcciones_errors.log` | Log de errores de correcciones. Debe estar en `.gitignore`. |
| `debug_flask.log` | Log de debug de Flask. Debe estar en `.gitignore`. |
| `antigravity.md` | Archivo sin contenido funcional, no rastreado por git. |
| `ejemplo_datos.csv` | Dato de ejemplo en la raíz. Mover a `data/` o eliminar. |
| `salida_medias_.xlsx` | Archivo de salida generado, dejado en la raíz. |
| `test_umbrales_IPI_50.json` | Dato de prueba en la raíz. Mover a `data/` o eliminar. |
| `Pasted image.png` | Imagen pegada sin propósito declarado. |
| `PROTOTIPO_LOVABLE.tsx` | Prototipo en TSX en un proyecto Python. Mover a `_Documentación/` o eliminar. |
| `pages/spikes.json` | Archivo de datos dentro de `pages/`. Debería estar en `data/`. |
| `data/Plantilla - copia.json` | Copia de plantilla (nombre con " - copia"). |
| `data/Plantilla_Ejemplo_RST_vacio - copia.json` | Ídem. |
| `biblioteca_plantillas/kk/` | Plantilla de sandbox (nombre "kk"). |
| `biblioteca_plantillas/kk_1/` | Ídem. |
| `biblioteca_plantillas/kk_03/` | Ídem. |
| `biblioteca_plantillas/INCL_AR_kk_2/` | Ídem (sufijo "kk"). |
| `biblioteca_plantillas/INCL_AR_prueba_kk_01/` | Plantilla de prueba temporal. |
| `biblioteca_graficos/grafico_ejemplo/` | Script placeholder, sin uso productivo. |
| `biblioteca_tablas/ejemplo_tabla_kk/` | Script placeholder, sin uso productivo. |
| `utils/analyze_dependencies.py` | Herramienta de análisis de dev. No forma parte del despliegue. |
| `Documentación IncliData_v0_Claude.docx` | Documentación antigua (v0). |
| `Documentación IncliData_v0_Claude.pdf` | Ídem. |
| `_Documentación/` | Carpeta de documentación no versionable en la raíz del proyecto. |
| `ANALISIS_GENERACION_PDF.md` | Análisis puntual ya asimilado en el código. |
| `analisis_graficos.md` | Ídem. |
| `analisis_plantillas.md` | Ídem. |
| `DOCUMENTACION_EDITOR_PLANTILLAS.md` | Documentación que solapa con `CLAUDE.md`. |
| `DOCUMENTACION_FINAL.md` | Ídem. |
| `listado_archivos.md` | Este `CONTEXT.md` lo reemplaza. |
| `LIBRERIAS_POR_ARCHIVO.md` | Puede derivarse de `requirements.txt` + imports. |
| `Guia_estilo.md` | Consolidar en `CLAUDE.md`. |
| `Guía_uso_Importar.md` | Consolidar en `README.md` o `CLAUDE.md`. |

---

# ⚠️ Análisis de Deuda Técnica

_Actualizado 2026-04-26 tras primera ronda de refactorización._

### ✅ Resuelto

| Item | Solución |
|---|---|
| `requirements.txt` con `pydantic` duplicado y `SQLAlchemy` sin uso | Eliminados. Archivo limpio. |
| `from sqlalchemy import false` en `correcciones.py` | Eliminado (era importación de constante booleana, nunca usada en código). |
| Bloque de debug logging en `correcciones.py` (FileHandler en cada import) | Reemplazado con `logging.getLogger(__name__)` estándar. |
| Monkey-patch de callbacks en `app.py` | Extraído a `utils/dev_logging.py`. Se activa con `DEBUG_CALLBACKS=1`. |
| Estilos dark mode duplicados en `app.py` | Consolidados en dict `_THEMES` con `_SIDEBAR_BASE` y `_CONTENT_BASE`. |
| Imports comentados en `app.py` (`graficar_debug`, `configuracion_plantilla_gpt`) | Eliminados. |
| `editor_plantilla.py` (6 801 líneas) | Layout extraído a `editor_plantilla_layout.py`. Reducido a 4 522 líneas. |
| `graficar.py` (3 528 líneas) | Layout extraído a `graficar_layout.py`. Reducido a 2 922 líneas. |
| `correcciones.py` (2 628 líneas) | Layout extraído a `correcciones_layout.py`. Reducido a 2 059 líneas. |
| 33 archivos temporales/sandbox eliminados | Ver historial de git. |

### 🔴 Pendiente — Alta prioridad

**`pages/editor_plantilla.py` (4 522 líneas)**
El `register_callbacks(app)` concentra ≈67 callbacks (≈4 480 líneas desde la línea 40). La siguiente fase de refactorización debe dividirlos en grupos de responsabilidad:
- `_register_canvas_callbacks(app)` — renderizado del canvas
- `_register_tabla_callbacks(app)` — gestión de tablas
- `_register_grupos_callbacks(app)` — grupos de plantilla
- `_register_export_callbacks(app)` — guardado y exportación

Cada sub-función se define en el mismo archivo pero permite navegación y mantenimiento independiente.

### 🟡 Pendiente — Media prioridad

**`pages/editor_plantilla_layout.py` (2 289 líneas)**
La función `layout()` es un árbol de componentes Dash de 2 280 líneas. Se puede dividir en funciones `_render_*()` privadas (sin extraer a otro archivo), reduciendo la profundidad de anidación.

**`pages/graficar.py` — callbacks muy largos**
Los callbacks `actualizar_graficos` (~320 l.) y `actualizar_grafico_temporal` (~80 l.) mezclan orquestación Dash con construcción de figuras Plotly. Mover la construcción de figuras a `utils/funciones_graficar.py`.

**`pages/configuraciones.py` — stub vacío**
Placeholder de 6 líneas. Implementar o eliminar. No está en navegación ni en `register_callbacks`.

### 🟢 Pendiente — Baja prioridad

**Tipado parcial en callbacks**
Ningún callback tiene type hints. Añadir `-> dash.development.base_component.Component` en layouts y tipos en callbacks.

**`biblioteca_plantillas/incli_L9_BCN_v0[b]/`**
Nombre con corchetes puede causar problemas con glob. Renombrar a `incli_L9_BCN_v0b/`.

**`utils/diccionarios.py` (24 líneas)**
Evaluar absorber en `funciones_comunes.py` o crear `utils/constants.py`.

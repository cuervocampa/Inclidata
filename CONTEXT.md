# Arquitectura de IncliData — v2.0 (motor HTML/Playwright)

**IncliData** es un visor, corrector e impresor standalone de datos de instrumentación geotécnica (principalmente inclinómetros). Carga archivos de sensor (RST/SISGEO/Soil_dux), permite corregir lecturas, y genera informes PDF mediante plantillas creadas en Maketator.

> **El editor de plantillas fue eliminado de IncliData.** Las plantillas se diseñan en Maketator (editor visual React + dce.Editor). Son recuperables en `tag v1.0-pre-poda-reportlab` o `rama archive/full-editor-reportlab`.

---

## Stack tecnológico

- **Frontend/UI:** Dash 4.x + Dash Mantine Components v2 + Dash Bootstrap Components
- **Visualización interactiva:** Plotly
- **Generación PDF:** `engines/html_engine.py` + `utils/report_engine.py` (trasplantados de Maketator) → Playwright/Chromium
- **Datos:** Pandas 2.x (pin <3.0), NumPy, SciPy
- **Validación:** Pydantic v2 (modelos en `models/`, reducidos tras migración)
- **Testing:** pytest

---

## Flujo principal

```
Importar JSON/CSV (pages/importar)
  → Corregir datos (pages/correcciones)
    → Graficar (pages/graficar)
      → Modal de informe: seleccionar plantilla + parámetros $CURRENT
        → generate_report_pdf_from_state (utils/report_engine)
          → engines/html_engine.py → Playwright/Chromium → PDF
```

---

## Motor de render HTML

El motor es un trasplante directo de Maketator. **No se parchea localmente**: cualquier cambio debe coordinarse con Maketator y trasplantarse de nuevo.

| Archivo | Rol |
|---|---|
| `engines/html_engine.py` | Motor principal: convierte plantilla JSON → HTML → PDF via Playwright |
| `utils/report_engine.py` | Fachada: recibe plantilla dict + context, llama al motor, devuelve PDF |
| `biblioteca_plantillas/html/` | Plantillas en formato HTML (namespace `html/`) |
| `biblioteca_graficos/html/` | Scripts de gráficos con namespace `html/` |
| `biblioteca_tablas/funciones/` | Scripts de tablas por grupo |

**Stubs heredados del trasplante** (requeridos por html_engine pero sin uso real en IncliData):
- `models/server.py` — stub vacío (html_engine importa `server_id` condicionalmente)
- `models/database.py` — stub vacío (html_engine importa `DB` condicionalmente)
- `sqlmodel` en requirements — solo para satisfacer import condicional de html_engine

---

## Puente de datos: json_inclis

Al subir un archivo de sensor, `pages/graficar.py` escribe el JSON original a `json_inclis/{sensor_id}.json` y limpia el caché de `columna_incli_json`. El `sensor_id` canónico vive en `store["info"]["_sensor_id"]`.

El motor HTML lee el JSON del sensor directamente desde disco cuando renderiza gráficos.

---

## Regla del store `graficar-tubo`

Las claves raíz del store `graficar-tubo` son **exclusivamente timestamps de campaña** (ISO 8601) más las claves reservadas `info` y `umbrales`. Cualquier metadato nuevo (sensor_id, nombre, etc.) va **dentro de `info{}`**, nunca como clave raíz.

---

## Data binding `$CURRENT`

El token `$CURRENT` en los parámetros de elementos `grafico`/`tabla` de una plantilla se sustituye en tiempo de render por el valor actual del control de UI correspondiente (eje, escala, fechas, etc.). Ver `generar_informe_pdf` en `pages/graficar.py`.

---

## Arranque dual

```python
# Modo estable (producción / desarrollo sin hot-reload):
python app.py

# Modo dev (reloader activo, exclude_patterns protegen archivos de runtime):
INCLIDATA_DEBUG=1 python app.py
```

**Por qué `exclude_patterns`:** el reloader watchdog de werkzeug reiniciaba el servidor cuando la app escribía `json_inclis/*.json` o `_assets/registry.json` durante un callback en vuelo, matando la petición con "server did not respond". `exclude_patterns` excluye esos paths del watching sin desactivar el reloader completo.

En modo estable (`debug=False, use_reloader=False`) el proceso es único y el problema no existe.

---

## Estructura de carpetas

```
app.py                        Punto de entrada. Arranque dual controlado por INCLIDATA_DEBUG.
pages/
  info.py                     Bienvenida/información del sensor cargado.
  importar.py                 Parsers RST, SISGEO, Soil_dux.
  graficar.py                 Callbacks de visualización + modal de informe PDF.
  graficar_layout.py          Layout de la página Graficar.
  correcciones.py             Callbacks de corrección (bias, spikes).
  correcciones_layout.py      Layout de Correcciones.
  importar_umbrales.py        Importación de umbrales desde Excel.
  configuraciones.py          Stub vacío.

utils/
  report_engine.py            Fachada del motor HTML: recibe plantilla+context, devuelve PDF.
  template_service.py         Carga de plantillas y scripts (API reducida; funciones del editor en info/legacy/).
  script_registry.py          Registro/descubrimiento de scripts (@register_script).
  asset_manager.py            Gestión centralizada de imágenes (_assets/).
  funciones_importar.py       Parsers de datos de sensor.
  funciones_graficar.py       Construcción de figuras Plotly.
  funciones_correcciones.py   Algoritmos de corrección.
  funciones_comunes.py        Utilidades compartidas.
  dev_logging.py              Monkey-patch de logging de callbacks (DEBUG_CALLBACKS=1).

engines/
  html_engine.py              Motor HTML trasplantado de Maketator. NO parchear localmente.

models/
  server.py                   Stub vacío (requerido por html_engine).
  database.py                 Stub vacío (requerido por html_engine).

biblioteca_plantillas/html/   Plantillas en formato HTML.
biblioteca_graficos/html/     Scripts de gráficos con namespace html/.
biblioteca_tablas/funciones/  Scripts de tablas.
json_inclis/                  JSONs de sensor escritos en runtime. Excluidos del reloader.
_assets/                      Imágenes centralizadas (registry.json + archivos por hash).

info/legacy/                  Código archivado (ReportLab, editor visual, callbacks de vista previa).
  motor_reportlab/            Motor ReportLab original (pdf_generator.py, report_engine.py).
  graficos_reportlab/         Scripts de gráficos para el motor ReportLab.
  tablas_reportlab/           Scripts de tablas para el motor ReportLab.
  template_models.py          Modelos Pydantic del editor visual (Plantilla, Elemento, TipoElemento).
  template_service_editor_funcs.py  Funciones del editor (guardar_plantilla, fusionar_grupo, etc.).
  graficar_vista_previa_legacy.py   Callbacks de vista previa ReportLab/matplotlib.
  funciones_informe_inclinometro_legacy.py  Mini-motor ReportLab de informe.
```

---

## Deuda técnica activa

| Item | Prioridad |
|---|---|
| `pages/graficar.py` — callbacks `actualizar_graficos` y `actualizar_grafico_temporal` muy largos | Media |
| `models/server.py` y `models/database.py` — stubs que ocultan dependencias de Maketator | Baja |
| `biblioteca_plantillas/incli_L9_BCN_v0[b]/` — corchetes en nombre pueden romper glob | Baja |

# Estado del Proyecto — maketador_web
_Generado: 2026-04-02_

---

## 1. Arquitectura general

Maketator Web es una plataforma para generación automática de informes PDF desde plantillas visuales. Combina tres capas:

**Editor visual (React + TypeScript):** Un componente Dash personalizado (`dce.Editor`) que permite diseñar plantillas arrastrando elementos (texto, imagen, tabla, gráfico, línea, rectángulo) sobre un canvas A4. El estado del canvas vive en un Zustand store y se serializa a JSON.

**Gestión y dispatch (Dash + Python):** La página `dispatch_table.py` gestiona los `ReportDefinition` (qué plantilla, con qué servidor, con qué sensores). El `JobRunner` ejecuta la generación en threads, persiste el resultado en SQLite y notifica el progreso via callbacks Dash.

**Motores de renderizado (Python):** El JSON de la plantilla se procesa por uno de dos motores (seleccionado por el campo `"engine"` en el JSON):
- **`html_engine.py`:** Genera HTML con posiciones CSS absolutas (en cm), lo renderiza con Playwright headless → PDF. Usa Plotly para gráficos.
- **`reportlab_engine.py`:** Dibuja directamente en canvas ReportLab. Usa Matplotlib para gráficos.

**Flujo de datos resumido:**
```
Editor React → JSON plantilla (biblioteca_plantillas/)
    ↓
dispatch_table.py: selección de informe + sensores + fechas
    ↓
JobRunner → report_engine.py (factory) → html_engine | reportlab_engine
    ↓
engine: recorre elementos JSON → renderiza cada tipo
    ↓
Para tablas: _generate_rows_from_cells() + funciones de celda (biblioteca_tablas/funciones/)
Para gráficos: genera script de biblioteca_graficos/ → Figure/HTML
    ↓
output/YYYY/MM/nombre.pdf
```

---

## 2. Stack tecnológico

### Backend Python 3.12+
| Librería | Versión | Uso |
|---|---|---|
| Dash | ≥2.17 | Framework web + multi-página |
| dash-mantine-components | 2.6.0 (fija) | UI components (Button, Modal, Grid…) |
| dash-ag-grid | ≥31.0 | Tablas editables |
| ReportLab | ≥4.1 | Motor PDF directo |
| Matplotlib | ≥3.8 | Gráficos en motor ReportLab |
| Playwright | ≥1.40 | Headless Chromium → PDF (motor HTML) |
| Plotly | ≥5.18 | Gráficos interactivos en motor HTML |
| SQLModel + SQLAlchemy | — | ORM + SQLite |
| Pandas | ≥2.2 | Procesamiento de datos |
| cryptography (Fernet) | ≥41.0 | Cifrado de contraseñas de servidor |
| pymysql / psycopg2 / pyodbc | — | Conexiones a BD remotas |
| python-dotenv | ≥1.0 | Variables de entorno |
| Plataforma | Linux + Windows | Rutas con pathlib.Path, encoding UTF-8 explícito en todos los open() |

**Motor activo por defecto:** `"reportlab"` (campo `"engine"` en plantilla JSON).

### Frontend React 18.3.1 + TypeScript 5.8.3
| Librería | Versión | Uso |
|---|---|---|
| Zustand | 5.0.11 | State management del canvas |
| @dnd-kit/core | 6.3.1 | Drag & drop de elementos |
| Radix UI (11+ paquetes) | — | Primitivos UI (accordion, dialog…) |
| TailwindCSS | 3.4.17 | Styling |
| Framer Motion | — | Animaciones en canvas |
| Recharts | 2.15.4 | Gráficos en UI |
| React Hook Form + Zod | 7.61.1 / 3.25 | Formularios con validación |
| lucide-react | 0.462.0 | Iconos |
| Webpack | 5.84.1 | Build → `dash_component_editor.min.js` |

---

## 3. Mapa de archivos — Backend Python

### Punto de entrada
| Archivo | Propósito | Funciones/clases clave | Depende de |
|---|---|---|---|
| `app.py` | Entry point Dash multi-página, AppShell, init DB, dark mode | `app`, `server`, layout con navbar, `clientside_callback` (AG Grid dark sync) | `models/database.py`, `pages/*`, `utils/ui_blueprints.py` |

### Páginas (`pages/`)
| Archivo | Propósito | Callbacks principales | Depende de |
|---|---|---|---|
| `pages/dispatch_table.py` | CRUD ReportDefinition, batch generation, preview | `load_rows`, `create_rd`, `update_cell_db`, `start_batch`, `poll_batch_progress`, `update_wizard_ui`, `abrir_modal_formato` | `models/dispatch.py`, `core/job_runner.py`, `utils/template_service.py`, `utils/report_engine.py` |
| `pages/editor_visual.py` | Editor visual de plantillas JSON | `cargar_plantilla`, `guardar_plantilla`, `exportar_grupo`, `importar_grupo`, `detectar_accion_crear_grupo`, `confirmar_crear_grupo`, `confirmar_overwrite_grupo` | `utils/template_service.py`, `utils/funciones_grupos.py`, `dash_component_editor` |
| `pages/admin_servidores.py` | CRUD servidores BD remotas | `create_server`, `edit_server`, `test_conexion`, `smart_port` | `models/server.py`, `utils/security.py`, `utils/server_tester.py` |
| `pages/historial.py` | Visor AG Grid de ReportJob con colores por estado | `refresh_historial` | `models/dispatch.py`, `models/database.py` |

### Motores (`engines/`)
| Archivo | Propósito | Funciones clave | Depende de |
|---|---|---|---|
| `engines/base.py` | Contrato abstracto `BaseReportEngine` | `render()`, `render_preview_png()` | — |
| `engines/html_engine.py` | Motor HTML/Playwright → PDF | `_elem_rect`, `_elem_linea`, `_elem_texto`, `_elem_imagen`, `_elem_imagen_dinamica`, `_elem_grafico`, `_elem_tabla`, `_build_html_cuadricula`, `_generate_rows_from_cells`, `_generate_placeholder_rows`, `_build_html` | `utils/script_registry.py`, `utils/cell_function_registry.py`, Playwright |
| `engines/reportlab_engine.py` | Motor ReportLab → PDF | `_draw_rect`, `_draw_line`, `_draw_text`, `_draw_imagen`, `_draw_imagen_dinamica`, `_draw_grafico`, `_draw_tabla`, `_fetch_script_data`, `_resolve_params`, `_resolve_tokens`, `_render_all_pages` | `utils/script_registry.py`, ReportLab, Matplotlib |

### Servicios (`utils/`)
| Archivo | Propósito | Funciones clave | Depende de |
|---|---|---|---|
| `utils/report_engine.py` | Factory de motores (router) | `generate_report_pdf()`, `generate_report_pdf_from_state()`, `render_preview_png()`, `_get_engine()` | `engines/*` |
| `utils/template_service.py` | Gestión de plantillas JSON | `listar_plantillas_disponibles()`, `cargar_plantilla()`, `guardar_plantilla()`, `extraer_params_clasificados()`, `extraer_textos_editables()`, `extraer_todos_parametros_current()`, `extraer_parametros_por_elemento()`, `fusionar_grupo_en_plantilla()`, `importar_grupo_desde_bytes()`, `listar_scripts_graficos()`, `listar_scripts_tablas()`, `listar_plantillas_tabla()`, `cargar_plantilla_tabla()`, `guardar_plantilla_tabla()`, `obtener_params_map_scripts()`, `listar_funciones_celda()` | `biblioteca_plantillas/`, `biblioteca_tablas/plantillas/`, `utils/script_registry.py` |
| `utils/script_registry.py` | Registry singleton de scripts gráficos | `ScriptRegistry._scan()`, `get_params(script_name)` | `biblioteca_graficos/` |
| `utils/cell_function_registry.py` | Carga dinámica de funciones de celda | `get_function(name)`, `list_functions()` | `biblioteca_tablas/funciones/` |
| `utils/ui_blueprints.py` | Abstracciones DMC reutilizables | `icon_button()`, `notify()`, `form_modal()`, `render_card()`, `two_col_row()` | dash-mantine-components |
| `utils/security.py` | Cifrado Fernet de contraseñas | `encrypt_pwd()`, `decrypt_pwd()` | cryptography |
| `utils/server_tester.py` | Test de conexión a BD remota (timeout 5s) | `test_server_connection(server)` | pymysql / psycopg2 / pyodbc |
| `utils/asset_manager.py` | Gestión de assets (imágenes de plantilla) | `register_asset()`, `get_asset_path()`, `track_usage()` | — |
| `utils/funciones_grupos.py` | Gestión de grupos de elementos en disco | `guardar_nuevo_grupo()`, `grupo_existe()`, `listar_grupos_disponibles()`, `exportar_grupo_zip()`, `leer_datos_grupo()` | `utils/asset_manager.py` |

### Modelos (`models/`)
| Archivo | Propósito | Clases clave | Depende de |
|---|---|---|---|
| `models/database.py` | Engine SQLite, init, migración | `init_db()`, `get_session()`, `_migrate_schema()` | SQLModel, todos los modelos |
| `models/dispatch.py` | Modelos de informe y job | `ReportDefinition`, `ReportJob`, `ExecutionLog`, `JobStatus`, `ColumnSchema` | SQLModel |
| `models/server.py` | Modelo de servidor BD remoto | `Server` | SQLModel |
| `models/template_models.py` | Tipos de plantilla (mínimo) | — | — |

### Core (`core/`)
| Archivo | Propósito | Clases/funciones clave | Depende de |
|---|---|---|---|
| `core/job_runner.py` | Orquestador batch con threading | `JobRunner`, `.run()` | `utils/report_engine.py`, `models/dispatch.py` |
| `core/data_fetcher.py` | Conexión a servidores SQL remotos | `fetch_dataframe()`, `fetch_sensor_data()`, `fetch_temporal_data()` | pymysql, psycopg2, pyodbc |

### Bibliotecas de contenido
| Directorio | Contenido | Convención |
|---|---|---|
| `biblioteca_graficos/html/` | 4 scripts Plotly (`grafico_spline_l9.py`, `grafico_spline_l9_v1.py`, `grafico_base_plotly.py`, `kpi_asentamiento.py`) | `generate(params, figsize) → str (HTML)` + `PARAMETER_METADATA` |
| `biblioteca_graficos/reportlab/` | 7 scripts Matplotlib (`grafico_incli_*.py`, `temporal_1eje_draft_00.py`, `test_grafico_temporal_00.py`) | `generate(params, figsize) → matplotlib.Figure` + `PARAMETER_METADATA` |
| `biblioteca_tablas/funciones/` | 5 funciones de celda (`ultimo_dato.py`, `penultimo_dato.py`, `incremento.py`, `fecha_anterior.py`, `fecha_ultima.py`) | `evaluate(params, data, context) → float\|str` + `CELL_FUNCTION_METADATA` |
| `biblioteca_tablas/html/` | 2 tablas legacy (`tabla_pernos.py`, `tabla_resumen_l9.py`) | Scripts con `generate()` |
| `biblioteca_plantillas/html/` | 7 plantillas JSON (test_temporal_10a/b/c, L9_Modern_Dashboard…) | `{nombre}/{nombre}.json` |
| `biblioteca_plantillas/reportlab/` | 5 plantillas JSON (`temporal_test_01`…`04a`) | idem |

---

## 4. Mapa de archivos — Frontend React

Todos bajo `dash_component_editor_src/src/lib/`

| Archivo | Propósito | Componentes/hooks exportados | Depende de |
|---|---|---|---|
| `components/Editor.react.tsx` | Componente Dash (punto de entrada) | `Editor` (default export) | `templateStore.ts`, `TemplateEditor.tsx` |
| `internal/store/templateStore.ts` | Zustand store — modelo central de datos | `useTemplateStore`, tipos: `TemplateElement`, `ElementType`, `ElementStyle`, `Cuadricula`, `GridColumn`, `ColumnOrigin`, `ParamValue`, `ParamClasificacion`, `ParamMetadata`, `ChartConfig`, `MapaConfig`, `MapaConfigGis`, `MapaConfigFolium`, `PendingAction`, `CellFunctionMeta`; acciones: `dispatchAction()`, `setScriptParamsMap()`, `setCellFunctions()` | zustand |
| `internal/components/editor/TemplateEditor.tsx` | Orquestador principal del editor | `TemplateEditor` | `EditorCanvas`, `PropertiesPanel`, `EditorHeader`, `ToolsSidebar`, @dnd-kit |
| `internal/components/editor/EditorCanvas.tsx` | Canvas A4 con rulers y elementos | `EditorCanvas` | `CanvasElement.tsx`, `templateStore.ts` |
| `internal/components/editor/CanvasElement.tsx` | Elemento individual en el canvas | `CanvasElement` | `templateStore.ts`, framer-motion |
| `internal/components/editor/PropertiesPanel.tsx` | Panel lateral de propiedades | `PropertiesPanel` + sub-componentes internos: `NumericField`, `ColorInput`, `LineaSection`, `ImageModeWrapper`, `ChartSection`, `ScriptParamsForm`, `ParamPrimaryToggle`, `TableSection`, `CellFormatModal`, `ColumnOriginEditor`; panel multi-selección con `dispatchAction` | `templateStore.ts`, Radix UI |
| `internal/components/editor/EditorHeader.tsx` | Barra superior: zoom, grid, motor | `EditorHeader` | `templateStore.ts` |
| `internal/components/editor/ToolsSidebar.tsx` | Paleta de herramientas con drag | `ToolsSidebar` | `templateStore.ts`, @dnd-kit |
| `internal/components/editor/JsonInspector.tsx` | Inspector JSON del estado actual | `JsonInspector` | `templateStore.ts` |
| `internal/components/ui/` | Primitivos shadcn/ui (35+ archivos) | button, input, select, slider, dialog, accordion, tabs… | Radix UI, TailwindCSS |
| `internal/hooks/use-mobile.tsx` | Hook breakpoint mobile | `useIsMobile` | — |

---

## 5. Modelo de datos — Elemento de plantilla

### Esquema completo de `TemplateElement`

```json
{
  "id": "el_1234567890_abcdefgh",
  "tipo": "texto|imagen|linea|rectangulo|grafico|tabla|mapa",

  "geometria": {
    "x": 1.0,
    "y": 2.0,
    "ancho": 8.0,
    "alto": 3.0
  },

  "estilo": {
    "color": "#000000",
    "color_relleno": "#ffffff",
    "color_borde": "#cbd5e1",
    "grosor_borde": 1,
    "opacidad": 1.0,
    "familia_fuente": "Arial",
    "tamano": 14,
    "negrita": "normal|bold",
    "cursiva": "normal|italic",
    "alineacion_h": "left|center|right"
  },

  "contenido": {
    "texto": "Texto con tokens {{zona}} o {{$CURRENT_sensor}}"
  },

  "metadata": {
    "zIndex": 0,
    "visible": true,
    "grupo": "encabezado"
  },

  "configuracion": {
    "PARA TIPO linea (modelo nuevo)": {
      "x1": 1.0, "y1": 2.0,
      "x2": 8.0, "y2": 2.0,
      "grosor": 1,
      "color": "#000000",
      "estilo_linea": "solida|discontinua|punteada"
    },
    "PARA TIPO grafico": {
      "script": "grafico_spline_l9_v1.py",
      "formato": "svg|png",
      "parametros": {
        "sensor": "$CURRENT",
        "fecha_inicio": "$CURRENT_fecha_inicial",
        "fecha_fin": "$CURRENT_fecha_final"
      },
      "params_clasificacion": {
        "sensor":       { "tipo": "primario",   "label": "Sensor" },
        "fecha_inicio": { "tipo": "secundario",  "label": "Fecha inicio" },
        "fecha_fin":    { "tipo": "secundario",  "label": "Fecha fin" }
      },
      "descripcion": "Texto descriptivo opcional. Acepta tokens {{clave}}. Se renderiza en 8pt gris debajo del elemento."
    },
    "PARA TIPO tabla (configuracion)": {
      "descripcion": "Igual que grafico — campo opcional en configuracion. Los motores leen configuracion.descripcion para ambos tipos."
    },
    "PARA TIPO linea (modelo nuevo)": {
      "x1": 1.0, "y1": 2.0,
      "x2": 8.0, "y2": 2.0,
      "grosor": 1,
      "color": "#000000",
      "estilo_linea": "solida|discontinua|punteada"
    }
  },

  "mapa_config": {
    "fuente": "gis|folium",
    "gis": {
      "operacion": "planoarea",
      "obra": "OBRA-01",
      "sistema": "",
      "capas": "",
      "padding": 50,
      "ancho_minimo": 800
    },
    "folium": {
      "tile_layer": "cartodb|esri",
      "algoritmo_anticolision": false,
      "zoom_padding": 50
    },
    "posicion_imagen": "center|top|bottom|left|right",
    "ajuste": "contain|cover",
    "mapa_params_clasificacion": {
      "obra": { "tipo": "primario", "label": "Obra" }
    },
    "descripcion": "Texto descriptivo opcional. Acepta tokens {{clave}}. Se renderiza en 8pt gris debajo del mapa."
  },

  "imagen": {
    "formato": "png|jpg",
    "datos_temp": "<base64>",
    "ruta_original": "assets/logo.png",
    "ruta_nueva": "assets/logo_nueva.png",
    "nombre_archivo": "logo.png",
    "estado": "pendiente|guardada"
  },

  "imagen_config": {
    "modo": "estatica|dinamica",
    "nombre_imagen": "121212_ejemplo.png",
    "marco": {
      "borde_ancho": 0,
      "borde_color": "#e2e8f0",
      "borde_radio": 0,
      "fondo": "transparent"
    },
    "posicion": "center|top|bottom|left|right",
    "ajuste": "contain|cover"
  },

  "cuadricula": {
    "niveles": [
      {
        "tipo": "fijo",
        "columnas": [
          {
            "ancho": 3.0,
            "contenido": "Sensor",
            "origen": { "tipo": "fijo" },
            "formato": {
              "fuente": "Aptos",
              "tamano": 10,
              "color_texto": "#000000",
              "color_fondo": "#ffffff",
              "alineacion": "left|center|right",
              "negrita": false
            },
            "bordes": {
              "superior":  { "activo": true,  "grosor": 1, "color": "#000000" },
              "inferior":  { "activo": true,  "grosor": 1, "color": "#000000" },
              "izquierdo": { "activo": false, "grosor": 1, "color": "#000000" },
              "derecho":   { "activo": false, "grosor": 1, "color": "#000000" }
            }
          }
        ]
      },
      {
        "tipo": "autorrelleno",
        "num_filas": 10,
        "zebra": true,
        "color_par": "#ffffff",
        "color_impar": "#f8fafc",
        "columnas": [
          {
            "ancho": 3.0,
            "contenido": "{{NOM_SENSOR}}",
            "origen": {
              "tipo": "funcion",
              "funcion": "ultimo_dato",
              "parametros": {
                "sensor":        { "ref": "ancla" },
                "fecha_limite":  { "ref": "contexto", "clave": "fecha_seleccionada" },
                "decimales":     { "ref": "literal", "valor": 2 }
              }
            },
            "formato": { "fuente": "Aptos", "tamano": 10, "color_texto": "#000000", "color_fondo": "#ffffff", "alineacion": "right", "negrita": false },
            "bordes": { "superior": {"activo":false,"grosor":1,"color":"#000"}, "inferior": {"activo":true,"grosor":1,"color":"#e2e8f0"}, "izquierdo": {"activo":false,"grosor":1,"color":"#000"}, "derecho": {"activo":false,"grosor":1,"color":"#000"} }
          }
        ]
      }
    ],
    "columna_ancla": 0,
    "fuente_ancla": "$CURRENT",
    "fuente_ancla_primario": true,
    "fuente_ancla_label": "Sensor"
  }
}
```

### Nota sobre `configuracion` para líneas (modelo nuevo vs legado)

- **Nuevo (desde iteración actual):** `configuracion.x1/y1/x2/y2` + `grosor` + `color` + `estilo_linea`. La `geometria` se deriva automáticamente como bounding box.
- **Legado:** Sin `configuracion`, usa `geometria.ancho/alto` como vector dirección. Ambos motores tienen fallback.

---

## 6. Flujo de generación de PDF

```
┌──────────────────────────────────────────────────────────────┐
│  Editor React (CanvasElement → Zustand store)               │
│  Serializa → JSON plantilla + guarda en biblioteca_plantillas│
└──────────────────────────────────────────────────────────────┘
                         ↓ JSON
┌──────────────────────────────────────────────────────────────┐
│  dispatch_table.py                                           │
│  ReportDefinition: template_name + context (sensores, fechas)│
│  → JobRunner.run()                                           │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│  utils/report_engine.py → _get_engine(template_name)        │
│  Lee campo "engine" del JSON → selecciona motor             │
└──────────────────────────────────────────────────────────────┘
          ↓ "html"                    ↓ "reportlab"
┌──────────────────┐       ┌────────────────────────┐
│ html_engine.py   │       │ reportlab_engine.py     │
│                  │       │                         │
│ Por cada página: │       │ Por cada página:        │
│ Por cada elem:   │       │ Por cada elem:          │
│                  │       │                         │
│ tipo→función:    │       │ tipo→función:           │
│ texto →_elem_texto│       │ texto →_draw_text      │
│ imagen→_elem_imagen│      │ imagen→_draw_imagen    │
│ linea →_elem_linea│       │ linea →_draw_line      │
│ rect  →_elem_rect │       │ rect  →_draw_rect      │
│ grafico→_elem_grafico     │ grafico→_draw_grafico  │
│ tabla →_elem_tabla│       │ tabla →_draw_tabla     │
│                  │       │                         │
│ → HTML string    │       │ → ReportLab canvas      │
│ → Playwright→PDF │       │ → canvas.save() → PDF   │
└──────────────────┘       └────────────────────────┘
          ↓                           ↓
┌──────────────────────────────────────────────────────────────┐
│  Para tablas tipo "autorrelleno":                            │
│  _generate_rows_from_cells()                                 │
│  → Por cada fila de sensor (columna_ancla):                  │
│     → Por cada columna tipo "funcion":                       │
│        → cell_function_registry.get_function(nombre)        │
│        → evaluate(params_resueltos, data, context)           │
└──────────────────────────────────────────────────────────────┘
          ↓
┌──────────────────────────────────────────────────────────────┐
│  Para gráficos:                                              │
│  script_registry.get_params(script_name)                    │
│  → import script → generate(params, figsize)                │
│  → Figure (Matplotlib) | HTML string (Plotly)               │
└──────────────────────────────────────────────────────────────┘
          ↓
    output/YYYY/MM/nombre.pdf
```

---

## 7. Estado de implementación por funcionalidad

| Funcionalidad | Estado | Archivos implicados | Notas |
|---|---|---|---|
| Elementos: texto | ✅ Completo | `html_engine._elem_texto`, `reportlab._draw_text` | Tokens `{{clave}}` resueltos desde context |
| Elementos: imagen estática | ✅ Completo | `html_engine._elem_imagen`, `reportlab._draw_imagen` | Base64 embebido o ruta relativa |
| Elementos: imagen dinámica | ✅ Completo | `html_engine._elem_imagen_dinamica`, `reportlab._draw_imagen_dinamica` | `imagen_config.modo = "dinamica"`, nombre desde dispatch |
| Elementos: rectángulo | ✅ Completo | `html_engine._elem_rect`, `reportlab._draw_rect` | Relleno + borde |
| Elementos: línea | ✅ Completo (nuevo modelo) | `html_engine._elem_linea`, `reportlab._draw_line`, `CanvasElement.tsx` | Modelo x1/y1/x2/y2 + estilo_linea; fallback a geometría legada |
| Elementos: gráfico | ✅ Completo | `html_engine._elem_grafico` + `_elem_caption_html`, `reportlab._draw_grafico` + `_draw_caption`, `PropertiesPanel.tsx ChartSection` | `params_clasificacion` inicializado por `ChartSection`; soporta `configuracion.descripcion` (caption 8pt gris debajo del elemento, acepta tokens) |
| Elementos: tabla (script legacy) | ✅ Completo | `html_engine._elem_tabla` → `_build_html_table_from_data` + `_elem_caption_html`, `reportlab._run_tabla_script_rl` + `_draw_caption` | Scripts en `biblioteca_tablas/html/`; soporta `configuracion.descripcion` (mismo campo que gráfico) |
| Elementos: tabla (celda a celda) | ✅ Completo | `html_engine._build_html_cuadricula`, `_generate_rows_from_cells`, `PropertiesPanel.tsx TableSection` | Funciones de celda, columna ancla, zebra; `fuente_ancla_primario/label`; caption vía `configuracion.descripcion`; **plantillas de cuadrícula** cargables desde `biblioteca_tablas/plantillas/` (Select + botón Save en TableSection; API Flask `GET/POST /api/tabla-plantilla`) |
| Elementos: mapa | ✅ Completo | `html_engine._elem_mapa` + `_elem_caption_html`, `html_engine._elem_mapa_folium`, `reportlab._draw_mapa` + `_draw_caption`, `PropertiesPanel.tsx MapaSection` | GIS → API `gis2png`; Folium → mapa vía Playwright; `mapa_params_clasificacion`; soporta `mapa_config.descripcion` (caption 8pt gris debajo del elemento) |
| Editor visual: drag & drop | ✅ Completo | `CanvasElement.tsx`, `EditorCanvas.tsx`, `ToolsSidebar.tsx` | @dnd-kit |
| Editor visual: resize | ✅ Completo | `CanvasElement.tsx handleResizeStart` | Handle SE para no-líneas |
| Editor visual: línea con extremos arrastrables | ✅ Completo | `CanvasElement.tsx handleEndpointMouseDown` | Ctrl → ortogonal; drag cuerpo sincroniza configuracion |
| Editor visual: undo/redo | ✅ Completo | `templateStore.ts undo()/redo()` | Debounce 1.5s, stack de acciones |
| Generación PDF: motor HTML | ✅ Completo | `engines/html_engine.py`, Playwright | Requiere `playwright install chromium` |
| Generación PDF: motor ReportLab | ✅ Completo | `engines/reportlab_engine.py` | Motor por defecto |
| Dispatch table / modal de informe | ✅ Completo | `pages/dispatch_table.py` | CRUD, bulk update, duplicar, batch |
| Textos editables en dispatch (inline) | ✅ Completo | `dispatch_table.py update_cell_db` | cellValueChanged → auto-save |
| Grupos de elementos | ✅ Completo | `editor_visual.py`, `utils/funciones_grupos.py` | Export/import como ZIP; `grupo_existe()` + modal overwrite; botón "Guardar en biblioteca" via `dispatchAction` |
| Importar/exportar grupos | ✅ Completo | `editor_visual.py exportar_grupo/importar_grupo` | ZIP con JSON + assets; selector auto-refrescado al abrir modal |
| Vista previa (maquetación) | ✅ Completo | `dispatch_table.py`, `utils/report_engine.render_preview_png()` | `is_maquetacion=True` → placeholder rows |
| Wizard de mapeo de parámetros | ✅ Completo | `dispatch_table.py update_wizard_ui`, `template_service.extraer_params_clasificados()` | Modelo `params_clasificacion` (gráficos) + `fuente_ancla_primario/label` (tablas) + `mapa_params_clasificacion` (mapas) |
| ColumnSchema (columnas dispatch table dinámicas) | ✅ Completo | `models/dispatch.py ColumnSchema`, `pages/dispatch_table.py` | Columnas obligatorias + custom editables en AG Grid |
| Textos editables en wizard | ✅ Completo | `template_service.extraer_textos_editables()`, `dispatch_table.py` | Bloque 4 del wizard: Textarea por elemento `editable:true` |
| Gestión de servidores BD | ✅ Completo | `pages/admin_servidores.py`, `models/server.py`, `utils/security.py` | MySQL, PostgreSQL, SQL Server, SQLite |
| Dark Mode (modo oscuro) | ✅ Completo | `app.py`, `assets/dark_mode.css`, `assets/dashAgGridFunctions.js` | `defaultColorScheme="auto"`, `ColorSchemeToggle`, AG Grid sync via clientside callback, persistencia en localStorage |

---

## 8. Problemas conocidos y deuda técnica

| # | Problema | Archivo | Severidad |
|---|---|---|---|
| 1 | `print()` residual eliminado de `reportlab._draw_line` — ya corregido | `engines/reportlab_engine.py` | Resuelto ✅ |
| 2 | Archivos huérfanos en `output/` si falla generación a mitad | `core/job_runner.py` | Baja — sin GC automático |
| 3 | `build:py` en `package.json` apunta a ruta hardcodeada de otro venv | `dash_component_editor_src/package.json` | Baja — solo afecta si cambia la API del componente |
| 4 | `servers.json` legacy con credenciales sin cifrar coexiste con el nuevo modelo `Server` cifrado | raíz del proyecto | Media — riesgo de seguridad si se usa |
| 5 | Sesión SQLAlchemy y threading: definiciones deben cargarse fuera del hilo | `core/job_runner.py` | Documentado — vigilar en cambios futuros |
| 6 | SQL Server requiere `unixodbc` instalado en Linux (`sudo apt install unixodbc`) | `utils/server_tester.py` | Documentado |
| 7 | Motor HTML requiere `playwright install chromium` post-instalación | `engines/html_engine.py` | Documentado |
| 8 | Funciones de celda con `ref_celda`: valores deben venir resueltos por el motor; no acceden a `data["historico"]` directamente | `biblioteca_tablas/funciones/` | Media — validación de tipos débil |
| 9 | `params_clasificacion` queda `{}` en gráficos si el usuario nunca tocó los toggles P/S al guardar la plantilla. Fix parcial: `ChartSection.useEffect` sincroniza al reabrir, pero no retroactivo si el script no está en `scriptParamsMap` en ese instante. | `PropertiesPanel.tsx ChartSection`, `utils/template_service.py extraer_params_clasificados()` | Media — wizard no muestra acordeón para ese gráfico |
| 10 | Elemento `mapa` con fuente `folium` requiere `folium` y `pyproj` instalados. Sin ellos devuelve placeholder sin error visible en UI. | `engines/html_engine.py _elem_mapa_folium` | Baja — dependencia opcional |
| 11 | `pendingAction` del store React se limpia via `setTimeout(0)` tras `dispatchAction` — funciona pero es una heurística de timing, no un ACK real de Dash | `PropertiesPanel.tsx dispatchCreateGroup`, `Editor.react.tsx StoreSync` | Baja — solo afecta si el store cambia en el mismo tick |
| 12 | `build:py` en `package.json` usa ruta hardcodeada a venv Unix — no funciona en Windows tal cual | `dash_component_editor_src/package.json` | Baja — solo afecta si se recompila la API Python del componente; `build:js` funciona en ambas plataformas |
| 13 | SQL Server en Windows requiere ODBC Driver 17 instalado manualmente (distinto a unixodbc en Linux) | `utils/server_tester.py`, `core/data_fetcher.py` | Documentado en README — no es un bug sino una diferencia de plataforma |
| 14 | Playwright en Windows descarga Chromium en `%USERPROFILE%\AppData\Local\ms-playwright` — no compartido con instalación Linux | `engines/html_engine.py` | Documentado — requiere `playwright install chromium` por separado en cada OS |
| 15 | ✅ **RESUELTO 2026-04-25** `_resolve_params` diverge entre motores: html_engine sanitiza 7 claves numéricas; reportlab_engine solo 5. Fix: añadidos `y_decimals` y `label_size` al loop de reportlab | `engines/reportlab_engine.py` | ✅ |
| 16 | ✅ **RESUELTO 2026-04-25** `_ctx_lookup` diverge: html_engine no tenía case `total_camp`. Fix: añadido `if param_name == "total_camp": return ... or 10` en html_engine | `engines/html_engine.py` | ✅ |
| 17 | ✅ **RESUELTO 2026-04-25** `_CURRENT_TOKEN_MAP` solo existía en html_engine. Fix: añadido como constante de módulo en reportlab_engine sincronizado con html_engine | `engines/reportlab_engine.py` L57–64 | ✅ |
| 18 | ✅ **RESUELTO 2026-04-25** `servers.json` era infraestructura activa en 5 módulos con credenciales en texto plano. Fix: engines migrados a ORM `Server` + Fernet; dispatch_table migrado a ORM; `core/data_fetcher.load_servers` ya no se importa en dispatch_table | Todos los módulos citados | ✅ |
| 19 | ✅ **RESUELTO 2026-04-25** `_fetch_script_data` en ambos engines usaba `get_server()` de servers.json. Fix: usa `context["_server"]` (ORM Server ya resuelto) o fallback ORM por nombre/ID con `_orm_server_to_config()` | `engines/html_engine.py`, `engines/reportlab_engine.py` | ✅ |
| 20 | ✅ **RESUELTO 2026-04-25** 2 excepts completamente silenciosos en dispatch_table.py. Fix: añadidos `logger.warning(...)` en L38 (import template_service) y L123 (engine fallback) | `pages/dispatch_table.py` | ✅ |
| 21 | `dispatch_table.py` es un monolito de 5947 líneas (2.6× html_engine). Contiene ≥50 callbacks Dash, lógica CRUD, batch, wizard, modal de formato, undo/redo, edición masiva, duplicación y mapeo de parámetros mezclados. Dificulta testing y navegación | `pages/dispatch_table.py` | Baja — deuda de mantenibilidad a largo plazo; candidato a refactorizar en submódulos por dominio |
| 22 | ✅ **RESUELTO 2026-04-25** 3 `print()` en `seed_db.py`. Fix: añadido `logging.basicConfig` + `logger`, sustituidas las 3 llamadas por `logger.info()` | `seed_db.py` | ✅ |
| 23 | ✅ **RESUELTO 2026-04-25** Imágenes creadas con el editor no tenían `imagen_config.modo`, por lo que `dispatch_table.update_wizard_ui` las filtraba silenciosamente (requiere `modo == "dinamica"`). Causa raíz: `defaultElements['imagen']` en `TemplateEditor.tsx` no incluía `imagen_config`, y el spread al llamar `addElement` tampoco lo propagaba. Fix triple: (1) `defaultElements['imagen']` incluye `imagen_config` con `modo:"estatica"`; (2) `handleDragEnd` propaga `imagen_config` igual que `configuracion`/`mapa_config`; (3) `loadTemplate` en `templateStore.ts` inyecta `imagen_config` fallback para plantillas legacy | `TemplateEditor.tsx`, `templateStore.ts` | ✅ — `dispatch_table.py` añade `logger.debug` diagnóstico |

---

## 9. Guía "qué archivos pedir" por área de trabajo

### Para trabajar en el engine de renderizado HTML (render de elementos)
```
engines/html_engine.py
```
Opcionalmente si tocas tablas:
```
utils/cell_function_registry.py
biblioteca_tablas/funciones/{funcion}.py
```

### Para trabajar en el engine ReportLab (render de elementos)
```
engines/reportlab_engine.py
```

### Para añadir o modificar un tipo de elemento (ambos motores)
```
engines/html_engine.py          ← función _elem_{tipo}
engines/reportlab_engine.py     ← función _draw_{tipo}
dash_component_editor_src/src/lib/internal/components/editor/CanvasElement.tsx     ← case '{tipo}' en renderContent()
dash_component_editor_src/src/lib/internal/components/editor/PropertiesPanel.tsx   ← sección de propiedades
dash_component_editor_src/src/lib/internal/store/templateStore.ts                  ← tipos si se añaden campos
```

### Para trabajar en el canvas React (interacción visual)
```
dash_component_editor_src/src/lib/internal/components/editor/CanvasElement.tsx
dash_component_editor_src/src/lib/internal/store/templateStore.ts
```

### Para trabajar en el panel de propiedades
```
dash_component_editor_src/src/lib/internal/components/editor/PropertiesPanel.tsx
dash_component_editor_src/src/lib/internal/store/templateStore.ts
```
Si el cambio afecta a cómo se guarda en JSON (nuevos campos en `configuracion`):
```
engines/html_engine.py          ← también actualizar render
engines/reportlab_engine.py     ← también actualizar render
```

### Para trabajar en tablas (celda a celda)
```
dash_component_editor_src/src/lib/internal/components/editor/PropertiesPanel.tsx   ← TableSection, CellFormatModal, ColumnOriginEditor
engines/html_engine.py          ← _build_html_cuadricula, _generate_rows_from_cells
utils/cell_function_registry.py
biblioteca_tablas/funciones/    ← funciones individuales
```
Si la tabla es tipo autorrelleno con `fuente_ancla`:
```
utils/template_service.py       ← extraer_todos_parametros_current
pages/dispatch_table.py         ← update_wizard_ui
```
> **Regla para nuevas plantillas de tabla (JSON manual o importado):** El wizard NO mostrará sensor ni fechas si faltan estos campos en `cuadricula`. Checklist obligatorio:
> - `cuadricula.fuente_ancla = "$CURRENT"`
> - `cuadricula.fuente_ancla_primario = true`
> - `cuadricula.fuente_ancla_label = "Sensor"` (o etiqueta descriptiva)
> - En cada función de celda dependiente de fecha (`fecha_anterior`, `penultimo_dato`, `fecha_ultima`, `ultimo_dato`): añadir `"fecha_limite": { "ref": "contexto", "clave": "$CURRENT_fecha_fin", "primario": true, "label": "Fecha Límite" }` en sus `parametros`.
> Con el editor visual, el toggle P/S en ColumnOriginEditor escribe estos campos automáticamente.

### Para añadir una función de celda nueva
```
biblioteca_tablas/funciones/{nueva_funcion}.py    ← nueva función con CELL_FUNCTION_METADATA + evaluate()
utils/cell_function_registry.py                   ← verificar que el scan la detecta (automático)
```
No es necesario registrar manualmente — `cell_function_registry` hace scan dinámico.

### Para trabajar en gráficos (HTML/Plotly)
```
biblioteca_graficos/html/{script}.py
engines/html_engine.py          ← _elem_grafico (si cambias cómo se embebe)
utils/script_registry.py        ← si cambias metadata
```
Consultar también:
```
biblioteca_graficos/CLAUDE.md   ← estándares de ingeniería Plotly (§12–§24)
```

### Para trabajar en gráficos (ReportLab/Matplotlib)
```
biblioteca_graficos/reportlab/{script}.py
engines/reportlab_engine.py     ← _draw_grafico
```
Consultar también:
```
biblioteca_graficos/CLAUDE.md   ← estándares de ingeniería Matplotlib (§1–§11)
```

### Para trabajar en el dispatch table (gestión de informes)
```
pages/dispatch_table.py
models/dispatch.py
utils/template_service.py
```

### Para trabajar en el wizard de mapeo de parámetros
```
pages/dispatch_table.py         ← update_wizard_ui, abrir_modal_formato, _build_initial_wizard_values
utils/template_service.py       ← extraer_params_clasificados, extraer_parametros_por_elemento, extraer_textos_editables
```
**Inicialización universal del store:** `_build_initial_wizard_values(template_data, existing_mapeo, existing_custom)` construye los valores iniciales completos para `dt-wizard-values` y `dt-custom-settings-store` al abrir el modal. Itera `extraer_params_clasificados()` para todos los tipos de elemento. Añadir un nuevo tipo de elemento no requiere cambios aquí — solo requiere que `extraer_params_clasificados()` lo soporte.

Modelo de clasificación P/S:
- Gráficos: `configuracion.params_clasificacion[param].tipo` → `"primario"|"secundario"`.
- Tablas: `cuadricula.fuente_ancla_primario` (bool) + `fuente_ancla_label`; y por parámetro de función: `origen.parametros[p].primario` (bool) + `.label`.
- Mapas: `mapa_config.mapa_params_clasificacion[campo].tipo` → `"primario"|"secundario"`.

### Para trabajar en el sistema de grupos
```
pages/editor_visual.py          ← detectar_accion_crear_grupo, confirmar_crear_grupo, confirmar_overwrite_grupo, abrir_modal_exportar_grupo
utils/funciones_grupos.py       ← guardar_nuevo_grupo, grupo_existe, listar_grupos_disponibles
dash_component_editor_src/src/lib/internal/components/editor/PropertiesPanel.tsx  ← panel multi-selección, dispatchCreateGroup
```
Flujo completo: `dispatchAction({type:'create_group', elementIds:[...]})` en React → `StoreSync` emite `action` en `visual-editor.value` → `detectar_accion_crear_grupo` abre modal Dash → `confirmar_crear_grupo` llama a `guardar_nuevo_grupo` (con check `grupo_existe` + modal overwrite si duplicado).

### Para trabajar en el elemento mapa
```
engines/html_engine.py          ← _elem_mapa, _elem_mapa_folium
engines/reportlab_engine.py     ← _draw_mapa
dash_component_editor_src/src/lib/internal/store/templateStore.ts  ← MapaConfig, MapaConfigGis, MapaConfigFolium
dash_component_editor_src/src/lib/internal/components/editor/PropertiesPanel.tsx  ← sección mapa
utils/template_service.py       ← extraer_params_clasificados (bloque mapa)
```
Dependencias externas: `utils/gis_client.py` (API gis2png), `core/data_fetcher.fetch_sensor_coords`, `folium` + `pyproj` (fuente folium).

### Para trabajar en la gestión de servidores BD
```
pages/admin_servidores.py
models/server.py
utils/security.py
utils/server_tester.py
```

### Para trabajar en el editor visual (página Dash)
```
pages/editor_visual.py
utils/template_service.py
utils/ui_blueprints.py
```

### Para añadir una nueva página Dash
```
app.py                          ← registrar en navbar
pages/{nueva_pagina}.py         ← nueva página
utils/ui_blueprints.py          ← blueprints disponibles
```

### Para tocar el modelo de datos React (nuevos campos en elementos)
```
dash_component_editor_src/src/lib/internal/store/templateStore.ts
```
Después, actualizar los archivos que consumen esos campos:
```
CanvasElement.tsx               ← render visual
PropertiesPanel.tsx             ← controles de edición
engines/html_engine.py          ← render a HTML
engines/reportlab_engine.py     ← render a PDF
```
Y recompilar:
```bash
cd dash_component_editor_src && npm run build:js
```

### Para trabajar en los modelos SQL / migración de schema
```
models/database.py              ← _migrate_schema() — añadir columnas aquí
models/dispatch.py              ← campos SQL fijos de ReportDefinition
models/server.py                ← campos de Server
```
**Regla:** Nunca añadir columnas a `ReportDefinition`. Nuevos campos van en `context` (JSON).

Campos de `context` documentados: `zona`, `tipo`, `sector`, `seccion`, `activo`, `sensores_1`, `fecha_inicio`, `fecha_fin`, `server_id`, `mapeo_parametros`, `custom_chart_settings`, `imagenes_dinamicas`, `imagen_config_overrides`, `textos_editables`, `is_maquetacion`, `elem_nombres: dict` — `{elem_id: nombre_usuario}` nombres descriptivos de elementos de plantilla (generado por `_build_initial_wizard_values`).

### Para verificar compatibilidad cross-platform
```
models/database.py              ← construcción de ruta SQLite
utils/template_service.py       ← rutas a biblioteca_plantillas/
utils/script_registry.py        ← rutas a biblioteca_graficos/
utils/cell_function_registry.py ← rutas a biblioteca_tablas/
utils/funciones_grupos.py       ← rutas a grupos + assets
engines/html_engine.py          ← archivos temporales + Playwright
engines/reportlab_engine.py     ← rutas a assets
core/job_runner.py              ← rutas a output/
dash_component_editor_src/package.json ← scripts npm
```
Verificar: pathlib.Path, encoding="utf-8", tempfile, sin print().

---

## 10. Convenciones del proyecto

### Nombres de campos
- **JSON de plantilla / React:** español (`color_borde`, `grosor`, `alineacion_h`, `color_relleno`, `tamano`)
- **Engines Python:** leen español primero, fallback inglés (`estilo.get("color_borde") or estilo.get("borderColor")`)
- **No mezclar** dentro de un mismo objeto; el español es canónico

### Unidades
- **En JSON:** centímetros (`"x": 1.5` significa 1.5 cm)
- **En React canvas:** píxeles (factor `cmToPx = 37.8`)
- **En ReportLab:** puntos (`_CM = 28.3465`, `x_rl = x_cm * _CM`)
- **En HTML CSS:** unidades `cm` directamente (`left: 1.5cm`)

### Estructura de `configuracion` por tipo de elemento
| Tipo | Campos en `configuracion` |
|---|---|
| `linea` | `x1, y1, x2, y2` (cm), `grosor` (pt), `color` (hex), `estilo_linea` (solida\|discontinua\|punteada) |
| `grafico` | `script` (nombre archivo), `formato` (svg\|png), `parametros` (Record), `params_clasificacion` (Record&lt;string, {tipo: primario\|secundario, label: string}&gt;) |
| `tabla` | No usa `configuracion` — usa `cuadricula` en el nivel raíz del elemento |
| `imagen` | No usa `configuracion` — usa `imagen_config` |
| `mapa` | No usa `configuracion` — usa `mapa_config` en el nivel raíz del elemento |
| resto | Sin `configuracion` — todo en `estilo` + `contenido` |

### Patrón de callbacks Dash
```python
@app.callback(
    Output("componente", "prop"),
    Input("trigger", "prop"),
    prevent_initial_call=True,
)
def mi_callback(valor):
    ...
```
- `allow_duplicate=True` cuando múltiples callbacks escriben el mismo Output
- Blueprints: usar `notify()` de `utils/ui_blueprints.py` para notificaciones
- Nunca usar `print()` — usar `logger = logging.getLogger(__name__)`

### Patrón de funciones de celda
```python
CELL_FUNCTION_METADATA = { "nombre": "...", "devuelve": "...", "parametros": [...] }

def evaluate(params: dict, data: dict, context: dict) -> float | str:
    # params: valores ya resueltos (ref_celda → valor real)
    # data: {"historico": [...]}
    # context: contexto del informe (fechas, zona, etc.)
```

### Patrón de scripts de gráficos (HTML/Plotly)
```python
PARAMETER_METADATA: list[dict] = [...]
metadata = ScriptMetadata(...)

@register_script(metadata)
def generate(params: dict[str, Any], figsize: tuple[float, float]) -> str:
    # Retorna HTML string (pio.to_html(full_html=False, ...))
    # En caso de error: return _html_error("mensaje")
```

### Compilación del componente React
Después de cualquier cambio en `dash_component_editor_src/src/`:
```bash
cd dash_component_editor_src
npm run build:js        # Genera dash_component_editor.min.js
# No usar "npm run build" completo — build:py apunta a ruta hardcodeada de otro proyecto
```
Reiniciar la app tras el build para que Dash sirva el nuevo bundle.

### Compatibilidad cross-platform (Linux / Windows)
- **Rutas:** Usar siempre `pathlib.Path` con `_BASE_DIR` anclado a `Path(__file__).resolve().parent.parent`. No concatenar strings con `/`.
- **Encoding:** Todo `open()` en modo texto debe llevar `encoding="utf-8"`.
- **Archivos temporales:** Usar `tempfile.gettempdir()` o `tempfile.NamedTemporaryFile()`. No hardcodear `/tmp` ni `temp/`.
- **JSON:** Usar `json.dump(..., ensure_ascii=False)` para preservar caracteres españoles.
- **Logs:** Nunca `print()` — siempre `logger`. Windows cp1252 puede fallar con `print()` de caracteres no-ASCII.
- **npm scripts:** No usar comandos Unix (rm -rf, cp). Usar `npx shx` o `npx rimraf` si es necesario.

### Migración de schema SQL
Nuevas columnas en tablas existentes se añaden en `models/database.py → _migrate_schema()`:
```python
# Patrón: PRAGMA table_info + ALTER TABLE ADD COLUMN si no existe
```
No usar Alembic salvo activación explícita. Requiere SQLite ≥ 3.35 para `DROP COLUMN`.

---

## 11. Arquitectura de Elementos

---

### 11.1 ¿Cómo funciona un elemento? (Introducción divulgativa)

Imagina que Maketator Web es una imprenta automatizada. Tú diseñas la plantilla
(la maqueta), le dices qué datos usar, y la imprenta produce el PDF. Los
**elementos** son las piezas de esa maqueta: un titular, una tabla de lecturas,
un gráfico de evolución, un mapa de la obra.

#### El ciclo de vida de un elemento

**1. Diseño en el editor visual**

El usuario arrastra un elemento desde la paleta lateral al canvas A4. El canvas
es el editor React. Cada elemento ocupa una caja rectangular en el lienzo y
tiene propiedades que se pueden ajustar en el panel lateral:

- *¿Dónde está y cuánto ocupa?* → campos de **geometría** (x, y, ancho, alto en
  centímetros).
- *¿Qué aspecto tiene?* → campos de **estilo** (color, fuente, bordes, opacidad).
- *¿Qué muestra?* → el **contenido** y la **configuración específica** del tipo
  (para un gráfico: qué script ejecutar y con qué parámetros; para una tabla:
  qué columnas y funciones de celda; etc.).

Todo esto vive en el store de React (Zustand) y se serializa como JSON cuando el
usuario pulsa "Guardar plantilla". El JSON se guarda en `biblioteca_plantillas/`.

**2. Configuración en el dispatch table**

La plantilla define la *estructura*, pero no los datos concretos: no sabe aún de
qué sensor habla ni qué fechas cubrir. Eso lo decide el usuario en la página
de Dispatch Table (gestión de informes).

Aquí, cada fila es un `ReportDefinition`: plantilla + servidor de datos +
sensores + fechas. El **wizard de mapeo** recorre la plantilla y muestra los
parámetros que necesitan un valor real (los marcados como **primarios**). El
usuario mapea cada parámetro a la columna correcta de su informe.

**3. Generación del PDF**

Al pulsar "Generar", el `JobRunner` construye un `context` (diccionario Python)
con todos los valores del `ReportDefinition` y llama al motor de renderizado. El
motor lee el JSON de la plantilla, recorre cada página y cada elemento, y convierte
cada uno en HTML o en trazos ReportLab. El resultado es un PDF en `output/`.

#### Cuatro tipos principales

| Tipo | Función | Dependencia principal |
|---|---|---|
| **Texto** | Muestra texto con tokens (`{{zona}}`, `$CURRENT`) | Ninguna externa |
| **Tabla** | Rellena filas con funciones de celda por sensor | `biblioteca_tablas/funciones/`, datos SQL |
| **Gráfico** | Ejecuta un script Plotly (HTML) o Matplotlib (ReportLab) | `biblioteca_graficos/`, datos SQL |
| **Mapa** | Imagen cartográfica desde API GIS o mapa Folium | API `gis2png` o librería `folium` |

Los tipos `imagen`, `rectangulo` y `línea` son elementos decorativos sin
dependencia de datos.

---

### 11.2 Referencia técnica por tipo de elemento

---

#### Elemento: `texto`

**Campos en JSON de plantilla**

| Campo | Ubicación | Tipo Python | Descripción |
|---|---|---|---|
| `contenido.texto` | `contenido` | `str` | Texto con tokens `{{clave}}` o `$CURRENT_*` |
| `estilo.color` | `estilo` | `str` (hex) | Color del texto |
| `estilo.tamano` | `estilo` | `int` | Tamaño en pt |
| `estilo.familia_fuente` | `estilo` | `str` | Nombre de fuente |
| `estilo.negrita` | `estilo` | `str` | `"normal"` \| `"bold"` |
| `estilo.cursiva` | `estilo` | `str` | `"normal"` \| `"italic"` |
| `estilo.alineacion_h` | `estilo` | `str` | `"left"` \| `"center"` \| `"right"` |
| `metadata.nombre` | `metadata` | `str` | Nombre descriptivo del elemento |
| `contenido.editable` | `contenido` | `bool` | Si `true`, aparece en el wizard de dispatch como campo editable |

**Configuración en el editor React**

- Componente: sección de texto en `PropertiesPanel` (sin sub-componente separado).
- Controles: `Input` para texto, `ColorInput` para color, `NumericField` para
  tamaño, selects de alineación/fuente, toggles negrita/cursiva.
- Toggle `editable` → `contenido.editable = true`.

**Configuración en dispatch table (wizard)**

- `extraer_textos_editables()` detecta elementos con `contenido.editable == true`.
- `update_wizard_ui` genera un `dmc.Textarea` por cada elemento editable (bloque 4).
- El valor se guarda en `context["textos_editables"][elem_id]`.
- Antes de `_resolve_tokens`, el motor inyecta el valor del context en el texto del elemento.

**Renderizado**

| Motor | Función | Notas |
|---|---|---|
| HTML | `_elem_texto` | `_resolve_tokens()` reemplaza `{{clave}}` desde context |
| ReportLab | `_draw_text` | `_resolve_tokens()` + `_resolve_font()` para fallbacks español↔inglés |

**Flujo P/S:** No aplica — el texto no tiene `params_clasificacion`.

---

#### Elemento: `tabla`

**Campos en JSON de plantilla**

| Campo | Ubicación | Tipo Python | Descripción |
|---|---|---|---|
| `cuadricula.niveles` | `cuadricula` | `list[GridLevel]` | Array de niveles (fijo \| autorrelleno) |
| `cuadricula.columna_ancla` | `cuadricula` | `int` | Índice de columna que identifica el sensor por fila (default 0) |
| `cuadricula.fuente_ancla` | `cuadricula` | `str` | Token `$CURRENT` que el motor resuelve como nombre del sensor |
| `cuadricula.fuente_ancla_primario` | `cuadricula` | `bool` | Si `true`, el sensor aparece en el acordeón primario del wizard |
| `cuadricula.fuente_ancla_label` | `cuadricula` | `str` | Etiqueta del campo sensor en el wizard |
| `nivel.tipo` | `cuadricula.niveles[n]` | `str` | `"fijo"` \| `"autorrelleno"` |
| `nivel.columnas[n].origen` | `cuadricula` | `ColumnOrigin` | `{tipo:"fijo"}` \| `{tipo:"funcion", funcion:str, parametros:{...}}` |
| `origen.parametros[p].ref` | `cuadricula` | `str` | `"ancla"` \| `"contexto"` \| `"literal"` \| `"celda"` |
| `origen.parametros[p].primario` | `cuadricula` | `bool` | Si `true` (y `ref=="contexto"`), aparece en accordion primario del wizard |
| `origen.parametros[p].label` | `cuadricula` | `str` | Etiqueta en el wizard |

**Configuración en el editor React**

- Componentes: `TableSection` → gestiona niveles, columnas, sombreado alterno; `CellFormatModal` (Dialog) → fuente, tamaño, bordes, colores por columna; `ColumnOriginEditor` → selector fijo/función, configurador de parámetros (ancla/contexto/literal/ref_celda).
- `fuente_ancla` configurable en el nivel autorrelleno (solo opción `$CURRENT` por ahora).
- Toggle P/S en `ColumnOriginEditor` solo cuando `ref == "contexto"`.

**Configuración en dispatch table (wizard)**

- `extraer_params_clasificados()` recorre `cuadricula.niveles → columnas → origen.parametros`, extrae los `ref=="contexto"` con campo `primario`.
- También extrae `fuente_ancla_primario` como parámetro de sensor.
- `update_wizard_ui` genera un acordeón por tabla con `dmc.Select` para cada parámetro primario.
- `context` recibe `mapeo_parametros[elem_id][param_name] = col_key`.

**Renderizado**

| Motor | Función | Notas |
|---|---|---|
| HTML | `_elem_tabla → _build_html_cuadricula → _generate_rows_from_cells` | Itera sensores, llama `cell_function_registry.evaluate()` |
| ReportLab | `_draw_tabla` | Soporte tabla legacy (script) y cuadrícula (pendiente de verificar) |

**Flujo P/S:** parámetros marcados `primario=true` → wizard los expone en el accordion del informe. El motor resuelve el valor desde `context[col_key]` antes de llamar a cada función de celda.

---

#### Elemento: `grafico`

**Campos en JSON de plantilla**

| Campo | Ubicación | Tipo Python | Descripción |
|---|---|---|---|
| `configuracion.script` | `configuracion` | `str` | Nombre del archivo en `biblioteca_graficos/{motor}/` |
| `configuracion.formato` | `configuracion` | `str` | `"svg"` \| `"png"` (motor ReportLab) |
| `configuracion.parametros` | `configuracion` | `dict` | Valores de los parámetros del script (pueden incluir tokens `$CURRENT`) |
| `configuracion.params_clasificacion` | `configuracion` | `dict` | `{param_name: {tipo: "primario"|"secundario", label: str}}` |

**Configuración en el editor React**

- Componentes: `ChartSection` → selector de script, selector de formato; `ScriptParamsForm` → input por parámetro con tipo correcto (bool, número, lista, texto/fecha); `ParamPrimaryToggle` → botón P/S inline (20×20px, rojo/gris).
- Al cambiar de script, `handleConfigChange("script", value)` reconstruye `params_clasificacion` desde `scriptParamsMap`: conserva entradas existentes, añade las nuevas como `{tipo: "secundario", label: pm.nombre}`.
- Un `useEffect([config.script, scriptParamsMap])` sincroniza entradas faltantes al abrir una plantilla antigua.
- El store recibe `params_clasificacion` en `configuracion.params_clasificacion`.

**Configuración en dispatch table (wizard)**

- `extraer_params_clasificados()` lee `configuracion.params_clasificacion` directamente.
- Parámetros `tipo=="primario"` → aparecen en el acordeón del informe con `dmc.Select` (mapeo a columna de context).
- Parámetros `tipo=="secundario"` → aparecen en el modal `dt-modal-formato` como controles custom.
- Si `params_clasificacion == {}` (bug: toggles nunca tocados y `useEffect` no encontró `scriptParamsMap`), el acordeón no aparece para ese gráfico.

**Renderizado**

| Motor | Función | Notas |
|---|---|---|
| HTML | `_elem_grafico` | `script_registry.get_params()` → `_resolve_params()` → `generate(params, figsize)` → HTML |
| ReportLab | `_draw_grafico` | Igual pero `generate()` devuelve `matplotlib.Figure` → SVG/PNG embebido |

**Dependencias externas:** `utils/script_registry.py` (singleton que escanea y cachea scripts), `biblioteca_graficos/html/` o `biblioteca_graficos/reportlab/`.

**Flujo P/S:** Motor llama a `_resolve_params(elem, context)` que sustituye tokens `$CURRENT_*` usando el mapeo guardado en `context["mapeo_parametros"][elem_id]`.

---

#### Elemento: `mapa`

**Campos en JSON de plantilla**

| Campo | Ubicación | Tipo Python | Descripción |
|---|---|---|---|
| `mapa_config.fuente` | `mapa_config` | `str` | `"gis"` (API TunnelData) \| `"folium"` (mapa cartográfico) |
| `mapa_config.gis.operacion` | `mapa_config` | `str` | Operación GIS (ej. `"planoarea"`) |
| `mapa_config.gis.obra` | `mapa_config` | `str \| dict` | Nombre de la obra; puede ser `{ref:"primario", valor:..., label:...}` |
| `mapa_config.gis.sistema` | `mapa_config` | `str` | Sistema de coordenadas |
| `mapa_config.gis.capas` | `mapa_config` | `str` | Capas activas |
| `mapa_config.gis.padding` | `mapa_config` | `int` | Margen en px alrededor de la geometría |
| `mapa_config.gis.ancho_minimo` | `mapa_config` | `int \| dict` | Ancho mínimo de la imagen resultante |
| `mapa_config.folium.tile_layer` | `mapa_config` | `str` | `"cartodb"` \| `"esri"` |
| `mapa_config.folium.algoritmo_anticolision` | `mapa_config` | `bool` | Evita solapamiento de marcadores |
| `mapa_config.folium.zoom_padding` | `mapa_config` | `int` | Margen de zoom |
| `mapa_config.posicion_imagen` | `mapa_config` | `str` | `"center"` \| `"top"` \| `"bottom"` \| `"left"` \| `"right"` |
| `mapa_config.ajuste` | `mapa_config` | `str` | `"contain"` \| `"cover"` |
| `mapa_config.mapa_params_clasificacion` | `mapa_config` | `dict` | `{campo: {tipo:"primario"|"secundario", label:str}}` — mismo patrón que `params_clasificacion` de gráficos |

**Configuración en el editor React**

- Componente: sección mapa en `PropertiesPanel` (selector de fuente, campos GIS/Folium, toggle posición/ajuste).
- `MapaConfig`, `MapaConfigGis`, `MapaConfigFolium` definidos en `templateStore.ts`.
- `mapa_params_clasificacion` editable vía toggle P/S en los campos configurables.

**Configuración en dispatch table (wizard)**

- `extraer_params_clasificados()` lee `mapa_config.mapa_params_clasificacion`.
- Campos marcados como `"primario"` aparecen en el acordeón del wizard.
- Los overrides de wizard se almacenan en `context["mapa_config_overrides"][elem_id]` y `context["custom_chart_settings"][elem_id]`.
- El motor aplica estos overrides antes de hacer la llamada a la API GIS o construir el mapa Folium.

**Renderizado**

| Motor | Función | Notas |
|---|---|---|
| HTML (fuente: gis) | `_elem_mapa` → `GisClient.request()` | Llama API `gis2png`, recibe PNG, lo embebe en CSS |
| HTML (fuente: folium) | `_elem_mapa → _elem_mapa_folium` | Construye mapa `folium.Map`, renderiza a PNG via Playwright headless |
| ReportLab | `_draw_mapa` | Misma lógica GIS; embebe PNG en canvas ReportLab |

**Dependencias externas:** `utils/gis_client.py` (wraps API TunnelData), `core/data_fetcher.fetch_sensor_coords`, `folium`, `pyproj` (fuente folium).

**Flujo P/S:** Los campos de `mapa_params_clasificacion` con `tipo=="primario"` se exponen en el wizard; el motor los resuelve desde los overrides del context antes de llamar a GIS o construir el mapa Folium.

---

#### Elemento: `imagen`

**Campos en JSON de plantilla**

| Campo | Ubicación | Tipo Python | Descripción |
|---|---|---|---|
| `imagen_config.modo` | `imagen_config` | `str` | `"estatica"` (embebida) \| `"dinamica"` (asignada desde dispatch) |
| `imagen_config.nombre_imagen` | `imagen_config` | `str` | Solo modo `dinamica`: nombre del archivo en `assets/` |
| `imagen_config.marco.borde_ancho` | `imagen_config` | `int` | Grosor del marco en pt |
| `imagen_config.marco.borde_color` | `imagen_config` | `str` | Color del marco (hex) |
| `imagen_config.marco.borde_radio` | `imagen_config` | `int` | Radio de esquinas en pt |
| `imagen_config.marco.fondo` | `imagen_config` | `str` | Color de fondo o `"transparent"` |
| `imagen_config.posicion` | `imagen_config` | `str` | `"center"` \| `"top"` \| `"bottom"` \| `"left"` \| `"right"` |
| `imagen_config.ajuste` | `imagen_config` | `str` | `"contain"` \| `"cover"` |
| `imagen.datos_temp` | `imagen` | `str` | Base64 de la imagen (modo estático en editor) |
| `imagen.nombre_archivo` | `imagen` | `str` | Nombre del archivo |
| `imagen.asset_id` | `imagen` | `str` | ID en `utils/asset_manager` |

**Renderizado**

| Motor | Función | Modo | Notas |
|---|---|---|---|
| HTML | `_elem_imagen` | estático | Ruta relativa o base64 |
| HTML | `_elem_imagen_dinamica` | dinámico | `context["images"][nombre_imagen]` → base64 |
| ReportLab | `_draw_imagen` | estático | `ReportLab Image()` |
| ReportLab | `_draw_imagen_dinamica` | dinámico | Igual, fuente desde context |

---

#### Elemento: `rectangulo`

**Campos en JSON de plantilla**

| Campo | Ubicación | Tipo Python | Descripción |
|---|---|---|---|
| `estilo.color_relleno` | `estilo` | `str` | Color de relleno (hex o `"transparent"`) |
| `estilo.color_borde` | `estilo` | `str` | Color del borde |
| `estilo.grosor_borde` | `estilo` | `int` | Grosor en pt |
| `estilo.opacidad` | `estilo` | `float` | 0.0–1.0 |

**Renderizado:** `_elem_rect` (HTML: `<div>` con CSS) / `_draw_rect` (ReportLab: `rect()`). Fallbacks español↔inglés para `color_relleno`/`backgroundColor`, `color_borde`/`borderColor`.

---

#### Elemento: `linea`

**Campos en JSON de plantilla (modelo nuevo)**

| Campo | Ubicación | Tipo Python | Descripción |
|---|---|---|---|
| `configuracion.x1, y1, x2, y2` | `configuracion` | `float` | Extremos en cm |
| `configuracion.grosor` | `configuracion` | `int` | Grosor en pt |
| `configuracion.color` | `configuracion` | `str` | Color hex |
| `configuracion.estilo_linea` | `configuracion` | `str` | `"solida"` \| `"discontinua"` \| `"punteada"` |

`geometria` se usa como bounding box (derivado de x1/y1/x2/y2). Ambos motores tienen fallback al modelo legado (sin `configuracion`, usa `geometria.ancho/alto` como vector dirección).

**Renderizado:** `_elem_linea` (HTML: `<div>` con `transform: rotate()`) / `_draw_line` (ReportLab: `line()`).

---

### 11.3 Análisis de escalabilidad y particularidades

---

#### Patrón estándar compartido por todos los elementos

Todos los elementos siguen este flujo mínimo:

1. **JSON de plantilla** → campo `tipo` como discriminador.
2. **Motor** llama a la función especializada `_elem_{tipo}` / `_draw_{tipo}`.
3. La función lee `geometria` (posición y tamaño en cm) y genera el fragmento HTML o los trazos ReportLab.
4. Los campos de `estilo`, `contenido`, `metadata` se leen con `estilo.get("campo") or estilo.get("fallback_ingles", valor_default)`.

El store React centraliza el modelo: cualquier campo nuevo debe añadirse primero en `templateStore.ts` (interfaz TypeScript), luego ser consumido por `PropertiesPanel` y finalmente leído por los motores Python.

---

#### Particularidades por tipo

**`grafico`**

- `params_clasificacion` puede quedar vacío `{}` si el usuario nunca interactuó con los toggles P/S. Consecuencia: `extraer_params_clasificados()` no ve ningún parámetro y el wizard no muestra el acordeón. El `useEffect` en `ChartSection` intenta corregirlo al reabrir la plantilla, pero depende de que `scriptParamsMap` ya esté cargado en ese instante.
- Dos implementaciones de `generate()` según motor: Plotly (devuelve HTML string) para `html_engine`, Matplotlib (devuelve `Figure`) para `reportlab_engine`. El `ScriptRegistry` es compartido pero la firma del script debe soportar ambos (o existir versiones separadas en `biblioteca_graficos/html/` y `biblioteca_graficos/reportlab/`).
- `script_registry` hace scan dinámico al arrancar — añadir un script nuevo no requiere registro manual.

**`tabla`**

- La estructura `cuadricula` es propia del elemento tabla; no usa `configuracion`.
- `fuente_ancla` (`$CURRENT` por defecto) determina qué valor del context se usa como identificador de sensor por fila. Si se cambia, debe actualizarse también en `extraer_params_clasificados` y en `_elem_tabla`.
- `columna_ancla` (índice de columna) y `fuente_ancla` son ortogonales: el primero indica qué columna del nivel autorrelleno muestra el sensor; el segundo indica de qué token del context se obtiene.
- Las funciones de celda (`biblioteca_tablas/funciones/`) con `ref_celda` reciben valores ya resueltos por el motor — no acceden a `data["historico"]` directamente. Esto simplifica las funciones pero exige que el motor resuelva primero las columnas referenciadas.

**`mapa`**

- `mapa_config` con subestructura `gis` + `folium` — cada fuente tiene campos propios que el motor detecta por `mapa_config.fuente`.
- Llamada a API externa `gis2png` (TunnelData): red obligatoria, sin fallback de datos mockeados.
- Fuente `folium` requiere `playwright install chromium` además de `pip install folium pyproj` — triple dependencia externa.
- `mapa_params_clasificacion` sigue el mismo patrón que `params_clasificacion` de gráficos pero vive en `mapa_config` en lugar de en `configuracion`.
- Los overrides del wizard llegan como `context["mapa_config_overrides"][elem_id]` → el motor los aplica con una fusión superficial sobre los sub-dicts `gis`/`folium`.

**`texto`**

- El más simple: solo depende de `_resolve_tokens()`.
- El flag `contenido.editable = true` activa un flujo adicional: el wizard de dispatch muestra un textarea por cada elemento editable, y el motor sustituye `contenido.texto` por el valor del context antes de renderizar.
- No tiene `params_clasificacion` — los textos editables son siempre "primarios" implícitos.

**`imagen`**

- Dos modos con flujos de persistencia completamente distintos:
  - **Estática:** base64 en `imagen.datos_temp` durante edición; al guardar en biblioteca grupo, se registra en `utils/asset_manager` y el base64 se elimina del JSON.
  - **Dinámica:** `imagen_config.nombre_imagen` apunta a un archivo en `assets/`; el dispatch table (o el context) inyecta la imagen real en `context["images"]`.
- Ambos modos comparten los campos de `imagen_config` (marco, posición, ajuste).

---

#### Recomendaciones para añadir un nuevo tipo de elemento

**Convención de nombres:** Los campos del JSON de plantilla van en español (`color_relleno`, `grosor_borde`). Los motores Python leen español con fallback inglés. No mezclar en un mismo objeto.

**Dónde registrar el nuevo tipo (checklist):**

- [ ] **`templateStore.ts`** — añadir la interfaz del nuevo tipo (`MiElementoConfig`), añadir el `tipo` literal a `ElementType`, añadir el campo al `TemplateElement` interface.
- [ ] **`CanvasElement.tsx`** — añadir `case 'mi_tipo':` en `renderContent()` con un placeholder visual.
- [ ] **`PropertiesPanel.tsx`** — añadir sección de propiedades `MiElementoSection` component, usar `ChartSection` o `TableSection` como referencia de patrón.
- [ ] **`engines/html_engine.py`** — añadir `def _elem_mi_tipo(elem, context) -> str` y llamarla en el bloque `match tipo` del motor.
- [ ] **`engines/reportlab_engine.py`** — añadir `def _draw_mi_tipo(c, elem, context, h_cm) -> None` y llamarla en el bloque equivalente.
- [ ] **`utils/template_service.py`** — si el elemento tiene parámetros configurables en el wizard, añadir un bloque en `extraer_params_clasificados()` para leer su estructura de clasificación P/S.
- [ ] **`pages/dispatch_table.py`** — si el wizard necesita controles nuevos, actualizar `update_wizard_ui`.
- [ ] **`ToolsSidebar.tsx`** — añadir el nuevo tipo a la paleta de herramientas con su icono.
- [ ] **Recompilar:** `cd dash_component_editor_src && npm run build:js`.
- [ ] **Verificar dmc props:** `python3 -c "import inspect, dash_mantine_components as dmc; print(sorted(a.arg for a in inspect.signature(dmc.NombreComponente.__init__).parameters.values()))"` para cualquier componente DMC nuevo.

**Cómo declarar `params_clasificacion` desde el inicio:**

Declarar en la interfaz TypeScript un campo `mi_params_clasificacion?: Record<string, ParamClasificacion>` en la config del elemento. En `PropertiesPanel`, inicializarlo al crear el elemento con todos los parámetros en `{tipo: "secundario", label: nombre}`. En `extraer_params_clasificados()`, añadir un bloque `elif elem_tipo == "mi_tipo":` que lo lea. Esto garantiza que el wizard funcione sin configuración adicional desde el primer uso.

**Patrón de override del wizard:**

Para que los valores del wizard sobreescriban los del JSON sin modificar la plantilla guardada, usar `context["mi_config_overrides"][elem_id]` y aplicarlo en el motor antes de usar los campos del JSON. Ver `_elem_mapa` como referencia.

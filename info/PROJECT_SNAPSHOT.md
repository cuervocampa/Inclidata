# PROJECT_SNAPSHOT — IncliData
_Generado: 2026-07-01 — lectura read-only del repositorio. Uso: base de conocimiento para asesor externo._

---

## Resumen ejecutivo

**IncliData** es una aplicación web Python/Dash para importar, corregir, visualizar y generar informes PDF de datos de inclinómetros geotécnicos (instrumentación de taludes, túneles, etc.). El stack central es **Dash 4.x + Dash Mantine Components + ReportLab** (motor PDF legacy) y **HTML/Plotly + Playwright** (motor PDF activo). Incluye un componente React custom (`dash_component_editor`) que actúa como editor visual de plantillas A4 con drag-and-drop. El proyecto tiene ~54 archivos `.py` de código productivo, ~75 JSON de datos y plantillas, y ~1 400 CSV de lecturas de campo. Tamaño estimado del código fuente Python: ~16 000 líneas en archivos de producción.

---

## Estructura (árbol resumido)

```
IncliData/
├── app.py                          # Punto de entrada (207 l.)
├── CLAUDE.md                       # Instrucciones canónicas para el asistente
├── CONTEXT.md                      # Mapa completo de archivos y arquitectura (197 l.)
├── CONTEXT_maketator_web.md        # Arquitectura detallada + modelos de datos (1105 l.)
├── requirements.txt                # Dependencias Python
│
├── pages/                          # Páginas Dash (multi-página)
│   ├── importar.py                 # Importación JSON fabricantes (RST, Sisgeo, Soil_dux)
│   ├── correcciones.py             # Corrección datos: bias, spikes (2062 l.)
│   ├── correcciones_layout.py      # Layout de correcciones (573 l.)
│   ├── graficar.py                 # Visualización interactiva (2922 l.)
│   ├── graficar_layout.py          # Layout de graficar (618 l.)
│   ├── editor_plantilla.py         # Editor de plantillas JSON legado (4522 l.) ⚠️
│   ├── editor_plantilla_layout.py  # Layout del editor legado (2289 l.)
│   ├── editor_visual.py            # Editor visual moderno con dce.Editor (754 l.)
│   ├── importar_umbrales.py        # Importación de umbrales desde Excel
│   ├── info.py                     # Página de bienvenida
│   ├── configuraciones.py          # Stub vacío (futuro)
│   └── spikes.json                 # Config de spikes (ruta intencional)
│
├── utils/                          # Lógica de negocio y servicios
│   ├── pdf_generator.py            # Motor ReportLab (1699 l.) — parcialmente legado
│   ├── report_engine.py            # Factory de motores / API pública (513 l.)
│   ├── template_service.py         # Carga/guardado/conversión de plantillas (715 l.)
│   ├── script_registry.py          # Registro dinámico de scripts gráficos (223 l.)
│   ├── asset_manager.py            # Gestión centralizada de imágenes (279 l.)
│   ├── funciones_importar.py       # Parsers por fabricante
│   ├── funciones_graficar.py       # Construcción de figuras Plotly
│   ├── funciones_correcciones.py   # Algoritmos bias/spikes
│   ├── funciones_grupos.py         # Gestión de grupos en disco
│   ├── funciones_comunes.py        # Utilidades compartidas
│   ├── funciones_graficos.py       # Helpers gráficos
│   ├── funciones_informe_inclinometro.py
│   ├── funciones_configuracion_plantilla.py
│   ├── dev_logging.py              # Monkey-patch logging callbacks (DEBUG_CALLBACKS=1)
│   ├── rutas.py                    # Centraliza rutas del sistema de archivos
│   └── diccionarios.py             # Constantes (24 l.)
│
├── models/
│   └── template_models.py          # Modelos Pydantic v2: Plantilla, Elemento, etc. (741 l.)
│
├── biblioteca_graficos/            # Scripts que generan gráficos para PDF
│   ├── grafico_incli_0/            # Perfil inclinómetro (gráfico principal)
│   ├── grafico_incli_evo_tempo/    # Evolución temporal
│   ├── grafico_incli_evo_std_chk/  # Evolución estándar con chequeo
│   ├── grafico_incli_series_0/     # Series temporales
│   └── grafico_incli_leyenda_0/    # Leyenda flotante
│
├── biblioteca_tablas/
│   └── tabla_datos_inc/            # Tabla de datos inclinómetro para PDF
│
├── biblioteca_grupos/              # Grupos reutilizables de elementos de plantilla
│   ├── grupo_encab_hor_L9/
│   ├── grupo_encab_vert_L9/
│   ├── grupo_encab_vert_L9_minimalista/
│   └── tabla_inclis_L9_3camp/
│
├── biblioteca_plantillas/          # Plantillas JSON de informes
│   ├── _assets/registry.json       # Registro centralizado de imágenes
│   ├── INCL_AR/                    # Plantilla de producción
│   ├── Incli_L9_BCN/               # Plantilla de producción
│   ├── Rozmarin_test/              # Plantilla de prueba
│   ├── encabezado_0/, encabezado_1/ # Plantillas de encabezado
│   └── tabla_incli_L9/
│
├── data/                           # Datos de instrumentos (JSON por inclinómetro)
│   ├── Rozmarin_IN_01..23.json     # 23 sensores del proyecto Rozmarin
│   ├── Plantilla*.json             # Plantillas base de configuración
│   └── ordenar_Rozmarin_15/        # CSVs de campo
│
├── assets/                         # CSS global (custom.css, styles.css)
├── tests/                          # Tests pytest
├── scripts/migrate_assets.py       # Script one-shot de migración
│
├── dash_component_editor_src/      # Fuente TypeScript/React del editor visual
│   ├── src/lib/
│   │   ├── components/Editor.react.tsx           # Componente Dash (entry point)
│   │   └── internal/
│   │       ├── store/templateStore.ts            # Zustand store (modelo central)
│   │       └── components/editor/               # CanvasElement, PropertiesPanel, etc.
│   ├── package.json
│   └── tsconfig.json
│
└── _migracion/                     # Contratos de integración con asesor externo
    ├── CONTRATO_motor_maketador.md  # Contrato de interfaz del motor de renderizado
    ├── GLOSARIO.md                  # Vocabulario canónico
    └── PLANTILLA_contrato.md
```

**Conteo de archivos por extensión relevante** (excl. node_modules, __pycache__, binarios):

| Extensión | Cantidad | Propósito |
|-----------|----------|-----------|
| `.csv`    | 1 384    | Lecturas de campo de inclinómetros |
| `.json`   | ~75      | Datos de sensores + plantillas de informes |
| `.py`     | ~54      | Código productivo Python |
| `.md`     | 10       | Documentación |
| `.tsx/.ts`| 35+      | Código fuente React del editor |
| `.css`    | 4        | Estilos globales |

---

## Stack y dependencias

**Gestor de paquetes:** `pip` + `requirements.txt` (sin lockfile `pip.lock`; sin `pyproject.toml`).  
**Python:** 3.12+ (inferido por sintaxis y librerías).

### Python — dependencias principales (`requirements.txt`)

| Librería | Versión | Uso |
|---|---|---|
| `dash` | ≥4.0.0 | Framework web multi-página |
| `dash-mantine-components` | ≥2.5.1 | Componentes UI (DMC v2) |
| `dash-bootstrap-components` | ≥2.0.4 | Estilos Bootstrap |
| `dash-ag-grid` | ≥33.3.3 | Tablas editables |
| `plotly` | ≥6.5.2 | Gráficos interactivos (UI) |
| `matplotlib` | ≥3.10.8 | Gráficos para PDF |
| `pandas` | ≥2.3.3,<3.0.0 | Procesamiento de datos (pin <3.0) |
| `numpy` | ≥2.4.1 | Cálculo numérico |
| `scipy` | ≥1.17.0 | Algoritmos científicos |
| `reportlab` | ≥4.4.9 | Motor PDF directo (legado/activo) |
| `svglib` | ≥1.6.0 | SVG → ReportLab |
| `Pillow` | ≥12.1.0 | Procesamiento de imágenes |
| `pydantic` | ≥2.0.0 | Validación de modelos JSON (v2) |
| `openpyxl` / `XlsxWriter` | ≥3.1.5 / ≥3.2.9 | Lectura/escritura Excel |
| `requests` | ≥2.32.5 | HTTP cliente |
| `icecream` | ≥2.1.10 | Debug |
| `pywin32` | ≥311 | Solo Windows |
| `pytest` | ≥8.0.0 | Tests |

### Frontend — `dash_component_editor_src/package.json`

| Librería | Versión | Uso |
|---|---|---|
| React | 18.3.x | Framework UI |
| TypeScript | 5.8.x | Tipado |
| Zustand | 5.0.x | State management del canvas |
| @dnd-kit/core | 6.3.x | Drag & drop |
| Radix UI (11+ paquetes) | — | Primitivos UI |
| TailwindCSS | 3.4.x | Styling |
| React Hook Form + Zod | 7.x / 3.x | Formularios con validación |
| Webpack | 5.84.x | Build → `dash_component_editor.min.js` |

---

## Arquitectura y entry points

**Entry point:** `app.py` — inicializa Dash, registra callbacks de todas las páginas, define el layout de la sidebar y el contenido principal. Se arranca con `python app.py`.

**Organización:** monolito multi-página con capas:
1. **`pages/`** — callbacks Dash y layouts por dominio (importar → corregir → graficar → editar plantilla → generar PDF)
2. **`utils/`** — lógica de negocio pura (parsers, algoritmos, servicios de plantillas, motor PDF)
3. **`models/`** — modelos Pydantic v2 para validación de plantillas
4. **`biblioteca_*`** — scripts de contenido dinámico (gráficos, tablas) y plantillas JSON

**Flujo principal:**
```
Importar JSON/CSV fabricante (pages/importar)
  → Corregir datos (pages/correcciones)
    → Graficar (pages/graficar)
      → Diseñar plantilla (pages/editor_visual + pages/editor_plantilla)
        → Generar PDF (utils/report_engine → utils/pdf_generator)
```

**Motor PDF activo:** `utils/report_engine.py` orquesta el renderizado; el motor primario es ReportLab (`utils/pdf_generator.py`). Existe infraestructura parcial para un motor HTML/Playwright (referenciada en `CONTEXT_maketator_web.md`) pero en la rama `main` el motor productivo es ReportLab.

---

## Documentación existente y su estado

| Archivo | Líneas | Estado |
|---|---|---|
| `CLAUDE.md` | 50 | **Vigente** — instrucciones canónicas para el asistente (reglas, arquitectura, comandos) |
| `CONTEXT.md` | 197 | **Vigente** — mapa completo de archivos, arquitectura, flujo, deuda técnica. Actualizado 2026-04-26 |
| `CONTEXT_maketator_web.md` | 1105 | **Vigente** — arquitectura detallada de la versión "maketador_web", esquema de datos completo de elementos, flujo PDF, sección "qué archivos pedir". Actualizado 2026-04-02. Describe una versión más avanzada que la actual rama `main` (motores duales, dispatch table, SQLite) — leer con cuidado, algunos módulos descritos pueden no existir aún en `main` |
| `_migracion/CONTRATO_motor_maketador.md` | 697 | **Vigente** — contrato de integración con sistema externo (IncliData → Maketator). Define esquema JSON de sensor, tokens `$CURRENT`, parámetros de scripts, flujo de render |
| `_migracion/GLOSARIO.md` | 15 | **Vigente** — vocabulario canónico |
| `_migracion/PLANTILLA_contrato.md` | — | Plantilla para nuevos contratos |

---

## Convenciones detectadas

- **Nomenclatura Python:** `snake_case` para funciones/variables, `PascalCase` para clases (definido en CLAUDE.md).
- **Nomenclatura JSON (plantillas):** campos en español canónico (`color_borde`, `grosor`, `alineacion_h`). Los motores Python leen español con fallback inglés.
- **Unidades en JSON de disco:** centímetros (cm) para geometría. El editor React usa píxeles; ReportLab usa puntos.
- **Idioma del código:** español (identificadores, comentarios, nombres de campo en JSON).
- **Callbacks Dash:** siempre con `prevent_initial_call=True`; `allow_duplicate=True` cuando múltiples callbacks escriben el mismo Output. Sin `print()` — siempre `logger = logging.getLogger(__name__)`.
- **Token de data binding:** `$CURRENT` inyecta el valor del sensor activo; `$CURRENT_fecha_final`, etc. para otros valores del contexto.
- **Linters/formatters:** no se detectó `ruff.toml`, `.editorconfig`, `pyproject.toml` ni `setup.cfg`. Sin configuración explícita de linting en el repo.
- **Tests:** pytest en `tests/` (`conftest.py`, `test_funciones_*.py`). Sin CI detectado.

---

## Archivos críticos / candidatos a protegidos

Los siguientes archivos concentran la mayor lógica de negocio o definen contratos de datos. **No tocar sin confirmación explícita del usuario.**

| Archivo | Líneas | Por qué es crítico |
|---|---|---|
| `utils/pdf_generator.py` | 1699 | Motor de renderizado ReportLab — dibuja cada tipo de elemento en el PDF |
| `utils/report_engine.py` | 513 | API pública del motor; punto de entrada para generar PDFs |
| `utils/template_service.py` | 715 | Carga/guarda/convierte plantillas; conversión cm↔%; extracción de parámetros |
| `models/template_models.py` | 741 | Modelos Pydantic v2 — contrato tipado de la plantilla JSON |
| `pages/editor_plantilla.py` | 4522 | 67+ callbacks del editor legado; toca casi todo |
| `pages/graficar.py` | 2922 | Visualización interactiva; lógica de correcciones implícita |
| `pages/correcciones.py` | 2062 | Algoritmos de bias y detección de spikes |
| `utils/asset_manager.py` | 279 | Gestión de imágenes — si se rompe, las imágenes de plantillas quedan huérfanas |
| `utils/script_registry.py` | 223 | Descubrimiento dinámico de scripts; si falla, los gráficos dejan de renderizar |
| `biblioteca_plantillas/_assets/registry.json` | — | Registro centralizado de assets; no editar manualmente |
| `biblioteca_plantillas/INCL_AR/INCL_AR.json` | — | Plantilla de producción |
| `biblioteca_plantillas/Incli_L9_BCN/Incli_L9_BCN.json` | — | Plantilla de producción |
| `_migracion/CONTRATO_motor_maketador.md` | 697 | Contrato de integración externo — cambios requieren coordinación |

**Archivos grandes a vigilar (no editar sin entender el impacto):**
- `pages/editor_plantilla.py` (4522 l.) y `pages/editor_plantilla_layout.py` (2289 l.): candidatos a refactorización según CONTEXT.md pero aún monolíticos.
- `CONTEXT_maketator_web.md` (1105 l.): documento vivo; puede describir funcionalidades en desarrollo.

---

## Contratos de datos

### 1. Plantilla JSON de informe (`biblioteca_plantillas/{nombre}/{nombre}.json`)

```json
{
  "configuracion": { "nombre_plantilla": "str", "num_paginas": int },
  "paginas": {
    "1": {
      "elementos": {
        "{id}": {
          "tipo": "texto|imagen|linea|rectangulo|grafico|tabla",
          "geometria": { "x": float, "y": float, "ancho": float, "alto": float },
          "estilo": { "color": "#hex", "tamano": int, "familia_fuente": "str", ... },
          "contenido": { "texto": "str con tokens {{clave}}" },
          "configuracion": {
            "script": "grafico_incli_0.py",
            "parametros": { "sensor": "$CURRENT" },
            "params_clasificacion": { "sensor": { "tipo": "primario", "label": "Sensor" } }
          },
          "cuadricula": { ... },
          "imagen_config": { "modo": "estatica|dinamica", ... }
        }
      }
    }
  }
}
```

- **Unidades en disco:** centímetros para geometría; el editor convierte a % para visualización.
- **Token `$CURRENT`:** resuelto en tiempo de render desde el contexto de ejecución.
- **`params_clasificacion`:** metadato de UI; `primario` = parámetro obligatorio en el wizard.

### 2. Archivo de sensor inclinométrico (`data/Rozmarin_IN_*.json`, esquema canónico en `_migracion/CONTRATO_motor_maketador.md`)

```json
{
  "info": { "nom_sensor": "str", "coordenadas": {...}, "cota_1000": float, ... },
  "umbrales": { "deformadas": {}, "valores": [] },
  "YYYY-MM-DDTHH:MM:SS": {
    "campaign_info": { "active": bool, "reference": bool, "importador": "RST|Sisgeo|Soil_dux", ... },
    "raw": [ { "index": int, "cota_abs": float, "depth": float, "a0": float, ... } ],
    "calc": [ { "index": int, "cota_abs": float, "depth": float,
                "desp_a": float, "desp_b": float, "abs_dev_a": float, "abs_dev_b": float,
                "incr_dev_a": float, "incr_dev_b": float, ... } ]
  }
}
```

- **Los scripts solo consumen `calc[]`** — `raw[]` no es consumido por los motores de renderizado.
- Todos los desplazamientos en `calc` están en **milímetros (mm)**.
- El nombre del archivo (sin `.json`) debe coincidir exactamente con `context["sensor"]`.

### 3. Modelos Pydantic v2 (`models/template_models.py`, 741 l.)

Clases: `Plantilla`, `Elemento`, `TipoElemento` (enum), `Columna`. Validan el JSON de plantilla al cargar. Incluyen conversión cm↔% para anchos de columna de tablas.

### 4. Grupos reutilizables (`biblioteca_grupos/{nombre}/{nombre}.json`)

Fragmentos de plantilla (conjunto de elementos) exportados como ZIP (JSON + assets). Importados con `utils/funciones_grupos.py`.

---

## MANIFIESTO DE SUBIDA

Lista priorizada para la base de conocimiento del asesor externo.

### PRIORIDAD ALTA — Documentos-mapa y contratos de datos

| Ruta | Tamaño aprox. | Por qué subirlo |
|---|---|---|
| `CLAUDE.md` | 2 KB | Instrucciones canónicas del proyecto (reglas, comandos, arquitectura resumida). **Leer primero.** |
| `CONTEXT.md` | 8 KB | Mapa completo de todos los archivos, flujo, deuda técnica. Fuente de verdad sobre estructura. |
| `CONTEXT_maketator_web.md` | 45 KB | Arquitectura detallada, esquema completo de elementos JSON, flujo PDF, sección "qué archivos pedir por área". |
| `_migracion/CONTRATO_motor_maketador.md` | 28 KB | Contrato de integración: esquema JSON de sensor, tokens $CURRENT, parámetros de scripts, API de render. |
| `_migracion/GLOSARIO.md` | 1 KB | Vocabulario canónico del dominio (30 términos). |
| `requirements.txt` | 1 KB | Dependencias con versiones — define el stack completo. |

### PRIORIDAD ALTA — Archivos de código más centrales

| Ruta | Líneas | Por qué subirlo |
|---|---|---|
| `app.py` | 207 | Entry point: inicialización, registro de páginas, estructura de la app. |
| `utils/report_engine.py` | 513 | API pública del motor PDF; factory de motores; punto de entrada para generación. |
| `utils/template_service.py` | 715 | Toda la lógica de gestión de plantillas (carga, conversión, extracción de parámetros). |
| `utils/pdf_generator.py` | 1699 | Motor de renderizado ReportLab — lógica de dibujo por tipo de elemento. |
| `models/template_models.py` | 741 | Contrato tipado (Pydantic v2) de la plantilla JSON. |

### PRIORIDAD MEDIA — Lógica de negocio por dominio

| Ruta | Líneas | Por qué subirlo |
|---|---|---|
| `pages/editor_visual.py` | 754 | Editor visual moderno con React; callbacks de carga/guardado de plantillas. |
| `utils/asset_manager.py` | 279 | Gestión de imágenes — reglas críticas de no contaminar JSON con base64. |
| `utils/script_registry.py` | 223 | Registro dinámico de scripts — patrón a seguir para añadir gráficos nuevos. |
| `pages/graficar.py` | 2922 | Callbacks de visualización interactiva (grande — subir si el trabajo afecta a graficar). |
| `pages/correcciones.py` | 2062 | Algoritmos de bias/spikes (subir solo si el trabajo afecta correcciones). |
| `utils/funciones_importar.py` | — | Parsers por fabricante (RST, Sisgeo, Soil_dux) — subir si el trabajo afecta importación. |
| `biblioteca_graficos/grafico_incli_0/grafico_incli_0.py` | — | Script de gráfico más representativo; sirve de referencia para el patrón. |
| `biblioteca_tablas/tabla_datos_inc/tabla_datos_inc.py` | — | Script de tabla más representativo. |

### PRIORIDAD MEDIA — Plantillas de datos de referencia

| Ruta | Tamaño aprox. | Por qué subirlo |
|---|---|---|
| `biblioteca_plantillas/INCL_AR/INCL_AR.json` | ~20 KB | Plantilla de producción — ejemplo real del esquema JSON de plantilla. |
| `data/Rozmarin_IN_01.json` | ~1-2 MB | Ejemplo real de JSON de sensor con múltiples campañas. |
| `biblioteca_plantillas/_assets/registry.json` | ~5 KB | Registro de assets — entender la estructura de gestión de imágenes. |

### PRIORIDAD BAJA — Componente React (solo si el trabajo afecta el editor visual)

| Ruta | Por qué subirlo |
|---|---|
| `dash_component_editor_src/src/lib/internal/store/templateStore.ts` | Modelo central de datos React (Zustand store, tipos TypeScript de todos los elementos). |
| `dash_component_editor_src/src/lib/internal/components/editor/PropertiesPanel.tsx` | Panel de propiedades del editor — lógica de edición por tipo de elemento. |
| `dash_component_editor_src/src/lib/internal/components/editor/CanvasElement.tsx` | Renderizado visual de cada elemento en el canvas. |

### QUÉ NO HACE FALTA SUBIR

- **`data/ordenar_Rozmarin_15/`** — 1 384 CSVs de lecturas de campo; datos crudos, no código.
- **`dash_component_editor_src/node_modules/`** — dependencias npm (~100 MB+); nunca subir.
- **`dash_component_editor_src/dash_component_editor/dash_component_editor.min.js`** — bundle compilado (generado).
- **`data/RST/`**, **`data/Ejemplo RST/`**, **`data/Ejemplo_Soil/`** — datos de ejemplo; no son código.
- **`data/L11/`**, archivos `.xlsm/.xlsx` — datos brutos de campo.
- **`__pycache__/`**, **`*.pyc`**, **`*.log`** — artefactos de ejecución.
- **`venv/`** — entorno virtual (no versionado).
- **`.idea/`** — configuración IDE (JetBrains).
- **`biblioteca_plantillas/kk/`, `kk_1/`** (borrados en git) — plantillas sandbox.
- **`correcciones_errors.log`**, **`dash_errors.log`** — logs de ejecución.
- **`.png`, `.jpg`** en `assets/` — imágenes estáticas de UI; no son lógica.
- **`scripts/migrate_assets.py`** — script one-shot ya ejecutado; sin valor ongoing.

---

## Verificación

### Estado git (solo se creó `info/PROJECT_SNAPSHOT.md`)

```
git status --short | grep "info/"
→ ?? info/
```

Los archivos con estado `D` (deleted) y `M` (modified) en el working tree son **cambios preexistentes** registrados en el git status inicial de la sesión — no son efecto de este reconocimiento. El **único artefacto nuevo** creado en esta sesión es `info/PROJECT_SNAPSHOT.md` (directorio `info/` aparece como `??` untracked).

### Estadísticas del informe

- **Líneas de este informe:** 389
- **Archivos en MANIFIESTO por prioridad:**
  - Alta: 11 entradas (6 documentación + 5 código central)
  - Media: 11 entradas (8 código por dominio + 3 plantillas de datos)
  - Baja: 3 entradas (componentes React del editor visual)
  - No subir: 10+ categorías explícitas

_Nota: este snapshot refleja el estado de la rama `main` en la fecha de generación (2026-07-01). `CONTEXT_maketator_web.md` describe una versión más avanzada del sistema ("maketador_web") que puede diferir de lo que actualmente existe en `main`; verificar presencia de rutas antes de asumir que existen (e.g., `engines/`, `pages/dispatch_table.py`, `models/database.py`)._

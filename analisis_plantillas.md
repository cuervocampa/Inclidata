# Análisis del Sistema de Plantillas en Inclidata

Este documento analiza cómo funcionan las plantillas de informes PDF en Inclidata: su estructura en disco, los tipos de componentes que soportan, cómo se crean y modifican desde el editor visual (`pages/editor_visual.py`) y cómo se genera el PDF final.

---

## 1. Almacenamiento y estructura de archivos

### 1.1 Plantillas

Cada plantilla es una **carpeta con nombre propio** dentro de `biblioteca_plantillas/`. La convención es:

```
biblioteca_plantillas/
├── INCL_AR_prueba_kk_01/
│   ├── INCL_AR_prueba_kk_01.json   ← fichero principal de la plantilla
│   └── assets/                     ← imágenes exportadas de la plantilla
│       └── imagen 2.png
├── encabezado_0/
│   └── encabezado_0.json
└── _assets/                        ← almacén centralizado de assets (deduplicado por MD5)
    ├── b80fb2c6.png
    ├── registry.json               ← índice: asset_id → {filename, ext, md5, usages}
    └── ...
```

Una plantilla **existe y es reconocida por la aplicación** si y solo si existe la carpeta **y** dentro de ella el archivo JSON con el mismo nombre que la carpeta.

### 1.2 Grupos

Los grupos de elementos reutilizables residen en `biblioteca_grupos/`:

```
biblioteca_grupos/
├── grupo_encab_vert_L9/
│   ├── grupo_encab_vert_L9.json    ← elementos del grupo
│   └── assets/                     ← imágenes del grupo (exportación local)
└── ...
```

### 1.3 Scripts dinámicos

```
biblioteca_graficos/
└── grafico_incli_0/
    └── grafico_incli_0.py          ← función grafico_incli_0(context, parametros)

biblioteca_tablas/
└── tabla_datos/
    └── tabla_datos.py              ← función tabla_datos(context, parametros)
```

---

## 2. Estructura del JSON de la plantilla

El JSON tiene siempre la siguiente raíz:

```json
{
  "paginas": {
    "1": {
      "elementos": { ... },
      "configuracion": { "orientacion": "portrait" }
    },
    "2": { ... }
  },
  "pagina_actual": "1",
  "configuracion": {
    "nombre_plantilla": "INCL_AR_prueba_kk_01",
    "num_paginas": 1
  }
}
```

> **Nota**: Los campos `chartScripts`, `tableScripts` y `scriptMetadata` **no se guardan en disco**; se inyectan en tiempo de carga por `cargar_plantilla_para_editor()`.

- **`paginas`**: diccionario indexado por número de página (`"1"`, `"2"`, ...). Cada página tiene un sub-diccionario `elementos` y su propia `configuracion` (orientación portrait/landscape).
- **`pagina_actual`**: indica en qué página está el editor en ese momento.
- **`configuracion`**: metadatos de la plantilla (nombre, número de páginas).

---

## 3. Elementos: tipos y estructura de cada uno

Cada elemento es una entrada en el diccionario `paginas.N.elementos`, cuya **clave** es el ID del elemento (ej. `"grafico_A"`, `"titulo"`, `"Rectángulo 1"`). Todos los elementos comparten esta estructura base:

```json
{
  "id": "nombre_elemento",
  "tipo": "texto | rectangulo | linea | grafico | tabla | imagen",
  "geometria": {
    "x": 5.0,      
    "y": 1.4,      
    "ancho": 8.2,  
    "alto": 1.0    
  },
  "estilo": {
    "backgroundColor": "#FFFFFF",
    "borderColor":     "#000000",
    "borderWidth":     0.5,
    "opacity":         1,
    "color":           "#000000",
    "tamano":          14,
    "fontFamily":      "Helvetica",
    "fontWeight":      "bold | normal",
    "fontStyle":       "italic | normal",
    "textAlign":       "left | center | right"
  },
  "contenido": {
    "texto": "...",
    "src":   null
  },
  "grupo": {
    "nombre": "INCL_AR",
    "color":  "#cccccc"
  },
  "metadata": {
    "zIndex":  20,
    "visible": true,
    "grupo":   "INCL_AR"
  }
}
```

### 3.1 `texto`
Campo `contenido.texto` con el texto a mostrar. Si el texto es editable en el modal de configuración del PDF debe marcarse como `"editable": true` dentro de `contenido`.

### 3.2 `rectangulo`
Caja con fondo de color sólido. No tiene contenido de texto propiamente dicho (`contenido.texto` es `null`). Sirve principalmente como fondo decorativo o separador visual.

### 3.3 `linea`
Similar al rectángulo pero utilizado como separador horizontal o vertical fino.

### 3.4 `grafico`
Elemento que referencia dinámicamente un **script de Python** para generar la imagen del gráfico. Incluye una propiedad adicional `configuracion`:

```json
{
  "tipo": "grafico",
  "configuracion": {
    "script":   "grafico_incli_0.py",
    "formato":  "svg",
    "parametros": {
      "sensor":               "desp_a",
      "mostrar_titulo":       true,
      "etiqueta_eje_x":       "Desplazamiento (mm)",
      "nombre_sensor":        "$CURRENT",
      "fecha_inicial":        "$CURRENT_fecha_inicial",
      "fecha_final":          "$CURRENT_fecha_final",
      "color_scheme":         "$CURRENT",
      "escala_desplazamiento":"$CURRENT",
      "dpi":                  600
    }
  }
}
```

Los **tokens `$CURRENT*`** se sustituyen en tiempo de generación del PDF por los valores del contexto. Ver tabla completa en la sección 8.

### 3.5 `tabla`
Similar al gráfico, referencia un script de tabla, y añade adicionalmente una estructura `cuadricula`:

```json
{
  "tipo": "tabla",
  "configuracion": {
    "script": "tabla_datos.py",
    "parametros": { ... }
  },
  "cuadricula": {
    "niveles": [
      {
        "columnas": [
          { "titulo": "Fecha",    "campo": "fecha",    "ancho": 25.5 },
          { "titulo": "Cota",     "campo": "cota",     "ancho": 20.0 },
          { "titulo": "Desp. A",  "campo": "desp_a",   "ancho": 27.5 },
          { "titulo": "Desp. B",  "campo": "desp_b",   "ancho": 27.0 }
        ]
      }
    ]
  }
}
```

**Nota sobre anchos de columna**: El editor visual trabaja siempre con anchos en **porcentaje (0-100)**. Al guardar en disco se convierten a **cm** (función `_convertir_anchos_pct_a_cm` en `template_service.py`). Al cargar del disco se convierten de vuelta a % (dentro del método `to_editor_dict()` del modelo Pydantic `Plantilla`).

### 3.6 `imagen`
Referencia a un archivo de imagen (PNG, JPG, SVG). La imagen puede estar en tres estados:

1. **En memoria temporal**: `contenido.src` o `imagen.datos_temp` contiene un data URI (base64) durante la edición.
2. **En el almacén centralizado**: `imagen.asset_id` es un hash corto (ej. `"b80fb2c6"`) que referencia la imagen en `biblioteca_plantillas/_assets/`.
3. **En la carpeta de la plantilla**: `imagen.ruta_nueva` = `"assets/nombre.png"` es la ruta relativa para acceso desde el generador de PDF.

```json
{
  "tipo": "imagen",
  "imagen": {
    "formato":        "png",
    "ruta_original":  "",
    "ruta_nueva":     "assets/imagen 2.png",
    "nombre_archivo": "imagen 2.png",
    "estado":         "guardada",
    "asset_id":       "b80fb2c6"
  },
  "contenido": { "src": null, "texto": null }
}
```

**Prioridad de resolución de imagen** (para PDF): `asset_id` → `ruta_nueva` → `datos_temp` (crea archivo temporal).

---

## 4. Arquitectura de servicios

El editor visual delega casi toda la lógica de negocio en servicios especializados sin dependencias de Dash:

```
pages/editor_visual.py
        │
        ├─► utils/template_service.py   ← carga, guardado, conversión, fusión de plantillas
        │           │
        │           ├─► models/template_models.py   ← modelos Pydantic (Plantilla, Elemento, …)
        │           ├─► utils/asset_manager.py      ← almacén centralizado de imágenes
        │           └─► utils/script_registry.py    ← descubrimiento y metadatos de scripts
        │
        ├─► utils/funciones_grupos.py   ← CRUD de grupos en biblioteca_grupos/
        └─► utils/report_engine.py      ← resolución de tokens + generación PDF (desde estado)
                    │
                    ├─► utils/template_service.py   (cargar_plantilla)
                    └─► utils/pdf_generator.py      ← renderizado ReportLab
```

---

## 5. Flujo en `editor_visual.py`

### 5.1 Layout de la UI

El editor expone los siguientes botones en la cabecera:

| Botón | Función |
|---|---|
| **Importar Grupo** | Carga un grupo de elementos (`.json` o `.zip`) y lo fusiona en la página actual |
| **Exportar Grupo** | Abre modal de selección y descarga el grupo elegido como `.zip` |
| **Cargar Plantilla** | Abre modal de selección, lee el JSON de disco y lo envía al componente React |
| **Guardar Plantilla** | Abre modal de nombre y guarda el JSON completo en `biblioteca_plantillas/` |
| **Guardar Cambios** | Sobreescribe el fichero JSON de la plantilla actualmente cargada sin pedir nombre |
| **Generar PDF** | Abre modal de contexto; botón **"Generar maquetación PDF"** genera el PDF de maquetación |

El editor visual utiliza el componente de React `dce.Editor` (`id="visual-editor"`) para renderizar el canvas de edición.  
El estado de todo lo que está en el canvas se serializa en `visual-editor.value` como el diccionario de plantilla descrito en la sección 2.

### 5.2 Callbacks principales

#### `cargar_plantilla`
Triggered: clic en **Cargar › Confirmar**
1. Llama a `cargar_plantilla_para_editor(nombre)` de `template_service`.
2. El servicio lee el JSON → valida con `Plantilla.model_validate()` (normaliza estilos antiguos, geometría de tablas, estructura plana) → inyecta data URIs de imágenes → convierte anchos de columna cm → %.
3. Inyecta `chartScripts`, `tableScripts` y `scriptMetadata` (metadatos de parámetros de cada script).
4. Envía el dict al componente React.

#### `confirmar_guardar_plantilla` / `save_template`
Triggered: clic en **Guardar Plantilla** (modal) o **Guardar Cambios**
1. Llama a `guardar_plantilla(editor_state, nombre)` de `template_service`.
2. El servicio elimina campos de runtime (`chartScripts`, `tableScripts`, `action`, `scriptMetadata`).
3. Extrae imágenes embebidas como base64 y las guarda físicamente en `{plantilla}/assets/`.
4. Convierte anchos de columna de % a cm.
5. Registra los assets en el almacén centralizado (`register_asset`) y limpia los base64.
6. **Escritura atómica**: escribe a un `.tmp` y luego hace rename al `.json` final.

#### `importar_grupo_archivo`
Triggered: subida de un archivo mediante el componente `dcc.Upload`
1. Decodifica los bytes del archivo subido (base64 → raw).
2. Llama a `importar_grupo_desde_bytes(raw_bytes, filename)` en `template_service`.
3. Soporta `.json` (estructura de grupo sencilla) o `.zip` (JSON + assets): los assets del ZIP se registran en el almacén centralizado.
4. Fusiona los elementos del grupo en la página actual usando `fusionar_grupo_en_plantilla`, añadiendo un sufijo UUID de 4 caracteres a cada ID para evitar colisiones.

#### `exportar_grupo`
Triggered: clic en **Exportar Grupo › Descargar**
1. Localiza la carpeta del grupo en `biblioteca_grupos/{nombre_grupo}/`.
2. Empaqueta el `.json` y la carpeta `assets/` en un ZIP.
3. Lo envía al navegador como descarga.

#### `detectar_accion_crear_grupo` + `confirmar_crear_grupo`
Triggered: el componente React emite una acción de tipo `create_group`
1. Se detecta la acción en el callback atado a `Input("visual-editor", "value")`.
2. Se abre el modal de creación de grupo.
3. Al confirmar, se usa `guardar_nuevo_grupo()` de `funciones_grupos.py` para persistir el grupo en disco: sanitiza el nombre, crea la carpeta, registra imágenes en el almacén centralizado y escribe el JSON.

#### `abrir_modal_generar_pdf`
Triggered: clic en **Generar PDF**
1. Escanea el `editor_state` con `_detectar_tokens_usados()` para encontrar tokens `$CURRENT*`.
2. Muestra badges informativos con los parámetros dinámicos detectados.
3. Abre el modal con el formulario de contexto (sensor, fechas, nº de campañas).

#### `confirmar_generar_pdf`
Triggered: clic en **Generar maquetación PDF**
1. Opera con `editor_value or editor_data` (acepta el estado aunque no haya cambios).
2. Llama a `generate_report_pdf_from_state(editor_state, context, tmp_path)` de `report_engine`.
3. El engine convierte anchos % → cm, valida con Pydantic, resuelve imágenes, ejecuta scripts con valores dummy si es modo maquetación y delega el renderizado a `pdf_generator.py`.
4. Lee el PDF del archivo temporal y lo envía al navegador como descarga.

---

## 6. Conversiones internas de formato

La conversión entre el **formato de disco** y el **formato del editor React** la realiza ahora el modelo Pydantic `Plantilla` / `Elemento` en `models/template_models.py` (validación) y sus métodos `to_editor_dict()`. La tabla de equivalencias es:

| Disco / Antiguo | Editor React / Nuevo |
|---|---|
| `estilo.color_relleno` | `estilo.backgroundColor` |
| `estilo.color_borde` | `estilo.borderColor` |
| `estilo.grosor_borde` | `estilo.borderWidth` |
| `estilo.opacidad` (0-100) | `estilo.opacity` (0-1) |
| `estilo.familia_fuente` | `estilo.fontFamily` |
| `estilo.negrita` | `estilo.fontWeight` |
| `estilo.cursiva` | `estilo.fontStyle` |
| `estilo.alineacion_h` | `estilo.textAlign` |
| `geometria.ancho_maximo` (tablas) | `geometria.ancho` |
| `geometria.alto_maximo` (tablas) | `geometria.alto` |
| `cuadricula.niveles[n].columnas[m].ancho` en cm | en % al cargar, vuelve a cm al guardar |
| `grupo.nombre` | `metadata.grupo` |

---

## 7. Gestión de scripts dinámicos (`script_registry.py`)

Los scripts de gráficos y tablas se registran en un **singleton** `ScriptRegistry` al ser importados mediante el decorador `@register_script`:

```python
from utils.script_registry import register_script, ScriptMetadata, ParameterMetadata

metadata = ScriptMetadata(
    nombre="grafico_incli_0",
    tipo="grafico",
    descripcion="Gráfico de inclinómetro.",
    parametros=[
        ParameterMetadata(nombre="sensor", tipo="str", descripcion="Sensor a graficar"),
        ParameterMetadata(nombre="fecha_inicial", tipo="str", default="$CURRENT_fecha_inicial"),
    ],
)

@register_script(metadata)
def grafico_incli_0(context, parametros):
    ...
```

`discover_scripts()` recorre `biblioteca_graficos/` y `biblioteca_tablas/`, importa cada `{nombre}/{nombre}.py` y, si el script no registró metadatos, genera un fallback mínimo. Esta función se llama de forma diferida (lazy) la primera vez que se necesita la lista de scripts.

Los metadatos (`scriptMetadata`) se inyectan también en el payload que recibe el editor React para que el componente pueda mostrar los parámetros disponibles de cada script.

---

## 8. Tokens de contexto `$CURRENT*`

Los tokens se sustituyen en `report_engine._resolve_params()` durante la generación del PDF. Si un token no puede resolverse desde el contexto real, se usa `DUMMY_CONTEXT` (valores de prueba):

| Token | Campo del contexto | Valor dummy |
|---|---|---|
| `$CURRENT` | `context["info"]["nom_sensor"]` | `"SENSOR_PRUEBA"` |
| `$CURRENT_fecha_seleccionada` | `context["fecha_seleccionada"]` | `"2026-01-31"` |
| `$CURRENT_fecha_inicial` | `context["fecha_inicial"]` | `"2026-01-01"` |
| `$CURRENT_fecha_final` | `context["fecha_final"]` | `"2026-01-31"` |
| `$CURRENT_ultimas_camp` | `context["ultimas_camp"]` | `"3"` |

En **modo maquetación** (`context["is_maquetacion"] = True`):
- Los gráficos muestran un **placeholder** gris con el nombre del script (no se ejecuta el script real).
- Las tablas reciben datos dummy con 4 celdas de ejemplo.

---

## 9. Flujo de generación de PDF

```
[Editor React] editor_state (dict con anchos en %)
       │
       ▼
generate_report_pdf_from_state()          ← report_engine.py
       │
       ├─ 1. Elimina campos de runtime (chartScripts, tableScripts…)
       ├─ 2. _convertir_anchos_pct_a_cm()  → anchos en cm
       ├─ 3. Plantilla.model_validate()    → objeto Pydantic
       ├─ 4. Resuelve imágenes (asset_id → data URI, datos_temp)
       ├─ 5. resolve_template()
       │       ├─ _merge_dummy_context()  → rellena claves ausentes
       │       ├─ _resolve_params()      → sustituye tokens $CURRENT*
       │       ├─ _execute_graph()       → data URI o placeholder
       │       └─ _execute_table()       → datos_ejecutados o dummy
       ├─ 6. _plantilla_to_pdf_dict()   → dict para pdf_generator
       └─ 7. generate_pdf_from_template() → BytesIO con el PDF
```

Para generación de un PDF plenamente real (desde nombre de plantilla guardada):

```python
generate_report_pdf(nombre_plantilla, context, output_path)
# Carga desde disco → resolve_template → pdf_generator
```

---

## 10. Assets e imágenes (`asset_manager.py`)

Existe un sistema centralizado de gestión de assets en `biblioteca_plantillas/_assets/` que evita duplicar imágenes en el sistema de ficheros mediante deduplicación por hash MD5:

| Función | Descripción |
|---|---|
| `register_asset(source, nombre)` | Persiste la imagen (data URI, bytes o Path) y devuelve un `asset_id` (8 primeros chars del MD5). Acepta los tres formatos de entrada. |
| `get_asset_data_uri(asset_id)` | Devuelve el data URI para renderizar en el editor. |
| `get_asset_path(asset_id)` | Devuelve la ruta física del archivo. |
| `track_usage(asset_id, nombre_plantilla)` | Registra qué plantillas usan cada asset en `registry.json`. |
| `untrack_usage(asset_id, nombre_plantilla)` | Elimina el registro de uso. |
| `resolve_image_element(element, template_name)` | Resuelve el data URI para mostrar en HTML (prioridad: `asset_id` → `datos_temp` → `ruta_nueva`). |
| `resolve_image_path(element, template_name)` | Resuelve la ruta al archivo físico para el PDF (prioridad: `asset_id` → `ruta_nueva` → `datos_temp` crea tempfile). |

Al guardar una plantilla, las imágenes del almacén se copian también a la carpeta `assets/` de la plantilla concreta para que `pdf_generator.py` pueda acceder a ellas por ruta relativa.

---

## 11. Grupos (`funciones_grupos.py`)

Los grupos son subconjuntos reutilizables de elementos. Se almacenan en `biblioteca_grupos/{nombre}/` con el mismo esquema de elementos pero **sin** la capa de `paginas`.

### Estructura del JSON de un grupo
```json
{
  "nombre": "grupo_encab_vert_L9",
  "descripcion": "Encabezado vertical L9",
  "elementos": {
    "titulo": { ... },
    "logo":   { ... }
  }
}
```

### Operaciones disponibles
| Función | Descripción |
|---|---|
| `listar_grupos_disponibles()` | Lista los grupos válidos de `biblioteca_grupos/` como `[{label, value}]`. |
| `leer_datos_grupo(nombre)` | Lee el JSON del grupo y devuelve el dict. |
| `guardar_nuevo_grupo(nombre, desc, elementos, assets_dir)` | Crea la carpeta, registra assets en el almacén centralizado y escribe el JSON. Sanitiza el nombre (solo alfanuméricos + `_` + `-`). |
| `copiar_assets_grupo()` | **DEPRECADA** — los assets se gestionan ahora desde `_assets/`. |

Al importar un grupo, `fusionar_grupo_en_plantilla()` añade un sufijo UUID de 4 caracteres a cada ID de elemento para evitar colisiones con elementos ya presentes en la página.

---

## 12. Árbol de dependencias de `editor_visual.py`

### 12.1 Imports directos

```python
# Dash (paquetes externos)
import dash
from dash import html, dcc, Input, Output, State
import dash_mantine_components as dmc          # pip install dash-mantine-components
from dash_iconify import DashIconify           # pip install dash-iconify
import dash_component_editor as dce            # componente React local (dash_component_editor_src/)

# Stdlib
import base64, io, zipfile
from pathlib import Path

# Internos del proyecto
from utils.funciones_grupos import (
    listar_grupos_disponibles,
    leer_datos_grupo,
    guardar_nuevo_grupo,
)
from utils.asset_manager import ASSETS_DIR
from utils.template_service import (
    listar_plantillas_disponibles, listar_scripts_graficos, listar_scripts_tablas,
    cargar_plantilla_para_editor, guardar_plantilla,
    fusionar_grupo_en_plantilla, importar_grupo_desde_bytes,
    PlantillaNoEncontrada, PlantillaInvalida,
)

# Importación diferida (solo al generar PDF):
from utils.report_engine import generate_report_pdf_from_state
```

### 12.2 Árbol completo de dependencias internas

```
pages/editor_visual.py
│
├── utils/funciones_grupos.py
│   └── utils/asset_manager.py
│       └── [stdlib: hashlib, json, base64, mimetypes, tempfile, pathlib]
│
├── utils/asset_manager.py                     (importado también directamente)
│
├── utils/template_service.py
│   ├── models/template_models.py
│   │   └── [pydantic v2]
│   ├── utils/asset_manager.py
│   └── utils/script_registry.py
│       └── [pydantic v2]
│
└── utils/report_engine.py  (solo en el callback de generación PDF)
    ├── models/template_models.py
    ├── utils/script_registry.py
    ├── utils/template_service.py              (cargar_plantilla)
    └── utils/pdf_generator.py
        └── [reportlab, matplotlib]
```

### 12.3 Dependencias externas (pip)

| Paquete | Uso en editor_visual |
|---|---|
| `dash` | Framework core |
| `dash-mantine-components` | Todos los componentes UI (Modal, Button, Textarea…) |
| `dash-iconify` | Iconos MDI en los botones |
| `dash-component-editor` | Componente React `dce.Editor` (canvas de edición) |
| `pydantic` (v2) | Validación y serialización de modelos de plantilla |
| `reportlab` | Generación del PDF (solo en `pdf_generator.py`) |
| `matplotlib` | Imágenes de placeholder/error en `report_engine.py` |

### 12.4 Datos en disco que necesita el editor

| Ruta | Descripción |
|---|---|
| `biblioteca_plantillas/` | Plantillas guardadas (JSON + assets) |
| `biblioteca_plantillas/_assets/` | Almacén centralizado de imágenes |
| `biblioteca_grupos/` | Grupos de elementos reutilizables |
| `biblioteca_graficos/` | Scripts Python de gráficos (`{nombre}/{nombre}.py`) |
| `biblioteca_tablas/` | Scripts Python de tablas (`{nombre}/{nombre}.py`) |

---

## 13. Portabilidad: ¿Es `editor_visual.py` independiente de la app principal?

### Respuesta directa: **Casi sí, con tres condiciones**

`editor_visual.py` **no comparte ningún estado, callback ni store** con el resto de páginas
(`importar`, `graficar`, `correcciones`, etc.). Todo su estado vive en `dce.Editor.value` / `.data`,
que son props locales del componente. Por tanto, se puede aislar y ejecutar en un proyecto Dash
independiente **siempre que se cumplan estas tres condiciones**:

1. **La carpeta de datos existe** en el mismo path relativo (o las rutas base en los módulos se
   reconfiguren).
2. **El componente `dce.Editor`** (paquete `dash_component_editor`) está disponible e instalado.
3. **Los módulos de `utils/` y `models/` se copian junto con la página**.

Lo que **sí depende** de `app.py` en la versión actual:

| Elemento | Dónde está | Impacto |
|---|---|---|
| `dmc.MantineProvider` | En `app.py` como wrapper global | El `layout()` de `editor_visual` incluye su propio `MantineProvider` interno → **no hay impacto** |
| `dmc.NotificationProvider` | En `app.py` | Las notificaciones (`dmc.Notification`) no se mostrarán a menos que el nuevo `app.py` incluya `dmc.NotificationProvider(position="top-right")` |
| `dcc.Location` + routing | En `app.py` | Solo necesario si se quiere navegar entre páginas; para un proyecto de una sola página no se requiere |
| `suppress_callback_exceptions=True` | En `app.py` | Necesario porque los callbacks se registran dinámicamente con `register_callbacks(app)` |

### 13.1 Lista de archivos a migrar

#### Obligatorios (el editor no arranca sin ellos)

```
pages/
└── editor_visual.py

utils/
├── template_service.py
├── funciones_grupos.py
├── asset_manager.py
└── script_registry.py

models/
└── template_models.py
```

#### Necesarios para la generación de PDF (botón "Generar maquetación PDF")

```
utils/
├── report_engine.py
└── pdf_generator.py
```

#### Datos en disco (carpetas de biblioteca)

```
biblioteca_plantillas/        ← con las plantillas existentes y _assets/
biblioteca_grupos/            ← grupos reutilizables
biblioteca_graficos/          ← scripts de gráficos
biblioteca_tablas/            ← scripts de tablas
```

#### Componente React externo

```
dash_component_editor/        ← paquete pip o carpeta local con el componente
```
> Si el componente no está publicado en PyPI habrá que copiar también la carpeta
> `dash_component_editor_src/` y el proceso de build del componente.

### 13.2 `app.py` mínimo para el proyecto aislado

```python
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_mantine_components as dmc
from pages import editor_visual

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
)

app.layout = dmc.MantineProvider(
    children=[
        dmc.NotificationProvider(position="top-right", zIndex=9999),
        dcc.Location(id="url"),
        editor_visual.layout(),
    ]
)

editor_visual.register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
```

### 13.3 Qué **no** hay que llevarse

Los siguientes módulos son específicos de la app de inclinómetros y **no son necesarios** para el
editor visual:

| Módulo | Razón |
|---|---|
| `utils/funciones_comunes.py` | Utilidades de procesado de datos de inclinómetro |
| `utils/funciones_graficar.py` | Generación de gráficos de sensores |
| `utils/funciones_importar.py` | Importación de ficheros de datos |
| `utils/funciones_correcciones.py` | Correcciones de inclinómetro |
| `utils/funciones_configuracion_plantilla.py` | Solo lo usa `editor_plantilla.py` |
| `pages/importar.py`, `graficar.py`, etc. | Páginas de la app principal |
| `data/` | Datos de mediciones de sensores |

> **Nota**: los scripts en `biblioteca_graficos/` y `biblioteca_tablas/` sí pueden necesitar
> `utils/funciones_comunes.py` u otros módulos de la app para acceder a los datos reales. Si se
> quiere el editor **solo como diseñador de plantillas** (sin generación real de PDF), esos
> scripts no se ejecutan y no se necesitan.


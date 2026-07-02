# CONTRATO DE INTERFAZ — Motor de renderizado Maketator
Vocabulario canónico: GLOSARIO.md. Toda afirmación técnica no trivial incluye ruta:línea.

---

## 1. Propósito y frontera

**Expone:** el motor de renderizado de Maketator como caja negra que toma
(lámina/plantilla + contexto de ejecución) y produce un PDF de inclinometría.

**Frontera de integración:**
```
inclidata  ──→  json_inclis/{sensor}.json  ──→  Maketator render  ──→  PDF
```

**Fuera de alcance:** el editor visual (`dash_component_editor_src/`),
la dispatch table, la UI Dash, gestión de servidores SQL, mapas Folium.

**Mitad de consumo** (lo que inclidata necesita): `utils/report_engine.py`,
`engines/html_engine.py`, `biblioteca_graficos/html/`, `biblioteca_tablas/funciones/`,
`json_inclis/`. El editor es autoría pura; no es necesario para el render.

---

## 2. Objetos de datos

### 2.1 Lámina (plantilla JSON)

Archivo: `biblioteca_plantillas/html/{nombre}/{nombre}.json`

```
{
  "engine":         "html",                    ← selecciona motor
  "configuracion":  { "nombre_plantilla": str, "num_paginas": int },
  "paginas": {
    "1": {
      "elementos": {
        "{id}": {
          "tipo":      "grafico | tabla | mapa | texto | imagen | rectangulo | linea",
          "geometria": { "x": float, "y": float, "ancho": float, "alto": float },
          "configuracion": {
            "script":              "html/grafico_inclinometro_v2.py",
            "parametros": {
              "sensor":     "$CURRENT",
              "variable_x": "abs_dev_a",
              "fecha_fin":  "$CURRENT_fecha_final"
            },
            "params_clasificacion": {
              "sensor": { "tipo": "primario", "label": "sensor" }
            }
          },
          "id": "{id}"
        }
      }
    }
  },
  "secciones":  {}   ← encabezados/pies; round-trip completo, no tocar
}
```

`params_clasificacion` es metadata de UI (editor). No afecta al render directamente.
`tipo: "primario"` = obligatorio en el contexto de ejecución;
`tipo: "secundario"` = tiene default en `parametros`.

### 2.2 Contexto de ejecución

Dict Python que consume `generate_report_pdf()` (`utils/report_engine.py:79`):

```python
{
    "sensor":             str,   # nombre del sensor → resuelve $CURRENT
    "sensores":           list[str],
    "fecha_inicial":      str,   # ISO 8601 → $CURRENT_fecha_inicial
    "fecha_final":        str,   # → $CURRENT_fecha_final / $CURRENT_fecha_fin
    "fecha_seleccionada": str,   # → $CURRENT_fecha_seleccionada
    "ultimas_camp":       int,   # → $CURRENT_ultimas_camp
    "data":               dict,  # payload datos externos (no consumido hoy por scripts incli)
    # opcionales: zona, tipo, frecuencia, activo, tags, is_maquetacion...
}
```

`context["sensor"]` es el nombre de archivo JSON (sin `.json`) en `json_inclis/`.

### 2.3 Archivo de sensor — `json_inclis/{sensor}.json`

**Este es el contrato de datos principal para inclinometría.**

El nombre de archivo (sin `.json`) debe coincidir exactamente con `context["sensor"]`.

#### Esquema completo

```jsonc
{
  // ── Metadatos del tubo ─────────────────────────────────────────────
  "info": {
    "nom_sensor":      "string — nombre canónico (coincide con filename)",
    "coordenadas":     { "x": number, "y": number, "z": number },
    "cota_1000":       number,           // cota del index_0 (m)
    "adquisicion":     "manual",
    "disposicion":     "vertical",
    "sentido_calculo": "abajo-arriba"
  },

  // ── Perfiles de umbral (puede estar vacío) ─────────────────────────
  "umbrales": {
    "deformadas": {
      // una entrada por umbral; nombre debe coincidir con columna en "valores"
      "<nombre_umbral>": {
        "color":      "#EF4444",                       // hex
        "tipo_linea": "dashed|dotted|dashdot|longdash|solid",
        "flanco":     "flanco_positivo|flanco_negativo|null",
        "nivel":      number | null
      }
    },
    "valores": [
      // una fila por profundidad; columna por umbral
      { "cota_abs": number, "depth": number, "<nombre_umbral>": number }
    ]
  },

  // ── Campañas (clave = timestamp ISO) ──────────────────────────────
  "YYYY-MM-DDTHH:MM:SS": {
    "campaign_info": {
      "index_0":             number,    // índice de la lectura más superficial
      "importador":          "RST|Sisgeo|Soil (dux)|...",
      "instrument_constant": number,    // factor de conversión raw → unidades físicas
      "active":              boolean,   // false → ignorado por todos los scripts
      "quarentine":          boolean,
      "alarm":               null | string,
      "reference":           boolean    // true → campaña base (desp_a/b = 0)
    },
    "info_readout": {          // metadatos de campo (variable por importador)
      "fecha_campo": "YYYY-MM-DDTHH:MM:SS",
      // ... campos adicionales dependientes del importador
    },
    "raw": [                   // lecturas brutas del sondeo; NO consumido por los scripts
      {
        "index":    number,
        "cota_abs": number,    // m, negativo hacia abajo
        "depth":    number,    // m, positivo hacia abajo desde la superficie
        "a0":       number,    // cara A, pasada 0 (unidades: ver instrument_constant)
        "a180":     number,    // cara A, pasada 180
        "b0":       number,    // cara B, pasada 0
        "b180":     number     // cara B, pasada 180
      }
    ],
    "calc": [                  // desplazamientos calculados — ÚNICO array que leen los scripts
      {
        "index":            number,
        "cota_abs":         number,   // m, misma convención que raw
        "depth":            number,   // m, misma convención que raw
        "a0":               number,   // raw redondeado
        "a180":             number,
        "b0":               number,
        "b180":             number,
        "checksum_a":       number,   // a0 + a180 (QC; idealmente ≈ 0)
        "checksum_b":       number,   // b0 + b180
        "dev_a":            number,   // (a0-a180)/2 × instrument_constant (mm/intervalo)
        "dev_b":            number,   // ídem eje B
        "incr_checksum_a":  number,   // Δchecksum_a vs campaña anterior
        "incr_checksum_b":  number,
        "incr_dev_a":       number,   // Δdev_a vs campaña anterior (mm)
        "incr_dev_b":       number,
        "incr_dev_abs_a":   number,   // |incr_dev_a|
        "incr_dev_abs_b":   number,
        "abs_dev_a":        number,   // perfil de deformación acumulada eje A (mm)
        "abs_dev_b":        number,   // ídem eje B
        "desp_a":           number,   // desplazamiento vs campaña de referencia, eje A (mm); 0 en referencia
        "desp_b":           number    // ídem eje B
      }
    ]
  }
}
```

#### Campos requeridos por los scripts de renderizado

| Sección | Campo | Obligatorio | Consumido por |
|---|---|---|---|
| `campaign_info` | `active` | Sí | todos los scripts (filtro) |
| `campaign_info` | `reference` | Sí | convención de valor 0 en `desp_*` |
| `calc[]` | `cota_abs`, `depth` | Sí | eje Y de gráficos |
| `calc[]` | `desp_a`, `desp_b` | Sí* | `grafico_inclinometro_v2` (variable_x típica) |
| `calc[]` | `abs_dev_a`, `abs_dev_b` | Sí* | ídem |
| `calc[]` | `incr_dev_a`, `incr_dev_b` | Sí* | ídem (opcional si no se seleccionan) |
| `calc[]` | `checksum_a`, `checksum_b` | Sí* | ídem |
| `umbrales` | objeto (puede ser vacío) | Sí | `_draw_umbrales()` (`html_engine.py:~700`) |
| `raw[]` | todos | No | ningún script lo consume hoy |
| `info` | todos los campos | No | ningún script lo consume hoy |
| `info_readout` | todos los campos | No | ningún script lo consume hoy |

*Obligatorio si la plantilla utiliza ese campo como `variable_x`; como mínimo se requiere
un campo de `calc[]` por cada `variable_x` que aparezca en los elementos gráficos de la plantilla.

Las claves `"info"` y `"umbrales"` son excluidas explícitamente del loop de campañas
(`_EXCLUIDAS_JSON = {"info", "umbrales"}` en `grafico_inclinometro_v2.py:515`).

#### Ejemplo real (recorte de `json_inclis/Rozmarin_IN_01.json` — 2 campañas × 3 profundidades)

Fuente: `json_inclis/Rozmarin_IN_01.json`. Se conservan los valores exactos del disco;
se omiten las claves `raw` (no consumidas), `info_readout` y las campañas restantes.
El tubo tiene 42 lecturas (depth 0.5–21.0 m); aquí se muestran las 3 más superficiales.

```json
{
  "info": {
    "nom_sensor": "Rozmarin_IN_01",
    "coordenadas": { "x": 100, "y": 200, "z": 300 },
    "cota_1000": 0,
    "adquisicion": "manual",
    "disposicion": "vertical",
    "sentido_calculo": "abajo-arriba"
  },
  "umbrales": { "deformadas": {}, "valores": [] },

  "2024-07-18T13:17:03": {
    "campaign_info": {
      "index_0": 1000, "importador": "RST", "instrument_constant": 1,
      "active": true, "quarentine": false, "alarm": null, "reference": true
    },
    "calc": [
      {
        "index": 1000, "cota_abs": -0.5, "depth": 0.5,
        "a0": 12.3, "a180": -11.33, "b0": 4.84, "b180": -5.4,
        "checksum_a": 0.97, "checksum_b": -0.56,
        "dev_a": 11.82, "dev_b": 5.12,
        "incr_checksum_a": 0, "incr_checksum_b": 0,
        "incr_dev_a": 0, "incr_dev_b": 0,
        "incr_dev_abs_a": 0, "incr_dev_abs_b": 0,
        "abs_dev_a": 57.96, "abs_dev_b": 55.32,
        "desp_a": 0, "desp_b": 0
      },
      {
        "index": 1001, "cota_abs": -1, "depth": 1,
        "a0": 11.9, "a180": -10.85, "b0": 4.57, "b180": -4.93,
        "checksum_a": 1.05, "checksum_b": -0.36,
        "dev_a": 11.38, "dev_b": 4.75,
        "incr_checksum_a": 0, "incr_checksum_b": 0,
        "incr_dev_a": 0, "incr_dev_b": 0,
        "incr_dev_abs_a": 0, "incr_dev_abs_b": 0,
        "abs_dev_a": 46.14, "abs_dev_b": 50.2,
        "desp_a": 0, "desp_b": 0
      },
      {
        "index": 1002, "cota_abs": -1.5, "depth": 1.5,
        "a0": 10.84, "a180": -10.06, "b0": 4.76, "b180": -4.82,
        "checksum_a": 0.78, "checksum_b": -0.06,
        "dev_a": 10.45, "dev_b": 4.79,
        "incr_checksum_a": 0, "incr_checksum_b": 0,
        "incr_dev_a": 0, "incr_dev_b": 0,
        "incr_dev_abs_a": 0, "incr_dev_abs_b": 0,
        "abs_dev_a": 34.76, "abs_dev_b": 45.45,
        "desp_a": 0, "desp_b": 0
      }
    ]
  },

  "2024-07-18T13:37:38": {
    "campaign_info": {
      "index_0": 1000, "importador": "RST", "instrument_constant": 1,
      "active": true, "quarentine": false, "alarm": null, "reference": false
    },
    "calc": [
      {
        "index": 1000, "cota_abs": -0.5, "depth": 0.5,
        "a0": 11.63, "a180": -10.94, "b0": 5.32, "b180": -4.83,
        "checksum_a": 0.69, "checksum_b": 0.49,
        "dev_a": 11.29, "dev_b": 5.08,
        "incr_checksum_a": -0.28, "incr_checksum_b": 1.05,
        "incr_dev_a": -0.53, "incr_dev_b": -0.04,
        "incr_dev_abs_a": -0.53, "incr_dev_abs_b": -0.04,
        "abs_dev_a": 58.19, "abs_dev_b": 55.03,
        "desp_a": 0.23, "desp_b": -0.29
      },
      {
        "index": 1001, "cota_abs": -1, "depth": 1,
        "a0": 11.84, "a180": -10.78, "b0": 5.1, "b180": -4.87,
        "checksum_a": 1.06, "checksum_b": 0.23,
        "dev_a": 11.31, "dev_b": 4.98,
        "incr_checksum_a": 0.01, "incr_checksum_b": 0.59,
        "incr_dev_a": -0.07, "incr_dev_b": 0.23,
        "incr_dev_abs_a": -0.07, "incr_dev_abs_b": 0.23,
        "abs_dev_a": 46.9, "abs_dev_b": 49.95,
        "desp_a": 0.76, "desp_b": -0.25
      },
      {
        "index": 1002, "cota_abs": -1.5, "depth": 1.5,
        "a0": 10.93, "a180": -9.99, "b0": 4.94, "b180": -4.86,
        "checksum_a": 0.94, "checksum_b": 0.08,
        "dev_a": 10.46, "dev_b": 4.9,
        "incr_checksum_a": 0.16, "incr_checksum_b": 0.14,
        "incr_dev_a": 0.01, "incr_dev_b": 0.11,
        "incr_dev_abs_a": 0.01, "incr_dev_abs_b": 0.11,
        "abs_dev_a": 35.59, "abs_dev_b": 44.97,
        "desp_a": 0.83, "desp_b": -0.48
      }
    ]
  }
}
```

**Verificación de relaciones matemáticas** (comprobado contra el disco):

| Relación | Ejemplo | Resultado |
|---|---|---|
| `dev_a = (a0−a180)/2 × IC` | `(12.3−(−11.33))/2 × 1 = 11.82` | ✓ coincide con campo `dev_a` |
| `abs_dev_a[i] = abs_dev_a[i+1] + dev_a[i]` | `46.14 + 11.82 = 57.96` | ✓ (sentido abajo→arriba) |
| `desp_a = abs_dev_a(camp) − abs_dev_a(ref)` | `58.19 − 57.96 = 0.23` | ✓ coincide con `desp_a` campaña 2 |

Las fórmulas de §4 son correctas tal como están.

### 2.4 Salida del render

`generate_report_pdf()` escribe un PDF en `output_path` y devuelve `list` (log de ejecución).
El PDF es A4 portrait (21 × 29.7 cm) o landscape (29.7 × 21 cm) según la configuración de la plantilla.
Motor único activo: HTML/Plotly → Playwright/Chromium headless → PDF.

---

## 3. Parámetros y clasificación

### `grafico_inclinometro_v2.py` — Perfil de deformación

`biblioteca_graficos/html/grafico_inclinometro_v2.py:55–161`

| Parámetro | Tipo | Default | Clasificación | Descripción |
|---|---|---|---|---|
| `sensor` | texto | `$CURRENT` | primario | Nombre de archivo JSON (sin extensión) en `json_inclis/` |
| `variable_x` | lista | `abs_dev_a` | primario | Campo de `calc[]` en eje X: `desp_a`, `desp_b`, `abs_dev_a`, `abs_dev_b`, `incr_dev_a`, `incr_dev_b`, `checksum_a`, `checksum_b` |
| `variable_y` | lista | `cota_abs` | primario | `cota_abs` (eje normal, m) o `depth` (eje invertido, 0 arriba) |
| `fecha_inicio` | texto | `$CURRENT_fecha_inicial` | primario | Límite inferior de campañas (ISO) |
| `fecha_fin` | texto | `$CURRENT_fecha_final` | primario | Límite superior de campañas (ISO) |
| `total_camp` | número | 10 | secundario | Máximo de campañas a mostrar |
| `ultimas_camp` | número | 3 | secundario | Campañas recientes consecutivas (también desde `$CURRENT_ultimas_camp`) |
| `cadencia_dias` | número | 15 | secundario | Salto mínimo en días entre campañas históricas |
| `escala_grafico` | lista | `auto` | secundario | `auto` o `manual` |
| `valor_min_x` | número | -50 | secundario | Límite inferior X en mm (escala manual) |
| `valor_max_x` | número | 50 | secundario | Límite superior X en mm (escala manual) |
| `color_scheme` | lista | `Viridis` | secundario | `Viridis` / `Plasma` / `Azules` / `Rojos` |
| `mostrar_umbrales` | bool | `false` | secundario | Dibuja perfiles de `umbrales.deformadas` del JSON |
| `show_markers` | bool | `false` | secundario | Puntos individuales sobre las líneas |
| `show_legend` | bool | `false` | secundario | Leyenda de fechas en el propio gráfico |
| `destacar_actual` | bool | `true` | secundario | Resalta la campaña más reciente |
| `width_actual` | número | 2.8 | secundario | Grosor línea campaña actual (px) |
| `width_historico` | número | 1.0 | secundario | Grosor líneas históricas (px) |
| `opacity_historico` | número | 0.40 | secundario | Opacidad líneas históricas (0–1) |
| `dtick_x` | número | 5 | secundario | Intervalo divisiones eje X (mm); 0 = automático |
| `x_axis_title` | texto | `Desplazamiento (mm)` | secundario | Etiqueta eje X |
| `y_axis_title` | texto | `Cota (m)` | secundario | Etiqueta eje Y |
| `titulo` | texto | `""` | secundario | Título centrado; vacío = sin título |
| `color_actual` | texto | `""` | secundario | Color hex campaña actual; vacío = último de la rampa |

### `grafico_escala_inclis.py` — Leyenda de campañas

`biblioteca_graficos/html/grafico_escala_inclis.py:44–120`

| Parámetro | Tipo | Default | Clasificación | Descripción |
|---|---|---|---|---|
| `sensor` | texto | `$CURRENT` | primario | Nombre de archivo JSON (sin extensión) |
| `fecha_inicio` | texto | `$CURRENT_fecha_inicial` | primario | Filtro inicio ISO |
| `fecha_fin` | texto | `$CURRENT_fecha_final` | primario | Filtro fin ISO |
| `total_camp` | número | 10 | secundario | Máximo de campañas |
| `ultimas_camp` | número | 3 | secundario | Campañas recientes consecutivas |
| `cadencia_dias` | número | 15 | secundario | Salto días entre históricas |
| `color_scheme` | lista | `Viridis` | secundario | **Debe coincidir con el gráfico de perfiles** |
| `orientacion` | lista | `vertical` | secundario | `vertical` (columna) o `horizontal` (fila) |
| `titulo` | texto | `Leyenda` | secundario | Título visible sobre las entradas |
| `font_size` | número | 8 | secundario | Tamaño de fuente (pt) |
| `pin_actual` | bool | `true` | secundario | Destacar campaña actual en caja separada |
| `eje` | lista | `todos` | secundario | Filtro umbrales: `todos`, `a`, `b` |
| `mostrar_umbrales` | bool | `false` | secundario | Añade entradas de umbral al final |

### Funciones de celda de tabla

`biblioteca_tablas/funciones/nesima_lect_incli.py:34–77`

| Parámetro | Tipo | Descripción |
|---|---|---|
| `sensor` | texto | Stem del JSON |
| `posicion` | número | 1 = más antigua del grupo, N = más reciente |
| `max_lecturas` | número | Máximo de campañas a considerar (default 6) |
| `fecha_fin` | texto | Fecha tope ISO; fallback desde `context["fecha_final"]` |

`biblioteca_tablas/funciones/columna_incli_json.py:45–86`

| Parámetro | Tipo | Descripción |
|---|---|---|
| `sensor` | texto | Stem del JSON |
| `fecha` | texto | Clave ISO exacta de la campaña |
| `clave` | texto | Campo de `calc[]` a extraer (ej. `desp_a`, `depth`) |
| `decimales` | número | Precisión del redondeo (default 2) |

---

## 4. Convenios y unidades

### Geometría del sondeo

- **`depth`** (m): profundidad desde la superficie; positivo hacia abajo. `0` = boca del tubo.
- **`cota_abs`** (m): cota absoluta; negativa hacia abajo desde el nivel de referencia.
  Relación: `cota_abs = cota_1000 - depth × interval` (con `cota_1000` y `interval` del JSON).
- **Intervalo típico:** 0.5 m entre lecturas consecutivas.
- **`index`**: entero secuencial. `index_0` (de `campaign_info`) es el índice de la lectura más superficial (típicamente 1000). `index = index_0 + depth / interval`.

### Campañas

- Una campaña = conjunto de lecturas de una misma visita de campo; identificada por su clave ISO (`"YYYY-MM-DDTHH:MM:SS"`).
- **Campaña de referencia** (`reference: true`): base de cálculo; sus valores de `desp_a`/`desp_b` son `0`.
- **Campaña ignorada:** `active: false` o `quarentine: true` — todos los scripts la excluyen.
- Solo puede haber una campaña de referencia por sensor (primera en orden cronológico, típicamente).

### Lecturas brutas (`raw`)

- `a0`, `a180`, `b0`, `b180`: lecturas de las cuatro caras del tubo en dos pasadas.
- Las **unidades de `raw`** dependen del instrumento:
  - RST (digital): décimas de grado sexagesimal (ej. 12.3 = 1.23°)
  - Sisgeo: kSinα (ej. 249.07)
  - Soil/dux: cuentas ADC (ej. -3947)
- `instrument_constant` convierte de unidades del sensor a mm/intervalo.
- Los scripts de Maketator **NO consumen `raw`**; solo consumen `calc`.

### Desplazamientos calculados (`calc`)

Todos los campos de desplazamiento en `calc` están en **milímetros (mm)**:

| Campo | Definición |
|---|---|
| `checksum_a = a0 + a180` | Control de calidad eje A (≈ 0 si la sonda es correcta) |
| `checksum_b = b0 + b180` | Ídem eje B |
| `dev_a = (a0 − a180) / 2 × instrument_constant` | Desviación angular por intervalo, eje A (mm/intervalo) |
| `dev_b` | Ídem eje B |
| `abs_dev_a` | Suma acumulada de `dev_a` desde el fondo hacia arriba: perfil de deformación total de la campaña (mm) |
| `abs_dev_b` | Ídem eje B |
| `desp_a = abs_dev_a − abs_dev_a_referencia` | Desplazamiento acumulado respecto a campaña de referencia, eje A (mm) |
| `desp_b` | Ídem eje B |
| `incr_dev_a` | Incremento de `dev_a` respecto a la campaña anterior (mm) |
| `incr_dev_b` | Ídem eje B |
| `incr_dev_abs_a = |incr_dev_a|` | Valor absoluto del incremento eje A |
| `incr_dev_abs_b` | Ídem eje B |
| `incr_checksum_a` | Δchecksum_a respecto a campaña anterior |
| `incr_checksum_b` | Ídem eje B |

### Signos y sentido de cálculo

- `sentido_calculo: "abajo-arriba"`: la acumulación (`abs_dev_*`) empieza en el fondo del tubo
  (índice máximo, mayor profundidad) y suma hacia la boca (índice mínimo, `depth` → 0).
- Positivo: desplazamiento en la dirección nominal de los ejes A o B.
- Los ejes A y B son ortogonales entre sí. Su orientación geográfica (azimut) no está
  codificada en el JSON — es metadata externa al formato.

### Fechas

- Todas las fechas en formato ISO 8601: `YYYY-MM-DDTHH:MM:SS` (sin zona horaria en los archivos actuales).
- Los parámetros `fecha_inicio` / `fecha_fin` admiten `YYYY-MM-DD` o ISO completo.
- El filtro de campañas compara solo los primeros 10 caracteres (fecha):
  `clave[:10] <= str(fecha_fin)[:10]` (`nesima_lect_incli.py:108`).

---

## 5. Puntos de extensión

### 5.1 Resolución de tokens $CURRENT*

**Cadena completa:**

```
Plantilla JSON:
  elemento.configuracion.parametros.sensor = "$CURRENT"
          ↓
engines/html_engine.py:3125  _resolve_params(params_input, context, sensor_context)
  _CURRENT_TOKEN_MAP (engines/html_engine.py:56):
    "$CURRENT"                      → context["sensor"]
    "$CURRENT_fecha_final"          → context["fecha_final"]
    "$CURRENT_fecha_fin"            → context["fecha_final"]
    "$CURRENT_fecha_inicial"        → context["fecha_inicial"]
    "$CURRENT_fecha_seleccionada"   → context["fecha_seleccionada"]
    "$CURRENT_ultimas_camp"         → context["ultimas_camp"]
          ↓
params["sensor"] = "Rozmarin_IN_01"   (resuelto antes de llamar a generate())
          ↓
generate(params, figsize)
  → _load_mock_data("Rozmarin_IN_01")
  → json_inclis/Rozmarin_IN_01.json
```

Nota: los scripts de gráficos también hacen fallback en el nombre del sensor
(`grafico_inclinometro_v2.py:1036–1043`):
```python
sensor_name = (
    params.get("sensor") or params.get("sensores_1")
    or params.get("sensores 1") or params.get("sensores1")
    or params.get("sensores") or ""
)
```

### 5.2 Scripts que leen de disco hoy

| Script | Función lectora | Def. | Llamada | Ruta construida |
|---|---|---|---|---|
| `biblioteca_graficos/html/grafico_inclinometro_v2.py` | `_load_mock_data(sensor_name)` | :544 | :1054 | `Path.cwd() / "json_inclis" / f"{sensor_name}.json"` |
| `biblioteca_graficos/html/grafico_escala_inclis.py` | `_load_data(sensor_name)` | :469 | :679 | `Path.cwd() / "json_inclis" / f"{sensor_name}.json"` |
| `biblioteca_tablas/funciones/columna_incli_json.py` | `_load_sensor_json(sensor)` | :91 | :151 | `_JSON_INCLIS_DIR / f"{sensor}.json"` (:39) |
| `biblioteca_tablas/funciones/nesima_lect_incli.py` | `_cargar_campanas_activas(sensor, fecha_fin)` | :82 | :150 | `_JSON_INCLIS_DIR / f"{sensor}.json"` (:31) |

`_JSON_INCLIS_DIR = Path(__file__).resolve().parent.parent.parent / "json_inclis"` (raíz del repo).
`Path.cwd()` en ejecución normal (`python app.py` desde la raíz) apunta al mismo directorio.
Hay un caché en memoria en `columna_incli_json.py:42`: `_json_cache: dict[str, dict]`.

### 5.3 Alta de script nuevo en ScriptRegistry

1. Crear `biblioteca_graficos/html/mi_script.py` siguiendo el esqueleto de
   `biblioteca_graficos/CLAUDE.md §2`.
2. Declarar `metadata = ScriptMetadata(...)` y `PARAMETER_METADATA = [...]`.
3. Decorar la función principal con `@register_script(metadata)`.
4. Al arrancar, `ScriptRegistry._scan()` (`utils/script_registry.py:142`)
   lo detecta automáticamente mediante `rglob("*.py")`.
5. Para funciones de celda de tabla: mismo patrón en `biblioteca_tablas/funciones/`,
   con `CELL_FUNCTION_METADATA` en lugar de `PARAMETER_METADATA`.

### 5.4 Motor de render: solo HTML/Playwright

```python
# utils/report_engine.py:28
_ENGINES = {"html": "engines.html_engine.HTMLEngine"}
_DEFAULT_ENGINE = "html"
```

El motor ReportLab/Matplotlib fue archivado a `info/legacy/graficos_reportlab/` (junio 2026).
Todo el renderizado de inclinometría es HTML/Plotly → Playwright/Chromium → PDF.

### 5.5 API pública de consumo

```python
# utils/report_engine.py:79
def generate_report_pdf(
    nombre_plantilla: str,   # carpeta en biblioteca_plantillas/ (sin ruta)
    context: dict,           # §2.2
    output_path: str,        # ruta de salida del PDF
    server=None,             # ORM Server; no requerido para inclinometría
) -> list:                   # log de ejecución
    ...

# render desde estado en memoria (sin plantilla guardada en disco)
# utils/report_engine.py:104
def generate_report_pdf_from_state(
    editor_state: dict,      # JSON completo de la plantilla (prop value del editor)
    context: dict,
    output_path: str,
) -> list:
    ...
```

### 5.6 Separación autoría / consumo

- **Autoría:** `dash_component_editor_src/` (React/TypeScript), `pages/editor_visual.py`.
  No necesario para el render.
- **Consumo:** `utils/report_engine.py` → `engines/html_engine.py` →
  `biblioteca_graficos/html/` + `biblioteca_tablas/funciones/` + `json_inclis/`.
  Este subconjunto es lo que inclidata necesita activar.

---

## 6. Gráficos

### 6.1 Perfil de deformación inclinométrica

**Script:** `biblioteca_graficos/html/grafico_inclinometro_v2.py`
**Output:** fragmento HTML con Plotly.js (CDN), sin `<html>` ni `<body>`
**Tipo:** gráfico XY (scatter + lines)
**Eje X:** campo de `calc[]` configurable; típico `desp_a` o `abs_dev_a` (mm)
**Eje Y:** `cota_abs` (m, eje normal) o `depth` (m, eje invertido, 0 arriba)
**Series:** una traza por campaña seleccionada
**Rampa de color:** de más antigua (valor bajo) a más reciente (valor alto)
**Campaña actual:** línea más gruesa (`width_actual`), opacidad 1.0; históricas con `opacity_historico`
**Umbrales:** perfiles opcionales de `umbrales.deformadas` + `umbrales.valores`; filtrados por eje (`_a`/`_b`)
**Selección de campañas:** algoritmo IncliData (`_select_campaigns()` :579):
  las `ultimas_camp` más recientes + retrocede `cadencia_dias` días hasta `total_camp`
**Línea de cero:** `fig.add_vline(x=0)` siempre visible

### 6.2 Leyenda de campañas

**Script:** `biblioteca_graficos/html/grafico_escala_inclis.py`
**Output:** HTML/CSS puro (sin Plotly); fragmento ligero
**Tipo:** lista visual color-fecha (rectángulo de color + etiqueta de fecha)
**Requisito de coherencia:** `total_camp`, `ultimas_camp`, `cadencia_dias`, `color_scheme`
deben coincidir con el gráfico de perfiles de la misma plantilla

### 6.3 Tabla de lecturas inclinométricas

**Grupos:**
- `biblioteca_grupos/Tabla_inclis_6_lecturas/` — tabla con 6 campañas en cabecera
- `biblioteca_grupos/Tabla_inclis_3_lecturas/` — variante de 3 campañas

**Mecanismo:** la plantilla referencia el grupo en `configuracion.plantilla`.
El nivel estático usa `nesima_lect_incli` para inyectar fechas en el contexto
(`context_key: "fecha_lect_N"`); el nivel autorrelleno usa `columna_incli_json`
para extraer los valores por profundidad.

**Funciones de celda disponibles:**

| Función | Ruta | Descripción |
|---|---|---|
| `nesima_lect_incli` | `biblioteca_tablas/funciones/nesima_lect_incli.py` | Fecha ISO de la N-ésima campaña activa |
| `ultima_lect_incli` | `biblioteca_tablas/funciones/ultima_lect_incli.py` | Alias: posición = última |
| `penultima_lect_incli` | `biblioteca_tablas/funciones/penultima_lect_incli.py` | Alias: posición = penúltima |
| `antepenultima_lect_incli` | `biblioteca_tablas/funciones/antepenultima_lect_incli.py` | Alias: posición = antepenúltima |
| `columna_incli_json` | `biblioteca_tablas/funciones/columna_incli_json.py` | Array de valores por profundidad para una campaña |

---

## 7. Supuestos, límites y preguntas abiertas

### 7.1 Inventario de reutilizable (sin cambios de código)

Todo lo siguiente funciona tal cual con cualquier sensor que cumpla el esquema §2.3:

| Activo | Ruta | Descripción |
|---|---|---|
| Plantilla perfil + tabla | `biblioteca_plantillas/html/Incli_vertical_00_iter_0/` | 2 páginas: perfiles eje A y B + tabla 6 lecturas |
| Variante de diseño | `biblioteca_plantillas/html/Borrador_inclis_AR_v1/` | Diseño alternativo |
| Gráfico perfil deformación | `biblioteca_graficos/html/grafico_inclinometro_v2.py` | Operativo |
| Leyenda campañas | `biblioteca_graficos/html/grafico_escala_inclis.py` | Operativo |
| Función columna de datos | `biblioteca_tablas/funciones/columna_incli_json.py` | Operativo |
| Función fecha N-ésima | `biblioteca_tablas/funciones/nesima_lect_incli.py` | Operativo |
| Función última lectura | `biblioteca_tablas/funciones/ultima_lect_incli.py` | Operativo |
| Función penúltima lectura | `biblioteca_tablas/funciones/penultima_lect_incli.py` | Operativo |
| Función antepenúltima | `biblioteca_tablas/funciones/antepenultima_lect_incli.py` | Operativo |
| Grupo tabla 6 campañas | `biblioteca_grupos/Tabla_inclis_6_lecturas/` | Operativo |
| Grupo tabla 3 campañas | `biblioteca_grupos/Tabla_inclis_3_lecturas/` | Operativo |

### 7.2 Disyuntiva de integración (pendiente de decisión)

**Opción (a): inclidata deposita JSONs en `json_inclis/`**

Requisitos del JSON:
- Sigue exactamente el esquema §2.3.
- Nombre de archivo: `{sensor_name}.json` donde `sensor_name = context["sensor"]`.
- Campos mínimos por campaña: `campaign_info.active` + `calc[]` con todos los campos de
  desplazamiento que usen las plantillas activas.

Implicaciones operativas:
- **Cero cambios de código** en Maketator.
- Inclidata necesita acceso de escritura a `json_inclis/` en el servidor Maketator
  (transferencia de archivos, API de escritura, o volumen compartido).
- Los JSONs crecen con cada campaña. Tamaños actuales: 1–8 MB por sensor
  (ej. `IN-E09-16_RST.json` = 8.3 MB con ~100 campañas × ~64 profundidades).
- Actualización: inclidata sobreescribe el archivo completo añadiendo la nueva campaña.
- El caché en memoria de `columna_incli_json.py` no se invalida entre reinicios sin limpiar
  `_json_cache`; en la práctica, el servidor se reinicia al actualizar archivos.

**Opción (b): pasar el payload de datos en `context["data"]` y modificar los scripts**

Scripts a modificar (4 funciones de lectura en §5.2):

| Script | Función | Línea | Cambio necesario |
|---|---|---|---|
| `grafico_inclinometro_v2.py` | `_load_mock_data()` | :544 | Si `params.get("data")`, usar eso; si no, leer del disco |
| `grafico_escala_inclis.py` | `_load_data()` | :469 | Ídem |
| `columna_incli_json.py` | `_load_sensor_json()` | :91 | Ídem |
| `nesima_lect_incli.py` | `_cargar_campanas_activas()` | :82 | Ídem |

Estructura esperada de `context["data"]`: equivalente al contenido del JSON del sensor
(mismo dict de campañas, misma estructura que §2.3).

Implicaciones operativas:
- **Requiere cambios de código** en 4 scripts (modificación menor pero controlada).
- Inclidata no necesita acceso al sistema de archivos de Maketator.
- El payload viaja en cada llamada (serializado en context): para sensores grandes
  (8 MB+) puede ser costoso si hay múltiples elementos inclinométricos por plantilla.
- Permite múltiples sensores sin gestión de archivos en disco.
- Alineado con el contrato genérico `params["data"]` descrito en
  `biblioteca_graficos/CLAUDE.md §3` (mecanismo ya usado por scripts no inclinométricos).

### 7.3 Preguntas abiertas

1. **Georeferenciación de ejes A/B:** el JSON no vincula Eje A / Eje B a orientaciones
   geográficas (azimut). Si inclidata necesita representar vectores de desplazamiento en
   coordenadas reales, el esquema deberá extenderse o el parámetro se pasa externamente.

2. **Perfiles de umbral:** todos los archivos de ejemplo tienen `umbrales.deformadas = {}`.
   ¿Inclidata calcula y proporciona perfiles de umbral por profundidad? Si es así, ¿en qué
   magnitud (`abs_dev_*` o `desp_*`) están expresados los valores del umbral?

3. **Multi-sensor:** las plantillas actuales trabajan con un sensor a la vez (un `$CURRENT`).
   ¿Inclidata necesita informes con dos o más inclinómetros en una sola plantilla?

4. **Ciclo de vida del JSON:** ¿las campañas se acumulan indefinidamente por sensor
   o hay política de purga? Afecta a las opciones (a) y (b) por tamaño de payload.

5. **Identidad del sensor:** el `sensor_name` en `context["sensor"]` debe coincidir
   exactamente con el nombre de archivo. ¿Cómo se mapea el identificador interno de
   inclidata al nombre de archivo en Maketator?

6. **`raw` vs `calc` — ¿quién calcula?:** los scripts solo consumen `calc`. Si inclidata
   exporta solo datos brutos del sensor, Maketator necesitaría un paso de cálculo previo
   (no existe hoy). Confirmar que inclidata entrega `calc` ya calculado.

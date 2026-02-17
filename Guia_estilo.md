# Guía de Estilo — Inclidata (Premium / Lovable)

Referencia rápida para aplicar el estilo visual consistente en todas las páginas Dash del proyecto.

---

## 1. Paleta de Colores (CSS Custom Properties)

| Variable | Light Mode | Dark Mode | Uso |
|---|---|---|---|
| `--id-primary` | `#4A6FA5` | (igual) | Botones, acentos, bordes activos |
| `--id-primary-hover` | `#3E5F8F` | (igual) | Hover de elementos primarios |
| `--id-primary-10` | `rgba(74,111,165,0.10)` | (igual) | Hover sutil (fondos) |
| `--id-primary-40` | `rgba(74,111,165,0.40)` | (igual) | Bordes dashed (upload) |
| `--id-destructive` | `#C45B5B` | (igual) | Acciones destructivas |
| `--id-background` | `#f5f5f4` | `#1c1917` | Fondo general de la app |
| `--id-card-bg` | `#FFFFFF` | `#292524` | Fondo de tarjetas |
| `--id-border` | `#e7e5e4` | `#44403c` | Bordes de tarjetas y separadores |
| `--id-text-primary` | `#1c1917` | `#e7e5e4` | Texto principal |
| `--id-text-muted` | `#78716c` | `#a8a29e` | Texto secundario / labels |
| `--id-text-white` | `#FFFFFF` | (igual) | Texto sobre fondos oscuros |

---

## 2. Tipografía

- **Fuente:** `Inter` (Google Fonts), con fallback a `system-ui, -apple-system, Segoe UI, Roboto, Arial`
- **Variable CSS:** `--id-font`

| Uso | Componente | Props |
|---|---|---|
| Título de sección | `dmc.Title` | `order=3`, `style={"color": "var(--id-text-primary)"}` |
| Subtítulo | `dmc.Title` | `order=4`, `style={"color": "var(--id-text-primary)"}` |
| Texto normal | `dmc.Text` | `size="sm"` |
| Label enfatizado | `dmc.Text` | `fw=600`, `size="sm"`, `style={"color": "var(--id-text-primary)"}` |
| Texto secundario | `dmc.Text` | `c="dimmed"`, `size="sm"` |

---

## 3. Clases CSS Utilitarias

### `.id-card` — Tarjeta contenedora

Tarjeta con borde, sombra y esquinas redondeadas. Usar para secciones de contenido.

```python
html.Div(
    children=[...],
    className='id-card',
    style={'padding': '1rem', 'marginBottom': '1rem'}
)
```

**Propiedades aplicadas:**
- `border-radius: 12px`
- `border: 1px solid var(--id-border)`
- `background-color: var(--id-card-bg)`
- `box-shadow: 0 1px 3px rgba(0,0,0,0.08)`

---

### `.id-graph-card` — Contenedor de gráficos

Similar a `.id-card` pero con `padding` incluido y `overflow: hidden` para gráficos Plotly.

```python
html.Div(
    children=[
        dmc.Text("Título del gráfico", fw=500, size="sm", c="dimmed"),
        dcc.Graph(id='mi-grafico', style={'height': '400px'})
    ],
    className='id-graph-card',
    style={'marginBottom': '1rem'}
)
```

---

### `.id-btn` — Botón estándar

Altura 40px, tipografía Inter, esquinas redondeadas. Aplicar a `dmc.Button`.

```python
dmc.Button(
    "Texto del botón",
    id='btn-accion',
    className='id-btn',
    color='blue',
    leftSection=DashIconify(icon="lucide:play", width=14)
)
```

---

### `.id-btn-outline` — Botón con borde (variante secundaria)

Fondo transparente con borde azul. Combinar con `.id-btn`.

```python
dmc.Button(
    "Acción secundaria",
    id='btn-secundario',
    variant='outline',
    className='id-btn id-btn-outline',
    leftSection=DashIconify(icon="lucide:filter", width=14)
)
```

---

### `.id-btn-destructive` — Botón de acción destructiva

Gradiente rojo para acciones como eliminar. Combinar con `.id-btn`.

```python
dmc.Button(
    "Eliminar",
    id='btn-eliminar',
    className='id-btn id-btn-destructive',
    leftSection=DashIconify(icon="lucide:trash-2", width=14)
)
```

---

### `.id-upload-area` — Zona de carga de archivos

Borde dashed azul con efecto hover. Aplicar al contenedor interior del `dcc.Upload`.

```python
dcc.Upload(
    id='upload-archivo',
    children=html.Div(
        [
            DashIconify(icon="lucide:upload", width=20, className='id-upload-icon'),
            html.Span("Arrastra o haz clic para subir archivo", className='id-upload-text')
        ],
        style={'display': 'flex', 'alignItems': 'center',
               'justifyContent': 'center', 'height': '100%', 'gap': '0.5rem'}
    ),
    className='id-upload-area',
    style={'width': '100%'}
)
```

---

## 4. Iconos (DashIconify + Lucide)

Se usa el set de iconos **Lucide** a través de `DashIconify`.

```python
from dash_iconify import DashIconify
```

| Acción | Icono | Código |
|---|---|---|
| Subir archivo | `lucide:upload` | `DashIconify(icon="lucide:upload", width=20)` |
| Descargar | `lucide:download` | `DashIconify(icon="lucide:download", width=14)` |
| Guardar | `lucide:save` | `DashIconify(icon="lucide:save", width=14)` |
| Filtrar | `lucide:filter` | `DashIconify(icon="lucide:filter", width=14)` |
| Reproducir | `lucide:play` | `DashIconify(icon="lucide:play", width=14)` |
| Eliminar | `lucide:trash-2` | `DashIconify(icon="lucide:trash-2", width=14)` |
| Gráfico | `lucide:bar-chart-3` | `DashIconify(icon="lucide:bar-chart-3", width=14)` |
| Editar | `lucide:pencil` | `DashIconify(icon="lucide:pencil", width=14)` |
| Refrescar | `lucide:refresh-cw` | `DashIconify(icon="lucide:refresh-cw", width=14)` |
| Tabla | `lucide:table` | `DashIconify(icon="lucide:table", width=14)` |

**Tamaños recomendados:**
- En botones: `width=14`
- En zona de upload: `width=20`
- Standalone / decorativo: `width=24`

---

## 5. Separadores de Sección

Para dividir secciones temáticas, usar `dmc.Divider` con label.

```python
dmc.Divider(
    label="Nombre de la Sección",
    labelPosition="center",
    style={'marginTop': '1.5rem', 'marginBottom': '1rem'}
)
```

---

## 6. Tablas AgGrid (tema Quartz)

Se usa el tema **`ag-theme-quartz`** para todas las tablas AgGrid. Este tema utiliza CSS variables, por lo que se adapta automáticamente al modo claro/oscuro sin necesidad de cambiar la clase.

### Uso básico

```python
from dash_ag_grid import AgGrid

AgGrid(
    id='mi-tabla',
    className='ag-theme-quartz',
    rowData=[...],
    columnDefs=[...],
    defaultColDef={
        'flex': 1,
        'minWidth': 100,
        'resizable': True,
        'wrapHeaderText': True,
        'autoSizeAllColumns': True
    },
    columnSize='responsiveSizeToFit',
    style={'height': '300px', 'width': '100%'}
)
```

### Variables CSS aplicadas (en `custom.css`)

| Variable | Light | Dark | Efecto |
|---|---|---|---|
| `--ag-background-color` | `var(--id-card-bg)` | `var(--id-card-bg)` | Fondo de la tabla |
| `--ag-header-background-color` | `var(--id-background)` | `#1c1917` | Fondo del header |
| `--ag-foreground-color` | `var(--id-text-primary)` | `var(--id-text-primary)` | Texto general |
| `--ag-border-color` | `var(--id-border)` | `var(--id-border)` | Bordes |
| `--ag-odd-row-background-color` | `var(--id-primary-5)` | `rgba(255,255,255,0.03)` | Filas alternas (striped) |
| `--ag-row-hover-color` | `var(--id-primary-10)` | `rgba(255,255,255,0.06)` | Hover en filas |
| `--ag-row-height` | `38px` | `38px` | Altura de fila |
| `--ag-header-height` | `40px` | `40px` | Altura del header |
| `--ag-font-family` | `var(--id-font)` | `var(--id-font)` | Tipografía Inter |
| `--ag-font-size` | `0.875rem` | `0.875rem` | Tamaño de texto |

### Importante

- **NO** usar `ag-theme-alpine` ni `ag-theme-alpine-dark`. Siempre `ag-theme-quartz`.
- El callback de cambio de tema devuelve siempre `"ag-theme-quartz"` (la adaptación la hacen las CSS variables).
- Las esquinas redondeadas (`--ag-wrapper-border-radius: var(--id-radius-lg)`) coinciden con las tarjetas `.id-card`.

---

## 7. Espaciado y Layout

| Concepto | Valor |
|---|---|
| Margen superior de página | `1.5rem` |
| Padding de tarjeta (`.id-card`) | `1rem` |
| Separación entre tarjetas | `marginBottom: '1rem'` |
| Gap entre botones | `gap: '0.5rem'` en contenedor `display: 'flex'` |

### Estructura base de página

```python
def layout():
    return html.Div([
        html.Div(style={'height': '1.5rem'}),  # Espaciado superior

        # Sección 1: Upload / Controles
        html.Div([
            # ... contenido
        ], className='id-card', style={'padding': '1rem', 'marginBottom': '1rem'}),

        # Sección 2: Tabla de datos
        html.Div([
            dmc.Title("Datos", order=3, style={"color": "var(--id-text-primary)"}),
            dag.AgGrid(...)
        ], className='id-card', style={'padding': '1rem', 'marginBottom': '1rem'}),

        # Sección 3: Gráficos
        html.Div([
            dmc.Text("Gráfico principal", fw=500, c="dimmed", size="sm"),
            dcc.Graph(...)
        ], className='id-graph-card', style={'marginBottom': '1rem'}),
    ])
```

---

## 8. Modo Oscuro

El tema oscuro se activa automáticamente con `data-mantine-color-scheme="dark"`. Las clases utilitarias (`.id-card`, `.id-graph-card`, `.id-upload-area`, `.id-btn-outline`) y las tablas (`.ag-theme-quartz`) ya tienen overrides en `custom.css`.

**Regla:** Usar siempre variables CSS (`var(--id-text-primary)`, `var(--id-border)`, etc.) en estilos inline para que se adapten automáticamente al modo oscuro. **Nunca** usar colores fijos en estilos inline.

---

## 9. Referencia Rápida de Imports

```python
import dash_mantine_components as dmc
from dash import html, dcc, callback, Input, Output, State
from dash_iconify import DashIconify
import dash_ag_grid as dag
```

---

## 10. Checklist para Nuevas Páginas

- [ ] Contenedor principal: `html.Div([...])`
- [ ] Secciones en tarjetas: `className='id-card'` con `padding: '1rem'`
- [ ] Gráficos en: `className='id-graph-card'`
- [ ] Tablas AgGrid: `className='ag-theme-quartz'` (nunca alpine)
- [ ] Zona de upload: `className='id-upload-area'`
- [ ] Botones primarios: `className='id-btn'`
- [ ] Botones secundarios: `className='id-btn id-btn-outline'`
- [ ] Títulos: `dmc.Title(order=3, style={"color": "var(--id-text-primary)"})`
- [ ] Labels: `dmc.Text(fw=600, size="sm")`
- [ ] Iconos en botones: `leftSection=DashIconify(icon="lucide:...", width=14)`
- [ ] Separadores: `dmc.Divider(label="...", labelPosition="center")`
- [ ] Colores inline: siempre usar `var(--id-*)`, nunca hex fijo
- [ ] Import de `DashIconify` presente

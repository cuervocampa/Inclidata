# Análisis del Sistema de Generación de Informes PDF

*Última actualización: 28/01/2026*

Este documento detalla la arquitectura técnica y el flujo de ejecución del sistema de generación de informes PDF en **IncliData**, desde la interacción del usuario hasta la renderización final del documento.

---

## 1. Visión General del Proceso

El proceso se divide en cinco etapas principales:

1. **Configuración (Frontend):** El usuario selecciona datos y personaliza parámetros visuales en la página `/graficar`.
2. **Selección de Plantilla:** Se carga una plantilla JSON desde `biblioteca_plantillas/`.
3. **Sustitución Dinámica:** Los placeholders (`$CURRENT`, `$SENSOR`, `$FECHA`) se reemplazan por valores reales.
4. **Generación de Elementos:** Scripts modulares crean gráficos y tablas.
5. **Composición del PDF:** `ReportLab` ensambla todos los elementos en el documento final.

---

## 2. Flujo Detallado

### A. Punto de Entrada (`pages/graficar.py`)

La generación se inicia mediante un **callback de Dash** que responde al botón "Generar Informe PDF".

**Entrada:**
- Estado de los controles de la UI (selector de tubo, fechas, escalas).
- Datos almacenados en `dcc.Store` (`datos_procesados`).
- Plantilla seleccionada.

**Acción:**
1. Carga la plantilla JSON seleccionada desde `biblioteca_plantillas/`.
2. Sustituye los placeholders en la plantilla con los valores reales.
3. Llama a la función `generate_pdf_from_template` en `utils/pdf_generator.py`.

**Salida:** Un objeto `bytes` que contiene el PDF, listo para ser descargado.

### B. Motor de Generación (`utils/pdf_generator.py`)

Este es el núcleo del sistema.

**Función Principal:** `generate_pdf_from_template(template_data, data_source, ...)`

**Parámetros:**
- `template_data`: Diccionario con la estructura de la plantilla.
- `data_source`: Datos del inclinómetro seleccionado.
- `biblioteca_plantillas_path`: Ruta a la biblioteca de plantillas.
- `biblioteca_graficos_path`: Ruta a la biblioteca de gráficos.
- `biblioteca_tablas_path`: Ruta a la biblioteca de tablas.

**Lógica:**
1. Itera sobre las páginas definidas en el JSON de la plantilla.
2. Configura el tamaño y orientación de página (A4 Portrait/Landscape).
3. Ordena los elementos por `zIndex` (capas).
4. Despacha el dibujo de cada elemento a funciones especializadas:
   - `draw_line()` - Líneas
   - `draw_rectangle()` - Rectángulos
   - `draw_text()` - Textos
   - `draw_image()` - Imágenes
   - `draw_graph()` - Gráficos generados por scripts
   - `draw_table()` - Tablas simples
   - `draw_multilevel_table()` - Tablas multinivel

### C. Generación de Gráficos (`biblioteca_graficos/`)

Los gráficos se delegan a scripts externos modulares para máxima flexibilidad.

**Definición en JSON:**
```json
{
  "tipo": "grafico",
  "geometria": { "x": 1, "y": 3, "ancho": 18, "alto": 12 },
  "configuracion": {
    "script": "grafico_incli_0",
    "formato": "svg",
    "parametros": {
      "sensor": "$CURRENT",
      "campanas": 5
    }
  }
}
```

**Ejecución Dinámica:**
1. La función `render_matplotlib_graph` localiza el script `.py` especificado.
2. Carga el módulo dinámicamente usando `importlib`.
3. Ejecuta la función principal del script, pasando los datos filtrados y parámetros.
4. La figura Matplotlib se guarda temporalmente como SVG o PNG.
5. Se inserta en el PDF y se elimina el archivo temporal.

**Scripts Disponibles:**
| Script | Descripción |
|--------|-------------|
| `grafico_incli_0` | Gráfico principal de desplazamientos |
| `grafico_incli_evo_std_chk` | Evolución con desviación estándar |
| `grafico_incli_evo_tempo` | Evolución temporal |
| `grafico_incli_leyenda_0` | Leyenda de campañas |
| `grafico_incli_series_0` | Series temporales |

### D. Generación de Tablas (`biblioteca_tablas/`)

**Definición en JSON:**
```json
{
  "tipo": "tabla",
  "geometria": { "x": 1, "y": 20, "ancho_maximo": 18, "alto_maximo": 5 },
  "configuracion": {
    "script": "tabla_datos_inc",
    "parametros": {
      "fecha_seleccionada": "$FECHA"
    }
  },
  "estructura": {
    "num_columnas": 5,
    "anchos_columnas": [3.6, 3.6, 3.6, 3.6, 3.6]
  }
}
```

**Retorno del Script:**
```python
{
    "encabezados": ["Profundidad", "A+", "A-", "B+", "B-"],
    "filas": [
        ["-0.5", "1.23", "-0.45", "0.89", "-0.12"],
        ["-1.0", "2.34", "-0.67", "1.45", "-0.23"],
        # ...
    ]
}
```

### E. Composición con ReportLab

Una vez generados los activos gráficos temporales:

- **SVG (vectorial):** Se utiliza `svglib` para convertir a objetos nativos de ReportLab (`Drawing`), permitiendo calidad infinita al escalar.
- **PNG (raster):** Se inserta como imagen de mapa de bits estándar.
- Los archivos temporales se eliminan automáticamente.
- `pdf.save()` escribe el stream de bytes del PDF completo.

---

## 3. Dependencias Clave

| Librería | Propósito |
|----------|-----------|
| **Dash** | Interfaz de usuario y gestión de estado |
| **ReportLab** | Creación programática de PDFs |
| **Matplotlib** | Generación de gráficos científicos |
| **Svglib** | Conversión de SVG a ReportLab (calidad vectorial) |
| **Pillow** | Manipulación de imágenes raster |

---

## 4. Personalización de Plantillas

El sistema es altamente personalizable gracias a su arquitectura basada en datos (JSON).

### Estructura de una Plantilla

Las plantillas residen en `biblioteca_plantillas/` y constan de:

1. **Archivo JSON:** Define la posición, tamaño y propiedades de todos los elementos visuales.
2. **Carpeta `assets/`:** Contiene recursos estáticos (logotipos, imágenes de fondo).

### Edición por el Usuario

El usuario **NO** necesita editar el JSON manualmente. La aplicación incluye un editor visual dedicado:

- **Página:** `/editor_plantilla`
- **Funcionalidad:**
  - Permite cargar una plantilla existente.
  - Ofrece herramientas visuales para mover, redimensionar y modificar propiedades.
  - Permite añadir nuevos elementos (textos, imágenes, gráficos, tablas).
  - Guarda los cambios directamente en el archivo JSON.

### Cambiar de Plantilla

En la página de generación (`/graficar`), un menú desplegable permite al usuario elegir qué plantilla aplicar a los datos actuales.

---

## 5. Placeholders Dinámicos

El sistema soporta variables que se sustituyen automáticamente:

| Placeholder | Descripción |
|-------------|-------------|
| `$CURRENT` | Nombre del sensor/tubo actualmente seleccionado |
| `$FECHA` | Fecha de la campaña seleccionada |
| `$CAMPANAS` | Número de campañas a mostrar |
| `$HOY` | Fecha actual de generación |

---

## 6. Diagrama de Flujo

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Usuario       │────▶│   graficar.py   │────▶│ pdf_generator   │
│ (Selecciona)    │     │ (Prepara datos) │     │ (Renderiza)     │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌────────────────────────────────┼────────────────────────────────┐
                        │                                │                                │
                        ▼                                ▼                                ▼
              ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
              │ biblioteca_     │              │ biblioteca_     │              │   ReportLab     │
              │ graficos/*.py   │              │ tablas/*.py     │              │   (PDF final)   │
              │ (Matplotlib)    │              │ (Datos tabla)   │              │                 │
              └─────────────────┘              └─────────────────┘              └─────────────────┘
```

---

*Documentación técnica para IncliData v1.0 - 28/01/2026*

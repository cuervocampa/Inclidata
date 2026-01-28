# Editor de Plantillas de Informe - Documentación

*Última actualización: 28/01/2026*

---

## Descripción General

El Editor de Plantillas de Informe (`editor_plantilla.py`) es una herramienta visual para diseñar y generar plantillas PDF multipágina. Permite crear documentos con diversos elementos posicionables (texto, imágenes, gráficos, líneas, rectángulos, tablas simples y multinivel) y exportarlos tanto como archivos JSON (para reutilización) como PDF (para impresión/distribución).

**Características principales:**
- Editor visual WYSIWYG
- Soporte multipágina con orientación independiente
- Grupos reutilizables (encabezados, pies de página)
- Tablas dinámicas y multinivel
- Previsualización en tiempo real

---

## Arquitectura

### Estructura del Archivo

| Sección | Descripción |
|---------|-------------|
| Constantes y imports | Configuración de tamaños A4, factores de conversión |
| `layout()` | Interfaz de usuario con todos los componentes visuales |
| `register_callbacks(app)` | Lógica de callbacks para interactividad |

**Tamaño actual:** ~352 KB (~9000+ líneas)

### Constantes de Conversión

```python
A4_PORTRAIT_WIDTH = 595   # Puntos (21 cm)
A4_PORTRAIT_HEIGHT = 842  # Puntos (29.7 cm)
A4_LANDSCAPE_WIDTH = 842  # Puntos (29.7 cm)
A4_LANDSCAPE_HEIGHT = 595 # Puntos (21 cm)
SCALE_FACTOR = 0.8        # Visualización en pantalla
CM_TO_POINTS = 28.35      # 1 cm = 28.35 puntos
MM_TO_POINTS = 2.835      # 1 mm = 2.835 puntos
```

---

## Estructura de Datos

### Store Principal: `store-componentes`

El estado de la plantilla se almacena en un `dcc.Store` con la siguiente estructura:

```json
{
  "paginas": {
    "1": {
      "elementos": {
        "nombre_elemento": { ... }
      },
      "configuracion": {
        "orientacion": "portrait" | "landscape"
      }
    },
    "2": { ... }
  },
  "pagina_actual": "1",
  "seleccionado": null,
  "configuracion": {
    "nombre_plantilla": "Mi Plantilla",
    "version": "1.0",
    "num_paginas": 1
  }
}
```

---

## Tipos de Elementos

### 1. Línea (`tipo: "linea"`)

Elemento para dibujar líneas simples entre dos puntos.

```json
{
  "tipo": "linea",
  "geometria": {
    "x1": 0,      // Inicio X (cm)
    "y1": 0,      // Inicio Y (cm)
    "x2": 10,     // Fin X (cm)
    "y2": 10      // Fin Y (cm)
  },
  "estilo": {
    "grosor": 1,         // Grosor de línea (puntos)
    "color": "#000000"   // Color hexadecimal
  },
  "grupo": {
    "nombre": "Sin grupo",
    "color": "#cccccc"
  },
  "metadata": {
    "zIndex": 0,         // Orden de apilamiento
    "visible": true,     // Visibilidad
    "bloqueado": false   // Bloqueo de edición
  }
}
```

**Callbacks relacionados:**
- `open_line_drawer`: Abre el drawer de configuración
- `crear_actualizar_linea`: Crea o actualiza una línea
- `borrar_linea`: Elimina una línea
- `fill_line_form`: Rellena el formulario al seleccionar
- `update_line_selector`: Actualiza el selector de líneas

---

### 2. Rectángulo (`tipo: "rectangulo"`)

Elemento para dibujar rectángulos con relleno y borde.

```json
{
  "tipo": "rectangulo",
  "geometria": {
    "x": 0,        // Posición X (cm)
    "y": 0,        // Posición Y (cm)
    "ancho": 5,    // Ancho (cm)
    "alto": 3      // Alto (cm)
  },
  "estilo": {
    "grosor_borde": 1,           // Grosor borde (puntos)
    "color_borde": "#000000",    // Color borde
    "color_relleno": "#ffffff",  // Color relleno
    "opacidad": 100              // Opacidad (0-100)
  },
  "grupo": {
    "nombre": "Sin grupo",
    "color": "#cccccc"
  },
  "metadata": {
    "zIndex": 0,
    "visible": true,
    "bloqueado": false
  }
}
```

**Callbacks relacionados:**
- `open_rectangle_drawer`: Abre el drawer
- `crear_actualizar_rectangulo`: Crea/actualiza
- `borrar_rectangulo`: Elimina
- `fill_rectangle_form`: Rellena formulario
- `update_rectangle_selector`: Actualiza selector

---

### 3. Texto (`tipo: "texto"`)

Elemento para insertar texto formateado.

```json
{
  "tipo": "texto",
  "geometria": {
    "x": 0,        // Posición X (cm)
    "y": 0,        // Posición Y (cm)
    "ancho": 5,    // Ancho del cuadro (cm)
    "alto": 2      // Alto del cuadro (cm)
  },
  "estilo": {
    "familia_fuente": "Helvetica",  // Fuente
    "tamano": 12,                    // Tamaño (puntos)
    "negrita": "normal" | "bold",   // Negrita
    "cursiva": "normal" | "italic", // Cursiva
    "color": "#000000",              // Color texto
    "alineacion_h": "left" | "center" | "right",
    "alineacion_v": "top" | "middle" | "bottom",
    "rotacion": 0                    // Rotación en grados
  },
  "contenido": {
    "texto": "Contenido del texto",
    "ajuste_automatico": true,       // Ajustar al cuadro
    "editable": false                // Editable en PDF (futuro)
  },
  "grupo": {
    "nombre": "Sin grupo",
    "color": "#cccccc"
  },
  "metadata": {
    "zIndex": 0,
    "visible": true,
    "bloqueado": false
  }
}
```

**Callbacks relacionados:**
- `open_text_drawer`: Abre el drawer
- `crear_actualizar_texto`: Crea/actualiza
- `borrar_texto`: Elimina
- `fill_text_form`: Rellena formulario
- `update_text_selector`: Actualiza selector

---

### 4. Imagen (`tipo: "imagen"`)

Elemento para insertar imágenes (PNG, JPG, etc.)

```json
{
  "tipo": "imagen",
  "geometria": {
    "x": 0,         // Posición X (cm)
    "y": 0,         // Posición Y (cm)
    "ancho": 5,     // Ancho (cm)
    "alto": 5       // Alto (cm)
  },
  "estilo": {
    "opacidad": 100,             // Opacidad (0-100)
    "mantener_proporcion": true, // Mantener aspect ratio
    "reduccion": 0               // Margen interno (puntos)
  },
  "imagen": {
    "formato": "png",                    // Formato archivo
    "datos_temp": "data:image/png;...",  // Base64 temporal
    "ruta_original": "",                 // Ruta original
    "ruta_nueva": "assets/imagen.png",   // Ruta guardada
    "nombre_archivo": "imagen.png",      // Nombre archivo
    "estado": "nueva" | "faltante"       // Estado imagen
  },
  "grupo": {
    "nombre": "Sin grupo",
    "color": "#cccccc"
  },
  "metadata": {
    "zIndex": 0,
    "visible": true,
    "bloqueado": false
  }
}
```

**Callbacks relacionados:**
- `open_image_drawer`: Abre el drawer
- `process_image_upload`: Procesa carga de imagen
- `process_image_url`: Procesa URL de imagen
- `crear_actualizar_imagen`: Crea/actualiza
- `borrar_imagen`: Elimina
- `fill_image_form`: Rellena formulario
- `update_image_selector`: Actualiza selector

---

### 5. Gráfico (`tipo: "grafico"`)

Elemento para insertar gráficos dinámicos generados por scripts.

```json
{
  "tipo": "grafico",
  "geometria": {
    "x": 0,         // Posición X (cm)
    "y": 0,         // Posición Y (cm)
    "ancho": 10,    // Ancho (cm)
    "alto": 8       // Alto (cm)
  },
  "configuracion": {
    "script": "grafico_desplazamiento",  // Nombre del script
    "formato": "png",                     // Formato de salida
    "parametros": {                       // Parámetros del script
      "variable": "valor"
    }
  },
  "estilo": {
    "opacidad": 100,   // Opacidad (0-100)
    "reduccion": 0     // Margen interno
  },
  "grupo": {
    "nombre": "Sin grupo",
    "color": "#cccccc"
  },
  "metadata": {
    "zIndex": 0,
    "visible": true,
    "bloqueado": false
  }
}
```

**Callbacks relacionados:**
- `open_graph_drawer`: Abre el drawer
- `crear_actualizar_grafico`: Crea/actualiza
- `borrar_grafico`: Elimina
- `fill_graph_form`: Rellena formulario
- `update_graph_selector`: Actualiza selector

---

### 6. Tabla (`tipo: "tabla"`)

Elemento para insertar tablas dinámicas generadas por scripts Python.

```json
{
  "tipo": "tabla",
  "geometria": {
    "x": 1.0,           // Posición X (cm)
    "y": 2.0,           // Posición Y (cm)
    "ancho_maximo": 18.0, // Ancho máximo disponible (cm)
    "alto_maximo": 6.0    // Alto máximo disponible (cm)
  },
  "configuracion": {
    "script": "tabla_resumen_campana",  // Nombre del script Python
    "parametros": {}                     // Parámetros para el script
  },
  "estructura": {
    "num_columnas": 5,                   // Número de columnas
    "anchos_columnas": [3.6, 3.6, 3.6, 3.6, 3.6],  // Anchos individuales
    "modo_anchos": "iguales",            // "iguales" | "personalizado"
    "alto_fila": 0.5,                    // Alto de fila de datos (cm)
    "mostrar_encabezados": true,         // Mostrar fila de encabezados
    "alto_encabezado": 0.7               // Alto de fila de encabezado (cm)
  },
  "estilo": {
    "bordes": {
      "tipo": "todos",         // "ninguno" | "todos" | "horizontal" | "exterior"
      "grosor": 1,             // Grosor en píxeles
      "color": "#333333"       // Color del borde
    },
    "sombreado": {
      "estilo": "alternado",   // "ninguno" | "alternado" | "encabezado"
      "color_par": "#f8f9fa",  // Color filas pares
      "color_impar": "#ffffff", // Color filas impares
      "color_encabezado": "#e9ecef"  // Color fila encabezado
    },
    "fuente": "Helvetica",
    "tamano_fuente": 8,
    "color_texto": "#333333"
  },
  "grupo": {
    "nombre": "Sin grupo",
    "color": "#cccccc"
  },
  "metadata": {
    "zIndex": 30,
    "visible": true,
    "bloqueado": false
  }
}
```

**Callbacks relacionados:**
- `open_table_drawer`: Abre el drawer con nombre sugerido
- `update_table_selector`: Actualiza la lista de tablas
- `fill_table_form`: Rellena el formulario al seleccionar
- `crear_actualizar_tabla`: Crea o actualiza una tabla
- `borrar_tabla`: Elimina una tabla
- `update_total_width_display`: Actualiza el display de ancho total
- `distribute_columns_equally`: Distribuye columnas equitativamente
- `generate_column_width_inputs`: Genera inputs dinámicos de ancho
- `update_width_progress`: Valida suma de anchos en tiempo real
- `generate_table_preview`: Genera vista previa dinámica

**Script de datos para tablas:**

Los scripts de tabla deben estar en `biblioteca_graficos/` y devolver un diccionario con el siguiente formato:

```python
def mi_script_tabla(data_source, params):
    """
    Genera los datos para una tabla.
    
    Args:
        data_source: Datos de origen (mismo que para gráficos)
        params: Parámetros configurados en el drawer
    
    Returns:
        dict con 'encabezados' (lista) y 'filas' (lista de listas)
    """
    # Procesar datos...
    return {
        "encabezados": ["Columna 1", "Columna 2", "Columna 3"],
        "filas": [
            ["Valor 1-1", "Valor 1-2", "Valor 1-3"],
            ["Valor 2-1", "Valor 2-2", "Valor 2-3"],
            # ... más filas
        ]
    }
```

---

## Flujo de Trabajo

### 1. Crear Nueva Plantilla

1. **Configurar nombre**: Ingresar nombre en el campo "Nombre de la plantilla"
2. **Seleccionar orientación**: Portrait (vertical) o Landscape (horizontal)
3. **Añadir elementos**: Usar los botones del panel de herramientas
4. **Posicionar elementos**: Configurar coordenadas en los drawers

### 2. Añadir Elementos

1. Hacer clic en el botón del tipo de elemento deseado
2. Se abre un drawer lateral con el formulario de configuración
3. Rellenar los campos:
   - **Geometría**: Posición X, Y, dimensiones
   - **Estilo**: Colores, fuentes, opacidad
   - **Nombre**: Identificador único del elemento
   - **zIndex**: Orden de apilamiento (mayor = encima)
4. Hacer clic en "Crear/Actualizar"

### 3. Editar Elementos

1. Seleccionar el elemento en el dropdown del drawer correspondiente
2. Los campos se rellenan automáticamente con los valores actuales
3. Modificar los valores deseados
4. Hacer clic en "Crear/Actualizar" para guardar cambios

### 4. Gestión de Páginas

- **Añadir página**: Botón "+" crea nueva página
- **Navegar**: Flechas "←" y "→" o selector de página
- **Cada página tiene su propia orientación**:puede ser diferente

### 5. Guardar Plantilla

#### Como JSON (reutilizable)
1. Hacer clic en "Guardar JSON"
2. Ingresar nombre de archivo en el modal
3. Se guarda en `plantillas/{nombre}/plantilla.json`
4. Las imágenes se guardan en `plantillas/{nombre}/assets/`

#### Como PDF (para distribución)
1. Hacer clic en "Generar PDF"
2. Se genera y descarga el PDF con todos los elementos

### 6. Cargar Plantilla

1. Hacer clic en "Cargar JSON"
2. Seleccionar archivo `.json` de plantilla
3. Se carga toda la estructura y elementos

---

## Generación de PDF

### Proceso (`generate_pdf`)

1. **Crear buffer PDF** con ReportLab
2. **Iterar sobre páginas**:
   - Configurar orientación específica de cada página
   - Ordenar elementos por zIndex
3. **Dibujar cada elemento**:
   - **Líneas**: `pdf.line(x1, y1, x2, y2)`
   - **Rectángulos**: `pdf.rect(x, y, ancho, alto)`
   - **Texto**: `pdf.drawString()` con estilos
   - **Imágenes**: `pdf.drawImage()` desde archivo o base64
   - **Gráficos**: Ejecutar script y dibujar resultado
4. **Añadir páginas**: `pdf.showPage()` entre páginas
5. **Guardar y descargar**

### Conversión de Coordenadas

```python
# Convertir cm a puntos
x_puntos = x_cm * CM_TO_POINTS  # 1 cm = 28.35 puntos

# Ajustar Y (ReportLab: origen en esquina inferior izquierda)
y_pdf = page_height - y_pantalla - alto_elemento
```

---

## Dependencias

| Librería | Uso |
|----------|-----|
| `dash` | Framework principal |
| `dash_mantine_components` | Componentes UI |
| `dash_iconify` | Iconos |
| `reportlab` | Generación de PDF |
| `pathlib` | Manejo de rutas |

---

## Archivos Relacionados

| Archivo | Descripción |
|---------|-------------|
| `utils/funciones_configuracion_plantilla.py` | Funciones auxiliares de orientación |
| `utils/funciones_grupos.py` | Gestión de grupos reutilizables |
| `utils/pdf_generator.py` | Motor de renderizado PDF |
| `biblioteca_plantillas/` | Directorio de plantillas guardadas |
| `biblioteca_plantillas/{nombre}/{nombre}.json` | Archivo JSON de plantilla |
| `biblioteca_plantillas/{nombre}/assets/` | Imágenes de la plantilla |
| `biblioteca_graficos/` | Scripts de gráficos para PDF |
| `biblioteca_tablas/` | Scripts de tablas dinámicas |
| `biblioteca_grupos/` | Grupos reutilizables (encabezados) |

---

## Notas Técnicas

### Sistema de Coordenadas

- **Pantalla**: Origen en esquina **superior izquierda**, Y crece hacia abajo
- **PDF (ReportLab)**: Origen en esquina **inferior izquierda**, Y crece hacia arriba
- **Conversión**: `y_pdf = altura_pagina - y_pantalla - alto_elemento`

### zIndex

El orden de apilamiento determina qué elementos se dibujan encima de otros:
- **Menor zIndex**: Se dibuja primero (detrás)
- **Mayor zIndex**: Se dibuja después (encima)

### Gestión de Imágenes

1. **Carga temporal**: Las imágenes se almacenan en base64 en `datos_temp`
2. **Guardado**: Al guardar JSON, se extraen y guardan como archivos
3. **Búsqueda en PDF**: Se busca en múltiples ubicaciones posibles
4. **Fallback**: Si no se encuentra, se muestra rectángulo con mensaje

---

## Ejemplo de Plantilla JSON Completa

```json
{
  "paginas": {
    "1": {
      "elementos": {
        "titulo": {
          "tipo": "texto",
          "geometria": {"x": 2, "y": 1, "ancho": 20, "alto": 1.5},
          "estilo": {
            "familia_fuente": "Helvetica",
            "tamano": 24,
            "negrita": "bold",
            "cursiva": "normal",
            "color": "#333333",
            "alineacion_h": "center",
            "alineacion_v": "middle",
            "rotacion": 0
          },
          "contenido": {
            "texto": "INFORME DE INCLINÓMETRO",
            "ajuste_automatico": false,
            "editable": false
          },
          "grupo": {"nombre": "Sin grupo", "color": "#cccccc"},
          "metadata": {"zIndex": 10, "visible": true, "bloqueado": false}
        },
        "logo": {
          "tipo": "imagen",
          "geometria": {"x": 1, "y": 0.5, "ancho": 3, "alto": 2},
          "estilo": {"opacidad": 100, "mantener_proporcion": true, "reduccion": 0},
          "imagen": {
            "formato": "png",
            "datos_temp": null,
            "ruta_original": "",
            "ruta_nueva": "assets/logo.png",
            "nombre_archivo": "logo.png",
            "estado": "nueva"
          },
          "grupo": {"nombre": "Sin grupo", "color": "#cccccc"},
          "metadata": {"zIndex": 5, "visible": true, "bloqueado": false}
        }
      },
      "configuracion": {"orientacion": "landscape"}
    }
  },
  "pagina_actual": "1",
  "seleccionado": null,
  "configuracion": {
    "nombre_plantilla": "Informe Estándar",
    "version": "1.0",
    "num_paginas": 1
  }
}
```

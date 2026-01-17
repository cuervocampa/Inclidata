# Análisis del Sistema de Generación de Informes PDF

Este documento detalla la arquitectura técnica y el flujo de ejecución del sistema de generación de informes PDF en **IncliData**, desde la interacción del usuario hasta la renderización final del documento.

## 1. Visión General del Proceso

El proceso se divide en cuatro etapas principales:
1.  **Configuración (Frontend):** El usuario selecciona datos y personaliza parámetros visuales en la página `/graficar`.
2.  **Orquestación (Backend):** Dash recolecta estos parámetros y activa el proceso de generación a través de un callback.
3.  **Generación de Gráficos (Data Viz):** Se ejecutan scripts de Python independientes (`matplotlib`) para crear cada gráfico definido en la plantilla.
4.  **Composición del PDF (Render):** `ReportLab` ensambla todos los elementos (gráficos, textos, formas) en un archivo PDF final.

---

## 2. Flujo Detallado

### A. Punto de Entrada (`pages/graficar.py`)
La generación se inicia mediante un **callback de Dash** que responde al botón "Generar Informe PDF".
*   **Entrada:** Estado de los controles de la UI (selector de tubo, fechas, escalas, plantilla seleccionada) y datos almacenados en `dcc.Store` (`datos_procesados`).
*   **Acción:**
    1.  Carga la plantilla JSON seleccionada desde `biblioteca_plantillas`.
    2.  Sustituye los placeholders (ej. `$CURRENT`) en la plantilla con los valores reales seleccionados por el usuario.
    3.  Llama a la función `generate_pdf_from_template` en `utils/pdf_generator.py`.
*   **Salida:** Un objeto `bytes` que contiene el PDF, listo para ser descargado por el componente `dcc.Download`.

### B. Motor de Generación (`utils/pdf_generator.py`)
Este es el núcleo del sistema.
*   **Función Principal:** `generate_pdf_from_template(template_data, data_source, ...)`
*   **Lógica:**
    *   Itera sobre las páginas definidas en el JSON de la plantilla.
    *   Configura el tamaño y orientación de página (A4 Portrait/Landscape).
    *   Ordena los elementos por `zIndex` (capas).
    *   Despacha el dibujo de cada elemento a funciones especializadas: `draw_line`, `draw_rectangle`, `draw_text`, `draw_image`, `draw_graph`.

### C. Generación de Gráficos (`biblioteca_graficos/...`)
Los gráficos no se generan directamente en el motor PDF, sino que se delegan a scripts externos modulares para máxima flexibilidad.
*   **Definición en JSON:**
    ```json
    "grafico_A": {
      "tipo": "grafico",
      "configuracion": {
        "script": "grafico_incli_0.py",
        "formato": "svg",
        "parametros": { ... }
      }
    }
    ```
*   **Ejecución Dinámica:**
    *   La función `render_matplotlib_graph` localiza el script `.py` especificado.
    *   Carga el módulo dinámicamente usando `importlib`.
    *   Ejecuta la función principal del script, pasando los datos filtrados y los parámetros de configuración.
*   **Salida del Script:** Una figura de `matplotlib`.
*   **Renderizado:** La figura se guarda temporalmente como un archivo (SVG o PNG) en el sistema de archivos.

### D. Composición con ReportLab
Una vez generados los activos gráficos temporales:
*   Si es **SVG** (vectorial): Se utiliza `svglib` para convertir el SVG a objetos nativos de ReportLab (`Drawing`), permitiendo una calidad infinita al escalar.
*   Si es **PNG** (raster): Se inserta como una imagen de mapa de bits estándar.
*   Se eliminan los archivos temporales para limpieza.
*   Finalmente, `pdf.save()` escribe el stream de bytes del PDF completo.

---

## 3. Dependencias Clave

*   **Dash:** Interfaz de usuario y gestión de estado.
*   **ReportLab:** Librería de bajo nivel para la creación programática de PDFs.
*   **Matplotlib:** Motor de generación de gráficos científicos.
*   **Svglib:** Puente crítico para convertir gráficos Matplotlib (SVG) a ReportLab, manteniendo la calidad vectorial.
*   **Pillow (PIL):** Manipulación de imágenes raster (logos, fotos).

---

## 4. Personalización de Plantillas

El sistema es altamente personalizable gracias a su arquitectura basada en datos (JSON).

### Estructura de una Plantilla
Las plantillas residen en `biblioteca_plantillas/` y constan de:
1.  **Archivo JSON:** Define la posición, tamaño y propiedades de todos los elementos visuales.
2.  **Carpeta `assets/`:** Contiene recursos estáticos como logotipos o imágenes de fondo específicas de esa plantilla.

### Edición por el Usuario
El usuario **NO** necesita editar el JSON manualmente. La aplicación incluye un editor visual dedicado:
*   **Página:** `/configuracion_plantilla_claude`
*   **Funcionalidad:**
    *   Permite cargar una plantilla existente.
    *   Ofrece herramientas visuales para mover, redimensionar y modificar propiedades de los elementos.
    *   Permite añadir nuevos elementos (textos, imágenes, áreas de gráfico).
    *   Guarda los cambios directamente en el archivo JSON de la plantilla, haciendo que las modificaciones estén disponibles inmediatamente para la generación de nuevos informes.

### Cambiar de Plantilla
En la página de generación (`/graficar`), un menú desplegable permite al usuario elegir qué plantilla aplicar a los datos actuales. Esto permite tener, por ejemplo, una plantilla para "Informes Ejecutivos" y otra para "Informes Técnicos Detallados", usando los mismos datos base.

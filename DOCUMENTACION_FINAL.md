# Documentación Final del Proyecto IncliData

## Capítulo 1: Introducción y Estructura

Bienvenido a la documentación del proyecto **IncliData**. Esta aplicación web, construida sobre Dash y Python, está diseñada para la gestión, análisis, corrección y visualización de datos de inclinometría, permitiendo la generación automatizada de informes en PDF.

### Estructura de la Aplicación

La aplicación se navega a través de una barra lateral fija que da acceso a los siguientes módulos principales:

#### 1. Info (`/`)
*   **Propósito:** Página de inicio y bienvenida.
*   **Funcionalidad:** Proporciona una visión general del estado de la aplicación o instrucciones básicas de uso.

#### 2. Importar (`/importar`)
*   **Propósito:** Ingesta de datos brutos.
*   **Funcionalidades:**
    *   Carga de archivos de datos (formatos soportados: Excel `.xlsx`, `.xlsm`, CSV, etc.).
    *   Selección de tubos inclinométricos.
    *   Previsualización de los datos importados.
    *   Almacenamiento de datos en la sesión activa (`dcc.Store`) para su uso en otros módulos.

#### 3. Graficar (`/graficar`)
*   **Propósito:** Visualización avanzada y generación de informes oficiales en PDF.
*   **Funcionalidades:**
    *   **Selección de Datos:** Elegir tubo, rango de fechas y parámetros visuales.
    *   **Configuración de Gráficos:** Personalización de ejes, leyendas y escalas de colores.
    *   **Gestión de Plantillas:** Selección de plantillas JSON predefinidas para homogeneizar los informes.
    *   **Generación de PDF:** Motor de renderizado que combina gráficos (PNG/SVG) y tablas en un documento PDF descargable.
    *   **Previsualización:** Vista rápida de cómo quedarían los gráficos antes de generar el informe final.

#### 4. Correcciones (`/correcciones`)
*   **Propósito:** Limpieza y ajuste fino de los datos.
*   **Funcionalidades:**
    *   **Corrección de Bias:** Desplazamiento sistemático de lecturas.
    *   **Eliminación de Spikes:** Detección y filtrado de picos anómalos en las lecturas.
    *   **Edición Manual:** Interfaz tipo tabla (`AgGrid` o similar) para modificar valores puntuales si es necesario.
    *   **Guardado:** Persistencia de las correcciones aplicadas para que se reflejen en los gráficos finales.

#### 5. Importar Umbrales (`/importar_umbrales`)
*   **Propósito:** Definición de límites de alerta y alarma.
*   **Funcionalidades:**
    *   Carga de configuraciones de umbrales.
    *   Asociación de niveles de aviso (Aviso, Alerta, Emergencia) con colores y estilos de línea específicos para los gráficos.

#### 6. Editor de Plantilla Claude (`/configuracion_plantilla_claude`)
*   **Propósito:** Diseño visual y edición de las plantillas de informes PDF.
*   **Funcionalidades:**
    *   **Interfaz WYSIWYG:** Constructor visual de la estructura del PDF (cabeceras, pies de página, posición de gráficos).
    *   **Gestión de Elementos:** Añadir, mover o editar cajas de texto, imágenes (logos) y áreas de gráficos.
    *   **Edición JSON:** Vista dual para editar la configuración en formato código o visualmente.
    *   **Previsualización en tiempo real:** Ver cómo afectan los cambios al diseño final del informe.

---

### Instrucciones de Ejecución

Para iniciar la aplicación en un entorno de desarrollo local:

1.  **Activar entorno virtual:**
    ```powershell
    .\venv\Scripts\Activate
    ```
2.  **Iniciar servidor:**
    ```powershell
    python app.py
    ```
3.  **Acceder:** Abrir navegador en `http://127.0.0.1:8050/`

---
*Documentación generada automáticamente el 17/01/2026.*

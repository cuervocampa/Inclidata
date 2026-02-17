# Guía de Uso de la Página "Importar"

El flujo de actividad en la página **Importar** de la aplicación Inclidata está diseñado como un asistente paso a paso (wizard) que guía al usuario de manera segura y controlada desde la selección del archivo base hasta el guardado definitivo de los nuevos datos procesados.

A continuación se detalla el análisis del flujo:

## 1. Selección del Archivo Base (Paso 1)
*   **Acción**: El usuario selecciona un archivo `.json` de inclinómetro existente desde el desplegable.
*   **Proceso Interno**: La aplicación lee este archivo de la carpeta `data` y lo carga en la memoria temporal del navegador (`dcc.Store id='tubo'`).

## 2. Configuración del Importador (Paso 2)
*   **Detección Automática**: El sistema analiza el archivo cargado para sugerir la configuración usada en la última campaña (tipo de importador e `index_0` o profundidad de inicio).
*   **Acción del Usuario**:
    *   Confirma o cambia el **Importador** (RST, Sisgeo, Soil).
    *   Establece el **Index_0** (referencia de inicio de la sonda).
    *   Define si esta carga será una nueva **Referencia** inicial.

## 3. Subida de Archivos de Datos (Paso 3)
*   **Acción**: El usuario arrastra o selecciona los archivos de datos crudos (archivos `.csv` de RST, `.xml` de Sisgeo, etc.) en el área de carga.
*   **Visualización**: Se muestra una lista confirmando los archivos que se van a procesar.

## 4. Procesamiento y Previsualización (Paso 4 - El "Cerebro")
Al pulsar "Continuar", ocurre la mayor parte de la lógica compleja:
1.  **Lectura y Parsing**: Se decodifican los archivos subidos y se envían a la función específica (`import_RST`, `import_Sisgeo`, etc.) en `utils/funciones_importar.py`.
    *   Se extraen las lecturas crudas (A+, A-, B+, B-).
    *   Se convierten a milímetros y se normalizan.
2.  **Validación Cronológica Crítica**: El sistema verifica que la fecha de las nuevas campañas **NO sea anterior** a la primera referencia existente. Si detecta un conflicto, bloquea el proceso y muestra una alerta.
3.  **Cálculos Matemáticos**:
    *   Se integran las nuevas campañas en el objeto `tubo` temporal.
    *   Se calculan los **incrementos** comparando cada nueva lectura con su referencia correspondiente.
    *   Se evalúan si superan los **umbrales de alarma** definidos en el archivo JSON.
4.  **Generación de Interfaz**:
    *   Se generan gráficos preliminares para inspección visual.
    *   Se construye una **Tabla de Configuración** donde el usuario puede ver y editar: Fecha, Hora, si la campaña está Activa/Cuarentena, y si se debe Subir o Ignorar.

## 5. Guardado Final (Paso 5)
*   **Acción**: El usuario revisa la tabla y pulsa "Guardar campañas".
*   **Escritura en Disco**:
    1.  Se recolectan todos los datos y correcciones manuales de la tabla.
    2.  La función `insertar_camp` lee nuevamente el archivo original del disco (para seguridad).
    3.  Inserta las nuevas campañas.
    4.  **Reordena todo el archivo cronológicamente** (fundamental para mantener la consistencia de las series temporales).
    5.  Sobrescribe el archivo JSON con la versión actualizada.

---
**Resumen del Flujo**:
`Carga JSON base` -> `Configura Importador` -> `Sube Raw Data` -> `Procesa/Calcula/Valida` -> `Revisa` -> `Guarda y Ordena`

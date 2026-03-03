# Análisis de la Generación de Gráficos en Inclidata

Este documento analiza cómo se estructura cada gráfico, cómo y dónde se almacena la información, la estructura del JSON utilizado y cómo se definen los gráficos en la carpeta `/biblioteca_graficos`, en el contexto del script `pages/graficar.py`.

## 1. Almacenamiento de la Información

Cuando el usuario carga un archivo JSON a través del componente `dcc.Upload` en `pages/graficar.py` (id=`graficar-uploader`), el contenido decodificado se procesa y se almacena en componente `dcc.Store` de memoria con el identificador `graficar-tubo`. 

La información viaja como un diccionario por la aplicación y se pasa como los argumentos `data` a las funciones encargadas de generar los gráficos. Por otra parte, desde la interfaz (sliders, inputs, botones) se conforma un diccionario `parametros` con opciones de configuración (esquema de colores, tipo de escala de los ejes, nombre del sensor, etc).

## 2. Estructura del JSON (Diccionario de Datos `data`)

El diccionario (generado a partir del JSON subido) tiene la siguiente forma:

1. **`info`**: Objeto con metadatos del sensor (ej: `nom_sensor`, `nombre`).
2. **`umbrales`**: Objeto que define los umbrales de alerta. Dentro, típicamente hay una clave `valores` con un array de registros indicando la deformación máxima/mínima por cota para cada alerta (`umbral1_a`, `umbral1_b`, etc.).
3. **Claves de fecha (`YYYY-MM-DDTHH:MM:SS`)**: El resto de claves en el primer nivel del diccionario suelen ser fechas ISO correspondientes a cada campaña de lectura activa. Estas fechas contienen en su interior:
   - `campaign_info`: Detalles de la campaña (ej. `active`: true/false).
   - `info_readout`: Metadatos de lectura.
   - **`calc`**: Un array de objetos, donde cada objeto corresponde a una lectura a una profundidad determinada y porta sus parámetros calculados:
     - `index`: Índice o profundidad raw.
     - `cota_abs`: Cota absoluta.
     - `depth`: Profundidad desde la superficie.
     - Diferentes parámetros de sensores como: `desp_a`, `desp_b`, `incr_dev_a`, `incr_dev_b`, `incr_dev_abs_a`, `checksum_a`, etc.

## 3. Estructura y Definiciones en `biblioteca_graficos`

Los gráficos se diseñan de manera modular. Todo el código para renderizar cada tipo de gráfico reside en capetas individuales dentro de `/biblioteca_graficos` (por ejemplo, `grafico_incli_0`, `grafico_incli_evo_tempo`, etc).

### A. Estructura de cada subcarpeta
Cada subcarpeta correspondiente a un gráfico suele contener:
- El archivo principal del gráfico (ej. `grafico_incli_0.py`).
- Un archivo de funciones auxiliares (`funciones.py`).

### B. El archivo principal del gráfico
El archivo principal define una función con el mismo nombre de la carpeta (ej. `def grafico_incli_0(data, parametros):`). Sus responsabilidades son:
1. Recibir los dos parámetros esenciales: 
   - `data`: El diccionario del JSON anteriormente descrito.
   - `parametros`: Diccionario de opciones visuales y selecciones de la UI.
2. Formatear y preparar los subconjuntos del JSON empleando el módulo interno `funciones.py`.
3. Instanciar un gráfico usando `matplotlib.pyplot` en un backend no interactivo (`Agg`).
4. Generar el trazado con las series, configurar los ejes, el título, y manejar las reservas de espacio (como en `grafico_incli_evo_tempo` que reserva el 25% de espacio).
5. Guardar la figura en un buffer binario en formato `PNG` o `SVG`.
6. Retornar la imagen directamente como una cadena codificada en Base64 lista para web/pdf: `f"data:image/png;base64,{imagen_base64}"`.

### C. Archivo de Funciones (`funciones.py`)
Encapsula la lógica matemática y de preprocesamiento necesaria para construir el gráfico particular:
- `calcular_fechas_seleccionadas`: Calcula dinámicamente qué campañas/fechas son las que se van a renderizar de acuerdo a la UI (cadencia, últimas campañas, etc).
- `get_color_for_index` / `generar_info_colores`: Lógica para los esquemas "monocromo" y "multicromo".
- `extraer_datos_fecha` / `extraer_datos_temporales_profundidades`: Recorre el objeto `calc` de la fecha indicada del diccionario y crea listas con los valores purgados de `X` e `Y` listas para dárselas a `matplotlib`.
- `interpolar_def_tubo`: Ajustes matemáticos en caso de que los valores de umbrales en cotas no cuadren exactamente con la cota de lectura actual del tubo.

## 4. Generación de PDF y vista previa (`graficar.py`)

A través de la función `generar_seccion_grafico` de `utils/funciones_graficar.py`, la aplicación carga estas funciones de forma **dinámica**. Lee la configuración, busca el script necesario como módulo (ej. `importlib.util.spec_from_file_location`), y le evalúa los parámetros actuales pasándole el JSON en memoria (`graficar-tubo`). El Base64 devuelto se inyecta luego en el informe final en PDF o se muestra a nivel de previsualización web.

## 5. Configuración del Informe PDF (Textos Editables)

Al pulsar en el botón de "PDF" y abrirse el modal "Configuración del Informe PDF", se despliega una interfaz que permite al usuario seleccionar una **plantilla base** para el informe y personalizar su contenido estático antes de generarlo. 

Lo que hace específicamente el apartado de **TEXTOS EDITABLES** que se muestra en la imagen (al seleccionar una plantilla) es lo siguiente:

1. **Lectura de la Plantilla**: La aplicación (`pages/graficar.py`, mediante el callback `cargar_plantilla_seleccionada_mejorada`) carga por detrás el archivo JSON de la plantilla seleccionada (por ejemplo, `INCL_AR_prueba_kk_01.json`).
2. **Búsqueda de Textos Dinámicos**: El código recorre toda la estructura de la plantilla JSON buscando elementos que sean de tipo `"texto"` y que tengan la propiedad `"editable": true`.
3. **Generación Dinámica de Formularios**: Por cada texto editable encontrado, genera un campo de entrada (input) en la interfaz:
   - La **etiqueta** que aparece encima de cada input (ej: `[paginas][1][elementos][titulo][contenido][texto]`) representa la ruta exacta dentro de la estructura profunda del JSON de la plantilla donde se ubica ese texto. 
   - El **valor por defecto** del input es el texto "placeholder" que viene precargado en el documento JSON de la plantilla original (por ejemplo, `"ROZMARIN INCLINOMETERS"` o `"PROJECT:"`).
   - Existe un **caso especial** programado en el código para el texto llamado `nombre_sensor`. Si la plantilla requiere el nombre del sensor, el sistema ignora el texto por defecto del JSON e inserta automáticamente el nombre del archivo de datos actual (ej: "IN_Ejemplo" obtenido de la memoria de la app).
4. **Propósito Final**: Esto habilita al usuario a modificar títulos, nombres de proyectos, responsables, referencias o localizaciones que requiera el informe PDF finalizado, de una manera cómoda en la UI y sin tener que recompilar la plantilla base.

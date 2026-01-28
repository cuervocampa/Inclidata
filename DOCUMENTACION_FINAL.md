# Documentación Final del Proyecto IncliData

*Última actualización: 28/01/2026*

---

## Capítulo 1: Introducción y Estructura

Bienvenido a la documentación del proyecto **IncliData**. Esta aplicación web, construida sobre Dash y Python, está diseñada para la gestión, análisis, corrección y visualización de datos de inclinometría, permitiendo la generación automatizada de informes en PDF.

### Tecnologías Principales

| Tecnología | Versión Mínima | Propósito |
|------------|----------------|-----------|
| Python | 3.10+ | Lenguaje base |
| Dash | 2.16+ | Framework web |
| Plotly | 5.20+ | Gráficos interactivos |
| Matplotlib | 3.8+ | Gráficos para PDF |
| ReportLab | 4.0+ | Generación de PDF |
| Pandas | 2.2+ | Procesamiento de datos |

---

## Capítulo 2: Estructura del Proyecto

```
IncliData/
├── app.py                      # Punto de entrada principal
├── requirements.txt            # Dependencias del proyecto
│
├── pages/                      # Módulos de la aplicación
│   ├── info.py                 # Página de inicio
│   ├── importar.py             # Importación de datos
│   ├── graficar.py             # Visualización y generación PDF
│   ├── correcciones.py         # Corrección de datos (bias, spikes)
│   ├── importar_umbrales.py    # Gestión de umbrales de alarma
│   ├── editor_plantilla.py     # Editor visual de plantillas PDF
│   └── configuraciones.py      # Configuraciones (placeholder)
│
├── utils/                      # Funciones auxiliares
│   ├── diccionarios.py         # Constantes y mapeos
│   ├── funciones_comunes.py    # Utilidades generales
│   ├── funciones_correcciones.py
│   ├── funciones_graficar.py
│   ├── funciones_graficos.py
│   ├── funciones_grupos.py
│   ├── funciones_importar.py
│   ├── funciones_configuracion_plantilla.py
│   ├── pdf_generator.py        # Motor de generación PDF
│   └── analyze_dependencies.py # Script para documentar librerías
│
├── biblioteca_graficos/        # Scripts de gráficos para PDF
│   ├── grafico_incli_0/        # Gráfico de desplazamientos
│   ├── grafico_incli_evo_std_chk/  # Evolución con std
│   ├── grafico_incli_evo_tempo/    # Evolución temporal
│   ├── grafico_incli_leyenda_0/    # Leyendas
│   └── grafico_incli_series_0/     # Series temporales
│
├── biblioteca_tablas/          # Scripts de tablas dinámicas
│   └── tabla_datos_inc/        # Tabla de datos de inclinómetro
│
├── biblioteca_grupos/          # Grupos reutilizables (encabezados)
│   ├── grupo_encab_hor_L9/
│   ├── grupo_encab_vert_L9/
│   └── tabla_inclis_L9_3camp/
│
├── biblioteca_plantillas/      # Plantillas PDF configurables
│   ├── Incli_L9_BCN/
│   ├── encabezado_0/
│   └── ...
│
├── data/                       # Datos de inclinómetros (JSON)
└── assets/                     # Recursos estáticos (CSS, imágenes)
```

---

## Capítulo 3: Módulos de la Aplicación

La aplicación se navega a través de una barra lateral fija que da acceso a los siguientes módulos principales:

### 1. Info (`/`)
- **Propósito:** Página de inicio y bienvenida.
- **Funcionalidad:** Proporciona una visión general del estado de la aplicación.

### 2. Importar (`/importar`)
- **Propósito:** Ingesta de datos brutos.
- **Funcionalidades:**
  - Carga de archivos de datos (formatos: RST, Sisgeo, Soil Dux, Excel).
  - Selección y gestión de tubos inclinométricos.
  - Previsualización de los datos importados.
  - Almacenamiento de datos en la sesión activa (`dcc.Store`).

### 3. Graficar (`/graficar`)
- **Propósito:** Visualización avanzada y generación de informes PDF.
- **Funcionalidades:**
  - **Selección de Datos:** Elegir tubo, rango de fechas y parámetros visuales.
  - **Configuración de Gráficos:** Personalización de ejes, leyendas y escalas de colores.
  - **Gestión de Plantillas:** Selección de plantillas JSON predefinidas.
  - **Generación de PDF:** Motor que combina gráficos (SVG/PNG), tablas y textos.
  - **Previsualización en tiempo real:** Vista de los gráficos antes de generar.
  - **Parámetros dinámicos:** Soporte para `$CURRENT` que se sustituye automáticamente.

### 4. Correcciones (`/correcciones`)
- **Propósito:** Limpieza y ajuste fino de los datos.
- **Funcionalidades:**
  - **Corrección de Bias:** Desplazamiento sistemático de lecturas.
  - **Eliminación de Spikes:** Detección y filtrado de picos anómalos.
  - **Edición Manual:** Interfaz tipo tabla (AgGrid) para modificar valores.
  - **Gráficos de Violines:** Visualización estadística de la distribución.
  - **Guardado:** Persistencia de las correcciones en el JSON del tubo.

### 5. Importar Umbrales (`/importar_umbrales`)
- **Propósito:** Definición de límites de alerta y alarma.
- **Funcionalidades:**
  - Carga de configuraciones de umbrales desde Excel.
  - Asociación de niveles (Aviso, Alerta, Emergencia) con colores.
  - Visualización de umbrales en los gráficos.

### 6. Editor de Plantillas (`/editor_plantilla`)
- **Propósito:** Diseño visual de plantillas de informes PDF.
- **Funcionalidades:**
  - **Interfaz WYSIWYG:** Constructor visual de la estructura del PDF.
  - **Elementos soportados:** Texto, imágenes, líneas, rectángulos, gráficos, tablas.
  - **Gestión de Páginas:** Soporte multipágina con orientación independiente.
  - **Grupos reutilizables:** Encabezados y pies de página guardables.
  - **Tablas multinivel:** Configuración avanzada de columnas y subcolumnas.
  - **Exportación:** Guardar como JSON (reutilizable) o PDF (distribución).

---

## Capítulo 4: Sistema de Generación de PDF

### Flujo de Generación

1. **Configuración (Frontend):** El usuario selecciona datos y plantilla en `/graficar`.
2. **Orquestación (Backend):** Dash recolecta parámetros y activa el callback.
3. **Sustitución de Placeholders:** Variables como `$CURRENT` se reemplazan.
4. **Generación de Gráficos:** Scripts de `biblioteca_graficos/` crean figuras Matplotlib.
5. **Composición del PDF:** ReportLab ensambla todos los elementos.
6. **Descarga:** El PDF se entrega al navegador.

### Bibliotecas de Elementos

| Biblioteca | Contenido |
|------------|-----------|
| `biblioteca_graficos/` | Scripts Python que generan gráficos Matplotlib |
| `biblioteca_tablas/` | Scripts Python que generan datos para tablas |
| `biblioteca_grupos/` | Elementos JSON reutilizables (encabezados) |
| `biblioteca_plantillas/` | Plantillas completas de informe |

---

## Capítulo 5: Instrucciones de Ejecución

### Requisitos Previos

- Python 3.10 o superior
- Windows (para algunas funcionalidades de `pywin32`)

### Instalación

```powershell
# Clonar repositorio
git clone https://github.com/cuervocampa/IncliData.git
cd IncliData

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
.\venv\Scripts\Activate

# Instalar dependencias
pip install -r requirements.txt
```

### Ejecución

```powershell
# Activar entorno virtual (si no está activo)
.\venv\Scripts\Activate

# Iniciar servidor
python app.py
```

### Acceso

Abrir navegador en: **http://127.0.0.1:8050/**

---

## Capítulo 6: Archivos de Configuración

### `requirements.txt`
Contiene todas las dependencias del proyecto con versiones mínimas compatibles.

### Plantillas JSON
Las plantillas en `biblioteca_plantillas/` definen:
- Estructura de páginas
- Posición y estilo de elementos
- Parámetros para gráficos y tablas
- Referencias a assets (logos, imágenes)

### Datos de Inclinómetros
Los archivos JSON en `data/` contienen:
- Campañas de medición por fecha
- Profundidades y lecturas
- Correcciones aplicadas (bias, spikes)
- Umbrales configurados

---

*Documentación generada para IncliData v1.0 - 28/01/2026*

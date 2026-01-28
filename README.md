# IncliData

**Aplicación de gestión, análisis y visualización de datos de inclinometría**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Dash](https://img.shields.io/badge/Dash-2.16+-green.svg)](https://dash.plotly.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

---

## 📋 Descripción

**IncliData** es una aplicación web construida con Dash y Python, diseñada para la gestión integral de datos de inclinometría. Permite:

- 📥 **Importar** datos desde múltiples formatos (RST, Sisgeo, Soil Dux, Excel)
- 📊 **Visualizar** gráficos interactivos de desplazamientos y evolución temporal
- 🔧 **Corregir** datos (bias, spikes) mediante herramientas visuales
- 📄 **Generar** informes PDF personalizados con plantillas configurables
- ⚠️ **Gestionar** umbrales de alerta y alarma

---

## 🚀 Instalación

### Requisitos

- Python 3.10 o superior
- Windows (para algunas funcionalidades de integración)

### Pasos

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

---

## ▶️ Ejecución

```powershell
# Activar entorno virtual
.\venv\Scripts\Activate

# Iniciar servidor
python app.py
```

Abrir navegador en: **http://127.0.0.1:8050/**

---

## 📁 Estructura del Proyecto

```
IncliData/
├── app.py                      # Punto de entrada principal
├── requirements.txt            # Dependencias
│
├── pages/                      # Módulos de la aplicación
│   ├── info.py                 # Página de inicio
│   ├── importar.py             # Importación de datos
│   ├── graficar.py             # Visualización y PDF
│   ├── correcciones.py         # Corrección de datos
│   ├── importar_umbrales.py    # Gestión de umbrales
│   └── editor_plantilla.py     # Editor de plantillas
│
├── utils/                      # Funciones auxiliares
│   ├── pdf_generator.py        # Motor de generación PDF
│   └── ...
│
├── biblioteca_graficos/        # Scripts de gráficos
├── biblioteca_tablas/          # Scripts de tablas
├── biblioteca_grupos/          # Elementos reutilizables
├── biblioteca_plantillas/      # Plantillas PDF
│
└── data/                       # Datos de inclinómetros
```

---

## 📚 Documentación

| Documento | Descripción |
|-----------|-------------|
| [DOCUMENTACION_FINAL.md](DOCUMENTACION_FINAL.md) | Documentación general del proyecto |
| [ANALISIS_GENERACION_PDF.md](ANALISIS_GENERACION_PDF.md) | Arquitectura del sistema de PDF |
| [DOCUMENTACION_EDITOR_PLANTILLAS.md](DOCUMENTACION_EDITOR_PLANTILLAS.md) | Guía del editor de plantillas |
| [LIBRERIAS_POR_ARCHIVO.md](LIBRERIAS_POR_ARCHIVO.md) | Dependencias por archivo |

---

## 🛠️ Tecnologías

| Tecnología | Uso |
|------------|-----|
| **Dash** | Framework web |
| **Plotly** | Gráficos interactivos |
| **Matplotlib** | Gráficos para PDF |
| **ReportLab** | Generación de PDF |
| **Pandas** | Procesamiento de datos |
| **Mantine Components** | UI moderna |

---

## 📊 Módulos

### Importar (`/importar`)
Carga de datos desde archivos en formatos RST, Sisgeo, Soil Dux y Excel.

### Graficar (`/graficar`)
Visualización de desplazamientos con gráficos interactivos y generación de informes PDF.

### Correcciones (`/correcciones`)
Herramientas para corregir bias sistemático y eliminar picos anómalos.

### Importar Umbrales (`/importar_umbrales`)
Configuración de niveles de alerta con umbrales personalizables.

### Editor de Plantillas (`/editor_plantilla`)
Editor visual WYSIWYG para diseñar plantillas de informes PDF.

---

## 📝 Versión

**v1.0** - Enero 2026

---

## 👤 Autor

**[Cuervo Campa]**

---

*Última actualización: 28/01/2026*

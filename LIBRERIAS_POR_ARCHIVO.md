# Documentación de Librerías por Archivo

Este documento detalla las librerías de terceros utilizadas en cada archivo del proyecto **IncliData**.

*Última actualización: 28/01/2026*

---

## Archivo Principal

### `app.py`
- dash
- dash-bootstrap-components
- dash-mantine-components

---

## Páginas (`pages/`)

### `pages/info.py`
- dash

### `pages/importar.py`
- dash
- dash-bootstrap-components
- dash-iconify
- dash-mantine-components

### `pages/graficar.py`
- dash
- dash-bootstrap-components
- dash-iconify
- dash-mantine-components
- icecream
- matplotlib
- pandas
- plotly

### `pages/correcciones.py`
- dash
- dash-ag-grid
- dash-mantine-components
- icecream
- pandas
- plotly
- sqlalchemy

### `pages/importar_umbrales.py`
- dash
- dash-iconify
- dash-mantine-components
- numpy
- pandas

### `pages/editor_plantilla.py`
- dash
- dash-iconify
- dash-mantine-components
- reportlab
- requests

### `pages/configuraciones.py`
- dash

---

## Utilidades (`utils/`)

### `utils/diccionarios.py`
- *(Sin dependencias externas)*

### `utils/funciones_comunes.py`
- plotly
- pywin32 (`win32gui`)

### `utils/funciones_configuracion_plantilla.py`
- dash

### `utils/funciones_correcciones.py`
- dash
- pandas
- plotly

### `utils/funciones_graficar.py`
- dash
- dash-mantine-components
- numpy
- plotly

### `utils/funciones_graficos.py`
- dash
- pandas
- plotly

### `utils/funciones_grupos.py`
- *(Solo librería estándar: pathlib, json, shutil)*

### `utils/funciones_importar.py`
- dash

### `utils/pdf_generator.py`
- Pillow
- matplotlib
- reportlab
- svglib

### `utils/analyze_dependencies.py`
- *(Script de utilidad para generar esta documentación)*

---

## Biblioteca de Gráficos (`biblioteca_graficos/`)

### `biblioteca_graficos/grafico_incli_0/`
| Archivo | Librerías |
|---------|-----------|
| `funciones.py` | matplotlib, numpy, pandas |
| `grafico_incli_0.py` | matplotlib, numpy, pandas |

### `biblioteca_graficos/grafico_incli_evo_std_chk/`
| Archivo | Librerías |
|---------|-----------|
| `funciones.py` | matplotlib, numpy, pandas, scipy |
| `grafico_incli_evo_std_chk.py` | matplotlib, numpy, pandas |

### `biblioteca_graficos/grafico_incli_evo_tempo/`
| Archivo | Librerías |
|---------|-----------|
| `funciones.py` | matplotlib, numpy, pandas |
| `grafico_incli_evo_tempo.py` | matplotlib, numpy, pandas |

### `biblioteca_graficos/grafico_incli_leyenda_0/`
| Archivo | Librerías |
|---------|-----------|
| `funciones.py` | matplotlib, numpy |
| `grafico_incli_leyenda_0.py` | matplotlib |

### `biblioteca_graficos/grafico_incli_series_0/`
| Archivo | Librerías |
|---------|-----------|
| `funciones.py` | matplotlib, numpy |
| `grafico_incli_series_0.py` | matplotlib |

---

## Biblioteca de Tablas (`biblioteca_tablas/`)

### `biblioteca_tablas/tabla_datos_inc/`
| Archivo | Librerías |
|---------|-----------|
| `tabla_datos_inc.py` | *(Depende de data_source)* |

---

## Resumen de Dependencias

| Librería | Uso Principal |
|----------|---------------|
| `dash` | Framework principal de la aplicación web |
| `dash-mantine-components` | Componentes UI modernos |
| `dash-bootstrap-components` | Layout y estilos Bootstrap |
| `dash-ag-grid` | Tablas interactivas editables |
| `dash-iconify` | Iconos SVG |
| `plotly` | Gráficos interactivos en web |
| `matplotlib` | Gráficos estáticos para PDFs |
| `pandas` | Manipulación de datos |
| `numpy` | Cálculos numéricos |
| `scipy` | Interpolaciones y funciones científicas |
| `reportlab` | Generación de PDFs |
| `svglib` | Conversión SVG → ReportLab |
| `Pillow` | Procesamiento de imágenes |
| `SQLAlchemy` | Conexiones a bases de datos |
| `openpyxl` | Lectura de archivos Excel |
| `XlsxWriter` | Escritura de archivos Excel |
| `icecream` | Debug y logging |
| `pywin32` | Integración con Windows |
| `requests` | Peticiones HTTP |

---

## Instalación

```bash
pip install -r requirements.txt
```

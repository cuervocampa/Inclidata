CLAUDE.md - Contexto de Inclidata

Sistema de generación de informes PDF dinámicos para instrumentación geotécnica.
🛠 Comandos del Proyecto

    Iniciar App: python app.py

    Tests: pytest

    Instalar dependencias: pip install -r requirements.txt

📋 Reglas de Estilo y Arquitectura

    Python: Usar snake_case para funciones/variables y PascalCase para clases.

    Componentes: Basados en Dash y Dash Mantine Components (DMC).

    Modelos de Datos: Se prefiere el uso de Pydantic v2 para validación de JSON (en refactorización).

    Lógica de Negocio: Mantener callbacks de Dash ligeros; delegar lógica pesada a archivos en utils/.

🏗️ Sistema de Plantillas (Core Logic)

    Unidades de Medida: * Disco (JSON): Siempre en centímetros (cm) para geometría y anchos de columna.

        Editor (React): Usa porcentajes (%) para anchos de columna en tablas y coordenadas visuales.

        Conversión: La función _convertir_elemento hace el puente entre formatos.

    Gestión de Assets:

        Las imágenes se gestionan centralizadamente en utils/asset_manager.py.

        IMPORTANTE: Al guardar, se debe limpiar el campo src (base64) del JSON y registrar el asset_id para evitar archivos gigantes.

    Estructura de Carpetas:

        biblioteca_plantillas/{nombre}/: Contiene {nombre}.json y carpeta assets/.

        biblioteca_graficos/ y biblioteca_tablas/: Contienen los scripts .py que generan contenido dinámico.

    Data Binding: Se usa el token "$CURRENT" para inyectar valores de la UI en los parámetros de los scripts.

📂 Estructura Crítica

    pages/editor_visual.py: Editor principal con componente React dce.Editor.

    utils/pdf_generator.py: Motor de renderizado (ReportLab/WeasyPrint).

    utils/asset_manager.py: Registro y trackeo de imágenes.
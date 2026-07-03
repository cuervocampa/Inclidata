CLAUDE.md - Contexto de Inclidata

IncliData es un visor/corrector/impresor de datos de instrumentación geotécnica (inclinómetros).
Las plantillas de informe se diseñan en Maketator (editor eliminado de IncliData en v2.0).

---

🛠 Comandos del Proyecto

    Iniciar App (estable):     python app.py
    Iniciar App (modo dev):    INCLIDATA_DEBUG=1 python app.py
    Tests:                     pytest
    Instalar dependencias:     pip install -r requirements.txt

---

📋 Reglas de Estilo y Arquitectura

    Python: snake_case para funciones/variables, PascalCase para clases.

    Componentes: Dash 4.x + Dash Mantine Components (DMC v2) + Dash Bootstrap Components.

    Callbacks ligeros: delegar lógica pesada a utils/. No acumular estado en callbacks.

    Motor productivo = HTML/Playwright (engines/html_engine.py + utils/report_engine.py).
    ESTOS ARCHIVOS NO SE PARCHEAN LOCALMENTE. Vienen trasplantados de Maketator; cualquier
    cambio se coordina con Maketator y se trasplanta de nuevo.

---

🏗️ Motor de Render

    Render: engines/html_engine.py → Playwright/Chromium → PDF
    Fachada: utils/report_engine.py (generate_report_pdf_from_state)
    Plantillas: biblioteca_plantillas/html/{nombre}/{nombre}.json
    Scripts gráficos: biblioteca_graficos/html/{namespace}/{script}.py
    Scripts tablas: biblioteca_tablas/funciones/{script}.py

    ReportLab está RETIRADO. El código ReportLab vive en info/legacy/ como referencia.

---

📦 Puente de datos: json_inclis

    Al subir un sensor, graficar.py escribe el JSON original a json_inclis/{sensor_id}.json.
    El motor HTML lee ese archivo en tiempo de render para generar gráficos.
    json_inclis/ está excluido del reloader (ver CONTEXT.md).

---

⚠️ Regla del store `graficar-tubo`

    Las claves raíz del store graficar-tubo son EXCLUSIVAMENTE timestamps de campaña (ISO 8601)
    más las claves reservadas `info` y `umbrales`.
    Cualquier metadato nuevo (sensor_id, nombre, etc.) va DENTRO de info{}, nunca en la raíz.

---

🚦 Arranque dual (app.py)

    Estable (por defecto): debug=False, use_reloader=False
    Dev (INCLIDATA_DEBUG=1): debug=True, dev_tools_hot_reload=False, exclude_patterns=[...]

    exclude_patterns es CRÍTICO en modo dev: evita que el reloader reinicie el servidor cuando
    la app escribe archivos en runtime (json_inclis, logs, registry.json). Sin esto los callbacks
    en vuelo mueren con "server did not respond".

---

📂 Archivos críticos

    app.py                     Punto de entrada. Arranque dual. Logging consola+archivo.
    pages/graficar.py          Modal de informe PDF, subida de sensor, visualización.
    utils/report_engine.py     Fachada del motor HTML.
    engines/html_engine.py     Motor HTML (NO parchear localmente).
    utils/template_service.py  Carga de plantillas y scripts.
    utils/asset_manager.py     Gestión centralizada de imágenes.

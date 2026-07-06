---
name: IncliData v2.0 — motor HTML consolidado
description: Estado del proyecto tras consolidación migración motor HTML (tag v2.0-motor-html, 2026-07-03)
type: project
---

The project reached the v2.0-motor-html milestone on 2026-07-03. IncliData is now a standalone PDF printer using the HTML/Playwright engine transplanted from Maketator. The template editor was removed.

Key facts:
- Motor productivo: engines/html_engine.py + utils/report_engine.py (Playwright/Chromium)
- ReportLab completamente retirado de requirements.txt y del código vivo
- Template editor (dce.Editor React) eliminado; plantillas se crean en Maketator
- Arranque dual: python app.py (estable) / INCLIDATA_DEBUG=1 python app.py (dev con exclude_patterns)
- Código muerto archivado en info/legacy/: template_models.py, template_service_editor_funcs.py, graficar_vista_previa_legacy.py, funciones_informe_inclinometro_legacy.py
- models/template_models.py movido a info/legacy/ (sin importadores vivos)
- Recuperación del estado anterior: tag v1.0-pre-poda-reportlab o rama archive/full-editor-reportlab

**Why:** La migración al motor HTML elimina la dependencia de ReportLab y del editor visual, dejando IncliData como un viewer/corrector/printer limpio.
**How to apply:** No modificar engines/html_engine.py localmente; coordinar cambios con Maketator. Para añadir metadatos al store graficar-tubo, poner dentro de info{}, nunca en la raíz.

# Estado de Refactorización — IncliData

_Última actualización: 2026-04-26_

---

## Fase 1 — Limpieza sin riesgo funcional ✅ COMPLETA

| # | Tarea | Estado |
|---|---|---|
| 1.1 | `requirements.txt`: eliminar `pydantic` duplicado y `SQLAlchemy` | ✅ |
| 1.2 | Logs rastreados en git: ya cubiertos por `.gitignore` (no estaban trackeados) | ✅ |
| 1.3 | Archivos temp: `debug_bias.json`, `debug_spikes.json`, `tmp_*.txt`, `antigravity.md` | ✅ |
| 1.4 | Scripts residuales: `inclidata.py`, `debug_import.py`, `reproduce_issue.py` | ✅ |
| 1.5 | Datos/salidas sueltas en raíz: `ejemplo_datos.csv`, `salida_medias_.xlsx`, `test_umbrales_IPI_50.json`, `Pasted image.png`, `PROTOTIPO_LOVABLE.tsx` | ✅ |
| 1.6 | Plantillas sandbox "kk": `kk/`, `kk_1/`, `kk_03/`, `INCL_AR_kk_2/`, `INCL_AR_prueba_kk_01/` | ✅ |
| 1.7 | Scripts ejemplo: `biblioteca_graficos/grafico_ejemplo/`, `biblioteca_tablas/ejemplo_tabla_kk/` | ✅ |
| 1.8 | Docs redundantes: `ANALISIS_GENERACION_PDF.md`, `analisis_graficos.md`, `analisis_plantillas.md`, `DOCUMENTACION_EDITOR_PLANTILLAS.md`, `DOCUMENTACION_FINAL.md`, `listado_archivos.md`, `LIBRERIAS_POR_ARCHIVO.md` | ✅ |
| 1.9 | Docs legacy: `Documentación IncliData_v0_Claude.docx/pdf`, `_Documentación/` | ✅ |
| 1.10 | Copias de plantillas: `data/Plantilla - copia.json`, `data/Plantilla_Ejemplo_RST_vacio - copia.json` | ✅ |
| 1.11 | Herramienta de dev: `utils/analyze_dependencies.py` | ✅ |

---

## Fase 2 — Limpieza de app.py ✅ COMPLETA

| # | Tarea | Resultado |
|---|---|---|
| 2.1 | Eliminar imports comentados (`configuracion_plantilla_gpt`, `graficar_debug`) | ✅ |
| 2.2 | Monkey-patch de callbacks → `utils/dev_logging.py` (activa con `DEBUG_CALLBACKS=1`) | ✅ |
| 2.3 | Limpiar comentarios de debug inline | ✅ |
| 2.4 | Dark mode: reemplazar dicts duplicados con `_THEMES = {"light": {...}, "dark": {...}}` | ✅ |
| 2.5 | Router: reemplazar if/elif con dict `routes` | ✅ (bonus) |

---

## Fase 3 — Refactorización de archivos grandes ✅ COMPLETA (primera ronda)

| # | Archivo | Antes | Después | Delta | Técnica |
|---|---|---|---|---|---|
| 3.1 | `pages/graficar.py` | 3 528 | 2 922 | -606 | Layout → `graficar_layout.py` |
| 3.2 | `pages/correcciones.py` | 2 628 | 2 059 | -569 | Layout → `correcciones_layout.py` + fix SQLAlchemy + fix logging |
| 3.3 | `pages/editor_plantilla.py` | 6 801 | 4 522 | -2 279 | Layout → `editor_plantilla_layout.py` |

**Total extraído: 3 454 líneas** a tres archivos `_layout.py` independientes y testeables.

### Archivos nuevos creados
- `pages/graficar_layout.py` (618 líneas)
- `pages/correcciones_layout.py` (573 líneas)
- `pages/editor_plantilla_layout.py` (2 289 líneas)
- `utils/dev_logging.py` (47 líneas)

---

## Próximas iteraciones (Fase 4 — pendiente)

| Prioridad | Tarea | Descripción |
|---|---|---|
| 🔴 Alta | Dividir `register_callbacks` en `editor_plantilla.py` | Separar ≈67 callbacks en grupos: `_register_canvas_callbacks`, `_register_tabla_callbacks`, `_register_grupos_callbacks`, `_register_export_callbacks`. Cada grupo permanece en el mismo archivo pero como funciones top-level. |
| 🟡 Media | Extraer constructores de figura en `graficar.py` | Mover lógica de figuras Plotly de los callbacks a `utils/funciones_graficar.py`. |
| 🟡 Media | Dividir `layout()` en `editor_plantilla_layout.py` | 2 280 líneas en una función — dividir en funciones `_render_*()` privadas. |
| 🟢 Baja | Añadir type hints a callbacks | Empezar por los callbacks más cortos. |
| 🟢 Baja | Renombrar `biblioteca_plantillas/incli_L9_BCN_v0[b]/` | Los corchetes en el nombre causan problemas de glob/shell. |

---

## Notas técnicas

- `pages/spikes.json` es intencional en esa carpeta (path relativo calculado en `correcciones.py:1059`).
- `scripts/migrate_assets.py` se mantiene por si la migración necesita re-ejecutarse.
- `Guia_estilo.md` y `Guía_uso_Importar.md` se mantienen hasta consolidar en `CLAUDE.md`.
- Verificación de imports: `python -c "from pages import graficar, correcciones, editor_plantilla"` → OK.

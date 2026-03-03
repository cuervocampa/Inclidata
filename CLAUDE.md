# Proyecto Inclidata (Dash App)

## Comandos rápidos
- Ejecutar App: `python app.py`
- Instalar dependencias: `pip install -r requirements.txt`
- Tests: `pytest`

## Guía de Estilo Python/Dash
- Seguir PEP 8.
- Organizar los callbacks de Dash cerca de los componentes de layout correspondientes.
- Usar nombres descriptivos para los `id` de los componentes (ej: `dropdown-seleccion-pais`).

## Notas de Arquitectura
- El servidor de Dash está en la variable `app.server` (para despliegues).
- Los archivos estáticos están en `/assets`.

## Preferencias de Claude Code
- **Concisión**: No expliques conceptos básicos de Python o Dash a menos que se solicite.
- **Diffs**: Prefiere mostrar solo los fragmentos de código modificados en lugar de archivos completos.
- **Validación**: Antes de proponer un cambio en un callback, verifica los `id` en el layout para evitar errores de `ComponentID`.
- **Estilo**: Si el código es para un componente nuevo, usa el formato `html.Div([...])` de forma compacta.
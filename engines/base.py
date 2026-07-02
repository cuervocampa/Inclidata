"""Contrato abstracto para motores de generación de informes.

Para añadir un motor nuevo:
1. Crea ``engines/mi_motor.py`` con una clase que herede de ``BaseReportEngine``.
2. Implementa el método ``render()``.
3. Regístralo en el dict ``_ENGINES`` de ``utils/report_engine.py``.
"""

from abc import ABC, abstractmethod


class BaseReportEngine(ABC):
    """Motor de renderizado de informes.

    Contrato mínimo: implementar ``render()``.
    Los métodos ``render_from_state``, ``render_preview_png`` y
    ``render_preview_graficos`` son opcionales; lanzan ``NotImplementedError``
    por defecto.
    """

    def __init__(self, server=None) -> None:
        """Almacena el ORM ``Server`` asociado al informe (opcional).

        Args:
            server: Instancia del modelo ``Server`` de Maketator (puede ser
                    ``None`` cuando el motor se usa sin contexto de BD, por
                    ejemplo en previsualizaciones del editor visual).
        """
        self._server = server

    @abstractmethod
    def render(
        self,
        context: dict,
        nombre_plantilla: str,
        output_path: str,
    ) -> list:
        """Genera el informe y devuelve el log de ejecución.

        Args:
            context:          Diccionario de ejecución (zona, fechas, sensor, data…).
            nombre_plantilla: Nombre de la carpeta de plantilla en ``biblioteca_plantillas/``.
            output_path:      Ruta de salida del archivo generado.

        Returns:
            Lista de dicts con hitos de ejecución (``{"hito": str, "ts": str, …}``).
        """

    def render_from_state(
        self,
        context: dict,
        editor_state: dict,
        output_path: str,
    ) -> list:
        """Genera un informe efímero desde el estado en memoria del editor visual.

        Args:
            context:      Diccionario de ejecución.
            editor_state: Estado del editor (prop ``value`` / ``data`` del componente).
            output_path:  Ruta de salida.

        Returns:
            Lista de hitos de ejecución.
        """
        raise NotImplementedError(
            f"{type(self).__name__} no implementa render_from_state()"
        )

    def render_preview_png(
        self,
        context: dict,
        nombre_plantilla: str,
        width_px: int = 800,
    ) -> bytes:
        """Genera una vista previa PNG de la primera página del informe.

        Args:
            context:          Contexto de ejecución.
            nombre_plantilla: Nombre de la carpeta de plantilla.
            width_px:         Ancho aproximado de la imagen en píxeles.

        Returns:
            Bytes del PNG generado.
        """
        raise NotImplementedError(
            f"{type(self).__name__} no implementa render_preview_png()"
        )

    def render_preview_graficos(
        self,
        context: dict,
        nombre_plantilla: str,
    ) -> list[dict]:
        """Genera previsualizaciones de todos los gráficos de la plantilla.

        Args:
            context:          Contexto de ejecución.
            nombre_plantilla: Nombre de la carpeta de plantilla.

        Returns:
            Lista de dicts con claves ``index``, ``element_id``, ``script``,
            ``result`` (data URL o ``None``) y ``error`` (mensaje o ``None``).
        """
        raise NotImplementedError(
            f"{type(self).__name__} no implementa render_preview_graficos()"
        )

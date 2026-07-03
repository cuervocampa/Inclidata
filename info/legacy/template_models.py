"""
models/template_models.py
=========================
Modelos Pydantic v2 para el sistema de plantillas de Inclidata.

Representan fielmente la estructura de los JSON en disco
(biblioteca_plantillas/{nombre}/{nombre}.json) y aplican automáticamente
las mismas conversiones que hace `_convertir_elemento` en editor_visual.py:

  - Mapeo de nombres de estilo: color_relleno → backgroundColor, etc.
  - Normalización de opacidad: 0-100 → 0-1.
  - Normalización de geometría de tablas: ancho_maximo/alto_maximo → ancho/alto.

Convenciones de unidades:
  - Geometría (x, y, ancho, alto): SIEMPRE en cm (tanto en disco como en modelo).
  - Anchos de columna (Columna.ancho): cm en disco.
      Usar columnas_a_pct(ancho_total_cm) para obtener % para el editor.
      Usar columnas_a_cm(ancho_total_cm) para volver a cm al guardar.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TipoElemento(str, Enum):
    """Tipos de elemento soportados en una plantilla."""
    TEXTO = "texto"
    RECTANGULO = "rectangulo"
    LINEA = "linea"
    GRAFICO = "grafico"
    TABLA = "tabla"
    IMAGEN = "imagen"


class Orientacion(str, Enum):
    """Orientación de página para el PDF."""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


# ---------------------------------------------------------------------------
# Geometría
# ---------------------------------------------------------------------------

class Geometria(BaseModel):
    """Posición y tamaño del elemento. Todas las unidades en centímetros (cm)."""

    x: float = 0.0
    """Posición horizontal desde el borde izquierdo de la página (cm)."""

    y: float = 0.0
    """Posición vertical desde el borde superior de la página (cm)."""

    ancho: float = 10.0
    """Ancho del elemento (cm)."""

    alto: float = 5.0
    """Alto del elemento (cm)."""

    @model_validator(mode="before")
    @classmethod
    def normalizar_tablas(cls, data: Any) -> Any:
        """Compatibilidad con el formato antiguo: ancho_maximo/alto_maximo → ancho/alto."""
        if not isinstance(data, dict):
            return data
        if "ancho" not in data and "ancho_maximo" in data:
            data["ancho"] = data["ancho_maximo"]
        if "alto" not in data and "alto_maximo" in data:
            data["alto"] = data["alto_maximo"]
        return data


# ---------------------------------------------------------------------------
# Estilo
# ---------------------------------------------------------------------------

class Estilo(BaseModel):
    """
    Estilos visuales de un elemento.

    Acepta tanto el formato antiguo (editor_plantilla.py) como el nuevo
    (editor_visual.py / React). El validador `normalizar_nombres` hace el
    mismo mapeo que `_convertir_elemento` en editor_visual.py.

    Formato antiguo → Nuevo:
      color_relleno    → backgroundColor
      color_borde      → borderColor
      grosor_borde     → borderWidth
      opacidad (0-100) → opacity (0-1)
      familia_fuente   → fontFamily
      negrita          → fontWeight
      cursiva          → fontStyle
      alineacion_h     → textAlign
    """

    backgroundColor: str = "transparent"
    """Color de fondo. Defecto: 'transparent' (o '#e2e8f0' para rectángulos)."""

    borderColor: str = "#cbd5e1"
    """Color del borde."""

    borderWidth: float = 0.0
    """Grosor del borde en puntos."""

    opacity: float = 1.0
    """Opacidad (0.0–1.0)."""

    color: str = "#000000"
    """Color del texto."""

    tamano: float = 14.0
    """Tamaño de fuente en puntos."""

    fontFamily: str = "sans-serif"
    """Familia tipográfica."""

    fontWeight: str = "normal"
    """Peso de fuente: 'normal' o 'bold'."""

    fontStyle: str = "normal"
    """Estilo de fuente: 'normal' o 'italic'."""

    textAlign: str = "left"
    """Alineación horizontal del texto: 'left', 'center' o 'right'."""

    @model_validator(mode="before")
    @classmethod
    def normalizar_nombres(cls, data: Any) -> Any:
        """
        Mapea campos del formato antiguo al nuevo y normaliza la opacidad.
        Prioridad: nombre antiguo > nombre nuevo > valor por defecto del campo.
        """
        if not isinstance(data, dict):
            return data

        d = dict(data)

        # color_relleno → backgroundColor
        if "color_relleno" in d:
            d.setdefault("backgroundColor", d.pop("color_relleno"))

        # color_borde → borderColor
        if "color_borde" in d:
            d.setdefault("borderColor", d.pop("color_borde"))

        # grosor_borde → borderWidth
        if "grosor_borde" in d:
            d.setdefault("borderWidth", d.pop("grosor_borde"))

        # familia_fuente → fontFamily
        if "familia_fuente" in d:
            d.setdefault("fontFamily", d.pop("familia_fuente"))

        # negrita → fontWeight (puede venir como bool o string)
        if "negrita" in d:
            val = d.pop("negrita")
            if isinstance(val, bool):
                val = "bold" if val else "normal"
            d.setdefault("fontWeight", val)

        # cursiva → fontStyle (puede venir como bool o string)
        if "cursiva" in d:
            val = d.pop("cursiva")
            if isinstance(val, bool):
                val = "italic" if val else "normal"
            d.setdefault("fontStyle", val)

        # alineacion_h → textAlign
        if "alineacion_h" in d:
            d.setdefault("textAlign", d.pop("alineacion_h"))

        # opacidad (0-100) → opacity (0-1)
        raw = d.pop("opacidad", d.get("opacity"))
        if raw is not None:
            d["opacity"] = raw / 100.0 if raw > 1 else float(raw)

        return d


# ---------------------------------------------------------------------------
# Contenido
# ---------------------------------------------------------------------------

class Contenido(BaseModel):
    """Contenido renderizable del elemento (texto o imagen inline)."""

    texto: Optional[str] = None
    """Texto a mostrar (tipo='texto'). None para los demás tipos."""

    src: Optional[str] = None
    """
    Data URI base64 de la imagen durante la edición (tipo='imagen').
    SIEMPRE debe quedar a None en el JSON guardado en disco.
    El sistema usa imagen.asset_id como referencia persistente.
    """

    editable: bool = False
    """Si True, el texto se puede sobreescribir en el modal de generación PDF."""


# ---------------------------------------------------------------------------
# Metadatos del elemento
# ---------------------------------------------------------------------------

class Metadata(BaseModel):
    """Metadatos de renderizado y agrupación."""

    zIndex: int = 0
    """Orden de apilamiento (mayor = más arriba)."""

    visible: bool = True
    """Si False, el elemento no se renderiza en el PDF."""

    grupo: Optional[str] = None
    """Nombre del grupo al que pertenece el elemento."""


# ---------------------------------------------------------------------------
# Grupo visual (objeto de agrupación en formato disco)
# ---------------------------------------------------------------------------

class GrupoRef(BaseModel):
    """Referencia al grupo visual al que pertenece el elemento (formato disco)."""

    nombre: str
    color: str = "#cccccc"


# ---------------------------------------------------------------------------
# Imagen
# ---------------------------------------------------------------------------

class ImagenAsset(BaseModel):
    """Referencia y metadatos del asset de imagen."""

    formato: Optional[str] = None
    """Extensión/formato del archivo: 'png', 'jpg', 'svg', etc."""

    ruta_original: Optional[str] = None
    """Ruta original del archivo al importarlo por primera vez."""

    ruta_nueva: Optional[str] = None
    """
    Ruta relativa dentro de la carpeta de la plantilla, p. ej. 'assets/logo.png'.
    Se usa en tiempo de generación de PDF para localizar el archivo.
    """

    nombre_archivo: Optional[str] = None
    """Nombre de archivo base, ej. 'imagen 2.png'."""

    estado: Optional[str] = None
    """Estado del asset: 'guardada', 'pendiente', etc."""

    asset_id: Optional[str] = None
    """
    Identificador corto (primeros 8 chars del MD5) en el almacén centralizado
    biblioteca_plantillas/_assets/. Referencia primaria para resolver la imagen.
    """

    datos_temp: Optional[str] = None
    """
    Data URI temporal inyectada en tiempo de carga por el editor para que React
    pueda mostrar la imagen. NO se persiste en disco.
    """


# ---------------------------------------------------------------------------
# Cuadrícula de tablas
# ---------------------------------------------------------------------------

class FormatoColumna(BaseModel):
    """Estilo visual de una celda/columna en la cuadrícula."""

    fuente: Optional[str] = None
    tamano: Optional[float] = None
    color_texto: Optional[str] = None
    color_fondo: Optional[str] = None
    alineacion: Optional[str] = None
    negrita: Optional[bool] = None


class BordeConfig(BaseModel):
    """Configuración de un borde (superior, inferior, izquierdo, derecho)."""

    activo: bool = False
    grosor: float = 1.0
    color: str = "#000000"


class BordesColumna(BaseModel):
    """Bordes de una celda de la cuadrícula."""

    superior: Optional[BordeConfig] = None
    inferior: Optional[BordeConfig] = None
    izquierdo: Optional[BordeConfig] = None
    derecho: Optional[BordeConfig] = None


class Columna(BaseModel):
    """
    Definición de una columna dentro de un nivel de cuadrícula.

    El campo `ancho` está en **centímetros** cuando se lee del disco.
    Usar los helpers de `NivelCuadricula` para convertir a/desde %.
    """

    ancho: float
    """Ancho de la columna. En cm en disco; en % en el editor React."""

    titulo: Optional[str] = None
    """Título de cabecera (usado en tablas simples estilo `tabla_datos.py`)."""

    campo: Optional[str] = None
    """Nombre del campo de datos que alimenta esta columna."""

    contenido: Optional[str] = None
    """Expresión de contenido dinámico (puede incluir tokens $CURRENT)."""

    formato: Optional[FormatoColumna] = None
    """Estilo visual de la celda."""

    bordes: Optional[BordesColumna] = None
    """Configuración de bordes de la celda."""


class EstiloNivel(BaseModel):
    """Estilo aplicado a todas las filas de un nivel."""

    fuente: Optional[str] = None
    tamano: Optional[float] = None


class NivelCuadricula(BaseModel):
    """
    Un nivel (fila de cabecera o fila de datos) dentro de la cuadrícula.

    Métodos de conversión de unidades
    ----------------------------------
    columnas_a_pct(ancho_total_cm):
        Devuelve la lista de columnas con `ancho` convertido a % (0-100).
        Usar al enviar datos al editor React.

    columnas_a_cm(ancho_total_cm):
        Devuelve la lista de columnas con `ancho` convertido a cm.
        Usar al guardar en disco desde datos con % del editor React.
    """

    id: Optional[int] = None
    tipo: Optional[str] = None
    """'estatico' | 'dinamico' — indica si las filas son fijas o generadas."""

    num_columnas: Optional[int] = None
    alto_fila: Optional[float] = None
    """Alto de cada fila en cm."""

    estilo: Optional[EstiloNivel] = None
    columnas: list[Columna] = Field(default_factory=list)

    def columnas_a_pct(self, ancho_total_cm: float) -> list[Columna]:
        """
        Devuelve copias de las columnas con `ancho` convertido de cm a %,
        igual que hace `_convertir_elemento` en editor_visual.py.

        Args:
            ancho_total_cm: Ancho total del elemento tabla en cm.

        Returns:
            Lista de Columna con ancho en porcentaje (0-100).
        """
        n = len(self.columnas) or 1
        resultado = []
        for col in self.columnas:
            c = col.model_copy()
            if ancho_total_cm > 0:
                c.ancho = round((col.ancho / ancho_total_cm) * 100, 2)
            else:
                c.ancho = round(100 / n, 2)
            resultado.append(c)
        return resultado

    def columnas_a_cm(self, ancho_total_cm: float) -> list[Columna]:
        """
        Devuelve copias de las columnas con `ancho` convertido de % a cm,
        igual que hace `_convertir_anchos_pct_a_cm` en editor_visual.py.

        Args:
            ancho_total_cm: Ancho total del elemento tabla en cm.

        Returns:
            Lista de Columna con ancho en cm.
        """
        resultado = []
        for col in self.columnas:
            c = col.model_copy()
            c.ancho = round((col.ancho / 100.0) * ancho_total_cm, 2)
            resultado.append(c)
        return resultado


class Cuadricula(BaseModel):
    """Estructura de la cuadrícula de una tabla, compuesta por niveles."""

    niveles: list[NivelCuadricula] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Configuración de gráfico / tabla
# ---------------------------------------------------------------------------

class ConfiguracionElemento(BaseModel):
    """
    Configuración dinámica de un elemento de tipo 'grafico' o 'tabla'.
    Referencia el script Python que genera el contenido y sus parámetros.

    Los valores '$CURRENT' (o '$CURRENT_<campo>') se sustituyen en tiempo de
    generación por el valor actual de los controles de la UI.
    """

    script: str = ""
    """Nombre de archivo del script, ej. 'grafico_incli_0.py'."""

    formato: Optional[str] = "svg"
    """Formato de salida del gráfico: 'svg' | 'png'."""

    parametros: dict[str, Any] = Field(default_factory=dict)
    """
    Parámetros pasados al script. Pueden contener el token '$CURRENT'
    para indicar valores que provienen de la UI en tiempo de generación.
    """

    datos_ejecutados: Optional[dict] = Field(default=None, exclude=True)
    """
    Resultado pre-computado por report_engine (no se persiste en disco).
    Para tablas: dict con 'encabezados_nivel_1' y 'filas'.
    """


# ---------------------------------------------------------------------------
# Elemento (modelo unificado)
# ---------------------------------------------------------------------------

class Elemento(BaseModel):
    """
    Elemento de una plantilla. Cubre todos los tipos (texto, rectangulo,
    linea, grafico, tabla, imagen).

    El validador `normalizar_formato_antiguo` aplica al cargar desde disco
    el mismo mapeo que `_convertir_elemento` en editor_visual.py:
      - Rellena `id` desde la clave del diccionario si falta.
      - Normaliza `grupo` (objeto → metadata.grupo).
      - Aplica defaults por tipo a `estilo`.
      - Resuelve `geometria.ancho_maximo` / `geometria.alto_maximo`.

    Los anchos de columna de `cuadricula` se mantienen en cm (formato disco).
    Usar `NivelCuadricula.columnas_a_pct()` para obtener % al pasar al editor.
    """

    id: Optional[str] = None
    """ID del elemento. Coincide con la clave en el dict de elementos."""

    tipo: TipoElemento
    """Tipo de elemento."""

    geometria: Geometria = Field(default_factory=Geometria)
    estilo: Estilo = Field(default_factory=Estilo)
    contenido: Contenido = Field(default_factory=Contenido)
    metadata: Metadata = Field(default_factory=Metadata)

    # Campos opcionales según tipo
    grupo: Optional[GrupoRef] = None
    """Referencia al grupo (formato disco). En runtime se refleja en metadata.grupo."""

    imagen: Optional[ImagenAsset] = None
    """Datos del asset de imagen. Solo presente si tipo == 'imagen'."""

    configuracion: Optional[ConfiguracionElemento] = None
    """Script y parámetros dinámicos. Solo presente si tipo in ('grafico', 'tabla')."""

    cuadricula: Optional[Cuadricula] = None
    """Estructura de columnas de la tabla. Solo presente si tipo == 'tabla'."""

    @model_validator(mode="before")
    @classmethod
    def normalizar_formato_antiguo(cls, data: Any) -> Any:
        """
        Aplica el mismo mapeo que `_convertir_elemento` en editor_visual.py.

        1. Defaults de estilo por tipo.
        2. grupo (objeto) → metadata.grupo.
        3. contenido vacío → objeto vacío con texto/src None.
        """
        if not isinstance(data, dict):
            return data

        d = dict(data)
        tipo = d.get("tipo", "")

        # --- defaults de estilo según tipo ---
        estilo = dict(d.get("estilo") or {})
        if tipo == "rectangulo":
            estilo.setdefault("backgroundColor", "#e2e8f0")
            estilo.setdefault("borderWidth", 1)
        else:
            estilo.setdefault("backgroundColor", "transparent")
            estilo.setdefault("borderWidth", 0)
        d["estilo"] = estilo

        # --- normalizar grupo: objeto → metadata.grupo ---
        grupo_raw = d.get("grupo")
        if isinstance(grupo_raw, dict) and "nombre" in grupo_raw:
            meta = dict(d.get("metadata") or {})
            meta.setdefault("grupo", grupo_raw["nombre"])
            d["metadata"] = meta

        # --- contenido mínimo garantizado ---
        if not d.get("contenido"):
            d["contenido"] = {"texto": None, "src": None}

        return d

    def to_editor_dict(self) -> dict[str, Any]:
        """
        Serializa el elemento al formato que espera el componente React,
        convirtiendo anchos de columna de cm a %.

        Equivale a lo que devuelve `_convertir_elemento` en editor_visual.py.
        """
        data = self.model_dump(exclude_none=False)

        # Convertir anchos de columna cm → % si es tabla
        if self.tipo == TipoElemento.TABLA and self.cuadricula:
            ancho_cm = self.geometria.ancho
            niveles_pct = []
            for nivel in self.cuadricula.niveles:
                n_data = nivel.model_dump()
                n_data["columnas"] = [
                    c.model_dump() for c in nivel.columnas_a_pct(ancho_cm)
                ]
                niveles_pct.append(n_data)
            data["cuadricula"] = {"niveles": niveles_pct}

        return data

    def limpiar_base64(self) -> None:
        """
        Limpia los campos de datos binarios inline que NO deben persistirse en disco:
          - contenido.src → None
          - imagen.datos_temp → None

        Llamar antes de serializar a JSON para guardar en biblioteca_plantillas/.
        """
        self.contenido.src = None
        if self.imagen:
            self.imagen.datos_temp = None


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------

class ConfiguracionPagina(BaseModel):
    """Configuración de una página individual."""

    orientacion: Orientacion = Orientacion.PORTRAIT


class Pagina(BaseModel):
    """
    Una página de la plantilla.
    Contiene un diccionario de elementos indexado por su ID.
    """

    elementos: dict[str, Elemento] = Field(default_factory=dict)
    configuracion: ConfiguracionPagina = Field(default_factory=ConfiguracionPagina)

    @model_validator(mode="before")
    @classmethod
    def inyectar_ids_elementos(cls, data: Any) -> Any:
        """Inyecta el ID de clave a cada elemento hijo para que el modelo lo recoja."""
        if not isinstance(data, dict):
            return data
        elems = data.get("elementos") or {}
        for elem_id, elem in elems.items():
            if isinstance(elem, dict):
                elem.setdefault("id", elem_id)
        return data

    def to_editor_dict(self) -> dict[str, Any]:
        """Serializa la página con todos los elementos en formato editor React."""
        return {
            "elementos": {
                eid: elem.to_editor_dict()
                for eid, elem in self.elementos.items()
            },
            "configuracion": self.configuracion.model_dump(),
        }


# ---------------------------------------------------------------------------
# Configuración global de la plantilla
# ---------------------------------------------------------------------------

class ConfiguracionPlantilla(BaseModel):
    """Metadatos globales de la plantilla."""

    nombre_plantilla: str = "Nueva Plantilla"
    num_paginas: int = 1

    # Campos inyectados en tiempo de carga (no están en disco)
    chartScripts: list[str] = Field(default_factory=list, exclude=True)
    tableScripts: list[str] = Field(default_factory=list, exclude=True)


# ---------------------------------------------------------------------------
# Plantilla (raíz del JSON)
# ---------------------------------------------------------------------------

class Plantilla(BaseModel):
    """
    Raíz del JSON de una plantilla de Inclidata.

    Corresponde exactamente a la estructura de disco en
    biblioteca_plantillas/{nombre}/{nombre}.json.

    Uso típico
    ----------
    Cargar desde disco::

        with open(ruta_json) as f:
            plantilla = Plantilla.model_validate(json.load(f))

    Guardar a disco::

        plantilla.limpiar_base64()
        plantilla.convertir_anchos_a_cm()
        ruta_json.write_text(
            plantilla.model_dump_json(indent=2, exclude_none=False)
        )

    Enviar al editor React::

        payload = plantilla.to_editor_dict()
    """

    paginas: dict[str, Pagina] = Field(default_factory=dict)
    """Páginas indexadas por número de página como string: '1', '2', ..."""

    pagina_actual: str = "1"
    """ID de la página activa en el editor."""

    configuracion: ConfiguracionPlantilla = Field(
        default_factory=ConfiguracionPlantilla
    )

    # Campos de runtime inyectados por el editor (no en disco)
    chartScripts: list[str] = Field(default_factory=list, exclude=True)
    tableScripts: list[str] = Field(default_factory=list, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def normalizar_estructura_plana(cls, data: Any) -> Any:
        """
        Compatibilidad con plantillas antiguas sin capa `paginas`.
        Si el JSON tiene `elementos` en la raíz, lo envuelve en pagina '1'.
        """
        if not isinstance(data, dict):
            return data
        if "paginas" not in data and "elementos" in data:
            data = {
                "paginas": {
                    "1": {
                        "elementos": data["elementos"],
                        "configuracion": {"orientacion": "portrait"},
                    }
                },
                "pagina_actual": "1",
                "configuracion": data.get("configuracion", {}),
            }
        return data

    def to_editor_dict(self) -> dict[str, Any]:
        """
        Serializa la plantilla completa al formato que espera el componente React.
        Incluye conversión de anchos de columna cm → % en todos los elementos tabla.
        """
        return {
            "paginas": {
                pid: pagina.to_editor_dict()
                for pid, pagina in self.paginas.items()
            },
            "pagina_actual": self.pagina_actual,
            "configuracion": self.configuracion.model_dump(),
            "chartScripts": self.chartScripts,
            "tableScripts": self.tableScripts,
        }

    def limpiar_base64(self) -> None:
        """
        Limpia todos los campos de datos binarios inline (contenido.src,
        imagen.datos_temp) de todos los elementos de todas las páginas.
        Llamar antes de serializar a JSON para guardar en disco.
        """
        for pagina in self.paginas.values():
            for elem in pagina.elementos.values():
                elem.limpiar_base64()

    def convertir_anchos_a_cm(self) -> None:
        """
        Convierte anchos de columna de % (editor React) a cm (disco) en todos
        los elementos tabla. Equivale a `_convertir_anchos_pct_a_cm`.
        Llamar antes de serializar a JSON para guardar en disco.
        """
        for pagina in self.paginas.values():
            for elem in pagina.elementos.values():
                if elem.tipo != TipoElemento.TABLA or not elem.cuadricula:
                    continue
                ancho_cm = elem.geometria.ancho
                for nivel in elem.cuadricula.niveles:
                    nivel.columnas = nivel.columnas_a_cm(ancho_cm)

    def convertir_anchos_a_pct(self) -> None:
        """
        Convierte anchos de columna de cm (disco) a % (editor React) en todos
        los elementos tabla. Equivale a la parte de cuadrícula de `_convertir_elemento`.
        Llamar después de cargar desde disco antes de usar en el editor.
        """
        for pagina in self.paginas.values():
            for elem in pagina.elementos.values():
                if elem.tipo != TipoElemento.TABLA or not elem.cuadricula:
                    continue
                ancho_cm = elem.geometria.ancho
                for nivel in elem.cuadricula.niveles:
                    nivel.columnas = nivel.columnas_a_pct(ancho_cm)

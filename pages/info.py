# pages/info.py
"""
Página de inicio de IncliData con documentación a dos niveles:
- Usuario: Guía de uso del programa
- Desarrollador: Arquitectura técnica y librerías
"""

from dash import html, dcc
import dash_mantine_components as dmc
from dash_iconify import DashIconify


def layout():
    return dmc.Container([
        # Header principal
        dmc.Stack([
            dmc.Group([
                DashIconify(icon="mdi:chart-timeline-variant", width=48, color="#228be6"),
                dmc.Title("IncliData", order=1, c="#228be6"),
            ], gap="md", justify="center"),
            dmc.Text(
                "Sistema de gestión, análisis y visualización de datos de inclinometría",
                size="lg",
                c="dimmed",
                ta="center"
            ),
            dmc.Badge("v1.0 - Enero 2026", color="blue", variant="light", size="lg"),
        ], align="center", gap="xs", mt="xl", mb="xl"),

        dmc.Divider(my="lg"),

        # Sección de navegación rápida
        dmc.Title("🚀 Acceso Rápido", order=2, mb="md"),
        dmc.SimpleGrid(
            cols={"base": 1, "sm": 2, "md": 3},
            spacing="lg",
            children=[
                _crear_tarjeta_modulo(
                    "Importar Datos",
                    "Carga archivos RST, Sisgeo, Soil Dux o Excel",
                    "mdi:file-upload",
                    "/importar",
                    "#40c057"
                ),
                _crear_tarjeta_modulo(
                    "Graficar",
                    "Visualiza y genera informes PDF",
                    "mdi:chart-areaspline",
                    "/graficar",
                    "#228be6"
                ),
                _crear_tarjeta_modulo(
                    "Correcciones",
                    "Corrige bias y elimina spikes",
                    "mdi:tools",
                    "/correcciones",
                    "#fab005"
                ),
                _crear_tarjeta_modulo(
                    "Umbrales",
                    "Configura niveles de alerta",
                    "mdi:alert-circle",
                    "/importar_umbrales",
                    "#fa5252"
                ),
                _crear_tarjeta_modulo(
                    "Editor Plantillas",
                    "Diseña plantillas PDF personalizadas",
                    "mdi:file-document-edit",
                    "/editor_plantilla",
                    "#7950f2"
                ),
            ],
        ),

        dmc.Divider(my="xl"),

        # Sección de documentación
        dmc.Title("📚 Documentación", order=2, mb="md"),
        dmc.Text(
            "Selecciona el nivel de documentación según tu necesidad:",
            c="dimmed",
            mb="lg"
        ),

        dmc.SimpleGrid(
            cols={"base": 1, "md": 2},
            spacing="xl",
            children=[
                # Panel de Usuario
                _crear_panel_documentacion_usuario(),
                # Panel de Desarrollador
                _crear_panel_documentacion_desarrollador(),
            ],
        ),

        dmc.Divider(my="xl"),

        # Footer
        dmc.Group([
            dmc.Text("© 2026 IncliData", size="sm", c="dimmed"),
            dmc.Text("•", size="sm", c="dimmed"),
            dmc.Text("Desarrollado para gestión de inclinometría", size="sm", c="dimmed"),
        ], justify="center", mb="xl"),

    ], size="lg", py="xl")


def _crear_tarjeta_modulo(titulo, descripcion, icono, href, color):
    """Crea una tarjeta de navegación para un módulo."""
    return dmc.Anchor(
        dmc.Paper(
            dmc.Group([
                dmc.ThemeIcon(
                    DashIconify(icon=icono, width=24),
                    size="xl",
                    radius="md",
                    color=color,
                    variant="light",
                ),
                dmc.Stack([
                    dmc.Text(titulo, fw=600, size="md"),
                    dmc.Text(descripcion, size="sm", c="dimmed", lineClamp=2),
                ], gap=2),
            ], gap="md"),
            p="md",
            radius="md",
            withBorder=True,
            shadow="sm",
            style={"cursor": "pointer", "transition": "all 0.2s ease"},
            className="hover-card",
        ),
        href=href,
        underline=False,
    )


def _crear_panel_documentacion_usuario():
    """Panel de documentación para usuarios."""
    return dmc.Paper([
        dmc.Group([
            dmc.ThemeIcon(
                DashIconify(icon="mdi:account-circle", width=28),
                size="xl",
                radius="xl",
                color="teal",
                variant="gradient",
                gradient={"from": "teal", "to": "cyan", "deg": 45},
            ),
            dmc.Title("Guía de Usuario", order=3),
        ], gap="md", mb="md"),

        dmc.Text(
            "Aprende a utilizar IncliData para gestionar tus datos de inclinometría.",
            c="dimmed",
            size="sm",
            mb="lg"
        ),

        dmc.Accordion(
            chevronPosition="left",
            variant="contained",
            children=[
                dmc.AccordionItem([
                    dmc.AccordionControl(
                        dmc.Group([
                            DashIconify(icon="mdi:numeric-1-circle", width=20, color="#40c057"),
                            dmc.Text("Importar Datos", fw=500),
                        ], gap="sm"),
                    ),
                    dmc.AccordionPanel([
                        dmc.List([
                            dmc.ListItem("Accede a la página 'Importar' desde el menú lateral"),
                            dmc.ListItem("Selecciona el tipo de archivo (RST, Sisgeo, Soil Dux)"),
                            dmc.ListItem("Arrastra o selecciona los archivos a importar"),
                            dmc.ListItem("Revisa la previsualización y confirma"),
                        ], size="sm", spacing="xs"),
                    ]),
                ], value="importar"),

                dmc.AccordionItem([
                    dmc.AccordionControl(
                        dmc.Group([
                            DashIconify(icon="mdi:numeric-2-circle", width=20, color="#228be6"),
                            dmc.Text("Visualizar y Generar PDF", fw=500),
                        ], gap="sm"),
                    ),
                    dmc.AccordionPanel([
                        dmc.List([
                            dmc.ListItem("Ve a 'Graficar' para visualizar datos"),
                            dmc.ListItem("Selecciona el tubo inclinométrico"),
                            dmc.ListItem("Ajusta las fechas y campañas a mostrar"),
                            dmc.ListItem("Elige una plantilla y genera el PDF"),
                        ], size="sm", spacing="xs"),
                    ]),
                ], value="graficar"),

                dmc.AccordionItem([
                    dmc.AccordionControl(
                        dmc.Group([
                            DashIconify(icon="mdi:numeric-3-circle", width=20, color="#fab005"),
                            dmc.Text("Corregir Datos", fw=500),
                        ], gap="sm"),
                    ),
                    dmc.AccordionPanel([
                        dmc.List([
                            dmc.ListItem("Accede a 'Correcciones' para limpiar datos"),
                            dmc.ListItem("Utiliza la corrección de Bias para desplazamientos"),
                            dmc.ListItem("Elimina Spikes (picos anómalos) automáticamente"),
                            dmc.ListItem("Revisa los gráficos de violines para validar"),
                        ], size="sm", spacing="xs"),
                    ]),
                ], value="correcciones"),

                dmc.AccordionItem([
                    dmc.AccordionControl(
                        dmc.Group([
                            DashIconify(icon="mdi:numeric-4-circle", width=20, color="#fa5252"),
                            dmc.Text("Configurar Umbrales", fw=500),
                        ], gap="sm"),
                    ),
                    dmc.AccordionPanel([
                        dmc.List([
                            dmc.ListItem("Importa umbrales desde un archivo Excel"),
                            dmc.ListItem("Define niveles: Aviso, Alerta, Emergencia"),
                            dmc.ListItem("Los umbrales se mostrarán en los gráficos"),
                            dmc.ListItem("Usa colores personalizados para cada nivel"),
                        ], size="sm", spacing="xs"),
                    ]),
                ], value="umbrales"),

                dmc.AccordionItem([
                    dmc.AccordionControl(
                        dmc.Group([
                            DashIconify(icon="mdi:numeric-5-circle", width=20, color="#7950f2"),
                            dmc.Text("Crear Plantillas PDF", fw=500),
                        ], gap="sm"),
                    ),
                    dmc.AccordionPanel([
                        dmc.List([
                            dmc.ListItem("Usa el 'Editor de Plantillas' para diseñar"),
                            dmc.ListItem("Añade textos, imágenes, gráficos y tablas"),
                            dmc.ListItem("Configura posición y estilo de cada elemento"),
                            dmc.ListItem("Guarda como JSON para reutilizar"),
                        ], size="sm", spacing="xs"),
                    ]),
                ], value="plantillas"),
            ],
        ),

        dmc.Space(h="md"),

        dmc.Alert(
            "¿Necesitas más ayuda? Consulta los manuales PDF en la carpeta de documentación del proyecto.",
            title="Tip",
            icon=DashIconify(icon="mdi:lightbulb-on"),
            color="teal",
            variant="light",
        ),

    ], p="lg", radius="md", withBorder=True, shadow="sm")


def _crear_panel_documentacion_desarrollador():
    """Panel de documentación para desarrolladores."""
    return dmc.Paper([
        dmc.Group([
            dmc.ThemeIcon(
                DashIconify(icon="mdi:code-braces", width=28),
                size="xl",
                radius="xl",
                color="grape",
                variant="gradient",
                gradient={"from": "grape", "to": "violet", "deg": 45},
            ),
            dmc.Title("Documentación Técnica", order=3),
        ], gap="md", mb="md"),

        dmc.Text(
            "Arquitectura, librerías y estructura del código fuente.",
            c="dimmed",
            size="sm",
            mb="lg"
        ),

        # Tarjetas de documentación técnica
        dmc.Stack([
            _crear_tarjeta_doc(
                "📋 Estructura del Proyecto",
                "Organización de carpetas, módulos y archivos",
                "DOCUMENTACION_FINAL.md",
                "blue"
            ),
            _crear_tarjeta_doc(
                "🖨️ Sistema de Generación PDF",
                "Motor de renderizado, scripts de gráficos y tablas",
                "ANALISIS_GENERACION_PDF.md",
                "orange"
            ),
            _crear_tarjeta_doc(
                "🎨 Editor de Plantillas",
                "Arquitectura del editor visual WYSIWYG",
                "DOCUMENTACION_EDITOR_PLANTILLAS.md",
                "grape"
            ),
            _crear_tarjeta_doc(
                "📦 Librerías por Archivo",
                "Dependencias externas utilizadas en cada módulo",
                "LIBRERIAS_POR_ARCHIVO.md",
                "teal"
            ),
        ], gap="sm"),

        dmc.Space(h="md"),

        dmc.Divider(label="Tecnologías", labelPosition="center"),

        dmc.Space(h="md"),

        # Badges de tecnologías
        dmc.Group([
            dmc.Badge("Python 3.10+", color="blue", variant="light", leftSection=DashIconify(icon="mdi:language-python", width=14)),
            dmc.Badge("Dash 2.16+", color="indigo", variant="light", leftSection=DashIconify(icon="simple-icons:plotly", width=14)),
            dmc.Badge("Plotly", color="violet", variant="light", leftSection=DashIconify(icon="mdi:chart-line", width=14)),
            dmc.Badge("Matplotlib", color="cyan", variant="light", leftSection=DashIconify(icon="mdi:chart-areaspline", width=14)),
            dmc.Badge("ReportLab", color="red", variant="light", leftSection=DashIconify(icon="mdi:file-pdf-box", width=14)),
            dmc.Badge("Pandas", color="green", variant="light", leftSection=DashIconify(icon="mdi:table", width=14)),
        ], gap="xs", wrap="wrap"),

        dmc.Space(h="md"),

        dmc.Divider(label="Estructura", labelPosition="center"),

        dmc.Space(h="sm"),

        # Árbol de directorios simplificado
        dmc.Code(
            """IncliData/
├── app.py              # Entrada principal
├── pages/              # Módulos de la UI
├── utils/              # Funciones auxiliares
├── biblioteca_graficos/  # Scripts de gráficos
├── biblioteca_tablas/    # Scripts de tablas
├── biblioteca_grupos/    # Elementos reutilizables
├── biblioteca_plantillas/# Plantillas PDF
└── data/               # Datos JSON""",
            block=True,
            color="dark",
        ),

        dmc.Space(h="md"),

        dmc.Alert(
            "Los archivos .md de documentación están en la raíz del proyecto y pueden abrirse con cualquier visor de Markdown.",
            title="Nota",
            icon=DashIconify(icon="mdi:information"),
            color="grape",
            variant="light",
        ),

    ], p="lg", radius="md", withBorder=True, shadow="sm")


def _crear_tarjeta_doc(titulo, descripcion, archivo, color):
    """Crea una tarjeta pequeña de documentación."""
    return dmc.Paper(
        dmc.Group([
            dmc.Stack([
                dmc.Text(titulo, fw=600, size="sm"),
                dmc.Text(descripcion, size="xs", c="dimmed"),
            ], gap=2, style={"flex": 1}),
            dmc.Badge(archivo, color=color, variant="outline", size="sm"),
        ], justify="space-between", align="center"),
        p="sm",
        radius="sm",
        withBorder=True,
        style={"backgroundColor": "var(--mantine-color-gray-0)"},
    )

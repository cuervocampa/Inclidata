"""Stub de compatibilidad con engines/html_engine.py (trasplantado de Maketator, fase 3).
IncliData no tiene ORM: este módulo existe solo para satisfacer el import condicional
de render(). La rama de BD nunca se ejecuta porque context nunca lleva server_id.
"""


def get_session():
    raise RuntimeError(
        "get_session es un stub: IncliData no tiene ORM. "
        "Si ves este error, una plantilla está intentando abrir una sesión SQL, "
        "no soportado en IncliData."
    )

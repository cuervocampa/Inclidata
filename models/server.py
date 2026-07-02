"""Stub de compatibilidad con engines/html_engine.py (trasplantado de Maketator, fase 3).
IncliData no tiene ORM: este módulo existe solo para satisfacer el import condicional
de render(). La rama de BD nunca se ejecuta porque context nunca lleva server_id.
"""


class Server:
    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "Server es un stub: IncliData no tiene ORM. "
            "Si ves este error, una plantilla está intentando usar datos de servidor SQL, "
            "no soportados en IncliData."
        )

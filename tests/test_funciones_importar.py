"""
Tests para utils/funciones_importar.py

Cubre:
  - es_fecha_isoformat
  - parse_alarm_val
  - default_value
  - insertar_camp
"""
import json
import pytest

from utils.funciones_importar import (
    es_fecha_isoformat,
    parse_alarm_val,
    default_value,
    insertar_camp,
)
from tests.conftest import FECHA_REF, FECHA_1, FECHA_2


# ── es_fecha_isoformat ────────────────────────────────────────────────────────

class TestEsFechaIsoformat:

    @pytest.mark.parametrize("clave,esperado", [
        ("2023-01-01T10:30:00", True),
        ("2023-01-01T10:30",    True),
        ("2023-01-01",          True),
        ("info",                False),
        ("umbrales",            False),
        ("",                    False),
        ("2023/01/01",          False),
        ("01-01-2023",          False),
        ("2023-13-01T00:00:00", True),   # regex no valida rangos, solo formato
        ("abcd-ef-ghTij:kl:mn", False),  # no son dígitos
    ])
    def test_validacion(self, clave, esperado):
        assert es_fecha_isoformat(clave) == esperado

    def test_fechas_del_tubo(self):
        assert es_fecha_isoformat(FECHA_REF) is True
        assert es_fecha_isoformat(FECHA_1) is True

    def test_claves_especiales_false(self):
        for clave in ("info", "umbrales", "spike", "bias"):
            assert es_fecha_isoformat(clave) is False


# ── parse_alarm_val ───────────────────────────────────────────────────────────

class TestParseAlarmVal:

    def test_lista_con_nivel(self):
        raw = ['Supera umbral "Red_a", nivel: 12']
        assert parse_alarm_val(raw) == 12

    def test_string_con_nivel(self):
        assert parse_alarm_val('Supera umbral "X", nivel: 3') == 3

    def test_none_devuelve_none(self):
        assert parse_alarm_val(None) is None

    def test_lista_vacia_devuelve_none(self):
        assert parse_alarm_val([]) is None

    def test_string_sin_nivel_devuelve_none(self):
        assert parse_alarm_val("sin umbral") is None

    def test_lista_primer_elemento(self):
        """Solo usa el primer elemento de la lista."""
        raw = ['nivel: 7', 'nivel: 2']
        assert parse_alarm_val(raw) == 7

    def test_nivel_multidigito(self):
        assert parse_alarm_val("nivel: 100") == 100

    def test_tipo_int_devuelve_int(self):
        result = parse_alarm_val("nivel: 5")
        assert isinstance(result, int)


# ── default_value ─────────────────────────────────────────────────────────────

class TestDefaultValue:

    def test_sin_campanas_devuelve_defaults(self, tubo_sin_campanas):
        result = default_value(tubo_sin_campanas)
        assert result["latest_campaign"] is None
        assert result["latest_reference"] is None
        assert result["importador"] is None
        assert result["index_0"] is None

    def test_sin_campanas_lee_info(self, tubo_sin_campanas):
        result = default_value(tubo_sin_campanas)
        assert result["cota_1000"] == 5.0
        assert result["adquisicion"] == "automatica"
        assert result["disposicion"] == "horizontal"

    def test_con_campanas_detecta_ultima(self, tubo_basico):
        result = default_value(tubo_basico)
        # default_value toma la última entre campanas activas; FECHA_2 está inactiva
        assert result["latest_campaign"] == FECHA_1

    def test_con_campanas_detecta_importador(self, tubo_basico):
        result = default_value(tubo_basico)
        assert result["importador"] == "RST"

    def test_con_campanas_detecta_referencia(self, tubo_basico):
        result = default_value(tubo_basico)
        assert result["latest_reference"] == FECHA_REF

    def test_devuelve_dict_con_todas_las_claves(self, tubo_sin_campanas):
        result = default_value(tubo_sin_campanas)
        claves_esperadas = {
            "cota_1000", "adquisicion", "disposicion", "sentido_calculo",
            "umbrales", "latest_campaign", "latest_reference",
            "camp_anterior_referencia", "importador", "index_0",
        }
        assert claves_esperadas.issubset(result.keys())


# ── insertar_camp ─────────────────────────────────────────────────────────────

class TestInsertarCamp:

    def test_inserta_nueva_campana(self, tmp_json):
        tmp_path, filename = tmp_json
        nueva_fecha = "2024-03-01T08:00:00"
        nuevas_camps = {
            nueva_fecha: {
                "campaign_info": {
                    "index_0": 1000, "importador": "RST",
                    "active": True, "reference": False,
                    "quarentine": False, "alarm": None,
                },
                "calc": [],
                "raw": [],
            }
        }
        result = insertar_camp(nuevas_camps, [nueva_fecha], filename, str(tmp_path))
        assert result == "campañas añadidas"

        # Verificar que se guardó en disco
        saved = json.loads((tmp_path / filename).read_text())
        assert nueva_fecha in saved

    def test_devuelve_error_si_filename_vacio(self, tmp_path):
        """filename vacío provoca ValueError interno → 'Error'."""
        result = insertar_camp({}, [], "", str(tmp_path))
        assert result == "Error"

    def test_preserva_campanas_existentes(self, tmp_json):
        tmp_path, filename = tmp_json
        nueva_fecha = "2024-06-01T00:00:00"
        nuevas_camps = {
            nueva_fecha: {
                "campaign_info": {"index_0": 1000, "importador": "RST",
                                  "active": True, "reference": False,
                                  "quarentine": False, "alarm": None},
                "calc": [], "raw": [],
            }
        }
        insertar_camp(nuevas_camps, [nueva_fecha], filename, str(tmp_path))
        saved = json.loads((tmp_path / filename).read_text())
        # Las campañas originales siguen ahí
        assert FECHA_REF in saved
        assert FECHA_1 in saved

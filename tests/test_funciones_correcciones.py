"""
Tests para utils/funciones_correcciones.py

Cubre:
  - tabla_del_json
  - creacion_df_bias  (requiere pandas)
"""
import pytest
import pandas as pd

from utils.funciones_correcciones import tabla_del_json, creacion_df_bias
from tests.conftest import FECHA_REF, FECHA_1


# ── tabla_del_json ────────────────────────────────────────────────────────────

class TestTablaDelJson:

    @pytest.fixture
    def df_con_campanas(self, tubo_basico):
        return tubo_basico

    def test_devuelve_lista(self, df_con_campanas):
        result = tabla_del_json(df_con_campanas, [FECHA_REF, FECHA_1])
        assert isinstance(result, list)

    def test_longitud_igual_a_fechas(self, df_con_campanas):
        result = tabla_del_json(df_con_campanas, [FECHA_REF, FECHA_1])
        assert len(result) == 2

    def test_claves_en_cada_fila(self, df_con_campanas):
        result = tabla_del_json(df_con_campanas, [FECHA_REF])
        row = result[0]
        assert "Fecha" in row
        assert "Referencia" in row
        assert "Activa" in row
        assert "Cuarentena" in row
        assert "spike" in row
        assert "bias" in row
        assert "Limpiar" in row

    def test_fecha_correcta(self, df_con_campanas):
        result = tabla_del_json(df_con_campanas, [FECHA_REF])
        assert result[0]["Fecha"] == FECHA_REF

    def test_referencia_correcta(self, df_con_campanas):
        result = tabla_del_json(df_con_campanas, [FECHA_REF, FECHA_1])
        ref_row    = next(r for r in result if r["Fecha"] == FECHA_REF)
        normal_row = next(r for r in result if r["Fecha"] == FECHA_1)
        assert ref_row["Referencia"] is True
        assert normal_row["Referencia"] is False

    def test_spike_false_si_no_hay_correccion(self, df_con_campanas):
        result = tabla_del_json(df_con_campanas, [FECHA_REF])
        assert result[0]["spike"] is False

    def test_spike_true_si_hay_correccion(self, tubo_basico):
        tubo_basico[FECHA_REF]["spike"] = {"depth": 1.0}
        result = tabla_del_json(tubo_basico, [FECHA_REF])
        assert result[0]["spike"] is True

    def test_bias_true_si_hay_correccion(self, tubo_basico):
        tubo_basico[FECHA_1]["bias"] = True
        result = tabla_del_json(tubo_basico, [FECHA_1])
        assert result[0]["bias"] is True

    def test_limpiar_siempre_false_por_defecto(self, df_con_campanas):
        result = tabla_del_json(df_con_campanas, [FECHA_REF, FECHA_1])
        assert all(r["Limpiar"] is False for r in result)

    def test_lista_vacia_de_fechas(self, df_con_campanas):
        result = tabla_del_json(df_con_campanas, [])
        assert result == []


# ── creacion_df_bias ──────────────────────────────────────────────────────────

class TestCreacionDfBias:

    @pytest.fixture
    def calc_ref(self):
        return [
            {"index": 1000, "cota_abs": -0.5, "depth": 0.5,
             "dev_a": 10.0, "dev_b": 5.0, "checksum_a": 0.0, "checksum_b": 0.0,
             "desp_a": 0.0, "desp_b": 0.0},
            {"index": 1001, "cota_abs": -1.0, "depth": 1.0,
             "dev_a": 8.0,  "dev_b": 4.0, "checksum_a": 0.0, "checksum_b": 0.0,
             "desp_a": 0.0, "desp_b": 0.0},
        ]

    @pytest.fixture
    def calc_corr(self):
        return [
            {"index": 1000, "cota_abs": -0.5, "depth": 0.5,
             "dev_a": 12.0, "dev_b": 7.0, "checksum_a": 0.1, "checksum_b": 0.1,
             "desp_a": 2.0, "desp_b": 2.0},
            {"index": 1001, "cota_abs": -1.0, "depth": 1.0,
             "dev_a": 9.0,  "dev_b": 5.0, "checksum_a": 0.1, "checksum_b": 0.1,
             "desp_a": 1.0, "desp_b": 1.0},
        ]

    def test_devuelve_dataframe(self, calc_ref, calc_corr):
        result = creacion_df_bias(calc_ref, calc_corr)
        assert isinstance(result, pd.DataFrame)

    def test_longitud_correcta(self, calc_ref, calc_corr):
        result = creacion_df_bias(calc_ref, calc_corr)
        assert len(result) == 2

    def test_columnas_incremento_presentes(self, calc_ref, calc_corr):
        result = creacion_df_bias(calc_ref, calc_corr)
        assert "incr_dev_a" in result.columns
        assert "incr_dev_b" in result.columns

    def test_columnas_desplazamiento_presentes(self, calc_ref, calc_corr):
        result = creacion_df_bias(calc_ref, calc_corr)
        assert "desp_a" in result.columns
        assert "desp_b" in result.columns

    def test_incr_dev_a_correcto(self, calc_ref, calc_corr):
        """incr_dev_a = dev_a_corr - dev_a_ref"""
        result = creacion_df_bias(calc_ref, calc_corr)
        expected_row0 = round(12.0 - 10.0, 2)
        assert result["incr_dev_a"].iloc[0] == pytest.approx(expected_row0, abs=0.01)

"""
Tests para utils/funciones_comunes.py

Cubre:
  - valores_calc_directos
  - extraer_fechas_activas
  - buscar_referencia
  - buscar_ant_referencia
  - obtener_fecha_activa_anterior
  - get_color_for_index
  - evaluar_umbrales
  - asignar_colores
  - calcular_incrementos
"""
import copy
import pytest
from utils.funciones_comunes import (
    valores_calc_directos,
    extraer_fechas_activas,
    buscar_referencia,
    buscar_ant_referencia,
    obtener_fecha_activa_anterior,
    get_color_for_index,
    evaluar_umbrales,
    asignar_colores,
    calcular_incrementos,
)

from tests.conftest import FECHA_REF, FECHA_1, FECHA_2


# ── valores_calc_directos ─────────────────────────────────────────────────────

class TestValoresCalcDirectos:

    def test_devuelve_dict_con_claves_esperadas(self):
        result = valores_calc_directos(1000, -0.5, 0.5, 0.01, -0.01, 0.005, -0.005, 1000)
        claves = {"index", "cota_abs", "depth", "a0", "a180", "b0", "b180",
                  "checksum_a", "checksum_b", "dev_a", "dev_b"}
        assert claves.issubset(result.keys())

    def test_preserva_index_cota_depth(self):
        result = valores_calc_directos(1234, -2.5, 3.0, 0.01, -0.01, 0.005, -0.005, 1000)
        assert result["index"] == 1234
        assert result["cota_abs"] == -2.5
        assert result["depth"] == 3.0

    def test_checksum_simetrico_es_cero(self):
        """Con a0 = -a180 y b0 = -b180 el checksum debe ser 0."""
        result = valores_calc_directos(1000, 0.0, 0.5, 0.01, -0.01, 0.02, -0.02, 1000)
        assert result["checksum_a"] == 0.0
        assert result["checksum_b"] == 0.0

    def test_dev_a_formula(self):
        """dev_a = round((a0*cte - a180*cte) / 2, 2)"""
        a0, a180, cte = 0.016, -0.015, 1000
        result = valores_calc_directos(1000, 0.0, 0.5, a0, a180, 0.0, 0.0, cte)
        a0c = round(a0 * cte, 2)
        a180c = round(a180 * cte, 2)
        expected = round((a0c - a180c) / 2, 2)
        assert result["dev_a"] == expected

    def test_checksum_asimetrico(self):
        """checksum_a = round(a0*cte + a180*cte, 4)"""
        a0, a180, cte = 0.016, -0.015, 1000
        result = valores_calc_directos(1000, 0.0, 0.5, a0, a180, 0.0, 0.0, cte)
        expected = round(round(a0 * cte, 2) + round(a180 * cte, 2), 4)
        assert result["checksum_a"] == expected

    def test_cte_1_no_multiplica(self):
        """Con cte=1 los valores no cambian (ya vienen en mm)."""
        result = valores_calc_directos(1000, 0.0, 0.5, 10.0, -10.0, 5.0, -5.0, 1)
        assert result["a0"] == 10.0
        assert result["dev_a"] == 10.0


# ── extraer_fechas_activas ────────────────────────────────────────────────────

class TestExtraerFechasActivas:

    def test_devuelve_solo_activas(self, tubo_basico):
        fechas = extraer_fechas_activas(tubo_basico)
        assert FECHA_REF in fechas
        assert FECHA_1 in fechas
        assert FECHA_2 not in fechas   # inactiva

    def test_ignora_info_y_umbrales(self, tubo_basico):
        fechas = extraer_fechas_activas(tubo_basico)
        assert "info" not in fechas
        assert "umbrales" not in fechas

    def test_orden_ascendente(self, tubo_basico):
        fechas = extraer_fechas_activas(tubo_basico)
        assert fechas == sorted(fechas)

    def test_tubo_sin_campanas(self, tubo_sin_campanas):
        fechas = extraer_fechas_activas(tubo_sin_campanas)
        assert fechas == []

    def test_todas_inactivas(self):
        data = {
            "2023-01-01T00:00:00": {"campaign_info": {"active": False}},
            "2023-06-01T00:00:00": {"campaign_info": {"active": False}},
        }
        assert extraer_fechas_activas(data) == []


# ── buscar_referencia ─────────────────────────────────────────────────────────

class TestBuscarReferencia:

    def test_encuentra_referencia_exacta(self, tubo_basico):
        ref = buscar_referencia(tubo_basico, FECHA_REF)
        assert ref == FECHA_REF

    def test_encuentra_referencia_anterior(self, tubo_basico):
        ref = buscar_referencia(tubo_basico, FECHA_1)
        assert ref == FECHA_REF

    def test_no_hay_referencia_anterior(self, tubo_basico):
        """Fecha anterior a todas las referencias → None."""
        ref = buscar_referencia(tubo_basico, "2022-01-01T00:00:00")
        assert ref is None

    def test_ultima_referencia_de_varias(self):
        """Con dos referencias elige la más reciente que no supere fecha_calc."""
        data = {
            "info": {},
            "2023-01-01T00:00:00": {"campaign_info": {"reference": True,  "active": True}},
            "2023-06-01T00:00:00": {"campaign_info": {"reference": True,  "active": True}},
            "2023-12-01T00:00:00": {"campaign_info": {"reference": False, "active": True}},
        }
        ref = buscar_referencia(data, "2023-12-01T00:00:00")
        assert ref == "2023-06-01T00:00:00"


# ── buscar_ant_referencia ─────────────────────────────────────────────────────

class TestBuscarAntReferencia:

    def test_no_hay_campanas_anteriores(self, tubo_ref_only):
        # Solo existe la referencia, no hay campaña anterior
        # Nota: buscar_ant_referencia no filtra 'umbrales', se pasan solo las claves de campaña
        data = {
            "info": {},
            FECHA_REF: {"campaign_info": {"active": True, "reference": True}},
        }
        result = buscar_ant_referencia(data, FECHA_REF)
        assert result is None

    def test_encuentra_campana_anterior_activa(self):
        data = {
            "info": {},
            "2023-01-01T00:00:00": {"campaign_info": {"active": True,  "reference": False}},
            "2023-06-01T00:00:00": {"campaign_info": {"active": True,  "reference": True}},
        }
        result = buscar_ant_referencia(data, "2023-06-01T00:00:00")
        assert result == "2023-01-01T00:00:00"


# ── obtener_fecha_activa_anterior ─────────────────────────────────────────────

class TestObtenerFechaActivaAnterior:

    def test_devuelve_campana_anterior(self, tubo_basico):
        result = obtener_fecha_activa_anterior(tubo_basico, FECHA_1)
        assert result == tubo_basico[FECHA_REF]

    def test_devuelve_vacio_si_no_hay_anterior(self, tubo_basico):
        result = obtener_fecha_activa_anterior(tubo_basico, FECHA_REF)
        assert result == {}

    def test_devuelve_vacio_sin_campanas_activas(self, tubo_sin_campanas):
        result = obtener_fecha_activa_anterior(tubo_sin_campanas, "2023-01-01T00:00:00")
        assert result == {}


# ── get_color_for_index ───────────────────────────────────────────────────────

class TestGetColorForIndex:

    def test_monocromo_devuelve_hex(self):
        color = get_color_for_index(0, "monocromo", 5)
        assert isinstance(color, str)
        assert color.startswith("#")
        assert len(color) == 7

    def test_multicromo_devuelve_hex(self):
        color = get_color_for_index(0, "multicromo")
        assert isinstance(color, str)
        assert color.startswith("#")

    def test_multicromo_rota_paleta(self):
        """Índices que superen la paleta deben rotar."""
        import plotly.colors as pcolors
        n = len(pcolors.qualitative.Plotly)
        assert get_color_for_index(0) == get_color_for_index(n)

    def test_esquema_invalido_lanza_error(self):
        with pytest.raises(ValueError):
            get_color_for_index(0, "invalido")

    def test_monocromo_total_1_no_error(self):
        """total_colors=1 no debe causar división por cero."""
        color = get_color_for_index(0, "monocromo", total_colors=1)
        assert color.startswith("#")


# ── evaluar_umbrales ──────────────────────────────────────────────────────────

class TestEvaluarUmbrales:

    @pytest.fixture
    def umbrales_simple(self):
        return {
            "deformadas": {
                "Red_a": {"flanco": "flanco_positivo", "nivel": 2},
                "Yel_a": {"flanco": "flanco_positivo", "nivel": 1},
            },
            "valores": [
                {"cota_abs": -0.5, "Red_a": 5.0, "Yel_a": 3.0},
                {"cota_abs": -1.0, "Red_a": 10.0, "Yel_a": 6.0},
            ],
        }

    def test_sin_superacion_devuelve_none(self, umbrales_simple):
        calc = [
            {"cota_abs": -0.5, "desp_a": 2.0, "desp_b": 0.0},
            {"cota_abs": -1.0, "desp_a": 4.0, "desp_b": 0.0},
        ]
        assert evaluar_umbrales(calc, umbrales_simple) is None

    def test_supera_umbral_devuelve_string(self, umbrales_simple):
        calc = [{"cota_abs": -0.5, "desp_a": 6.0, "desp_b": 0.0}]
        result = evaluar_umbrales(calc, umbrales_simple)
        assert result is not None
        assert isinstance(result, str)
        assert "nivel" in result

    def test_selecciona_nivel_mayor(self, umbrales_simple):
        """Si supera dos umbrales, devuelve el de mayor nivel."""
        calc = [{"cota_abs": -0.5, "desp_a": 6.0, "desp_b": 0.0}]
        result = evaluar_umbrales(calc, umbrales_simple)
        assert "Red_a" in result   # nivel 2, mayor que Yel_a (nivel 1)

    def test_umbrales_vacios_devuelve_none(self):
        calc = [{"cota_abs": -0.5, "desp_a": 999.0, "desp_b": 0.0}]
        umbrales = {"deformadas": {}, "valores": []}
        assert evaluar_umbrales(calc, umbrales) is None

    def test_flanco_negativo(self):
        umbrales = {
            "deformadas": {"Neg_b": {"flanco": "flanco_negativo", "nivel": 1}},
            "valores": [{"cota_abs": -0.5, "Neg_b": -3.0}],
        }
        # desp_b = -5.0 < -3.0 → supera flanco negativo
        calc = [{"cota_abs": -0.5, "desp_a": 0.0, "desp_b": -5.0}]
        result = evaluar_umbrales(calc, umbrales)
        assert result is not None
        assert "Neg_b" in result

    def test_sin_flanco_ignorado(self):
        """Curvas con sin_flanco se ignoran."""
        umbrales = {
            "deformadas": {"X_a": {"flanco": "sin_flanco", "nivel": 3}},
            "valores": [{"cota_abs": -0.5, "X_a": 0.0}],
        }
        calc = [{"cota_abs": -0.5, "desp_a": 999.0, "desp_b": 0.0}]
        assert evaluar_umbrales(calc, umbrales) is None


# ── asignar_colores ───────────────────────────────────────────────────────────

class TestAsignarColores:

    COLORES = ["verde", "naranja", "rojo", "azul", "gris"]

    def test_primeros_tres_a_son_fijos(self):
        umbrales = ["Lev1_a", "Lev2_a", "Lev3_a"]
        result = asignar_colores(umbrales, self.COLORES)
        assert result["Lev1_a"] == "verde"
        assert result["Lev2_a"] == "naranja"
        assert result["Lev3_a"] == "rojo"

    def test_primeros_tres_b_son_fijos(self):
        umbrales = ["Lev1_b", "Lev2_b", "Lev3_b"]
        result = asignar_colores(umbrales, self.COLORES)
        assert result["Lev1_b"] == "verde"
        assert result["Lev2_b"] == "naranja"
        assert result["Lev3_b"] == "rojo"

    def test_lista_vacia_devuelve_dict_vacio(self):
        result = asignar_colores([], self.COLORES)
        assert result == {}

    def test_none_devuelve_dict_vacio(self):
        result = asignar_colores(None, self.COLORES)
        assert result == {}

    def test_todas_las_claves_presentes(self):
        umbrales = ["A_a", "B_a", "A_b"]
        result = asignar_colores(umbrales, self.COLORES)
        assert set(result.keys()) == {"A_a", "B_a", "A_b"}


# ── calcular_incrementos ──────────────────────────────────────────────────────

class TestCalcularIncrementos:

    def test_referencia_no_tiene_incrementos(self, tubo_basico):
        tubo = copy.deepcopy(tubo_basico)
        calcular_incrementos(tubo, FECHA_REF, FECHA_REF)
        entrada = tubo[FECHA_REF]["calc"][0]
        assert entrada["incr_dev_a"] == 0
        assert entrada["incr_dev_b"] == 0

    def test_referencia_tiene_abs_dev(self, tubo_basico):
        """abs_dev_a = suma de dev_a desde esa profundidad al fondo."""
        tubo = copy.deepcopy(tubo_basico)
        calcular_incrementos(tubo, FECHA_REF, FECHA_REF)
        dev_a = tubo[FECHA_REF]["calc"][0]["dev_a"]
        abs_dev_a = tubo[FECHA_REF]["calc"][0]["abs_dev_a"]
        assert abs_dev_a == dev_a  # un solo nivel → abs = dev

    def test_campana_normal_incr_correcto(self, tubo_basico):
        tubo = copy.deepcopy(tubo_basico)
        calcular_incrementos(tubo, FECHA_REF, FECHA_REF)
        calcular_incrementos(tubo, FECHA_1, FECHA_REF)
        dev_ref  = tubo[FECHA_REF]["calc"][0]["dev_a"]
        dev_calc = tubo[FECHA_1]["calc"][0]["dev_a"]
        incr     = tubo[FECHA_1]["calc"][0]["incr_dev_a"]
        assert incr == round(dev_calc - dev_ref, 2)

    def test_devuelve_data_mutado(self, tubo_basico):
        tubo = copy.deepcopy(tubo_basico)
        result = calcular_incrementos(tubo, FECHA_REF, FECHA_REF)
        assert result is tubo  # modifica in-place y devuelve el mismo dict

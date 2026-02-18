"""
Fixtures compartidas para todos los tests de Inclidata.
"""
import copy
import json
import pytest

# ── Fechas de referencia ──────────────────────────────────────────────────────
FECHA_REF = "2023-01-01T00:00:00"
FECHA_1   = "2023-06-01T00:00:00"
FECHA_2   = "2023-12-01T00:00:00"


def _calc_entry(index=1000, cota_abs=-0.5, depth=0.5,
                dev_a=10.0, dev_b=5.0,
                checksum_a=0.0, checksum_b=0.0):
    """Entrada mínima válida para el array 'calc' de una campaña."""
    return {
        "index": index,
        "cota_abs": cota_abs,
        "depth": depth,
        "dev_a": dev_a,
        "dev_b": dev_b,
        "checksum_a": checksum_a,
        "checksum_b": checksum_b,
        "incr_dev_a": 0.0,
        "incr_dev_b": 0.0,
        "desp_a": 0.0,
        "desp_b": 0.0,
        "abs_dev_a": 0.0,
        "abs_dev_b": 0.0,
    }


def _raw_entry(index=1000, cota_abs=-0.5, depth=0.5,
               a0=0.01, a180=-0.01, b0=0.005, b180=-0.005):
    return {
        "index": index, "cota_abs": cota_abs, "depth": depth,
        "a0": a0, "a180": a180, "b0": b0, "b180": b180,
    }


def _campaign(ref=True, active=True, quarentine=False,
              importador="RST", index_0=1000,
              dev_a=10.0, dev_b=5.0):
    return {
        "campaign_info": {
            "index_0": index_0,
            "importador": importador,
            "instrument_constant": 1000,
            "active": active,
            "reference": ref,
            "quarentine": quarentine,
            "alarm": None,
        },
        "info_readout": {
            "probe_serial": "23790000,Cal Date,04/22/2020",
            "reel_serial": "32500000",
            "interval": 0.5,
        },
        "raw": [_raw_entry()],
        "calc": [_calc_entry(dev_a=dev_a, dev_b=dev_b)],
    }


# ── Tubo con referencia + 2 campañas normales ─────────────────────────────────
_TUBO_BASE = {
    "info": {
        "nom_sensor": "TEST-01",
        "cota_1000": 0.0,
        "adquisicion": "manual",
        "disposicion": "vertical",
        "sentido_calculo": "abajo-arriba",
    },
    "umbrales": {"deformadas": {}, "valores": []},
    FECHA_REF: _campaign(ref=True,  active=True,  dev_a=10.0, dev_b=5.0),
    FECHA_1:   _campaign(ref=False, active=True,  dev_a=12.0, dev_b=7.0),
    FECHA_2:   _campaign(ref=False, active=False, dev_a=14.0, dev_b=9.0),
}


@pytest.fixture
def tubo_basico():
    """Tubo con referencia + campaña activa + campaña inactiva."""
    return copy.deepcopy(_TUBO_BASE)


@pytest.fixture
def tubo_ref_only():
    """Tubo con sólo la campaña de referencia."""
    return copy.deepcopy({
        "info": _TUBO_BASE["info"],
        "umbrales": _TUBO_BASE["umbrales"],
        FECHA_REF: _campaign(ref=True, active=True),
    })


@pytest.fixture
def tubo_sin_campanas():
    """Tubo vacío (sólo info y umbrales)."""
    return {
        "info": {
            "nom_sensor": "EMPTY",
            "cota_1000": 5.0,
            "adquisicion": "automatica",
            "disposicion": "horizontal",
            "sentido_calculo": "arriba-abajo",
        },
        "umbrales": {"deformadas": {}, "valores": []},
    }


@pytest.fixture
def tmp_json(tmp_path):
    """Archivo JSON temporal con estructura mínima de tubo."""
    data = copy.deepcopy(_TUBO_BASE)
    filepath = tmp_path / "test_tubo.json"
    filepath.write_text(json.dumps(data, indent=4))
    return tmp_path, "test_tubo.json"

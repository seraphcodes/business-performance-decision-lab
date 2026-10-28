"""The JavaScript simulator must give the same numbers as src/scenario.py.

Runs web/js/scenario.js with Node on many price/volume/cost combinations and compares
with the tested Python functions. Skipped if Node is not installed.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from src.scenario import baseline, breakeven_volume_pct, scenario

ROOT = Path(__file__).resolve().parent.parent
node = shutil.which("node")
pytestmark = pytest.mark.skipif(node is None, reason="Node.js not installed")

BASE = {"gross": 1000.0, "cancellations": -50.0, "net": 950.0, "cancellation_rate": 0.05}
MONTHLY = [
    {"year_month": "2011-01", "is_partial_month": 0, "gross_product_sales": 100.0, "cancellation_value": -10.0},
    {"year_month": "2011-02", "is_partial_month": 0, "gross_product_sales": 200.0, "cancellation_value": -20.0},
    {"year_month": "2011-03", "is_partial_month": 0, "gross_product_sales": 300.0, "cancellation_value": -30.0},
    {"year_month": "2011-04", "is_partial_month": 1, "gross_product_sales": 9999.0, "cancellation_value": -999.0},
]


def test_js_matches_python_on_a_grid(tmp_path):
    cases = [{"base": BASE, "price": p, "volume": v, "cost": c, "monthly": MONTHLY}
             for p in (-30, -10, -5, 0, 5, 10, 30) for v in (-50, -20, 0, 7, 50) for c in (10, 40, 60, 90)]
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(cases))
    result = subprocess.run([node, str(ROOT / "tests" / "js_scenario_check.js"), str(path)],
                            capture_output=True, text=True, check=True)
    got = json.loads(result.stdout)
    for case, js in zip(cases, got["out"]):
        py = scenario(case["base"], case["price"], case["volume"], case["cost"])
        for key in ("net", "cost", "profit", "profit_change"):
            assert js[key] == pytest.approx(py[key], abs=1e-9), (case, key)
        expected = breakeven_volume_pct(case["price"], case["cost"])
        if expected is None:
            assert js["breakeven"] is None
        else:
            assert js["breakeven"] == pytest.approx(expected, abs=1e-9)
    py_base = baseline(pd.DataFrame(MONTHLY), months=2)
    for key in ("gross", "cancellations", "net", "cancellation_rate"):
        assert got["baseline"][key] == pytest.approx(py_base[key])
    assert got["baseline"]["first_month"] == "2011-02" and got["baseline"]["months"] == 2

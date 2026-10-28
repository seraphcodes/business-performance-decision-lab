"""Hand-calculated tests for src/scenario.py."""
import pandas as pd
import pytest

from src.scenario import baseline, breakeven_volume_pct, scenario, sensitivity

BASE = {"gross": 1000.0, "cancellations": -50.0, "net": 950.0, "cancellation_rate": 0.05}


def test_baseline_uses_last_full_months_only():
    monthly = pd.DataFrame({
        "year_month": ["2011-01", "2011-02", "2011-03", "2011-04"],
        "is_partial_month": [0, 0, 0, 1],
        "gross_product_sales": [100.0, 200.0, 300.0, 9999.0],
        "cancellation_value": [-10.0, -20.0, -30.0, -999.0],
    })
    base = baseline(monthly, months=2)
    assert base["gross"] == 500.0 and base["cancellations"] == -50.0 and base["net"] == 450.0
    assert base["cancellation_rate"] == pytest.approx(0.10)
    assert (base["first_month"], base["last_month"], base["months"]) == ("2011-02", "2011-03", 2)


def test_baseline_without_full_months_is_an_error():
    monthly = pd.DataFrame({"year_month": ["2011-12"], "is_partial_month": [1],
                            "gross_product_sales": [1.0], "cancellation_value": [0.0]})
    with pytest.raises(ValueError):
        baseline(monthly)


def test_no_change_means_no_change():
    result = scenario(BASE, 0, 0, 60)
    assert result["net"] == pytest.approx(950.0)
    assert result["net_change"] == pytest.approx(0.0)
    assert result["profit_change"] == pytest.approx(0.0)


def test_price_up_ten_percent_volume_down_five_percent():
    # gross 1000*1.1*0.95 = 1045 ; net 1045*0.95 = 992.75 ; cost 0.6*950*0.95 = 541.5
    # profit 451.25 ; baseline profit 950*0.4 = 380 ; change +71.25
    result = scenario(BASE, 10, -5, 60)
    assert result["gross"] == pytest.approx(1045.0)
    assert result["net"] == pytest.approx(992.75)
    assert result["cost"] == pytest.approx(541.5)
    assert result["profit"] == pytest.approx(451.25)
    assert result["base_profit"] == pytest.approx(380.0)
    assert result["profit_change"] == pytest.approx(71.25)
    assert result["net_change"] == pytest.approx(42.75)


def test_breakeven_price_up_ten_cost_sixty_is_minus_twenty_percent():
    assert breakeven_volume_pct(10, 60) == pytest.approx(-20.0)
    # and the scenario really does leave profit unchanged at that volume
    assert scenario(BASE, 10, -20, 60)["profit_change"] == pytest.approx(0.0)


def test_breakeven_price_down_ten_needs_a_third_more_volume():
    assert breakeven_volume_pct(-10, 60) == pytest.approx(100 / 3)
    assert scenario(BASE, -10, 100 / 3, 60)["profit_change"] == pytest.approx(0.0)


def test_breakeven_impossible_when_price_falls_to_cost():
    assert breakeven_volume_pct(-40, 60) is None   # new margin = 0
    assert breakeven_volume_pct(-50, 60) is None   # new margin < 0


def test_sensitivity_grid_matches_single_scenarios():
    grid = sensitivity(BASE, [-10, 0, 10], [-5, 0, 5], 60)
    assert grid.shape == (3, 3)
    assert grid.loc[10, -5] == pytest.approx(71.25)
    assert grid.loc[0, 0] == pytest.approx(0.0)
    assert grid.loc[-10, 5] == pytest.approx(scenario(BASE, -10, 5, 60)["profit_change"])

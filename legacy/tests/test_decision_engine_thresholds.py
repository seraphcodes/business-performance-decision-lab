from modules.decision_engine import (
    demand_score,
    profit_score,
    payback_score,
    financing_score,
    current_ratio_score,
    quick_ratio_score,
    recommendation,
)


def test_threshold_behavior_is_unchanged():
    assert demand_score(6000) == 100
    assert demand_score(3000) == 80
    assert demand_score(1500) == 60
    assert demand_score(500) == 40

    assert profit_score(60000) == 100
    assert profit_score(25000) == 80
    assert profit_score(12000) == 60
    assert profit_score(5000) == 40

    assert payback_score(2) == 100
    assert payback_score(4) == 80
    assert payback_score(6) == 60
    assert payback_score(10) == 40

    assert financing_score(30) == 100
    assert financing_score(55) == 80
    assert financing_score(80) == 50

    assert current_ratio_score(2.5) == 100
    assert current_ratio_score(1.7) == 80
    assert current_ratio_score(1.1) == 60
    assert current_ratio_score(0.8) == 30

    assert quick_ratio_score(1.5) == 100
    assert quick_ratio_score(0.9) == 80
    assert quick_ratio_score(0.7) == 60
    assert quick_ratio_score(0.3) == 30

    assert recommendation(90) == "Proceed"
    assert recommendation(78) == "Proceed with Caution"
    assert recommendation(60) == "Needs Further Analysis"
    assert recommendation(45) == "Do Not Proceed"

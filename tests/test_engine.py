import pytest
from src.engine import run_simulation, TierResult, Bottleneck
from src.loader import Tier, GameData


def test_run_simulation_returns_one_result_per_tier(simple_game_data):
    results = run_simulation(simple_game_data)
    assert len(results) == 1
    assert results[0].tier_name == "Automation Science"


def test_simulated_hours_equals_target_when_under_budget(simple_game_data):
    # budget is 50 (early), we have a small chain — should be under budget
    results = run_simulation(simple_game_data)
    r = results[0]
    if r.total_machines <= 50:
        assert r.simulated_hours == pytest.approx(r.target_hours)


def test_simulated_hours_exceeds_target_when_over_budget(simple_recipes, simple_config):
    # Use a tiny machine budget to force over-budget
    from dataclasses import replace
    from src.loader import GameData
    tight_config = replace(simple_config, machine_budget={"nauvis": {"early": 1, "mid": 1, "late": 1}})
    tier = Tier(
        name="Automation Science",
        target_hours=3.0,
        science_packs={"automation-science-pack": 100},
        unlocks=[],
    )
    data = GameData(recipes=simple_recipes, tiers=[tier], config=tight_config)
    results = run_simulation(data)
    r = results[0]
    assert r.simulated_hours > r.target_hours


def test_machine_counts_are_positive_integers(simple_game_data):
    results = run_simulation(simple_game_data)
    for recipe_name, count in results[0].machine_counts.items():
        assert isinstance(count, int)
        assert count > 0


def test_target_hours_falls_back_to_default_when_none(simple_recipes, simple_config):
    from src.loader import GameData
    tier = Tier(
        name="Late Tier",
        target_hours=None,
        science_packs={"automation-science-pack": 100},
        unlocks=[],
    )
    # Tier index 0 → 'early' stage → default 3.0 hours
    data = GameData(recipes=simple_recipes, tiers=[tier], config=simple_config)
    results = run_simulation(data)
    assert results[0].target_hours == pytest.approx(3.0)


def test_bottleneck_detected_when_delta_exceeds_threshold(simple_recipes, simple_config):
    from dataclasses import replace
    from src.loader import GameData
    # Low threshold so any delta triggers a bottleneck
    sensitive_config = replace(simple_config, bottleneck_threshold=1)
    tier1 = Tier("Tier 1", 3.0, {"automation-science-pack": 10}, [])
    tier2 = Tier("Tier 2", 8.0, {"automation-science-pack": 1_000_000}, [])
    data = GameData(recipes=simple_recipes, tiers=[tier1, tier2], config=sensitive_config)
    results = run_simulation(data)
    # Tier 2 should have bottlenecks since machine counts jump significantly
    assert len(results[1].bottlenecks) > 0


def test_no_bottleneck_on_first_tier(simple_game_data):
    results = run_simulation(simple_game_data)
    # First tier has no previous tier to delta against — no bottlenecks
    assert results[0].bottlenecks == []

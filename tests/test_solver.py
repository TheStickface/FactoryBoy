# tests/test_solver.py
import pytest
from src.graph import RecipeGraph
from src.solver import solve


def test_solve_single_item_at_root(simple_recipes, simple_config):
    graph = RecipeGraph.build(simple_recipes)
    # Asking for water — the root input — should just record it and stop
    result = solve("water", 1.0, graph, simple_config)
    assert result.rates["water"] == pytest.approx(1.0)
    assert len(result.rates) == 1


def test_solve_linear_chain(simple_recipes, simple_config):
    # iron-plate requires iron-ore (1:1), iron-ore requires water (10:1)
    graph = RecipeGraph.build(simple_recipes)
    result = solve("iron-plate", 1.0, graph, simple_config)
    assert "iron-plate" in result.rates
    assert "iron-ore" in result.rates
    assert "water" in result.rates
    assert result.rates["iron-plate"] == pytest.approx(1.0)
    # iron-ore: 1.0 units/s of iron-plate * (1 ore / 1 plate) = 1.0 ore/s
    assert result.rates["iron-ore"] == pytest.approx(1.0)
    # water: 1.0 ore/s * (10 water / 1 ore) = 10.0 water/s
    assert result.rates["water"] == pytest.approx(10.0)


def test_solve_branching_recipe(simple_recipes, simple_config):
    # automation-science-pack needs iron-plate(1) + copper-plate(1)
    # each plate chain goes back to water separately
    graph = RecipeGraph.build(simple_recipes)
    result = solve("automation-science-pack", 1.0, graph, simple_config)
    assert result.rates["iron-plate"] == pytest.approx(1.0)
    assert result.rates["copper-plate"] == pytest.approx(1.0)
    # Both chains need water: 10 + 10 = 20
    assert result.rates["water"] == pytest.approx(20.0)


def test_solve_accumulates_shared_ingredients():
    # Two products share the same intermediate — demands should sum
    from src.loader import Recipe, Config
    recipes = {
        "a": Recipe("a", {"root": 1.0}, {"a": 1.0}, 1.0, "assembler-1"),
        "b": Recipe("b", {"root": 1.0}, {"b": 1.0}, 1.0, "assembler-1"),
        "ab": Recipe("ab", {"a": 1.0, "b": 1.0}, {"ab": 1.0}, 1.0, "assembler-1"),
    }
    config = Config(
        root_input="root", root_input_rate=1000.0,
        machine_speeds={"assembler-1": 0.5},
        bottleneck_threshold=20,
        machine_budget={"early": 50, "mid": 200, "late": 800},
        default_target_hours={"early": 3.0, "mid": 9.0, "late": 20.0},
        report_output="reports/latest.html",
    )
    graph = RecipeGraph.build(recipes)
    result = solve("ab", 1.0, graph, config)
    # Both a and b need 1 root/s each -> root demand = 2.0
    assert result.rates["root"] == pytest.approx(2.0)


def test_solve_handles_cycle_without_infinite_loop():
    from src.loader import Recipe, Config
    # a needs b, b needs a — pathological cycle
    recipes = {
        "a": Recipe("a", {"b": 1.0}, {"a": 1.0}, 1.0, "assembler-1"),
        "b": Recipe("b", {"a": 1.0}, {"b": 1.0}, 1.0, "assembler-1"),
    }
    config = Config(
        root_input="root", root_input_rate=1000.0,
        machine_speeds={"assembler-1": 0.5},
        bottleneck_threshold=20,
        machine_budget={"early": 50, "mid": 200, "late": 800},
        default_target_hours={"early": 3.0, "mid": 9.0, "late": 20.0},
        report_output="reports/latest.html",
    )
    graph = RecipeGraph.build(recipes)
    # Must terminate without recursion error
    result = solve("a", 1.0, graph, config)
    assert "a" in result.rates

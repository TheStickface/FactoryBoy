# tests/conftest.py
import pytest
from src.loader import Recipe, Tier, Config, GameData


@pytest.fixture
def simple_recipes():
    return {
        "iron-ore": Recipe(
            name="iron-ore",
            ingredients={"water": 10.0},
            products={"iron-ore": 1.0},
            crafting_time=10.0,
            machine="chemical-plant",
            surface="nauvis",
        ),
        "copper-ore": Recipe(
            name="copper-ore",
            ingredients={"water": 10.0},
            products={"copper-ore": 1.0},
            crafting_time=10.0,
            machine="chemical-plant",
            surface="nauvis",
        ),
        "iron-plate": Recipe(
            name="iron-plate",
            ingredients={"iron-ore": 1.0},
            products={"iron-plate": 1.0},
            crafting_time=3.2,
            machine="stone-furnace",
            surface="nauvis",
        ),
        "copper-plate": Recipe(
            name="copper-plate",
            ingredients={"copper-ore": 1.0},
            products={"copper-plate": 1.0},
            crafting_time=3.2,
            machine="stone-furnace",
            surface="nauvis",
        ),
        "automation-science-pack": Recipe(
            name="automation-science-pack",
            ingredients={"iron-plate": 1.0, "copper-plate": 1.0},
            products={"automation-science-pack": 1.0},
            crafting_time=5.0,
            machine="assembler-1",
            surface="nauvis",
        ),
    }


@pytest.fixture
def simple_config():
    return Config(
        root_input="water",
        root_input_rate=1000.0,
        machine_speeds={"assembler-1": 0.5, "stone-furnace": 1.0, "chemical-plant": 1.0},
        bottleneck_threshold=20,
        machine_budget={"nauvis": {"early": 50, "mid": 200, "late": 800}},
        spoilage_multiplier=1.0,
        perishable_items=[],
        default_target_hours={"early": 3.0, "mid": 9.0, "late": 20.0},
        report_output="reports/latest.html",
    )


@pytest.fixture
def simple_tier():
    return Tier(
        name="Automation Science",
        target_hours=3.0,
        science_packs={"automation-science-pack": 100},
        unlocks=["iron-plate", "copper-plate"],
    )


@pytest.fixture
def simple_game_data(simple_recipes, simple_config, simple_tier):
    return GameData(
        recipes=simple_recipes,
        tiers=[simple_tier],
        config=simple_config,
    )
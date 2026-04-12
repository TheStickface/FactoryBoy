# FactoryBoy Simulation Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool that simulates Seablock-style Factorio modpack progression, generates interactive HTML reports showing tier pacing and production bottlenecks, and supports side-by-side comparison of two data configurations.

**Architecture:** A demand-driven simulation engine reads human-editable YAML data files (recipes, tech tree, config), walks the recipe dependency graph backwards from each science tier's required science pack rate, computes machine counts and achievability against a configurable budget, then renders a self-contained HTML report using Plotly. Two commands: `run` for a single simulation, `compare` for a diff of two data directories.

**Tech Stack:** Python 3.11+, PyYAML, Plotly, pytest

---

## File Structure

```
C:/Dev/Factorio/FactoryBoy/
├── factoryboy.py                  # CLI entry point (run + compare commands)
├── requirements.txt
├── data/                          # Default data directory
│   ├── recipes.yaml
│   ├── tech_tree.yaml
│   └── config.yaml
├── src/
│   ├── __init__.py
│   ├── loader.py                  # Dataclasses + YAML parsing + validation
│   ├── graph.py                   # RecipeGraph: item → recipe lookup
│   ├── solver.py                  # Demand solver: backward throughput traversal
│   ├── engine.py                  # Orchestrates solver, machine counts, achievability, bottlenecks
│   └── reporter.py                # HTML report generation (run + compare modes)
├── tests/
│   ├── conftest.py                # Shared pytest fixtures
│   ├── test_loader.py
│   ├── test_graph.py
│   ├── test_solver.py
│   ├── test_engine.py
│   └── test_reporter.py
└── reports/                       # Generated HTML output (gitignored)
```

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `reports/.gitkeep`
- Create: `.gitignore`

- [ ] **Step 1: Create requirements.txt**

```
pyyaml>=6.0
plotly>=5.18
pytest>=8.0
```

- [ ] **Step 2: Create src/__init__.py and tests/__init__.py**

Both files are empty. Create them so Python treats these as packages:

```python
# src/__init__.py
# (empty)
```

```python
# tests/__init__.py
# (empty)
```

- [ ] **Step 3: Create .gitignore**

```
reports/*.html
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 4: Create reports/.gitkeep**

Empty file. Ensures the `reports/` directory is tracked by git but generated HTML is ignored.

- [ ] **Step 5: Install dependencies**

Run: `pip install -r requirements.txt`

Expected: packages install without error.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt src/__init__.py tests/__init__.py .gitignore reports/.gitkeep
git commit -m "chore: project setup with dependencies and directory structure"
```

---

## Task 2: Data Loader

**Files:**
- Create: `src/loader.py`
- Create: `tests/conftest.py`
- Create: `tests/test_loader.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_loader.py
import pytest
from pathlib import Path
from src.loader import load_data, Recipe, Tier, Config, GameData

def test_load_config_fields(tmp_path):
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text("""
root_input: water
root_input_rate: 1000
machine_speeds:
  assembler-1: 0.5
  stone-furnace: 1.0
bottleneck_threshold: 20
machine_budget:
  early: 50
  mid: 200
  late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
    recipes_yaml = tmp_path / "recipes.yaml"
    recipes_yaml.write_text("recipes: {}")
    tech_tree_yaml = tmp_path / "tech_tree.yaml"
    tech_tree_yaml.write_text("tiers: []")

    data = load_data(str(tmp_path))
    assert data.config.root_input == "water"
    assert data.config.root_input_rate == 1000.0
    assert data.config.machine_speeds["assembler-1"] == 0.5
    assert data.config.machine_budget["early"] == 50
    assert data.config.default_target_hours["mid"] == 9.0
    assert data.config.bottleneck_threshold == 20

def test_load_recipes(tmp_path):
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text("""
root_input: water
root_input_rate: 1000
machine_speeds:
  assembler-1: 0.5
bottleneck_threshold: 20
machine_budget:
  early: 50
  mid: 200
  late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
    recipes_yaml = tmp_path / "recipes.yaml"
    recipes_yaml.write_text("""
recipes:
  iron-plate:
    ingredients:
      iron-ore: 1
    products:
      iron-plate: 1
    crafting_time: 3.2
    machine: stone-furnace
""")
    tech_tree_yaml = tmp_path / "tech_tree.yaml"
    tech_tree_yaml.write_text("tiers: []")

    data = load_data(str(tmp_path))
    assert "iron-plate" in data.recipes
    r = data.recipes["iron-plate"]
    assert r.ingredients == {"iron-ore": 1.0}
    assert r.products == {"iron-plate": 1.0}
    assert r.crafting_time == 3.2
    assert r.machine == "stone-furnace"

def test_load_tech_tree(tmp_path):
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text("""
root_input: water
root_input_rate: 1000
machine_speeds: {}
bottleneck_threshold: 20
machine_budget:
  early: 50
  mid: 200
  late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
    recipes_yaml = tmp_path / "recipes.yaml"
    recipes_yaml.write_text("recipes: {}")
    tech_tree_yaml = tmp_path / "tech_tree.yaml"
    tech_tree_yaml.write_text("""
tiers:
  - name: Automation Science
    target_hours: 3
    science_packs:
      automation-science-pack: 100
    unlocks:
      - iron-plate
""")

    data = load_data(str(tmp_path))
    assert len(data.tiers) == 1
    t = data.tiers[0]
    assert t.name == "Automation Science"
    assert t.target_hours == 3.0
    assert t.science_packs == {"automation-science-pack": 100}
    assert t.unlocks == ["iron-plate"]

def test_tier_without_target_hours(tmp_path):
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text("""
root_input: water
root_input_rate: 1000
machine_speeds: {}
bottleneck_threshold: 20
machine_budget:
  early: 50
  mid: 200
  late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
    recipes_yaml = tmp_path / "recipes.yaml"
    recipes_yaml.write_text("recipes: {}")
    tech_tree_yaml = tmp_path / "tech_tree.yaml"
    tech_tree_yaml.write_text("""
tiers:
  - name: Late Tier
    science_packs:
      science-pack: 500
""")

    data = load_data(str(tmp_path))
    assert data.tiers[0].target_hours is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_loader.py -v`

Expected: `ModuleNotFoundError` or `ImportError` — `src.loader` does not exist yet.

- [ ] **Step 3: Implement src/loader.py**

```python
# src/loader.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class Recipe:
    name: str
    ingredients: dict[str, float]
    products: dict[str, float]
    crafting_time: float
    machine: str


@dataclass
class Tier:
    name: str
    target_hours: Optional[float]
    science_packs: dict[str, int]
    unlocks: list[str]


@dataclass
class Config:
    root_input: str
    root_input_rate: float
    machine_speeds: dict[str, float]
    bottleneck_threshold: int
    machine_budget: dict[str, int]
    default_target_hours: dict[str, float]
    report_output: str


@dataclass
class GameData:
    recipes: dict[str, Recipe]
    tiers: list[Tier]
    config: Config


def load_data(data_dir: str) -> GameData:
    path = Path(data_dir)
    config = _load_config(path / "config.yaml")
    recipes = _load_recipes(path / "recipes.yaml")
    tiers = _load_tech_tree(path / "tech_tree.yaml")
    return GameData(recipes=recipes, tiers=tiers, config=config)


def _load_config(path: Path) -> Config:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Config(
        root_input=raw["root_input"],
        root_input_rate=float(raw["root_input_rate"]),
        machine_speeds={k: float(v) for k, v in raw["machine_speeds"].items()},
        bottleneck_threshold=int(raw["bottleneck_threshold"]),
        machine_budget={k: int(v) for k, v in raw["machine_budget"].items()},
        default_target_hours={k: float(v) for k, v in raw["default_target_hours"].items()},
        report_output=raw["report_output"],
    )


def _load_recipes(path: Path) -> dict[str, Recipe]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    recipes = {}
    for name, data in (raw.get("recipes") or {}).items():
        recipes[name] = Recipe(
            name=name,
            ingredients={k: float(v) for k, v in data["ingredients"].items()},
            products={k: float(v) for k, v in data["products"].items()},
            crafting_time=float(data["crafting_time"]),
            machine=data["machine"],
        )
    return recipes


def _load_tech_tree(path: Path) -> list[Tier]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    tiers = []
    for data in (raw.get("tiers") or []):
        tiers.append(Tier(
            name=data["name"],
            target_hours=data.get("target_hours"),
            science_packs={k: int(v) for k, v in data["science_packs"].items()},
            unlocks=data.get("unlocks", []),
        ))
    return tiers
```

- [ ] **Step 4: Create tests/conftest.py with shared fixtures**

```python
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
        ),
        "copper-ore": Recipe(
            name="copper-ore",
            ingredients={"water": 10.0},
            products={"copper-ore": 1.0},
            crafting_time=10.0,
            machine="chemical-plant",
        ),
        "iron-plate": Recipe(
            name="iron-plate",
            ingredients={"iron-ore": 1.0},
            products={"iron-plate": 1.0},
            crafting_time=3.2,
            machine="stone-furnace",
        ),
        "copper-plate": Recipe(
            name="copper-plate",
            ingredients={"copper-ore": 1.0},
            products={"copper-plate": 1.0},
            crafting_time=3.2,
            machine="stone-furnace",
        ),
        "automation-science-pack": Recipe(
            name="automation-science-pack",
            ingredients={"iron-plate": 1.0, "copper-plate": 1.0},
            products={"automation-science-pack": 1.0},
            crafting_time=5.0,
            machine="assembler-1",
        ),
    }


@pytest.fixture
def simple_config():
    return Config(
        root_input="water",
        root_input_rate=1000.0,
        machine_speeds={"assembler-1": 0.5, "stone-furnace": 1.0, "chemical-plant": 1.0},
        bottleneck_threshold=20,
        machine_budget={"early": 50, "mid": 200, "late": 800},
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_loader.py -v`

Expected: 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/loader.py tests/conftest.py tests/test_loader.py src/__init__.py tests/__init__.py
git commit -m "feat: data loader with YAML parsing and dataclasses"
```

---

## Task 3: Recipe Graph

**Files:**
- Create: `src/graph.py`
- Create: `tests/test_graph.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_graph.py
import pytest
from src.graph import RecipeGraph


def test_recipe_for_returns_recipe(simple_recipes):
    graph = RecipeGraph.build(simple_recipes)
    r = graph.recipe_for("iron-plate")
    assert r is not None
    assert r.name == "iron-plate"


def test_recipe_for_returns_none_for_unknown(simple_recipes):
    graph = RecipeGraph.build(simple_recipes)
    assert graph.recipe_for("does-not-exist") is None


def test_recipe_for_root_input_returns_none(simple_recipes):
    # water has no recipe in simple_recipes
    graph = RecipeGraph.build(simple_recipes)
    assert graph.recipe_for("water") is None


def test_all_products_indexed(simple_recipes):
    graph = RecipeGraph.build(simple_recipes)
    for recipe in simple_recipes.values():
        for product in recipe.products:
            assert graph.recipe_for(product) is not None


def test_last_recipe_wins_for_duplicate_product(simple_recipes):
    from src.loader import Recipe
    extra = Recipe(
        name="iron-plate-alt",
        ingredients={"scrap": 2.0},
        products={"iron-plate": 1.0},
        crafting_time=1.0,
        machine="assembler-1",
    )
    recipes = {**simple_recipes, "iron-plate-alt": extra}
    graph = RecipeGraph.build(recipes)
    # Should not raise; one recipe wins
    assert graph.recipe_for("iron-plate") is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_graph.py -v`

Expected: `ModuleNotFoundError` — `src.graph` does not exist yet.

- [ ] **Step 3: Implement src/graph.py**

```python
# src/graph.py
from __future__ import annotations
from dataclasses import dataclass, field
from src.loader import Recipe


@dataclass
class RecipeGraph:
    recipes: dict[str, Recipe]
    _item_to_recipe: dict[str, Recipe] = field(default_factory=dict, repr=False)

    @classmethod
    def build(cls, recipes: dict[str, Recipe]) -> RecipeGraph:
        item_to_recipe: dict[str, Recipe] = {}
        for recipe in recipes.values():
            for product in recipe.products:
                item_to_recipe[product] = recipe
        instance = cls(recipes=recipes)
        instance._item_to_recipe = item_to_recipe
        return instance

    def recipe_for(self, item: str) -> Recipe | None:
        return self._item_to_recipe.get(item)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_graph.py -v`

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/graph.py tests/test_graph.py
git commit -m "feat: recipe dependency graph with item-to-recipe lookup"
```

---

## Task 4: Demand Solver

**Files:**
- Create: `src/solver.py`
- Create: `tests/test_solver.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_solver.py
import pytest
from src.graph import RecipeGraph
from src.solver import solve


def test_solve_single_item_at_root(simple_recipes, simple_config):
    graph = RecipeGraph.build(simple_recipes)
    # Asking for water — the root input — should just record it
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
    # Both a and b need 1 root/s each → root demand = 2.0
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
    # Should terminate without recursion error
    result = solve("a", 1.0, graph, config)
    assert "a" in result.rates
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_solver.py -v`

Expected: `ModuleNotFoundError` — `src.solver` does not exist yet.

- [ ] **Step 3: Implement src/solver.py**

```python
# src/solver.py
from __future__ import annotations
from dataclasses import dataclass, field
from src.loader import Config
from src.graph import RecipeGraph


@dataclass
class ThroughputMap:
    rates: dict[str, float] = field(default_factory=dict)

    def add(self, item: str, rate: float) -> None:
        self.rates[item] = self.rates.get(item, 0.0) + rate


def solve(item: str, rate: float, graph: RecipeGraph, config: Config) -> ThroughputMap:
    """Compute throughput (units/second) required for every item in the chain to produce
    `rate` units/second of `item`. Traces back to config.root_input."""
    result = ThroughputMap()
    _recurse(item, rate, graph, config.root_input, result, frozenset())
    return result


def _recurse(
    item: str,
    rate: float,
    graph: RecipeGraph,
    root_input: str,
    result: ThroughputMap,
    visited: frozenset,
) -> None:
    result.add(item, rate)

    if item == root_input or item in visited:
        return

    recipe = graph.recipe_for(item)
    if recipe is None:
        return

    output_qty = recipe.products[item]
    new_visited = visited | {item}

    for ingredient, qty in recipe.ingredients.items():
        ingredient_rate = rate * (qty / output_qty)
        _recurse(ingredient, ingredient_rate, graph, root_input, result, new_visited)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_solver.py -v`

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/solver.py tests/test_solver.py
git commit -m "feat: demand solver with backward throughput traversal and cycle detection"
```

---

## Task 5: Simulation Engine

**Files:**
- Create: `src/engine.py`
- Create: `tests/test_engine.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_engine.py
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
    tight_config = replace(simple_config, machine_budget={"early": 1, "mid": 1, "late": 1})
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
    tier2 = Tier("Tier 2", 8.0, {"automation-science-pack": 500}, [])
    data = GameData(recipes=simple_recipes, tiers=[tier1, tier2], config=sensitive_config)
    results = run_simulation(data)
    # Tier 2 should have bottlenecks since machine counts jump significantly
    assert len(results[1].bottlenecks) > 0


def test_no_bottleneck_on_first_tier(simple_game_data):
    results = run_simulation(simple_game_data)
    # First tier has no previous tier to delta against — no bottlenecks
    assert results[0].bottlenecks == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine.py -v`

Expected: `ModuleNotFoundError` — `src.engine` does not exist yet.

- [ ] **Step 3: Implement src/engine.py**

```python
# src/engine.py
from __future__ import annotations
import math
from dataclasses import dataclass, field
from src.loader import GameData, Tier, Config
from src.graph import RecipeGraph
from src.solver import solve, ThroughputMap


@dataclass
class Bottleneck:
    recipe_name: str
    machines_required: int
    delta: int


@dataclass
class TierResult:
    tier_name: str
    target_hours: float
    simulated_hours: float
    total_machines: int
    machine_counts: dict[str, int]
    bottlenecks: list[Bottleneck]


def run_simulation(data: GameData) -> list[TierResult]:
    graph = RecipeGraph.build(data.recipes)
    results: list[TierResult] = []
    prev_counts: dict[str, int] = {}

    for i, tier in enumerate(data.tiers):
        target_hours = _resolve_target_hours(tier, i, data.config)
        stage = _get_stage(i)

        combined = ThroughputMap()
        for pack_name, total_count in tier.science_packs.items():
            rate = total_count / (target_hours * 3600.0)
            pack_map = solve(pack_name, rate, graph, data.config)
            for item, item_rate in pack_map.rates.items():
                combined.add(item, item_rate)

        machine_counts = _compute_machine_counts(combined, graph, data.config)
        total_machines = sum(machine_counts.values())
        simulated_hours = _compute_simulated_hours(target_hours, total_machines, stage, data.config)
        bottlenecks = _detect_bottlenecks(machine_counts, prev_counts, data.config.bottleneck_threshold)

        results.append(TierResult(
            tier_name=tier.name,
            target_hours=target_hours,
            simulated_hours=simulated_hours,
            total_machines=total_machines,
            machine_counts=machine_counts,
            bottlenecks=bottlenecks,
        ))
        prev_counts = machine_counts

    return results


def _get_stage(tier_index: int) -> str:
    if tier_index <= 1:
        return "early"
    elif tier_index <= 4:
        return "mid"
    return "late"


def _resolve_target_hours(tier: Tier, tier_index: int, config: Config) -> float:
    if tier.target_hours is not None:
        return float(tier.target_hours)
    stage = _get_stage(tier_index)
    return config.default_target_hours[stage]


def _compute_machine_counts(throughput: ThroughputMap, graph: RecipeGraph, config: Config) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item, rate in throughput.rates.items():
        recipe = graph.recipe_for(item)
        if recipe is None:
            continue
        output_qty = recipe.products[item]
        speed = config.machine_speeds.get(recipe.machine, 1.0)
        machines_float = rate * recipe.crafting_time / (speed * output_qty)
        counts[recipe.name] = counts.get(recipe.name, 0) + math.ceil(machines_float)
    return counts


def _compute_simulated_hours(target_hours: float, total_machines: int, stage: str, config: Config) -> float:
    budget = config.machine_budget[stage]
    if total_machines <= budget:
        return target_hours
    return target_hours * (total_machines / budget)


def _detect_bottlenecks(
    machine_counts: dict[str, int],
    prev_counts: dict[str, int],
    threshold: int,
) -> list[Bottleneck]:
    bottlenecks = []
    for recipe_name, count in machine_counts.items():
        delta = count - prev_counts.get(recipe_name, 0)
        if delta >= threshold:
            bottlenecks.append(Bottleneck(
                recipe_name=recipe_name,
                machines_required=count,
                delta=delta,
            ))
    bottlenecks.sort(key=lambda b: b.delta, reverse=True)
    return bottlenecks
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_engine.py -v`

Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/engine.py tests/test_engine.py
git commit -m "feat: simulation engine with machine counts, achievability, and bottleneck detection"
```

---

## Task 6: HTML Reporter — Run Mode

**Files:**
- Create: `src/reporter.py`
- Create: `tests/test_reporter.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_reporter.py
import pytest
from pathlib import Path
from src.engine import run_simulation, TierResult
from src.reporter import generate_report, generate_comparison_report


def test_generate_report_creates_html_file(simple_game_data, tmp_path):
    results = run_simulation(simple_game_data)
    out = str(tmp_path / "report.html")
    generate_report(results, out)
    assert Path(out).exists()
    content = Path(out).read_text(encoding="utf-8")
    assert "<html" in content.lower()


def test_report_contains_tier_name(simple_game_data, tmp_path):
    results = run_simulation(simple_game_data)
    out = str(tmp_path / "report.html")
    generate_report(results, out)
    content = Path(out).read_text(encoding="utf-8")
    assert "Automation Science" in content


def test_report_contains_plotly(simple_game_data, tmp_path):
    results = run_simulation(simple_game_data)
    out = str(tmp_path / "report.html")
    generate_report(results, out)
    content = Path(out).read_text(encoding="utf-8")
    assert "plotly" in content.lower()


def test_report_contains_bottleneck_table(simple_game_data, tmp_path):
    results = run_simulation(simple_game_data)
    out = str(tmp_path / "report.html")
    generate_report(results, out)
    content = Path(out).read_text(encoding="utf-8")
    assert "Bottleneck" in content


def test_comparison_report_contains_both_labels(simple_game_data, tmp_path):
    results = run_simulation(simple_game_data)
    out = str(tmp_path / "compare.html")
    generate_comparison_report(results, results, out, label_a="Baseline", label_b="Modified")
    content = Path(out).read_text(encoding="utf-8")
    assert "Baseline" in content
    assert "Modified" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reporter.py -v`

Expected: `ModuleNotFoundError` — `src.reporter` does not exist yet.

- [ ] **Step 3: Implement src/reporter.py**

```python
# src/reporter.py
from __future__ import annotations
from pathlib import Path
import plotly.graph_objects as go
from src.engine import TierResult


def generate_report(results: list[TierResult], output_path: str) -> None:
    """Generate a standalone HTML report for a single simulation run."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    html = _build_html(results, comparison=None)
    Path(output_path).write_text(html, encoding="utf-8")


def generate_comparison_report(
    base_results: list[TierResult],
    mod_results: list[TierResult],
    output_path: str,
    label_a: str = "Baseline",
    label_b: str = "Modified",
) -> None:
    """Generate a side-by-side comparison HTML report."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    html = _build_html(base_results, comparison=(mod_results, label_a, label_b))
    Path(output_path).write_text(html, encoding="utf-8")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_html(results: list[TierResult], comparison) -> str:
    sections: list[str] = []
    include_js = True  # embed plotly.js once

    # Section 1: Tier Timeline
    fig = _timeline_figure(results, label="")
    if comparison is not None:
        mod_results, label_a, label_b = comparison
        fig_mod = _timeline_figure(mod_results, label=label_b)
        sections.append(f"<h2>Tier Timeline — {label_a}</h2>")
        sections.append(fig.to_html(full_html=False, include_plotlyjs=include_js))
        include_js = False
        sections.append(f"<h2>Tier Timeline — {label_b}</h2>")
        sections.append(fig_mod.to_html(full_html=False, include_plotlyjs=False))
    else:
        sections.append("<h2>Tier Timeline</h2>")
        sections.append(fig.to_html(full_html=False, include_plotlyjs=include_js))
        include_js = False

    # Section 2: Machine Counts per tier
    for result in results:
        fig_m = _machine_counts_figure(result)
        sections.append(f"<h2>Machine Counts — {result.tier_name}</h2>")
        sections.append(fig_m.to_html(full_html=False, include_plotlyjs=False))

    if comparison is not None:
        mod_results, label_a, label_b = comparison
        for result in mod_results:
            fig_m = _machine_counts_figure(result)
            sections.append(f"<h2>Machine Counts ({label_b}) — {result.tier_name}</h2>")
            sections.append(fig_m.to_html(full_html=False, include_plotlyjs=False))

    # Section 3: Bottleneck Table
    sections.append("<h2>Bottleneck Table</h2>")
    sections.append(_bottleneck_table(results))

    if comparison is not None:
        mod_results, label_a, label_b = comparison
        sections.append(f"<h2>Bottleneck Table — {label_b}</h2>")
        sections.append(_bottleneck_table(mod_results))

    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>FactoryBoy Simulation Report</title>
<style>
  body {{ font-family: sans-serif; margin: 2em; background: #1a1a2e; color: #e0e0e0; }}
  h1 {{ color: #f0a500; }}
  h2 {{ color: #a0c4ff; border-bottom: 1px solid #333; padding-bottom: 0.3em; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 2em; }}
  th, td {{ border: 1px solid #444; padding: 0.5em 1em; text-align: left; }}
  th {{ background: #2a2a4a; }}
  tr.bottleneck {{ background: #4a1a1a; }}
  tr.bottleneck td:last-child {{ color: #ff6b6b; font-weight: bold; }}
</style>
</head>
<body>
<h1>FactoryBoy Simulation Report</h1>
{body}
</body>
</html>"""


def _timeline_figure(results: list[TierResult], label: str) -> go.Figure:
    names = [r.tier_name for r in results]
    target = [r.target_hours for r in results]
    simulated = [r.simulated_hours for r in results]
    title = f"Tier Timeline{' — ' + label if label else ''}"
    fig = go.Figure(data=[
        go.Bar(name="Target Hours", x=names, y=target, marker_color="steelblue"),
        go.Bar(name="Simulated Hours", x=names, y=simulated, marker_color="darkorange"),
    ])
    fig.update_layout(
        barmode="group",
        title=title,
        xaxis_title="Science Tier",
        yaxis_title="Hours",
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#1a1a2e",
        font_color="#e0e0e0",
    )
    return fig


def _machine_counts_figure(result: TierResult) -> go.Figure:
    sorted_items = sorted(result.machine_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    names = [item[0] for item in sorted_items]
    counts = [item[1] for item in sorted_items]
    fig = go.Figure(data=[go.Bar(x=names, y=counts, marker_color="teal")])
    fig.update_layout(
        title=f"Machine Counts — {result.tier_name}",
        xaxis_title="Recipe",
        yaxis_title="Machines Required",
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#1a1a2e",
        font_color="#e0e0e0",
    )
    return fig


def _bottleneck_table(results: list[TierResult]) -> str:
    rows: list[str] = []
    for result in results:
        for b in result.bottlenecks:
            flag = "⚠" if b.delta >= 20 else ""
            row_class = ' class="bottleneck"' if flag else ""
            rows.append(
                f'<tr{row_class}>'
                f"<td>{result.tier_name}</td>"
                f"<td>{b.recipe_name}</td>"
                f"<td>{b.machines_required}</td>"
                f"<td>+{b.delta}</td>"
                f"<td>{flag}</td>"
                f"</tr>"
            )
    if not rows:
        rows.append('<tr><td colspan="5">No bottlenecks detected.</td></tr>')
    header = (
        "<table>"
        "<thead><tr>"
        "<th>Tier</th><th>Recipe</th><th>Machines Required</th>"
        "<th>Delta from Previous</th><th>Flag</th>"
        "</tr></thead><tbody>"
    )
    return header + "\n".join(rows) + "</tbody></table>"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_reporter.py -v`

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/reporter.py tests/test_reporter.py
git commit -m "feat: HTML reporter with Plotly timeline, machine count charts, and bottleneck table"
```

---

## Task 7: CLI Entry Point

**Files:**
- Create: `factoryboy.py`

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/test_cli.py
import subprocess
import sys
from pathlib import Path


def test_cli_help_exits_cleanly():
    result = subprocess.run(
        [sys.executable, "factoryboy.py", "--help"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0
    assert "run" in result.stdout
    assert "compare" in result.stdout


def test_cli_run_with_data_dir(tmp_path):
    # Write minimal valid data files
    (tmp_path / "config.yaml").write_text("""
root_input: water
root_input_rate: 1000
machine_speeds:
  assembler-1: 0.5
  stone-furnace: 1.0
bottleneck_threshold: 20
machine_budget:
  early: 50
  mid: 200
  late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
    (tmp_path / "recipes.yaml").write_text("""
recipes:
  test-pack:
    ingredients:
      water: 1
    products:
      test-pack: 1
    crafting_time: 1.0
    machine: assembler-1
""")
    (tmp_path / "tech_tree.yaml").write_text("""
tiers:
  - name: Test Tier
    target_hours: 2
    science_packs:
      test-pack: 50
    unlocks: []
""")
    out_path = tmp_path / "out.html"
    result = subprocess.run(
        [sys.executable, "factoryboy.py", "run",
         "--data", str(tmp_path), "--output", str(out_path)],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0
    assert out_path.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py -v`

Expected: `FAIL` — `factoryboy.py` does not exist yet.

- [ ] **Step 3: Implement factoryboy.py**

```python
#!/usr/bin/env python3
# factoryboy.py
"""FactoryBoy — Seablock modpack playtest simulation tool.

Usage:
  python factoryboy.py run [--data DATA_DIR] [--output OUTPUT_PATH]
  python factoryboy.py compare DIR_A DIR_B [--output OUTPUT_PATH] [--label-a LABEL] [--label-b LABEL]
"""
import argparse
import sys
import webbrowser
from pathlib import Path

from src.loader import load_data
from src.engine import run_simulation
from src.reporter import generate_report, generate_comparison_report


def cmd_run(args) -> int:
    data = load_data(args.data)
    results = run_simulation(data)
    output = args.output or data.config.report_output
    generate_report(results, output)
    print(f"Report written to: {output}")
    if not args.no_open:
        webbrowser.open(Path(output).resolve().as_uri())
    return 0


def cmd_compare(args) -> int:
    data_a = load_data(args.dir_a)
    data_b = load_data(args.dir_b)
    results_a = run_simulation(data_a)
    results_b = run_simulation(data_b)
    output = args.output or "reports/comparison.html"
    generate_comparison_report(
        results_a, results_b, output,
        label_a=args.label_a,
        label_b=args.label_b,
    )
    print(f"Comparison report written to: {output}")
    if not args.no_open:
        webbrowser.open(Path(output).resolve().as_uri())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="factoryboy",
        description="Seablock modpack playtest simulation tool",
    )
    parser.add_argument("--no-open", action="store_true", help="Don't open report in browser")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run simulation and generate report")
    run_parser.add_argument("--data", default="data", help="Data directory (default: data/)")
    run_parser.add_argument("--output", default=None, help="Output HTML path (overrides config)")
    run_parser.add_argument("--no-open", action="store_true", help="Don't open report in browser")

    cmp_parser = sub.add_parser("compare", help="Compare two data directories")
    cmp_parser.add_argument("dir_a", help="Baseline data directory")
    cmp_parser.add_argument("dir_b", help="Modified data directory")
    cmp_parser.add_argument("--output", default=None, help="Output HTML path")
    cmp_parser.add_argument("--label-a", default="Baseline", help="Label for dir_a")
    cmp_parser.add_argument("--label-b", default="Modified", help="Label for dir_b")
    cmp_parser.add_argument("--no-open", action="store_true", help="Don't open report in browser")

    args = parser.parse_args()
    if args.command == "run":
        return cmd_run(args)
    if args.command == "compare":
        return cmd_compare(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`

Expected: 2 tests pass.

- [ ] **Step 5: Run full test suite**

Run: `pytest -v`

Expected: All tests pass (no failures).

- [ ] **Step 6: Commit**

```bash
git add factoryboy.py tests/test_cli.py
git commit -m "feat: CLI entry point with run and compare commands"
```

---

## Task 8: Sample Data Files

**Files:**
- Create: `data/config.yaml`
- Create: `data/recipes.yaml`
- Create: `data/tech_tree.yaml`

These are the default data files — a starter Seablock-style chain from water through two science tiers. Edit these freely as you build your modpack.

- [ ] **Step 1: Create data/config.yaml**

```yaml
# FactoryBoy simulation config
# Root input: the single unconstrained base resource for this modpack.
root_input: water
root_input_rate: 100000      # units/second — treat as infinite

machine_speeds:
  assembler-1: 0.5
  assembler-2: 0.75
  assembler-3: 1.25
  stone-furnace: 1.0
  electric-furnace: 2.0
  chemical-plant: 1.0
  centrifuge: 0.75
  boiler: 1.0

# Flag a recipe in the bottleneck table when its machine count
# jumps by more than this many machines between consecutive tiers.
bottleneck_threshold: 20

# Maximum total machines a player reasonably has at each stage.
# If a tier requires more than the budget to hit its target pace,
# simulated_hours is scaled up proportionally.
machine_budget:
  early: 50       # tiers 0-1
  mid: 200        # tiers 2-4
  late: 800       # tiers 5+

# Fallback pacing when a tier doesn't specify target_hours.
default_target_hours:
  early: 3
  mid: 9
  late: 20

report_output: reports/latest.html
```

- [ ] **Step 2: Create data/recipes.yaml**

```yaml
# FactoryBoy recipe definitions
# Each recipe: ingredients, products, crafting_time (seconds), machine type.
# Items with no recipe are treated as raw materials by the solver.

recipes:
  # ── Water processing ──────────────────────────────────────────────────────
  steam:
    ingredients:
      water: 10
    products:
      steam: 10
    crafting_time: 1.0
    machine: boiler

  mineralized-water:
    ingredients:
      water: 100
      steam: 100
    products:
      mineralized-water: 100
    crafting_time: 5.0
    machine: chemical-plant

  mineral-sludge:
    ingredients:
      mineralized-water: 10
    products:
      mineral-sludge: 1
    crafting_time: 10.0
    machine: chemical-plant

  # ── Ore extraction ────────────────────────────────────────────────────────
  iron-ore:
    ingredients:
      mineral-sludge: 1
    products:
      iron-ore: 1
      copper-ore: 1
    crafting_time: 10.0
    machine: centrifuge

  copper-ore:
    ingredients:
      mineral-sludge: 1
    products:
      iron-ore: 1
      copper-ore: 1
    crafting_time: 10.0
    machine: centrifuge

  # ── Smelting ──────────────────────────────────────────────────────────────
  iron-plate:
    ingredients:
      iron-ore: 1
    products:
      iron-plate: 1
    crafting_time: 3.2
    machine: stone-furnace

  copper-plate:
    ingredients:
      copper-ore: 1
    products:
      copper-plate: 1
    crafting_time: 3.2
    machine: stone-furnace

  # ── Basic components ──────────────────────────────────────────────────────
  iron-gear-wheel:
    ingredients:
      iron-plate: 2
    products:
      iron-gear-wheel: 1
    crafting_time: 0.5
    machine: assembler-1

  copper-cable:
    ingredients:
      copper-plate: 1
    products:
      copper-cable: 2
    crafting_time: 0.5
    machine: assembler-1

  electronic-circuit:
    ingredients:
      iron-plate: 1
      copper-cable: 3
    products:
      electronic-circuit: 1
    crafting_time: 0.5
    machine: assembler-1

  # ── Science packs ─────────────────────────────────────────────────────────
  automation-science-pack:
    ingredients:
      iron-plate: 1
      copper-plate: 1
    products:
      automation-science-pack: 1
    crafting_time: 5.0
    machine: assembler-1

  logistic-science-pack:
    ingredients:
      electronic-circuit: 1
      iron-gear-wheel: 1
    products:
      logistic-science-pack: 1
    crafting_time: 6.0
    machine: assembler-1
```

- [ ] **Step 3: Create data/tech_tree.yaml**

```yaml
# FactoryBoy tech tree
# Tiers run in order. target_hours is the desired player time to complete
# all research in this tier. science_packs lists total pack counts needed.

tiers:
  - name: "Automation Science"
    target_hours: 3
    science_packs:
      automation-science-pack: 100
    unlocks:
      - iron-plate
      - copper-plate
      - iron-gear-wheel
      - copper-cable
      - automation-science-pack

  - name: "Logistic Science"
    target_hours: 8
    science_packs:
      automation-science-pack: 300
      logistic-science-pack: 300
    unlocks:
      - electronic-circuit
      - logistic-science-pack
```

- [ ] **Step 4: Verify the full tool runs end-to-end**

Run: `python factoryboy.py run --no-open`

Expected output (approximately):
```
Report written to: reports/latest.html
```

File `reports/latest.html` should exist and open correctly in a browser showing:
- A tier timeline bar chart (two tiers, target vs simulated hours)
- Machine count charts for each tier
- Bottleneck table (may show no bottlenecks on this small dataset)

- [ ] **Step 5: Commit**

```bash
git add data/config.yaml data/recipes.yaml data/tech_tree.yaml
git commit -m "feat: starter Seablock-style sample data with two science tiers"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Pure software simulation with YAML data files (Task 2)
- [x] Recipe dependency graph (Task 3)
- [x] Demand solver — backward traversal to root input (Task 4)
- [x] Machine count estimation per recipe (Task 5)
- [x] Achievability: simulated hours vs target hours via machine budget (Task 5)
- [x] Bottleneck detection with configurable threshold (Task 5)
- [x] HTML report: tier timeline chart (Task 6)
- [x] HTML report: machine counts chart per tier (Task 6)
- [x] HTML report: bottleneck table (Task 6)
- [x] Comparison mode: side-by-side diff of two data directories (Task 6, Task 7)
- [x] CLI `run` command (Task 7)
- [x] CLI `compare` command (Task 7)
- [x] Single configurable root input (config.yaml)
- [x] Default pacing targets (config.yaml + engine fallback)
- [x] Sample starter data (Task 8)

**Type consistency check:**
- `ThroughputMap.rates` — used in solver.py, consumed in engine.py ✓
- `TierResult` fields (`tier_name`, `target_hours`, `simulated_hours`, `total_machines`, `machine_counts`, `bottlenecks`) — defined in engine.py, consumed in reporter.py ✓
- `Bottleneck` fields (`recipe_name`, `machines_required`, `delta`) — defined in engine.py, rendered in reporter.py ✓
- `RecipeGraph.recipe_for()` — defined in graph.py, called in solver.py and engine.py ✓
- `load_data(data_dir: str)` — defined in loader.py, called in factoryboy.py ✓

**Note on ore extraction recipes:** `data/recipes.yaml` defines both `iron-ore` and `copper-ore` as separate recipes that produce both products from `mineral-sludge`. The solver will pick one recipe per product (last-write-wins in `RecipeGraph.build`). This means copper-ore and iron-ore effectively share a single `mineral-sludge` upstream chain. This is a simplification — refine the recipe data as your modpack's ore extraction takes shape.

# FactoryBoy

Factorio production chain simulator. Computes throughput requirements for every item in a recipe chain, simulates machine budgets across game tiers, and generates HTML reports with bottleneck analysis.

## Architecture

```
factoryboy.py       — CLI entry point (argparse: --help, --run)
src/loader.py       — Data models + YAML loading (Recipe, Tier, Config, GameData)
src/graph.py        — RecipeGraph: indexes recipes by product for fast lookup
src/solver.py       — solve(): backward traversal from target item to root_input
src/engine.py       — run_simulation(): solver → machine counts → budget check → bottlenecks
src/reporter.py     — generate_report(): HTML + Plotly charts from simulation results
tests/              — pytest suite (45 tests: 28 unit + 17 integration, all passing as of 2026-05-03)
data/               — YAML data files (config.yaml, recipes.yaml, tech_tree.yaml)
reports/            — generated HTML report output
```

## Data Models

### Recipe
- `name`: str — recipe identifier
- `ingredients`: dict[str, float] — input items → quantity per craft
- `products`: dict[str, float] — output items → quantity per craft
- `crafting_time`: float — seconds per craft cycle
- `machine`: str — machine type (e.g., "assembler-1", "stone-furnace")
- `surface`: str — planet/surface where recipe is available (e.g., "nauvis", "skyline")

### Tier
- `name`: str — tier display name
- `target_hours`: float | None — target production hours (falls back to config defaults)
- `science_packs`: dict[str, int] — science pack → total quantity needed
- `unlocks`: list[str] — items/tech unlocked by this tier

### Config
- `root_input`: str — terminal item with no upstream recipe (e.g., "water")
- `root_input_rate`: float — max extraction rate for root input
- `machine_speeds`: dict[str, float] — machine type → speed factor
- `bottleneck_threshold`: int — machine count delta that triggers bottleneck warning
- `machine_budget`: dict[str, dict[str, int]] — surface → {stage: budget} (stages: early/mid/late)
- `spoilage_multiplier`: float — throughput multiplier for perishable items (default 1.0)
- `perishable_items`: list[str] — items subject to spoilage
- `default_target_hours`: dict[str, float] — stage → default hours fallback
- `report_output`: str — path for generated HTML report

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Run with data directory
python factoryboy.py --run data/

# Generate reports
python factoryboy.py --run data/ --output reports/my_report.html

# Run tests
python -m pytest -v tests/
```

## Solver Algorithm

The solver performs a backward traversal from the target item to `root_input`:

1. Start with pending demand `{target_item: requested_rate}`
2. Process largest pending demand first (numerical stability)
3. For each item, look up its recipe and compute ingredient demands
4. Apply spoilage multiplier for perishable items
5. Accumulate all demands into a ThroughputMap

**Cycle detection**: A visited set prevents infinite loops on circular dependencies. The root input is intentionally excluded from the visited set so demands from multiple branching chains can accumulate correctly.

## Simulation Pipeline

`run_simulation(GameData) → list[TierResult]`:

1. For each tier, compute science pack demands
2. Solve throughput for each required science pack
3. Convert throughput to machine counts using crafting_time and machine_speeds
4. Check total machines against surface budget for the current stage
5. If over budget, scale simulated_hours upward proportionally
6. Detect bottlenecks by comparing machine count deltas between consecutive tiers

## Current State (2026-05-03)

- **Branch**: `master`
- **Tests**: 51/51 passing (34 unit + 17 integration, all passing as of 2026-05-03)
- **Schema**: Multi-surface aware with surface-aware recipe selection
- **Last addition**: Surface-aware recipe selection — solver prefers recipes on target surface with fallback

## Pending Work / Next Steps

1. **~Integration tests — DONE~** — End-to-end YAML → loader → engine → reporter pipeline ✅
2. **~Surface-aware recipe selection — DONE~** — Solver selects recipes by target surface, falls back to any-surface ✅
3. **Perishable/spoilage data** — Add perishable items to `data/recipes.yaml` and test spoilage multiplier
4. **~Multi-surface simulation — DONE~** — Engine tracks machine budgets per-surface with surface_machine_counts ✅
5. **Tech tree dependencies** — Loader supports `unlocks` but engine doesn't yet model prerequisite gating
6. **Data expansion** — Populate `data/recipes.yaml` with full Factorio recipe database

## File Format Reference

### data/config.yaml
```yaml
root_input: water
root_input_rate: 1000.0
machine_speeds:
  assembler-1: 0.5
  stone-furnace: 1.0
bottleneck_threshold: 5
machine_budget:
  nauvis:
    early: 50
    mid: 200
    late: 500
spoilage_multiplier: 1.0
perishable_items: []
default_target_hours:
  early: 3.0
  mid: 9.0
  late: 20.0
report_output: reports/latest.html
```

### data/recipes.yaml
```yaml
recipes:
  iron-plate:
    ingredients: { iron-ore: 2.0 }
    products: { iron-plate: 4.0 }
    crafting_time: 2.0
    machine: stone-furnace
    surface: nauvis
```

### data/tech_tree.yaml
```yaml
tiers:
  - name: Automation Science
    target_hours: 3.0
    science_packs: { automation-science-pack: 500 }
    unlocks: []
# FactoryBoy — Seablock Modpack Playtest Simulation Tool
**Design Spec — 2026-04-12**

## Overview

FactoryBoy is a pure mathematical simulation tool for playtesting a custom Seablock-style Factorio modpack (Factorio 2.x + Space Age). Its purpose is to detect balance problems — specifically science tiers that take too long to complete and production chains that cannot reasonably scale — without requiring a running Factorio instance.

The tool models an idealized player: one who always produces optimally. This gives a ceiling on performance, not a realistic average, which is the right tool for detecting recipe/tech-tree balance problems before they reach play.

---

## Architecture

Three layers, cleanly separated:

```
YAML Data Files          Simulation Engine          HTML Report
─────────────────        ──────────────────         ───────────
recipes.yaml      ──►    Recipe graph builder  ──►  Timeline chart
tech_tree.yaml    ──►    Demand solver        ──►  Bottleneck table
config.yaml       ──►    Timeline builder     ──►  Throughput curves
                         Bottleneck detector  ──►  Comparison diff
```

**CLI interface — two commands:**
- `python factoryboy.py run` — run simulation using `data/` directory, generate and open HTML report
- `python factoryboy.py compare data/baseline/ data/modified/` — diff two complete data directories, generate comparison report

Each data directory contains its own `recipes.yaml`, `tech_tree.yaml`, and `config.yaml`. The `run` command defaults to `data/`. The `compare` command accepts any two directories with valid data files.

---

## Data Model

Three human-editable YAML files. These are the source of truth for the simulation — no Factorio mod files are parsed.

### `data/recipes.yaml`

Defines every recipe in the modpack.

```yaml
recipes:
  iron-plate:
    ingredients:
      iron-ore: 1
    products:
      iron-plate: 1
    crafting_time: 3.2      # seconds
    machine: stone-furnace

  electronic-circuit:
    ingredients:
      iron-plate: 1
      copper-cable: 3
    products:
      electronic-circuit: 1
    crafting_time: 0.5
    machine: assembler-1
```

Fields:
- `ingredients` — map of item name to quantity consumed per craft
- `products` — map of item name to quantity produced per craft
- `crafting_time` — seconds per craft cycle (base, before machine speed)
- `machine` — machine type used; looked up in `config.yaml` for speed multiplier

### `data/tech_tree.yaml`

Defines science tiers in progression order.

```yaml
tiers:
  - name: "Automation Science"
    target_hours: 3
    science_packs:
      automation-science-pack: 100    # total packs needed to complete this tier
    unlocks:
      - iron-plate
      - copper-plate
      - electronic-circuit

  - name: "Logistic Science"
    target_hours: 8
    science_packs:
      automation-science-pack: 200
      logistic-science-pack: 200
    unlocks:
      - advanced-circuit
      - steel-plate
```

Fields:
- `target_hours` — desired real-world hours for a player to complete this tier (the benchmark)
- `science_packs` — map of science pack type to total count required to unlock everything in this tier
- `unlocks` — list of recipes/items made available upon completing this tier (informational, used for graph scoping)

Science pack counts are **cumulative totals**, not rates. The engine derives rate from `total / target_hours`.

### `config.yaml`

Simulation-wide settings.

```yaml
root_input: water                  # the single unconstrained base resource
root_input_rate: 1000              # units/second (effectively infinite; configurable for future constraints)

machine_speeds:
  assembler-1: 0.5
  assembler-2: 0.75
  assembler-3: 1.25
  stone-furnace: 1.0
  electric-furnace: 2.0

bottleneck_threshold: 20           # flag a recipe if machine delta between tiers exceeds this

machine_budget:                    # max machines a player reasonably has at each stage
  early: 50                        # tiers 1-2
  mid: 200                         # tiers 3-5
  late: 800                        # tiers 6+

default_target_hours:              # fallback pacing used if target_hours not set on a tier
  early: 3                         # tiers 1-2
  mid: 9                           # tiers 3-5
  late: 20                         # tiers 6+

report_output: reports/latest.html
```

---

## Simulation Engine

Runs in four steps per science tier, executed sequentially across all tiers.

### Step 1 — Recipe Graph Construction
Parse `recipes.yaml` into a directed dependency graph at startup. Each node is an item; each edge is a recipe relationship (consumes → produces). Built once, reused across all tiers.

### Step 2 — Demand Solver
For each tier:
1. Derive required science pack rate: `target_rate = total_packs / (target_hours × 3600)` packs/second
2. Walk the dependency graph backwards from each required science pack
3. Recursively compute required throughput of every ingredient down to root input
4. Output: a **throughput map** — `{ item_name: required_rate_per_second }` for the entire production chain

This is ratio math, not optimization — no solver library required.

### Step 3 — Machine Count Estimation
For each recipe in the throughput map:
```
machines_needed = required_rate / (machine_speed × (1 / crafting_time))
```
Produces a concrete, human-readable number per recipe per tier. A value that is absurdly large relative to neighboring tiers is a direct balance signal.

### Step 4 — Achievability & Simulated Hours
Compare total machines required for the tier against `machine_budget` for that stage:

```
budget = machine_budget[stage]           # from config.yaml
required = sum of all machines_needed across this tier's recipes

if required <= budget:
    simulated_hours = target_hours       # on pace
else:
    simulated_hours = target_hours × (required / budget)   # takes longer than target
```

`simulated_hours` is what appears in the timeline chart. A tier where `simulated_hours > target_hours` means the player cannot hit the target pace with a reasonable factory — a direct pacing problem signal.

### Step 5 — Bottleneck Detection
Rank recipes by the delta in machine count between consecutive tiers. Flag any recipe where the inter-tier delta exceeds `bottleneck_threshold` from `config.yaml`. These are the recipes the player is being asked to massively scale between tiers.

---

## HTML Report Output

Single self-contained `.html` file. Plotly is embedded — no internet connection required. Can be saved as a snapshot of balance state over time.

### Section 1 — Tier Timeline (bar chart)
- X-axis: science tiers in order
- Y-axis: hours
- Two bar series: target hours (blue) vs. simulated hours (orange)
- Tiers where simulated exceeds target are visually obvious pacing problems

### Section 2 — Machine Counts by Tier (bar chart per tier)
- Top 15 most-demanded recipes ranked by machine count for each tier
- Shows what production scale is being asked of the player at each stage
- Steepness of inter-tier jumps is the key signal

### Section 3 — Bottleneck Table
Sortable table:

| Tier | Recipe | Machines Required | Delta from Previous Tier | Flag |
|------|--------|-------------------|--------------------------|------|
| 3 | advanced-circuit | 47 | +31 | ⚠ |

Rows highlighted red when delta exceeds threshold.

### Comparison Mode
When invoked via `compare`, each section renders two columns side-by-side. Delta values shown inline in green (improvement) or red (regression). Example: `14.2h → 9.8h (-4.4h)`.

---

## Default Pacing Targets

Starting benchmarks (configurable in `config.yaml`):

| Tier Stage | Target Hours |
|------------|-------------|
| Early (1-2) | 2-4 hours |
| Mid (3-5) | 6-12 hours |
| Late (6+) | 15-30 hours |

---

## Constraints & Assumptions

- The simulated player is idealized — optimal production ratios, no waste, no spatial constraints
- Logistics (belt throughput, inserter timing, train scheduling) are not modeled
- Biter pressure is not modeled
- Power generation is not modeled in v1 (treat electricity as free)
- Root input is configurable but treated as unconstrained by default
- Machine counts are whole-machine estimates (not fractional), rounded up

---

## Future Considerations (out of scope for v1)

- Lua mod file parser to auto-sync recipe data from actual mod files
- Multiple root inputs
- Power generation modeling
- Module/beacon efficiency modeling
- Named scenario snapshots for comparison history

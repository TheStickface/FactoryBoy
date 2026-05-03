# src/engine.py
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional
from src.loader import GameData, Tier, Config
from src.graph import RecipeGraph
from src.solver import solve, ThroughputMap


@dataclass
class Bottleneck:
    recipe_name: str
    machines_required: int
    delta: int
    surface: str = ""


@dataclass
class TierResult:
    tier_name: str
    target_hours: float
    simulated_hours: float
    total_machines: int
    machine_counts: dict[str, int]
    bottlenecks: list[Bottleneck]
    # New: per-surface machine breakdown
    surface_machine_counts: dict[str, dict[str, int]] = field(default_factory=dict)


def run_simulation(data: GameData, surface: Optional[str] = None) -> list[TierResult]:
    """Run the full simulation pipeline.

    If surface is specified, recipe selection prefers recipes available on that
    surface and machine budgets are checked per-surface. If None, uses legacy
    global behavior with backward compatibility.
    """
    graph = RecipeGraph.build(data.recipes)
    results: list[TierResult] = []
    prev_counts: dict[str, int] = {}

    for i, tier in enumerate(data.tiers):
        target_hours = _resolve_target_hours(tier, i, data.config)
        stage = _get_stage(i)

        combined = ThroughputMap()
        for pack_name, total_count in tier.science_packs.items():
            rate = total_count / (target_hours * 3600.0)
            pack_map = solve(pack_name, rate, graph, data.config, surface=surface)
            for item, item_rate in pack_map.rates.items():
                combined.add(item, item_rate)

        machine_counts, surface_machine_counts = _compute_machine_counts(
            combined, graph, data.config
        )
        total_machines = sum(machine_counts.values())
        simulated_hours = _compute_simulated_hours(
            target_hours, surface_machine_counts, stage, data.config
        )
        bottlenecks = _detect_bottlenecks(machine_counts, prev_counts, data.config.bottleneck_threshold, graph)

        results.append(TierResult(
            tier_name=tier.name,
            target_hours=target_hours,
            simulated_hours=simulated_hours,
            total_machines=total_machines,
            machine_counts=machine_counts,
            bottlenecks=bottlenecks,
            surface_machine_counts=surface_machine_counts,
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


def _compute_machine_counts(
    throughput: ThroughputMap, graph: RecipeGraph, config: Config
) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    """Compute machine counts globally and per-surface.

    Returns:
        (global_counts, surface_counts) where:
          - global_counts: recipe_name → total machines
          - surface_counts: surface → {recipe_name → machines}
    """
    counts: dict[str, int] = {}
    surface_counts: dict[str, dict[str, int]] = {}

    for item, rate in throughput.rates.items():
        recipe = graph.recipe_for(item)
        if recipe is None:
            continue
        output_qty = recipe.products[item]
        speed = config.machine_speeds.get(recipe.machine, 1.0)
        machines_float = rate * recipe.crafting_time / (speed * output_qty)
        machines = math.ceil(machines_float)

        # Global count
        counts[recipe.name] = counts.get(recipe.name, 0) + machines

        # Per-surface count
        surface = recipe.surface
        if surface not in surface_counts:
            surface_counts[surface] = {}
        surface_counts[surface][recipe.name] = (
            surface_counts[surface].get(recipe.name, 0) + machines
        )

    return counts, surface_counts


def _compute_simulated_hours(
    target_hours: float,
    surface_machine_counts: dict[str, dict[str, int]],
    stage: str,
    config: Config,
) -> float:
    """Compute simulated hours by checking per-surface machine budgets.

    If any surface exceeds its budget for the current stage, scale hours
    upward proportionally using the worst overage ratio.
    """
    worst_multiplier = 1.0
    for surface, recipe_counts in surface_machine_counts.items():
        surface_total = sum(recipe_counts.values())
        budget = config.machine_budget.get(surface, {}).get(stage, 1000000)
        if surface_total > budget:
            worst_multiplier = max(worst_multiplier, surface_total / budget)

    return target_hours * worst_multiplier


def _detect_bottlenecks(
    machine_counts: dict[str, int],
    prev_counts: dict[str, int],
    threshold: int,
    graph: RecipeGraph,
) -> list[Bottleneck]:
    bottlenecks = []
    for recipe_name, count in machine_counts.items():
        delta = count - prev_counts.get(recipe_name, 0)
        if delta >= threshold:
            recipe = graph.recipes.get(recipe_name)
            surface = recipe.surface if recipe else ""
            bottlenecks.append(Bottleneck(
                recipe_name=recipe_name,
                machines_required=count,
                delta=delta,
                surface=surface,
            ))
    bottlenecks.sort(key=lambda b: b.delta, reverse=True)
    return bottlenecks
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

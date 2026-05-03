# src/solver.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from src.loader import Config
from src.graph import RecipeGraph


@dataclass
class ThroughputMap:
    rates: dict[str, float] = field(default_factory=dict)

    def add(self, item: str, rate: float) -> None:
        self.rates[item] = self.rates.get(item, 0.0) + rate


def solve(item: str, rate: float, graph: RecipeGraph, config: Config, surface: Optional[str] = None) -> ThroughputMap:
    """Compute throughput (units/second) required for every item in the chain
    to produce `rate` units/second of `item`. Traces back to config.root_input.

    If surface is specified, recipe selection prefers recipes available on that
    surface. Falls back to any-surface recipes if no match exists.

    Cycle detection uses a visited set to prevent infinite loops on circular
    dependencies. The root input is intentionally excluded so demands from multiple
    branches can accumulate into it even after first processing."""
    result = ThroughputMap()
    pending: dict[str, float] = {item: rate}
    visited: set[str] = set()

    while pending:
        # Process the largest pending demand first for numerical stability
        current_item = max(pending, key=pending.get)
        current_rate = pending.pop(current_item)

        # Cycle detection: skip non-root items already fully processed.
        # The root input is intentionally excluded so demands from multiple
        # branches can accumulate into it even after first processing.
        if current_item != config.root_input and current_item in visited:
            continue
        if current_item != config.root_input:
            visited.add(current_item)

        # Apply spoilage markup if item perishes
        if current_item in config.perishable_items:
            current_rate *= config.spoilage_multiplier

        result.add(current_item, current_rate)

        if current_item == config.root_input:
            continue

        # Surface-aware recipe selection: try target surface first, then fallback
        recipe = graph.recipe_for(current_item, surface=surface)
        if recipe is None:
            recipe = graph.recipe_for(current_item)  # fallback to any surface
        if recipe is None:
            continue

        output_qty = recipe.products.get(current_item, 0.0)
        if output_qty <= 0:
            continue

        for ingredient, qty in recipe.ingredients.items():
            ingredient_rate = current_rate * (qty / output_qty)
            if ingredient_rate < 1e-6:
                continue
            pending[ingredient] = pending.get(ingredient, 0.0) + ingredient_rate

    return result
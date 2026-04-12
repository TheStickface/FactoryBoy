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
    """Compute throughput (units/second) required for every item in the chain
    to produce `rate` units/second of `item`. Traces back to config.root_input."""
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

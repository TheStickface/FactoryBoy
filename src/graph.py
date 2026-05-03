# src/graph.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from src.loader import Recipe


@dataclass
class RecipeGraph:
    recipes: dict[str, Recipe]
    _item_to_recipe: dict[str, Recipe] = field(default_factory=dict, repr=False)
    _item_surface_to_recipes: dict[str, dict[str, list[Recipe]]] = field(default_factory=dict, repr=False)

    @classmethod
    def build(cls, recipes: dict[str, Recipe]) -> RecipeGraph:
        # Legacy flat index: item → last recipe producing it (backward compat)
        item_to_recipe: dict[str, Recipe] = {}
        # New composite index: item → {surface → [recipes]}
        item_surface_to_recipes: dict[str, dict[str, list[Recipe]]] = {}

        for recipe in recipes.values():
            for product in recipe.products:
                item_to_recipe[product] = recipe

                if product not in item_surface_to_recipes:
                    item_surface_to_recipes[product] = {}
                surface_map = item_surface_to_recipes[product]

                if recipe.surface not in surface_map:
                    surface_map[recipe.surface] = []
                surface_map[recipe.surface].append(recipe)

        instance = cls(recipes=recipes)
        instance._item_to_recipe = item_to_recipe
        instance._item_surface_to_recipes = item_surface_to_recipes
        return instance

    def recipe_for(self, item: str, surface: Optional[str] = None) -> Recipe | None:
        """Return a recipe that produces `item`.

        If surface is specified, return the first recipe matching that surface.
        If surface is None, return the first recipe found (backward compat).
        Returns None if no recipe found.
        """
        if surface is None:
            return self._item_to_recipe.get(item)

        surface_map = self._item_surface_to_recipes.get(item, {})
        candidates = surface_map.get(surface, [])
        return candidates[0] if candidates else None

    def recipes_for(self, item: str, surface: Optional[str] = None) -> list[Recipe]:
        """Return all recipes that produce `item`, optionally filtered by surface."""
        surface_map = self._item_surface_to_recipes.get(item, {})
        if surface is None:
            all_recipes: list[Recipe] = []
            for recipes in surface_map.values():
                all_recipes.extend(recipes)
            return all_recipes
        return surface_map.get(surface, [])

    def available_surfaces(self, item: str) -> list[str]:
        """Return list of surfaces where `item` can be produced."""
        surface_map = self._item_surface_to_recipes.get(item, {})
        return list(surface_map.keys())
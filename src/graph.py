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

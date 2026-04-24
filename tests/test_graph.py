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
        surface="nauvis",
    )
    recipes = {**simple_recipes, "iron-plate-alt": extra}
    graph = RecipeGraph.build(recipes)
    # Should not raise; one recipe wins
    assert graph.recipe_for("iron-plate") is not None

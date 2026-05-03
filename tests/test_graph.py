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


# ── Surface-aware tests ──────────────────────────────────────────────────────


def test_recipe_for_with_surface_filter():
    """Recipes on different surfaces should be selectable by surface."""
    from src.loader import Recipe
    recipes = {
        "iron-plate-nauvis": Recipe(
            name="iron-plate-nauvis",
            ingredients={"iron-ore": 1.0},
            products={"iron-plate": 1.0},
            crafting_time=3.2,
            machine="stone-furnace",
            surface="nauvis",
        ),
        "iron-plate-gleba": Recipe(
            name="iron-plate-gleba",
            ingredients={"scrap": 2.0},
            products={"iron-plate": 1.0},
            crafting_time=2.0,
            machine="assembler-1",
            surface="gleba",
        ),
    }
    graph = RecipeGraph.build(recipes)

    # Without surface filter: returns some recipe
    r = graph.recipe_for("iron-plate")
    assert r is not None

    # With surface=nauvis: returns nauvis recipe
    r_nauvis = graph.recipe_for("iron-plate", surface="nauvis")
    assert r_nauvis is not None
    assert r_nauvis.surface == "nauvis"
    assert r_nauvis.name == "iron-plate-nauvis"

    # With surface=gleba: returns gleba recipe
    r_gleba = graph.recipe_for("iron-plate", surface="gleba")
    assert r_gleba is not None
    assert r_gleba.surface == "gleba"
    assert r_gleba.name == "iron-plate-gleba"


def test_recipe_for_returns_none_when_surface_not_available():
    """If item only exists on nauvis, requesting gleba should return None."""
    from src.loader import Recipe
    recipes = {
        "iron-plate-nauvis": Recipe(
            name="iron-plate-nauvis",
            ingredients={"iron-ore": 1.0},
            products={"iron-plate": 1.0},
            crafting_time=3.2,
            machine="stone-furnace",
            surface="nauvis",
        ),
    }
    graph = RecipeGraph.build(recipes)
    assert graph.recipe_for("iron-plate", surface="gleba") is None


def test_recipes_for_returns_all_candidates():
    """recipes_for should return all recipes producing an item."""
    from src.loader import Recipe
    recipes = {
        "iron-plate-nauvis": Recipe(
            name="iron-plate-nauvis",
            ingredients={"iron-ore": 1.0},
            products={"iron-plate": 1.0},
            crafting_time=3.2,
            machine="stone-furnace",
            surface="nauvis",
        ),
        "iron-plate-gleba": Recipe(
            name="iron-plate-gleba",
            ingredients={"scrap": 2.0},
            products={"iron-plate": 1.0},
            crafting_time=2.0,
            machine="assembler-1",
            surface="gleba",
        ),
    }
    graph = RecipeGraph.build(recipes)

    # All recipes
    all_r = graph.recipes_for("iron-plate")
    assert len(all_r) == 2

    # Filtered by surface
    nauvis_r = graph.recipes_for("iron-plate", surface="nauvis")
    assert len(nauvis_r) == 1
    assert nauvis_r[0].surface == "nauvis"


def test_available_surfaces():
    """available_surfaces should list all surfaces where an item can be produced."""
    from src.loader import Recipe
    recipes = {
        "iron-plate-nauvis": Recipe(
            name="iron-plate-nauvis",
            ingredients={"iron-ore": 1.0},
            products={"iron-plate": 1.0},
            crafting_time=3.2,
            machine="stone-furnace",
            surface="nauvis",
        ),
        "iron-plate-gleba": Recipe(
            name="iron-plate-gleba",
            ingredients={"scrap": 2.0},
            products={"iron-plate": 1.0},
            crafting_time=2.0,
            machine="assembler-1",
            surface="gleba",
        ),
    }
    graph = RecipeGraph.build(recipes)
    surfaces = graph.available_surfaces("iron-plate")
    assert set(surfaces) == {"nauvis", "gleba"}

    # Unknown item returns empty
    assert graph.available_surfaces("nonexistent") == []

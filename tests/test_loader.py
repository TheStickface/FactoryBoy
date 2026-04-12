# tests/test_loader.py
import pytest
from pathlib import Path
from src.loader import load_data, Recipe, Tier, Config, GameData

def test_load_config_fields(tmp_path):
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text("""
root_input: water
root_input_rate: 1000
machine_speeds:
  assembler-1: 0.5
  stone-furnace: 1.0
bottleneck_threshold: 20
machine_budget:
  early: 50
  mid: 200
  late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
    recipes_yaml = tmp_path / "recipes.yaml"
    recipes_yaml.write_text("recipes: {}")
    tech_tree_yaml = tmp_path / "tech_tree.yaml"
    tech_tree_yaml.write_text("tiers: []")

    data = load_data(str(tmp_path))
    assert data.config.root_input == "water"
    assert data.config.root_input_rate == 1000.0
    assert data.config.machine_speeds["assembler-1"] == 0.5
    assert data.config.machine_budget["early"] == 50
    assert data.config.default_target_hours["mid"] == 9.0
    assert data.config.bottleneck_threshold == 20

def test_load_recipes(tmp_path):
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text("""
root_input: water
root_input_rate: 1000
machine_speeds:
  assembler-1: 0.5
bottleneck_threshold: 20
machine_budget:
  early: 50
  mid: 200
  late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
    recipes_yaml = tmp_path / "recipes.yaml"
    recipes_yaml.write_text("""
recipes:
  iron-plate:
    ingredients:
      iron-ore: 1
    products:
      iron-plate: 1
    crafting_time: 3.2
    machine: stone-furnace
""")
    tech_tree_yaml = tmp_path / "tech_tree.yaml"
    tech_tree_yaml.write_text("tiers: []")

    data = load_data(str(tmp_path))
    assert "iron-plate" in data.recipes
    r = data.recipes["iron-plate"]
    assert r.ingredients == {"iron-ore": 1.0}
    assert r.products == {"iron-plate": 1.0}
    assert r.crafting_time == 3.2
    assert r.machine == "stone-furnace"

def test_load_tech_tree(tmp_path):
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text("""
root_input: water
root_input_rate: 1000
machine_speeds: {}
bottleneck_threshold: 20
machine_budget:
  early: 50
  mid: 200
  late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
    recipes_yaml = tmp_path / "recipes.yaml"
    recipes_yaml.write_text("recipes: {}")
    tech_tree_yaml = tmp_path / "tech_tree.yaml"
    tech_tree_yaml.write_text("""
tiers:
  - name: Automation Science
    target_hours: 3
    science_packs:
      automation-science-pack: 100
    unlocks:
      - iron-plate
""")

    data = load_data(str(tmp_path))
    assert len(data.tiers) == 1
    t = data.tiers[0]
    assert t.name == "Automation Science"
    assert t.target_hours == 3.0
    assert t.science_packs == {"automation-science-pack": 100}
    assert t.unlocks == ["iron-plate"]

def test_tier_without_target_hours(tmp_path):
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text("""
root_input: water
root_input_rate: 1000
machine_speeds: {}
bottleneck_threshold: 20
machine_budget:
  early: 50
  mid: 200
  late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
    recipes_yaml = tmp_path / "recipes.yaml"
    recipes_yaml.write_text("recipes: {}")
    tech_tree_yaml = tmp_path / "tech_tree.yaml"
    tech_tree_yaml.write_text("""
tiers:
  - name: Late Tier
    science_packs:
      science-pack: 500
""")

    data = load_data(str(tmp_path))
    assert data.tiers[0].target_hours is None

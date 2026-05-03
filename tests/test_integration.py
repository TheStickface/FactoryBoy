"""Integration tests — end-to-end YAML → loader → engine → reporter pipeline.

These tests exercise the full stack using real YAML fixtures, verifying that:
1. Data loads correctly from YAML files
2. Solver computes throughput through the entire chain
3. Engine produces valid TierResults with machine counts and bottlenecks
4. Reporter generates valid HTML with expected content
5. Edge cases (spoilage, over-budget, multi-surface) work end-to-end
"""
import pytest
from pathlib import Path
from src.loader import load_data
from src.engine import run_simulation
from src.reporter import generate_report, generate_comparison_report


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_data_dir(tmp_path):
    """Create a minimal valid data directory in tmp_path."""
    (tmp_path / "config.yaml").write_text("""
root_input: water
root_input_rate: 1000
machine_speeds:
  assembler-1: 0.5
  stone-furnace: 1.0
  chemical-plant: 1.0
bottleneck_threshold: 20
machine_budget:
  nauvis:
    early: 50
    mid: 200
    late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
    (tmp_path / "recipes.yaml").write_text("""
recipes:
  iron-ore:
    ingredients:
      water: 10
    products:
      iron-ore: 1
    crafting_time: 10.0
    machine: chemical-plant
  iron-plate:
    ingredients:
      iron-ore: 1
    products:
      iron-plate: 1
    crafting_time: 3.2
    machine: stone-furnace
  automation-science-pack:
    ingredients:
      iron-plate: 1
    products:
      automation-science-pack: 1
    crafting_time: 5.0
    machine: assembler-1
""")
    (tmp_path / "tech_tree.yaml").write_text("""
tiers:
  - name: Automation Science
    target_hours: 3
    science_packs:
      automation-science-pack: 100
    unlocks: []
""")
    return tmp_path


@pytest.fixture
def multi_tier_data_dir(tmp_path):
    """Create a multi-tier data directory with branching recipes."""
    (tmp_path / "config.yaml").write_text("""
root_input: water
root_input_rate: 10000
machine_speeds:
  assembler-1: 0.5
  stone-furnace: 1.0
  chemical-plant: 1.0
  centrifuge: 0.75
bottleneck_threshold: 5
machine_budget:
  nauvis:
    early: 50
    mid: 200
    late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
spoilage_multiplier: 1.0
perishable_items: []
report_output: reports/latest.html
""")
    (tmp_path / "recipes.yaml").write_text("""
recipes:
  mineralized-water:
    ingredients:
      water: 100
    products:
      mineralized-water: 100
    crafting_time: 5.0
    machine: chemical-plant
  mineral-sludge:
    ingredients:
      mineralized-water: 10
    products:
      mineral-sludge: 1
    crafting_time: 10.0
    machine: chemical-plant
  iron-ore:
    ingredients:
      mineral-sludge: 1
    products:
      iron-ore: 1
      copper-ore: 1
    crafting_time: 10.0
    machine: centrifuge
  copper-ore:
    ingredients:
      mineral-sludge: 1
    products:
      iron-ore: 1
      copper-ore: 1
    crafting_time: 10.0
    machine: centrifuge
  iron-plate:
    ingredients:
      iron-ore: 1
    products:
      iron-plate: 1
    crafting_time: 3.2
    machine: stone-furnace
  copper-plate:
    ingredients:
      copper-ore: 1
    products:
      copper-plate: 1
    crafting_time: 3.2
    machine: stone-furnace
  iron-gear-wheel:
    ingredients:
      iron-plate: 2
    products:
      iron-gear-wheel: 1
    crafting_time: 0.5
    machine: assembler-1
  copper-cable:
    ingredients:
      copper-plate: 1
    products:
      copper-cable: 2
    crafting_time: 0.5
    machine: assembler-1
  electronic-circuit:
    ingredients:
      iron-plate: 1
      copper-cable: 3
    products:
      electronic-circuit: 1
    crafting_time: 0.5
    machine: assembler-1
  automation-science-pack:
    ingredients:
      iron-plate: 1
      copper-plate: 1
    products:
      automation-science-pack: 1
    crafting_time: 5.0
    machine: assembler-1
  logistic-science-pack:
    ingredients:
      electronic-circuit: 1
      iron-gear-wheel: 1
    products:
      logistic-science-pack: 1
    crafting_time: 6.0
    machine: assembler-1
""")
    (tmp_path / "tech_tree.yaml").write_text("""
tiers:
  - name: Automation Science
    target_hours: 3
    science_packs:
      automation-science-pack: 100
    unlocks: []
  - name: Logistic Science
    target_hours: 8
    science_packs:
      automation-science-pack: 300
      logistic-science-pack: 300
    unlocks: []
  - name: Space Science
    target_hours: 20
    science_packs:
      automation-science-pack: 5000
      logistic-science-pack: 5000
    unlocks: []
""")
    return tmp_path


@pytest.fixture
def spoilage_data_dir(tmp_path):
    """Create a data directory with perishable items and spoilage multiplier."""
    (tmp_path / "config.yaml").write_text("""
root_input: nutrients
root_input_rate: 1000
machine_speeds:
  assembler-1: 0.5
bottleneck_threshold: 20
machine_budget:
  gleba:
    early: 50
    mid: 200
    late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
spoilage_multiplier: 1.05
perishable_items:
  - nutrients
  - biochamber
report_output: reports/latest.html
""")
    (tmp_path / "recipes.yaml").write_text("""
recipes:
  biochamber:
    ingredients:
      nutrients: 10
    products:
      biochamber: 1
    crafting_time: 10.0
    machine: assembler-1
    surface: gleba
  agricultural-science-pack:
    ingredients:
      nutrients: 10
      biochamber: 1
    products:
      agricultural-science-pack: 1
    crafting_time: 12.0
    machine: assembler-1
    surface: gleba
""")
    (tmp_path / "tech_tree.yaml").write_text("""
tiers:
  - name: Agricultural Science
    target_hours: 5
    science_packs:
      agricultural-science-pack: 500
    unlocks: []
""")
    return tmp_path


@pytest.fixture
def multi_surface_data_dir(tmp_path):
    """Create a data directory with recipes on multiple surfaces."""
    (tmp_path / "config.yaml").write_text("""
root_input: water
root_input_rate: 10000
machine_speeds:
  assembler-1: 0.5
  chemical-plant: 1.0
  centrifuge: 0.75
bottleneck_threshold: 20
machine_budget:
  nauvis:
    early: 50
    mid: 200
    late: 800
  gleba:
    early: 20
    mid: 100
    late: 300
default_target_hours:
  early: 3
  mid: 9
  late: 20
spoilage_multiplier: 1.0
perishable_items: []
report_output: reports/latest.html
""")
    (tmp_path / "recipes.yaml").write_text("""
recipes:
  # Nauvis recipes
  mineralized-water:
    ingredients:
      water: 100
    products:
      mineralized-water: 100
    crafting_time: 5.0
    machine: chemical-plant
    surface: nauvis
  mineral-sludge:
    ingredients:
      mineralized-water: 10
    products:
      mineral-sludge: 1
    crafting_time: 10.0
    machine: chemical-plant
    surface: nauvis
  iron-ore:
    ingredients:
      mineral-sludge: 1
    products:
      iron-ore: 1
    crafting_time: 10.0
    machine: centrifuge
    surface: nauvis
  iron-plate:
    ingredients:
      iron-ore: 1
    products:
      iron-plate: 1
    crafting_time: 3.2
    machine: assembler-1
    surface: nauvis
  automation-science-pack:
    ingredients:
      iron-plate: 1
    products:
      automation-science-pack: 1
    crafting_time: 5.0
    machine: assembler-1
    surface: nauvis
  # Gleba recipes
  biochamber:
    ingredients:
      nutrients: 10
    products:
      biochamber: 1
    crafting_time: 10.0
    machine: assembler-1
    surface: gleba
  agricultural-science-pack:
    ingredients:
      nutrients: 5
      biochamber: 1
    products:
      agricultural-science-pack: 1
    crafting_time: 12.0
    machine: assembler-1
    surface: gleba
""")
    (tmp_path / "tech_tree.yaml").write_text("""
tiers:
  - name: Automation Science
    target_hours: 3
    science_packs:
      automation-science-pack: 100
    unlocks: []
  - name: Agricultural Science
    target_hours: 8
    science_packs:
      automation-science-pack: 200
      agricultural-science-pack: 200
    unlocks: []
""")
    return tmp_path


# ── Tests: Full Pipeline ──────────────────────────────────────────────────────

class TestFullPipeline:
    """End-to-end tests: YAML → loader → engine → reporter."""

    def test_minimal_pipeline_produces_report(self, minimal_data_dir, tmp_path):
        """Full pipeline with minimal data produces valid HTML report."""
        data = load_data(str(minimal_data_dir))
        results = run_simulation(data)
        output = str(tmp_path / "report.html")
        generate_report(results, output)

        # Report file exists and contains expected content
        assert Path(output).exists()
        content = Path(output).read_text(encoding="utf-8")
        assert "<html" in content.lower()
        assert "Automation Science" in content
        assert "FactoryBoy" in content

    def test_minimal_pipeline_tier_result_structure(self, minimal_data_dir):
        """Verify TierResult has all expected fields populated."""
        data = load_data(str(minimal_data_dir))
        results = run_simulation(data)

        assert len(results) == 1
        tier = results[0]

        # Structure checks
        assert tier.tier_name == "Automation Science"
        assert tier.target_hours == pytest.approx(3.0)
        assert tier.simulated_hours >= tier.target_hours
        assert tier.total_machines > 0
        assert len(tier.machine_counts) > 0
        # First tier has no previous tier, so no bottlenecks
        assert tier.bottlenecks == []

        # Machine counts are positive integers
        for name, count in tier.machine_counts.items():
            assert isinstance(count, int)
            assert count > 0, f"Machine count for {name} should be positive"

    def test_minimal_pipeline_throughput_chain(self, minimal_data_dir):
        """Verify the entire throughput chain is traced from science pack to root input."""
        from src.graph import RecipeGraph
        from src.solver import solve

        data = load_data(str(minimal_data_dir))
        graph = RecipeGraph.build(data.recipes)

        # Solve for automation-science-pack
        result = solve("automation-science-pack", 1.0, graph, data.config)

        # All items in the chain should have throughput
        assert "automation-science-pack" in result.rates
        assert "iron-plate" in result.rates
        assert "iron-ore" in result.rates
        assert "water" in result.rates

        # Rates should be monotonically increasing toward root
        assert result.rates["water"] > result.rates["iron-ore"] >= result.rates["iron-plate"] >= result.rates["automation-science-pack"]

    def test_multi_tier_pipeline_order_and_bottlenecks(self, multi_tier_data_dir):
        """Multi-tier simulation processes tiers in order and detects bottlenecks."""
        data = load_data(str(multi_tier_data_dir))
        results = run_simulation(data)

        # Three tiers processed
        assert len(results) == 3
        assert results[0].tier_name == "Automation Science"
        assert results[1].tier_name == "Logistic Science"
        assert results[2].tier_name == "Space Science"

        # First tier has no bottlenecks (no previous tier)
        assert results[0].bottlenecks == []

        # Later tiers should have machine counts
        for tier in results:
            assert tier.total_machines > 0
            assert len(tier.machine_counts) > 0

        # Space Science (tier 3) should have more machines than Automation (tier 1)
        assert results[2].total_machines > results[0].total_machines


class TestSpoilageIntegration:
    """Integration tests for spoilage multiplier through the full pipeline."""

    def test_spoilage_applied_in_simulation(self, spoilage_data_dir):
        """Spoilage multiplier increases throughput for perishable items."""
        data = load_data(str(spoilage_data_dir))

        # Verify config has spoilage settings
        assert data.config.spoilage_multiplier == 1.05
        assert "nutrients" in data.config.perishable_items
        assert "biochamber" in data.config.perishable_items

        results = run_simulation(data)
        assert len(results) == 1

        # Simulation should complete without error
        tier = results[0]
        assert tier.total_machines > 0
        assert tier.tier_name == "Agricultural Science"

    def test_spoilage_increases_machine_count(self, tmp_path):
        """Compare simulation with and without spoilage to verify impact."""
        # Create base data without spoilage
        (tmp_path / "config.yaml").write_text("""
root_input: nutrients
root_input_rate: 1000
machine_speeds:
  assembler-1: 0.5
bottleneck_threshold: 20
machine_budget:
  gleba:
    early: 500
    mid: 500
    late: 500
default_target_hours:
  early: 3
  mid: 9
  late: 20
spoilage_multiplier: 1.0
perishable_items:
  - nutrients
report_output: reports/latest.html
""")
        (tmp_path / "recipes.yaml").write_text("""
recipes:
  biochamber:
    ingredients:
      nutrients: 10
    products:
      biochamber: 1
    crafting_time: 10.0
    machine: assembler-1
  science-pack:
    ingredients:
      nutrients: 5
      biochamber: 1
    products:
      science-pack: 1
    crafting_time: 12.0
    machine: assembler-1
""")
        (tmp_path / "tech_tree.yaml").write_text("""
tiers:
  - name: Test Tier
    target_hours: 5
    science_packs:
      science-pack: 500
    unlocks: []
""")

        # Run without spoilage
        data_no_spoilage = load_data(str(tmp_path))
        results_no_spoilage = run_simulation(data_no_spoilage)

        # Now enable spoilage
        (tmp_path / "config.yaml").write_text("""
root_input: nutrients
root_input_rate: 1000
machine_speeds:
  assembler-1: 0.5
bottleneck_threshold: 20
machine_budget:
  gleba:
    early: 500
    mid: 500
    late: 500
default_target_hours:
  early: 3
  mid: 9
  late: 20
spoilage_multiplier: 1.10
perishable_items:
  - nutrients
report_output: reports/latest.html
""")

        data_with_spoilage = load_data(str(tmp_path))
        results_with_spoilage = run_simulation(data_with_spoilage)

        # Spoilage should increase total machines needed
        assert results_with_spoilage[0].total_machines >= results_no_spoilage[0].total_machines


class TestMultiSurfaceIntegration:
    """Integration tests for multi-surface simulation."""

    def test_multi_surface_budget_tracking(self, multi_surface_data_dir):
        """Simulation correctly handles recipes on different surfaces."""
        data = load_data(str(multi_surface_data_dir))
        results = run_simulation(data)

        assert len(results) == 2

        # Tier 1 (Automation) only uses nauvis recipes
        tier1 = results[0]
        assert tier1.total_machines > 0

        # Tier 2 (Agricultural) uses both nauvis and gleba recipes
        tier2 = results[1]
        assert tier2.total_machines > 0
        # Tier 2 should have more machines (more science packs + more surfaces)
        assert tier2.total_machines > tier1.total_machines

    def test_multi_surface_report_generation(self, multi_surface_data_dir, tmp_path):
        """Full pipeline with multi-surface data produces valid report."""
        data = load_data(str(multi_surface_data_dir))
        results = run_simulation(data)
        output = str(tmp_path / "multi_surface_report.html")
        generate_report(results, output)

        assert Path(output).exists()
        content = Path(output).read_text(encoding="utf-8")
        assert "Automation Science" in content
        assert "Agricultural Science" in content


class TestOverBudgetIntegration:
    """Integration tests for budget scaling."""

    def test_tight_budget_scales_simulated_hours(self, tmp_path):
        """When machine budget is tight, simulated_hours exceeds target_hours."""
        (tmp_path / "config.yaml").write_text("""
root_input: water
root_input_rate: 1000
machine_speeds:
  assembler-1: 0.5
  stone-furnace: 1.0
bottleneck_threshold: 20
machine_budget:
  nauvis:
    early: 2
    mid: 2
    late: 2
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
        (tmp_path / "recipes.yaml").write_text("""
recipes:
  iron-ore:
    ingredients:
      water: 5
    products:
      iron-ore: 1
    crafting_time: 5.0
    machine: assembler-1
  iron-plate:
    ingredients:
      iron-ore: 1
    products:
      iron-plate: 1
    crafting_time: 3.2
    machine: stone-furnace
  science-pack:
    ingredients:
      iron-plate: 2
    products:
      science-pack: 1
    crafting_time: 5.0
    machine: assembler-1
""")
        (tmp_path / "tech_tree.yaml").write_text("""
tiers:
  - name: Test Tier
    target_hours: 3
    science_packs:
      science-pack: 1000
    unlocks: []
""")

        data = load_data(str(tmp_path))
        results = run_simulation(data)

        assert len(results) == 1
        tier = results[0]
        # With only 2 machines budget, simulated hours should exceed target
        assert tier.simulated_hours > tier.target_hours
        # Total machines required should exceed budget
        assert tier.total_machines > 2


class TestComparisonReportIntegration:
    """Integration tests for comparison reports."""

    def test_comparison_report_full_pipeline(self, minimal_data_dir, tmp_path):
        """Generate comparison report from two different data directories."""
        # Load base data
        data_a = load_data(str(minimal_data_dir))
        results_a = run_simulation(data_a)

        # Create modified data with higher machine speeds
        (minimal_data_dir / "config.yaml").write_text("""
root_input: water
root_input_rate: 1000
machine_speeds:
  assembler-1: 1.0
  stone-furnace: 2.0
  chemical-plant: 2.0
bottleneck_threshold: 20
machine_budget:
  nauvis:
    early: 50
    mid: 200
    late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
        data_b = load_data(str(minimal_data_dir))
        results_b = run_simulation(data_b)

        # Generate comparison report
        output = str(tmp_path / "comparison.html")
        generate_comparison_report(results_a, results_b, output, "Slow Machines", "Fast Machines")

        assert Path(output).exists()
        content = Path(output).read_text(encoding="utf-8")
        assert "Slow Machines" in content
        assert "Fast Machines" in content

        # Faster machines should require fewer machines
        assert results_b[0].total_machines <= results_a[0].total_machines


class TestEdgeCases:
    """Integration tests for edge cases."""

    def test_empty_tiers_list(self, tmp_path):
        """Simulation with no tiers returns empty results."""
        (tmp_path / "config.yaml").write_text("""
root_input: water
root_input_rate: 1000
machine_speeds:
  assembler-1: 0.5
bottleneck_threshold: 20
machine_budget:
  nauvis:
    early: 50
    mid: 200
    late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
        (tmp_path / "recipes.yaml").write_text("recipes: {}")
        (tmp_path / "tech_tree.yaml").write_text("tiers: []")

        data = load_data(str(tmp_path))
        results = run_simulation(data)
        assert results == []

    def test_tier_with_no_target_hours_uses_default(self, tmp_path):
        """Tier without target_hours falls back to config default."""
        (tmp_path / "config.yaml").write_text("""
root_input: water
root_input_rate: 1000
machine_speeds:
  assembler-1: 0.5
bottleneck_threshold: 20
machine_budget:
  nauvis:
    early: 50
    mid: 200
    late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
        (tmp_path / "recipes.yaml").write_text("""
recipes:
  science-pack:
    ingredients:
      water: 1
    products:
      science-pack: 1
    crafting_time: 1.0
    machine: assembler-1
""")
        (tmp_path / "tech_tree.yaml").write_text("""
tiers:
  - name: No Hours Tier
    science_packs:
      science-pack: 100
    unlocks: []
""")

        data = load_data(str(tmp_path))
        results = run_simulation(data)

        assert len(results) == 1
        # Tier index 0 -> "early" stage -> default 3 hours
        assert results[0].target_hours == pytest.approx(3.0)

    def test_recipe_with_multiple_products(self, tmp_path):
        """Recipes that produce multiple items are handled correctly."""
        (tmp_path / "config.yaml").write_text("""
root_input: water
root_input_rate: 1000
machine_speeds:
  centrifuge: 0.75
bottleneck_threshold: 20
machine_budget:
  nauvis:
    early: 50
    mid: 200
    late: 800
default_target_hours:
  early: 3
  mid: 9
  late: 20
report_output: reports/latest.html
""")
        (tmp_path / "recipes.yaml").write_text("""
recipes:
  ore-split:
    ingredients:
      water: 10
    products:
      iron-ore: 2
      copper-ore: 1
    crafting_time: 5.0
    machine: centrifuge
""")
        (tmp_path / "tech_tree.yaml").write_text("""
tiers:
  - name: Ore Tier
    target_hours: 3
    science_packs:
      iron-ore: 100
    unlocks: []
""")

        data = load_data(str(tmp_path))
        results = run_simulation(data)

        assert len(results) == 1
        assert results[0].total_machines > 0
        # The recipe should be counted once even though it produces multiple items
        assert "ore-split" in results[0].machine_counts


class TestReportContent:
    """Integration tests verifying report content accuracy."""

    def test_report_contains_all_tier_names(self, multi_tier_data_dir, tmp_path):
        """Report HTML contains all tier names."""
        data = load_data(str(multi_tier_data_dir))
        results = run_simulation(data)
        output = str(tmp_path / "report.html")
        generate_report(results, output)

        content = Path(output).read_text(encoding="utf-8")
        for tier_result in results:
            assert tier_result.tier_name in content

    def test_report_contains_machine_count_data(self, minimal_data_dir, tmp_path):
        """Report contains machine count information."""
        data = load_data(str(minimal_data_dir))
        results = run_simulation(data)
        output = str(tmp_path / "report.html")
        generate_report(results, output)

        content = Path(output).read_text(encoding="utf-8")
        # Should contain recipe names from machine counts
        for recipe_name in results[0].machine_counts:
            assert recipe_name in content

    def test_report_contains_bottleneck_section(self, multi_tier_data_dir, tmp_path):
        """Report contains bottleneck table section."""
        data = load_data(str(multi_tier_data_dir))
        results = run_simulation(data)
        output = str(tmp_path / "report.html")
        generate_report(results, output)

        content = Path(output).read_text(encoding="utf-8")
        assert "Bottleneck" in content
        assert "<table>" in content.lower() or "table" in content.lower()

    def test_report_is_valid_html_structure(self, minimal_data_dir, tmp_path):
        """Report has valid HTML structure."""
        data = load_data(str(minimal_data_dir))
        results = run_simulation(data)
        output = str(tmp_path / "report.html")
        generate_report(results, output)

        content = Path(output).read_text(encoding="utf-8")
        assert content.strip().startswith("<!DOCTYPE html>")
        assert "</html>" in content.lower()
        assert "<head>" in content.lower()
        assert "</head>" in content.lower()
        assert "<body>" in content.lower()
        assert "</body>" in content.lower()
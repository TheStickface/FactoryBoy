import subprocess
import sys
from pathlib import Path


def test_cli_help_exits_cleanly():
    result = subprocess.run(
        [sys.executable, "factoryboy.py", "--help"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0
    assert "run" in result.stdout
    assert "compare" in result.stdout


def test_cli_run_with_data_dir(tmp_path):
    # Write minimal valid data files
    (tmp_path / "config.yaml").write_text("""
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
    (tmp_path / "recipes.yaml").write_text("""
recipes:
  test-pack:
    ingredients:
      water: 1
    products:
      test-pack: 1
    crafting_time: 1.0
    machine: assembler-1
""")
    (tmp_path / "tech_tree.yaml").write_text("""
tiers:
  - name: Test Tier
    target_hours: 2
    science_packs:
      test-pack: 50
    unlocks: []
""")
    out_path = tmp_path / "out.html"
    result = subprocess.run(
        [sys.executable, "factoryboy.py", "run",
         "--data", str(tmp_path), "--output", str(out_path),
         "--no-open"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0
    assert out_path.exists()

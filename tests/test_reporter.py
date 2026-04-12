import pytest
from pathlib import Path
from src.engine import run_simulation, TierResult
from src.reporter import generate_report, generate_comparison_report


def test_generate_report_creates_html_file(simple_game_data, tmp_path):
    results = run_simulation(simple_game_data)
    out = str(tmp_path / "report.html")
    generate_report(results, out)
    assert Path(out).exists()
    content = Path(out).read_text(encoding="utf-8")
    assert "<html" in content.lower()


def test_report_contains_tier_name(simple_game_data, tmp_path):
    results = run_simulation(simple_game_data)
    out = str(tmp_path / "report.html")
    generate_report(results, out)
    content = Path(out).read_text(encoding="utf-8")
    assert "Automation Science" in content


def test_report_contains_plotly(simple_game_data, tmp_path):
    results = run_simulation(simple_game_data)
    out = str(tmp_path / "report.html")
    generate_report(results, out)
    content = Path(out).read_text(encoding="utf-8")
    assert "plotly" in content.lower()


def test_report_contains_bottleneck_table(simple_game_data, tmp_path):
    results = run_simulation(simple_game_data)
    out = str(tmp_path / "report.html")
    generate_report(results, out)
    content = Path(out).read_text(encoding="utf-8")
    assert "Bottleneck" in content


def test_comparison_report_contains_both_labels(simple_game_data, tmp_path):
    results = run_simulation(simple_game_data)
    out = str(tmp_path / "compare.html")
    generate_comparison_report(results, results, out, label_a="Baseline", label_b="Modified")
    content = Path(out).read_text(encoding="utf-8")
    assert "Baseline" in content
    assert "Modified" in content

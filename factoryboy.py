#!/usr/bin/env python3
"""FactoryBoy — Seablock modpack playtest simulation tool.

Usage:
  python factoryboy.py run [--data DATA_DIR] [--output OUTPUT_PATH]
  python factoryboy.py compare DIR_A DIR_B [--output OUTPUT_PATH] [--label-a LABEL] [--label-b LABEL]
"""
import argparse
import sys
import webbrowser
from pathlib import Path

from src.loader import load_data
from src.engine import run_simulation
from src.reporter import generate_report, generate_comparison_report


def cmd_run(args) -> int:
    data = load_data(args.data)
    results = run_simulation(data)
    output = args.output or data.config.report_output
    generate_report(results, output)
    print(f"Report written to: {output}")
    if not args.no_open:
        webbrowser.open(Path(output).resolve().as_uri())
    return 0


def cmd_compare(args) -> int:
    data_a = load_data(args.dir_a)
    data_b = load_data(args.dir_b)
    results_a = run_simulation(data_a)
    results_b = run_simulation(data_b)
    output = args.output or "reports/comparison.html"
    generate_comparison_report(
        results_a, results_b, output,
        label_a=args.label_a,
        label_b=args.label_b,
    )
    print(f"Comparison report written to: {output}")
    if not args.no_open:
        webbrowser.open(Path(output).resolve().as_uri())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="factoryboy",
        description="Seablock modpack playtest simulation tool",
    )
    parser.add_argument("--no-open", action="store_true", help="Don't open report in browser")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run simulation and generate report")
    run_parser.add_argument("--data", default="data", help="Data directory (default: data/)")
    run_parser.add_argument("--output", default=None, help="Output HTML path (overrides config)")
    run_parser.add_argument("--no-open", action="store_true", help="Don't open report in browser")

    cmp_parser = sub.add_parser("compare", help="Compare two data directories")
    cmp_parser.add_argument("dir_a", help="Baseline data directory")
    cmp_parser.add_argument("dir_b", help="Modified data directory")
    cmp_parser.add_argument("--output", default=None, help="Output HTML path")
    cmp_parser.add_argument("--label-a", default="Baseline", help="Label for dir_a")
    cmp_parser.add_argument("--label-b", default="Modified", help="Label for dir_b")
    cmp_parser.add_argument("--no-open", action="store_true", help="Don't open report in browser")

    args = parser.parse_args()
    if args.command == "run":
        return cmd_run(args)
    if args.command == "compare":
        return cmd_compare(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())

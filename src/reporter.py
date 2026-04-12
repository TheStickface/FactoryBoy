# src/reporter.py
from __future__ import annotations
from pathlib import Path
import plotly.graph_objects as go
from src.engine import TierResult


def generate_report(results: list[TierResult], output_path: str) -> None:
    """Generate a standalone HTML report for a single simulation run."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    html = _build_html(results, comparison=None)
    Path(output_path).write_text(html, encoding="utf-8")


def generate_comparison_report(
    base_results: list[TierResult],
    mod_results: list[TierResult],
    output_path: str,
    label_a: str = "Baseline",
    label_b: str = "Modified",
) -> None:
    """Generate a side-by-side comparison HTML report."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    html = _build_html(base_results, comparison=(mod_results, label_a, label_b))
    Path(output_path).write_text(html, encoding="utf-8")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_html(results: list[TierResult], comparison) -> str:
    sections: list[str] = []
    include_js = True  # embed plotly.js once

    # Section 1: Tier Timeline
    fig = _timeline_figure(results, label="")
    if comparison is not None:
        mod_results, label_a, label_b = comparison
        fig_mod = _timeline_figure(mod_results, label=label_b)
        sections.append(f"<h2>Tier Timeline — {label_a}</h2>")
        sections.append(fig.to_html(full_html=False, include_plotlyjs=include_js))
        include_js = False
        sections.append(f"<h2>Tier Timeline — {label_b}</h2>")
        sections.append(fig_mod.to_html(full_html=False, include_plotlyjs=False))
    else:
        sections.append("<h2>Tier Timeline</h2>")
        sections.append(fig.to_html(full_html=False, include_plotlyjs=include_js))
        include_js = False

    # Section 2: Machine Counts per tier
    for result in results:
        fig_m = _machine_counts_figure(result)
        sections.append(f"<h2>Machine Counts — {result.tier_name}</h2>")
        sections.append(fig_m.to_html(full_html=False, include_plotlyjs=False))

    if comparison is not None:
        mod_results, label_a, label_b = comparison
        for result in mod_results:
            fig_m = _machine_counts_figure(result)
            sections.append(f"<h2>Machine Counts ({label_b}) — {result.tier_name}</h2>")
            sections.append(fig_m.to_html(full_html=False, include_plotlyjs=False))

    # Section 3: Bottleneck Table
    sections.append("<h2>Bottleneck Table</h2>")
    sections.append(_bottleneck_table(results))

    if comparison is not None:
        mod_results, label_a, label_b = comparison
        sections.append(f"<h2>Bottleneck Table — {label_b}</h2>")
        sections.append(_bottleneck_table(mod_results))

    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>FactoryBoy Simulation Report</title>
<style>
  body {{ font-family: sans-serif; margin: 2em; background: #1a1a2e; color: #e0e0e0; }}
  h1 {{ color: #f0a500; }}
  h2 {{ color: #a0c4ff; border-bottom: 1px solid #333; padding-bottom: 0.3em; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 2em; }}
  th, td {{ border: 1px solid #444; padding: 0.5em 1em; text-align: left; }}
  th {{ background: #2a2a4a; }}
  tr.bottleneck {{ background: #4a1a1a; }}
  tr.bottleneck td:last-child {{ color: #ff6b6b; font-weight: bold; }}
</style>
</head>
<body>
<h1>FactoryBoy Simulation Report</h1>
{body}
</body>
</html>"""


def _timeline_figure(results: list[TierResult], label: str) -> go.Figure:
    names = [r.tier_name for r in results]
    target = [r.target_hours for r in results]
    simulated = [r.simulated_hours for r in results]
    title = f"Tier Timeline{' — ' + label if label else ''}"
    fig = go.Figure(data=[
        go.Bar(name="Target Hours", x=names, y=target, marker_color="steelblue"),
        go.Bar(name="Simulated Hours", x=names, y=simulated, marker_color="darkorange"),
    ])
    fig.update_layout(
        barmode="group",
        title=title,
        xaxis_title="Science Tier",
        yaxis_title="Hours",
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#1a1a2e",
        font_color="#e0e0e0",
    )
    return fig


def _machine_counts_figure(result: TierResult) -> go.Figure:
    sorted_items = sorted(result.machine_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    names = [item[0] for item in sorted_items]
    counts = [item[1] for item in sorted_items]
    fig = go.Figure(data=[go.Bar(x=names, y=counts, marker_color="teal")])
    fig.update_layout(
        title=f"Machine Counts — {result.tier_name}",
        xaxis_title="Recipe",
        yaxis_title="Machines Required",
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#1a1a2e",
        font_color="#e0e0e0",
    )
    return fig


def _bottleneck_table(results: list[TierResult]) -> str:
    rows: list[str] = []
    for result in results:
        for b in result.bottlenecks:
            flag = "⚠" if b.delta >= 20 else ""
            row_class = ' class="bottleneck"' if flag else ""
            rows.append(
                f'<tr{row_class}>'
                f"<td>{result.tier_name}</td>"
                f"<td>{b.recipe_name}</td>"
                f"<td>{b.machines_required}</td>"
                f"<td>+{b.delta}</td>"
                f"<td>{flag}</td>"
                f"</tr>"
            )
    if not rows:
        rows.append('<tr><td colspan="5">No bottlenecks detected.</td></tr>')
    header = (
        "<table>"
        "<thead><tr>"
        "<th>Tier</th><th>Recipe</th><th>Machines Required</th>"
        "<th>Delta from Previous</th><th>Flag</th>"
        "</tr></thead><tbody>"
    )
    return header + "\n".join(rows) + "</tbody></table>"

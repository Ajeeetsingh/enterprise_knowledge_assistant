"""HTML dashboard for benchmark visualization and regression analysis."""

from __future__ import annotations

import html
import json
from pathlib import Path

from app.evaluation.history import (
    compare_reports,
    list_benchmark_runs,
    load_best_run,
    load_previous_run,
)
from app.evaluation.schemas import BenchmarkReport


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _load_history_reports(
    results_dir: Path,
    *,
    limit: int = 12,
) -> list[dict]:
    reports: list[dict] = []
    for path in list_benchmark_runs(results_dir)[:limit]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            reports.append(payload)
        except (json.JSONDecodeError, OSError):
            continue
    return list(reversed(reports))


def _metric_card(label: str, value: str, *, css_class: str = "") -> str:
    return (
        f'<div class="metric-card {css_class}">'
        f'<div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-value">{html.escape(value)}</div>'
        f"</div>"
    )


def _bar_chart(title: str, labels: list[str], values: list[int], *, color: str) -> str:
    if not values or max(values) == 0:
        max_value = 1
    else:
        max_value = max(values)
    bars = []
    for label, value in zip(labels, values, strict=True):
        width = max(4, int((value / max_value) * 100))
        bars.append(
            f'<div class="bar-row">'
            f'<div class="bar-label">{html.escape(label)}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{width}%;background:{color}"></div></div>'
            f'<div class="bar-value">{value}</div>'
            f"</div>"
        )
    return (
        f'<section class="panel"><h2>{html.escape(title)}</h2>'
        f'<div class="bar-chart">{"".join(bars)}</div></section>'
    )


def render_benchmark_dashboard(
    report: BenchmarkReport,
    *,
    results_dir: Path | None = None,
) -> str:
    """Render a self-contained HTML dashboard for one benchmark run."""
    directory = results_dir or Path(report.artifacts_dir or ".").parent
    if not directory.exists():
        directory = Path(__file__).resolve().parents[2] / "evaluation_results"

    history = _load_history_reports(directory)
    previous = load_previous_run(directory)
    best = load_best_run(directory)

    regression_rows = ""
    if previous is not None:
        comparison = compare_reports(previous, report, baseline_label="Previous", comparison_label="Current")
        for delta in comparison.deltas:
            sign = "+" if delta.delta >= 0 else ""
            if "latency" in delta.metric:
                formatted = f"{sign}{delta.delta:.1f} ms"
                before = f"{delta.before:.1f} ms"
                after = f"{delta.after:.1f} ms"
            elif "recall" in delta.metric or "accuracy" in delta.metric or delta.metric.endswith("_pct"):
                formatted = f"{sign}{delta.delta * 100:.1f}%"
                before = _pct(delta.before)
                after = _pct(delta.after)
            else:
                formatted = f"{sign}{delta.delta:.3f}"
                before = f"{delta.before:.3f}"
                after = f"{delta.after:.3f}"
            regression_rows += (
                "<tr>"
                f"<td>{html.escape(delta.metric)}</td>"
                f"<td>{before}</td>"
                f"<td>{after}</td>"
                f'<td class="{"positive" if delta.delta >= 0 else "negative"}">{formatted}</td>'
                "</tr>"
            )

    failure_labels = [item.failure_type for item in report.failure_type_analysis]
    failure_counts = [item.count for item in report.failure_type_analysis]

    metrics = report.metrics
    cards = [
        _metric_card("Recall@1", _pct(metrics.recall_at_1), css_class="primary"),
        _metric_card("Recall@3", _pct(metrics.recall_at_3)),
        _metric_card("MRR", f"{metrics.mrr:.3f}"),
        _metric_card("Answer Accuracy", _pct(metrics.answer_accuracy), css_class="primary"),
        _metric_card("Citation Accuracy", _pct(metrics.citation_accuracy)),
        _metric_card("Context Precision", _pct(metrics.context_precision), css_class="primary"),
        _metric_card("Hallucination Rate", _pct(metrics.hallucination_rate), css_class="warn"),
        _metric_card("Avg Latency", f"{metrics.avg_total_latency_ms:.1f} ms"),
    ]

    history_labels = json.dumps([
        item.get("started_at", "")[:10] for item in history
    ])
    history_recall = json.dumps([
        item.get("metrics", {}).get("recall_at_1", 0) * 100 for item in history
    ])
    history_answer = json.dumps([
        item.get("metrics", {}).get("answer_accuracy", 0) * 100 for item in history
    ])
    history_context = json.dumps([
        item.get("metrics", {}).get("context_precision", 0) * 100 for item in history
    ])

    question_rows = ""
    for result in report.question_results:
        status = "pass" if not result.failure_types else "fail"
        failures = ", ".join(failure.value for failure in result.failure_types) or "—"
        artifact_link = ""
        if result.artifact_path:
            artifact_name = Path(result.artifact_path).name
            artifact_link = f'<a href="artifacts/{report.run_id}/{artifact_name}">{artifact_name}</a>'
        question_rows += (
            f'<tr class="{status}">'
            f"<td>{html.escape(result.case_id)}</td>"
            f"<td>{html.escape(result.document_type)}</td>"
            f"<td>{html.escape(result.query_category)}</td>"
            f"<td>{html.escape(result.difficulty)}</td>"
            f"<td>{html.escape(str(result.retrieval.expected_rank or '—'))}</td>"
            f"<td>{_pct(1.0 if result.answer.passed else 0.0)}</td>"
            f"<td>{result.context_precision:.2f}</td>"
            f"<td>{'yes' if result.hallucination_detected else 'no'}</td>"
            f"<td>{html.escape(failures)}</td>"
            f"<td>{artifact_link}</td>"
            f"</tr>"
        )

    breakdown_html = ""
    if report.dataset_breakdown is not None:
        for title, mapping in (
            ("Document Types", report.dataset_breakdown.by_document_type),
            ("Difficulty", report.dataset_breakdown.by_difficulty),
            ("Query Categories", report.dataset_breakdown.by_query_category),
        ):
            labels = list(mapping.keys())
            values = list(mapping.values())
            breakdown_html += _bar_chart(title, labels, values, color="#3b82f6")

    best_note = ""
    if best is not None:
        best_note = (
            f"<p class='subtle'>Best run: {best.run_id[:8]} "
            f"(Recall@1 {_pct(best.metrics.recall_at_1)}, "
            f"Answer {_pct(best.metrics.answer_accuracy)})</p>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>RAG Benchmark Dashboard — {html.escape(report.run_id[:8])}</title>
  <style>
    :root {{
      --bg: #0b1020;
      --panel: #141b2d;
      --text: #e5e7eb;
      --muted: #94a3b8;
      --primary: #3b82f6;
      --positive: #22c55e;
      --negative: #ef4444;
      --warn: #f59e0b;
      --border: #243049;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, Segoe UI, sans-serif;
      background: linear-gradient(180deg, #0b1020 0%, #111827 100%);
      color: var(--text);
      padding: 24px;
    }}
    h1, h2 {{ margin: 0 0 12px; }}
    .header, .metrics, .grid, .panel, table {{ margin-bottom: 24px; }}
    .subtle {{ color: var(--muted); }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
    }}
    .metric-card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
    }}
    .metric-card.primary .metric-value {{ color: #93c5fd; }}
    .metric-card.warn .metric-value {{ color: var(--warn); }}
    .metric-label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .metric-value {{ font-size: 28px; font-weight: 700; margin-top: 8px; }}
    .grid {{
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 16px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
    }}
    canvas {{ width: 100% !important; height: 260px !important; }}
    .bar-row {{
      display: grid;
      grid-template-columns: 140px 1fr 40px;
      gap: 8px;
      align-items: center;
      margin-bottom: 8px;
      font-size: 13px;
    }}
    .bar-track {{
      background: #1f2937;
      border-radius: 999px;
      height: 10px;
      overflow: hidden;
    }}
    .bar-fill {{ height: 100%; border-radius: 999px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      font-size: 13px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    tr.pass td:first-child {{ border-left: 3px solid var(--positive); }}
    tr.fail td:first-child {{ border-left: 3px solid var(--negative); }}
    .positive {{ color: var(--positive); }}
    .negative {{ color: var(--negative); }}
    a {{ color: #93c5fd; }}
    @media (max-width: 960px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Enterprise RAG Benchmark Dashboard</h1>
    <p class="subtle">
      Run {html.escape(report.run_id)} · Dataset {html.escape(report.dataset_version)} ·
      {metrics.case_count} cases · {html.escape(report.started_at.isoformat()[:19])}
    </p>
    {best_note}
  </div>

  <div class="metrics">{''.join(cards)}</div>

  <div class="grid">
    <section class="panel">
      <h2>Metric Trends</h2>
      <canvas id="trendChart"></canvas>
    </section>
    {_bar_chart("Failure Distribution", failure_labels, failure_counts, color="#ef4444")}
  </div>

  <div class="grid">
    {breakdown_html}
    <section class="panel">
      <h2>Regression vs Previous Run</h2>
      <table>
        <thead><tr><th>Metric</th><th>Previous</th><th>Current</th><th>Delta</th></tr></thead>
        <tbody>{regression_rows or '<tr><td colspan="4">No previous run available.</td></tr>'}</tbody>
      </table>
    </section>
  </div>

  <section class="panel">
    <h2>Per-Question Results</h2>
    <table>
      <thead>
        <tr>
          <th>Case</th><th>Doc Type</th><th>Query Category</th><th>Difficulty</th>
          <th>Rank</th><th>Answer</th><th>Context Prec.</th><th>Hallucination</th>
          <th>Failures</th><th>Artifact</th>
        </tr>
      </thead>
      <tbody>{question_rows}</tbody>
    </table>
  </section>

  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    const labels = {history_labels};
    const recallData = {history_recall};
    const answerData = {history_answer};
    const contextData = {history_context};
    const ctx = document.getElementById('trendChart');
    if (ctx && labels.length > 0) {{
      new Chart(ctx, {{
        type: 'line',
        data: {{
          labels,
          datasets: [
            {{ label: 'Recall@1 %', data: recallData, borderColor: '#3b82f6', tension: 0.25 }},
            {{ label: 'Answer Accuracy %', data: answerData, borderColor: '#22c55e', tension: 0.25 }},
            {{ label: 'Context Precision %', data: contextData, borderColor: '#f59e0b', tension: 0.25 }},
          ],
        }},
        options: {{
          responsive: true,
          plugins: {{ legend: {{ labels: {{ color: '#e5e7eb' }} }} }},
          scales: {{
            x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#243049' }} }},
            y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#243049' }}, min: 0, max: 100 }},
          }},
        }},
      }});
    }}
  </script>
</body>
</html>"""


def export_html_dashboard(
    report: BenchmarkReport,
    output_path: str | Path,
    *,
    results_dir: Path | None = None,
) -> Path:
    """Write the HTML dashboard to disk."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_benchmark_dashboard(report, results_dir=results_dir),
        encoding="utf-8",
    )
    return path

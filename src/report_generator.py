
"""Generate an HTML report for SimuNexa CAE Copilot."""

import html
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.engineering_recommendations import generate_recommendations


def generate_report(
    diagnostics: dict[str, Any],
    output_path: str | Path,
    residual_analysis: dict[str, Any] | None = None,
    mesh_analysis: dict[str, Any] | None = None,
    mesh_thresholds: dict[str, float] | None = None,
) -> Path:
    """Generate an HTML CFD diagnostics report with recommendations."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    def escape(value: Any) -> str:
        return html.escape(str(value), quote=True)

    def fmt(value: Any) -> str:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f"{value:.6g}"
        return str(value) if value is not None else "Not available"

    def yes_no_unknown(value: Any) -> str:
        if value is True:
            return "Yes"
        if value is False:
            return "No"
        return "Unknown"

    fatal = bool(diagnostics.get("fatal_error"))
    completed = bool(diagnostics.get("solver_completed"))

    if fatal:
        status = "FATAL ERROR"
        status_color = "#b42318"
    elif completed:
        status = "COMPLETION MARKER FOUND"
        status_color = "#18794e"
    else:
        status = "COMPLETION NOT CONFIRMED"
        status_color = "#9a6700"

    summary_items = diagnostics.get("summary", [])
    warnings = diagnostics.get("warnings", [])
    errors = diagnostics.get("errors", [])
    courant_values = diagnostics.get("courant_max", [])

    valid_courant = []
    for value in courant_values:
        try:
            number = float(value)
            if math.isfinite(number) and number >= 0:
                valid_courant.append(number)
        except (TypeError, ValueError):
            continue

    threshold = diagnostics.get("courant_threshold")
    try:
        threshold = float(threshold)
        if not math.isfinite(threshold) or threshold < 0:
            threshold = None
    except (TypeError, ValueError):
        threshold = None

    exceedances = (
        sum(value > threshold for value in valid_courant)
        if threshold is not None
        else diagnostics.get("courant_exceedances", "Not available")
    )

    max_courant = max(valid_courant) if valid_courant else None
    final_courant = valid_courant[-1] if valid_courant else None

    def list_html(items: list[Any], empty_message: str) -> str:
        if not items:
            return f"<li>{escape(empty_message)}</li>"
        return "".join(f"<li>{escape(item)}</li>" for item in items)

    # Prepare residual summary table.
    residuals = (
        residual_analysis.get("residuals", {})
        if residual_analysis
        else {}
    )

    residual_rows = []

    for variable, metrics in sorted(residuals.items()):
        ratio = metrics.get("reduction_ratio")
        ratio_text = "Undefined" if ratio is None else fmt(ratio)

        residual_rows.append(
            "<tr>"
            f"<td>{escape(variable)}</td>"
            f"<td>{escape(fmt(metrics.get('initial')))}</td>"
            f"<td>{escape(fmt(metrics.get('final')))}</td>"
            f"<td>{escape(ratio_text)}</td>"
            f"<td>{escape(yes_no_unknown(metrics.get('below_tolerance')))}</td>"
            f"<td>{escape(yes_no_unknown(metrics.get('decreasing_overall')))}</td>"
            f"<td>{escape(yes_no_unknown(metrics.get('monotonic_decrease')))}</td>"
            f"<td>{escape(fmt(metrics.get('increases_count')))}</td>"
            f"<td>{escape(fmt(metrics.get('sample_count')))}</td>"
            f"<td>{escape(fmt(metrics.get('mean_solver_iterations')))}</td>"
            "</tr>"
        )

    if residual_rows:
        residual_table = (
            "<table><thead><tr>"
            "<th>Variable</th>"
            "<th>Initial residual</th>"
            "<th>Final residual</th>"
            "<th>Final / initial</th>"
            "<th>Below tolerance</th>"
            "<th>Decreasing overall</th>"
            "<th>Monotonic non-increase</th>"
            "<th>Residual increases</th>"
            "<th>Samples</th>"
            "<th>Mean solver iterations</th>"
            "</tr></thead><tbody>"
            + "".join(residual_rows)
            + "</tbody></table>"
        )
    else:
        residual_table = "<p>No residual analysis was supplied.</p>"

    residual_note = (
        residual_analysis.get("note", "")
        if residual_analysis
        else ""
    )

    residual_note_html = (
        f"<p class='explanation'>{escape(residual_note)}</p>"
        if residual_note
        else ""
    )

    # Prepare mesh-quality metrics for the HTML report.
    mesh_metrics = [
        ("OpenFOAM version", "openfoam_version"),
        ("Points", "points"),
        ("Faces", "faces"),
        ("Internal faces", "internal_faces"),
        ("Cells", "cells"),
        ("Boundary patches", "boundary_patches"),
        ("Maximum aspect ratio", "max_aspect_ratio"),
        ("Maximum non-orthogonality", "max_non_orthogonality"),
        ("Average non-orthogonality", "average_non_orthogonality"),
        ("Maximum skewness", "max_skewness"),
        ("Maximum cell openness", "max_cell_openness"),
        ("Mesh OK marker", "mesh_ok"),
        ("End marker", "end_marker"),
    ]

    mesh_rows = []
    if mesh_analysis:
        for label, key in mesh_metrics:
            value = mesh_analysis.get(key)
            if isinstance(value, bool):
                display_value = "Yes" if value else "No"
            else:
                display_value = fmt(value)

            mesh_rows.append(
                f"<tr><td>{escape(label)}</td>"
                f"<td>{escape(display_value)}</td></tr>"
            )

        for item in mesh_analysis.get("summary", []):
            mesh_rows.append(
                f"<tr><td>Finding</td><td>{escape(item)}</td></tr>"
            )

        for item in mesh_analysis.get("failed_checks", []):
            mesh_rows.append(
                f"<tr><td>Failed check</td><td>{escape(item)}</td></tr>"
            )

        for item in mesh_analysis.get("warnings", []):
            mesh_rows.append(
                f"<tr><td>Warning</td><td>{escape(item)}</td></tr>"
            )

    if mesh_rows:
        mesh_table_html = (
            "<table><thead><tr><th>Mesh metric</th><th>Value</th></tr></thead>"
            "<tbody>" + "".join(mesh_rows) + "</tbody></table>"
        )
    else:
        mesh_table_html = (
            "<p>No mesh-quality report was supplied. "
            "Use the --mesh-log option to include checkMesh results.</p>"
        )

    safe_mesh = escape(
        json.dumps(
            mesh_analysis or {},
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    # Generate engineering recommendations.
    recommendations = generate_recommendations(
        diagnostics,
        residual_analysis,
        mesh_analysis,
        mesh_thresholds,
    )

    recommendation_rows = []

    for item in recommendations:
        recommendation_rows.append(
            "<tr>"
            f"<td>{escape(item.get('priority', 'Info'))}</td>"
            f"<td>{escape(item.get('title', ''))}</td>"
            f"<td>{escape(item.get('evidence', ''))}</td>"
            f"<td>{escape(item.get('action', ''))}</td>"
            f"<td>{escape(item.get('limitation', ''))}</td>"
            "</tr>"
        )

    recommendations_html = (
        "<table><thead><tr>"
        "<th>Priority</th>"
        "<th>Finding</th>"
        "<th>Evidence</th>"
        "<th>Recommended action</th>"
        "<th>Limitation</th>"
        "</tr></thead><tbody>"
        + "".join(recommendation_rows)
        + "</tbody></table>"
        if recommendation_rows
        else "<p>No engineering recommendations are available.</p>"
    )

    # Locate residual plots beside the HTML report.
    plot_dir = output.parent / "residual_plots"
    plot_images = []

    if residuals and plot_dir.is_dir():
        for variable in sorted(residuals):
            safe_name = "".join(
                char for char in str(variable)
                if char.isalnum() or char in "_-"
            )
            if not safe_name:
                continue

            image_path = plot_dir / f"residual_{safe_name}.png"
            if not image_path.is_file():
                continue

            relative_image = image_path.relative_to(
                output.parent
            ).as_posix()

            plot_images.append(
                "<figure class='plot-card'>"
                f"<img src='{escape(relative_image)}' "
                f"alt='Residual history for {escape(variable)}'>"
                f"<figcaption>{escape(variable)} residual history</figcaption>"
                "</figure>"
            )

    plots_html = (
        "<div class='plot-grid'>"
        + "".join(plot_images)
        + "</div>"
        if plot_images
        else (
            "<p>No residual plots found. Generate plots in the "
            "'residual_plots' folder to display them here.</p>"
        )
    )

    safe_diagnostics = escape(
        json.dumps(
            diagnostics,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    safe_residuals = escape(
        json.dumps(
            residual_analysis or {},
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    safe_recommendations = escape(
        json.dumps(
            recommendations,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    generated = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    log_file = escape(diagnostics.get("file", "Not specified"))

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SimuNexa CAE Copilot | CFD Diagnostics</title>
<style>
:root {{
  color-scheme: light;
  --navy: #142b4a;
  --border: #d8e0e9;
  --muted: #596579;
  --surface: #f5f8fc;
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: Arial, Helvetica, sans-serif;
  max-width: 1200px;
  margin: 0 auto;
  padding: 28px;
  color: #202938;
  line-height: 1.55;
  background: #fff;
}}
header {{
  padding: 24px;
  color: white;
  background: var(--navy);
  border-radius: 12px;
}}
header h1 {{ margin: 0 0 5px; }}
header p {{ margin: 5px 0; }}
.status {{
  display: inline-block;
  padding: 7px 12px;
  margin-top: 10px;
  color: white;
  border-radius: 5px;
  background: {status_color};
  font-weight: bold;
}}
h2 {{
  margin-top: 30px;
  padding-bottom: 7px;
  border-bottom: 2px solid var(--border);
  color: var(--navy);
}}
.summary-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 14px;
  margin: 18px 0;
}}
.metric {{
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: var(--surface);
}}
.metric .label {{ color: var(--muted); font-size: 0.9em; }}
.metric .value {{
  margin-top: 5px;
  font-size: 1.35em;
  font-weight: bold;
  overflow-wrap: anywhere;
}}
table {{
  display: block;
  width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
  margin: 14px 0 22px;
}}
th, td {{
  border: 1px solid var(--border);
  padding: 10px;
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
}}
th {{ background: var(--surface); }}
.explanation {{
  color: var(--muted);
  font-size: 0.94em;
}}
.plot-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 18px;
}}
.plot-card {{
  min-width: 0;
  margin: 0;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 9px;
}}
.plot-card img {{ display: block; width: 100%; height: auto; }}
.plot-card figcaption {{
  margin-top: 8px;
  text-align: center;
  font-weight: bold;
}}
.note {{
  margin-top: 22px;
  padding: 16px;
  border-left: 5px solid #d99a18;
  background: #fff8e5;
  border-radius: 5px;
}}
pre {{
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  max-height: 520px;
  overflow: auto;
  background: var(--surface);
  padding: 14px;
  border-radius: 7px;
  font-size: 0.85em;
}}
footer {{
  margin-top: 38px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.9em;
}}
@media (max-width: 600px) {{
  body {{ padding: 12px; }}
  header {{ padding: 17px; }}
  .plot-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<header>
  <h1>SimuNexa CAE Copilot</h1>
  <p>CFD Solver Diagnostics Report</p>
  <p class="status">{escape(status)}</p>
</header>

<section>
  <h2>Report information</h2>
  <p><strong>Generated (UTC):</strong> {escape(generated)}</p>
  <p><strong>OpenFOAM log:</strong> {log_file}</p>
</section>

<section>
  <h2>Diagnostic overview</h2>
  <div class="summary-grid">
    <div class="metric">
      <div class="label">Solver completion</div>
      <div class="value">{'Confirmed' if completed else 'Not confirmed'}</div>
    </div>
    <div class="metric">
      <div class="label">Fatal error detected</div>
      <div class="value">{'Yes' if fatal else 'No'}</div>
    </div>
    <div class="metric">
      <div class="label">Maximum Courant number</div>
      <div class="value">{escape(fmt(max_courant))}</div>
    </div>
    <div class="metric">
      <div class="label">Residual records</div>
      <div class="value">{escape(fmt(diagnostics.get('residual_records')))}</div>
    </div>
  </div>
  <ul>{list_html(summary_items, 'No diagnostic summary available.')}</ul>
</section>

<section>
  <h2>Courant numbers</h2>
  <table>
    <thead><tr><th>Metric</th><th>Value</th></tr></thead>
    <tbody>
      <tr><td>Number of valid samples</td><td>{len(valid_courant)}</td></tr>
      <tr><td>Maximum Courant number</td><td>{escape(fmt(max_courant))}</td></tr>
      <tr><td>Final reported Courant number</td><td>{escape(fmt(final_courant))}</td></tr>
      <tr><td>Reporting threshold</td><td>{escape(fmt(threshold))}</td></tr>
      <tr><td>Samples above threshold</td><td>{escape(fmt(exceedances))}</td></tr>
    </tbody>
  </table>
  <p class="explanation">The threshold is a diagnostic flag, not a universal stability limit. Interpret it according to the solver, time scheme, mesh and case settings.</p>
</section>

<section>
  <h2>Warnings</h2>
  <ul>{list_html(warnings, 'No warnings detected by the log parser.')}</ul>
</section>

<section>
  <h2>Errors</h2>
  <ul>{list_html(errors, 'No error messages detected by the log parser.')}</ul>
</section>

<section>
  <h2>Residual analysis</h2>
  {residual_table}
  {residual_note_html}
</section>

<section>
  <h2>Mesh Quality Diagnostics</h2>
  {mesh_table_html}
  <details>
    <summary>Show mesh diagnostics data (JSON)</summary>
    <pre>{safe_mesh}</pre>
  </details>
</section>

<section>
  <h2>Engineering Recommendations</h2>
  <p class="explanation">Recommendations are generated from available log diagnostics and residual metrics. Review them using engineering judgment.</p>
  {recommendations_html}
  <details>
    <summary>Show recommendation data (JSON)</summary>
    <pre>{safe_recommendations}</pre>
  </details>
</section>

<section>
  <h2>Residual convergence plots</h2>
  {plots_html}
</section>

<div class="note">
  <strong>Engineering limitation:</strong>
  A completion marker and low residuals do not independently establish
  convergence or physical accuracy. Review residual histories,
  conservation balances, monitored quantities, mesh independence,
  boundary conditions, and validation against appropriate reference data.
  A high Courant number requires context-specific assessment; it is not
  automatically proof of failure.
</div>

<section>
  <h2>Diagnostic data (JSON)</h2>
  <details>
    <summary>Show diagnostic data</summary>
    <pre>{safe_diagnostics}</pre>
  </details>
</section>

<section>
  <h2>Residual data (JSON)</h2>
  <details>
    <summary>Show residual analysis data</summary>
    <pre>{safe_residuals}</pre>
  </details>
</section>

<footer>
  Generated by SimuNexa CAE Copilot.
</footer>
</body>
</html>
"""

    # Copy any existing plots beside the generated report.
    source_plot_dir = Path("reports/residual_plots")
    if source_plot_dir.is_dir() and source_plot_dir != plot_dir:
        plot_dir.mkdir(parents=True, exist_ok=True)
        for image in source_plot_dir.glob("residual_*.png"):
            destination = plot_dir / image.name
            if image.resolve() != destination.resolve():
                shutil.copy2(image, destination)

    output.write_text(report_html, encoding="utf-8")
    return output


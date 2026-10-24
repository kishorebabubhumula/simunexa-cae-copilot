
"""Generate an HTML report from SimuNexa CAE diagnostics."""

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def generate_report(
    diagnostics: dict[str, Any],
    output_path: str | Path,
    residual_analysis: dict[str, Any] | None = None,
) -> Path:
    """Write a self-contained HTML engineering report."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    def escape(value: Any) -> str:
        return html.escape(str(value))

    status = (
        "FATAL ERROR"
        if diagnostics.get("fatal_error")
        else "COMPLETION MARKER FOUND"
        if diagnostics.get("solver_completed")
        else "COMPLETION NOT CONFIRMED"
    )

    status_color = (
        "#b42318"
        if diagnostics.get("fatal_error")
        else "#18794e"
        if diagnostics.get("solver_completed")
        else "#9a6700"
    )

    summary_items = diagnostics.get("summary", [])
    warning_items = diagnostics.get("warnings", [])
    error_items = diagnostics.get("errors", [])
    courant_values = diagnostics.get("courant_max", [])

    diagnostic_rows = []
    for item in summary_items:
        diagnostic_rows.append(f"<li>{escape(item)}</li>")

    warning_rows = [
        f"<li>{escape(item)}</li>" for item in warning_items
    ]
    error_rows = [
        f"<li>{escape(item)}</li>" for item in error_items
    ]

    residual_rows = []
    if residual_analysis:
        for name, metrics in residual_analysis.get(
            "residuals", {}
        ).items():
            ratio = metrics.get("reduction_ratio")
            ratio_text = (
                "undefined"
                if ratio is None
                else f"{ratio:.6g}"
            )
            residual_rows.append(
                "<tr>"
                f"<td>{escape(name)}</td>"
                f"<td>{escape(metrics.get('initial'))}</td>"
                f"<td>{escape(metrics.get('final'))}</td>"
                f"<td>{escape(ratio_text)}</td>"
                f"<td>{'Yes' if metrics.get('below_tolerance') else 'No'}</td>"
                "</tr>"
            )

    residual_table = (
        "<table><thead><tr>"
        "<th>Variable</th><th>Initial residual</th>"
        "<th>Final residual</th><th>Final / initial</th>"
        "<th>Below tolerance</th></tr></thead><tbody>"
        + "".join(residual_rows)
        + "</tbody></table>"
        if residual_rows
        else "<p>No residual analysis was supplied.</p>"
    )

    safe_diagnostics = escape(
        json.dumps(diagnostics, indent=2, ensure_ascii=False)
    )
    safe_residuals = escape(
        json.dumps(
            residual_analysis or {},
            indent=2,
            ensure_ascii=False,
        )
    )

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SimuNexa CAE Copilot - CFD Report</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 1050px;
       margin: 35px auto; padding: 0 20px; color: #202938;
       line-height: 1.5; }}
header {{ border-bottom: 3px solid #2457a7; padding-bottom: 16px; }}
h1 {{ margin-bottom: 4px; }}
h2 {{ margin-top: 32px; border-bottom: 1px solid #d0d7de;
      padding-bottom: 6px; }}
.status {{ display: inline-block; padding: 7px 12px;
           color: white; border-radius: 5px;
           background: {status_color}; font-weight: bold; }}
table {{ border-collapse: collapse; width: 100%; margin: 14px 0; }}
th, td {{ border: 1px solid #d0d7de; padding: 9px;
          text-align: left; overflow-wrap: anywhere; }}
th {{ background: #f0f4f8; }}
pre {{ white-space: pre-wrap; overflow-wrap: anywhere;
       background: #f6f8fa; padding: 14px; border-radius: 5px; }}
.note {{ background: #fff8c5; padding: 12px; border-radius: 5px; }}
footer {{ margin-top: 40px; color: #57606a; font-size: 0.9em; }}
</style>
</head>
<body>
<header>
<h1>SimuNexa CAE Copilot</h1>
<p>CFD Solver Diagnostics Report</p>
<p class="status">{escape(status)}</p>
</header>

<h2>Report information</h2>
<p><strong>Generated (UTC):</strong>
{datetime.now(timezone.utc).isoformat(timespec="seconds")}</p>
<p><strong>Log file:</strong>
{escape(diagnostics.get("file", "Not specified"))}</p>

<h2>Diagnostic summary</h2>
<ul>{"".join(diagnostic_rows) or "<li>No summary messages.</li>"}</ul>

<h2>Courant numbers</h2>
<p>Reported maximum values: {escape(courant_values or "None found")}</p>

<h2>Warnings</h2>
<ul>{"".join(warning_rows) or "<li>No warnings detected.</li>"}</ul>

<h2>Errors</h2>
<ul>{"".join(error_rows) or "<li>No error messages detected.</li>"}</ul>

<h2>Residual analysis</h2>
{residual_table}

<div class="note">
<strong>Engineering limitation:</strong> A completion marker and decreasing
residuals do not independently establish convergence or physical accuracy.
Review conservation balances, monitored quantities, mesh independence,
boundary conditions, and validation against appropriate reference data.
</div>

<h2>Diagnostic data (JSON)</h2>
<pre>{safe_diagnostics}</pre>

<h2>Residual data (JSON)</h2>
<pre>{safe_residuals}</pre>

<footer>Generated by SimuNexa CAE Copilot.</footer>
</body>
</html>
"""

    output.write_text(report_html, encoding="utf-8")
    return output


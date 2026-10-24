"""Evidence-based engineering recommendations for CFD diagnostics."""

import math
from typing import Any



def generate_recommendations(
    diagnostics: dict[str, Any],
    residual_analysis: dict[str, Any] | None = None,
    mesh_analysis: dict[str, Any] | None = None,
    mesh_thresholds: dict[str, float] | None = None,
) -> list[dict[str, str]]:
    """Generate review recommendations from available diagnostic evidence.

    These rules flag items for engineering review; they do not prove
    convergence, stability, or physical accuracy.
    """

    recommendations: list[dict[str, str]] = []

    def add(
        priority: str,
        title: str,
        evidence: str,
        action: str,
        limitation: str,
    ) -> None:
        recommendations.append(
            {
                "priority": priority,
                "title": title,
                "evidence": evidence,
                "action": action,
                "limitation": limitation,
            }
        )

    # Solver completion and fatal errors.
    if diagnostics.get("fatal_error"):
        add(
            "High",
            "Investigate the fatal solver error",
            "The log parser detected a fatal OpenFOAM error.",
            "Inspect the error message and preceding log lines. Check "
            "the case dictionaries, mesh, boundary conditions, and "
            "field initialization relevant to the reported error.",
            "The log alone may not identify the complete root cause.",
        )
    elif not diagnostics.get("solver_completed"):
        add(
            "High",
            "Confirm why solver completion is unconfirmed",
            "The expected OpenFOAM End marker was not detected.",
            "Check the end of the log, process exit status, and whether "
            "the run was interrupted or the log was truncated.",
            "A missing marker does not by itself prove solver failure.",
        )
    else:
        add(
            "Info",
            "Validate the completed simulation",
            "The expected OpenFOAM End marker was detected.",
            "Review residual histories, conservation balances, monitored "
            "physical quantities, mesh quality, and validation data.",
            "Normal log completion does not establish convergence "
            "or physical accuracy.",
        )

    # Courant number review.
    courant_values = []
    for value in diagnostics.get("courant_max", []):
        try:
            number = float(value)
            if number >= 0 and number < float("inf"):
                courant_values.append(number)
        except (TypeError, ValueError):
            continue

    threshold = diagnostics.get("courant_threshold")
    try:
        threshold = float(threshold)
        if threshold < 0 or threshold == float("inf"):
            threshold = None
    except (TypeError, ValueError):
        threshold = None

    if courant_values and threshold is not None:
        maximum = max(courant_values)
        exceedances = sum(value > threshold for value in courant_values)

        if exceedances:
            add(
                "Review",
                "Review Courant number exceedances",
                f"Maximum reported Courant number is {maximum:g}; "
                f"{exceedances} sample(s) exceed the configured "
                f"threshold of {threshold:g}.",
                "Inspect local Courant-number distribution, time-step "
                "size, mesh resolution, and numerical schemes. For a "
                "transient case, assess whether a smaller time step is "
                "needed and compare results after the change.",
                "The configured threshold is a diagnostic flag, not a "
                "universal stability limit. Acceptability depends on "
                "the solver, scheme, mesh, and physics.",
            )
        else:
            add(
                "Info",
                "Courant threshold not exceeded",
                f"Maximum reported Courant number is {maximum:g}, "
                f"not above the configured threshold of {threshold:g}.",
                "Continue checking solution quality and the relevant "
                "solver-specific time-step or stability requirements.",
                "Being below this threshold does not prove stability "
                "or accuracy.",
            )
    # Mesh-quality recommendations.
    if mesh_analysis is not None:
        if not mesh_analysis.get("mesh_ok", False):
            add(
                "Review",
                "Investigate mesh quality-check result",
                "The mesh report does not contain the expected Mesh OK marker.",
                "Inspect the complete checkMesh output, failed checks, "
                "mesh topology, and local cell-quality metrics.",
                "A missing marker may mean the check failed, the log was "
                "truncated, or the report format differs.",
            )

        failed_checks = mesh_analysis.get("failed_checks", [])
        if failed_checks:
            add(
                "Review",
                "Review mesh checks reported as failed",
                f"The mesh log contains {len(failed_checks)} potential "
                "failed-check message(s).",
                "Review the listed messages in the original checkMesh log "
                "and identify the affected mesh regions.",
                "Text matching alone does not establish the severity "
                "or cause of a mesh issue.",
            )

        thresholds = {
            "max_non_orthogonality": 70.0,
            "max_skewness": 4.0,
            "max_aspect_ratio": 100.0,
        }
        if mesh_thresholds:
            thresholds.update(mesh_thresholds)

        mesh_metrics = [
            (
                "max_non_orthogonality",
                thresholds["max_non_orthogonality"],
                "maximum non-orthogonality",
                "degrees",
            ),
            (
                "max_skewness",
                thresholds["max_skewness"],
                "maximum skewness",
                "",
            ),
            (
                "max_aspect_ratio",
                thresholds["max_aspect_ratio"],
                "maximum aspect ratio",
                "",
            ),
        ]

        for key, threshold_value, label, unit in mesh_metrics:
            value = mesh_analysis.get(key)

            try:
                value = float(value)
            except (TypeError, ValueError):
                continue

            if not math.isfinite(value) or value < 0:
                continue

            if value > threshold_value:
                unit_text = f" {unit}" if unit else ""
                add(
                    "Review",
                    f"Investigate {label}",
                    f"Reported {label} is {value:g}{unit_text}, above "
                    f"the configurable default review threshold of "
                    f"{threshold_value:g}{unit_text}.",
                    "Locate the affected cells and assess mesh quality, "
                    "flow alignment, numerical schemes, and sensitivity "
                    "of the solution to mesh refinement.",
                    "This default threshold is a screening rule, not a "
                    "universal acceptance criterion. Suitability depends "
                    "on the physics and mesh location.",
                )
    # Residual trends.
    residuals = (
        residual_analysis.get("residuals", {})
        if residual_analysis
        else {}
    )

    for variable, metrics in sorted(residuals.items()):
        below_tolerance = metrics.get("below_tolerance")
        decreasing = metrics.get("decreasing_overall")
        increases = metrics.get("increases_count")

        try:
            increase_count = int(increases) if increases is not None else 0
        except (TypeError, ValueError):
            increase_count = 0

        if below_tolerance is False:
            add(
                "Review",
                f"Review final residual for {variable}",
                f"The final residual for {variable} is not below the "
                "configured tolerance.",
                "Inspect the residual history, solver settings, "
                "continuity or conservation errors, and relevant "
                "physical monitors.",
                "Residual tolerance alone is not a complete convergence "
                "criterion.",
            )

        if decreasing is False or increase_count > 0:
            add(
                "Review",
                f"Inspect residual trend for {variable}",
                f"Residual increases were recorded for {variable}: "
                f"{increase_count}.",
                "Inspect the residual plot alongside physical monitors "
                "and conservation balances. Determine whether increases "
                "are transient behavior, oscillation, or a numerical issue.",
                "Residual increases can occur in transient and iterative "
                "solvers; the count alone does not diagnose failure.",
            )

        if below_tolerance is True and decreasing is True:
            add(
                "Info",
                f"Residual reduction observed for {variable}",
                "The final residual is below the selected tolerance and "
                "the overall trend is decreasing.",
                "Confirm that monitored quantities and conservation "
                "balances are also acceptable.",
                "These indicators alone do not prove convergence.",
            )

    if not residual_analysis:
        add(
            "Info",
            "Run residual trend analysis",
            "No residual analysis was supplied to the recommendations engine.",
            "Use the automatic residual extraction option or supply a "
            "supported residual CSV.",
            "Recommendations are limited by the data provided.",
        )

    if not recommendations:
        add(
            "Info",
            "Review engineering validation evidence",
            "No specific rule was triggered by the available diagnostics.",
            "Check mesh independence, conservation balances, physical "
            "monitors, boundary conditions, and suitable validation data.",
            "Absence of a triggered rule does not establish solution quality.",
        )

    return recommendations


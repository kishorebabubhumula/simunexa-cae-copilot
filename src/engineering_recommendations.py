
"""Evidence-based engineering recommendations for CFD diagnostics."""

from typing import Any


def generate_recommendations(
    diagnostics: dict[str, Any],
    residual_analysis: dict[str, Any] | None = None,
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



"""Basic diagnostics for OpenFOAM solver log files."""

from pathlib import Path
import re


def analyze_openfoam_log(log_path):
    """Extract basic solver status, residuals, Courant numbers and warnings."""
    path = Path(log_path)

    if not path.is_file():
        raise FileNotFoundError(f"Log file not found: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")

    result = {
        "file": str(path),
        "solver_completed": False,
        "fatal_error": False,
        "residual_records": 0,
        "courant_max": [],
        "warnings": [],
        "errors": [],
        "summary": [],
    }

    # Common OpenFOAM normal-completion marker.
    result["solver_completed"] = bool(
        re.search(r"^\s*End\s*$", text, re.MULTILINE)
    )

    result["fatal_error"] = bool(
        re.search(r"FOAM FATAL ERROR|FOAM FATAL IO ERROR", text)
    )

    # Count lines that report initial residuals.
    residual_pattern = re.compile(
        r"Solving for\s+(\w+).*?"
        r"Initial residual\s*=\s*"
        r"([0-9.eE+-]+)",
        re.IGNORECASE,
    )
    residuals = residual_pattern.findall(text)
    result["residual_records"] = len(residuals)

    # Collect reported maximum Courant numbers.
    courant_pattern = re.compile(
        r"Courant Number.*?max:\s*([0-9.eE+-]+)",
        re.IGNORECASE,
    )
    result["courant_max"] = [
        float(value) for value in courant_pattern.findall(text)
    ]

    result["warnings"] = [
        line.strip()
        for line in text.splitlines()
        if "warning" in line.lower()
    ]

    result["errors"] = [
        line.strip()
        for line in text.splitlines()
        if "error" in line.lower() or "fatal" in line.lower()
    ]

    if result["fatal_error"]:
        result["summary"].append(
            "Fatal OpenFOAM error detected; inspect the log."
        )
    elif result["solver_completed"]:
        result["summary"].append(
            "Normal-completion marker found. Validate the solution separately."
        )
    else:
        result["summary"].append(
            "Normal-completion marker not found; the run may be incomplete."
        )

    if result["courant_max"]:
        maximum = max(result["courant_max"])
        result["summary"].append(
            f"Maximum reported Courant number: {maximum:g}"
        )

    result["summary"].append(
        f"Residual records detected: {result['residual_records']}"
    )

    return result


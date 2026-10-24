"""Extract per-solve residual records from an OpenFOAM log."""

import csv
import re
from pathlib import Path


TIME_PATTERN = re.compile(
    r"^\s*Time\s*=\s*([0-9.eE+-]+)\s*s?\s*$"
)

RESIDUAL_PATTERN = re.compile(
    r"^\s*([^:]+):\s*Solving for\s+(\w+),\s*"
    r"Initial residual\s*=\s*([0-9.eE+-]+),\s*"
    r"Final residual\s*=\s*([0-9.eE+-]+),\s*"
    r"No Iterations\s+(\d+)",
    re.IGNORECASE,
)


def extract_residuals_to_csv(
    log_path: str | Path,
    csv_path: str | Path,
) -> dict:
    """Extract solver, time, variable and residual values into a CSV."""

    source = Path(log_path).expanduser()
    destination = Path(csv_path).expanduser()

    if not source.is_file():
        raise FileNotFoundError(f"OpenFOAM log not found: {source}")

    current_time = None
    records = []

    for line in source.read_text(
        encoding="utf-8", errors="replace"
    ).splitlines():
        time_match = TIME_PATTERN.match(line)

        if time_match:
            current_time = float(time_match.group(1))
            continue

        match = RESIDUAL_PATTERN.match(line)

        if match:
            solver, variable, initial, final, iterations = match.groups()

            records.append({
                "time": current_time if current_time is not None else "",
                "solver": solver.strip(),
                "variable": variable,
                "initial_residual": float(initial),
                "final_residual": float(final),
                "solver_iterations": int(iterations),
            })

    if not records:
        raise ValueError(
            f"No residual records found in OpenFOAM log: {source}"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "time",
        "solver",
        "variable",
        "initial_residual",
        "final_residual",
        "solver_iterations",
    ]

    with destination.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    return {
        "log_file": str(source),
        "csv_file": str(destination),
        "records_extracted": len(records),
        "variables": sorted({row["variable"] for row in records}),
    }


def summarize_residual_records(
    csv_path: str | Path,
    tolerance: float = 1e-4,
) -> dict:
    """Summarize per-solve residual records by variable."""

    import math

    if (
        isinstance(tolerance, bool)
        or not isinstance(tolerance, (int, float))
        or not math.isfinite(tolerance)
        or tolerance < 0
    ):
        raise ValueError(
            "Tolerance must be a finite, non-negative number."
        )

    path = Path(csv_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Residual CSV not found: {path}")

    grouped = {}

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {
            "variable", "initial_residual",
            "final_residual", "solver_iterations",
        }

        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                "CSV must contain variable, initial_residual, "
                "final_residual and solver_iterations columns."
            )

        for row in reader:
            variable = row["variable"]
            initial = float(row["initial_residual"])
            final = float(row["final_residual"])
            iterations = int(row["solver_iterations"])

            if (
                not math.isfinite(initial)
                or not math.isfinite(final)
                or initial < 0
                or final < 0
                or iterations < 0
            ):
                raise ValueError("Residuals and iterations must be valid non-negative values.")

            grouped.setdefault(variable, []).append(
                (initial, final, iterations)
            )

    if not grouped:
        raise ValueError("Residual CSV contains no records.")

    summaries = {}

    for variable, records in grouped.items():
        initial = records[0][0]
        final = records[-1][1]
        ratio = (
            final / initial if initial != 0
            else 1.0 if final == 0
            else None
        )

        summaries[variable] = {
            "initial": initial,
            "final": final,
            "reduction_ratio": ratio,
            "below_tolerance": final <= tolerance,
            "decreasing_overall": final < initial,
            "sample_count": len(records),
            "mean_solver_iterations": (
                sum(item[2] for item in records) / len(records)
            ),
        }

    return {
        "file": str(path),
        "tolerance": tolerance,
        "rows_read": sum(len(rows) for rows in grouped.values()),
        "residuals": summaries,
        "note": (
            "Summaries use the first initial residual and last final "
            "residual recorded for each variable. Residual trends alone "
            "do not establish convergence."
        ),
    }

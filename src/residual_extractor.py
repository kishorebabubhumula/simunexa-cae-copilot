
"""Extract and summarize residual information from OpenFOAM logs."""

from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


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

CSV_FIELDS = [
    "time",
    "solver",
    "variable",
    "initial_residual",
    "final_residual",
    "solver_iterations",
]

SUMMARY_NOTE = (
    "Summaries use the first initial residual and the last final residual "
    "for each variable, in CSV order. Trend indicators describe recorded "
    "solver residuals; they do not establish solver or physical convergence. "
    "Check solver settings, monitored quantities, physical balances and "
    "mesh independence as appropriate."
)


def _finite_nonnegative(value: Any, field_name: str) -> float:
    """Convert a value to a finite, non-negative float."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric.") from exc

    if not math.isfinite(number) or number < 0:
        raise ValueError(
            f"{field_name} must be finite and non-negative."
        )

    return number


def extract_residuals_to_csv(
    log_path: str | Path,
    csv_path: str | Path,
) -> dict[str, Any]:
    """Extract residual records and return extraction metadata."""
    source = Path(log_path)
    destination = Path(csv_path)

    if not source.is_file():
        raise FileNotFoundError(f"OpenFOAM log not found: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)

    current_time: float | None = None
    records: list[dict[str, Any]] = []

    with source.open("r", encoding="utf-8", errors="replace") as log_file:
        for line_number, line in enumerate(log_file, start=1):
            time_match = TIME_PATTERN.match(line)

            if time_match:
                try:
                    parsed_time = float(time_match.group(1))
                    current_time = (
                        parsed_time if math.isfinite(parsed_time) else None
                    )
                except ValueError:
                    current_time = None
                continue

            residual_match = RESIDUAL_PATTERN.match(line)

            if not residual_match or current_time is None:
                continue

            try:
                initial_residual = _finite_nonnegative(
                    residual_match.group(3),
                    "initial_residual",
                )
                final_residual = _finite_nonnegative(
                    residual_match.group(4),
                    "final_residual",
                )
                iterations = int(residual_match.group(5))
            except ValueError as exc:
                raise ValueError(
                    f"Invalid residual record on line {line_number}: {exc}"
                ) from exc

            if iterations < 0:
                raise ValueError(
                    f"Negative solver iteration count on line {line_number}."
                )

            records.append(
                {
                    "time": current_time,
                    "solver": residual_match.group(1).strip(),
                    "variable": residual_match.group(2).strip(),
                    "initial_residual": initial_residual,
                    "final_residual": final_residual,
                    "solver_iterations": iterations,
                }
            )

    with destination.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)

    return {
        "records_extracted": len(records),
        "csv_file": str(destination),
        "csv_path": str(destination),
    }


def summarize_residual_records(
    csv_path: str | Path,
    tolerance: float = 1e-4,
) -> dict[str, Any]:
    """Summarize residual trends from the extracted CSV."""
    source = Path(csv_path)

    if not source.is_file():
        raise FileNotFoundError(f"Residual CSV not found: {source}")

    tolerance = _finite_nonnegative(tolerance, "tolerance")

    grouped: dict[str, list[dict[str, float]]] = defaultdict(list)
    rows_read = 0

    with source.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)

        if not reader.fieldnames:
            raise ValueError("Residual CSV is empty or has no header.")

        missing = set(CSV_FIELDS) - set(reader.fieldnames)
        if missing:
            raise ValueError(
                "Residual CSV is missing required columns: "
                + ", ".join(sorted(missing))
            )

        for line_number, row in enumerate(reader, start=2):
            variable = (row.get("variable") or "").strip()

            if not variable:
                raise ValueError(
                    f"Missing variable in residual CSV line {line_number}."
                )

            initial = _finite_nonnegative(
                row["initial_residual"],
                f"initial_residual on line {line_number}",
            )
            final = _finite_nonnegative(
                row["final_residual"],
                f"final_residual on line {line_number}",
            )

            try:
                iterations = int(row["solver_iterations"])
                time_value = float(row["time"])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid time or iteration count on line {line_number}."
                ) from exc

            if (
                iterations < 0
                or not math.isfinite(time_value)
                or time_value < 0
            ):
                raise ValueError(
                    f"Invalid time or iteration count on line {line_number}."
                )

            grouped[variable].append(
                {
                    "initial": initial,
                    "final": final,
                    "iterations": float(iterations),
                }
            )
            rows_read += 1

    summaries: dict[str, dict[str, Any]] = {}

    for variable, records in grouped.items():
        first_initial = records[0]["initial"]
        final_residual = records[-1]["final"]

        reduction_ratio = (
            final_residual / first_initial
            if first_initial > 0
            else (0.0 if final_residual == 0 else None)
        )

        final_values = [record["final"] for record in records]

        increases_count = sum(
            current > previous
            for previous, current in zip(
                final_values,
                final_values[1:],
            )
        )

        summaries[variable] = {
            "initial": first_initial,
            "final": final_residual,
            "reduction_ratio": reduction_ratio,
            "below_tolerance": final_residual <= tolerance,
            "decreasing_overall": final_residual < first_initial,
            "monotonic_decrease": all(
                current <= previous
                for previous, current in zip(
                    final_values,
                    final_values[1:],
                )
            ),
            "increases_count": increases_count,
            "sample_count": len(records),
            "mean_solver_iterations": (
                sum(record["iterations"] for record in records)
                / len(records)
            ),
        }

    return {
        "file": str(source),
        "tolerance": tolerance,
        "rows_read": rows_read,
        "residuals": summaries,
        "note": SUMMARY_NOTE,
    }

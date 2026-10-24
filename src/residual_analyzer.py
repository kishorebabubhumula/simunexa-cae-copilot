
import csv
import math
from pathlib import Path
from typing import Any


def analyze_residuals(
    csv_path: str | Path,
    tolerance: float = 1e-4,
) -> dict[str, Any]:
    """
    Analyze residual histories stored in a CSV file.

    Expected columns:
        iteration, Ux, Uy, p, k, epsilon

    Returns initial/final residuals and basic trend indicators.

    Important:
        Residual trends alone do not establish numerical or physical
        convergence. Check solver settings, physical balances,
        monitored quantities, and mesh independence as appropriate.
    """

    if (
        isinstance(tolerance, bool)
        or not isinstance(tolerance, (int, float))
        or not math.isfinite(tolerance)
        or tolerance < 0
    ):
        raise ValueError(
            "Tolerance must be a finite, non-negative number."
        )

    path = Path(csv_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Residual CSV not found: {path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(
                "Residual CSV has no header."
            )

        if "iteration" not in reader.fieldnames:
            raise ValueError(
                "CSV must contain an 'iteration' column."
            )

        residual_columns = [
            name
            for name in reader.fieldnames
            if name != "iteration"
        ]

        if not residual_columns:
            raise ValueError(
                "CSV must contain at least one residual column."
            )

        rows = list(reader)

    if not rows:
        raise ValueError(
            "Residual CSV contains no data rows."
        )

    results: dict[str, dict[str, Any]] = {}

    for column in residual_columns:
        values: list[float] = []

        for row in rows:
            raw_value = row.get(column, "")

            if raw_value is None or not raw_value.strip():
                continue

            try:
                value = float(raw_value)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid residual value in column "
                    f"'{column}': {raw_value!r}"
                ) from exc

            if not math.isfinite(value) or value < 0:
                raise ValueError(
                    "Residuals must be finite and "
                    f"non-negative: {value}"
                )

            values.append(value)

        if not values:
            continue

        initial = values[0]
        final = values[-1]

        if initial == 0:
            reduction_ratio = (
                1.0 if final == 0 else None
            )
        else:
            reduction_ratio = final / initial

        # Count increases between successive recorded samples.
        increases_count = sum(
            current > previous
            for previous, current in zip(
                values,
                values[1:],
            )
        )

        # True when no successive sample increases.
        # For a single sample, this is True by definition,
        # but it does not indicate convergence.
        monotonic_decrease = all(
            current <= previous
            for previous, current in zip(
                values,
                values[1:],
            )
        )

        results[column] = {
            "initial": initial,
            "final": final,
            "reduction_ratio": reduction_ratio,
            "below_tolerance": final <= tolerance,
            "decreasing_overall": final < initial,
            "monotonic_decrease": monotonic_decrease,
            "increases_count": increases_count,
            "sample_count": len(values),
        }

    if not results:
        raise ValueError(
            "No usable residual values were found."
        )

    return {
        "file": str(path),
        "tolerance": tolerance,
        "rows_read": len(rows),
        "residuals": results,
        "note": (
            "Residual trends alone do not establish convergence. "
            "Also check solver settings, physical balances, "
            "monitored quantities, and mesh independence. "
            "A single-sample history is insufficient to establish "
            "a residual trend."
        ),
    }


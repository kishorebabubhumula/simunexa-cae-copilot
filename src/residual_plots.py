
"""Generate residual convergence plots for SimuNexa CAE Copilot."""

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


def generate_residual_plots(
    csv_path: str | Path,
    output_dir: str | Path,
) -> list[Path]:
    """Plot residual histories against simulation time when available."""

    source = Path(csv_path)
    destination = Path(output_dir)

    if not source.is_file():
        raise FileNotFoundError(f"Residual CSV not found: {source}")

    destination.mkdir(parents=True, exist_ok=True)

    # Each record contains: x value, final residual.
    grouped: dict[str, list[tuple[float, float]]] = {}

    with source.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        required = {"variable", "final_residual"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                "CSV must contain variable and final_residual columns."
            )

        has_time = "time" in reader.fieldnames

        for index, row in enumerate(reader, start=1):
            variable = (row.get("variable") or "").strip()

            try:
                residual = float(row["final_residual"])
            except (TypeError, ValueError):
                continue

            if not variable or not math.isfinite(residual) or residual <= 0:
                continue

            # Use physical simulation time if available.
            # Otherwise, fall back to the record number.
            if has_time:
                try:
                    x_value = float(row["time"])
                except (TypeError, ValueError):
                    continue

                if not math.isfinite(x_value):
                    continue
            else:
                x_value = float(index)

            grouped.setdefault(variable, []).append((x_value, residual))

    if not grouped:
        raise ValueError("No positive, finite residual values were found.")

    outputs: list[Path] = []

    for variable, records in sorted(grouped.items()):
        x_values = [item[0] for item in records]
        y_values = [item[1] for item in records]

        fig, ax = plt.subplots(figsize=(10, 5))

        ax.plot(x_values, y_values, linewidth=1.2)

        ax.set_yscale("log")

        if has_time:
            ax.set_xlabel("Simulation time")
        else:
            ax.set_xlabel("Extracted residual record")

        ax.set_ylabel("Final residual")
        ax.set_title(f"Residual History — {variable}")
        ax.grid(True, which="both", linestyle="--", alpha=0.4)

        fig.tight_layout()

        output_file = destination / f"residual_{variable}.png"
        fig.savefig(output_file, dpi=160)
        plt.close(fig)

        outputs.append(output_file)

    return outputs


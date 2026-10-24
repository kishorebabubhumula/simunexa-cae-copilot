"""Parse OpenFOAM solver logs and export residual histories."""

import argparse
import csv
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


TIME_RE = re.compile(r"^\s*Time\s*=\s*([0-9.eE+-]+)")
RESIDUAL_RE = re.compile(
    r"Solving for\s+([^,]+),\s*"
    r"Initial residual\s*=\s*([0-9.eE+-]+),\s*"
    r"Final residual\s*=\s*([0-9.eE+-]+),\s*"
    r"No Iterations\s+(\d+)"
)


def analyze_log(log_path):
    """Return residual records, warnings, and detected run status."""
    path = Path(log_path)
    if not path.is_file():
        raise FileNotFoundError(f"Log file not found: {path}")

    records = []
    warnings = []
    errors = []
    current_time = None
    saw_end = False

    with path.open("r", encoding="utf-8", errors="replace") as log:
        for line_number, line in enumerate(log, start=1):
            time_match = TIME_RE.search(line)
            if time_match:
                current_time = float(time_match.group(1))

            residual_match = RESIDUAL_RE.search(line)
            if residual_match:
                if current_time is None:
                    warnings.append(
                        f"Line {line_number}: residual found before a Time entry"
                    )
                    continue

                variable, initial, final, iterations = residual_match.groups()
                records.append({
                    "time": current_time,
                    "variable": variable.strip(),
                    "initial_residual": float(initial),
                    "final_residual": float(final),
                    "iterations": int(iterations),
                    "line_number": line_number,
                })

            if "FOAM FATAL ERROR" in line or "FOAM FATAL IO ERROR" in line:
                errors.append(f"Line {line_number}: {line.strip()}")

            if "Warning" in line or "WARNING" in line:
                warnings.append(f"Line {line_number}: {line.strip()}")

            if re.search(r"^\s*End\s*$", line):
                saw_end = True

    status = (
        "failed" if errors
        else "completed_marker_found" if saw_end
        else "end_marker_not_found"
    )

    return {
        "records": records,
        "warnings": warnings,
        "errors": errors,
        "status": status,
    }


def write_csv(records, output_path):
    """Write extracted residual records to CSV."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "time", "variable", "initial_residual",
        "final_residual", "iterations", "line_number"
    ]

    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def plot_residuals(records, output_path):
    """Plot final residuals against time-step index."""
    if not records:
        print("No residual data found; plot not generated.")
        return

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    variables = sorted({record["variable"] for record in records})

    fig, ax = plt.subplots(figsize=(9, 5))
    for variable in variables:
        subset = [r for r in records if r["variable"] == variable]
        x_values = list(range(1, len(subset) + 1))
        y_values = [r["final_residual"] for r in subset]

        # A logarithmic axis cannot display zero or negative residuals.
        valid = [(x, y) for x, y in zip(x_values, y_values) if y > 0]
        if valid:
            ax.semilogy(
                [point[0] for point in valid],
                [point[1] for point in valid],
                marker="o",
                label=variable,
            )

    ax.set_xlabel("Occurrence index for each variable")
    ax.set_ylabel("Final residual")
    ax.set_title("OpenFOAM Residual History")
    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze residuals and common errors in OpenFOAM logs."
    )
    parser.add_argument("logfile", help="Path to an OpenFOAM solver log")
    parser.add_argument(
        "--outdir", default="reports/latest",
        help="Output directory (default: reports/latest)"
    )
    args = parser.parse_args()

    result = analyze_log(args.logfile)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    write_csv(result["records"], outdir / "residuals.csv")
    plot_residuals(result["records"], outdir / "residuals.png")

    print(f"Run status: {result['status']}")
    print(f"Residual records extracted: {len(result['records'])}")
    print(f"Warnings detected: {len(result['warnings'])}")
    print(f"Errors detected: {len(result['errors'])}")
    print(f"CSV: {outdir / 'residuals.csv'}")
    print(f"Plot: {outdir / 'residuals.png'}")


if __name__ == "__main__":
    main()

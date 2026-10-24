"""Command-line interface for SimuNexa CAE Copilot."""

import argparse
import sys
from pathlib import Path

from src.openfoam_diagnostics import analyze_openfoam_log
from src.report_generator import generate_report
from src.residual_analyzer import analyze_residuals
from src.residual_extractor import (
    extract_residuals_to_csv,
    summarize_residual_records,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze an OpenFOAM solver log and generate an HTML report."
    )

    parser.add_argument(
        "--log",
        required=True,
        help="Path to the OpenFOAM solver log file.",
    )

    parser.add_argument(
        "--output",
        default="reports/cfd_report.html",
        help="Output HTML report path (default: reports/cfd_report.html).",
    )

    residual_group = parser.add_mutually_exclusive_group()

    residual_group.add_argument(
        "--residual-csv",
        help="Analyze an existing wide-format residual CSV.",
    )

    residual_group.add_argument(
        "--extract-residuals",
        action="store_true",
        help="Extract residual records from the OpenFOAM log automatically.",
    )

    parser.add_argument(
        "--residual-records-output",
        default="data/residual_records.csv",
        help="CSV destination for extracted residual records.",
    )

    parser.add_argument(
        "--residual-tolerance",
        type=float,
        default=1e-4,
        help="Residual tolerance (default: 1e-4).",
    )

    args = parser.parse_args()

    log_path = Path(args.log).expanduser()
    output_path = Path(args.output).expanduser()

    if not log_path.is_file():
        print(f"Error: log file not found: {log_path}", file=sys.stderr)
        return 2

    try:
        print(f"Analyzing OpenFOAM log: {log_path}")

        diagnostics = analyze_openfoam_log(log_path)
        residual_analysis = None

        if args.extract_residuals:
            records_csv = Path(args.residual_records_output).expanduser()

            extraction = extract_residuals_to_csv(
                log_path,
                records_csv,
            )

            print(f"Extracted residual records: {extraction['records_extracted']}")
            print(f"Residual records CSV: {extraction['csv_file']}")

            residual_analysis = summarize_residual_records(
                records_csv,
                tolerance=args.residual_tolerance,
            )

        elif args.residual_csv:
            residual_csv = Path(args.residual_csv).expanduser()

            residual_analysis = analyze_residuals(
                residual_csv,
                tolerance=args.residual_tolerance,
            )

            print(f"Residual CSV: {residual_csv}")

        report_path = generate_report(
            diagnostics,
            output_path,
            residual_analysis=residual_analysis,
        )

        print("\nAnalysis complete.")
        print(f"Solver completed: {diagnostics.get('solver_completed', False)}")
        print(f"Fatal error detected: {diagnostics.get('fatal_error', False)}")
        print(f"Residual records in log: {diagnostics.get('residual_records', 0)}")
        print(f"HTML report: {report_path}")

        if diagnostics.get("fatal_error", False):
            return 1

        return 0

    except (OSError, ValueError) as exc:
        print(f"Error while analyzing log: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

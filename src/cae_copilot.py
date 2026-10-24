
"""Command-line entry point for the SimuNexa CAE Copilot."""

import argparse
import sys
from pathlib import Path

from src.mesh_diagnostics import analyze_mesh_log
from src.openfoam_diagnostics import analyze_openfoam_log
from src.report_generator import generate_report
from src.residual_analyzer import analyze_residuals
from src.residual_extractor import extract_residuals_to_csv


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
    parser.add_argument(
        "--mesh-log",
        help="Optional path to an OpenFOAM checkMesh report.",
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
    parser.add_argument(
        "--max-non-orthogonality",
        type=float,
        default=70.0,
        help="Mesh review threshold in degrees (default: 70).",
    )
    parser.add_argument(
        "--max-skewness",
        type=float,
        default=4.0,
        help="Mesh skewness review threshold (default: 4.0).",
    )
    parser.add_argument(
        "--max-aspect-ratio",
        type=float,
        default=100.0,
        help="Mesh aspect-ratio review threshold (default: 100).",
    )

    args = parser.parse_args()

    # Validate numerical thresholds before analyzing files.
    numeric_thresholds = {
        "Residual tolerance": args.residual_tolerance,
        "Maximum non-orthogonality": args.max_non_orthogonality,
        "Maximum skewness": args.max_skewness,
        "Maximum aspect ratio": args.max_aspect_ratio,
    }
    for name, value in numeric_thresholds.items():
        if value <= 0 or value == float("inf") or value != value:
            print(f"Error: {name} must be a finite positive number.", file=sys.stderr)
            return 2

    log_path = Path(args.log).expanduser()
    output_path = Path(args.output).expanduser()

    mesh_analysis = None
    if args.mesh_log:
        mesh_path = Path(args.mesh_log).expanduser()
        if not mesh_path.is_file():
            print(f"Error: mesh log file not found: {mesh_path}", file=sys.stderr)
            return 2

        mesh_analysis = analyze_mesh_log(mesh_path)
        print(f"Mesh report: {mesh_path}")
        print(f"Mesh OK marker found: {mesh_analysis['mesh_ok']}")

    if not log_path.is_file():
        print(f"Error: log file not found: {log_path}", file=sys.stderr)
        return 2

    try:
        print(f"Analyzing OpenFOAM log: {log_path}")
        diagnostics = analyze_openfoam_log(log_path)
        residual_analysis = None

        if args.extract_residuals:
            records_csv = Path(args.residual_records_output).expanduser()
            extraction = extract_residuals_to_csv(log_path, records_csv)
            print(f"Extracted residual records: {extraction['records_extracted']}")
            print(f"Residual records CSV: {records_csv}")

            residual_analysis = analyze_residuals(
                records_csv,
                tolerance=args.residual_tolerance,
            )
        elif args.residual_csv:
            residual_csv = Path(args.residual_csv).expanduser()
            if not residual_csv.is_file():
                print(
                    f"Error: residual CSV file not found: {residual_csv}",
                    file=sys.stderr,
                )
                return 2

            residual_analysis = analyze_residuals(
                residual_csv,
                tolerance=args.residual_tolerance,
            )

        mesh_thresholds = {
            "max_non_orthogonality": args.max_non_orthogonality,
            "max_skewness": args.max_skewness,
            "max_aspect_ratio": args.max_aspect_ratio,
        }

        report_path = generate_report(
            diagnostics,
            output_path,
            residual_analysis=residual_analysis,
            mesh_analysis=mesh_analysis,
            mesh_thresholds=mesh_thresholds,
        )

        print("\nAnalysis complete.")
        print(f"Solver completed: {diagnostics.get('solver_completed', False)}")
        print(f"Fatal error detected: {diagnostics.get('fatal_error', False)}")
        print(f"Residual records in log: {diagnostics.get('residual_records', 0)}")
        print(f"HTML report: {report_path}")

        if diagnostics.get("fatal_error", False):
            return 1

        return 0

    except (OSError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

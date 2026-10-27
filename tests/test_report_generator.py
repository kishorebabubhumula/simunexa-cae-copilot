
from pathlib import Path

from src.report_generator import generate_report


def test_generates_html_report(tmp_path: Path):
    diagnostics = {
        "file": "log.simpleFoam",
        "solver_completed": True,
        "fatal_error": False,
        "residual_records": 10,
        "courant_max": [0.25, 0.45],
        "courant_threshold": 5.0,
        "warnings": [],
        "errors": [],
        "summary": ["Solver completed normally."],
    }

    output_file = tmp_path / "report.html"

    result = generate_report(diagnostics, output_file)

    assert result.exists()
    assert result == output_file

    content = result.read_text(encoding="utf-8")
    assert "<html" in content.lower()
    assert "Courant numbers" in content
    assert "Engineering limitation" in content
    assert "SimuNexa CAE Copilot" in content


def test_report_includes_residual_trend_indicators(tmp_path: Path):
    diagnostics = {
        "file": "log.pitzDaily",
        "solver_completed": True,
        "fatal_error": False,
        "residual_records": 3,
        "courant_max": [0.2, 0.4],
        "courant_threshold": 5.0,
        "warnings": [],
        "errors": [],
        "summary": [],
    }

    residual_analysis = {
        "file": "residual_records.csv",
        "tolerance": 1e-4,
        "rows_read": 3,
        "residuals": {
            "Ux": {
                "initial": 1.0,
                "final": 0.001,
                "trend": "decreasing",
                "reduction_ratio": 0.001,
                "below_tolerance": False,
                "decreasing_overall": True,
                "monotonic_decrease": False,
                "increases_count": 1,
                "sample_count": 3,
                "mean_solver_iterations": 4.0,
            }
        },
        "note": "Residual trends alone do not establish convergence.",
    }

    output_file = tmp_path / "report.html"

    generate_report(
        diagnostics,
        output_file,
        residual_analysis=residual_analysis,
    )

    content = output_file.read_text(encoding="utf-8")

    assert "Monotonic non-increase" in content
    assert "Residual increases" in content
    assert "Mean solver iterations" in content
    assert "Decreasing overall" in content
    assert "0.001" in content
    assert "Residual trends alone do not establish convergence." in content
    assert "Residual Trend Classification" in content
    assert "Trend classification" in content
    assert "decreasing" in content


def test_report_handles_missing_trend_metrics(tmp_path: Path):
    diagnostics = {
        "file": "log.simpleFoam",
        "solver_completed": False,
        "fatal_error": False,
        "residual_records": 0,
        "courant_max": [],
        "warnings": [],
        "errors": [],
        "summary": [],
    }

    residual_analysis = {
        "residuals": {
            "p": {
                "initial": 1.0,
                "final": 0.01,
                "reduction_ratio": 0.01,
                "below_tolerance": False,
            }
        }
    }

    output_file = tmp_path / "report.html"

    generate_report(
        diagnostics,
        output_file,
        residual_analysis=residual_analysis,
    )

    content = output_file.read_text(encoding="utf-8")

    assert "Unknown" in content
    assert "Not available" in content
    assert "COMPLETION NOT CONFIRMED" in content



def test_mesh_metrics_include_screening_statuses_and_custom_thresholds(
    tmp_path: Path,
):
    diagnostics = {
        "file": "log.simpleFoam",
        "solver_completed": True,
        "fatal_error": False,
        "residual_records": 0,
        "courant_max": [],
        "warnings": [],
        "errors": [],
        "summary": [],
    }
    mesh_analysis = {
        "openfoam_version": "13",
        "mesh_ok": True,
        "max_non_orthogonality": 60.0,
        "max_skewness": 5.0,
        "max_aspect_ratio": None,
        "summary": [],
        "failed_checks": [],
        "warnings": [],
    }
    output_file = tmp_path / "mesh_status_report.html"

    generate_report(
        diagnostics,
        output_file,
        mesh_analysis=mesh_analysis,
        mesh_thresholds={
            "max_non_orthogonality": 50.0,
            "max_skewness": 6.0,
            "max_aspect_ratio": 100.0,
        },
    )

    content = output_file.read_text(encoding="utf-8")

    assert "Screening status" in content
    assert "Review required" in content
    assert "Within threshold" in content
    assert "Unknown" in content
    assert "Maximum non-orthogonality" in content
    assert "Maximum skewness" in content
    assert "Maximum aspect ratio" in content

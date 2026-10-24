
from pathlib import Path

from src.report_generator import generate_report


def test_generates_html_report(tmp_path: Path):
    diagnostics = {
        "file": "log.simpleFoam",
        "solver_completed": True,
        "fatal_error": False,
        "residual_records": 10,
        "courant_max": [0.25, 0.45],
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



from pathlib import Path

import pytest

from src.mesh_diagnostics import analyze_mesh_log


def test_extracts_metrics_from_checkmesh_report(tmp_path: Path):
    log = tmp_path / "meshCheck.txt"
    log.write_text(
        """
OpenFOAM: The Open Source CFD Toolbox
Version: 14
Mesh stats
    points: 25012
    faces: 49180
    internal faces: 24170
    cells: 12225
    boundary patches: 5
Checking geometry...
    Max aspect ratio = 8.1407 OK.
    Mesh non-orthogonality Max: 5.95045 average: 1.63034
    Max skewness = 0.260575 OK.
Mesh OK.
End
""",
        encoding="utf-8",
    )

    result = analyze_mesh_log(log)

    assert result["openfoam_version"] == "14"
    assert result["points"] == 25012
    assert result["faces"] == 49180
    assert result["cells"] == 12225
    assert result["boundary_patches"] == 5
    assert result["max_aspect_ratio"] == pytest.approx(8.1407)
    assert result["max_non_orthogonality"] == pytest.approx(5.95045)
    assert result["average_non_orthogonality"] == pytest.approx(1.63034)
    assert result["max_skewness"] == pytest.approx(0.260575)
    assert result["mesh_ok"] is True
    assert result["end_marker"] is True


def test_missing_metrics_remain_none(tmp_path: Path):
    log = tmp_path / "minimal.log"
    log.write_text("Checking mesh...\n", encoding="utf-8")

    result = analyze_mesh_log(log)

    assert result["cells"] is None
    assert result["max_skewness"] is None
    assert result["mesh_ok"] is False


def test_missing_log_raises_error(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        analyze_mesh_log(tmp_path / "missing.log")


def test_reports_failed_check_lines(tmp_path: Path):
    log = tmp_path / "failed.log"
    log.write_text(
        "Mesh check failed: invalid topology\n",
        encoding="utf-8",
    )

    result = analyze_mesh_log(log)

    assert len(result["failed_checks"]) == 1



from src.openfoam_diagnostics import analyze_openfoam_log


def test_detects_normal_completion(tmp_path):
    log = tmp_path / "normal.log"
    log.write_text("Time = 1\nEnd\n", encoding="utf-8")

    result = analyze_openfoam_log(log)

    assert result["solver_completed"] is True
    assert result["fatal_error"] is False


def test_detects_fatal_error(tmp_path):
    log = tmp_path / "fatal.log"
    log.write_text(
        "FOAM FATAL ERROR: test failure\n",
        encoding="utf-8",
    )

    result = analyze_openfoam_log(log)

    assert result["fatal_error"] is True
    assert result["solver_completed"] is False


def test_missing_log_raises_error(tmp_path):
    missing_log = tmp_path / "missing.log"

    try:
        analyze_openfoam_log(missing_log)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_detects_courant_number(tmp_path):
    log = tmp_path / "courant.log"
    log.write_text(
        "Courant Number mean: 0.12 max: 0.85\n",
        encoding="utf-8",
    )

    result = analyze_openfoam_log(log)

    assert result["courant_max"] == [0.85]


def test_detects_warning(tmp_path):
    log = tmp_path / "warning.log"
    log.write_text(
        "Warning: test warning message\n",
        encoding="utf-8",
    )

    result = analyze_openfoam_log(log)

    assert len(result["warnings"]) == 1
    assert "Warning" in result["warnings"][0]


def test_detects_floating_point_exception(tmp_path):
    log = tmp_path / "floating_point.log"
    log.write_text(
        "FOAM FATAL ERROR: Floating point exception\n",
        encoding="utf-8",
    )

    result = analyze_openfoam_log(log)

    assert result["fatal_error"] is True


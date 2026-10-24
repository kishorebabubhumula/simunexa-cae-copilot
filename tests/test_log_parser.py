from src.log_parser import analyze_log


def test_sample_log():
    result = analyze_log("results/sample/sample_solver.log")
    assert len(result["records"]) == 6
    assert result["status"] == "completed_marker_found"
    assert result["errors"] == []


def test_missing_file():
    import pytest

    with pytest.raises(FileNotFoundError):
        analyze_log("results/sample/does_not_exist.log")


def test_fatal_error(tmp_path):
    log_file = tmp_path / "failed.log"
    log_file.write_text(
        "Time = 1\nFOAM FATAL ERROR: synthetic failure\n",
        encoding="utf-8",
    )

    result = analyze_log(log_file)

    assert result["status"] == "failed"
    assert len(result["errors"]) == 1

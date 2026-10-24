import csv

import pytest

from src.residual_analyzer import analyze_residuals


def create_csv(path):
    rows = [
        {
            "iteration": "1",
            "Ux": "0.1",
            "Uy": "0.05",
            "p": "0.01",
            "k": "0.005",
            "epsilon": "0.002",
        },
        {
            "iteration": "2",
            "Ux": "0.01",
            "Uy": "0.005",
            "p": "0.001",
            "k": "0.0005",
            "epsilon": "0.0002",
        },
        {
            "iteration": "3",
            "Ux": "0.0001",
            "Uy": "0.00005",
            "p": "0.00001",
            "k": "0.000005",
            "epsilon": "0.000002",
        },
    ]

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def test_analyzes_residual_reduction(tmp_path):
    csv_file = tmp_path / "residuals.csv"
    create_csv(csv_file)

    result = analyze_residuals(csv_file, tolerance=0.001)

    assert result["rows_read"] == 3
    assert result["residuals"]["Ux"]["initial"] == pytest.approx(0.1)
    assert result["residuals"]["Ux"]["final"] == pytest.approx(0.0001)
    assert result["residuals"]["Ux"]["below_tolerance"] is True
    assert result["residuals"]["Ux"]["decreasing_overall"] is True


def test_rejects_missing_csv(tmp_path):
    with pytest.raises(FileNotFoundError):
        analyze_residuals(tmp_path / "missing.csv")


def test_rejects_invalid_tolerance(tmp_path):
    csv_file = tmp_path / "residuals.csv"
    create_csv(csv_file)

    with pytest.raises(ValueError):
        analyze_residuals(csv_file, tolerance=-0.1)


def test_rejects_csv_without_iteration_column(tmp_path):
    csv_file = tmp_path / "invalid.csv"
    csv_file.write_text("Ux,p\n0.1,0.01\n", encoding="utf-8")

    with pytest.raises(ValueError):
        analyze_residuals(csv_file)

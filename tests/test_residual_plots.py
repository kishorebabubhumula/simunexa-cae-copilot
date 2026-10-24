
import csv

import pytest

from src.residual_plots import generate_residual_plots


def test_generates_plots_using_simulation_time(tmp_path):
    csv_file = tmp_path / "residuals.csv"
    output_dir = tmp_path / "plots"

    rows = [
        {
            "time": "0.1",
            "solver": "smoothSolver",
            "variable": "Ux",
            "initial_residual": "1.0",
            "final_residual": "0.01",
            "solver_iterations": "5",
        },
        {
            "time": "0.1",
            "solver": "GAMG",
            "variable": "p",
            "initial_residual": "1.0",
            "final_residual": "0.02",
            "solver_iterations": "8",
        },
        {
            "time": "0.2",
            "solver": "smoothSolver",
            "variable": "Ux",
            "initial_residual": "0.01",
            "final_residual": "0.001",
            "solver_iterations": "4",
        },
    ]

    with csv_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    outputs = generate_residual_plots(csv_file, output_dir)

    assert len(outputs) == 2
    assert (output_dir / "residual_Ux.png").is_file()
    assert (output_dir / "residual_p.png").is_file()


def test_rejects_csv_without_required_columns(tmp_path):
    csv_file = tmp_path / "invalid.csv"
    csv_file.write_text("time,solver\n0.1,GAMG\n", encoding="utf-8")

    with pytest.raises(ValueError, match="variable and final_residual"):
        generate_residual_plots(csv_file, tmp_path / "plots")


def test_rejects_missing_csv(tmp_path):
    with pytest.raises(FileNotFoundError):
        generate_residual_plots(
            tmp_path / "missing.csv",
            tmp_path / "plots",
        )


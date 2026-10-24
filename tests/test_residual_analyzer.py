
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

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=rows[0].keys(),
        )
        writer.writeheader()
        writer.writerows(rows)


def write_residual_csv(path, rows):
    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=rows[0].keys(),
        )
        writer.writeheader()
        writer.writerows(rows)


def test_analyzes_residual_reduction(tmp_path):
    csv_file = tmp_path / "residuals.csv"
    create_csv(csv_file)

    result = analyze_residuals(
        csv_file,
        tolerance=0.001,
    )

    assert result["rows_read"] == 3

    ux = result["residuals"]["Ux"]

    assert ux["initial"] == pytest.approx(0.1)
    assert ux["final"] == pytest.approx(0.0001)
    assert ux["below_tolerance"] is True
    assert ux["decreasing_overall"] is True
    assert ux["monotonic_decrease"] is True
    assert ux["increases_count"] == 0
    assert ux["sample_count"] == 3


def test_detects_fluctuating_residuals(tmp_path):
    csv_file = tmp_path / "fluctuating.csv"

    rows = [
        {"iteration": "1", "Ux": "0.1"},
        {"iteration": "2", "Ux": "0.01"},
        {"iteration": "3", "Ux": "0.02"},
        {"iteration": "4", "Ux": "0.001"},
    ]

    write_residual_csv(csv_file, rows)

    result = analyze_residuals(csv_file)
    ux = result["residuals"]["Ux"]

    assert ux["decreasing_overall"] is True
    assert ux["monotonic_decrease"] is False
    assert ux["increases_count"] == 1
    assert ux["sample_count"] == 4


def test_detects_residual_increase_overall(tmp_path):
    csv_file = tmp_path / "increasing.csv"

    rows = [
        {"iteration": "1", "Ux": "0.001"},
        {"iteration": "2", "Ux": "0.01"},
        {"iteration": "3", "Ux": "0.1"},
    ]

    write_residual_csv(csv_file, rows)

    result = analyze_residuals(csv_file)
    ux = result["residuals"]["Ux"]

    assert ux["decreasing_overall"] is False
    assert ux["monotonic_decrease"] is False
    assert ux["increases_count"] == 2


def test_single_sample_does_not_claim_convergence(tmp_path):
    csv_file = tmp_path / "single_sample.csv"

    rows = [
        {"iteration": "1", "Ux": "0.00001"},
    ]

    write_residual_csv(csv_file, rows)

    result = analyze_residuals(csv_file)
    ux = result["residuals"]["Ux"]

    assert ux["monotonic_decrease"] is True
    assert ux["sample_count"] == 1
    assert "insufficient" in result["note"]


def test_handles_zero_initial_residual(tmp_path):
    csv_file = tmp_path / "zero.csv"

    rows = [
        {"iteration": "1", "Ux": "0"},
        {"iteration": "2", "Ux": "0"},
    ]

    write_residual_csv(csv_file, rows)

    result = analyze_residuals(csv_file)
    ux = result["residuals"]["Ux"]

    assert ux["reduction_ratio"] == pytest.approx(1.0)
    assert ux["below_tolerance"] is True


def test_rejects_missing_csv(tmp_path):
    with pytest.raises(FileNotFoundError):
        analyze_residuals(
            tmp_path / "missing.csv"
        )


def test_rejects_invalid_tolerance(tmp_path):
    csv_file = tmp_path / "residuals.csv"
    create_csv(csv_file)

    for tolerance in (-0.1, float("nan"), float("inf"), True):
        with pytest.raises(ValueError):
            analyze_residuals(
                csv_file,
                tolerance=tolerance,
            )


def test_rejects_csv_without_iteration_column(tmp_path):
    csv_file = tmp_path / "invalid.csv"
    csv_file.write_text(
        "Ux,p\n0.1,0.01\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        analyze_residuals(csv_file)


def test_rejects_empty_csv(tmp_path):
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text(
        "iteration,Ux\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="no data rows"):
        analyze_residuals(csv_file)


@pytest.mark.parametrize(
    "invalid_value",
    [
        "not-a-number",
        "nan",
        "inf",
        "-0.1",
    ],
)
def test_rejects_invalid_residual_values(
    tmp_path,
    invalid_value,
):
    csv_file = tmp_path / "invalid_value.csv"

    rows = [
        {"iteration": "1", "Ux": invalid_value},
    ]

    write_residual_csv(csv_file, rows)

    with pytest.raises(ValueError):
        analyze_residuals(csv_file)


def test_rejects_csv_with_no_residual_columns(tmp_path):
    csv_file = tmp_path / "no_residuals.csv"
    csv_file.write_text(
        "iteration\n1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="at least one residual"):
        analyze_residuals(csv_file)


def test_rejects_blank_residual_history(tmp_path):
    csv_file = tmp_path / "blank.csv"

    rows = [
        {"iteration": "1", "Ux": ""},
        {"iteration": "2", "Ux": ""},
    ]

    write_residual_csv(csv_file, rows)

    with pytest.raises(ValueError, match="No usable residual"):
        analyze_residuals(csv_file)



@pytest.mark.parametrize(
    ("values", "expected_trend"),
    [
        ([0.1, 0.01, 0.001], "decreasing"),
        ([0.1, 0.102, 0.099], "stagnating"),
        ([0.01, 0.02, 0.03], "increasing"),
        ([0.001], "insufficient_data"),
    ],
)
def test_classifies_residual_trends(
    tmp_path,
    values,
    expected_trend,
):
    csv_file = tmp_path / "trend.csv"
    rows = [
        {"iteration": str(index), "Ux": str(value)}
        for index, value in enumerate(values, start=1)
    ]
    write_residual_csv(csv_file, rows)

    result = analyze_residuals(csv_file)
    ux = result["residuals"]["Ux"]

    assert ux["trend"] == expected_trend
    assert ux["trend_tolerance"] == pytest.approx(0.05)


def test_zero_residual_history_is_stagnating(tmp_path):
    csv_file = tmp_path / "zero_history.csv"
    rows = [
        {"iteration": "1", "Ux": "0"},
        {"iteration": "2", "Ux": "0"},
    ]
    write_residual_csv(csv_file, rows)

    result = analyze_residuals(csv_file)

    assert result["residuals"]["Ux"]["trend"] == "stagnating"

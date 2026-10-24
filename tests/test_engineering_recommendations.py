
from src.engineering_recommendations import generate_recommendations


def test_fatal_error_generates_high_priority_recommendation():
    results = generate_recommendations(
        {"fatal_error": True, "solver_completed": False}
    )

    assert any(
        item["priority"] == "High"
        and "fatal solver error" in item["title"].lower()
        for item in results
    )


def test_courant_exceedance_generates_review_recommendation():
    results = generate_recommendations(
        {
            "fatal_error": False,
            "solver_completed": True,
            "courant_max": [1.0, 6.2],
            "courant_threshold": 5.0,
        }
    )

    assert any(
        "Courant" in item["title"]
        and "exceed" in item["title"].lower()
        for item in results
    )


def test_missing_completion_marker_is_flagged():
    results = generate_recommendations(
        {"fatal_error": False, "solver_completed": False}
    )

    assert any(
        "completion is unconfirmed" in item["title"].lower()
        for item in results
    )


def test_residual_increases_trigger_review():
    results = generate_recommendations(
        {"fatal_error": False, "solver_completed": True},
        {
            "residuals": {
                "U": {
                    "below_tolerance": True,
                    "decreasing_overall": True,
                    "increases_count": 12,
                }
            }
        },
    )

    assert any(
        "residual trend" in item["title"].lower()
        for item in results
    )


def test_no_residual_analysis_is_reported():
    results = generate_recommendations(
        {"fatal_error": False, "solver_completed": True}
    )

    assert any(
        "residual trend analysis" in item["title"].lower()
        for item in results
    )


def test_recommendations_have_required_fields():
    results = generate_recommendations(
        {"fatal_error": False, "solver_completed": True}
    )

    required = {"priority", "title", "evidence", "action", "limitation"}

    assert results
    assert all(required.issubset(item) for item in results)
def test_poor_mesh_metrics_trigger_recommendations():
    mesh_analysis = {
        "mesh_ok": True,
        "failed_checks": [],
        "max_non_orthogonality": 80.0,
        "max_skewness": 5.0,
        "max_aspect_ratio": 120.0,
    }

    results = generate_recommendations(
        {"fatal_error": False, "solver_completed": True},
        None,
        mesh_analysis,
    )

    titles = [item["title"].lower() for item in results]

    assert any("non-orthogonality" in title for title in titles)
    assert any("skewness" in title for title in titles)
    assert any("aspect ratio" in title for title in titles)


def test_missing_mesh_ok_marker_triggers_review():
    mesh_analysis = {
        "mesh_ok": False,
        "failed_checks": [],
    }

    results = generate_recommendations(
        {"fatal_error": False, "solver_completed": True},
        None,
        mesh_analysis,
    )

    assert any(
        "mesh quality-check" in item["title"].lower()
        for item in results
    )


def test_mesh_failed_checks_trigger_review():
    mesh_analysis = {
        "mesh_ok": True,
        "failed_checks": ["Example failed check"],
    }

    results = generate_recommendations(
        {"fatal_error": False, "solver_completed": True},
        None,
        mesh_analysis,
    )

    assert any(
        "mesh checks" in item["title"].lower()
        for item in results
    )


def test_custom_mesh_thresholds_trigger_recommendations():
    mesh_analysis = {
        "mesh_ok": True,
        "failed_checks": [],
        "max_non_orthogonality": 10.0,
        "max_skewness": 1.0,
        "max_aspect_ratio": 20.0,
    }

    results = generate_recommendations(
        {"fatal_error": False, "solver_completed": True},
        None,
        mesh_analysis,
        {
            "max_non_orthogonality": 5.0,
            "max_skewness": 0.5,
            "max_aspect_ratio": 15.0,
        },
    )

    titles = [item["title"].lower() for item in results]

    assert any("non-orthogonality" in title for title in titles)
    assert any("skewness" in title for title in titles)
    assert any("aspect ratio" in title for title in titles)


def test_custom_mesh_thresholds_override_defaults():
    mesh_analysis = {
        "mesh_ok": True,
        "failed_checks": [],
        "max_non_orthogonality": 60.0,
        "max_skewness": 3.0,
        "max_aspect_ratio": 80.0,
    }

    results = generate_recommendations(
        {"fatal_error": False, "solver_completed": True},
        None,
        mesh_analysis,
        {
            "max_non_orthogonality": 50.0,
            "max_skewness": 2.0,
            "max_aspect_ratio": 70.0,
        },
    )

    titles = [item["title"].lower() for item in results]

    assert any("non-orthogonality" in title for title in titles)
    assert any("skewness" in title for title in titles)
    assert any("aspect ratio" in title for title in titles)


def test_default_mesh_thresholds_preserve_existing_behavior():
    mesh_analysis = {
        "mesh_ok": True,
        "failed_checks": [],
        "max_non_orthogonality": 60.0,
        "max_skewness": 3.0,
        "max_aspect_ratio": 80.0,
    }

    results = generate_recommendations(
        {"fatal_error": False, "solver_completed": True},
        None,
        mesh_analysis,
    )

    mesh_titles = [
        item["title"].lower()
        for item in results
        if "non-orthogonality" in item["title"].lower()
        or "skewness" in item["title"].lower()
        or "aspect ratio" in item["title"].lower()
    ]

    assert mesh_titles == []


def test_custom_mesh_thresholds_trigger_recommendations():
    mesh_analysis = {
        "mesh_ok": True,
        "failed_checks": [],
        "max_non_orthogonality": 10.0,
        "max_skewness": 1.0,
        "max_aspect_ratio": 20.0,
    }

    results = generate_recommendations(
        {"fatal_error": False, "solver_completed": True},
        None,
        mesh_analysis,
        {
            "max_non_orthogonality": 5.0,
            "max_skewness": 0.5,
            "max_aspect_ratio": 15.0,
        },
    )

    titles = [item["title"].lower() for item in results]

    assert any("non-orthogonality" in title for title in titles)
    assert any("skewness" in title for title in titles)
    assert any("aspect ratio" in title for title in titles)


def test_custom_mesh_thresholds_override_defaults():
    mesh_analysis = {
        "mesh_ok": True,
        "failed_checks": [],
        "max_non_orthogonality": 60.0,
        "max_skewness": 3.0,
        "max_aspect_ratio": 80.0,
    }

    results = generate_recommendations(
        {"fatal_error": False, "solver_completed": True},
        None,
        mesh_analysis,
        {
            "max_non_orthogonality": 50.0,
            "max_skewness": 2.0,
            "max_aspect_ratio": 70.0,
        },
    )

    titles = [item["title"].lower() for item in results]

    assert any("non-orthogonality" in title for title in titles)
    assert any("skewness" in title for title in titles)
    assert any("aspect ratio" in title for title in titles)


def test_default_mesh_thresholds_preserve_existing_behavior():
    mesh_analysis = {
        "mesh_ok": True,
        "failed_checks": [],
        "max_non_orthogonality": 60.0,
        "max_skewness": 3.0,
        "max_aspect_ratio": 80.0,
    }

    results = generate_recommendations(
        {"fatal_error": False, "solver_completed": True},
        None,
        mesh_analysis,
    )

    mesh_titles = [
        item["title"].lower()
        for item in results
        if "non-orthogonality" in item["title"].lower()
        or "skewness" in item["title"].lower()
        or "aspect ratio" in item["title"].lower()
    ]

    assert mesh_titles == []


import pytest


@pytest.mark.parametrize(
    ("trend", "expected_title"),
    [
        ("decreasing", "decreasing residual trend"),
        ("stagnating", "stagnating residual"),
        ("increasing", "increasing residual"),
        ("insufficient_data", "collect more residual data"),
    ],
)
def test_explicit_residual_trends_generate_recommendations(
    trend,
    expected_title,
):
    results = generate_recommendations(
        {"fatal_error": False, "solver_completed": True},
        {
            "residuals": {
                "U": {
                    "trend": trend,
                    "sample_count": 1 if trend == "insufficient_data" else 5,
                    "below_tolerance": False,
                    "decreasing_overall": trend == "decreasing",
                    "increases_count": 0,
                }
            }
        },
    )

    assert any(
        expected_title in item["title"].lower()
        for item in results
    )
    assert all(
        {"priority", "title", "evidence", "action", "limitation"}
        .issubset(item)
        for item in results
    )

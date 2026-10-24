
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



"""Parse mesh-quality metrics from an OpenFOAM checkMesh report."""

from pathlib import Path
import math
import re
from typing import Any


def analyze_mesh_log(log_path: str | Path) -> dict[str, Any]:
    """Extract mesh statistics and quality-check results."""

    path = Path(log_path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(f"Mesh log file not found: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")

    def find_int(pattern: str) -> int | None:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return int(match.group(1)) if match else None

    def find_float(pattern: str) -> float | None:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if not match:
            return None

        value = float(match.group(1))
        return value if math.isfinite(value) else None

    result: dict[str, Any] = {
        "file": str(path),
        "openfoam_version": None,
        "points": find_int(r"^\s*points:\s*(\d+)"),
        "faces": find_int(r"^\s*faces:\s*(\d+)"),
        "internal_faces": find_int(r"^\s*internal faces:\s*(\d+)"),
        "cells": find_int(r"^\s*cells:\s*(\d+)"),
        "boundary_patches": find_int(r"^\s*boundary patches:\s*(\d+)"),
        "max_aspect_ratio": find_float(
            r"Max aspect ratio\s*=\s*([0-9.eE+-]+)"
        ),
        "max_non_orthogonality": find_float(
            r"Mesh non-orthogonality Max:\s*([0-9.eE+-]+)"
        ),
        "average_non_orthogonality": find_float(
            r"Mesh non-orthogonality Max:\s*[0-9.eE+-]+"
            r"\s+average:\s*([0-9.eE+-]+)"
        ),
        "max_skewness": find_float(
            r"Max skewness\s*=\s*([0-9.eE+-]+)"
        ),
        "max_cell_openness": find_float(
            r"Max cell openness\s*=\s*([0-9.eE+-]+)"
        ),
        "mesh_ok": bool(
            re.search(r"^\s*Mesh OK\.\s*$", text, re.MULTILINE)
        ),
        "end_marker": bool(
            re.search(r"^\s*End\s*$", text, re.MULTILINE)
        ),
        "failed_checks": [],
        "warnings": [],
        "summary": [],
    }

    # Version is usually on a separate line from the OpenFOAM header.
    version_match = re.search(
        r"\bVersion:\s*(\d+)",
        text,
        re.MULTILINE,
    )
    if version_match:
        result["openfoam_version"] = version_match.group(1)

    result["failed_checks"] = [
        line.strip()
        for line in text.splitlines()
        if re.search(r"\bfailed\b|\bfailure\b", line, re.IGNORECASE)
    ]

    result["warnings"] = [
        line.strip()
        for line in text.splitlines()
        if "warning" in line.lower()
    ]

    if result["mesh_ok"]:
        result["summary"].append(
            "The checkMesh report contains the 'Mesh OK.' marker."
        )
    else:
        result["summary"].append(
            "The 'Mesh OK.' marker was not found. "
            "Inspect the full checkMesh output."
        )

    if result["failed_checks"]:
        result["summary"].append(
            f"Potential failed-check messages found: "
            f"{len(result['failed_checks'])}."
        )

    if result["max_non_orthogonality"] is not None:
        result["summary"].append(
            "Maximum non-orthogonality: "
            f"{result['max_non_orthogonality']:g} degrees."
        )

    if result["max_skewness"] is not None:
        result["summary"].append(
            f"Maximum skewness: {result['max_skewness']:g}."
        )

    return result


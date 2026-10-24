# SimuNexa CAE Copilot

Python-based prototype for CFD solver-log analysis, residual extraction, automated plotting, and basic diagnostic checks.

## Features

- Parse OpenFOAM-style solver logs.
- Extract residuals and iteration information.
- Export residual data to CSV.
- Generate residual-history plots.
- Detect common solver errors.
- Run automated tests using pytest.

## Technology Stack

- Python 3.12+
- OpenFOAM
- Matplotlib
- pytest
- Git

## Setup

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt

## Run the analyzer

    python -m src.log_parser results/sample/sample_solver.log

## Run tests

    python -m pytest -v

## Roadmap

- Improve solver-log parsing.
- Add convergence diagnostics.
- Add engineering validation metrics.
- Generate automated engineering reports.
- Explore AI-assisted CFD diagnostics.
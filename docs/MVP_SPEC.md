# MVP Specification - ECL Staging Explorer

## Objective

Build a simple commercial and pedagogical demonstrator for IFRS 9 staging, data quality controls and simplified Expected Credit Loss calculations.

## Scope V0.1

- Synthetic portfolio generation only.
- Basic data quality checks.
- Simplified Stage 1, Stage 2 and Stage 3 rules.
- Simplified ECL calculation.
- Streamlit dashboard.
- Excel export.
- Unit tests for core business rules.

## Out of Scope V0.1

- Advanced macroeconomic scenarios.
- Management overlays.
- Detailed audit trail.
- Committee summary note.
- Production-grade IFRS 9 engine.

## Simplifying Assumptions

- Ratings are numeric from 1 to 10.
- A higher numeric rating means a weaker credit quality.
- Stage 3 has priority over Stage 2.
- Stage 1 uses 12-month PD.
- Stage 2 uses lifetime PD.
- Stage 3 uses a 100 percent PD proxy.

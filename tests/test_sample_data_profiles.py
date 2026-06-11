from modules.sample_data import (
    DATA_QUALITY_LEVELS,
    DEMO_PORTFOLIO_PROFILES,
    generate_demo_portfolio,
)


def test_all_demo_profiles_generate_expected_number_of_rows():
    for profile in DEMO_PORTFOLIO_PROFILES:
        portfolio = generate_demo_portfolio(profile=profile, n_exposures=100, seed=7)
        assert len(portfolio) == 100
        assert "loan_id" in portfolio.columns


def test_low_risk_profile_has_no_defaults():
    portfolio = generate_demo_portfolio(profile="Low Risk Portfolio", n_exposures=200, seed=7)
    assert portfolio["default_flag"].sum() == 0
    assert portfolio["pd_12m"].max() <= 0.08


def test_data_quality_profile_injects_anomalies():
    portfolio = generate_demo_portfolio(profile="Data Quality Issues Portfolio", n_exposures=200, seed=7)
    assert portfolio["current_rating"].isna().sum() > 0
    assert portfolio["pd_12m"].isna().sum() > 0
    assert (portfolio["ead"] <= 0).sum() > 0


def test_cre_stress_profile_increases_real_estate_share():
    portfolio = generate_demo_portfolio(profile="CRE Stress Portfolio", n_exposures=200, seed=7)
    assert (portfolio["sector"] == "Real estate").mean() > 0.35


def test_generated_portfolio_contains_staging_transition_fields():
    portfolio = generate_demo_portfolio(
        profile="Balanced Portfolio",
        n_exposures=100,
        seed=7,
    )

    expected_fields = {
        "previous_stage",
        "origination_pd_12m",
        "sicr_flag",
        "credit_impaired_flag",
        "unlikely_to_pay_flag",
        "bankruptcy_flag",
        "distressed_restructuring_flag",
        "payment_normalized_flag",
        "cure_period_months",
        "probation_required_months",
    }
    assert expected_fields.issubset(portfolio.columns)


def test_all_data_quality_levels_preserve_portfolio_size():
    for level in DATA_QUALITY_LEVELS:
        portfolio = generate_demo_portfolio(
            profile="Balanced Portfolio",
            n_exposures=200,
            seed=7,
            data_quality_level=level,
        )
        assert len(portfolio) == 200


def test_data_quality_levels_inject_progressively_more_anomalies():
    high_quality = generate_demo_portfolio(
        profile="Balanced Portfolio",
        n_exposures=1_000,
        seed=7,
        data_quality_level="Tres bonne qualite",
    )
    average_quality = generate_demo_portfolio(
        profile="Balanced Portfolio",
        n_exposures=1_000,
        seed=7,
        data_quality_level="Qualite moyenne",
    )
    poor_quality = generate_demo_portfolio(
        profile="Balanced Portfolio",
        n_exposures=1_000,
        seed=7,
        data_quality_level="Qualite mediocre",
    )

    def injected_issue_count(portfolio):
        return (
            portfolio["current_rating"].isna().sum()
            + portfolio["pd_12m"].isna().sum()
            + portfolio["lgd"].isna().sum()
            + (portfolio["ead"] <= 0).sum()
            + (portfolio["days_past_due"] < 0).sum()
            + portfolio["loan_id"].duplicated(keep=False).sum()
        )

    assert injected_issue_count(high_quality) == 0
    assert injected_issue_count(average_quality) > 0
    assert injected_issue_count(poor_quality) > injected_issue_count(average_quality)

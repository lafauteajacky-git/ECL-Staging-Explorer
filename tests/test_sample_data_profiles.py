from modules.sample_data import DEMO_PORTFOLIO_PROFILES, generate_demo_portfolio


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

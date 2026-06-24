from opportunityforge.models.domain import FrictionProfile, ScoreBreakdown
from opportunityforge.services.scoring import calculate_opportunity_score, summarize_friction


def test_opportunity_score_product_excludes_engineering_effort() -> None:
    score = ScoreBreakdown(
        demand=8,
        decision_value=9,
        monetization_ease=7,
        defensibility=6,
        strategic_fit=5,
    )

    assert calculate_opportunity_score(score) == 15120


def test_friction_is_summarized_separately_from_score() -> None:
    profile = FrictionProfile(
        data_friction=4,
        trust_friction=9,
        distribution_friction=6,
        sales_friction=7,
        regulatory_friction=5,
        maintenance_friction=3,
    )

    assert summarize_friction(profile) == "Highest visible risk: trust friction (9/10)."

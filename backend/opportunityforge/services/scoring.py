from opportunityforge.models.domain import FrictionProfile, ScoreBreakdown


def calculate_opportunity_score(score: ScoreBreakdown) -> int:
    """Return the auditable opportunity score product.

    Development effort is intentionally excluded from the formula.
    """
    return score.opportunity_score


def summarize_friction(profile: FrictionProfile) -> str:
    """Summarize risk visibility without altering opportunity rank."""
    values = {
        "data": profile.data_friction,
        "trust": profile.trust_friction,
        "distribution": profile.distribution_friction,
        "sales": profile.sales_friction,
        "regulatory": profile.regulatory_friction,
        "maintenance": profile.maintenance_friction,
    }
    highest = max(values, key=values.get)
    return f"Highest visible risk: {highest} friction ({values[highest]}/10)."

from typing import Any

REQUIRED_DOSSIER_SECTIONS = [
    "Executive Summary",
    "Target User",
    "Decision Being Made",
    "Why This Matters",
    "Data Sources",
    "Demand Analysis",
    "Buyer Analysis",
    "Monetization Analysis",
    "Competitive Landscape",
    "Opportunity Score",
    "Friction Profile",
    "MVP Recommendation",
    "30-Day Validation Plan",
    "Risks",
    "Why This Could Win",
    "Why This Could Fail",
    "Next Actions",
]


def empty_dossier() -> dict[str, Any]:
    return {section: "" for section in REQUIRED_DOSSIER_SECTIONS}

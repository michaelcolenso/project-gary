from fastapi import APIRouter

from opportunityforge.agents.dossier import REQUIRED_DOSSIER_SECTIONS
from opportunityforge.models.domain import FrictionProfile, ScoreBreakdown
from opportunityforge.services.scoring import calculate_opportunity_score, summarize_friction

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/dossier/sections")
def dossier_sections() -> dict[str, list[str]]:
    return {"sections": REQUIRED_DOSSIER_SECTIONS}


@router.post("/score")
def score_opportunity(score: ScoreBreakdown) -> dict[str, int]:
    return {"opportunity_score": calculate_opportunity_score(score)}


@router.post("/friction/summary")
def friction_summary(profile: FrictionProfile) -> dict[str, str]:
    return {"summary": summarize_friction(profile)}

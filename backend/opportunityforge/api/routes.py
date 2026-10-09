from fastapi import APIRouter

from opportunityforge.agents.dossier import REQUIRED_DOSSIER_SECTIONS
from opportunityforge.evaluation_gates import evaluate_pair
from opportunityforge.models.domain import FrictionProfile, GateEvaluationRequest, ScoreBreakdown
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


@router.post("/evaluate/gates")
def evaluate_gates(request: GateEvaluationRequest) -> dict[str, object]:
    """Run a dataset-pair candidate through the Layer 2 evaluation gates
    (population overlap, competitive landscape, buyer validation, pricing
    cap, killer question) and return the compound value score + per-gate
    pass/fail breakdown."""
    result = evaluate_pair(**request.model_dump())
    return {
        "source_title": result.source_title,
        "target_title": result.target_title,
        "link_confidence": result.link_confidence,
        "population_overlap_pct": result.population_overlap_pct,
        "compound_value_score": result.compound_value_score,
        "killed": result.killed,
        "kill_reason": result.kill_reason,
        "all_passed": result.all_passed,
        "gates": [
            {
                "name": g.name,
                "passed": g.passed,
                "score": g.score,
                "reason": g.reason,
                "evidence": g.evidence,
            }
            for g in result.gates
        ],
    }

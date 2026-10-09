"""
Evaluation Gates — Layer 2 hardening for the linker.

Before an agent can assign a compound_value_score, these gates
must be passed. Each gate requires specific evidence that moves
evaluation from "I think this is cool" to "this has evidence."

Gates:
1. POPULATION OVERLAP — Hard kill if < 5% (from population_overlap.py)
2. COMPETITIVE LANDSCAPE — 3+ named competitors required, auto-scraped
3. BUYER VALIDATION — Specific job title + real company, not persona
4. PRICING CAP — $500/month max for year one
5. KILLER QUESTION — "Who loses their job if this doesn't exist?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GateResult:
    """Result of a single evaluation gate."""
    name: str
    passed: bool
    score: int  # 0-10 impact on compound value
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass 
class EvaluationResult:
    """Full evaluation of a dataset pair through all gates."""
    source_title: str
    target_title: str
    link_confidence: float
    population_overlap_pct: float
    gates: list[GateResult] = field(default_factory=list)
    compound_value_score: int = 0
    killed: bool = False
    kill_reason: str = ""

    @property
    def all_passed(self) -> bool:
        return all(g.passed for g in self.gates)


# ── Gate implementations ────────────────────────────────────────

def gate_population_overlap(overlap_pct: float) -> GateResult:
    """HARD GATE: population overlap must be ≥ 5% or unknown."""
    if overlap_pct < 0.05:
        return GateResult(
            name="Population Overlap",
            passed=False,
            score=0,
            reason=f"Overlap {overlap_pct:.1%} < 5% — different entity populations. HARD KILL.",
            evidence={"overlap_pct": overlap_pct},
        )
    return GateResult(
        name="Population Overlap",
        passed=True,
        score=0,
        reason=f"Overlap {overlap_pct:.1%} ≥ 5% — real population intersection exists.",
        evidence={"overlap_pct": overlap_pct},
    )


def gate_competitive_landscape(
    compound_name: str,
    competitors: list[str],
) -> GateResult:
    """Requires 3+ named competitors or substitutes.

    "No competitor" is almost always wrong. Even "nobody does this exact thing"
    means "the existing manual process is the competitor."
    """
    if len(competitors) < 3:
        return GateResult(
            name="Competitive Landscape",
            passed=False,
            score=-2,
            reason=f"Only {len(competitors)} competitor(s) named. Required: 3+. "
                   f"If no direct competitor exists, the manual process IS the competitor. "
                   f"Examples: 'manual weather.gov checking', 'Bloomberg terminal', "
                   f"'internal Excel spreadsheet'.",
            evidence={"competitors": competitors},
        )
    return GateResult(
        name="Competitive Landscape",
        passed=True,
        score=0,
        reason=f"{len(competitors)} competitors identified.",
        evidence={"competitors": competitors},
    )


def gate_buyer_validation(
    job_title: str,
    company_example: str,
) -> GateResult:
    """Requires a specific job title AND a real company where that role exists.

    No: "compliance officer at large banks"
    Yes: "VP of Supplier Risk Management at Walmart"
    """
    if not job_title or not company_example:
        return GateResult(
            name="Buyer Validation",
            passed=False,
            score=-2,
            reason="Must specify: specific job title AND a real company. "
                   "No personas. No 'compliance officers at large banks.' "
                   "Format: 'VP of X at [Real Company Name]'",
            evidence={},
        )

    # Check for persona-level vagueness
    vague_signals = ["officer", "manager", "analyst", "professional"]
    title_words = set(job_title.lower().split())
    if not (title_words - set(vague_signals)):
        return GateResult(
            name="Buyer Validation",
            passed=False,
            score=-1,
            reason=f"Job title too vague: '{job_title}'. Add department, seniority, "
                   f"or specific function. Example: 'Director of Power Trading at Citadel'",
            evidence={"job_title": job_title, "company": company_example},
        )

    return GateResult(
        name="Buyer Validation",
        passed=True,
        score=0,
        reason=f"Specific buyer: {job_title} at {company_example}.",
        evidence={"job_title": job_title, "company": company_example},
    )


def gate_pricing_cap(price_monthly: int) -> GateResult:
    """Cap pricing at $500/month for year one (solo developer)."""
    if price_monthly > 500:
        return GateResult(
            name="Pricing Reality",
            passed=False,
            score=-1,
            reason=f"${price_monthly}/month exceeds $500 solo-dev cap. "
                   f"Enterprise pricing requires case studies, SOC 2, and a sales team. "
                   f"Year one: cap at $500/month self-serve.",
            evidence={"price": price_monthly},
        )
    if price_monthly > 200:
        return GateResult(
            name="Pricing Reality",
            passed=True,
            score=0,
            reason=f"${price_monthly}/month — high but acceptable for self-serve B2B.",
            evidence={"price": price_monthly},
        )
    return GateResult(
        name="Pricing Reality",
        passed=True,
        score=0,
        reason=f"${price_monthly}/month — well within solo-dev range.",
        evidence={"price": price_monthly},
    )


def gate_killer_question(who_loses_job: str) -> GateResult:
    """"Who loses their job if this product doesn't exist?"

    If nobody loses their job → this is a vitamin, not a painkiller → score = 0.
    """
    if not who_loses_job or who_loses_job.lower() in ("nobody", "no one", "none", "n/a", ""):
        return GateResult(
            name="Killer Question",
            passed=False,
            score=-3,
            reason="Nobody loses their job if this doesn't exist. "
                   "This is a vitamin, not a painkiller. Compound value ≤ 3.",
            evidence={},
        )

    # Check for vague answers
    if len(who_loses_job) < 20:
        return GateResult(
            name="Killer Question",
            passed=False,
            score=-1,
            reason="Answer too vague. Be specific: name a real role at a real company "
                   "whose job performance depends on this data existing.",
            evidence={"answer": who_loses_job},
        )

    return GateResult(
        name="Killer Question",
        passed=True,
        score=2,
        reason=f"Real consequence: {who_loses_job[:120]}...",
        evidence={"answer": who_loses_job},
    )


# ── Full evaluation ─────────────────────────────────────────────

def evaluate_pair(
    source_title: str,
    target_title: str,
    link_confidence: float,
    population_overlap_pct: float,
    competitors: list[str],
    buyer_job_title: str,
    buyer_company: str,
    price_monthly: int,
    killer_answer: str,
) -> EvaluationResult:
    """Run all gates on a dataset pair and produce a compound value score.

    Returns an EvaluationResult with pass/fail per gate and final score.
    If any HARD gate fails, compound_value_score is forced to 0.
    """
    result = EvaluationResult(
        source_title=source_title,
        target_title=target_title,
        link_confidence=link_confidence,
        population_overlap_pct=population_overlap_pct,
    )

    # Gate 1: Population overlap (HARD KILL)
    g1 = gate_population_overlap(population_overlap_pct)
    result.gates.append(g1)
    if not g1.passed:
        result.killed = True
        result.kill_reason = g1.reason
        result.compound_value_score = 0
        return result

    # Gate 2: Competitive landscape
    g2 = gate_competitive_landscape(f"{source_title[:30]} × {target_title[:30]}", competitors)
    result.gates.append(g2)

    # Gate 3: Buyer validation
    g3 = gate_buyer_validation(buyer_job_title, buyer_company)
    result.gates.append(g3)

    # Gate 4: Pricing cap
    g4 = gate_pricing_cap(price_monthly)
    result.gates.append(g4)

    # Gate 5: Killer question
    g5 = gate_killer_question(killer_answer)
    result.gates.append(g5)

    # Compute compound value: base 5 + gate score adjustments
    # Max: 10, Min: 0 (if hard-gated)
    base_score = 5
    adjustments = sum(g.score for g in result.gates)
    result.compound_value_score = max(0, min(10, base_score + adjustments))

    if not result.all_passed:
        result.killed = True
        result.kill_reason = "; ".join(
            g.reason for g in result.gates if not g.passed
        )
        result.compound_value_score = 0

    return result


def format_evaluation(result: EvaluationResult) -> str:
    """Pretty-print an evaluation result."""
    lines = [
        f"{'='*60}",
        f"  {result.source_title[:40]}",
        f"  × {result.target_title[:40]}",
        f"{'='*60}",
        f"  Link confidence: {result.link_confidence:.3f}",
        f"  Population overlap: {result.population_overlap_pct:.1%}",
        f"  Compound value: {result.compound_value_score}/10",
        f"  Status: {'KILLED' if result.killed else 'SURVIVES'}",
    ]
    if result.killed:
        lines.append(f"  Reason: {result.kill_reason[:200]}")

    lines.append(f"\n  Gates:")
    for g in result.gates:
        icon = "✓" if g.passed else "✗"
        lines.append(f"    {icon} {g.name}: {g.reason[:120]}")
    
    lines.append("")
    return "\n".join(lines)

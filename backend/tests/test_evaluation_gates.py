from opportunityforge.evaluation_gates import (
    evaluate_pair,
    format_evaluation,
    gate_buyer_validation,
    gate_competitive_landscape,
    gate_killer_question,
    gate_pricing_cap,
    gate_population_overlap,
)


def test_gate_population_overlap_hard_kills_below_five_percent() -> None:
    result = gate_population_overlap(0.02)
    assert result.passed is False
    assert result.score == 0


def test_gate_population_overlap_passes_at_or_above_five_percent() -> None:
    result = gate_population_overlap(0.05)
    assert result.passed is True


def test_gate_competitive_landscape_requires_three_competitors() -> None:
    result = gate_competitive_landscape("X", ["Only One"])
    assert result.passed is False
    assert result.score == -2

    result = gate_competitive_landscape("X", ["A", "B", "C"])
    assert result.passed is True
    assert result.score == 0


def test_gate_buyer_validation_rejects_missing_fields() -> None:
    result = gate_buyer_validation("", "")
    assert result.passed is False
    assert result.score == -2


def test_gate_buyer_validation_rejects_vague_titles() -> None:
    result = gate_buyer_validation("Manager", "Acme")
    assert result.passed is False
    assert result.score == -1


def test_gate_buyer_validation_accepts_specific_role() -> None:
    result = gate_buyer_validation("VP of Supplier Risk Management", "Walmart")
    assert result.passed is True
    assert result.score == 0


def test_gate_pricing_cap_rejects_over_500() -> None:
    result = gate_pricing_cap(1500)
    assert result.passed is False
    assert result.score == -1


def test_gate_pricing_cap_accepts_within_cap() -> None:
    result = gate_pricing_cap(99)
    assert result.passed is True
    assert result.score == 0


def test_gate_killer_question_rejects_nobody() -> None:
    result = gate_killer_question("nobody")
    assert result.passed is False
    assert result.score == -3


def test_gate_killer_question_rejects_vague_answer() -> None:
    result = gate_killer_question("the compliance team")
    assert result.passed is False
    assert result.score == -1


def test_gate_killer_question_accepts_specific_consequence() -> None:
    result = gate_killer_question(
        "The VP of Supplier Risk at Walmart misses recall notices and faces liability."
    )
    assert result.passed is True
    assert result.score == 2


def test_evaluate_pair_hard_kills_on_population_overlap() -> None:
    result = evaluate_pair(
        source_title="Dataset A",
        target_title="Dataset B",
        link_confidence=0.9,
        population_overlap_pct=0.01,
        competitors=["A", "B", "C"],
        buyer_job_title="VP of Risk",
        buyer_company="Acme",
        price_monthly=99,
        killer_answer="Someone loses their job without this data existing today.",
    )
    assert result.killed is True
    assert result.compound_value_score == 0
    # Only the hard-kill gate should have run — the rest are short-circuited.
    assert len(result.gates) == 1


def test_evaluate_pair_computes_compound_value_when_all_gates_pass() -> None:
    result = evaluate_pair(
        source_title="Dataset A",
        target_title="Dataset B",
        link_confidence=0.8,
        population_overlap_pct=0.5,
        competitors=["A", "B", "C"],
        buyer_job_title="VP of Supplier Risk Management",
        buyer_company="Walmart",
        price_monthly=99,
        killer_answer="The VP of Supplier Risk at Walmart misses recall notices without this.",
    )
    assert result.killed is False
    assert result.compound_value_score == 7  # base 5 + killer_question bonus (2)
    assert len(result.gates) == 5
    assert result.all_passed is True


def test_evaluate_pair_kills_when_any_soft_gate_fails() -> None:
    result = evaluate_pair(
        source_title="Dataset A",
        target_title="Dataset B",
        link_confidence=0.8,
        population_overlap_pct=0.5,
        competitors=["Only One"],  # fails competitive landscape gate
        buyer_job_title="VP of Supplier Risk Management",
        buyer_company="Walmart",
        price_monthly=99,
        killer_answer="The VP of Supplier Risk at Walmart misses recall notices without this.",
    )
    assert result.killed is True
    assert result.compound_value_score == 0
    assert "competitor" in result.kill_reason.lower()


def test_format_evaluation_includes_gate_status() -> None:
    result = evaluate_pair(
        source_title="Dataset A",
        target_title="Dataset B",
        link_confidence=0.8,
        population_overlap_pct=0.01,
        competitors=[],
        buyer_job_title="",
        buyer_company="",
        price_monthly=0,
        killer_answer="",
    )
    text = format_evaluation(result)
    assert "KILLED" in text
    assert "Population Overlap" in text

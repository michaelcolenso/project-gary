from opportunityforge.population_overlap import (
    compute_overlap,
    fuzzy_match,
    normalize_entity,
    population_overlap_gate,
)


def test_normalize_entity_strips_legal_suffixes() -> None:
    assert normalize_entity("Acme Corp.") == "acme"
    assert normalize_entity("Widget Industries, LLC") == "widget industries"
    assert normalize_entity("Example Co., Ltd.") == "example"


def test_normalize_entity_handles_non_entities() -> None:
    assert normalize_entity("") == ""
    assert normalize_entity("N/A") == ""
    assert normalize_entity("Unknown") == ""
    assert normalize_entity(None) == ""  # type: ignore[arg-type]


def test_normalize_entity_strips_dba_sections() -> None:
    # "Co" is itself a legal-suffix token, so it's stripped along with d/b/a.
    assert normalize_entity("Big Co d/b/a Little Shop") == "big"


def test_fuzzy_match_exact_after_normalization() -> None:
    assert fuzzy_match("acme", "acme") is True


def test_fuzzy_match_substring_with_length_ratio() -> None:
    assert fuzzy_match("covidien", "covidien lp") is True
    # Too short a substring relative to the longer string should not match.
    assert fuzzy_match("co", "covidien international holdings") is False


def test_fuzzy_match_rejects_dissimilar_names() -> None:
    assert fuzzy_match("acme corp", "totally different entity") is False


def test_fuzzy_match_empty_inputs() -> None:
    assert fuzzy_match("", "acme") is False
    assert fuzzy_match("acme", "") is False


def test_compute_overlap_counts_matched_pairs() -> None:
    # compute_overlap uses a strict SequenceMatcher ratio (not fuzzy_match's
    # lenient substring/token logic), so only near-identical normalized
    # names match: "Acme Inc." / "Acme Corp" both normalize to "acme".
    # "Widget LLC" -> "widget" vs "Widget Industries" -> "widget industries"
    # falls below the 0.85 ratio threshold and does NOT match.
    result = compute_overlap(
        ["Acme Inc.", "Widget LLC", "Totally Unique Co"],
        ["Acme Corp", "Widget Industries"],
    )
    assert result["overlap_count"] == 1
    assert result["total_a"] == 3
    assert result["total_b"] == 2
    assert result["killed"] is False


def test_compute_overlap_kills_below_five_percent() -> None:
    result = compute_overlap(
        [f"Company {i}" for i in range(50)],
        ["Totally Different Firm"],
    )
    assert result["overlap_pct"] < 0.05
    assert result["killed"] is True


def test_compute_overlap_empty_lists_do_not_crash() -> None:
    result = compute_overlap([], [])
    assert result["overlap_count"] == 0
    assert result["overlap_pct"] == 0.0
    assert result["killed"] is True


def test_population_overlap_gate_unknown_when_no_samples(monkeypatch) -> None:
    import opportunityforge.population_overlap as pop

    monkeypatch.setattr(pop, "sample_entity_list", lambda *_: [])
    result = population_overlap_gate("a", "b", "Unmappable Dataset A", "Unmappable Dataset B")
    assert result["unknown"] is True
    assert result["killed"] is False


def test_population_overlap_gate_kills_low_overlap(monkeypatch) -> None:
    import opportunityforge.population_overlap as pop

    samples = {
        "A": [f"Company {i}" for i in range(20)],
        "B": ["Nothing Like Them Inc"],
    }
    monkeypatch.setattr(
        pop, "sample_entity_list", lambda _id, title: samples.get(title, [])
    )
    result = population_overlap_gate("a", "b", "A", "B")
    assert result["unknown"] is False
    assert result["killed"] is True
    assert "KILLED" in result["reason"]


def test_population_overlap_gate_survives_real_overlap(monkeypatch) -> None:
    import opportunityforge.population_overlap as pop

    samples = {
        "A": ["Acme Inc.", "Widget LLC", "Gizmo Corp"],
        "B": ["Acme Corporation", "Widget Industries", "Gizmo Co."],
    }
    monkeypatch.setattr(
        pop, "sample_entity_list", lambda _id, title: samples.get(title, [])
    )
    result = population_overlap_gate("a", "b", "A", "B")
    assert result["unknown"] is False
    assert result["killed"] is False
    assert "survives" in result["reason"]

"""
Dataset Linker — Layer 1: automated structural matching.

Scans all profiled datasets and scores every pair on entity overlap,
join key compatibility, and geographic alignment. Produces a ranked
list of link candidates for me (the agent) to evaluate in Layer 2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations
from typing import Any
from uuid import UUID

from sqlmodel import Session as DBSession, create_engine, select

from opportunityforge.models.domain import (
    DatasetLink,
    DatasetProfile,
    DatasetRecord,
)

DB_PATH = __import__("opportunityforge.pipeline", fromlist=["DB_PATH"]).DB_PATH
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)


# ── Matching helpers ────────────────────────────────────────────

# Known entity type families for cross-dataset matching
ENTITY_FAMILIES: dict[str, list[str]] = {
    "company": [
        "company", "recalling firm", "organization", "business",
        "corporation", "firm", "manufacturer", "brand",
    ],
    "person": [
        "person", "individual", "owner", "officer", "employee",
    ],
    "location": [
        "location", "address", "city", "state", "country",
        "manufacturing location", "geography",
    ],
    "product": [
        "product", "item", "drug", "device", "food",
        "vehicle", "equipment",
    ],
    "regulation": [
        "classification severity", "violation type", "regulation",
        "enforcement action", "compliance status",
    ],
}


def _normalize(s: str) -> str:
    return s.lower().strip()


def _entity_family(entity: str) -> str | None:
    """Map an entity type string to a family key, or None if unknown."""
    e = _normalize(entity)
    for family, members in ENTITY_FAMILIES.items():
        if e in members or any(m in e for m in members):
            return family
    return None


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity of two sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _entity_overlap(a: DatasetProfile, b: DatasetProfile) -> float:
    """Score how well two datasets' entity types align (0.0–1.0)."""
    families_a = {_entity_family(e) for e in a.entity_types if _entity_family(e)}
    families_b = {_entity_family(e) for e in b.entity_types if _entity_family(e)}

    if not families_a or not families_b:
        return 0.0

    # Direct Jaccard on entity families
    direct = _jaccard(families_a, families_b)

    # Bonus if they share the MOST specific entity type
    specific_overlap = len(set(a.entity_types) & set(b.entity_types))
    bonus = 0.2 if specific_overlap > 0 else 0.0

    return min(direct + bonus, 1.0)


def _geo_overlap(a: DatasetProfile, b: DatasetProfile, a_record: DatasetRecord, b_record: DatasetRecord) -> float:
    """Score geographic alignment (0.0–1.0)."""
    geo_a = (_normalize(a_record.geography or "")
             if a_record.geography else "")
    geo_b = (_normalize(b_record.geography or "")
             if b_record.geography else "")

    if not geo_a or not geo_b:
        return 0.5  # neutral — no geo info to contradict

    # Same country match
    countries = {"united states", "us", "usa", "u.s.", "nationwide"}
    a_is_us = any(c in geo_a for c in countries)
    b_is_us = any(c in geo_b for c in countries)
    if a_is_us and b_is_us:
        return 1.0

    # If both mention "international" or "worldwide"
    global_terms = {"worldwide", "international", "global", "foreign"}
    a_is_global = any(t in geo_a for t in global_terms)
    b_is_global = any(t in geo_b for t in global_terms)
    if a_is_global or b_is_global:
        return 0.8

    return 0.3


def _join_key_overlap(a: DatasetProfile, b: DatasetProfile) -> float:
    """Score join key compatibility (0.0–1.0)."""
    if not a.join_keys or not b.join_keys:
        return 0.0

    keys_a = {_normalize(k) for k in a.join_keys}
    keys_b = {_normalize(k) for k in b.join_keys}

    # Direct key overlap
    overlap = keys_a & keys_b
    if overlap:
        return 1.0

    # Family-level match: e.g. "company_name" ~ "recalling_firm"
    for ka in keys_a:
        for kb in keys_b:
            if ka.split("_")[-1] == kb.split("_")[-1]:
                return 0.6

    return 0.0


def _temporal_overlap(a: DatasetProfile, b: DatasetProfile) -> float:
    """Score temporal alignment (0.0–1.0). Most datasets are recent, so default neutral."""
    return 0.7  # conservative positive — most public datasets overlap temporally


# ── Public API ──────────────────────────────────────────────────


def find_potential_links() -> list[dict[str, Any]]:
    """Scan all dataset pairs and return ranked link candidates.

    Layer 1 (automated) — suggests links based on structural match.
    Layer 2 (agent) — I evaluate each candidate and assign compound value.
    """
    with DBSession(engine, expire_on_commit=False) as db:
        records = db.exec(
            select(DatasetRecord).order_by(DatasetRecord.id.desc())
        ).all()
        profiles = db.exec(
            select(DatasetProfile).order_by(DatasetProfile.id.desc())
        ).all()

    # Build profile lookup by dataset_id
    profile_by_dataset: dict[str, DatasetProfile] = {}
    for p in profiles:
        profile_by_dataset[str(p.dataset_id)] = p

    candidates: list[dict[str, Any]] = []

    for r1, r2 in combinations(records, 2):
        p1 = profile_by_dataset.get(str(r1.id))
        p2 = profile_by_dataset.get(str(r2.id))

        if not p1 or not p2:
            continue

        entity_score = _entity_overlap(p1, p2)
        geo_score = _geo_overlap(p1, p2, r1, r2)
        temporal_score = _temporal_overlap(p1, p2)
        join_score = _join_key_overlap(p1, p2)

        # Weighted confidence — entity overlap is the strongest signal
        link_confidence = (
            entity_score * 0.4
            + geo_score * 0.15
            + temporal_score * 0.15
            + join_score * 0.3
        )

        # Determine match type
        match_parts: list[str] = []
        if entity_score > 0.3:
            match_parts.append("entity_match")
        if geo_score > 0.5:
            match_parts.append("geo_overlap")
        if temporal_score > 0.5:
            match_parts.append("temporal_overlap")
        if join_score > 0.3:
            match_parts.append("join_key")

        match_type = "composite" if len(match_parts) > 1 else (match_parts[0] if match_parts else "temporal_overlap")

        # Best join keys for this pair
        shared_entity_families = list(
            {_entity_family(e) for e in p1.entity_types if _entity_family(e)}
            & {_entity_family(e) for e in p2.entity_types if _entity_family(e)}
        )

        candidates.append({
            "source_dataset_id": str(r1.id),
            "source_title": r1.title,
            "source_entity_types": p1.entity_types,
            "target_dataset_id": str(r2.id),
            "target_title": r2.title,
            "target_entity_types": p2.entity_types,
            "match_type": match_type,
            "shared_entity_families": shared_entity_families,
            "entity_overlap_score": round(entity_score, 3),
            "geo_overlap_score": round(geo_score, 3),
            "temporal_overlap_score": round(temporal_score, 3),
            "join_key_overlap_score": round(join_score, 3),
            "link_confidence": round(link_confidence, 3),
            "source_join_key": ", ".join(p1.join_keys),
            "target_join_key": ", ".join(p2.join_keys),
            "compound_value_score": None,  # Layer 2 — I fill this in
        })

    candidates.sort(key=lambda c: c["link_confidence"], reverse=True)
    return candidates


def persist_link(
    source_id: str,
    target_id: str,
    match_type: str,
    source_join_key: str,
    target_join_key: str,
    entity_overlap: float,
    geo_overlap: float,
    temporal_overlap: float,
    link_confidence: float,
    compound_value_score: int | None = None,
    compound_rationale: str | None = None,
) -> DatasetLink:
    """Persist a link candidate that I've evaluated."""
    link = DatasetLink(
        source_dataset_id=UUID(source_id) if isinstance(source_id, str) else source_id,
        target_dataset_id=UUID(target_id) if isinstance(target_id, str) else target_id,
        match_type=match_type,
        source_join_key=source_join_key,
        target_join_key=target_join_key,
        entity_overlap_score=entity_overlap,
        geo_overlap_score=geo_overlap,
        temporal_overlap_score=temporal_overlap,
        link_confidence=link_confidence,
        compound_value_score=compound_value_score,
        compound_rationale=compound_rationale,
        evaluated_at=datetime.now(timezone.utc) if compound_value_score is not None else None,
    )
    with DBSession(engine, expire_on_commit=False) as db:
        db.add(link)
        db.commit()
        db.refresh(link)
    return link


def list_persisted_links() -> list[dict[str, Any]]:
    """Show all evaluated links from the DB."""
    with DBSession(engine, expire_on_commit=False) as db:
        links = db.exec(
            select(DatasetLink).order_by(DatasetLink.created_at.desc())
        ).all()
        return [
            {
                "id": str(l.id),
                "source_dataset_id": str(l.source_dataset_id),
                "target_dataset_id": str(l.target_dataset_id),
                "match_type": l.match_type,
                "link_confidence": l.link_confidence,
                "compound_value_score": l.compound_value_score,
                "compound_rationale": l.compound_rationale,
                "evaluated": l.evaluated_at is not None,
            }
            for l in links
        ]

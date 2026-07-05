"""
OpportunityForge Pipeline — You are the agent.

This is the orchestrator. Each stage is a method YOU drive. You provide
the intelligence (search, analysis, reasoning). These methods handle
DB persistence so your work survives across sessions.

Usage:
    from opportunityforge.pipeline import PipelineSession
    session = PipelineSession()
    session.start("My Dataset Title", "URL or source description")

    # Then run stages one at a time, YOU provide the analysis:
    session.scout(...)      # Stage 1
    session.profile(...)    # Stage 2
    session.decide(...)     # Stage 3
    session.buyer(...)      # Stage 4
    session.monetize(...)   # Stage 5
    session.score(...)      # Stage 6
    session.generate_dossier()  # Stage 7 — writes the full dossier

    session.summary()       # Print current state
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlmodel import Session as DBSession, SQLModel, create_engine, select

from opportunityforge.models.domain import (
    BuyerProfile,
    DatasetProfile,
    DatasetRecord,
    DatasetSourceType,
    DecisionHypothesis,
    FrictionProfile,
    MonetizationBlueprint,
    MonetizationModel,
    Opportunity,
    ScoreBreakdown,
)

DB_PATH = Path(__file__).resolve().parent.parent / "opportunityforge.db"
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)
SQLModel.metadata.create_all(engine)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "pipeline_output"
OUTPUT_DIR.mkdir(exist_ok=True)


class PipelineSession:
    """One dataset moving through the OpportunityForge pipeline.
    
    Create one session per dataset. You drive each stage by calling the
    methods with YOUR analysis — the session handles persistence.
    """

    def __init__(self) -> None:
        self.dataset_id: UUID | None = None
        self.dataset: DatasetRecord | None = None
        self.profile_record: DatasetProfile | None = None
        self.decisions: list[DecisionHypothesis] = []
        self.buyers: list[BuyerProfile] = []
        self.blueprints: list[MonetizationBlueprint] = []
        self.opportunity: Opportunity | None = None
        self._stage_log: list[str] = []

    # ── Stage 1: Scout ──────────────────────────────────────────

    def scout(
        self,
        *,
        title: str,
        source_url: str,
        source_type: str = "other",
        publisher: str | None = None,
        description: str | None = None,
        update_frequency: str | None = None,
        geography: str | None = None,
        freshness: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> DatasetRecord:
        """Register a discovered dataset. YOU provide the scouted data."""
        try:
            st = DatasetSourceType(source_type)
        except ValueError:
            st = DatasetSourceType.OTHER

        record = DatasetRecord(
            title=title,
            source_type=st,
            source_url=source_url,
            publisher=publisher,
            description=description,
            update_frequency=update_frequency,
            geography=geography,
            freshness=freshness,
            metadata_json=metadata_json or {},
        )
        with DBSession(engine, expire_on_commit=False) as db:
            db.add(record)
            db.commit()
            db.refresh(record)

        self.dataset_id = record.id
        self.dataset = record
        self._log(f"SCOUT: {title}")
        return record

    # ── Stage 2: Profile ────────────────────────────────────────

    def profile(
        self,
        *,
        columns: list[str] | None = None,
        entity_types: list[str] | None = None,
        join_keys: list[str] | None = None,
        sample_summary: str | None = None,
        confidence: float = 0.5,
    ) -> DatasetProfile:
        """Profile the scouted dataset. YOU analyze the data and provide the profile."""
        assert self.dataset_id is not None, "Scout a dataset first"

        prof = DatasetProfile(
            dataset_id=self.dataset_id,
            columns=columns or [],
            entity_types=entity_types or [],
            join_keys=join_keys or [],
            sample_summary=sample_summary,
            profile_confidence=confidence,
        )
        with DBSession(engine, expire_on_commit=False) as db:
            db.add(prof)
            db.commit()
            db.refresh(prof)

        self.profile_record = prof
        self._log(f"PROFILE: {len(prof.columns)} columns, {len(prof.entity_types)} entities")
        return prof

    # ── Stage 3: Decide ─────────────────────────────────────────

    def decide(
        self,
        *,
        decisions: list[dict[str, Any]],
    ) -> list[DecisionHypothesis]:
        """Identify decisions this dataset enables. YOU brainstorm the hypotheses."""
        assert self.dataset_id is not None, "Scout a dataset first"

        results: list[DecisionHypothesis] = []
        with DBSession(engine, expire_on_commit=False) as db:
            for d in decisions:
                hyp = DecisionHypothesis(
                    dataset_id=self.dataset_id,
                    decision=d["decision"],
                    decision_maker=d.get("decision_maker", ""),
                    stakes=d.get("stakes", ""),
                    frequency=d.get("frequency", ""),
                    urgency=d.get("urgency", ""),
                    consequences=d.get("consequences", ""),
                    confidence_score=d.get("confidence_score", 5),
                )
                db.add(hyp)
                db.commit()
                db.refresh(hyp)
                results.append(hyp)

        self.decisions = results
        self._log(f"DECIDE: {len(results)} decision hypotheses")
        return results

    # ── Stage 4: Buyer ──────────────────────────────────────────

    def buyer(
        self,
        *,
        buyers: list[dict[str, Any]],
        decision_index: int = 0,
    ) -> list[BuyerProfile]:
        """Map buyer personas. YOU identify who pays and why."""
        assert self.decisions, "Run decide() first"

        decision_id = self.decisions[decision_index].id
        results: list[BuyerProfile] = []
        with DBSession(engine, expire_on_commit=False) as db:
            for b in buyers:
                bp = BuyerProfile(
                    decision_id=decision_id,
                    buyer_type=b["buyer_type"],
                    pain_points=b.get("pain_points", []),
                    reachability=b.get("reachability", 5),
                    willingness_to_pay=b.get("willingness_to_pay", 5),
                    confidence_score=b.get("confidence_score", 5),
                )
                db.add(bp)
                db.commit()
                db.refresh(bp)
                results.append(bp)

        self.buyers = results
        self._log(f"BUYER: {len(results)} buyer profiles")
        return results

    # ── Stage 5: Monetize ───────────────────────────────────────

    def monetize(
        self,
        *,
        blueprints: list[dict[str, Any]],
    ) -> list[MonetizationBlueprint]:
        """Design revenue models. YOU figure out how to package and sell."""
        assert self.opportunity is not None, "Create an opportunity first via score()"

        results: list[MonetizationBlueprint] = []
        with DBSession(engine, expire_on_commit=False) as db:
            for b in blueprints:
                try:
                    rm = MonetizationModel(b["revenue_model"])
                except ValueError:
                    rm = MonetizationModel.SUBSCRIPTION

                bp = MonetizationBlueprint(
                    opportunity_id=self.opportunity.id,
                    revenue_model=rm,
                    pricing_hypothesis=b.get("pricing_hypothesis", ""),
                    revenue_potential=b.get("revenue_potential", ""),
                    confidence_score=b.get("confidence_score", 5),
                )
                db.add(bp)
                db.commit()
                db.refresh(bp)
                results.append(bp)

        self.blueprints = results
        self._log(f"MONETIZE: {len(results)} blueprints")
        return results

    # ── Stage 6: Score + Create Opportunity ─────────────────────

    def score(
        self,
        *,
        title: str,
        summary: str,
        demand: int,
        decision_value: int,
        monetization_ease: int,
        defensibility: int,
        strategic_fit: int,
        rationale: dict[str, str] | None = None,
        data_friction: int = 5,
        trust_friction: int = 5,
        distribution_friction: int = 5,
        sales_friction: int = 5,
        regulatory_friction: int = 5,
        maintenance_friction: int = 5,
        friction_notes: dict[str, str] | None = None,
    ) -> Opportunity:
        """Score the opportunity and create a persisted Opportunity record.
        
        The score product is: demand × decision_value × monetization_ease × defensibility × strategic_fit
        """
        assert self.dataset_id is not None, "Scout a dataset first"

        score_breakdown = ScoreBreakdown(
            demand=demand,
            decision_value=decision_value,
            monetization_ease=monetization_ease,
            defensibility=defensibility,
            strategic_fit=strategic_fit,
            rationale=rationale or {},
        ).model_dump()

        friction_profile = FrictionProfile(
            data_friction=data_friction,
            trust_friction=trust_friction,
            distribution_friction=distribution_friction,
            sales_friction=sales_friction,
            regulatory_friction=regulatory_friction,
            maintenance_friction=maintenance_friction,
            notes=friction_notes or {},
        ).model_dump()

        decision_id = self.decisions[0].id if self.decisions else uuid4()

        opp = Opportunity(
            title=title,
            dataset_id=self.dataset_id,
            decision_id=decision_id,
            summary=summary,
            score_breakdown=score_breakdown,
            friction_profile=friction_profile,
            dossier={},
        )
        with DBSession(engine, expire_on_commit=False) as db:
            db.add(opp)
            db.commit()
            db.refresh(opp)

        self.opportunity = opp
        score_product = demand * decision_value * monetization_ease * defensibility * strategic_fit
        self._log(f"SCORE: {score_product} (product of 5 sub-scores)")
        return opp

    # ── Stage 7: Dossier ────────────────────────────────────────

    def generate_dossier(
        self,
        sections: dict[str, str],
    ) -> Opportunity:
        """Write the full opportunity dossier. YOU provide every section."""
        assert self.opportunity is not None, "Run score() first"

        required = [
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

        dossier = {section: sections.get(section, "") for section in required}

        with DBSession(engine, expire_on_commit=False) as db:
            opp = db.get(Opportunity, self.opportunity.id)
            opp.dossier = dossier
            db.add(opp)
            db.commit()
            db.refresh(opp)

        self.opportunity = opp
        self._log("DOSSIER: written")
        return opp

    # ── Utilities ───────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self._stage_log.append(f"[{ts}] {msg}")

    def summary(self) -> str:
        """Print pipeline state as a readable report."""
        parts = [f"── OpportunityForge Pipeline ──"]

        if self.dataset:
            parts.append(f"\n📡 Dataset: {self.dataset.title}")
            parts.append(f"   Source: {self.dataset.source_url}")
            parts.append(f"   Type: {self.dataset.source_type.value}")

        if self.profile_record:
            parts.append(f"\n🔬 Profile: {len(self.profile_record.columns)} columns")
            parts.append(f"   Entities: {', '.join(self.profile_record.entity_types)}")

        if self.decisions:
            parts.append(f"\n💡 Decisions ({len(self.decisions)}):")
            for d in self.decisions:
                parts.append(f"   • {d.decision} (confidence: {d.confidence_score}/10)")

        if self.buyers:
            parts.append(f"\n👤 Buyers ({len(self.buyers)}):")
            for b in self.buyers:
                parts.append(f"   • {b.buyer_type} (reach: {b.reachability}/10, pay: {b.willingness_to_pay}/10)")

        if self.blueprints:
            parts.append(f"\n💰 Monetization ({len(self.blueprints)}):")
            for b in self.blueprints:
                parts.append(f"   • {b.revenue_model.value} — {b.pricing_hypothesis}")

        if self.opportunity:
            sb = self.opportunity.score_breakdown
            score = sb.get("demand", 0) * sb.get("decision_value", 0) * sb.get("monetization_ease", 0) * sb.get("defensibility", 0) * sb.get("strategic_fit", 0)
            parts.append(f"\n🏆 Opportunity: {self.opportunity.title}")
            parts.append(f"   Score: {score}")
            dossier_size = len(self.opportunity.dossier.get("Executive Summary", ""))
            parts.append(f"   Dossier: {dossier_size} chars")

        parts.append(f"\n📋 Log:")
        for entry in self._stage_log:
            parts.append(f"   {entry}")

        return "\n".join(parts)

    def save_report(self) -> Path:
        """Save the full pipeline output as a JSON report."""
        assert self.opportunity is not None, "Nothing to save yet"

        report = {
            "dataset": self.dataset.model_dump() if self.dataset else None,
            "profile": self.profile_record.model_dump() if self.profile_record else None,
            "decisions": [d.model_dump() for d in self.decisions],
            "buyers": [b.model_dump() for b in self.buyers],
            "blueprints": [b.model_dump() for b in self.blueprints],
            "opportunity": self.opportunity.model_dump() if self.opportunity else None,
            "pipeline_log": self._stage_log,
        }

        slug = self.dataset.title.lower().replace(" ", "-")[:40] if self.dataset else "untitled"
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = OUTPUT_DIR / f"{slug}_{ts}.json"
        path.write_text(json.dumps(report, indent=2, default=str))
        return path


def list_datasets() -> list[dict[str, Any]]:
    """List all datasets in the pipeline (newest first)."""
    with DBSession(engine, expire_on_commit=False) as db:
        records = (
            db.exec(select(DatasetRecord).order_by(DatasetRecord.id.desc()))
            .all()
        )
        return [
            {
                "id": str(r.id),
                "title": r.title,
                "source_type": r.source_type.value,
                "publisher": r.publisher,
            }
            for r in records
        ]

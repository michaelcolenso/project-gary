from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field
from sqlmodel import JSON, Column, Field as SQLField, SQLModel


class DatasetSourceType(str, Enum):
    DATA_GOV = "data.gov"
    CKAN = "ckan"
    SOCRATA = "socrata"
    FEDERAL = "federal"
    STATE = "state"
    MUNICIPAL = "municipal"
    REGISTRY = "registry"
    OTHER = "other"


class MonetizationModel(str, Enum):
    SUBSCRIPTION = "subscription"
    DATA_LICENSING = "data_licensing"
    API_ACCESS = "api_access"
    LEAD_GENERATION = "lead_generation"
    PAID_REPORTS = "paid_reports"
    SPONSORSHIP = "sponsorship"
    AFFILIATE = "affiliate"
    ADVERTISING = "advertising"


class DatasetRecord(SQLModel, table=True):
    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    title: str
    source_type: DatasetSourceType
    source_url: str
    publisher: str | None = None
    description: str | None = None
    update_frequency: str | None = None
    geography: str | None = None
    freshness: str | None = None
    metadata_json: dict[str, Any] = SQLField(default_factory=dict, sa_column=Column(JSON))


class DatasetProfile(SQLModel, table=True):
    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    dataset_id: UUID = SQLField(index=True)
    columns: list[str] = SQLField(default_factory=list, sa_column=Column(JSON))
    entity_types: list[str] = SQLField(default_factory=list, sa_column=Column(JSON))
    join_keys: list[str] = SQLField(default_factory=list, sa_column=Column(JSON))
    sample_summary: str | None = None
    profile_confidence: float = 0.0


class DecisionHypothesis(SQLModel, table=True):
    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    dataset_id: UUID = SQLField(index=True)
    decision: str
    decision_maker: str
    stakes: str
    frequency: str
    urgency: str
    consequences: str
    confidence_score: int = SQLField(ge=1, le=10)


class BuyerProfile(SQLModel, table=True):
    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    decision_id: UUID = SQLField(index=True)
    buyer_type: str
    pain_points: list[str] = SQLField(default_factory=list, sa_column=Column(JSON))
    reachability: int = SQLField(ge=1, le=10)
    willingness_to_pay: int = SQLField(ge=1, le=10)
    confidence_score: int = SQLField(ge=1, le=10)


class MonetizationBlueprint(SQLModel, table=True):
    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    opportunity_id: UUID = SQLField(index=True)
    revenue_model: MonetizationModel
    pricing_hypothesis: str
    revenue_potential: str
    confidence_score: int = SQLField(ge=1, le=10)


class ScoreBreakdown(BaseModel):
    demand: int = Field(ge=1, le=10)
    decision_value: int = Field(ge=1, le=10)
    monetization_ease: int = Field(ge=1, le=10)
    defensibility: int = Field(ge=1, le=10)
    strategic_fit: int = Field(ge=1, le=10)
    rationale: dict[str, str] = Field(default_factory=dict)
    manual_overrides: dict[str, int] = Field(default_factory=dict)

    @computed_field
    @property
    def opportunity_score(self) -> int:
        return self.demand * self.decision_value * self.monetization_ease * self.defensibility * self.strategic_fit


class FrictionProfile(BaseModel):
    data_friction: int = Field(ge=1, le=10)
    trust_friction: int = Field(ge=1, le=10)
    distribution_friction: int = Field(ge=1, le=10)
    sales_friction: int = Field(ge=1, le=10)
    regulatory_friction: int = Field(ge=1, le=10)
    maintenance_friction: int = Field(ge=1, le=10)
    notes: dict[str, str] = Field(default_factory=dict)


class Opportunity(SQLModel, table=True):
    id: UUID = SQLField(default_factory=uuid4, primary_key=True)
    title: str
    dataset_id: UUID = SQLField(index=True)
    decision_id: UUID = SQLField(index=True)
    summary: str
    score_breakdown: dict[str, Any] = SQLField(default_factory=dict, sa_column=Column(JSON))
    friction_profile: dict[str, Any] = SQLField(default_factory=dict, sa_column=Column(JSON))
    dossier: dict[str, Any] = SQLField(default_factory=dict, sa_column=Column(JSON))

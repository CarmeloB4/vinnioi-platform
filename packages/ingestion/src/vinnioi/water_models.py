"""Contratti degli eventi dichiarati e dei calendari, senza inferenze di servizio."""

from datetime import date as CalendarDate
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl

from vinnioi.interventions import ValidationStatus


class TemporalReference(BaseModel):
    text: str
    kind: Literal["planned", "actual", "unresolved"]
    date: CalendarDate | None = None
    time: str | None = None


class MunicipalityMention(BaseModel):
    istat_code: str = Field(pattern=r"^084\d{3}$")
    name: str
    relationship: Literal["explicit_service_area", "mentioned_only"]
    evidence: str  # Estratto locale, escluso dai contratti pubblicabili.


class WaterEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    source_id: Literal["aica", "siciliacque"]
    source_url: HttpUrl
    document_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    title: str
    categories: list[
        Literal[
            "guasto",
            "interruzione",
            "manutenzione_programmata",
            "riduzione_portata",
            "emergenza_idrica",
            "potabilita",
            "ripristino_confermato",
        ]
    ]
    declared_status: str | None = None
    restoration_confirmed: bool = False
    network_level: Literal["adduction", "local_distribution", "unspecified"]
    municipalities: list[MunicipalityMention] = Field(default_factory=list)
    pipelines: list[str] = Field(default_factory=list)
    published_on: CalendarDate | None = None
    published_at: AwareDatetime | None = None
    acquired_at: AwareDatetime
    extracted_at: AwareDatetime
    temporal_references: list[TemporalReference] = Field(default_factory=list)
    reliability: Literal["rule_based", "needs_review", "human_reviewed"] = "needs_review"
    validation_status: ValidationStatus = ValidationStatus.REVIEW
    issues: list[str] = Field(default_factory=list)
    data_origin: Literal["real", "synthetic"] = "real"
    parser_version: str = "0.3.0"


class Turnation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turnation_id: str
    source_id: Literal["aica"] = "aica"
    source_url: HttpUrl
    calendar_version: str = Field(pattern=r"^[a-f0-9]{64}$")
    municipality: str | None = None
    municipality_istat_code: str | None = None
    municipality_original: str | None = None
    district: str | None = None
    source_locator: str
    reservoir: str | None = None
    zone: str | None = None
    street_description: str | None = None
    date: CalendarDate | None = None
    date_label_original: str
    time_slot: str | None = None
    value_original: str | None = None
    valid_from: CalendarDate | None = None
    valid_until: CalendarDate | None = None
    notes: str | None = None
    acquired_at: AwareDatetime
    validation_status: ValidationStatus = ValidationStatus.REVIEW
    issues: list[str] = Field(default_factory=list)
    data_origin: Literal["real", "synthetic"] = "real"
    actual_delivery_confirmed: Literal[False] = False


class CalendarResult(BaseModel):
    rows: list[Turnation] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    complete: bool = False
    version: str
    source_url: HttpUrl
    acquired_at: AwareDatetime


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision_id: str = Field(min_length=1)
    review_id: str
    expected_payload_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    actor: str = Field(min_length=1)
    decided_at: AwareDatetime
    action: Literal["approve", "reject"]
    reason: str = Field(min_length=10)
    evidence_url: HttpUrl
    rule_id: str | None = None
    corrections: dict[str, str | None] = Field(default_factory=dict)

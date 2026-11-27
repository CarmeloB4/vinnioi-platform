"""Contratti Phase 2. Le date della fonte non sono mai sostituite dal download."""

import hashlib
import json
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl


class ValidationStatus(StrEnum):
    VALIDATED = "validated"
    REVIEW = "needs_review"


class Intervention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intervention_id: str | None = None  # Chiave Vinnioi source + codice comune + codice fonte.
    source_id: str = "aica"
    source_intervention_id: str | None = None
    municipality: str | None = None
    municipality_istat_code: str | None = Field(default=None, pattern=r"^084\d{3}$")
    province: str | None = None
    area: str | None = None
    address: str | None = None
    address_original: str | None = None
    house_number: str | None = None
    address_quality: str = "not_assessed"
    intervention_type: str | None = None
    network_type: str | None = None
    reported_status: str | None = None
    published_at: AwareDatetime | None = None
    scheduled_at: AwareDatetime | None = None
    first_seen_at: AwareDatetime
    last_seen_at: AwareDatetime
    resolved_at: AwareDatetime | None = None
    source_url: HttpUrl
    document_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    extracted_at: AwareDatetime
    validation_status: ValidationStatus = ValidationStatus.REVIEW
    issues: list[str] = Field(default_factory=list)
    page_number: int = Field(ge=1)
    row_number: int = Field(ge=1)
    category: str = "intervento_programmato"
    restoration_confirmed: bool = False
    parser_version: str = "0.3.0"
    data_origin: str = "real"


class ParseResult(BaseModel):
    rows: list[Intervention] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    complete: bool = False
    expected_rows: int | None = None
    document_generated_at: str | None = None  # Stringa originale, non published_at.
    layout: str = "aica_table_v1"


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()

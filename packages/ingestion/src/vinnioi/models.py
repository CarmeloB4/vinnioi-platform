from datetime import datetime
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator


class Category(StrEnum):
    GUASTO = "guasto"
    PROGRAMMATO = "intervento_programmato"
    RIPRISTINO = "ripristino_confermato"
    NON_CLASSIFICATO = "non_classificato"


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-f0-9]{64}$")
    source: str = "aica"
    source_url: HttpUrl
    discovered_at: AwareDatetime
    fetched_at: AwareDatetime
    published_at: AwareDatetime | None = None
    event_at: AwareDatetime | None = None
    comune: str = Field(min_length=1)
    area: str | None = None
    category: Category
    declared_status: str | None = None
    evidence: str | None = None
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    parser_version: str = "0.1.0"
    review_required: bool = True
    redistribution_allowed: bool = False

    @model_validator(mode="after")
    def explicit_restoration(self):
        if self.category == Category.RIPRISTINO and not (self.evidence and self.declared_status):
            raise ValueError("Un ripristino richiede stato ed evidenza espliciti della fonte")
        if self.fetched_at < self.discovered_at:
            raise ValueError("fetched_at precedente alla scoperta")
        return self


class PDFText(BaseModel):
    pages: list[str]
    content_sha256: str
    extracted_at: datetime
    review_required: bool = True

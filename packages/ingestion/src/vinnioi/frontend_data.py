"""Contratto di anteprima locale: non autorizza pubblicazione dei dati reali."""

import json
from datetime import UTC, date, datetime
from typing import Literal, NotRequired

from pydantic import AwareDatetime, BaseModel, Field, HttpUrl
from typing_extensions import TypedDict


class EventSummary(TypedDict):
    event_id: str
    source_id: str
    title: str
    categories: list[str]
    source_url: HttpUrl
    published_on: date | None
    acquired_at: AwareDatetime
    reliability: str
    validation_status: str
    restoration_confirmed: bool
    network_level: str
    municipality_istat_codes: list[str]


class TechnicalSummary(TypedDict):
    intervention_id: str
    municipality: str | None
    municipality_istat_code: str | None
    intervention_type: str | None
    network_type: str | None
    reported_status: str | None
    address_quality: str | None
    source_url: HttpUrl
    last_seen_at: AwareDatetime


class TurnationSummary(TypedDict):
    turnation_id: str
    municipality: str | None
    municipality_istat_code: str | None
    zone: str | None
    reservoir: str | None
    date: date | None
    time_slot: str | None
    valid_from: date | None
    valid_until: date | None
    notes: str | None
    validation_status: str
    calendar_version: str
    source_url: HttpUrl
    actual_delivery_confirmed: Literal[False]


class TimelineEntry(TypedDict):
    entity_type: Literal["water_event", "turnation", "technical_intervention"]
    entity_id: str
    observed_at: AwareDatetime
    changes: list[str]
    present_in_calendar: NotRequired[bool]


class TerritorialIndicator(TypedDict):
    municipality_istat_code: str
    municipality: str
    operator_coverage: str
    explicitly_mentioned_events: int
    service_status: Literal["unknown"]


class UpdateStatus(TypedDict):
    last_attempt_at: AwareDatetime | None
    last_success_at: AwareDatetime | None
    last_source_observed_at: AwareDatetime | None
    status: str
    errors: int
    review_records: int
    scheduled_acquisition_enabled: Literal[False]
    caveat: str


class FrontendDataset(BaseModel):
    schema_version: Literal[3] = 3
    generated_at: AwareDatetime
    publication_approved: Literal[False] = False
    data_origin: Literal["real", "synthetic", "empty"]
    recent_events: list[EventSummary] = Field(default_factory=list)
    events_by_municipality: dict[str, list[str]] = Field(default_factory=dict)
    technical_interventions: list[TechnicalSummary] = Field(default_factory=list)
    turnations: list[TurnationSummary] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    territorial_indicators: list[TerritorialIndicator] = Field(default_factory=list)
    last_update: UpdateStatus


def frontend_preview(store) -> FrontendDataset:
    connection = store.connection
    origins = connection.execute("SELECT DISTINCT data_origin FROM ingestion_runs").fetchall()
    origin = origins[0][0] if origins else "empty"
    events, by_municipality, turns, timeline = [], {}, [], []
    for (raw,) in connection.execute(
        "SELECT payload FROM water_events ORDER BY last_seen_at DESC, event_id"
    ).fetchall():
        event = json.loads(raw)
        # Evidenze testuali, date ambigue e riferimenti di impatto non confermati restano locali.
        codes = [
            m["istat_code"]
            for m in event["municipalities"]
            if m["relationship"] == "explicit_service_area"
        ]
        events.append(
            {
                k: event[k]
                for k in (
                    "event_id",
                    "source_id",
                    "title",
                    "categories",
                    "source_url",
                    "published_on",
                    "acquired_at",
                    "reliability",
                    "validation_status",
                    "restoration_confirmed",
                    "network_level",
                )
            }
            | {"municipality_istat_codes": codes}
        )
        for code in codes:
            by_municipality.setdefault(code, []).append(event["event_id"])
    for (raw,) in connection.execute(
        "SELECT payload FROM water_turnations ORDER BY turnation_id"
    ).fetchall():
        turn = json.loads(raw)
        turns.append(
            {
                k: turn[k]
                for k in (
                    "turnation_id",
                    "municipality",
                    "municipality_istat_code",
                    "zone",
                    "reservoir",
                    "date",
                    "time_slot",
                    "valid_from",
                    "valid_until",
                    "notes",
                    "validation_status",
                    "calendar_version",
                    "source_url",
                    "actual_delivery_confirmed",
                )
            }
        )
    for event_id, observed_at, changes in (
        connection.execute("""SELECT event_id, observed_at,
            change_types FROM event_observations ORDER BY observed_at, observation_id""").fetchall()
    ):
        timeline.append(
            dict(
                entity_type="water_event",
                entity_id=event_id,
                observed_at=observed_at.isoformat(),
                changes=json.loads(changes),
            )
        )
    for identifier, observed_at, change, present in connection.execute("""SELECT turnation_id,
            observed_at, change_type, present FROM turnation_observations
            ORDER BY observed_at, observation_id""").fetchall():
        timeline.append(
            dict(
                entity_type="turnation",
                entity_id=identifier,
                observed_at=observed_at.isoformat(),
                changes=[change],
                present_in_calendar=present,
            )
        )
    for identifier, observed_at, changes in connection.execute("""SELECT intervention_id,
            observed_at, change_types FROM intervention_observations
            ORDER BY observed_at, observation_id""").fetchall():
        timeline.append(
            dict(
                entity_type="technical_intervention",
                entity_id=identifier,
                observed_at=observed_at.isoformat(),
                changes=json.loads(changes),
            )
        )
    last = connection.execute("""SELECT observed_at, status FROM ingestion_runs
        ORDER BY observed_at DESC LIMIT 1""").fetchone()
    success = connection.execute(
        "SELECT max(observed_at) FROM ingestion_runs WHERE status='completed'"
    ).fetchone()[0]
    technical = [
        {
            k: row[k]
            for k in (
                "intervention_id",
                "municipality",
                "municipality_istat_code",
                "intervention_type",
                "network_type",
                "reported_status",
                "address_quality",
                "source_url",
                "last_seen_at",
            )
        }
        for row in store.records()
    ]
    # Nessun indirizzo o numero civico tecnico nel contratto di anteprima.
    technical = json.loads(json.dumps(technical, default=str))
    indicators = [
        dict(
            municipality_istat_code=code,
            municipality=name,
            operator_coverage=coverage,
            explicitly_mentioned_events=len(by_municipality.get(code, [])),
            service_status="unknown",
        )
        for code, name, coverage in connection.execute("""SELECT
            municipality_istat_code, municipality, operator_coverage FROM municipalities
            ORDER BY municipality_istat_code""").fetchall()
    ]
    source_observed = connection.execute("""SELECT max(observed_at) FROM (
        SELECT observed_at FROM intervention_observations UNION ALL
        SELECT observed_at FROM event_observations UNION ALL
        SELECT observed_at FROM turnation_observations)""").fetchone()[0]
    quality = connection.execute("""SELECT q.report FROM quality_reports q
        JOIN ingestion_runs r USING(run_id) ORDER BY r.observed_at DESC LIMIT 1""").fetchone()
    quality = json.loads(quality[0]) if quality else {}
    return FrontendDataset(
        generated_at=datetime.now(UTC),
        data_origin=origin,
        recent_events=events,
        events_by_municipality=by_municipality,
        technical_interventions=technical,
        turnations=turns,
        timeline=sorted(timeline, key=lambda row: (row["observed_at"], row["entity_id"])),
        territorial_indicators=indicators,
        last_update=dict(
            last_attempt_at=last[0].isoformat() if last else None,
            last_success_at=success.isoformat() if success else None,
            last_source_observed_at=source_observed.isoformat() if source_observed else None,
            status=(
                "failed"
                if last and last[1] == "failed"
                else "needs_review"
                if quality.get("errors") or quality.get("review_records")
                else last[1]
                if last
                else "no_data"
            ),
            errors=quality.get("errors", 0),
            review_records=quality.get("review_records", 0),
            scheduled_acquisition_enabled=False,
            caveat="L'assenza di osservazioni non indica assenza di disservizi",
        ),
    )

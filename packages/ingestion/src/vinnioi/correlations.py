"""Relazioni candidate deterministiche: mai fusione automatica di eventi."""

import re
from datetime import timedelta
from itertools import combinations

from vinnioi.interventions import digest
from vinnioi.municipalities import normalize
from vinnioi.store import _insert
from vinnioi.water_models import WaterEvent


def candidates(events: list[WaterEvent]) -> list[dict]:
    result = []
    for left, right in combinations(sorted(events, key=lambda e: e.event_id), 2):
        if left.source_id == right.source_id:
            continue
        shared = sorted(
            {m.istat_code for m in left.municipalities}
            & {m.istat_code for m in right.municipalities}
        )
        pipes = sorted(
            {normalize(p) for p in left.pipelines} & {normalize(p) for p in right.pipelines}
        )
        dates = [
            [t.date for t in e.temporal_references if t.date and t.kind != "unresolved"]
            for e in (left, right)
        ]
        nearby = bool(
            all(dates)
            and min(dates[0]) <= max(dates[1]) + timedelta(days=1)
            and min(dates[1]) <= max(dates[0]) + timedelta(days=1)
        )
        common_categories = sorted(set(left.categories) & set(right.categories))
        tokens = [set(re.findall(r"\b\w{4,}\b", normalize(e.title))) for e in (left, right)]
        similarity = len(tokens[0] & tokens[1]) / len(tokens[0] | tokens[1]) if any(tokens) else 0
        if not shared or not (pipes or nearby):
            continue
        reasons = dict(
            municipality_mentions=shared,
            pipeline_names=pipes,
            temporal_distance_within_one_day=nearby,
            shared_categories=common_categories,
            title_token_jaccard=round(similarity, 4),
            caveat="Menzioni e somiglianza non provano lo stesso evento o lo stesso impatto",
        )
        score = round(
            0.30
            + 0.25 * bool(pipes)
            + 0.20 * nearby
            + 0.15 * bool(common_categories)
            + 0.10 * similarity,
            4,
        )
        result.append(
            dict(
                candidate_id=digest(
                    [left.event_id, right.event_id, left.document_hash, right.document_hash]
                ),
                left_event_id=left.event_id,
                right_event_id=right.event_id,
                left_document_hash=left.document_hash,
                right_document_hash=right.document_hash,
                score=score,
                reasons=reasons,
                status="candidate",
            )
        )
    return result


def record_candidates(store) -> list[dict]:
    events = [
        WaterEvent.model_validate_json(row[0])
        for row in store.connection.execute(
            "SELECT payload FROM water_events ORDER BY event_id"
        ).fetchall()
    ]
    found = candidates(events)
    for candidate in found:
        if store.connection.execute(
            "SELECT 1 FROM event_correlations WHERE candidate_id=?", [candidate["candidate_id"]]
        ).fetchone():
            continue
        _insert(store.connection, "event_correlations", candidate)
    return found

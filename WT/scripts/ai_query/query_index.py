from __future__ import annotations

import gzip
import json
from functools import lru_cache
from typing import Any

from .sources import OUTPUTS_DIR


INDEX_PATH = OUTPUTS_DIR / "WT_1D_Query_Index_1989_2025.json.gz"


def _key(*parts: Any) -> str:
    return "|".join(str(part) for part in parts)


@lru_cache(maxsize=1)
def load_1d_query_index() -> dict[str, Any] | None:
    if not INDEX_PATH.exists():
        return None
    with gzip.open(INDEX_PATH, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def get_total_curve_from_index(modality: str, sex_label: str, age_group: str) -> list[tuple[float, float]] | None:
    index = load_1d_query_index()
    if index is None:
        return None
    rows = index.get("total_curves", {}).get(_key(modality, sex_label, age_group))
    if rows is None:
        return None
    return [(float(seconds), float(percentile)) for seconds, percentile in rows]


def get_segment_curve_from_index(
    modality: str,
    sex_label: str,
    age_group: str,
    segment: str,
) -> list[tuple[float, float]] | None:
    index = load_1d_query_index()
    if index is None:
        return None
    rows = index.get("segment_curves", {}).get(_key(modality, sex_label, age_group, segment))
    if rows is None:
        return None
    return [(float(seconds), float(percentile)) for seconds, percentile in rows]


def get_total_params_from_index(modality: str, sex_label: str, age_group: str) -> list[dict[str, Any]] | None:
    index = load_1d_query_index()
    if index is None:
        return None
    rows = index.get("total_params", {}).get(_key(modality, sex_label, age_group))
    return None if rows is None else list(rows)


def get_total_meta_from_index(modality: str, sex_label: str, age_group: str) -> dict[str, Any] | None:
    index = load_1d_query_index()
    if index is None:
        return None
    row = index.get("total_meta", {}).get(_key(modality, sex_label, age_group))
    return None if row is None else dict(row)


def get_segment_params_from_index(
    modality: str,
    sex_label: str,
    age_group: str,
    segment: str,
) -> list[dict[str, Any]] | None:
    index = load_1d_query_index()
    if index is None:
        return None
    rows = index.get("segment_params", {}).get(_key(modality, sex_label, age_group, segment))
    return None if rows is None else list(rows)


def get_segment_meta_from_index(
    modality: str,
    sex_label: str,
    age_group: str,
    segment: str,
) -> dict[str, Any] | None:
    index = load_1d_query_index()
    if index is None:
        return None
    row = index.get("segment_meta", {}).get(_key(modality, sex_label, age_group, segment))
    return None if row is None else dict(row)

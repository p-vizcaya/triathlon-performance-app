from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
WT_DIR = PACKAGE_DIR.parents[1]
OUTPUTS_DIR = WT_DIR / "outputs"


@dataclass(frozen=True)
class SourceSpec:
    entity: str
    workbook: Path | dict[str, Path]
    main_sheet: str
    coverage_sheets: tuple[str, ...]
    notes: str = ""


AUTHORIZED_SOURCES: dict[str, SourceSpec] = {
    "total_time_curve": SourceSpec(
        entity="total_time_curve",
        workbook={
            "Sprint": OUTPUTS_DIR / "WT_Sprint_All_AgeGroup_Reference_Curves_Total_Time_1989_2025.xlsx",
            "Standard": OUTPUTS_DIR / "WT_Standard_All_AgeGroup_Reference_Curves_Total_Time_1989_2025.xlsx",
        },
        main_sheet="Reference_Curves",
        coverage_sheets=("Group_Summary",),
        notes="Official source for direct total-time percentile queries.",
    ),
    "segment_curve": SourceSpec(
        entity="segment_curve",
        workbook=OUTPUTS_DIR / "WT_All_Sprint_Standard_Segment_Percentiles.xlsx",
        main_sheet="Segment_Reference_Curves",
        coverage_sheets=("Group_Summary",),
        notes="Includes Total for the complete-splits subset, not the official total-time curve.",
    ),
    "segment_pair_plane": SourceSpec(
        entity="segment_pair_plane",
        workbook=OUTPUTS_DIR / "WT_Joint_Segment_Pair_Performance_Tables_1989_2025.xlsx",
        main_sheet="Pair_Performance_Tables",
        coverage_sheets=("Pair_Summary", "Group_Summary"),
    ),
    "sbr_cube": SourceSpec(
        entity="sbr_cube",
        workbook=OUTPUTS_DIR / "WT_All_Sprint_Standard_Joint_Swim_Bike_Run_Cubes_12x12x12_1989_2025.xlsx",
        main_sheet="Cube_Long",
        coverage_sheets=("Cube_Summary", "Skipped_Categories"),
    ),
}


MODALITIES = ("Sprint", "Standard")
SEX_CATEGORIES = ("F", "O")
SEGMENTS = ("Swim", "T1", "Bike", "T2", "Run", "Total")
PAIR_SEGMENTS = ("Swim", "Bike", "Run")
PAIRS = ("swim_bike", "swim_run", "bike_run")
CUBE_RESOLUTION = "12x12x12"

SPRINT_AGE_GROUPS = (
    "16-19",
    "20-24",
    "25-29",
    "30-34",
    "35-39",
    "40-44",
    "45-49",
    "50-54",
    "55-59",
    "60-64",
    "65-69",
    "70-74",
    "75-79",
    "80-84",
)
STANDARD_AGE_GROUPS = (
    "18-19",
    "20-24",
    "25-29",
    "30-34",
    "35-39",
    "40-44",
    "45-49",
    "50-54",
    "55-59",
    "60-64",
    "65-69",
    "70-74",
    "75-79",
    "80-84",
)


def list_available_dimensions() -> dict[str, object]:
    return {
        "modalities": list(MODALITIES),
        "sex_categories": list(SEX_CATEGORIES),
        "age_groups": {
            "Sprint": list(SPRINT_AGE_GROUPS),
            "Standard": list(STANDARD_AGE_GROUPS),
        },
        "segments": list(SEGMENTS),
        "pair_segments": list(PAIR_SEGMENTS),
        "pairs": list(PAIRS),
        "cube_resolution": CUBE_RESOLUTION,
    }


def get_source(entity: str) -> SourceSpec:
    try:
        return AUTHORIZED_SOURCES[entity]
    except KeyError as exc:
        valid = ", ".join(sorted(AUTHORIZED_SOURCES))
        raise ValueError(f"Unknown source entity {entity!r}. Expected one of: {valid}") from exc


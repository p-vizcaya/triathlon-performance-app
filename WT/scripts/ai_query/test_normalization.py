from __future__ import annotations

import unittest

from .normalization import (
    NormalizationError,
    format_seconds,
    normalize_modality,
    normalize_pair,
    normalize_query_inputs,
    normalize_segment,
    normalize_sex_category,
    parse_segment_time_to_seconds,
    parse_time_to_seconds,
    resolve_age_group,
)
from .sources import get_source, list_available_dimensions


class NormalizationTests(unittest.TestCase):
    def test_modality(self) -> None:
        self.assertEqual(normalize_modality("sprint"), "Sprint")
        self.assertEqual(normalize_modality("standard"), "Standard")
        self.assertEqual(normalize_modality("estandar"), "Standard")

    def test_sex_category(self) -> None:
        self.assertEqual(normalize_sex_category("F"), "F")
        self.assertEqual(normalize_sex_category("female"), "F")
        self.assertEqual(normalize_sex_category("open"), "O")
        self.assertEqual(normalize_sex_category("M"), "O")
        self.assertEqual(normalize_sex_category("hombre", field="sex"), "M")

    def test_age_groups(self) -> None:
        self.assertEqual(resolve_age_group(18, "Sprint"), "16-19")
        self.assertEqual(resolve_age_group(18, "Standard"), "18-19")
        self.assertEqual(resolve_age_group(42, "Standard"), "40-44")
        with self.assertRaises(NormalizationError):
            resolve_age_group(17, "Standard")

    def test_segments_and_pairs(self) -> None:
        self.assertEqual(normalize_segment("natacion"), "Swim")
        self.assertEqual(normalize_segment("transicion 1"), "T1")
        self.assertEqual(normalize_segment("carrera"), "Run")
        self.assertEqual(normalize_pair("swim bike"), "swim_bike")
        self.assertEqual(normalize_pair("ciclismo y carrera"), "bike_run")

    def test_times(self) -> None:
        self.assertEqual(parse_time_to_seconds("12:34"), 754)
        self.assertEqual(parse_time_to_seconds("1:02:03"), 3723)
        self.assertEqual(parse_time_to_seconds("45 min"), 2700)
        self.assertEqual(parse_time_to_seconds("1h 2m 3s"), 3723)
        self.assertEqual(format_seconds(3723), "1:02:03")
        self.assertEqual(format_seconds(754), "12:34")

    def test_sport_performance_units_to_segment_seconds(self) -> None:
        self.assertEqual(parse_segment_time_to_seconds("Standard", "Swim", "00:40"), 2400)
        self.assertEqual(parse_segment_time_to_seconds("Standard", "Run", "0:45"), 2700)
        self.assertEqual(parse_segment_time_to_seconds("Standard", "Swim", "1:40/100m"), 1500)
        self.assertEqual(parse_segment_time_to_seconds("Sprint", "Swim", "1:40 per 100m"), 750)
        self.assertEqual(parse_segment_time_to_seconds("Standard", "Bike", "32 km/h"), 4500)
        self.assertEqual(parse_segment_time_to_seconds("Sprint", "Bike", "30 kmh"), 2400)
        self.assertEqual(parse_segment_time_to_seconds("Standard", "Run", "5:00/km"), 3000)
        self.assertEqual(parse_segment_time_to_seconds("Sprint", "Run", "4:30 min/km"), 1350)

    def test_query_normalization(self) -> None:
        result = normalize_query_inputs(
            {
                "modality": "standard",
                "sex": "hombre",
                "age": 42,
                "segment": "carrera",
                "run_time": "44:30",
                "percentile": 80,
            }
        )
        self.assertEqual(result["modality"], "Standard")
        self.assertEqual(result["sex_label"], "O")
        self.assertEqual(result["sex"], "M")
        self.assertEqual(result["age_group"], "40-44")
        self.assertEqual(result["segment"], "Run")
        self.assertEqual(result["run_seconds"], 2670)
        self.assertEqual(result["percentile"], 80)

    def test_query_normalization_sport_unit_fields(self) -> None:
        result = normalize_query_inputs(
            {
                "modality": "Standard",
                "swim_pace_100m": "1:40/100m",
                "bike_speed_kmh": "32 km/h",
                "run_pace_km": "5:00/km",
            }
        )
        self.assertEqual(result["swim_seconds"], 1500)
        self.assertEqual(result["bike_seconds"], 4500)
        self.assertEqual(result["run_seconds"], 3000)

    def test_sources(self) -> None:
        dims = list_available_dimensions()
        self.assertIn("Sprint", dims["modalities"])
        self.assertIn("Standard", dims["modalities"])
        self.assertEqual(get_source("sbr_cube").main_sheet, "Cube_Long")


if __name__ == "__main__":
    unittest.main()

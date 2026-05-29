from __future__ import annotations

import unittest

from .router import route_query
from .query_agent import run_query_agent


class V1IntentContractTests(unittest.TestCase):
    def test_1_total_time_to_percentile(self) -> None:
        result = route_query(
            {
                "intent": "total_time_to_percentile",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "70-74",
                "total_time": "3:00:00",
            }
        )
        self.assertEqual(result["entity"], "total_time_curve")
        self.assertIn("performance_percentile", result)

    def test_2_percentile_to_total_time(self) -> None:
        result = route_query(
            {
                "intent": "percentile_to_total_time",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "70-74",
                "percentile": 80,
            }
        )
        self.assertEqual(result["entity"], "total_time_curve")
        self.assertIn("total_time", result)

    def test_3_gap_to_target_percentile_total(self) -> None:
        result = route_query(
            {
                "intent": "gap_to_target_percentile",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "70-74",
                "current_time": "3:00:00",
                "target_percentile": 80,
            },
            explain=True,
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["entity"], "gap_to_target_percentile")
        self.assertEqual(result["scope"], "Total")
        self.assertIn("explanation", result)

    def test_3_gap_to_target_percentile_segment(self) -> None:
        result = route_query(
            {
                "intent": "gap_to_target_percentile",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "70-74",
                "segment": "Run",
                "current_time": "54:00",
                "target_percentile": 80,
            }
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["scope"], "Run")

    def test_4_segment_time_to_percentile(self) -> None:
        result = route_query(
            {
                "intent": "segment_time_to_percentile",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "70-74",
                "segment": "Run",
                "segment_time": "54:00",
            }
        )
        self.assertEqual(result["entity"], "segment_curve")
        self.assertIn("performance_percentile", result)

    def test_5_full_split_evaluation(self) -> None:
        result = run_query_agent(
            {
                "intent": "full_split_evaluation",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "70-74",
                "swim_time": "40:00",
                "t1_time": "6:00",
                "bike_time": "1:15:00",
                "t2_time": "4:00",
                "run_time": "54:00",
            }
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["result"]["entity"], "full_split_profile")

    def test_6_required_missing_segment_for_target_percentile(self) -> None:
        result = route_query(
            {
                "intent": "required_missing_segment_for_target_percentile",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "70-74",
                "missing_segment": "Run",
                "swim_time": "40:00",
                "bike_time": "1:15:00",
                "percentile": 75,
            },
            explain=True,
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["entity"], "required_missing_segment_for_target_percentile")
        self.assertEqual(result["missing_segment"], "Run")
        self.assertIn("explanation", result)

    def test_7_compare_segments(self) -> None:
        result = route_query(
            {
                "intent": "compare_segments",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "70-74",
                "swim_time": "40:00",
                "bike_time": "1:15:00",
                "run_time": "54:00",
            },
            explain=True,
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["entity"], "compare_segments")
        self.assertIn("weakest_segment", result)
        self.assertIn("explanation", result)

    def test_8_explain_percentile_via_explain_flag(self) -> None:
        result = route_query(
            {
                "intent": "explain_percentile",
                "percentile": 67.3,
                "scope": "Standard O 70-74 Run",
            },
            explain=True,
        )
        self.assertIn("explanation", result)
        self.assertIn("P67.3", result["explanation"])


if __name__ == "__main__":
    unittest.main()

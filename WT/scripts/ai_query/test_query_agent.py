from __future__ import annotations

import unittest

from .explain import explain_result
from .router import route_query
from .query_agent import run_query_agent, run_query_plan_agent


class QueryAgentTests(unittest.TestCase):
    def test_agent_runs_direct_query(self) -> None:
        response = run_query_agent(
            {
                "intent": "total_percentile_by_time",
                "modality": "Sprint",
                "sex_category": "F",
                "age_group": "40-44",
                "total_time": "1:20:00",
            }
        )
        self.assertTrue(response["valid"])
        self.assertFalse(response["needs_clarification"])
        self.assertIn("explanation", response)
        self.assertEqual(response["result"]["entity"], "total_time_curve")

    def test_spanish_direct_segment_explanation_omits_difficulty_interval(self) -> None:
        result = route_query(
            {
                "intent": "segment_percentile_by_time",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "70-74",
                "segment": "Swim",
                "segment_time": "40:00",
            }
        )
        explanation = explain_result(result, locale="es")
        self.assertIn("P27.2", explanation)
        self.assertNotIn("rango intercuart", explanation)
        self.assertNotIn("P4.5", explanation)
        self.assertNotIn("difficulty_percentile_q25", result["uncertainty"])

    def test_absurd_segment_time_is_rejected(self) -> None:
        response = run_query_agent(
            {
                "intent": "segment_percentile_by_time",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "70-74",
                "segment": "Swim",
                "segment_time": "40",
            }
        )
        self.assertFalse(response["valid"])
        self.assertEqual(response["reason"], "outside_empirical_range")
        self.assertIn("outside the empirical range", response["message"])

    def test_agent_asks_for_missing_fields(self) -> None:
        response = run_query_agent(
            {
                "intent": "sbr_percentile_by_segment_times",
                "modality": "Standard",
                "sex_category": "O",
            }
        )
        self.assertFalse(response["valid"])
        self.assertTrue(response["needs_clarification"])
        self.assertIn("age_group", response["missing_fields"])
        self.assertIn("run_time", response["missing_fields"])

    def test_agent_runs_orchestrated_profile(self) -> None:
        response = run_query_agent(
            {
                "intent": "evaluate_main_segment_profile",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "40-44",
                "swim_time": "25:00",
                "bike_time": "1:10:00",
                "run_time": "45:00",
            }
        )
        self.assertTrue(response["valid"])
        self.assertIn("Weakest main segment", response["explanation"])
        self.assertEqual(response["result"]["entity"], "main_segment_profile")

    def test_agent_runs_scenario_comparison(self) -> None:
        response = run_query_agent(
            {
                "intent": "compare_segment_scenarios",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "40-44",
                "segment": "Run",
                "current_time": "45:00",
                "target_time": "42:00",
            }
        )
        self.assertTrue(response["valid"])
        self.assertIn("changes the marginal percentile", response["explanation"])

    def test_agent_runs_compare_segments(self) -> None:
        response = run_query_agent(
            {
                "intent": "compare_segments",
                "modality": "Sprint",
                "sex_category": "Male",
                "age_group": "50-54",
                "swim_time": "14:00",
                "t1_time": "2:30",
                "bike_time": "36:00",
                "t2_time": "1:50",
                "run_time": "24:30",
            }
        )
        self.assertTrue(response["valid"])
        self.assertIn("Strongest provided segment", response["explanation"])

    def test_agent_runs_event_time_to_position(self) -> None:
        response = run_query_agent(
            {
                "intent": "event_time_to_position",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "40-44",
                "segment": "Total",
                "time_value": "2:18:30",
                "event_years": [2009],
            }
        )
        self.assertTrue(response["valid"])
        comparison = response["result"]["comparisons"][0]
        self.assertEqual(comparison["year"], 2009)
        self.assertGreaterEqual(comparison["n"], 20)
        self.assertIn("estimated_position", comparison)

    def test_agent_rejects_event_time_outside_empirical_range(self) -> None:
        response = run_query_agent(
            {
                "intent": "event_time_to_position",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "70-74",
                "segment": "Bike",
                "time_value": "1:15:00",
                "event_years": [2023],
                "min_n": 20,
            }
        )
        self.assertFalse(response["valid"])
        self.assertEqual(response["reason"], "outside_empirical_range")
        self.assertIn("No extrapolation", response["message"])
        comparison = response["result"]["comparisons"][0]
        self.assertFalse(comparison["valid"])
        self.assertEqual(comparison["empirical_min_time"], "1:17:41")

    def test_agent_runs_event_time_by_percentile(self) -> None:
        response = run_query_agent(
            {
                "intent": "event_time_by_percentile",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "40-44",
                "segment": "Run",
                "percentile": 80,
                "event_years": [2009],
            }
        )
        self.assertTrue(response["valid"])
        comparison = response["result"]["comparisons"][0]
        self.assertEqual(comparison["year"], 2009)
        self.assertIn("estimated_time", comparison)

    def test_plan_agent_stops_for_clarification(self) -> None:
        response = run_query_plan_agent(
            [
                {
                    "intent": "total_percentile_by_time",
                    "modality": "Sprint",
                    "sex_category": "F",
                    "age_group": "40-44",
                    "total_time": "1:20:00",
                },
                {
                    "intent": "segment_percentile_by_time",
                    "modality": "Sprint",
                },
            ]
        )
        self.assertFalse(response["valid"])
        self.assertTrue(response["needs_clarification"])
        self.assertEqual(response["failed_step"], 2)


if __name__ == "__main__":
    unittest.main()

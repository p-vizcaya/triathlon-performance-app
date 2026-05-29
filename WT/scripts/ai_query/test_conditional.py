from __future__ import annotations

import unittest

from .conditional import conditional_segment_percentile_from_joint
from .router import route_query


class ConditionalTests(unittest.TestCase):
    def test_two_variable_conditional(self) -> None:
        result = conditional_segment_percentile_from_joint(
            "Standard",
            "O",
            "55-59",
            "Run",
            "45:00",
            "Swim",
            "32:00",
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["entity"], "conditional_segment_percentile")
        self.assertEqual(len(result["conditions"]), 1)
        self.assertEqual(result["method"], "Bayes ratio over cumulative joint performance distribution")
        self.assertGreater(result["denominator_probability"], 0)
        self.assertGreaterEqual(result["conditional_percentile"], 0)
        self.assertLessEqual(result["conditional_percentile"], 100)

    def test_three_variable_conditional(self) -> None:
        result = conditional_segment_percentile_from_joint(
            "Standard",
            "O",
            "55-59",
            "Run",
            "45:00",
            "Swim",
            "32:00",
            condition_2_segment="Bike",
            condition_2_time="1:20:00",
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "outside_empirical_range")

    def test_router_condition_fields(self) -> None:
        result = route_query(
            {
                "intent": "conditional_segment_percentile",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "55-59",
                "target_segment": "Run",
                "target_time": "45:00",
                "condition_1_segment": "Swim",
                "condition_1_time": "32:00",
                "condition_2_segment": "Bike",
                "condition_2_time": "1:20:00",
            },
            explain=True,
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "outside_empirical_range")

    def test_one_variable_interval_condition(self) -> None:
        result = conditional_segment_percentile_from_joint(
            "Sprint",
            "O",
            "35-39",
            "Run",
            "24:00",
            "Swim",
            None,
            condition_1_operator="between",
            condition_1_lower_time="13:00",
            condition_1_upper_time="14:00",
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["conditions"][0]["operator"], "between")
        self.assertGreater(result["denominator_probability"], 0)

    def test_one_variable_slower_than_condition(self) -> None:
        result = conditional_segment_percentile_from_joint(
            "Standard",
            "O",
            "60-64",
            "Run",
            "1:02:00",
            "Swim",
            "35:00",
            condition_1_operator="slower_than",
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["conditions"][0]["operator"], "slower_than")
        self.assertGreater(result["denominator_probability"], 0)

    def test_two_variable_interval_conditions(self) -> None:
        result = conditional_segment_percentile_from_joint(
            "Standard",
            "O",
            "40-44",
            "Run",
            "48:30",
            "Swim",
            None,
            condition_2_segment="Bike",
            condition_2_time=None,
            condition_1_operator="between",
            condition_1_lower_time="24:00",
            condition_1_upper_time="25:00",
            condition_2_operator="between",
            condition_2_lower_time="1:08:00",
            condition_2_upper_time="1:12:00",
        )
        self.assertTrue(result["valid"])
        self.assertEqual([condition["operator"] for condition in result["conditions"]], ["between", "between"])
        self.assertGreater(result["denominator_probability"], 0)

    def test_requires_condition(self) -> None:
        result = route_query(
            {
                "intent": "conditional_segment_percentile",
                "modality": "Standard",
                "sex_category": "O",
                "age_group": "55-59",
                "target_segment": "Run",
                "target_time": "45:00",
            }
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "missing_required_fields")


if __name__ == "__main__":
    unittest.main()

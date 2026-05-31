from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import app_storage


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_db_path = app_storage.DB_PATH
        app_storage.DB_PATH = Path(self.temp_directory.name) / "reflection_agent.db"
        app_storage.init_db()

    def tearDown(self) -> None:
        app_storage.DB_PATH = self.original_db_path
        self.temp_directory.cleanup()

    def test_default_goals_are_created(self) -> None:
        goals = app_storage.list_goals()

        self.assertEqual(len(goals), 3)
        self.assertEqual(goals[0]["area"], "AI career")

    def test_reflection_round_trip_and_analytics(self) -> None:
        saved = app_storage.save_reflection(
            {
                "id": "reflection-1",
                "day": "2026-05-31",
                "notes": "Built a small AI agent script and took a walk.",
                "score": 78,
                "label": "Builder day",
                "title": "A visible rep landed.",
                "summary": "The day produced a small artifact.",
                "pattern": "Building before consuming works.",
                "challenge": "Repeat the smallest version.",
                "tomorrow": "Write one test.",
                "scoreReason": "Output and movement were both visible.",
            }
        )

        analytics = app_storage.analytics()

        self.assertEqual(saved["id"], "reflection-1")
        self.assertTrue(saved["builderSignal"])
        self.assertTrue(saved["fitnessSignal"])
        self.assertEqual(analytics["reflectionCount"], 1)
        self.assertEqual(analytics["builderDays"], 1)

    def test_positive_avoidance_is_not_a_comfort_signal(self) -> None:
        signals = app_storage.infer_signals(
            {
                "notes": "I avoided distractions and did not scroll today.",
                "summary": "",
                "pattern": "",
                "challenge": "",
            }
        )

        self.assertFalse(signals["comfortSignal"])


if __name__ == "__main__":
    unittest.main()

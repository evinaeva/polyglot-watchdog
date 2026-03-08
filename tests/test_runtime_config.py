import unittest

from pipeline.runtime_config import load_phase1_runtime_config


class RuntimeConfigTests(unittest.TestCase):
    def test_load_phase1_runtime_config_normalizes_ui_and_programmatic_shape(self):
        ui = {
            "domain": "example.com",
            "run_id": "r1",
            "language": "fr",
            "viewport_kind": "mobile",
            "state": "user",
            "user_tier": "premium",
        }
        cfg = load_phase1_runtime_config(ui)
        self.assertEqual(cfg.domain, "example.com")
        self.assertEqual(cfg.run_id, "r1")
        self.assertEqual(cfg.language, "fr")
        self.assertEqual(cfg.viewport_kind, "mobile")
        self.assertEqual(cfg.state, "user")
        self.assertEqual(cfg.user_tier, "premium")

        programmatic = {
            "domain": "example.com",
            "run_id": "r2",
            "viewport": "desktop",
        }
        cfg2 = load_phase1_runtime_config(programmatic)
        self.assertEqual(cfg2.language, "en")
        self.assertEqual(cfg2.viewport_kind, "desktop")
        self.assertEqual(cfg2.state, "guest")
        self.assertIsNone(cfg2.user_tier)

    def test_load_phase1_runtime_config_validation(self):
        with self.assertRaisesRegex(ValueError, "domain is required"):
            load_phase1_runtime_config({"domain": "", "run_id": "x"})
        with self.assertRaisesRegex(ValueError, "run_id is required"):
            load_phase1_runtime_config({"domain": "example.com", "run_id": ""})
        with self.assertRaisesRegex(ValueError, "viewport_kind must be one of"):
            load_phase1_runtime_config({"domain": "example.com", "run_id": "x", "viewport_kind": "tv"})
        with self.assertRaisesRegex(ValueError, "state must be one of"):
            load_phase1_runtime_config({"domain": "example.com", "run_id": "x", "state": "baseline"})


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mousemover.config_loader import load_config, load_env_file, select_cloudstation_root


class ConfigLoaderTests(unittest.TestCase):
    def test_environment_default_and_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_file = root / "config.yaml"
            env_file = root / "common.env"
            config_file.write_text("value: ${SAMPLE_VALUE:-default}\n", encoding="utf-8")
            env_file.write_text("SAMPLE_VALUE=overridden\n", encoding="utf-8")
            environment: dict[str, str] = {}
            load_env_file(env_file, environment)
            self.assertEqual(environment["SAMPLE_VALUE"], "overridden")

    def test_cloudstation_explicit_value_has_priority(self) -> None:
        result = select_cloudstation_root(
            {
                "CLOUDSTATION_ROOT": "~/shared",
                "CLOUDSTATION_ROOT_WINDOWS": r"D:\CloudStation",
            },
            "Windows",
        )
        self.assertIsNotNone(result)
        self.assertTrue(str(result).endswith("shared"))

    def test_load_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.yaml"
            config_file.write_text("mouse_movement:\n  delay_seconds: 1.5\n", encoding="utf-8")
            config = load_config(config_file)
            self.assertEqual(config["mouse_movement"]["delay_seconds"], 1.5)


if __name__ == "__main__":
    unittest.main()

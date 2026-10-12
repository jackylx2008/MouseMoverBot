from __future__ import annotations

import unittest

from mousemover.modules.global_hotkey import canonicalize_hotkey


class GlobalHotkeyTests(unittest.TestCase):
    def test_macos_names_are_normalized(self) -> None:
        self.assertEqual(canonicalize_hotkey("Ctrl+Option+S"), "<ctrl>+<alt>+s")
        self.assertEqual(canonicalize_hotkey("Command+Shift+F8"), "<shift>+<cmd>+<f8>")

    def test_shortcut_requires_modifier(self) -> None:
        with self.assertRaisesRegex(ValueError, "修饰键"):
            canonicalize_hotkey("s")

    def test_shortcut_rejects_multiple_regular_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "一个普通按键"):
            canonicalize_hotkey("ctrl+s+x")

    def test_shortcut_rejects_duplicate_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "重复"):
            canonicalize_hotkey("ctrl+control+s")


if __name__ == "__main__":
    unittest.main()

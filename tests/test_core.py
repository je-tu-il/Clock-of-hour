# -*- coding: utf-8 -*-
"""
Suite de tests unitaires et d'intégration pour Clock-of-hour
"""
import json
import os
import subprocess
import sys
import tempfile
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest import mock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import main as clock_main  # noqa: E402


class TestClockofhourCore(unittest.TestCase):
    def test_get_app_dir_uses_executable_when_frozen(self):
        with mock.patch.object(clock_main.sys, "frozen", True, create=True), \
             mock.patch.object(clock_main.sys, "executable", r"C:\Apps\Clock\Clock-of-Hour.exe"):
            self.assertEqual(clock_main.get_app_dir(), r"C:\Apps\Clock")

    def test_resolve_startup_target_prefers_exe_or_pythonw(self):
        with tempfile.TemporaryDirectory() as tmp:
            main_py = os.path.join(tmp, "main.py")
            with open(main_py, "w", encoding="utf-8") as f:
                f.write("# stub\n")

            venv_scripts = os.path.join(tmp, "venv", "Scripts")
            os.makedirs(venv_scripts, exist_ok=True)
            pyw_path = os.path.join(venv_scripts, "pythonw.exe")
            with open(pyw_path, "w", encoding="utf-8") as f:
                f.write("")

            target, args, workdir = clock_main.resolve_startup_target(app_dir=tmp, frozen=False)
            self.assertEqual(os.path.normcase(target), os.path.normcase(pyw_path))
            self.assertEqual(args, f'"{main_py}"')
            self.assertEqual(os.path.normcase(workdir), os.path.normcase(tmp))

            exe_path = os.path.join(tmp, "Clock-of-Hour.exe")
            with open(exe_path, "w", encoding="utf-8") as f:
                f.write("")

            target, args, workdir = clock_main.resolve_startup_target(app_dir=tmp, frozen=False)
            self.assertEqual(os.path.normcase(target), os.path.normcase(exe_path))
            self.assertEqual(args, "")
            self.assertEqual(os.path.normcase(workdir), os.path.normcase(tmp))

    @unittest.skipUnless(sys.platform == "win32", "Windows shortcut test")
    def test_create_windows_shortcut_creates_valid_lnk(self):
        with tempfile.TemporaryDirectory() as tmp:
            lnk_path = os.path.join(tmp, "Clock-of-Hour.lnk")
            target = sys.executable
            args = f'"{os.path.join(PROJECT_ROOT, "main.py")}"'
            clock_main.create_windows_shortcut(
                lnk_path=lnk_path,
                target_path=target,
                arguments=args,
                working_dir=PROJECT_ROOT,
            )
            self.assertTrue(os.path.isfile(lnk_path))

            env = os.environ.copy()
            env["COH_LNK_CHECK"] = lnk_path
            out = subprocess.check_output(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:COH_LNK_CHECK); "
                    "Write-Output ($s.TargetPath + '|' + $s.Arguments + '|' + $s.WorkingDirectory)"
                ],
                env=env,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).strip()
            parts = out.split("|")
            self.assertEqual(os.path.normcase(parts[0]), os.path.normcase(target))
            self.assertEqual(parts[1], args)
            self.assertEqual(os.path.normcase(parts[2]), os.path.normcase(PROJECT_ROOT))

    def test_desktop_mode_persistence_and_no_topmost_or_double_menu(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            startup_dir = os.path.join(tmp, "Startup")
            os.makedirs(startup_dir, exist_ok=True)
            lnk_path = os.path.join(startup_dir, "Clock-of-Hour.lnk")
            bat_path = os.path.join(startup_dir, "Clock-of-Hour.bat")

            with mock.patch.object(clock_main, "CONFIG_FILE", cfg_path), \
                 mock.patch.object(clock_main, "STARTUP_DIR", startup_dir), \
                 mock.patch.object(clock_main, "STARTUP_SHORTCUT", lnk_path), \
                 mock.patch.object(clock_main, "LEGACY_STARTUP_BAT", bat_path):

                root1 = tk.Tk()
                root1.withdraw()
                app1 = clock_main.DigitClockApp(root1)
                root1.update()

                # No [T] binding and no "Premier Plan" menu entry
                self.assertEqual(root1.bind("<Key-t>"), "")
                self.assertEqual(root1.bind("<Key-T>"), "")
                self.assertFalse(bool(root1.attributes("-topmost")))
                menu_labels = [
                    app1.menu.entrycget(i, "label")
                    for i in range(app1.menu.index("end") + 1)
                    if app1.menu.type(i) == "command"
                ]
                self.assertFalse(any("Premier Plan" in lbl for lbl in menu_labels))

                # Single right-click triggers show_context_menu exactly once
                self.assertEqual(app1.canvas.tag_bind("all", "<Button-3>"), "")

                # Toggle desktop mode -> persists immediately
                app1.toggle_desktop_mode()
                self.assertTrue(app1.desktop_mode)
                with open(cfg_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self.assertTrue(saved["desktop_mode"])
                self.assertNotIn("always_on_top", saved)
                app1.on_close()

                # Fresh restart restores desktop_mode
                root2 = tk.Tk()
                root2.withdraw()
                app2 = clock_main.DigitClockApp(root2)
                root2.update()
                self.assertTrue(app2.desktop_mode)
                self.assertTrue(bool(root2.overrideredirect()))
                self.assertFalse(bool(root2.attributes("-topmost")))
                app2.on_close()

    def test_drag_uses_root_coords_without_oscillation(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            with mock.patch.object(clock_main, "CONFIG_FILE", cfg_path):
                root = tk.Tk()
                root.geometry("200x200+100+100")
                root.update()
                app = clock_main.DigitClockApp(root)
                root.geometry("200x200+100+100")
                root.update()

                app.start_drag(SimpleNamespace(x_root=150, y_root=150))
                app.do_drag(SimpleNamespace(x_root=175, y_root=190))
                root.update()
                self.assertEqual((root.winfo_x(), root.winfo_y()), (125, 140))

                # Subsequent motion with steady offset never zigzags
                app.do_drag(SimpleNamespace(x_root=175, y_root=190))
                root.update()
                self.assertEqual((root.winfo_x(), root.winfo_y()), (125, 140))

                app.end_drag(SimpleNamespace())
                app.on_close()

    def test_open_settings_and_startup_shortcut_toggle(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            startup_dir = os.path.join(tmp, "Startup")
            os.makedirs(startup_dir, exist_ok=True)
            lnk_path = os.path.join(startup_dir, "Clock-of-Hour.lnk")
            bat_path = os.path.join(startup_dir, "Clock-of-Hour.bat")
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write("@echo off\n")

            with mock.patch.object(clock_main, "CONFIG_FILE", cfg_path), \
                 mock.patch.object(clock_main, "STARTUP_DIR", startup_dir), \
                 mock.patch.object(clock_main, "STARTUP_SHORTCUT", lnk_path), \
                 mock.patch.object(clock_main, "LEGACY_STARTUP_BAT", bat_path):

                root = tk.Tk()
                root.withdraw()
                app = clock_main.DigitClockApp(root)
                root.update()

                # Startup toggle creates .lnk and removes legacy .bat
                self.assertFalse(app.check_startup_enabled())
                self.assertTrue(app.set_startup_enabled(True))
                self.assertTrue(app.check_startup_enabled())
                self.assertFalse(os.path.exists(bat_path))
                self.assertTrue(os.path.isfile(lnk_path))

                # Open settings creates one SettingsWindow and reuses it on repeat call
                app.open_settings()
                root.update()
                win1 = app.settings_window
                self.assertIsNotNone(win1)
                self.assertTrue(win1.winfo_exists())
                app.open_settings()
                self.assertIs(app.settings_window, win1)
                win1.save_and_close()

                # Disable startup removes .lnk
                self.assertTrue(app.set_startup_enabled(False))
                self.assertFalse(app.check_startup_enabled())
                app.on_close()


if __name__ == '__main__':
    unittest.main()

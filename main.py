#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clock-of-hour — Horloge fluide de bureau à aiguilles de chiffres & cadran verre liquide
Raccourcis & Contrôles :
- [B] : Basculer Mode Widget Bureau (Ancré au bureau, insensible à Win+D, masqué de Alt-Tab)
- [F] / [F11] : Basculer Plein écran
- [D] : Basculer Thème Sombre / Clair
- Molette souris : Redimensionner l'horloge avec zoom centré (70px à 1600px)
- Clic gauche + Glisser : Déplacer l'horloge librement
- Clic droit : Menu contextuel rapide
- Échap : Quitter plein écran / quitter mode bureau
"""

import ctypes
from ctypes import wintypes
import json
import math
import os
import shutil
import subprocess
import sys
import time
import tkinter as tk
from tkinter import messagebox

try:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
except Exception:
    user32 = None
    kernel32 = None


def _configure_win32_api():
    """Configure explicit 64-bit safe ctypes signatures for Win32 calls."""
    if not user32:
        return
    try:
        hwnd_t = wintypes.HWND
        uint_t = wintypes.UINT
        int_t = ctypes.c_int
        long_t = wintypes.LONG
        lptr_t = ctypes.c_ssize_t

        user32.GetAncestor.argtypes = [hwnd_t, uint_t]
        user32.GetAncestor.restype = hwnd_t

        user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        user32.FindWindowW.restype = hwnd_t

        if hasattr(user32, "GetShellWindow"):
            user32.GetShellWindow.argtypes = []
            user32.GetShellWindow.restype = hwnd_t

        user32.GetWindowLongW.argtypes = [hwnd_t, int_t]
        user32.GetWindowLongW.restype = long_t

        user32.SetWindowLongW.argtypes = [hwnd_t, int_t, long_t]
        user32.SetWindowLongW.restype = long_t

        if hasattr(user32, "SetWindowLongPtrW"):
            user32.SetWindowLongPtrW.argtypes = [hwnd_t, int_t, lptr_t]
            user32.SetWindowLongPtrW.restype = lptr_t

        user32.SetWindowPos.argtypes = [hwnd_t, hwnd_t, int_t, int_t, int_t, int_t, uint_t]
        user32.SetWindowPos.restype = wintypes.BOOL

        user32.SetForegroundWindow.argtypes = [hwnd_t]
        user32.SetForegroundWindow.restype = wintypes.BOOL
    except Exception:
        pass


_configure_win32_api()


def get_app_dir():
    """Retourne le dossier persistant de l'application (jamais le dossier temp _MEI PyInstaller)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_config_path():
    """Retourne le chemin de config.json dans le dossier applicatif (ou AppData si non inscriptible)."""
    app_dir = get_app_dir()
    local_cfg = os.path.join(app_dir, "config.json")
    appdata_dir = os.path.join(os.environ.get("APPDATA", app_dir), "Clock-of-Hour")
    appdata_cfg = os.path.join(appdata_dir, "config.json")
    if os.path.exists(local_cfg) and os.access(local_cfg, os.W_OK):
        return local_cfg
    if os.access(app_dir, os.W_OK):
        return local_cfg
    return appdata_cfg


def resolve_startup_target(app_dir=None, frozen=None, executable=None, pythonw_override=None):
    """Résout la cible et les arguments absolus pour le raccourci de démarrage sans console."""
    resolved_dir = os.path.abspath(app_dir or get_app_dir())
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    cur_exec = os.path.abspath(executable or sys.executable)

    if is_frozen and os.path.isfile(cur_exec):
        return cur_exec, "", os.path.dirname(cur_exec)

    exe_path = os.path.join(resolved_dir, "Clock-of-Hour.exe")
    if os.path.isfile(exe_path):
        return exe_path, "", resolved_dir

    main_py = os.path.join(resolved_dir, "main.py")
    if pythonw_override and os.path.isfile(pythonw_override):
        pythonw_path = os.path.abspath(pythonw_override)
    else:
        venv_pyw = os.path.join(resolved_dir, "venv", "Scripts", "pythonw.exe")
        sibling_pyw = os.path.join(os.path.dirname(cur_exec), "pythonw.exe")
        which_pyw = shutil.which("pythonw.exe") or shutil.which("pythonw")
        if os.path.isfile(venv_pyw):
            pythonw_path = venv_pyw
        elif os.path.isfile(sibling_pyw):
            pythonw_path = sibling_pyw
        elif which_pyw:
            pythonw_path = os.path.abspath(which_pyw)
        else:
            pythonw_path = cur_exec

    return pythonw_path, f'"{main_py}"', resolved_dir


def create_windows_shortcut(lnk_path, target_path, arguments="", working_dir="", description="Clock-of-Hour"):
    """Crée un raccourci Windows .lnk via WScript.Shell sans fenêtre console ni dépendance externe."""
    ps_script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:COH_LNK_PATH); "
        "$s.TargetPath = $env:COH_LNK_TARGET; "
        "$s.Arguments = $env:COH_LNK_ARGS; "
        "$s.WorkingDirectory = $env:COH_LNK_WORKDIR; "
        "$s.Description = $env:COH_LNK_DESC; "
        "$s.WindowStyle = 1; "
        "$s.Save()"
    )
    env = os.environ.copy()
    env["COH_LNK_PATH"] = lnk_path
    env["COH_LNK_TARGET"] = target_path
    env["COH_LNK_ARGS"] = arguments
    env["COH_LNK_WORKDIR"] = working_dir or os.path.dirname(target_path)
    env["COH_LNK_DESC"] = description

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_script],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        creationflags=creation_flags,
    )
    if result.returncode != 0 or not os.path.isfile(lnk_path):
        raise RuntimeError(result.stderr.strip() or "Échec de création du raccourci .lnk")


MUTEX_HANDLE = None


def acquire_single_instance_mutex():
    """Empêche le lancement simultané de plusieurs instances de l'horloge."""
    global MUTEX_HANDLE
    if not kernel32:
        return True
    ERROR_ALREADY_EXISTS = 183
    MUTEX_HANDLE = kernel32.CreateMutexW(None, False, "ClockOfHour_SingleInstance_Mutex_Global")
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        if user32:
            existing_hwnd = user32.FindWindowW(None, "Clock-of-Hour")
            if existing_hwnd:
                user32.SetForegroundWindow(existing_hwnd)
        return False
    return True


CONFIG_FILE = get_config_path()
STARTUP_DIR = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
STARTUP_SHORTCUT = os.path.join(STARTUP_DIR, "Clock-of-Hour.lnk")
LEGACY_STARTUP_BAT = os.path.join(STARTUP_DIR, "Clock-of-Hour.bat")
TRANSPARENT_KEY = "#010101"


class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("Paramètres — Clock-of-Hour")
        self.geometry("460x455")
        self.resizable(False, False)
        self.configure(bg="#1a1c23")

        if not self.app.desktop_mode:
            self.transient(parent)

        self.protocol("WM_DELETE_WINDOW", self.save_and_close)

        lbl_title = tk.Label(
            self, text="⚙ Paramètres de l'Horloge",
            font=("Segoe UI", 16, "bold"), fg="#ffffff", bg="#1a1c23"
        )
        lbl_title.pack(pady=(15, 10))

        frame_shortcuts = tk.LabelFrame(
            self, text="  Raccourcis Clavier & Contrôles  ",
            font=("Segoe UI", 10, "bold"), fg="#60a5fa", bg="#1a1c23", padx=12, pady=10
        )
        frame_shortcuts.pack(fill="x", padx=20, pady=8)

        shortcuts = [
            ("[B]", "Mode Bureau (Ancré, anti Win+D, sans Alt-Tab)"),
            ("[F] / [F11]", "Plein Écran"),
            ("[D]", "Changer Thème (Sombre / Clair)"),
            ("Molette Souris", "Zoom dynamique centré (70px → 1600px)"),
            ("Clic Gauche", "Glisser pour déplacer l'horloge"),
            ("Clic Droit", "Menu contextuel sur tout le cadran")
        ]

        for k, desc in shortcuts:
            row = tk.Frame(frame_shortcuts, bg="#1a1c23")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=k, font=("Consolas", 10, "bold"), fg="#34d399", bg="#1a1c23", width=16, anchor="w").pack(side="left")
            tk.Label(row, text=desc, font=("Segoe UI", 9), fg="#94a3b8", bg="#1a1c23", anchor="w").pack(side="left")

        frame_opts = tk.LabelFrame(
            self, text="  Préférences Système  ",
            font=("Segoe UI", 10, "bold"), fg="#60a5fa", bg="#1a1c23", padx=12, pady=10
        )
        frame_opts.pack(fill="x", padx=20, pady=8)

        row_theme = tk.Frame(frame_opts, bg="#1a1c23")
        row_theme.pack(fill="x", pady=5)
        tk.Label(row_theme, text="Thème d'affichage :", font=("Segoe UI", 10), fg="#e2e8f0", bg="#1a1c23").pack(side="left")

        self.theme_var = tk.StringVar(value="Sombre" if self.app.dark_mode else "Clair")
        btn_theme = tk.Button(
            row_theme, textvariable=self.theme_var, font=("Segoe UI", 9, "bold"),
            bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", activeforeground="#ffffff",
            relief="flat", padx=12, pady=3, cursor="hand2", command=self.toggle_theme_pref
        )
        btn_theme.pack(side="right")

        row_startup = tk.Frame(frame_opts, bg="#1a1c23")
        row_startup.pack(fill="x", pady=8)
        self.startup_var = tk.BooleanVar(value=self.app.check_startup_enabled())
        chk_startup = tk.Checkbutton(
            row_startup, text="Lancer automatiquement au démarrage de Windows",
            variable=self.startup_var, command=self.toggle_startup,
            font=("Segoe UI", 9), fg="#e2e8f0", bg="#1a1c23", selectcolor="#0f172a",
            activebackground="#1a1c23", activeforeground="#ffffff"
        )
        chk_startup.pack(side="left")

        btn_close = tk.Button(
            self, text="Enregistrer & Fermer", font=("Segoe UI", 10, "bold"),
            bg="#10b981", fg="#ffffff", activebackground="#059669", activeforeground="#ffffff",
            relief="flat", padx=20, pady=6, cursor="hand2", command=self.save_and_close
        )
        btn_close.pack(pady=15)

        self.lift()
        self.focus_force()
        self.grab_set()
        self.after(20, self.focus_force)

    def toggle_theme_pref(self):
        self.app.toggle_theme()
        self.theme_var.set("Sombre" if self.app.dark_mode else "Clair")

    def toggle_startup(self):
        ok = self.app.set_startup_enabled(self.startup_var.get())
        if not ok:
            self.startup_var.set(self.app.check_startup_enabled())

    def save_and_close(self):
        self.app.save_config()
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


class DigitClockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Clock-of-Hour")

        # Configuration d'état
        self.dark_mode = True
        self.is_fullscreen = False
        self.desktop_mode = False
        self.settings_window = None
        self._desktop_anchored = False
        self._clock_after_id = None
        self._last_valid_geom = (460, 460, 250, 200)

        self._is_dragging = False
        self._drag_start_root_x = 0
        self._drag_start_root_y = 0
        self._drag_win_x = 0
        self._drag_win_y = 0

        # Thèmes raffinés (sans chiffres sur le cadran - style épuré aiguilles pures)
        self.themes = {
            "dark": {
                "bg_window": "#121214",
                "glass_outer": "#1e2433",
                "glass_body": "#131622",
                "glass_inner": "#0d0f18",
                "bezel_accent": "#38bdf8",
                "bezel_subtle": "#2e384d",
                "dial_ticks_major": "#64748b",
                "dial_ticks_minor": "#334155",
                "hour_color": "#e2e8f0",
                "minute_color": "#38bdf8",
                "second_color": "#f43f5e",
                "center_ring": "#334155",
                "center_dot": "#38bdf8",
                "text_info": "#64748b"
            },
            "light": {
                "bg_window": "#f8fafc",
                "glass_outer": "#cbd5e1",
                "glass_body": "#f1f5f9",
                "glass_inner": "#e2e8f0",
                "bezel_accent": "#2563eb",
                "bezel_subtle": "#94a3b8",
                "dial_ticks_major": "#64748b",
                "dial_ticks_minor": "#cbd5e1",
                "hour_color": "#0f172a",
                "minute_color": "#2563eb",
                "second_color": "#dc2626",
                "center_ring": "#94a3b8",
                "center_dot": "#2563eb",
                "text_info": "#64748b"
            }
        }

        # Charger la configuration enregistrée
        self.load_config()
        try:
            self.root.attributes("-topmost", False)
        except Exception:
            pass

        # Canvas principal
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Menu contextuel
        self.menu = tk.Menu(self.root, tearoff=0, bg="#1e293b", fg="#ffffff", activebackground="#2563eb")
        self.update_context_menu()

        # Fermeture propre (sauvegarde systématique)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Raccourcis clavier
        self.root.bind("<Key-b>", lambda e: self.toggle_desktop_mode())
        self.root.bind("<Key-B>", lambda e: self.toggle_desktop_mode())
        self.root.bind("<Key-d>", lambda e: self.toggle_theme())
        self.root.bind("<Key-D>", lambda e: self.toggle_theme())
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Key-f>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Key-F>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Escape>", self.on_escape)

        # Déplacement souris & Clics (un seul binding Button-3 sur le canvas pour éviter le double popup)
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.do_drag)
        self.canvas.bind("<ButtonRelease-1>", self.end_drag)
        self.canvas.bind("<Button-3>", self.show_context_menu)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        # Protection contre la minimisation Win+D
        self.root.bind("<Unmap>", self.on_unmap)

        # Restauration immédiate du mode bureau si actif dans la config
        if self.desktop_mode:
            self.root.overrideredirect(True)
            self.apply_theme()
            self.root.after(50, lambda: self.apply_desktop_mode_win32(True))
            self.root.after(600, self._retry_desktop_anchor)
            self.root.after(1800, self._retry_desktop_anchor)
        else:
            self.apply_theme()

        self.update_clock()

    @property
    def current_theme(self):
        return self.themes["dark" if self.dark_mode else "light"]

    def load_config(self):
        w, h, x, y = 460, 460, 250, 200
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    w = max(70, int(cfg.get("width", 460)))
                    h = max(70, int(cfg.get("height", 460)))
                    x = int(cfg.get("x", 250))
                    y = int(cfg.get("y", 200))
                    self.dark_mode = bool(cfg.get("dark_mode", True))
                    self.desktop_mode = bool(cfg.get("desktop_mode", False))
            except Exception:
                pass
        self._last_valid_geom = (w, h, x, y)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def save_config(self):
        try:
            w, h, x, y = self._last_valid_geom
            if not self.is_fullscreen:
                cur_w = self.root.winfo_width()
                cur_h = self.root.winfo_height()
                if cur_w > 1 and cur_h > 1:
                    w = max(70, cur_w)
                    h = max(70, cur_h)
                    x = self.root.winfo_x()
                    y = self.root.winfo_y()
                    self._last_valid_geom = (w, h, x, y)

            cfg = {
                "width": w,
                "height": h,
                "x": x,
                "y": y,
                "dark_mode": self.dark_mode,
                "desktop_mode": self.desktop_mode
            }
            cfg_dir = os.path.dirname(CONFIG_FILE)
            if cfg_dir:
                os.makedirs(cfg_dir, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def check_startup_enabled(self):
        return os.path.isfile(STARTUP_SHORTCUT)

    def set_startup_enabled(self, enable):
        try:
            if os.path.exists(LEGACY_STARTUP_BAT):
                os.remove(LEGACY_STARTUP_BAT)
            if enable:
                os.makedirs(STARTUP_DIR, exist_ok=True)
                target_path, arguments, working_dir = resolve_startup_target()
                create_windows_shortcut(
                    STARTUP_SHORTCUT,
                    target_path=target_path,
                    arguments=arguments,
                    working_dir=working_dir,
                    description="Clock-of-Hour"
                )
            else:
                if os.path.exists(STARTUP_SHORTCUT):
                    os.remove(STARTUP_SHORTCUT)
            return True
        except Exception as e:
            messagebox.showwarning("Démarrage Windows", f"Impossible d'ajuster le démarrage : {e}")
            return False

    def update_context_menu(self):
        self.menu.delete(0, tk.END)
        if self.desktop_mode:
            self.menu.add_command(label="🔓 Quitter le Mode Bureau", command=self.toggle_desktop_mode)
        else:
            self.menu.add_command(label="📌 Fixer au Bureau (Mode Widget)", command=self.toggle_desktop_mode)
        self.menu.add_command(label="🎨 Thème (Sombre / Clair)", command=self.toggle_theme)
        self.menu.add_separator()
        self.menu.add_command(label="⚙ Paramètres", command=self.open_settings)
        self.menu.add_separator()
        self.menu.add_command(label="✕ Fermer l'Horloge", command=self.on_close)

    def show_context_menu(self, event):
        self.update_context_menu()
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()
        return "break"

    def open_settings(self):
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return
        self.settings_window = SettingsWindow(self.root, self)

    def on_close(self):
        if self._clock_after_id is not None:
            try:
                self.root.after_cancel(self._clock_after_id)
            except Exception:
                pass
            self._clock_after_id = None
        self.save_config()
        self.root.destroy()

    def start_drag(self, event):
        self._is_dragging = True
        self._drag_start_root_x = event.x_root
        self._drag_start_root_y = event.y_root
        self._drag_win_x = self.root.winfo_x()
        self._drag_win_y = self.root.winfo_y()

    def do_drag(self, event):
        if not self._is_dragging:
            return
        deltax = event.x_root - self._drag_start_root_x
        deltay = event.y_root - self._drag_start_root_y
        new_x = self._drag_win_x + deltax
        new_y = self._drag_win_y + deltay
        self.root.geometry(f"+{new_x}+{new_y}")
        w, h, _, _ = self._last_valid_geom
        self._last_valid_geom = (w, h, new_x, new_y)

    def end_drag(self, event):
        if self._is_dragging:
            self._is_dragging = False
            self.save_config()
            if self.desktop_mode:
                self.root.after_idle(self.reassert_desktop_presence)

    def on_mouse_wheel(self, event):
        """Redimensionnement dynamique centré à la molette — Très large amplitude (70px à 1600px)"""
        step = 30 if event.delta > 0 else -30
        cur_w = self.root.winfo_width()
        new_size = max(70, min(1600, cur_w + step))
        diff = new_size - cur_w
        new_x = self.root.winfo_x() - diff // 2
        new_y = self.root.winfo_y() - diff // 2
        self._last_valid_geom = (new_size, new_size, new_x, new_y)
        self.root.geometry(f"{new_size}x{new_size}+{new_x}+{new_y}")
        self.save_config()

    def get_toplevel_hwnd(self):
        """Récupère le véritable HWND racine sous Windows"""
        if not user32:
            return None
        try:
            return user32.GetAncestor(self.root.winfo_id(), 3)  # GA_ROOT = 3
        except Exception:
            return self.root.winfo_id()

    def _find_desktop_owner_hwnd(self):
        """Trouve le handle du bureau Windows (Progman ou ShellWindow)."""
        if not user32:
            return 0
        try:
            progman = user32.FindWindowW("Progman", None)
            if progman:
                return progman
            if hasattr(user32, "GetShellWindow"):
                return user32.GetShellWindow() or 0
        except Exception:
            pass
        return 0

    def _set_hwnd_owner(self, hwnd, owner_hwnd):
        """Définit GWLP_HWNDPARENT de manière compatible 32/64 bits."""
        if not user32 or not hwnd:
            return
        GWLP_HWNDPARENT = -8
        if hasattr(user32, "SetWindowLongPtrW"):
            user32.SetWindowLongPtrW(hwnd, GWLP_HWNDPARENT, owner_hwnd)
        else:
            user32.SetWindowLongW(hwnd, GWLP_HWNDPARENT, owner_hwnd)

    def _retry_desktop_anchor(self):
        """Réessaie l'ancrage au bureau si Explorer démarrait encore lors du boot Windows."""
        if self.desktop_mode and not self._desktop_anchored:
            self.apply_desktop_mode_win32(True)

    def on_unmap(self, event):
        """Restaure automatiquement l'horloge si Windows tente de la réduire lors de Win+D"""
        if self.desktop_mode and event.widget == self.root:
            self.root.after_idle(self.reassert_desktop_presence)

    def reassert_desktop_presence(self):
        """Maintient l'horloge visible au niveau du bureau sans jamais disparaître"""
        if self.desktop_mode:
            self.root.deiconify()
            hwnd = self.get_toplevel_hwnd()
            if hwnd and user32:
                # HWND_BOTTOM = 1, SWP_NOSIZE(1) | SWP_NOMOVE(2) | SWP_NOACTIVATE(16) | SWP_SHOWWINDOW(64) = 83
                try:
                    user32.SetWindowPos(hwnd, 1, 0, 0, 0, 0, 83)
                except Exception:
                    pass

    def apply_desktop_mode_win32(self, enable):
        """Active/désactive le mode bureau transparent ancré (visible, anti-Win+D, hors Alt-Tab)"""
        try:
            self.root.attributes("-topmost", False)
        except Exception:
            pass

        if not user32:
            self.apply_theme()
            return

        if enable:
            # 1. Fenêtre sans bordures
            self.root.overrideredirect(True)
            self.root.update_idletasks()

            hwnd = self.get_toplevel_hwnd()
            if not hwnd:
                return

            # 2. Transparence du fond de la fenêtre
            try:
                self.root.attributes("-transparentcolor", TRANSPARENT_KEY)
            except Exception:
                pass
            self.canvas.configure(bg=TRANSPARENT_KEY)
            self.root.configure(bg=TRANSPARENT_KEY)

            # 3. Masquer complètement de Alt-Tab (WS_EX_TOOLWINDOW)
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            try:
                ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ex_style |= WS_EX_TOOLWINDOW
                ex_style &= ~WS_EX_APPWINDOW
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            except Exception:
                pass

            # 4. Rendre Progman propriétaire de la fenêtre (anti-minimisation Win+D)
            owner_hwnd = self._find_desktop_owner_hwnd()
            if owner_hwnd:
                try:
                    self._set_hwnd_owner(hwnd, owner_hwnd)
                    self._desktop_anchored = True
                except Exception:
                    pass

            # 5. Positionner au niveau du bureau (HWND_BOTTOM = 1) et forcer l'affichage
            try:
                user32.SetWindowPos(hwnd, 1, 0, 0, 0, 0, 83)
            except Exception:
                pass

            self.root.deiconify()
        else:
            self._desktop_anchored = False
            hwnd = self.get_toplevel_hwnd()
            if hwnd:
                try:
                    self._set_hwnd_owner(hwnd, 0)
                except Exception:
                    pass

            self.root.overrideredirect(False)
            self.root.update_idletasks()

            hwnd = self.get_toplevel_hwnd()
            try:
                self.root.attributes("-transparentcolor", "")
            except Exception:
                pass

            if hwnd:
                GWL_EXSTYLE = -20
                WS_EX_TOOLWINDOW = 0x00000080
                try:
                    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    ex_style &= ~WS_EX_TOOLWINDOW
                    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
                except Exception:
                    pass

            self.apply_theme()

    def toggle_desktop_mode(self):
        self.desktop_mode = not self.desktop_mode
        self.save_config()
        self.apply_desktop_mode_win32(self.desktop_mode)
        self.update_context_menu()

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        self.save_config()

    def apply_theme(self):
        theme = self.current_theme
        if not self.desktop_mode:
            self.root.configure(bg=theme["bg_window"])
            self.canvas.configure(bg=theme["bg_window"])
        else:
            self.root.configure(bg=TRANSPARENT_KEY)
            self.canvas.configure(bg=TRANSPARENT_KEY)

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)

    def on_escape(self, event):
        if self.is_fullscreen:
            self.toggle_fullscreen()
        elif self.desktop_mode:
            self.toggle_desktop_mode()

    def value_to_angle(self, value, max_value):
        return (value / max_value) * 360 - 90

    def draw_digit_needle(self, center_x, center_y, value, angle, length, color, font_size, max_beads=4):
        """Dessine une aiguille lumineuse avec chiffres nets et non-chevauchants"""
        rad = math.radians(angle)
        cos_rad = math.cos(rad)
        sin_rad = math.sin(rad)
        val_str = str(value).zfill(2)

        tip_x = center_x + length * cos_rad
        tip_y = center_y + length * sin_rad

        # Ligne de corps d'aiguille lumineuse
        self.canvas.create_line(
            center_x, center_y, tip_x, tip_y,
            fill=color, width=max(1, int(font_size * 0.18)),
            capstyle="round", tags="needle"
        )

        # Calcul d'espacement pour empêcher TOUT chevauchement
        min_spacing = max(18, font_size * 2.2)
        count = max(2, min(max_beads, int(length // min_spacing)))

        for i in range(1, count + 1):
            ratio = i / (count + 0.3)
            x = center_x + length * ratio * cos_rad
            y = center_y + length * ratio * sin_rad

            # Ombre portée de découpage
            self.canvas.create_text(
                x + 1, y + 1,
                text=val_str,
                fill="#05070d",
                font=("Consolas", max(7, int(font_size)), "bold"),
                tags="needle_text"
            )
            # Chiffre net principal
            self.canvas.create_text(
                x, y,
                text=val_str,
                fill=color,
                font=("Consolas", max(7, int(font_size)), "bold"),
                tags="needle_text"
            )

        # Capsule lumineuse à la pointe
        pill_r = max(2, int(font_size * 0.28))
        self.canvas.create_oval(
            tip_x - pill_r, tip_y - pill_r,
            tip_x + pill_r, tip_y + pill_r,
            fill=color, outline="#ffffff", width=1, tags="needle_tip"
        )

    def update_clock(self):
        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return
        self.canvas.delete("all")
        theme = self.current_theme

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width > 1 and height > 1:
            center_x = width // 2
            center_y = height // 2
            radius = int(min(width, height) * 0.44)

            scale = radius / 150.0

            if radius > 15:
                # --- 1. FOND DE CADRAN VERRE LIQUIDE (Liquid Glass Frosted) ---
                self.canvas.create_oval(
                    center_x - radius, center_y - radius,
                    center_x + radius, center_y + radius,
                    fill=theme["glass_outer"], outline=theme["bezel_accent"],
                    width=max(2, int(3 * scale)), tags="dial_base"
                )

                r_body = int(radius * 0.96)
                self.canvas.create_oval(
                    center_x - r_body, center_y - r_body,
                    center_x + r_body, center_y + r_body,
                    fill=theme["glass_body"], outline=theme["bezel_subtle"],
                    width=max(1, int(1.5 * scale)), tags="dial_body"
                )

                r_inner = int(radius * 0.88)
                self.canvas.create_oval(
                    center_x - r_inner, center_y - r_inner,
                    center_x + r_inner, center_y + r_inner,
                    fill=theme["glass_inner"], outline="", tags="dial_inner"
                )

                # --- 2. GRADUATIONS DES 60 MINUTES / SECONDES (SANS CHIFFRES SUR LE CADRAN) ---
                for m in range(60):
                    angle = math.radians(m * 6 - 90)
                    cos_a = math.cos(angle)
                    sin_a = math.sin(angle)

                    if m % 5 == 0:
                        x1 = center_x + (r_inner - 2) * cos_a
                        y1 = center_y + (r_inner - 2) * sin_a
                        x2 = center_x + (r_body - 3) * cos_a
                        y2 = center_y + (r_body - 3) * sin_a
                        self.canvas.create_line(
                            x1, y1, x2, y2,
                            fill=theme["dial_ticks_major"],
                            width=max(2, int(2.2 * scale)),
                            tags="dial_ticks"
                        )
                    else:
                        dot_x = center_x + (r_body - 5) * cos_a
                        dot_y = center_y + (r_body - 5) * sin_a
                        dot_r = max(1, int(1.1 * scale))
                        self.canvas.create_oval(
                            dot_x - dot_r, dot_y - dot_r,
                            dot_x + dot_r, dot_y + dot_r,
                            fill=theme["dial_ticks_minor"], outline="", tags="dial_ticks"
                        )

                # --- 3. AIGUILLES DE CHIFFRES ---
                now = time.time()
                local = time.localtime(now)
                frac_sec = now % 60
                frac_min = local.tm_min + frac_sec / 60
                frac_hour = (local.tm_hour % 12) + frac_min / 60

                sec_val = int(frac_sec)
                min_val = local.tm_min
                hour_val = local.tm_hour % 24

                sec_angle = self.value_to_angle(frac_sec, 60)
                min_angle = self.value_to_angle(frac_min, 60)
                hour_angle = self.value_to_angle(frac_hour, 12)

                h_font = max(8, int(13 * scale))
                m_font = max(7, int(11 * scale))
                s_font = max(6, int(9 * scale))

                self.draw_digit_needle(center_x, center_y, hour_val, hour_angle, radius * 0.48, theme["hour_color"], h_font, max_beads=3)
                self.draw_digit_needle(center_x, center_y, min_val, min_angle, radius * 0.70, theme["minute_color"], m_font, max_beads=4)
                self.draw_digit_needle(center_x, center_y, sec_val, sec_angle, radius * 0.90, theme["second_color"], s_font, max_beads=5)

                # --- 4. PIVOT CENTRAL (Joyau Métallique) ---
                c_outer_r = max(4, int(6 * scale))
                c_inner_r = max(2, int(3 * scale))
                self.canvas.create_oval(
                    center_x - c_outer_r, center_y - c_outer_r,
                    center_x + c_outer_r, center_y + c_outer_r,
                    fill=theme["center_ring"], outline=theme["bezel_accent"],
                    width=max(1, int(1.5 * scale)), tags="center_pivot"
                )
                self.canvas.create_oval(
                    center_x - c_inner_r, center_y - c_inner_r,
                    center_x + c_inner_r, center_y + c_inner_r,
                    fill=theme["center_dot"], outline="", tags="center_pivot"
                )

                # --- 5. HORS MODE BUREAU : GUIDE RAPIDE ---
                if not self.desktop_mode:
                    self.canvas.create_text(
                        center_x, height - 14,
                        text="[B] Mode Bureau  |  [F] Plein Écran  |  [D] Thème",
                        fill=theme["text_info"],
                        font=("Segoe UI", max(7, int(8 * scale))),
                        tags="guide_text"
                    )

        self._clock_after_id = self.root.after(33, self.update_clock)


def main():
    if not acquire_single_instance_mutex():
        sys.exit(0)
    root = tk.Tk()
    app = DigitClockApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

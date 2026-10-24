#!/usr/bin/env python3
"""
Clock-of-hour — Horloge fluide avec aiguilles en chiffres
Horloge géométrique où chaque aiguille est composée de ses propres chiffres temporels.
Raccourcis :
- [T] : Toujours au premier plan (Always on top)
- [D] : Basculer Thème Sombre / Clair
- [F] / [F11] : Plein écran
- [Échap] : Quitter plein écran
"""

import tkinter as tk
import time
import math


class DigitClockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Clock of Hour — Horloge à aiguilles de chiffres")
        self.root.geometry("460x460")
        self.root.minsize(300, 300)

        # Options d'état
        self.dark_mode = True
        self.always_on_top = False
        self.is_fullscreen = False

        # Thèmes
        self.themes = {
            "dark": {
                "bg": "#121214",
                "circle": "#2a2b30",
                "center_dot": "#ffffff",
                "hour": "#e0e0e0",
                "minute": "#60a5fa",
                "second": "#f87171",
                "text_info": "#6b7280"
            },
            "light": {
                "bg": "#f9fafb",
                "circle": "#d1d5db",
                "center_dot": "#111827",
                "hour": "#111827",
                "minute": "#2563eb",
                "second": "#dc2626",
                "text_info": "#9ca3af"
            }
        }

        # Canvas principal
        self.canvas = tk.Canvas(root, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Événements
        self.root.bind("<Configure>", self.on_resize)
        self.root.bind("<Key-t>", lambda e: self.toggle_always_on_top())
        self.root.bind("<Key-T>", lambda e: self.toggle_always_on_top())
        self.root.bind("<Key-d>", lambda e: self.toggle_theme())
        self.root.bind("<Key-D>", lambda e: self.toggle_theme())
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Key-f>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Key-F>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Escape>", self.on_escape)

        self.apply_theme()
        self.update_clock()

    @property
    def current_theme(self):
        return self.themes["dark" if self.dark_mode else "light"]

    def apply_theme(self):
        theme = self.current_theme
        self.root.configure(bg=theme["bg"])
        self.canvas.configure(bg=theme["bg"])

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.root.attributes("-topmost", self.always_on_top)
        top_str = "Activé" if self.always_on_top else "Désactivé"
        self.root.title(f"Clock of Hour [Premier Plan: {top_str}]")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)

    def on_escape(self, event):
        if self.is_fullscreen:
            self.toggle_fullscreen()

    def on_resize(self, event):
        # Le rafraîchissement se fait automatiquement dans la boucle update_clock
        pass

    def value_to_angle(self, value, max_value):
        return (value / max_value) * 360 - 90

    def draw_digit_needle(self, center_x, center_y, value, angle, length, color, font_size, steps=10):
        rad = math.radians(angle)
        cos_rad = math.cos(rad)
        sin_rad = math.sin(rad)
        val_str = str(value).zfill(2)

        for i in range(1, steps + 1):
            ratio = i / steps
            x = center_x + length * ratio * cos_rad
            y = center_y + length * ratio * sin_rad
            self.canvas.create_text(
                x, y,
                text=val_str,
                fill=color,
                font=("Consolas", max(7, int(font_size)), "bold")
            )

    def update_clock(self):
        self.canvas.delete("all")
        theme = self.current_theme

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width > 1 and height > 1:
            center_x = width // 2
            center_y = height // 2
            radius = int(min(width, height) * 0.42)

            # Cadran extérieur
            self.canvas.create_oval(
                center_x - radius, center_y - radius,
                center_x + radius, center_y + radius,
                outline=theme["circle"], width=2
            )

            # Graduations subtiles des heures (12 points)
            for h in range(12):
                angle = math.radians(h * 30 - 90)
                dot_x = center_x + (radius - 8) * math.cos(angle)
                dot_y = center_y + (radius - 8) * math.sin(angle)
                dot_r = 2
                self.canvas.create_oval(
                    dot_x - dot_r, dot_y - dot_r,
                    dot_x + dot_r, dot_y + dot_r,
                    fill=theme["circle"], outline=""
                )

            now = time.time()
            local = time.localtime(now)
            frac_sec = now % 60
            frac_min = local.tm_min + frac_sec / 60
            frac_hour = (local.tm_hour % 12) + frac_min / 60

            # Valeurs
            sec_val = int(frac_sec)
            min_val = local.tm_min
            hour_val = local.tm_hour % 24

            # Angles fluides
            sec_angle = self.value_to_angle(frac_sec, 60)
            min_angle = self.value_to_angle(frac_min, 60)
            hour_angle = self.value_to_angle(frac_hour, 12)

            # Tailles adaptatives
            scale = radius / 150.0
            h_font = max(9, int(12 * scale))
            m_font = max(8, int(10 * scale))
            s_font = max(7, int(8 * scale))

            # Aiguilles de chiffres
            self.draw_digit_needle(center_x, center_y, hour_val, hour_angle, radius * 0.52, theme["hour"], h_font, steps=5)
            self.draw_digit_needle(center_x, center_y, min_val, min_angle, radius * 0.76, theme["minute"], m_font, steps=8)
            self.draw_digit_needle(center_x, center_y, sec_val, sec_angle, radius * 0.94, theme["second"], s_font, steps=10)

            # Point central
            c_r = max(3, int(4 * scale))
            self.canvas.create_oval(
                center_x - c_r, center_y - c_r,
                center_x + c_r, center_y + c_r,
                fill=theme["center_dot"], outline=""
            )

            # Aide raccourcis en bas
            self.canvas.create_text(
                center_x, height - 14,
                text="[D] Thème  |  [T] Premier plan  |  [F] Plein écran",
                fill=theme["text_info"],
                font=("Segoe UI", max(7, int(8 * scale)))
            )

        self.root.after(33, self.update_clock)  # ~30 FPS


def main():
    root = tk.Tk()
    app = DigitClockApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

import tkinter as tk
import time
import math

WIDTH = 400
HEIGHT = 400
CENTER_X = WIDTH // 2
CENTER_Y = HEIGHT // 2
RADIUS = 150

root = tk.Tk()
root.title("Horloge fluide avec aiguilles en chiffres")
canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="white")
canvas.pack()

def value_to_angle(value, max_value):
    return (value / max_value) * 360 - 90

def draw_digit_needle(value, angle, length, color, font_size, steps=10):
    rad = math.radians(angle)
    for i in range(1, steps + 1):
        ratio = i / steps
        x = CENTER_X + length * ratio * math.cos(rad)
        y = CENTER_Y + length * ratio * math.sin(rad)
        canvas.create_text(x, y, text=str(value).zfill(2), fill=color, font=("Arial", font_size, "bold"))

def update_clock():
    canvas.delete("all")
    canvas.create_oval(CENTER_X - RADIUS, CENTER_Y - RADIUS,
                       CENTER_X + RADIUS, CENTER_Y + RADIUS, outline="black")

    now = time.time()
    local = time.localtime(now)
    frac_sec = now % 60
    frac_min = local.tm_min + frac_sec / 60
    frac_hour = (local.tm_hour % 12) + frac_min / 60

    # Valeurs entières affichées sur les aiguilles
    sec_val = int(frac_sec)
    min_val = local.tm_min
    hour_val = local.tm_hour % 24

    # Angles fluides
    sec_angle = value_to_angle(frac_sec, 60)
    min_angle = value_to_angle(frac_min, 60)
    hour_angle = value_to_angle(frac_hour, 12)

    # Aiguilles-chiffres fluides
    draw_digit_needle(hour_val, hour_angle, RADIUS * 0.5, "black", 12, steps=5)
    draw_digit_needle(min_val, min_angle, RADIUS * 0.75, "blue", 10, steps=8)
    draw_digit_needle(sec_val, sec_angle, RADIUS * 0.95, "red", 8, steps=10)

    root.after(33, update_clock)  # ~30 FPS

update_clock()
root.mainloop()

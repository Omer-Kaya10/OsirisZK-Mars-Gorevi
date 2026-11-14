"""OSIRISZK / Mars Pathfinder v3.0 — Gezgin + Ingenuity tipi drone.

KURULUM: Python 3.10+ (Windows IDLE'da Run > Run Module).
Bağımlılıklar: yalnızca Python standart kütüphanesi (tkinter).

Fizik: Bilimsel kavramları öğretmek için yaklaşıksal OYUN MODELİ.
NASA Ingenuity'nin referans kütlesi ve rotor çapı ile Mars yerçekimi kullanılır.
Gezgin, güneş paneli, batarya değiştirme ve Dünya veri aktarımı kurgusal
araştırma sistemi olup gerçek donanım, bağlantı veya rota garantisi değildir.
"""
from __future__ import annotations

import csv
import json
import math
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Önceki sürümün API'si bu modülden kullanılmaya devam edebilir.
from mars_core import (  # noqa: F401
    INGENUITY_REFERANS, gerekliHavadaKalmaItisi, itisAnalizi,
    gerekli_havada_kalma_itisi, itis_analizi,
    Config, Vehicle, Rock, FlightModel, Mission,
    RoverConfig, Rover, RoverModel, DataPacket, GameSession,
    WORLD_W, WORLD_H, BASE_X, BASE_Y,
)
from kamera import create_capture


class MarsGame:
    BG = "#101923"
    PANEL = "#1a2836"
    FG = "#e6edf5"
    MUTED = "#a2b1be"
    CYAN = "#77ded0"
    ORANGE = "#ffb678"
    ROCK = "#ad725f"
    BLUE = "#8cb9e3"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("OSIRISZK | Mars Pathfinder 3.0 — Gezgin + Drone")
        self.root.geometry("1320x810")
        self.root.minsize(1050, 680)
        self.root.configure(bg=self.BG)
        self.session = GameSession()
        self.paused = True
        self.keys = set()
        self.actions_pressed = set()
        self.last_time = time.monotonic()
        self.accumulator = 0.0
        self.last_sample_at = -1.0
        self.last_blocked_at = -10.0
        self.last_event_text = ""
        self.make_ui()
        self.root.bind("<KeyPress>", self.key_down)
        self.root.bind("<KeyRelease>", self.key_up)
        self.root.bind("<FocusOut>", self.focus_lost)
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.draw()
        self.loop()

    def txt(self, parent, text="", size=10, color=None, bold=False, wrap=None):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color or self.FG,
                        font=("Segoe UI", size, "bold" if bold else "normal"),
                        anchor="w", justify="left", wraplength=wrap)

    def button(self, parent, text, fn, bg="#2d4658"):
        return tk.Button(parent, text=text, command=fn, bg=bg, fg=self.FG,
                         activebackground="#46677b", activeforeground="#ffffff",
                         relief="flat", highlightthickness=0, bd=0, font=("Segoe UI", 10),
                         cursor="hand2", padx=9, pady=6)

    def make_ui(self):
        top = tk.Frame(self.root, bg=self.BG)
        top.pack(fill="x", padx=17, pady=(13, 5))
        self.txt(top, "OSIRISZK  /  MARS PATHFINDER", 19, self.CYAN, True).pack(side="left")
        self.pause_label = self.txt(top, "BEKLEME  /  DRONE GEZGİN ÜZERİNDE", 10, self.ORANGE, True)
        self.pause_label.pack(side="right")
        self.txt(self.root,
                 "Jezero temalı şematik saha   •   Gezgin: enerji / iletişim / keşif   •   Drone: havadan gözlem",
                 9, self.MUTED).pack(anchor="w", padx=18, pady=(0, 7))
        content = tk.Frame(self.root, bg=self.BG)
        content.pack(fill="both", expand=True, padx=15, pady=5)
        self.canvas = tk.Canvas(content, width=850, height=560, bg="#30232a", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        right = tk.Frame(content, bg=self.PANEL, width=370)
        right.pack(side="right", fill="y", padx=(11, 0))
        right.pack_propagate(False)
        self.note = ttk.Notebook(right)
        self.note.pack(fill="both", expand=True, padx=8, pady=8)
        f1 = tk.Frame(self.note, bg=self.PANEL)
        f2 = tk.Frame(self.note, bg=self.PANEL)
        f3 = tk.Frame(self.note, bg=self.PANEL)
        self.note.add(f1, text="DRONE")
        self.note.add(f2, text="GEZGİN")
        self.note.add(f3, text="GÖREV / VERİ")
        self.txt(f1, "DRONE UÇUŞ TELEMETRİSİ", 11, self.CYAN, True).pack(fill="x", padx=13, pady=(18, 8))
        self.drone_stats = self.txt(f1, "", 10)
        self.drone_stats.pack(fill="x", padx=13, pady=4)
        self.txt(f1, "Drone: WASD hareket, Space / ↑ yüksel, Shift / ↓ alçal",
                 9, self.MUTED, wrap=324).pack(fill="x", padx=13, pady=10)
        self.txt(f2, "GEZGİN DESTEK SİSTEMLERİ", 11, self.CYAN, True).pack(fill="x", padx=13, pady=(18, 8))
        self.rover_stats = self.txt(f2, "", 10)
        self.rover_stats.pack(fill="x", padx=13, pady=4)
        self.txt(f2, "Güneş ve pil rafı şarjı otomatik. H: ısıtıcı, G: güneş paneli, T: Dünya bağlantısı",
                 9, self.MUTED, wrap=325).pack(fill="x", padx=13, pady=(8, 4))
        self.txt(f3, "ARAŞTIRMA VE VERİ İLETİMİ", 11, self.CYAN, True).pack(fill="x", padx=13, pady=(18, 8))
        self.mission_stats = self.txt(f3, "", 10, wrap=328)
        self.mission_stats.pack(fill="x", padx=13, pady=(4, 13))
        self.txt(f3, "SON OLAY", 10, self.CYAN, True).pack(fill="x", padx=13, pady=(6, 5))
        self.event_line = self.txt(f3, "", 9, self.ORANGE, wrap=328)
        self.event_line.pack(fill="x", padx=13)
        # Tüm temel eylemlere, klavye odağını kaybetmeden erişmek için düğmeler.
        tabs_bottom = tk.Frame(right, bg=self.PANEL)
        tabs_bottom.pack(fill="x", padx=8, pady=(0, 7))
        actions = [
            ("DRONE TARA [E]", self.scan), ("GEZGİN ARAŞTIR [R]", self.survey),
            ("KENETLE [F]", self.dock), ("PİL DEĞİŞTİR [B]", self.swap),
            ("DÜNYA AKTARIMI [T]", self.toggle_uplink), ("KAMERA [C]", self.photo),
            ("ISI [H]", self.toggle_heater), ("GÜNEŞ [G]", self.toggle_solar),
        ]
        for i, (label, fn) in enumerate(actions):
            self.button(tabs_bottom, label, fn).grid(row=i//2, column=i%2,
                                                   padx=3, pady=3, sticky="ew")
        self.button(tabs_bottom, "GÖRÜNTÜ KAYITLARINI GÖR [V]", self.show_gallery, "#315d6c").grid(
            row=4, column=0, columnspan=2, padx=3, pady=(4, 3), sticky="ew")
        for c in (0, 1):
            tabs_bottom.grid_columnconfigure(c, weight=1)
        toolbar = tk.Frame(self.root, bg=self.BG)
        toolbar.pack(fill="x", padx=16, pady=(3, 4))
        toolbar_actions = [
            ("▶  Başlat / Duraklat", self.toggle_pause, "#1a7b79"),
            ("⇄  Kontrol: Drone / Gezgin [Tab]", self.switch, "#435a79"),
            ("Onar [K]", self.repair, "#2d4658"),
            ("Kaydet", self.save, "#2d4658"),
            ("Yükle", self.load, "#2d4658"),
            ("CSV", self.export_csv, "#2d4658"),
            ("Yeni Görev", self.reset, "#674750"),
        ]
        for title, fn, bg in toolbar_actions:
            self.button(toolbar, title, fn, bg).pack(side="left", padx=(0, 7))
        self.notice = self.txt(self.root, "Başlat'a bas; drone gezginin üzerinde başlar.", 10, self.ORANGE)
        self.notice.pack(fill="x", padx=18, pady=(1, 10))

    def status(self, message: str):
        self.notice.config(text=message)
        self.last_event_text = message

    def toggle_pause(self):
        if self.session.mission.finished or self.session.mission.failed:
            self.status("Görev sonlandı. Yeni Görev düğmesine bas.")
            return
        self.paused = not self.paused
        self.last_time = time.monotonic()
        self.accumulator = 0.0
        self.status("Görev sürüyor." if not self.paused else "Görev duraklatıldı.")
        self.refresh_header()

    def refresh_header(self):
        state = "DURAKLATILDI" if self.paused else "GÖREV AKTİF"
        mode = "GEZGİN" if self.session.selected == "rover" else "DRONE"
        docked = " / KENETLİ" if self.session.drone.docked else ""
        self.pause_label.config(text=f"{state}  |  KONTROL: {mode}{docked}",
                                fg=self.ORANGE if self.paused else self.CYAN)

    def switch(self):
        selected = self.session.switch_vehicle()
        self.keys.clear()
        self.status(f"Kontrol: {'GEZGİN' if selected == 'rover' else 'DRONE'} — WASD kullan.")
        self.refresh_header()

    def reset(self):
        self.session = GameSession()
        self.paused = True
        self.keys.clear()
        self.actions_pressed.clear()
        self.last_sample_at = -1.0
        self.status("Yeni görev: Drone gezgin üzerinde. Başlat ve Space/↑ ile kalk.")
        self.refresh_header()
        self.draw()

    def focus_lost(self, _event):
        self.keys.clear()
        self.actions_pressed.clear()

    def key_down(self, event):
        key = event.keysym.lower()
        # Tek-seferlik komutlarda key-repeat, aynı işlemi durmadan çalıştırmasın.
        if key not in self.actions_pressed:
            action = {
                "p": self.toggle_pause, "tab": self.switch,
                "e": self.scan, "r": self.survey,
                "f": self.dock, "b": self.swap,
                "t": self.toggle_uplink, "h": self.toggle_heater,
                "g": self.toggle_solar, "c": self.photo,
                "k": self.repair, "v": self.show_gallery,
            }.get(key)
            if action:
                self.actions_pressed.add(key)
                action()
        if key in ("w", "a", "s", "d", "space", "up", "down", "shift_l", "shift_r"):
            self.keys.add(key)
        if key == "tab":
            return "break"  # Sekmelerin odağını bozmasın.

    def key_up(self, event):
        key = event.keysym.lower()
        self.keys.discard(key)
        self.actions_pressed.discard(key)

    def axes(self):
        k = self.keys
        x = int("d" in k) - int("a" in k)
        y = int("s" in k) - int("w" in k)
        climb = (int("up" in k or "space" in k)
                 - int("down" in k or "shift_l" in k or "shift_r" in k))
        return x, y, climb

    def _new_capture(self, packet):
        s = self.session
        v = s.drone if packet.source == "drone" else s.rover
        try:
            capture_path = create_capture(Path(__file__).resolve().parent / "kamera_kayitlari",
                                          packet.source, packet.packet_id, v.x, v.y,
                                          s.drone.altitude if packet.source == "drone" else 0.0,
                                          packet.target)
            # Görevin başka bilgisayara taşınmasında da PNG'ler bulunabilsin.
            packet.image_file = Path(capture_path).relative_to(Path(__file__).resolve().parent).as_posix()
        except OSError as exc:
            self.status(f"Paket hazır fakat PNG kaydı yapılamadı: {exc}")

    def scan(self):
        if self.paused:
            self.status("Tarama için önce görevi başlat.")
            return
        count = len(self.session.packets)
        result = self.session.scan_drone()
        if len(self.session.packets) > count:
            self._new_capture(self.session.packets[-1])
        self.status(result)

    def survey(self):
        if self.paused:
            self.status("Araştırma için önce görevi başlat.")
            return
        count = len(self.session.packets)
        result = self.session.survey_rover()
        if len(self.session.packets) > count:
            self._new_capture(self.session.packets[-1])
        self.status(result)

    def photo(self):
        if self.paused:
            self.status("Kamera için önce görevi başlat.")
            return
        count = len(self.session.packets)
        result = self.session.take_photo()
        if len(self.session.packets) > count:
            self._new_capture(self.session.packets[-1])
        self.status(result)

    def dock(self):
        if self.paused:
            self.status("Kenetlenmek için görevi başlat.")
            return
        self.status(self.session.try_dock())

    def swap(self):
        if self.paused:
            self.status("Batarya değişimi için görevi başlat.")
            return
        self.status(self.session.swap_battery())

    def repair(self):
        if self.paused:
            self.status("Onarım için görevi başlat.")
            return
        self.status(self.session.repair())

    def toggle_uplink(self):
        self.session.toggle_uplink()
        self.status(self.session.events[-1])

    def toggle_heater(self):
        self.session.toggle_heater()
        self.status(self.session.events[-1])

    def toggle_solar(self):
        self.session.toggle_solar()
        self.status(self.session.events[-1])

    def loop(self):
        now = time.monotonic()
        delta = min(0.1, max(0.0, now - self.last_time))
        self.last_time = now
        if not self.paused:
            self.accumulator += delta
            while self.accumulator >= 0.02:
                self.session.step(0.02, *self.axes())
                self.accumulator -= 0.02
                if self.session.rover_model.last_move_blocked and self.session.elapsed - self.last_blocked_at > 2:
                    self.last_blocked_at = self.session.elapsed
                    self.status("Gezginin önünde kayalık/harita sınırı var. Etrafından dolaş.")
                if self.session.mission.finished or self.session.mission.failed:
                    self.paused = True
                    self.status(self.session.mission.message)
                    self.refresh_header()
                    break
            if self.session.elapsed - self.last_sample_at >= 0.5:
                self.session.report.append(self.session.telemetry_row())
                self.session.report = self.session.report[-2500:]
                self.last_sample_at = self.session.elapsed
        self.draw()
        try:
            self.root.after(33, self.loop)
        except tk.TclError:
            pass

    def draw(self):
        canvas = self.canvas
        canvas.delete("all")
        width, height = max(200, canvas.winfo_width()), max(200, canvas.winfo_height())
        sx, sy = width / WORLD_W, height / WORLD_H
        def pos(x, y):
            return x * sx, y * sy
        canvas.create_rectangle(0, 0, width, height, fill="#34262c", outline="")
        # Soluk yüzey katmanları - gerçek Mars haritası değil, şematik zemin.
        for i in range(6):
            x1 = (i * .22 * width) % width
            y1 = height * (.12 + .115 * i)
            canvas.create_oval(x1 - 180, y1 - 52, x1 + 300, y1 + 120,
                               fill="#3e2c30" if i % 2 else "#412e2d", outline="")
        for i in range(0, WORLD_W, 80):
            canvas.create_line(i*sx, 0, i*sx, height, fill="#594042", dash=(1, 8))
        for j in range(0, WORLD_H, 80):
            canvas.create_line(0, j*sy, width, j*sy, fill="#594042", dash=(1, 8))
        base_x, base_y = pos(BASE_X, BASE_Y)
        canvas.create_oval(base_x-37, base_y-37, base_x+37, base_y+37,
                           fill="#245e5c", outline=self.CYAN, width=2)
        canvas.create_oval(base_x-27, base_y-27, base_x+27, base_y+27,
                           outline="#9aead9", dash=(3, 6), width=2)
        canvas.create_text(base_x+35, base_y+57, text="ANA ÜS / DÖNÜŞ", fill=self.CYAN,
                           anchor="w", font=("Segoe UI", 9, "bold"))
        for hx, hy, r in self.session.mission.hazards:
            x, y = pos(hx, hy)
            size = r * (sx + sy) * .50
            canvas.create_polygon(x-size, y+size*.6, x-size*.35, y-size*.6,
                                  x+size*.37, y-size*.8, x+size, y+size*.45,
                                  fill="#80504a", outline="#a37067", width=1.5)
        for rock in self.session.mission.rocks:
            x, y = pos(rock.x, rock.y)
            color = self.CYAN if rock.scanned else self.ORANGE
            r = 66 * min(sx, sy)
            canvas.create_oval(x-r, y-r, x+r, y+r, outline=color, dash=(2, 7))
            canvas.create_oval(x-14, y-14, x+14, y+14, fill=self.ROCK, outline=color, width=2)
            label = (("✓ " if rock.scanned else "○ ") + rock.label
                     + (" • G" if rock.surveyed else ""))
            canvas.create_text(x, y+27, text=label, fill=color,
                               font=("Segoe UI", 9, "bold"))
        self.draw_rover(canvas, pos, sx, sy)
        self.draw_drone(canvas, pos)
        # Uplink göstergesi: Dünya'ya gerçek radyo bağlantısı değil.
        r = self.session.rover
        rover_pos = pos(r.x, r.y)
        if self.session.rover_model.uplink_enabled:
            if self.session.rover_model.is_uplinking:
                canvas.create_line(*rover_pos, width-45, 55, fill=self.CYAN,
                                   dash=(6, 5), width=2)
            canvas.create_oval(width-67, 31, width-23, 75, outline=self.CYAN, width=2)
            canvas.create_text(width-45, 53, text="D", fill="#effef9", font=("Segoe UI", 12, "bold"))
            canvas.create_text(width-65, 87, text="DÜNYA (SİMÜLE)", anchor="e", fill=self.CYAN,
                               font=("Segoe UI", 8, "bold"))
        canvas.create_text(14, 14, text="JEZERO  •  OYUN HARİTASI  /  GERÇEK ÖLÇEK DEĞİL",
                           fill="#f3c8b0", anchor="nw", font=("Segoe UI", 10, "bold"))
        canvas.create_text(14, height-13, text=("SEÇİLİ: GEZGİN" if self.session.selected == "rover"
                                                else "SEÇİLİ: DRONE") + "  •  Tab: araç değiştir",
                           fill=self.CYAN, anchor="sw", font=("Segoe UI", 10, "bold"))
        self.update_panel()

    # Çizimler modeller/ klasöründeki mimari çizimlerin ÜST GÖRÜNÜŞÜNE göre yapılır:
    # gezgin 1,60 m × 1,20 m (arka yarı güneş paneli, ön yarı 0,60 × 0,60 m drone platformu,
    # her yanda 3 teker), drone Ø1,20 m eş eksenli iki rotor. Ölçek: 1,20 m = 40 piksel.
    ROVER_HALF_L, ROVER_HALF_W = 27, 20

    def draw_rover(self, canvas, pos, sx, sy):
        r = self.session.rover
        x, y = pos(r.x, r.y)
        L, W = self.ROVER_HALF_L, self.ROVER_HALF_W
        if self.session.selected == "rover":
            canvas.create_oval(x-L-9, y-W-12, x+L+9, y+W+12,
                               outline=self.CYAN, width=2, dash=(3, 4))
        # 6 teker (rocker-bogie): her yanda 3
        for dx in (-19, 0, 19):
            for yy in (-W-7, W-1):
                canvas.create_rectangle(x+dx-6, y+yy, x+dx+6, y+yy+8, fill="#101a22", outline="#8d9194")
        canvas.create_rectangle(x-L, y-W, x+L, y+W, fill="#a58b78", outline="#f0d3ae", width=2)
        # Arka yarı: güneş paneli (G ile açılıp kapanır)
        panel = "#215979" if r.solar_deployed else "#3a3f44"
        canvas.create_rectangle(x-L+3, y-W+3, x-2, y+W-3, fill=panel, outline="#80badc" if r.solar_deployed else "#666")
        if r.solar_deployed:
            for i in range(1, 4):
                canvas.create_line(x-L+3+i*(L-5)/4, y-W+3, x-L+3+i*(L-5)/4, y+W-3, fill="#6a9fbf")
            for j in range(1, 5):
                canvas.create_line(x-L+3, y-W+3+j*(2*W-6)/5, x-2, y-W+3+j*(2*W-6)/5, fill="#6a9fbf")
        # Ön yarı: 0,60 × 0,60 m drone iniş platformu (H)
        px, half = x + L/2, W/2
        canvas.create_rectangle(px-half, y-half, px+half, y+half, fill="#5b6867", outline=self.CYAN)
        canvas.create_oval(px-half+2, y-half+2, px+half-2, y+half-2, outline="#f7eec8")
        canvas.create_text(px, y, text="H", fill="#f7eec8", font=("Segoe UI", 8, "bold"))
        # Kamera direği (ön sol köşe) ve robotik kol (önde)
        canvas.create_oval(x+L-7, y-W-1, x+L+1, y-W+7, fill="#c6e4f3", outline="#294b59")
        canvas.create_line(x+L, y+W-6, x+L+11, y+W-2, fill="#d2c9a6", width=3)
        if r.heater_enabled:
            canvas.create_oval(x-L+5, y+W-9, x-L+11, y+W-3, fill="#ffb36e", outline="")
        canvas.create_text(x+L+6, y+W+14, text="GEZGİN / ROVER", anchor="w", fill="#f4e6d7",
                           font=("Segoe UI", 8, "bold"))

    def draw_drone(self, canvas, pos):
        d = self.session.drone
        x, y = pos(d.x, d.y)
        rotor = self.ROVER_HALF_W          # Ø1,20 m rotor = gezgin genişliği
        if d.docked:
            x += self.ROVER_HALF_L / 2     # platformun ortasında durur
            offset = 0
            angle = 0.6
        else:
            shadow_r = 9 + min(27, d.altitude * 2)
            canvas.create_oval(x-shadow_r, y-shadow_r*.40, x+shadow_r, y+shadow_r*.40,
                               fill="#1b1b20", outline="")
            offset = min(30, d.altitude * 2.5)
            angle = self.session.elapsed * 9.0 if d.airborne else 0.6
        if self.session.selected == "drone":
            canvas.create_oval(x-rotor-5, y-rotor-5-offset, x+rotor+5, y+rotor+5-offset,
                               outline=self.CYAN, width=2, dash=(3, 4))
        # Eş eksenli iki rotor: üstten bakınca zıt yönde dönen iki pala çifti
        for a, color in ((angle, "#f9fafb"), (-angle + 1.2, "#cfe0ee")):
            dx, dy = math.cos(a) * rotor, math.sin(a) * rotor
            canvas.create_line(x-dx, y-dy-offset, x+dx, y+dy-offset, fill=color, width=3)
        canvas.create_rectangle(x-4, y-4-offset, x+4, y+4-offset, fill="#e1e5e6", outline="#87b3c4", width=2)
        canvas.create_rectangle(x-2, y-2-offset, x+2, y+2-offset, fill="#215979", outline="")
        if not d.docked:
            canvas.create_text(x, y-rotor-offset-10, text=f"{d.altitude:.1f} m",
                               fill="white", font=("Segoe UI", 9, "bold"))

    def update_panel(self):
        self.refresh_header()
        s = self.session
        d, r, c = s.drone, s.rover, s.model.config
        a = s.model.analysis()
        progress = s.mission_progress()
        pwr = s.rover_model
        self.drone_stats.config(text=(
            f"Durum             {'GEZGİNE KENETLİ' if d.docked else 'HAVADA' if d.airborne else 'YERDE'}\n"
            f"Süre                    {s.elapsed:7.1f} s\n"
            f"Yükseklik            {d.altitude:7.2f} m\n"
            f"Dikey hız             {d.vertical_speed:7.2f} m/s\n"
            f"Kütle                   {c.mass:7.2f} kg\n"
            f"Gerekli itiş         {a['gerekliItisN']:7.2f} N\n"
            f"Anlık itiş            {s.model.thrust_n:7.2f} N\n"
            f"İtiş oranı             {a['itisOrani']:7.2f}\n"
            f"Anlık güç             {s.model.power_w:7.1f} W\n"
            f"Batarya               {d.battery_wh:7.2f} / {c.battery_wh:.0f} Wh\n"
            f"Sağlık                   {d.health:7.0f} / 100\n"
            f"Toplanan paket       {progress['waiting_on_drone']:7d}\n"
            f"X/Y                  {d.x:5.0f} / {d.y:5.0f}"
        ))
        spares = ", ".join(f"{b:.0f}" for b in r.spare_batteries_wh) or "yok"
        self.rover_stats.config(text=(
            f"Konum                   {r.x:5.0f} / {r.y:5.0f}\n"
            f"Ana pil              {r.battery_wh:7.1f} / {pwr.config.battery_capacity_wh:.0f} Wh\n"
            f"Güneş çıkışı        {pwr.solar_w:7.1f} W\n"
            f"Tüketim              {pwr.load_w:7.1f} W\n"
            f"Yedek şarjı          {pwr.charge_w:7.1f} W\n"
            f"Dış ortam              {pwr.ambient_c:7.1f} °C\n"
            f"Batarya bölmesi    {r.bay_temp_c:7.1f} °C\n"
            f"Isıtıcı               {'AÇIK' if r.heater_enabled else 'KAPALI'}\n"
            f"Panel                  {'AÇIK' if r.solar_deployed else 'KAPALI'}\n"
            f"Yedek piller         [{spares}] Wh\n"
            f"Batarya değişimi       {r.swapped_count}\n"
            f"Gezgin sağlığı         {r.health:.0f}/100\n"
            f"Radyo                   {'AKTARIYOR' if pwr.is_uplinking else 'AÇIK' if pwr.uplink_enabled else 'KAPALI'}\n"
            f"Toz fırtınası         {'VAR' if pwr.storm_active else 'YOK'}"
        ))
        sent = progress["transmitted"]
        total = progress["total_packets"]
        line1 = "✓" if progress["drone"] == 3 else "○"
        line2 = "✓" if progress["rover"] >= 2 else "○"
        line3 = "✓" if total >= 5 and sent == total else "○"
        line4 = "✓" if progress["docked"] else "○"
        line5 = "✓" if progress["at_base"] else "○"
        self.mission_stats.config(text=(
            f"{line1} Drone kaya taraması      {progress['drone']}/3\n"
            f"{line2} Gezgin yakın gözlemi    {progress['rover']}/2 (en az)\n"
            f"{line3} Dünya'ya veri iletimi  {sent}/{total} paket\n"
            f"{line4} Drone platformda      {'EVET' if progress['docked'] else 'HAYIR'}\n"
            f"{line5} Gezgin ana üste        {'EVET' if progress['at_base'] else 'HAYIR'}\n\n"
            "SIRA:\n"
            "1. Drone ile kayalara uç (Space, WASD), E ile tara.\n"
            "2. Tab ile gezgine geç; WASD ile kayalara yanaş, R ile araştır.\n"
            "3. Drone'u gezgine yaklaştır; alçalıp F ile kenetle.\n"
            "4. Gerekirse B ile pil değiştir, T ile Dünya'ya veri aktar.\n"
            "5. Tüm paketler Dünya'ya iletilince, gezginle üsse dön.\n\n"
            "K: Drone bakımı, C: Şematik kamera fotoğrafı."
        ))
        if s.events:
            self.event_line.config(text=s.events[-1])

    def _capture_path(self, image_file: str) -> Path:
        # Güvenli, taşınabilir, sadece oyunun kamera klasöründeki dosya.
        return Path(__file__).resolve().parent / image_file

    def show_gallery(self):
        """Simülasyon kamera PNG'lerini oyun içinde görüntüler."""
        stored = [p for p in self.session.packets if p.image_file and self._capture_path(p.image_file).is_file()]
        if not stored:
            messagebox.showinfo("Kamera görüntüleri", "Önce E, R veya C ile bir görüntü kaydet.")
            return
        window = tk.Toplevel(self.root)
        window.title("OSIRISZK — Sanal kamera kayıtları (şematik görüntüler)")
        window.geometry("750x550")
        window.configure(bg=self.BG)
        self.txt(window, "KAMERA / GÖRÜNTÜ ARŞİVİ", 15, self.CYAN, True).pack(fill="x", padx=14, pady=(14, 5))
        self.txt(window, "Bu görüntüler oyun tarafından üretilmiştir; gerçek Mars fotoğrafı değildir.",
                 9, self.MUTED).pack(fill="x", padx=14, pady=(0, 8))
        center = tk.Frame(window, bg=self.BG)
        center.pack(fill="both", expand=True, padx=12, pady=8)
        listing = tk.Listbox(center, width=31, bg=self.PANEL, fg=self.FG,
                             selectbackground="#397e88", relief="flat", borderwidth=0,
                             font=("Segoe UI", 10))
        listing.pack(side="left", fill="y", padx=(0, 12))
        preview = tk.Frame(center, bg=self.PANEL)
        preview.pack(side="left", fill="both", expand=True)
        image_label = self.txt(preview, "", 10)
        image_label.pack(pady=22)
        image_info = self.txt(preview, "", 9, self.MUTED, wrap=420)
        image_info.pack(fill="x", padx=10, pady=7)
        for packet in stored:
            listing.insert("end", f"#{packet.packet_id:03d} • {packet.source} • {packet.target[:15]}")

        def display(_event=None):
            choice = listing.curselection()
            if not choice:
                return
            packet = stored[choice[0]]
            try:
                photo = tk.PhotoImage(file=str(self._capture_path(packet.image_file))).zoom(2, 2)
            except tk.TclError as exc:
                image_info.config(text=f"Görüntü açılmadı: {exc}")
                return
            image_label.config(image=photo, text="")
            image_label.image = photo
            image_info.config(text=(f"Kaynak: {packet.source}\n"
                                    f"Hedef: {packet.target}\n"
                                    f"Görev saati: {packet.acquired_s:.1f} s\n"
                                    f"Durum: {'Dünya aktarıldı' if packet.delivered else 'Gezginde' if packet.transferred_to_rover else 'Drone hafızasında'}\n"
                                    f"Dosya: {packet.image_file}"))
        listing.bind("<<ListboxSelect>>", display)
        listing.selection_set(0)
        display()
        window.transient(self.root)

    def save(self):
        path = filedialog.asksaveasfilename(title="Görevi kaydet", initialfile="osiriszk_kayit_v3.json",
                                            defaultextension=".json", filetypes=[("JSON dosyası", "*.json")])
        if not path:
            return
        try:
            content = json.dumps(self.session.to_dict(), ensure_ascii=False, indent=2, allow_nan=False)
            Path(path).write_text(content, encoding="utf-8")
            self.status("Görev başarıyla kaydedildi. Kamera PNG dosyaları ayrı klasördedir.")
        except (OSError, TypeError, ValueError) as exc:
            messagebox.showerror("Kayıt hatası", str(exc))

    def load(self):
        path = filedialog.askopenfilename(title="Görev kaydı yükle", filetypes=[("JSON dosyası", "*.json")])
        if not path:
            return
        try:
            path = Path(path)
            if path.stat().st_size > 4_000_000:
                raise ValueError("Kayıt dosyası çok büyük (en çok 4 MB).")
            data = json.loads(path.read_text(encoding="utf-8"),
                              parse_constant=lambda v: (_ for _ in ()).throw(ValueError("NaN/Infinity yasak")))
            fresh = GameSession.from_dict(data)  # Hata olursa mevcut oyun bozulmaz.
            self.session = fresh
            self.paused = True
            self.keys.clear()
            self.last_sample_at = fresh.elapsed
            self.refresh_header()
            self.status("Görev yüklendi. Başlat'a basıp kaldığın yerden devam et.")
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            messagebox.showerror("Yükleme hatası", str(exc))

    def export_csv(self):
        if not self.session.report:
            messagebox.showinfo("CSV", "Önce görevi başlat ve kısa süre simülasyonu çalıştır.")
            return
        path = filedialog.asksaveasfilename(initialfile="osiriszk_telemetri.csv",
                                            defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as handle:
                fields = list(self.session.telemetry_row())
                writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(self.session.report)
            self.status("Telemetri CSV olarak dışa aktarıldı.")
        except (OSError, ValueError) as exc:
            messagebox.showerror("CSV hatası", str(exc))


def main():
    root = tk.Tk()
    MarsGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()

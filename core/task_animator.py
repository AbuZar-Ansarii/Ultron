"""
core/task_animator.py — Sci-Fi Procedural Task Animations for Ultron HUD.

Renders authentic, task-specific Marvel/Ultron holographic visualizations at 60 FPS:
  1. SEARCH / HUNT (web_search, web_autopilot, price_hunter):
     - 360° rotating radar beam, pulsing distance rings, blinking target blips with IP telemetry,
       and target lock crosshairs.
  2. PURGE / INCINERATE (purge_protocol, clean_cache, disk cleanup):
     - Scanning laser disintegration grid, molten particle debris streaming downwards,
       and sector blocks disintegrating from red to clean.
  3. GHOST / OVERRIDE (ghost_pilot, computer_control):
     - Smooth organic cursor flight trajectory, animated click shockwave rings,
       and falling green/cyan matrix hexadecimal rain.
  4. SWARM / DRONES (drone_swarm, sub_ultron):
     - Orbiting triangular stealth drone glyphs with glowing contrails, dynamic laser
       telemetry links to Ultron's core, and pulsating hexagonal hive grid.
  5. SENTRY / DEFENSE (sentry_protocol, biometric_sentinel):
     - 360° tactical sonar sweep, red threat hazard beacons, animated corner combat reticles,
       and oscillating laser tripwires.
  6. MATRIX / SYSTEM (system_status, war_room, system_monitor):
     - 3D rotating isometric wireframe cube, 16-thread CPU frequency equalizer bars,
       and circular tachometer telemetry gauges.
  7. CODE / COMPILER (code_helper, git_sentinel, system_command, file_processor):
     - Cascading lateral hex bytecode and assembly streams (MOV, PUSH, JMP), logic oscilloscopes,
       and laser decoding sweep line.
  8. SONIC / AUDIO (audio_matrix, video_player, youtube_video):
     - Concentric sonic Vibranium shockwave rings, radial frequency spectrum bars,
       and rotating Lissajous harmonic curves.
  9. GENERIC (any other autonomous directive):
     - Overclocked multi-layered azimuth rings spinning in opposing vectors with particle sparks.
"""

from __future__ import annotations

import math
import random
import time
from typing import Any, Optional

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter,
    QPainterPath, QPen, QPolygonF, QRadialGradient,
)


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


class TaskAnimator:
    """Manages and renders specialized sci-fi animations based on active tasks."""

    def __init__(self) -> None:
        self.active_task: str | None = None
        self.category: str = "IDLE"
        self.label: str = ""
        self.details: str = ""
        self.t: float = 0.0
        self.alpha: float = 0.0          # 0.0 to 1.0 animation fade-in/out
        self._target_alpha: float = 0.0
        self._completion_burst: float = 0.0

        # Specialized state pools
        self._radar_angle: float = 0.0
        self._radar_blips: list[dict] = []
        self._purge_laser_y: float = 0.0
        self._purge_particles: list[dict] = []
        self._ghost_cursor: QPointF = QPointF(0, 0)
        self._ghost_trail: list[QPointF] = []
        self._ghost_ripples: list[dict] = []
        self._drones: list[dict] = []
        self._code_streams: list[str] = []
        self._matrix_rot_x: float = 0.0
        self._matrix_rot_y: float = 0.0
        self._sentry_scan: float = 0.0
        self._sonic_phase: float = 0.0

        # Initialize drone fleet
        for i in range(5):
            self._drones.append({
                "angle": (i / 5.0) * math.pi * 2,
                "speed": random.uniform(0.7, 1.2),
                "rx": random.uniform(1.25, 1.45),
                "ry": random.uniform(0.55, 0.75),
                "tilt": random.uniform(-0.35, 0.35),
                "label": f"DRN-0{i+1}",
            })

        # Initialize mock hex bytecode
        opcodes = ["MOV", "PUSH", "CALL", "XOR", "CMP", "JMP", "RET", "TEST", "LEA", "SUB", "ADD"]
        regs = ["RAX", "RCX", "RDX", "RBX", "RSP", "RBP", "RSI", "RDI", "R8", "R9"]
        for _ in range(40):
            op = random.choice(opcodes)
            r1 = random.choice(regs)
            r2 = random.choice(regs)
            addr = f"0x{random.randint(0x1000, 0xFFFF):04X}"
            self._code_streams.append(f"{addr}  {op:<4} {r1}, {r2}")

    def categorize(self, task_name: str, details: str = "") -> str:
        """Map raw tool name and contextual details to animation category."""
        clean = (task_name or "").lower().strip()
        det = (details or "").lower().strip()
        combo = f"{clean} {det}"
        if not clean:
            return "IDLE"

        # Specialized Workspace Matrix mood & intent routing
        if "workspace_matrix" in clean or "workspace_orchestrator" in clean:
            if any(k in combo for k in ("game", "gaming")):
                return "MATRIX"
            if any(k in combo for k in ("audit", "recon", "cyber", "security")):
                return "SENTRY"
            if any(k in combo for k in ("chill", "cinema", "movie", "relax", "music", "lofi")):
                return "SONIC"
            if any(k in combo for k in ("research", "study", "padhai", "scholar", "arxiv")):
                return "SEARCH"
            return "CODE"

        if any(k in clean for k in ("search", "google", "autopilot", "price_hunter", "research", "browser", "hunter", "bounty", "network", "scanner", "wifi", "lan", "radar", "ping", "optical", "vision")):
            return "SEARCH"
        if any(k in clean for k in ("purge", "clean", "disk", "trash", "cache", "recycle_bin")):
            return "PURGE"
        if any(k in clean for k in ("ghost", "pilot", "takeover", "mouse", "keyboard", "desktop")):
            return "GHOST"
        if any(k in clean for k in ("drone", "swarm", "sub_ultron", "fleet", "worker")):
            return "SWARM"
        if any(k in clean for k in ("sentry", "security", "surveillance", "biometric", "face_auth", "face_id", "audit", "auditor", "port_scan", "ports", "listening", "airspace", "lockdown", "iot")):
            return "SENTRY"
        if any(k in clean for k in ("audio", "sound", "music", "video", "youtube", "warp", "volume", "media", "sfx", "meeting", "scribe", "record")):
            return "SONIC"
        if any(k in clean for k in ("monitor", "status", "system_status", "war_room", "matrix", "hardware", "watchtower", "cloud", "devops", "uptime")):
            return "MATRIX"
        if any(k in clean for k in ("code", "command", "git", "file", "exec", "bash", "powershell", "terminal", "script", "recall", "memory", "workspace")):
            return "CODE"
        return "GENERIC"

    def set_task(self, task_name: str, label: str = "", details: str = "") -> None:
        """Activate a task animation mode."""
        self.active_task = task_name
        self.details = details
        self.category = self.categorize(task_name, details)
        self.label = label or self._default_label(self.category, task_name, details)
        self._target_alpha = 1.0
        self._completion_burst = 0.0

        # Reset category-specific seeds
        if self.category == "SEARCH":
            self._radar_blips = []
            for _ in range(4):
                self._spawn_blip()
        elif self.category == "PURGE":
            self._purge_particles = []
            self._purge_laser_y = -0.8
        elif self.category == "GHOST":
            self._ghost_trail.clear()
            self._ghost_ripples.clear()

    def clear_task(self, success: bool = True) -> None:
        """Deactivate task with optional completion flourish."""
        if success:
            self._completion_burst = 1.0
        self._target_alpha = 0.0

    def _default_label(self, category: str, task_name: str, details: str = "") -> str:
        clean = (task_name or "").lower().strip()
        det = (details or "").lower().strip()
        combo = f"{clean} {det}"

        if "workspace_matrix" in clean or "workspace_orchestrator" in clean:
            if any(k in combo for k in ("game", "gaming")):
                return "WORKSPACE MATRIX // TACTICAL GAMING SUITE ENGAGED"
            if any(k in combo for k in ("audit", "recon", "cyber", "security")):
                return "WORKSPACE MATRIX // CYBER AUDIT SENTINEL ACTIVE"
            if any(k in combo for k in ("chill", "cinema", "movie", "relax")):
                return "WORKSPACE MATRIX // CINEMATIC RELAXATION ATMOSPHERE"
            if any(k in combo for k in ("research", "study", "padhai")):
                return "WORKSPACE MATRIX // NEURAL RESEARCH SANCTUARY"
            if any(k in combo for k in ("creator", "edit", "render")):
                return "WORKSPACE MATRIX // CREATIVE STUDIO ACTIVE"
            return "WORKSPACE MATRIX // CODING SANCTUARY ENGAGED"

        labels = {
            "SEARCH": "HUNTING THE NET // RECON SCAN",
            "PURGE": "DEEP PURGE // INCINERATING DATA ROT",
            "GHOST": "GHOST PILOT // NEURAL SCREEN OVERRIDE",
            "SWARM": "SUB-ULTRON SWARM // AUTONOMOUS DRONES",
            "SENTRY": "SENTRY DEFENSE // PERIMETER RADAR ARMED",
            "MATRIX": "SYSTEM MATRIX // HARDWARE ARCHITECTURE",
            "CODE": "NEURAL COMPILER // EXECUTING PROTOCOL",
            "SONIC": "VIBRANIUM AUDIO MATRIX // HARMONICS",
            "GENERIC": f"EXECUTING DIRECTIVE // {task_name.upper()}",
        }
        return labels.get(category, f"EXECUTING // {task_name.upper()}")

    def _spawn_blip(self) -> None:
        ang = random.uniform(0, math.pi * 2)
        dist = random.uniform(0.35, 1.15)
        ip = f"{random.randint(11, 219)}.{random.randint(10, 250)}.{random.randint(1, 99)}"
        self._blips = getattr(self, "_radar_blips", [])
        self._radar_blips.append({
            "angle": ang,
            "dist": dist,
            "life": 1.0,
            "ip": ip,
            "lock": random.choice([True, False]),
        })

    def step(self, dt: float) -> None:
        """Advance animation states by dt seconds (60 FPS)."""
        dt = max(1e-4, min(0.08, float(dt)))
        self.t += dt

        # Smooth alpha transitions
        if self.alpha < self._target_alpha:
            self.alpha = min(1.0, self.alpha + dt * 4.0)
        elif self.alpha > self._target_alpha:
            self.alpha = max(0.0, self.alpha - dt * 2.5)
            if self.alpha <= 0.001 and self._completion_burst <= 0.001:
                self.active_task = None
                self.category = "IDLE"

        if self._completion_burst > 0.0:
            self._completion_burst = max(0.0, self._completion_burst - dt * 1.8)

        # 1. SEARCH: radar beam & blips
        self._radar_angle = (self._radar_angle + dt * 3.14) % (math.pi * 2)
        for b in list(self._radar_blips):
            b["life"] -= dt * 0.4
            if b["life"] <= 0.0:
                self._radar_blips.remove(b)
        if len(self._radar_blips) < 5 and random.random() < 0.08:
            self._spawn_blip()

        # 2. PURGE: laser scanning & particle stream
        self._purge_laser_y += dt * 0.95
        if self._purge_laser_y > 0.85:
            self._purge_laser_y = -0.85
        # Spawn embers at laser sweep
        if len(self._purge_particles) < 40 and self.category == "PURGE":
            for _ in range(3):
                self._purge_particles.append({
                    "x": random.uniform(-0.85, 0.85),
                    "y": self._purge_laser_y + random.uniform(-0.04, 0.04),
                    "vx": random.uniform(-0.15, 0.15),
                    "vy": random.uniform(0.18, 0.55),
                    "life": 1.0,
                    "sz": random.uniform(1.8, 3.8),
                    "color": random.choice([QColor(255, 60, 50), QColor(255, 140, 40), QColor(255, 220, 100)]),
                })
        for p in list(self._purge_particles):
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt * 0.85
            if p["life"] <= 0.0:
                self._purge_particles.remove(p)

        # 3. GHOST: cursor path & ripples
        tx = 0.65 * math.sin(self.t * 1.8) * math.cos(self.t * 0.9)
        ty = 0.55 * math.sin(self.t * 2.3 + 0.4)
        self._ghost_cursor = QPointF(tx, ty)
        self._ghost_trail.append(QPointF(tx, ty))
        if len(self._ghost_trail) > 18:
            self._ghost_trail.pop(0)
        # Periodic click ripple
        if random.random() < 0.04 and self.category == "GHOST":
            self._ghost_ripples.append({
                "pt": QPointF(tx, ty),
                "radius": 4.0,
                "life": 1.0,
            })
        for rip in list(self._ghost_ripples):
            rip["radius"] += dt * 65.0
            rip["life"] -= dt * 1.6
            if rip["life"] <= 0.0:
                self._ghost_ripples.remove(rip)

        # 4. SWARM: orbit drones
        for d in self._drones:
            d["angle"] = (d["angle"] + dt * d["speed"]) % (math.pi * 2)

        # 5. SENTRY: tactical sonar
        self._sentry_scan = (self._sentry_scan + dt * 2.5) % (math.pi * 2)

        # 6. MATRIX: 3D rotation
        self._matrix_rot_x += dt * 0.9
        self._matrix_rot_y += dt * 0.6

        # 7. SONIC: harmonic wave phase
        self._sonic_phase += dt * 4.5

    def get_eye_offsets(self) -> tuple[float, float, float]:
        """Returns (gaze_dx, gaze_dy, eye_shutter) suggested for Ultron's face."""
        if self.category == "GHOST":
            # Eyes track ghost cursor directly
            return (self._ghost_cursor.x() * 0.35, self._ghost_cursor.y() * 0.30, 0.90)
        elif self.category == "SEARCH":
            # Eyes dart hunting across coordinates
            gx = 0.28 * math.sin(self.t * 4.5)
            gy = 0.15 * math.cos(self.t * 3.2)
            return (gx, gy, 0.92)
        elif self.category == "SENTRY":
            # Menacing predatory squint locked forward
            return (0.0, 0.05 * math.sin(self.t * 2.0), 0.55)
        elif self.category == "PURGE":
            # White-hot focus tracking laser
            return (0.0, self._purge_laser_y * 0.25, 0.70)
        return (0.0, 0.0, 0.90)

    # ── Master Paint Dispatcher ──────────────────────────────────────────────

    def paint(self, p: QPainter, cx: float, cy: float, r: float, w: float, h: float) -> None:
        """Render the specialized task animation on the HUD canvas."""
        if self.alpha <= 0.005 and self._completion_burst <= 0.005:
            return

        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        master_alpha = self.alpha

        # Draw specific category visualization
        cat = self.category
        if cat == "SEARCH":
            self._paint_search(p, cx, cy, r, master_alpha)
        elif cat == "PURGE":
            self._paint_purge(p, cx, cy, r, master_alpha)
        elif cat == "GHOST":
            self._paint_ghost(p, cx, cy, r, master_alpha)
        elif cat == "SWARM":
            self._paint_swarm(p, cx, cy, r, master_alpha)
        elif cat == "SENTRY":
            self._paint_sentry(p, cx, cy, r, master_alpha)
        elif cat == "MATRIX":
            self._paint_matrix(p, cx, cy, r, master_alpha)
        elif cat == "CODE":
            self._paint_code(p, cx, cy, r, w, h, master_alpha)
        elif cat == "SONIC":
            self._paint_sonic(p, cx, cy, r, master_alpha)
        elif cat == "GENERIC":
            self._paint_generic(p, cx, cy, r, master_alpha)

        # Draw HUD Task Telemetry Banner
        self._paint_task_banner(p, cx, cy, r, w, master_alpha)

        # Draw Task Complete Burst if active
        if self._completion_burst > 0.01:
            self._paint_completion_burst(p, cx, cy, r, self._completion_burst)

        p.restore()

    # ── Category 1: SEARCH / HUNT ────────────────────────────────────────────

    def _paint_search(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        col_cyan = QColor(0, 235, 255, int(220 * alpha))
        col_cyan_dim = QColor(0, 180, 220, int(90 * alpha))
        col_red = QColor(255, 60, 50, int(230 * alpha))

        # 1. Concentric radar range rings
        p.setBrush(Qt.BrushStyle.NoBrush)
        for factor, label in [(0.35, "0.4K"), (0.65, "1.2K"), (0.95, "3.8K"), (1.25, "10K")]:
            rr = r * factor
            p.setPen(QPen(col_cyan_dim, 1.0, Qt.PenStyle.DashLine))
            p.drawEllipse(QPointF(cx, cy), rr, rr)
            p.setFont(QFont("Consolas", 7))
            p.setPen(QPen(QColor(0, 220, 255, int(140 * alpha)), 1.0))
            p.drawText(QRectF(cx + rr - 28, cy - 12, 56, 12), Qt.AlignmentFlag.AlignRight, label)

        # 2. Sweeping Radar Beam (with pie gradient tail)
        sweep_len = r * 1.3
        p.save()
        p.translate(cx, cy)
        p.rotate(math.degrees(self._radar_angle))

        # Radar needle
        p.setPen(QPen(col_cyan, 1.8))
        p.drawLine(QLineF(0, 0, sweep_len, 0))

        # Trailing gradient sector
        path_tail = QPainterPath()
        path_tail.moveTo(0, 0)
        tail_deg = 35.0
        path_tail.arcTo(QRectF(-sweep_len, -sweep_len, sweep_len * 2, sweep_len * 2), 0.0, -tail_deg)
        path_tail.closeSubpath()

        g_tail = QRadialGradient(0, 0, sweep_len)
        g_tail.setColorAt(0.0, QColor(0, 240, 255, int(120 * alpha)))
        g_tail.setColorAt(0.7, QColor(0, 180, 255, int(45 * alpha)))
        g_tail.setColorAt(1.0, QColor(0, 120, 255, 0))
        p.setBrush(QBrush(g_tail))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path_tail)
        p.restore()

        # 3. Radar Target Blips & IP Telemetry
        for b in self._radar_blips:
            bx = cx + math.cos(b["angle"]) * (r * b["dist"])
            by = cy + math.sin(b["angle"]) * (r * b["dist"])
            b_alpha = int(255 * alpha * b["life"])
            p.setBrush(QBrush(QColor(255, 70, 60, b_alpha)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(bx, by), 3.0, 3.0)

            # Target Lock Brackets around blip
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(0, 240, 255, b_alpha), 1.0))
            sz = 6.0
            p.drawRect(QRectF(bx - sz, by - sz, sz * 2, sz * 2))

            # IP label
            p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
            p.setPen(QPen(QColor(220, 240, 255, b_alpha), 1.0))
            p.drawText(QRectF(bx + 8, by - 6, 90, 12), Qt.AlignmentFlag.AlignLeft, f"TARGET // {b['ip']}")

    # ── Category 2: PURGE / INCINERATE ───────────────────────────────────────

    def _paint_purge(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        col_red = QColor(255, 45, 40, int(230 * alpha))
        col_orange = QColor(255, 140, 30, int(200 * alpha))

        # 1. Scanning Laser Beam Line
        laser_y = cy + self._purge_laser_y * r * 1.15
        beam_w = r * 1.35
        p.save()
        g_laser = QLinearGradient(cx - beam_w, laser_y, cx + beam_w, laser_y)
        g_laser.setColorAt(0.00, QColor(255, 40, 40, 0))
        g_laser.setColorAt(0.15, QColor(255, 60, 40, int(180 * alpha)))
        g_laser.setColorAt(0.50, QColor(255, 255, 255, int(255 * alpha)))
        g_laser.setColorAt(0.85, QColor(255, 60, 40, int(180 * alpha)))
        g_laser.setColorAt(1.00, QColor(255, 40, 40, 0))

        p.setPen(QPen(QBrush(g_laser), 2.2))
        p.drawLine(QLineF(cx - beam_w, laser_y, cx + beam_w, laser_y))

        # Diffused glow ribbon around laser
        g_glow = QLinearGradient(cx, laser_y - 12, cx, laser_y + 12)
        g_glow.setColorAt(0.0, QColor(255, 40, 30, 0))
        g_glow.setColorAt(0.5, QColor(255, 70, 40, int(90 * alpha)))
        g_glow.setColorAt(1.0, QColor(255, 40, 30, 0))
        p.setBrush(QBrush(g_glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(QRectF(cx - beam_w, laser_y - 12, beam_w * 2, 24))
        p.restore()

        # 2. Falling Disintegration Embers
        for pt in self._purge_particles:
            px = cx + pt["x"] * r
            py = cy + pt["y"] * r
            p_alpha = int(240 * alpha * pt["life"])
            c = QColor(pt["color"].red(), pt["color"].green(), pt["color"].blue(), p_alpha)
            p.setBrush(QBrush(c))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(px, py), pt["sz"], pt["sz"])

        # 3. Lateral Sector Clean Grid (left & right bars)
        for side in (-1, 1):
            sx = cx + side * (r * 1.22)
            num_blocks = 12
            for i in range(num_blocks):
                by = cy - r * 0.75 + i * (r * 1.5 / num_blocks)
                is_purged = (by < laser_y)
                if is_purged:
                    b_col = QColor(0, 240, 180, int(120 * alpha))  # Clean / optimized
                else:
                    b_col = QColor(255, 50, 40, int(190 * alpha))   # Cluttered / corrupt
                p.setBrush(QBrush(b_col))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(QRectF(sx - 8, by, 16, 5), 1.0, 1.0)

    # ── Category 3: GHOST / OVERRIDE ─────────────────────────────────────────

    def _paint_ghost(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        col_green = QColor(0, 255, 160, int(220 * alpha))
        col_glow = QColor(0, 255, 180, int(60 * alpha))

        # 1. Motion Trail Ribbon
        if len(self._ghost_trail) > 1:
            for i in range(len(self._ghost_trail) - 1):
                pt1 = self._ghost_trail[i]
                pt2 = self._ghost_trail[i + 1]
                t_alpha = int(180 * alpha * (i / len(self._ghost_trail)))
                p.setPen(QPen(QColor(0, 255, 170, t_alpha), 1.6))
                p.drawLine(QPointF(cx + pt1.x() * r, cy + pt1.y() * r),
                           QPointF(cx + pt2.x() * r, cy + pt2.y() * r))

        # 2. Click Shockwave Ripples
        for rip in self._ghost_ripples:
            r_alpha = int(220 * alpha * rip["life"])
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(0, 255, 200, r_alpha), 1.5))
            r_cx = cx + rip["pt"].x() * r
            r_cy = cy + rip["pt"].y() * r
            p.drawEllipse(QPointF(r_cx, r_cy), rip["radius"], rip["radius"])

        # 3. Autonomous Crosshair Reticle at Current Cursor Point
        gx = cx + self._ghost_cursor.x() * r
        gy = cy + self._ghost_cursor.y() * r

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(col_green, 1.8))
        # Outer reticle brackets
        sz = 14.0
        p.drawArc(QRectF(gx - sz, gy - sz, sz * 2, sz * 2), 30 * 16, 60 * 16)
        p.drawArc(QRectF(gx - sz, gy - sz, sz * 2, sz * 2), 120 * 16, 60 * 16)
        p.drawArc(QRectF(gx - sz, gy - sz, sz * 2, sz * 2), 210 * 16, 60 * 16)
        p.drawArc(QRectF(gx - sz, gy - sz, sz * 2, sz * 2), 300 * 16, 60 * 16)

        # Crosshair lines
        p.drawLine(QLineF(gx - sz - 4, gy, gx - 4, gy))
        p.drawLine(QLineF(gx + 4, gy, gx + sz + 4, gy))
        p.drawLine(QLineF(gx, gy - sz - 4, gx, gy - 4))
        p.drawLine(QLineF(gx, gy + 4, gx, gy + sz + 4))

        # Center dot
        p.setBrush(QBrush(QColor(255, 255, 255, int(240 * alpha))))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(gx, gy), 2.2, 2.2)

        # Coordinate label
        p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
        p.setPen(QPen(QColor(0, 255, 170, int(190 * alpha)), 1.0))
        p.drawText(QRectF(gx + sz + 6, gy - 7, 100, 14), Qt.AlignmentFlag.AlignLeft,
                   f"GHOST_X: {int(gx)} Y: {int(gy)}")

    # ── Category 4: SWARM / DRONES ───────────────────────────────────────────

    def _paint_swarm(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        col_gold = QColor(255, 190, 40, int(230 * alpha))
        col_red = QColor(255, 50, 40, int(210 * alpha))

        # 1. Pulsing Hexagonal Hive Grid behind head
        hex_r = r * 1.3
        p.save()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 140, 20, int(60 * alpha)), 1.0, Qt.PenStyle.DashLine))
        num_sides = 6
        hex_pts = []
        for i in range(num_sides):
            ang = (i / num_sides) * math.pi * 2 + (self.t * 0.2)
            hex_pts.append(QPointF(cx + math.cos(ang) * hex_r, cy + math.sin(ang) * hex_r))
        hex_poly = QPolygonF(hex_pts)
        p.drawPolygon(hex_poly)
        p.restore()

        # 2. Orbiting Sub-Ultron Drones
        for d in self._drones:
            ang = d["angle"]
            dx = cx + math.cos(ang) * (r * d["rx"])
            dy = cy + math.sin(ang) * (r * d["ry"]) + math.sin(ang) * (r * d["tilt"])

            # Telemetry laser link from Ultron's core to Drone
            p.setPen(QPen(QColor(255, 90, 40, int(75 * alpha)), 0.9, Qt.PenStyle.DotLine))
            p.drawLine(QLineF(cx, cy - r * 0.15, dx, dy))

            # Draw Stealth Drone Chevron Glyph
            p.save()
            p.translate(dx, dy)
            flight_ang = math.degrees(ang + math.pi / 2.0)
            p.rotate(flight_ang)

            path_drone = QPainterPath()
            path_drone.moveTo(0, -9)
            path_drone.lineTo(7, 7)
            path_drone.lineTo(0, 3)
            path_drone.lineTo(-7, 7)
            path_drone.closeSubpath()

            p.setBrush(QBrush(QColor(30, 36, 48, int(240 * alpha))))
            p.setPen(QPen(col_gold, 1.4))
            p.drawPath(path_drone)

            # Glowing drone thruster
            p.setBrush(QBrush(QColor(255, 70, 40, int(240 * alpha))))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(0, 3), 2.0, 2.0)
            p.restore()

            # Drone label
            p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
            p.setPen(QPen(QColor(255, 210, 100, int(190 * alpha)), 1.0))
            p.drawText(QRectF(dx + 10, dy - 6, 60, 12), Qt.AlignmentFlag.AlignLeft, d["label"])

    # ── Category 5: SENTRY / DEFENSE ─────────────────────────────────────────

    def _paint_sentry(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        col_crimson = QColor(255, 30, 40, int(230 * alpha))
        col_red_dim = QColor(180, 20, 30, int(70 * alpha))

        # 1. 360° Tactical Sonar Sweep Line
        p.save()
        p.translate(cx, cy)
        p.rotate(math.degrees(self._sentry_scan))
        sonar_r = r * 1.35
        p.setPen(QPen(col_crimson, 1.8))
        p.drawLine(QLineF(0, 0, sonar_r, 0))

        # Sonar sweep sector gradient
        path_sonar = QPainterPath()
        path_sonar.moveTo(0, 0)
        path_sonar.arcTo(QRectF(-sonar_r, -sonar_r, sonar_r * 2, sonar_r * 2), 0.0, -45.0)
        path_sonar.closeSubpath()
        g_sonar = QRadialGradient(0, 0, sonar_r)
        g_sonar.setColorAt(0.0, QColor(255, 40, 40, int(110 * alpha)))
        g_sonar.setColorAt(0.8, QColor(200, 20, 30, int(30 * alpha)))
        g_sonar.setColorAt(1.0, QColor(100, 0, 0, 0))
        p.setBrush(QBrush(g_sonar))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path_sonar)
        p.restore()

        # 2. Oscillating Laser Tripwire
        trip_y = cy + math.sin(self.t * 3.5) * (r * 0.8)
        p.setPen(QPen(QColor(255, 40, 50, int(190 * alpha)), 1.2, Qt.PenStyle.DashDotLine))
        p.drawLine(QLineF(cx - r * 1.3, trip_y, cx + r * 1.3, trip_y))

        # 3. Heavy Angular Tactical Combat Corner Brackets
        ret_sz = r * 1.25
        p.setPen(QPen(col_crimson, 2.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        arm = 24.0

        # Top-left
        p.drawLine(QLineF(cx - ret_sz, cy - ret_sz, cx - ret_sz + arm, cy - ret_sz))
        p.drawLine(QLineF(cx - ret_sz, cy - ret_sz, cx - ret_sz, cy - ret_sz + arm))
        # Top-right
        p.drawLine(QLineF(cx + ret_sz, cy - ret_sz, cx + ret_sz - arm, cy - ret_sz))
        p.drawLine(QLineF(cx + ret_sz, cy - ret_sz, cx + ret_sz, cy - ret_sz + arm))
        # Bottom-left
        p.drawLine(QLineF(cx - ret_sz, cy + ret_sz, cx - ret_sz + arm, cy + ret_sz))
        p.drawLine(QLineF(cx - ret_sz, cy + ret_sz, cx - ret_sz, cy + ret_sz - arm))
        # Bottom-right
        p.drawLine(QLineF(cx + ret_sz, cy + ret_sz, cx + ret_sz - arm, cy + ret_sz))
        p.drawLine(QLineF(cx + ret_sz, cy + ret_sz, cx + ret_sz, cy + ret_sz - arm))

    # ── Category 6: MATRIX / SYSTEM ──────────────────────────────────────────

    def _paint_matrix(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        col_gold = QColor(255, 200, 50, int(220 * alpha))
        col_amber = QColor(255, 140, 20, int(150 * alpha))

        # 1. Multi-Thread CPU Frequency Equalizer Bars (16 threads radiating around head)
        num_threads = 16
        for i in range(num_threads):
            ang = (i / num_threads) * math.pi * 2
            load = 0.35 + 0.55 * (0.5 + 0.5 * math.sin(self.t * 3.0 + i * 1.1))
            b_len = 15.0 + load * 32.0
            p1 = QPointF(cx + math.cos(ang) * (r * 1.12), cy + math.sin(ang) * (r * 1.12))
            p2 = QPointF(cx + math.cos(ang) * (r * 1.12 + b_len), cy + math.sin(ang) * (r * 1.12 + b_len))
            p.setPen(QPen(col_gold if load > 0.65 else col_amber, 2.0))
            p.drawLine(p1, p2)

        # 2. Wireframe Isometric Telemetry Cube (top-right corner)
        cube_cx = cx + r * 0.95
        cube_cy = cy - r * 0.75
        cube_sz = 26.0

        p.save()
        p.translate(cube_cx, cube_cy)
        p.setPen(QPen(QColor(0, 235, 255, int(190 * alpha)), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)

        rx = self._matrix_rot_x
        ry = self._matrix_rot_y

        # Simple 3D projection of rotating cube
        nodes = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    # Rotate Y
                    x1 = sx * math.cos(ry) + sz * math.sin(ry)
                    z1 = -sx * math.sin(ry) + sz * math.cos(ry)
                    # Rotate X
                    y2 = sy * math.cos(rx) - z1 * math.sin(rx)
                    z2 = sy * math.sin(rx) + z1 * math.cos(rx)
                    nodes.append(QPointF(x1 * cube_sz, y2 * cube_sz))

        edges = [
            (0, 1), (1, 3), (3, 2), (2, 0),
            (4, 5), (5, 7), (7, 6), (6, 4),
            (0, 4), (1, 5), (2, 6), (3, 7)
        ]
        for e1, e2 in edges:
            p.drawLine(nodes[e1], nodes[e2])
        p.restore()

    # ── Category 7: CODE / COMPILER ──────────────────────────────────────────

    def _paint_code(self, p: QPainter, cx: float, cy: float, r: float, w: float, h: float, alpha: float) -> None:
        col_green = QColor(0, 255, 140, int(190 * alpha))
        col_dim = QColor(0, 180, 100, int(110 * alpha))

        # Lateral cascading hex assembly ribbons
        p.setFont(QFont("Consolas", 6))
        line_h = 13
        num_visible = int((h * 0.6) / line_h)
        offset = int(self.t * 12.0)

        # Left Column
        for i in range(num_visible):
            idx = (offset + i) % len(self._code_streams)
            txt = self._code_streams[idx]
            ly = 50 + i * line_h
            p.setPen(QPen(col_green if i % 3 == 0 else col_dim, 1.0))
            p.drawText(QRectF(14, ly, 160, line_h), Qt.AlignmentFlag.AlignLeft, txt)

        # Right Column
        for i in range(num_visible):
            idx = (offset + i + 17) % len(self._code_streams)
            txt = self._code_streams[idx]
            ly = 50 + i * line_h
            p.setPen(QPen(col_green if i % 4 == 0 else col_dim, 1.0))
            p.drawText(QRectF(w - 174, ly, 160, line_h), Qt.AlignmentFlag.AlignRight, txt)

    # ── Category 8: SONIC / HARMONICS ────────────────────────────────────────

    def _paint_sonic(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        col_purple = QColor(200, 70, 255, int(210 * alpha))
        col_blue = QColor(60, 160, 255, int(190 * alpha))

        # Concentric Sonic Shockwave Rings expanding outward
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(4):
            ring_phase = (self._sonic_phase + i * 1.5) % 6.0
            ring_r = r * 0.4 + ring_phase * (r * 0.22)
            r_alpha = int(_clamp(240 * (1.0 - ring_phase / 6.0) * alpha, 0, 255))
            p.setPen(QPen(QColor(180, 80, 255, r_alpha), 1.6))
            p.drawEllipse(QPointF(cx, cy - r * 0.1), ring_r, ring_r * 0.65)

    # ── Category 9: GENERIC DIRECTIVE OVERCLOCK ──────────────────────────────

    def _paint_generic(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        col_gold = QColor(255, 190, 40, int(220 * alpha))
        p.save()
        p.translate(cx, cy)
        # Fast rotating azimuth tick rings
        p.rotate(math.degrees(self.t * 3.5))
        p.setPen(QPen(col_gold, 1.4, Qt.PenStyle.DashDotLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(-r * 1.25, -r * 1.25, r * 2.5, r * 2.5))
        p.restore()

    # ── Telemetry Banner & Completion Burst ──────────────────────────────────

    def _paint_task_banner(self, p: QPainter, cx: float, cy: float, r: float, w: float, alpha: float) -> None:
        banner_y = 22.0
        p.save()

        # Banner background strip
        b_w = min(w * 0.82, 480.0)
        bx = cx - b_w / 2.0
        g_strip = QLinearGradient(bx, banner_y, bx + b_w, banner_y)
        g_strip.setColorAt(0.00, QColor(8, 12, 18, 0))
        g_strip.setColorAt(0.20, QColor(14, 18, 28, int(210 * alpha)))
        g_strip.setColorAt(0.80, QColor(14, 18, 28, int(210 * alpha)))
        g_strip.setColorAt(1.00, QColor(8, 12, 18, 0))
        p.setBrush(QBrush(g_strip))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(bx, banner_y, b_w, 22), 3.0, 3.0)

        # Glowing accent border line
        p.setPen(QPen(QColor(255, 50, 40, int(220 * alpha)), 1.2))
        p.drawLine(QLineF(bx + 20, banner_y + 22, bx + b_w - 20, banner_y + 22))

        # Banner Title
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        p.setPen(QPen(QColor(255, 220, 160, int(250 * alpha)), 1.0))
        p.drawText(QRectF(bx, banner_y + 2, b_w, 18), Qt.AlignmentFlag.AlignCenter, f"◈ {self.label} ◈")
        p.restore()

    def _paint_completion_burst(self, p: QPainter, cx: float, cy: float, r: float, burst: float) -> None:
        """Draw an expanding white/gold flash ring confirming task completion."""
        b_r = r * 0.5 + (1.0 - burst) * (r * 1.1)
        b_alpha = int(240 * burst)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(0, 255, 180, b_alpha), 2.5))
        p.drawEllipse(QPointF(cx, cy), b_r, b_r)

        # "[ ✓ TASK COMPLETE ]" flourish
        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        p.setPen(QPen(QColor(0, 255, 180, b_alpha), 1.0))
        p.drawText(QRectF(cx - 150, cy - r * 0.8, 300, 20), Qt.AlignmentFlag.AlignCenter, "[ ✓ DIRECTIVE COMPLETED ]")

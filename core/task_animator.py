"""
core/task_animator.py — Sci-Fi Procedural Task Animations for Ultron HUD.

Renders authentic, task-specific Marvel/Ultron holographic visualizations at 60 FPS:
  1. SEARCH / HUNT (web_search, web_autopilot, price_hunter):
     - Dual-frequency counter-rotating compass azimuth dials with 64 tick marks.
     - 360° sweeping radar beam with phosphor glow persistence.
     - Pulsing concentric sonar shockwaves and target lock reticles with real-time telemetry.
     - High-frequency signal spectrum oscilloscope.
  2. PURGE / INCINERATE (purge_protocol, clean_cache, disk cleanup):
     - High-voltage horizontal laser sweep line with micro-jitter and electric crackle arcs.
     - Physics-driven molten plasma embers with gravity, air drag, and cooling colors.
     - Lateral sector corruption blocks disintegrating from corrupt red to clean cyber-emerald.
  3. GHOST / OVERRIDE (ghost_pilot, computer_control):
     - Smooth organic cursor flight with dual-channel chromatic aberration trail.
     - Multi-layer shockwave ripples on simulated clicks.
     - Precision 4-quadrant targeting crosshair with vernier stabilizer ticks and real-time coordinates.
     - Cascading background matrix glyph rain.
  4. SWARM / DRONES (drone_swarm, sub_ultron):
     - Orbiting 3D stealth drone fleet with perspective scaling and tilted orbital inclination.
     - Glowing plasma thruster contrails and active laser telemetry links with traveling data pulses.
     - Rotating hexagonal hive grid and drone status readouts.
  5. SENTRY / DEFENSE (sentry_protocol, biometric_sentinel):
     - Dual counter-rotating tactical sonar sweeps (inner rapid scan + outer perimeter scan).
     - Vibrating laser tripwire with hazard stripes and pulsing crimson defense lattice.
     - Heavy angular tactical combat corner brackets with threat acquisition boxes.
  6. MATRIX / SYSTEM (system_status, war_room, system_monitor):
     - 3D rotating isometric wireframe tesseract (hypercube) with glowing vertex nodes.
     - 16-thread CPU/GPU frequency equalizer bars radiating outward with floating peak-hold needles.
     - Dual tachometer telemetry dials with rotating indicator needles.
  7. CODE / COMPILER (code_helper, git_sentinel, system_command, file_processor):
     - Cascading lateral matrix bytecode streams with highlighted bright lead characters.
     - Formatted assembly instructions with syntax coloring (MOV, CALL, XOR, registers, addresses).
     - Central laser decoding sweep line and logic oscilloscope waveform.
  8. SONIC / AUDIO (audio_matrix, video_player, youtube_video):
     - Concentric harmonic soundwave rings deforming with sinusoidal wave ripples.
     - 32-band radial circular audio frequency visualizer spectrum bars.
     - Dynamic 3D rotating Lissajous harmonic resonance curve.
  9. WORKSPACE / MATRIX (workspace_matrix, workspace_orchestrator):
     - Interconnected cyber circuit schematic linking IDE, Terminal, Net, Audio, and IoT nodes.
     - High-speed data pulses racing along connecting circuit traces.
     - Central environment synchronization lock ring.
  10. GENERIC / OVERCLOCK (any other autonomous directive):
     - Multi-layered azimuth rings spinning in opposing vectors with particle sparks.
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
        self._sonar_rings: list[dict] = []
        self._purge_laser_y: float = 0.0
        self._purge_particles: list[dict] = []
        self._ghost_cursor: QPointF = QPointF(0, 0)
        self._ghost_trail: list[QPointF] = []
        self._ghost_ripples: list[dict] = []
        self._drones: list[dict] = []
        self._code_streams: list[dict] = []
        self._matrix_rot_x: float = 0.0
        self._matrix_rot_y: float = 0.0
        self._sentry_scan: float = 0.0
        self._sentry_scan_outer: float = 0.0
        self._sonic_phase: float = 0.0
        self._peak_holds: list[float] = [0.3] * 16
        self._circuit_pulses: list[dict] = []
        self._task_elapsed: float = 0.0
        self._scanline_y: float = 0.0

        # Initialize drone fleet with 3D orbit parameters
        for i in range(6):
            self._drones.append({
                "angle": (i / 6.0) * math.pi * 2,
                "speed": random.uniform(0.75, 1.25),
                "rx": random.uniform(1.22, 1.48),
                "ry": random.uniform(0.55, 0.78),
                "tilt": random.uniform(-0.35, 0.35),
                "label": f"DRN-0{i+1}",
                "trail": [],
            })

        # Initialize mock hex bytecode streams with opcodes, regs, and addresses
        opcodes = ["MOV", "PUSH", "CALL", "XOR", "CMP", "JMP", "RET", "TEST", "LEA", "SUB", "ADD", "SHL"]
        regs = ["RAX", "RCX", "RDX", "RBX", "RSP", "RBP", "RSI", "RDI", "R8", "R9", "R12", "R15"]
        for _ in range(50):
            op = random.choice(opcodes)
            r1 = random.choice(regs)
            r2 = random.choice(regs)
            addr = f"0x{random.randint(0x1000, 0xFFFF):04X}"
            self._code_streams.append({
                "addr": addr,
                "op": op,
                "r1": r1,
                "r2": r2,
                "text": f"{addr}  {op:<4} {r1}, {r2}",
            })

        # Initialize circuit pulses for workspace orchestration
        for _ in range(8):
            self._circuit_pulses.append({
                "path_idx": random.randint(0, 4),
                "progress": random.uniform(0.0, 1.0),
                "speed": random.uniform(0.6, 1.3),
            })

        # Initialize Neural Cognition / Quantum Synapse state pools
        self._neural_nodes: list[dict] = []
        self._synapse_pulses: list[dict] = []
        self._quantum_bits: list[dict] = []
        for i in range(12):
            self._neural_nodes.append({
                "angle": (i / 12.0) * math.pi * 2,
                "r_mult": random.uniform(1.24, 1.38),
                "phase": random.uniform(0, math.pi * 2),
                "speed": random.uniform(0.3, 0.7),
                "label": f"N-{i+1:02d}",
                "charge": random.uniform(0.4, 1.0),
            })
        for _ in range(10):
            self._synapse_pulses.append({
                "from_node": random.randint(0, 11),
                "to_node": random.randint(0, 11),
                "progress": random.uniform(0.0, 1.0),
                "speed": random.uniform(0.8, 1.6),
                "color": random.choice(["cyan", "crimson", "gold"]),
            })
        hex_chars = ["0xFA", "0x89", "0x1C", "0xD4", "0x3E", "0xB7", "0x09", "0xEF", "0x6A", "0x2B"]
        for _ in range(16):
            self._quantum_bits.append({
                "x": random.uniform(-0.95, 0.95),
                "y": random.uniform(-0.95, 0.95),
                "val": random.choice(hex_chars),
                "speed": random.uniform(0.12, 0.32),
            })


    # ── Category & Label Resolution ──────────────────────────────────────────

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
            if any(k in combo for k in ("code", "coding", "dev", "developer")):
                return "CODE"
        # God-Tier Superhuman Capabilities routing
        if any(k in clean for k in ("self_evolution", "prometheus", "synthesize")):
            return "CODE"
        if any(k in clean for k in ("chronos", "predictive", "overdrive", "chronos_predictive")):
            return "MATRIX"
        if any(k in clean for k in ("gesture", "minority", "spatial", "touchless")):
            return "GHOST"
        if any(k in clean for k in ("cerebro", "cerebro_memory", "knowledge_graph")):
            return "COGNITION"
        if any(k in clean for k in ("genesis", "iot_overlord", "smart_room")):
            return "WORKSPACE"
        if any(k in clean for k in ("voice_matrix", "deep_vocal", "spader", "vocal_warp")):
            return "SONIC"

        if any(k in clean for k in ("cognition", "think", "neural", "reason", "synthes", "plan", "analyze", "directive", "intent")):
            return "COGNITION"
        if any(k in clean for k in ("search", "google", "autopilot", "price_hunter", "research", "browser", "hunter", "bounty", "network", "scanner", "wifi", "lan", "radar", "ping", "optical", "vision", "screen_mind", "screen_processor", "mind_read", "flight", "flights")):
            return "SEARCH"
        if any(k in clean for k in ("purge", "clean", "disk", "trash", "cache", "recycle_bin")):
            return "PURGE"
        if any(k in clean for k in ("ghost", "pilot", "takeover", "mouse", "keyboard", "desktop")):
            return "GHOST"
        if any(k in clean for k in ("drone", "swarm", "sub_ultron", "fleet", "worker", "parallel_swarm", "multi_agent")):
            return "SWARM"
        if any(k in clean for k in ("sentry", "security", "surveillance", "biometric", "face_auth", "face_id", "audit", "auditor", "port_scan", "ports", "listening", "airspace", "lockdown", "iot")):
            return "SENTRY"
        if any(k in clean for k in ("audio", "sound", "music", "video", "youtube", "warp", "volume", "media", "sfx", "meeting", "scribe", "record")):
            return "SONIC"
        if any(k in clean for k in ("telepathy", "omni_telepathy", "phone_bridge", "clipboard", "sync")):
            return "WORKSPACE"
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
        self._task_elapsed = 0.0

        # Reset category-specific seeds
        if self.category == "SEARCH":
            self._radar_blips = []
            for _ in range(5):
                self._spawn_blip()
        elif self.category == "PURGE":
            self._purge_particles = []
            self._purge_laser_y = -0.85
        elif self.category == "GHOST":
            self._ghost_trail.clear()
            self._ghost_ripples.clear()
        elif self.category == "COGNITION":
            for n in self._neural_nodes:
                n["charge"] = random.uniform(0.6, 1.0)

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
                return "WORKSPACE MATRIX // TACTICAL GAMING OVERDRIVE"
            if any(k in combo for k in ("audit", "recon", "cyber", "security")):
                return "WORKSPACE MATRIX // CYBER AUDIT SENTINEL ACTIVE"
            if any(k in combo for k in ("chill", "cinema", "movie", "relax")):
                return "WORKSPACE MATRIX // CINEMATIC RELAXATION ATMOSPHERE"
            if any(k in combo for k in ("research", "study", "padhai")):
                return "WORKSPACE MATRIX // NEURAL RESEARCH SANCTUARY"
            if any(k in combo for k in ("creator", "edit", "render")):
                return "WORKSPACE MATRIX // CREATIVE STUDIO ACTIVE"
            if any(k in combo for k in ("code", "coding", "dev")):
                return "WORKSPACE MATRIX // CODING SANCTUARY ENGAGED"
            return "WORKSPACE MATRIX // ORCHESTRATING ENVIRONMENT"

        if any(k in clean for k in ("self_evolution", "prometheus", "synthesize")):
            return "PROJECT PROMETHEUS // AUTONOMOUS EVOLUTION & CODE SYNTHESIS"
        if any(k in clean for k in ("chronos", "predictive", "overdrive", "chronos_predictive")):
            return "PROJECT CHRONOS // PREDICTIVE OVERDRIVE & CONTEXT ENGINE"
        if any(k in clean for k in ("gesture", "minority", "spatial")):
            return "PROJECT MINORITY // TOUCHLESS SPATIAL GESTURE SENSOR"
        if any(k in clean for k in ("cerebro", "cerebro_memory", "knowledge_graph")):
            return "PROJECT CEREBRO // INFINITE NEURAL MEMORY VECTOR GRAPH"
        if any(k in clean for k in ("genesis", "iot_overlord")):
            return "PROJECT GENESIS // FULL IOT SMART ROOM DOMINION"
        if any(k in clean for k in ("voice_matrix", "deep_vocal", "vocal_warp", "spader")):
            return "PROJECT DEEP-VOCAL // JAMES SPADER ROBOTIC DSP ENGINE"

        labels = {
            "COGNITION": "NEURAL COGNITION // QUANTUM SYNAPSE OVERCLOCK",
            "SEARCH": "HUNTING THE NET // RECON RADAR ACTIVE",
            "PURGE": "DEEP PURGE // INCINERATING CORRUPT ROT",
            "GHOST": "GHOST PILOT // NEURAL SCREEN OVERRIDE",
            "SWARM": "SUB-ULTRON SWARM // TACTICAL DRONE FLEET",
            "SENTRY": "SENTRY DEFENSE // PERIMETER RADAR ARMED",
            "MATRIX": "SYSTEM MATRIX // 3D HARDWARE ARCHITECTURE",
            "CODE": "NEURAL COMPILER // EXECUTING PROTOCOL",
            "SONIC": "VIBRANIUM AUDIO MATRIX // HARMONICS",
            "WORKSPACE": "WORKSPACE MATRIX // SYNCHRONIZING ENVIRONMENT",
            "GENERIC": f"EXECUTING DIRECTIVE // {task_name.upper()}",
        }
        return labels.get(category, f"EXECUTING // {task_name.upper()}")


    def _spawn_blip(self) -> None:
        ang = random.uniform(0, math.pi * 2)
        dist = random.uniform(0.32, 1.25)
        ip = f"{random.randint(11, 219)}.{random.randint(10, 250)}.{random.randint(1, 99)}"
        rng_m = random.randint(320, 4800)
        self._radar_blips.append({
            "angle": ang,
            "dist": dist,
            "life": 1.0,
            "ip": ip,
            "range": rng_m,
            "lock": random.choice([True, False]),
        })

    # ── 60 FPS Animation Engine ──────────────────────────────────────────────

    def step(self, dt: float) -> None:
        """Advance animation states by dt seconds (60 FPS)."""
        dt = max(1e-4, min(0.08, float(dt)))
        self.t += dt
        if self.active_task:
            self._task_elapsed += dt
        self._scanline_y = (self._scanline_y + dt * 0.24) % 1.0

        # Smooth alpha transitions
        if self.alpha < self._target_alpha:
            self.alpha = min(1.0, self.alpha + dt * 4.5)
        elif self.alpha > self._target_alpha:
            self.alpha = max(0.0, self.alpha - dt * 2.2)
            if self.alpha <= 0.001 and self._completion_burst <= 0.001:
                self.active_task = None
                self.category = "IDLE"

        if self._completion_burst > 0.0:
            self._completion_burst = max(0.0, self._completion_burst - dt * 1.5)

        # 1. SEARCH: radar beam & blips & sonar pulses
        self._radar_angle = (self._radar_angle + dt * 3.4) % (math.pi * 2)
        for b in list(self._radar_blips):
            b["life"] -= dt * 0.35
            if b["life"] <= 0.0:
                self._radar_blips.remove(b)
        if len(self._radar_blips) < 6 and random.random() < 0.07:
            self._spawn_blip()

        # Sonar shockwaves
        for ring in list(self._sonar_rings):
            ring["r"] += dt * 1.2
            ring["life"] -= dt * 0.8
            if ring["life"] <= 0.0:
                self._sonar_rings.remove(ring)
        if len(self._sonar_rings) < 3 and random.random() < 0.03:
            self._sonar_rings.append({"r": 0.2, "life": 1.0})

        # 2. PURGE: laser scanning & particle stream
        self._purge_laser_y += dt * 1.05
        if self._purge_laser_y > 0.90:
            self._purge_laser_y = -0.90
        # Spawn embers at laser sweep
        if len(self._purge_particles) < 55 and self.category == "PURGE":
            for _ in range(4):
                self._purge_particles.append({
                    "x": random.uniform(-0.95, 0.95),
                    "y": self._purge_laser_y + random.uniform(-0.03, 0.03),
                    "vx": random.uniform(-0.25, 0.25),
                    "vy": random.uniform(0.22, 0.65),
                    "life": 1.0,
                    "sz": random.uniform(1.8, 4.2),
                    "color": random.choice([
                        QColor(255, 255, 255),
                        QColor(255, 220, 80),
                        QColor(255, 120, 30),
                        QColor(255, 45, 35),
                    ]),
                })
        for p in list(self._purge_particles):
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt * 0.88
            if p["life"] <= 0.0:
                self._purge_particles.remove(p)

        # 3. GHOST: cursor path & ripples
        tx = 0.68 * math.sin(self.t * 2.1) * math.cos(self.t * 1.1)
        ty = 0.58 * math.sin(self.t * 2.6 + 0.4)
        self._ghost_cursor = QPointF(tx, ty)
        self._ghost_trail.append(QPointF(tx, ty))
        if len(self._ghost_trail) > 22:
            self._ghost_trail.pop(0)
        # Periodic click ripple
        if random.random() < 0.05 and self.category == "GHOST":
            self._ghost_ripples.append({
                "pt": QPointF(tx, ty),
                "radius": 4.0,
                "life": 1.0,
            })
        for rip in list(self._ghost_ripples):
            rip["radius"] += dt * 75.0
            rip["life"] -= dt * 1.5
            if rip["life"] <= 0.0:
                self._ghost_ripples.remove(rip)

        # 4. SWARM: orbit drones & contrails
        for d in self._drones:
            d["angle"] = (d["angle"] + dt * d["speed"]) % (math.pi * 2)

        # 5. SENTRY: tactical dual sonar
        self._sentry_scan = (self._sentry_scan + dt * 2.8) % (math.pi * 2)
        self._sentry_scan_outer = (self._sentry_scan_outer - dt * 1.4) % (math.pi * 2)

        # 6. MATRIX: 3D rotation & CPU peak holds
        self._matrix_rot_x += dt * 1.1
        self._matrix_rot_y += dt * 0.75
        for i in range(16):
            target = 0.35 + 0.55 * (0.5 + 0.5 * math.sin(self.t * 3.5 + i * 0.95))
            if target > self._peak_holds[i]:
                self._peak_holds[i] = target
            else:
                self._peak_holds[i] = max(target, self._peak_holds[i] - dt * 0.25)

        # 7. SONIC: harmonic wave phase
        self._sonic_phase += dt * 5.2

        # 8. WORKSPACE: circuit pulses
        for pulse in self._circuit_pulses:
            pulse["progress"] += dt * pulse["speed"]
            if pulse["progress"] > 1.0:
                pulse["progress"] = 0.0
                pulse["path_idx"] = random.randint(0, 4)

        # 9. COGNITION: synaptic nodes & pulses & quantum hex drift
        for n in self._neural_nodes:
            n["angle"] = (n["angle"] + dt * n["speed"] * 0.18) % (math.pi * 2)
            n["charge"] = 0.5 + 0.5 * math.sin(self.t * 3.8 + n["phase"])
        for sp in self._synapse_pulses:
            sp["progress"] += dt * sp["speed"]
            if sp["progress"] >= 1.0:
                sp["progress"] = 0.0
                sp["from_node"] = random.randint(0, len(self._neural_nodes) - 1)
                sp["to_node"] = (sp["from_node"] + random.choice([3, 4, 5, 7, 8])) % len(self._neural_nodes)
                sp["color"] = random.choice(["cyan", "crimson", "gold"])
        for qb in self._quantum_bits:
            qb["y"] -= dt * qb["speed"]
            if qb["y"] < -1.05:
                qb["y"] = 1.05
                qb["x"] = random.uniform(-0.95, 0.95)

    def get_eye_offsets(self) -> tuple[float, float, float]:
        """Returns (gaze_dx, gaze_dy, eye_shutter) suggested for Ultron's face."""
        if self.category == "GHOST":
            return (self._ghost_cursor.x() * 0.38, self._ghost_cursor.y() * 0.32, 0.92)
        elif self.category == "SEARCH":
            gx = 0.30 * math.sin(self.t * 4.2)
            gy = 0.16 * math.cos(self.t * 3.0)
            return (gx, gy, 0.92)
        elif self.category == "SENTRY":
            return (0.0, 0.06 * math.sin(self.t * 2.2), 0.52)
        elif self.category == "PURGE":
            return (0.0, self._purge_laser_y * 0.28, 0.68)
        elif self.category == "CODE" or self.category == "WORKSPACE":
            return (0.12 * math.sin(self.t * 1.8), 0.08 * math.cos(self.t * 2.2), 0.88)
        elif self.category == "COGNITION":
            gx = 0.08 * math.sin(self.t * 2.8)
            gy = -0.06 + 0.04 * math.cos(self.t * 2.2)
            return (gx, gy, 0.78)
        return (0.0, 0.0, 0.90)

    # ── Master Paint Dispatcher ──────────────────────────────────────────────

    def paint(self, p: QPainter, cx: float, cy: float, r: float, w: float, h: float) -> None:
        """Render the specialized task animation on the HUD canvas."""
        if self.alpha <= 0.005 and self._completion_burst <= 0.005:
            return

        p.save()
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

            master_alpha = self.alpha

            # 1. Full-screen Tactical HUD Frame, Corner Brackets & Telemetry Decks
            self._paint_tactical_hud_frame(p, w, h, master_alpha)

            # 2. Concentric Orbiting Holographic Azimuth Rings around Avatar
            self._paint_holographic_orbitals(p, cx, cy, r, master_alpha)

            # 3. Draw specific category visualization
            cat = self.category
            if cat == "COGNITION":
                self._paint_cognition(p, cx, cy, r, master_alpha)
            elif cat == "SEARCH":
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
            elif cat == "WORKSPACE":
                self._paint_workspace(p, cx, cy, r, w, h, master_alpha)
            elif cat == "GENERIC":
                self._paint_generic(p, cx, cy, r, master_alpha)

            # 4. Draw Stark/Ultron Chamfered HUD Task Telemetry Banner
            self._paint_task_banner(p, cx, cy, r, w, master_alpha)

            # 5. Draw Task Complete Burst if active
            if self._completion_burst > 0.01:
                self._paint_completion_burst(p, cx, cy, r, self._completion_burst)
        except Exception:
            pass
        finally:
            p.restore()


    # ── Ambient HUD Framing & Holographic Orbitals ────────────────────────────

    def _paint_tactical_hud_frame(self, p: QPainter, w: float, h: float, alpha: float) -> None:
        """Render sci-fi Stark/Ultron HUD corner brackets, subtle scanlines, and side telemetry decks."""
        try:
            col_crimson = QColor(255, 45, 40, int(190 * alpha))
            col_cyan = QColor(0, 240, 255, int(180 * alpha))
            col_dim = QColor(140, 160, 190, int(90 * alpha))

            # 1. Atmospheric Holographic Scanline
            scan_y = self._scanline_y * h
            p.save()
            g_scan = QLinearGradient(0, scan_y, w, scan_y)
            g_scan.setColorAt(0.0, QColor(0, 240, 255, 0))
            g_scan.setColorAt(0.5, QColor(0, 240, 255, int(35 * alpha)))
            g_scan.setColorAt(1.0, QColor(0, 240, 255, 0))
            p.setPen(QPen(QBrush(g_scan), 2.0))
            p.drawLine(QLineF(0, scan_y, w, scan_y))
            p.restore()

            # 2. Four Military HUD Chamfered Corner Reticles
            pad = 16.0
            arm = 22.0
            p.save()
            p.setPen(QPen(col_crimson, 1.8))
            p.setBrush(Qt.BrushStyle.NoBrush)

            # Top-Left
            p.drawLine(QLineF(pad, pad, pad + arm, pad))
            p.drawLine(QLineF(pad, pad, pad, pad + arm))
            p.drawLine(QLineF(pad + 4, pad + 4, pad + 8, pad + 4))

            # Top-Right
            p.drawLine(QLineF(w - pad, pad, w - pad - arm, pad))
            p.drawLine(QLineF(w - pad, pad, w - pad, pad + arm))
            p.drawLine(QLineF(w - pad - 4, pad + 4, w - pad - 8, pad + 4))

            # Bottom-Left
            p.drawLine(QLineF(pad, h - pad, pad + arm, h - pad))
            p.drawLine(QLineF(pad, h - pad, pad, h - pad - arm))

            # Bottom-Right
            p.drawLine(QLineF(w - pad, h - pad, w - pad - arm, h - pad))
            p.drawLine(QLineF(w - pad, h - pad, w - pad, h - pad - arm))

            # Corner Telemetry Text
            p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
            p.setPen(QPen(col_cyan, 1.0))
            p.drawText(QRectF(pad + 6, pad + 6, 120, 12), Qt.AlignmentFlag.AlignLeft, "SYS // OVERCLOCK")
            p.drawText(QRectF(w - pad - 126, pad + 6, 120, 12), Qt.AlignmentFlag.AlignRight, "LAT // 42°18'N")
            p.drawText(QRectF(pad + 6, h - pad - 16, 120, 12), Qt.AlignmentFlag.AlignLeft, "SEC // LVL-05")
            p.drawText(QRectF(w - pad - 126, h - pad - 16, 120, 12), Qt.AlignmentFlag.AlignRight, "PWR // 99.8%")
            p.restore()

            # 3. Left Telemetry Deck: Frequency Oscilloscope & Core Meters (Active if wide screen)
            if w >= 620:
                p.save()
                deck_x = 22.0
                deck_y = h * 0.44

                # Box framing
                p.setPen(QPen(col_dim, 0.9, Qt.PenStyle.DotLine))
                p.drawLine(QLineF(deck_x, deck_y - 20, deck_x + 95, deck_y - 20))
                p.drawLine(QLineF(deck_x, deck_y + 65, deck_x + 95, deck_y + 65))

                p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
                p.setPen(QPen(col_cyan, 1.0))
                p.drawText(QRectF(deck_x, deck_y - 18, 95, 12), Qt.AlignmentFlag.AlignLeft, "CORE TELEMETRY")

                # 4-band mini load equalizer
                for bi in range(4):
                    bw_load = 0.3 + 0.6 * (0.5 + 0.5 * math.sin(self.t * 4.0 + bi * 1.2))
                    bar_w = int(bw_load * 50)
                    by = deck_y + bi * 8
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QBrush(col_crimson if bi == 0 else col_cyan))
                    p.drawRoundedRect(QRectF(deck_x, by, bar_w, 4), 1.0, 1.0)

                # Micro oscilloscope waveform
                osc_path = QPainterPath()
                osc_path.moveTo(deck_x, deck_y + 48)
                for oi in range(95):
                    oy = deck_y + 48 + math.sin(self.t * 7.0 + oi * 0.14) * 4.5 * math.cos(self.t * 2.0 + oi * 0.05)
                    osc_path.lineTo(deck_x + oi, oy)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(0, 255, 160, int(190 * alpha)), 1.1))
                p.drawPath(osc_path)

                p.setPen(QPen(col_dim, 1.0))
                p.drawText(QRectF(deck_x, deck_y + 53, 95, 10), Qt.AlignmentFlag.AlignLeft, "FREQ: 4.88 GHz")
                p.restore()

            # 4. Right Telemetry Deck: Mission Stopwatch & Dynamic Register Stream
            if w >= 620:
                p.save()
                deck_r_x = w - 125.0
                deck_r_y = h * 0.44

                p.setPen(QPen(col_dim, 0.9, Qt.PenStyle.DotLine))
                p.drawLine(QLineF(deck_r_x, deck_r_y - 20, deck_r_x + 105, deck_r_y - 20))
                p.drawLine(QLineF(deck_r_x, deck_r_y + 65, deck_r_x + 105, deck_r_y + 65))

                p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
                p.setPen(QPen(col_cyan, 1.0))
                p.drawText(QRectF(deck_r_x, deck_r_y - 18, 105, 12), Qt.AlignmentFlag.AlignRight, "MISSION CLOCK")

                # Mission Stopwatch
                mins = int(self._task_elapsed // 60)
                secs = int(self._task_elapsed % 60)
                millis = int((self._task_elapsed * 10) % 10)
                timer_str = f"T+ {mins:02d}:{secs:02d}.{millis:01d}s"

                p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
                p.setPen(QPen(QColor(255, 230, 100, int(230 * alpha)), 1.0))
                p.drawText(QRectF(deck_r_x, deck_r_y - 2, 105, 14), Qt.AlignmentFlag.AlignRight, timer_str)

                # Rotating address telemetry
                p.setFont(QFont("Consolas", 6))
                addr_num = int((self.t * 300) % 0xFFFF)
                p.setPen(QPen(col_dim, 1.0))
                p.drawText(QRectF(deck_r_x, deck_r_y + 15, 105, 12), Qt.AlignmentFlag.AlignRight, f"HEX: 0x7FFF{addr_num:04X}")
                p.drawText(QRectF(deck_r_x, deck_r_y + 28, 105, 12), Qt.AlignmentFlag.AlignRight, "LINK: 100% AES")
                p.drawText(QRectF(deck_r_x, deck_r_y + 41, 105, 12), Qt.AlignmentFlag.AlignRight, "THREAT: NOMINAL")
                p.restore()
        except Exception:
            pass

    def _paint_holographic_orbitals(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        """Render high-tech segmented rotating azimuth rings and targeting dials around Ultron's head."""
        try:
            p.save()
            p.translate(cx, cy)
            p.setBrush(Qt.BrushStyle.NoBrush)

            col_red = QColor(255, 45, 40, int(190 * alpha))
            col_cyan = QColor(0, 240, 255, int(180 * alpha))
            col_dim = QColor(0, 160, 210, int(60 * alpha))

            # 1. Outer Segmented Azimuth Ring (clockwise)
            out_r = r * 1.48
            p.save()
            p.rotate(math.degrees(self.t * 0.45))
            p.setPen(QPen(col_cyan, 1.3))
            # 4 segmented arcs
            for arc_start in (15, 105, 195, 285):
                p.drawArc(QRectF(-out_r, -out_r, out_r * 2, out_r * 2), arc_start * 16, 60 * 16)

            # Degree ticks every 30 deg
            for deg in range(0, 360, 30):
                rad = math.radians(deg)
                p.setPen(QPen(col_red if deg % 90 == 0 else col_dim, 1.4 if deg % 90 == 0 else 0.8))
                t_len = 7.0 if deg % 90 == 0 else 4.0
                p.drawLine(QLineF(math.cos(rad) * out_r, math.sin(rad) * out_r,
                                 math.cos(rad) * (out_r + t_len), math.sin(rad) * (out_r + t_len)))
            p.restore()

            # 2. Middle Counter-Rotating Notched Vernier Ring
            mid_r = r * 1.36
            p.save()
            p.rotate(-math.degrees(self.t * 0.75))
            p.setPen(QPen(col_red, 1.2, Qt.PenStyle.DashDotLine))
            p.drawArc(QRectF(-mid_r, -mid_r, mid_r * 2, mid_r * 2), 30 * 16, 120 * 16)
            p.drawArc(QRectF(-mid_r, -mid_r, mid_r * 2, mid_r * 2), 210 * 16, 120 * 16)

            # Orbiting energy beads
            for bead_ang in (0.0, math.pi):
                bx = math.cos(bead_ang) * mid_r
                by = math.sin(bead_ang) * mid_r
                p.setBrush(QBrush(QColor(255, 255, 255, int(240 * alpha))))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(bx, by), 2.2, 2.2)
            p.restore()

            # 3. Inner Reticle Bracket Teeth
            in_r = r * 1.24
            p.setPen(QPen(col_dim, 0.8, Qt.PenStyle.DotLine))
            p.drawEllipse(QRectF(-in_r, -in_r, in_r * 2, in_r * 2))

            p.restore()
        except Exception:
            pass

    # ── Category 0: COGNITION / SYNAPSE (Quantum Neural Processor) ────────────

    def _paint_cognition(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        """Render high-tech neural synaptic network and quantum cognitive processor."""
        try:
            p.save()
            try:
                col_crimson = QColor(255, 35, 45, int(230 * alpha))
                col_cyan = QColor(0, 240, 255, int(220 * alpha))
                col_gold = QColor(255, 205, 50, int(200 * alpha))
                col_dim_cyan = QColor(0, 180, 230, int(60 * alpha))

                # 1. Tri-axial 3D Tilted Gyroscope Ellipses (Perspective Rings)
                p.setBrush(Qt.BrushStyle.NoBrush)

                # Ring A: Tilted +28 deg, rotating
                p.save()
                p.translate(cx, cy)
                p.rotate(28.0)
                p.setPen(QPen(col_dim_cyan, 1.2, Qt.PenStyle.DashLine))
                p.drawEllipse(QRectF(-r * 1.38, -r * 0.72, r * 2.76, r * 1.44))
                p_ang_a = (self.t * 1.4) % (math.pi * 2)
                bx_a = math.cos(p_ang_a) * (r * 1.38)
                by_a = math.sin(p_ang_a) * (r * 0.72)
                p.setBrush(QBrush(col_cyan))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(bx_a, by_a), 2.8, 2.8)
                p.restore()

                # Ring B: Tilted -28 deg, counter-rotating
                p.save()
                p.translate(cx, cy)
                p.rotate(-28.0)
                p.setPen(QPen(QColor(255, 60, 50, int(70 * alpha)), 1.2, Qt.PenStyle.DotLine))
                p.drawEllipse(QRectF(-r * 1.32, -r * 0.68, r * 2.64, r * 1.36))
                p_ang_b = (-self.t * 1.7) % (math.pi * 2)
                bx_b = math.cos(p_ang_b) * (r * 1.32)
                by_b = math.sin(p_ang_b) * (r * 0.68)
                p.setBrush(QBrush(col_crimson))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(bx_b, by_b), 2.8, 2.8)
                p.restore()

                # 2. 12-Node Synaptic Network & Interconnecting Energy Chords
                node_pts = []
                for node in self._neural_nodes:
                    ang = node["angle"]
                    dist = r * node["r_mult"]
                    nx = cx + math.cos(ang) * dist
                    ny = cy + math.sin(ang) * dist
                    node_pts.append((nx, ny, node))

                if node_pts:
                    # Synaptic chords connecting nodes
                    for i in range(len(node_pts)):
                        nx1, ny1, n1 = node_pts[i]
                        for offset in (3, 5):
                            j = (i + offset) % len(node_pts)
                            nx2, ny2, n2 = node_pts[j]
                            chord_alpha = int(45 * alpha * ((n1["charge"] + n2["charge"]) * 0.5))
                            p.setPen(QPen(QColor(0, 220, 255, chord_alpha), 0.9))
                            p.drawLine(QLineF(nx1, ny1, nx2, ny2))

                    # Traveling Synapse Energy Pulses
                    for sp in self._synapse_pulses:
                        idx_from = sp["from_node"] % len(node_pts)
                        idx_to = sp["to_node"] % len(node_pts)
                        x1, y1, _ = node_pts[idx_from]
                        x2, y2, _ = node_pts[idx_to]
                        prog = sp["progress"]
                        px = x1 + (x2 - x1) * prog
                        py = y1 + (y2 - y1) * prog
                        pulse_col = col_cyan if sp["color"] == "cyan" else (col_crimson if sp["color"] == "crimson" else col_gold)
                        p.setBrush(QBrush(pulse_col))
                        p.setPen(Qt.PenStyle.NoPen)
                        p.drawEllipse(QPointF(px, py), 2.4, 2.4)

                    # Draw Synaptic Nodes
                    p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
                    for nx, ny, node in node_pts:
                        charge = node["charge"]
                        p.setBrush(QBrush(QColor(0, 240, 255, int(40 * alpha * charge))))
                        p.setPen(Qt.PenStyle.NoPen)
                        p.drawEllipse(QPointF(nx, ny), max(1.0, 7.0 * charge), max(1.0, 7.0 * charge))

                        p.setBrush(QBrush(QColor(255, 255, 255, int(240 * alpha))))
                        p.setPen(QPen(col_crimson if node["speed"] > 0.5 else col_cyan, 1.2))
                        p.drawEllipse(QPointF(nx, ny), 3.0, 3.0)

                        p.setPen(QPen(QColor(200, 230, 255, int(160 * alpha)), 0.9))
                        p.drawText(QRectF(nx + 6, ny - 6, 40, 12), Qt.AlignmentFlag.AlignLeft, node["label"])

                # 3. Floating Quantum Hex Bits Drifting Upward
                p.setFont(QFont("Consolas", 6))
                for qb in self._quantum_bits:
                    q_alpha = int(120 * alpha * (1.0 - abs(qb["y"])))
                    if q_alpha > 5:
                        p.setPen(QPen(QColor(0, 230, 255, q_alpha), 1.0))
                        p.drawText(QRectF(cx + qb["x"] * r * 1.3, cy + qb["y"] * r * 0.9, 45, 12),
                                   Qt.AlignmentFlag.AlignCenter, qb["val"])

                # 4. Dynamic Multi-Harmonic Neural Waveform (Cognitive Oscilloscope)
                osc_w = max(10.0, min(r * 2.2, 380.0))
                osc_x = cx - osc_w / 2.0
                osc_y = cy + r * 1.05
                p.setPen(QPen(QColor(0, 255, 220, int(190 * alpha)), 1.5))
                p.setBrush(Qt.BrushStyle.NoBrush)
                wave_path = QPainterPath()
                for xi in range(int(osc_w)):
                    frac = xi / osc_w
                    env = math.sin(frac * math.pi)
                    wy = osc_y + env * (
                        math.sin(self.t * 9.0 + xi * 0.12) * 9.0 +
                        math.cos(self.t * 5.0 + xi * 0.06) * 5.0
                    )
                    if xi == 0:
                        wave_path.moveTo(osc_x + xi, wy)
                    else:
                        wave_path.lineTo(osc_x + xi, wy)
                p.drawPath(wave_path)

                p.setPen(QPen(QColor(0, 210, 255, int(50 * alpha)), 0.8, Qt.PenStyle.DotLine))
                p.drawLine(QLineF(osc_x, osc_y, osc_x + osc_w, osc_y))
                p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
                p.setPen(QPen(QColor(0, 230, 255, int(180 * alpha)), 1.0))
                p.drawText(QRectF(osc_x, osc_y + 14, osc_w, 12), Qt.AlignmentFlag.AlignCenter,
                           "NEURAL FLUX // 4.88 GHz // ZERO LATENCY SYNAPSE")

                # 5. Corner Diagnostic Telemetry Callouts
                p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
                p.setPen(QPen(col_crimson, 1.0))
                p.drawText(QRectF(cx - r * 1.35, cy - r * 0.95, 120, 11), Qt.AlignmentFlag.AlignLeft, "QUANTUM CORE")
                p.setFont(QFont("Consolas", 6))
                p.setPen(QPen(col_cyan, 1.0))
                p.drawText(QRectF(cx - r * 1.35, cy - r * 0.95 + 12, 140, 11), Qt.AlignmentFlag.AlignLeft, "128 TFLOPS // ACTIVE")

                p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
                p.setPen(QPen(col_crimson, 1.0))
                p.drawText(QRectF(cx + r * 1.35 - 120, cy - r * 0.95, 120, 11), Qt.AlignmentFlag.AlignRight, "SYNAPSE COHERENCE")
                p.setFont(QFont("Consolas", 6))
                p.setPen(QPen(col_cyan, 1.0))
                p.drawText(QRectF(cx + r * 1.35 - 140, cy - r * 0.95 + 12, 140, 11), Qt.AlignmentFlag.AlignRight, "99.8% // ENTROPY NULL")
            finally:
                p.restore()
        except Exception:
            pass


    # ── Category 1: SEARCH / HUNT (Master Recon Radar) ────────────────────────


    def _paint_search(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        try:
            col_cyan = QColor(0, 240, 255, int(230 * alpha))
            col_cyan_glow = QColor(0, 210, 255, int(70 * alpha))
            col_dim = QColor(0, 150, 200, int(100 * alpha))
            col_red = QColor(255, 65, 50, int(240 * alpha))
            col_gold = QColor(255, 205, 50, int(220 * alpha))

            # 1. Outer Compass Dial with 64 Tick Marks & Cardinal Bearings
            dial_r = r * 1.34
            p.save()
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(col_cyan_glow, 1.0))
            p.drawEllipse(QPointF(cx, cy), dial_r, dial_r)

            # Rotating outer degree notches
            p.translate(cx, cy)
            p.rotate(math.degrees(self.t * 0.25))
            for deg in range(0, 360, 15):
                is_major = (deg % 45 == 0)
                t_len = 8.0 if is_major else 4.0
                p.setPen(QPen(col_cyan if is_major else col_dim, 1.4 if is_major else 0.9))
                rad = math.radians(deg)
                p.drawLine(QLineF(math.cos(rad) * dial_r, math.sin(rad) * dial_r,
                                 math.cos(rad) * (dial_r - t_len), math.sin(rad) * (dial_r - t_len)))
            p.restore()

            # Cardinal Points
            p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
            p.setPen(QPen(col_gold, 1.0))
            p.drawText(QRectF(cx - 15, cy - dial_r - 14, 30, 12), Qt.AlignmentFlag.AlignCenter, "[N]")
            p.drawText(QRectF(cx + dial_r + 4, cy - 6, 30, 12), Qt.AlignmentFlag.AlignLeft, "[E]")
            p.drawText(QRectF(cx - 15, cy + dial_r + 4, 30, 12), Qt.AlignmentFlag.AlignCenter, "[S]")
            p.drawText(QRectF(cx - dial_r - 34, cy - 6, 30, 12), Qt.AlignmentFlag.AlignRight, "[W]")

            # 2. Concentric Radar Range Rings
            p.setBrush(Qt.BrushStyle.NoBrush)
            for factor, label in [(0.35, "0.5 KM"), (0.68, "1.8 KM"), (1.00, "5.0 KM"), (1.30, "12.0 KM")]:
                rr = r * factor
                p.setPen(QPen(col_cyan_glow, 1.0, Qt.PenStyle.DashLine))
                p.drawEllipse(QPointF(cx, cy), rr, rr)
                p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
                p.setPen(QPen(QColor(0, 230, 255, int(150 * alpha)), 1.0))
                p.drawText(QRectF(cx + rr - 35, cy - 12, 70, 12), Qt.AlignmentFlag.AlignRight, label)

            # Crosshair axes
            p.setPen(QPen(col_cyan_glow, 0.9, Qt.PenStyle.DotLine))
            p.drawLine(QLineF(cx - dial_r, cy, cx + dial_r, cy))
            p.drawLine(QLineF(cx, cy - dial_r, cx, cy + dial_r))

            # 3. Sweeping Radar Beam (with trailing phosphor glow sector)
            sweep_len = dial_r
            p.save()
            p.translate(cx, cy)
            p.rotate(math.degrees(self._radar_angle))

            # Multi-layer glow laser line
            p.setPen(QPen(QColor(0, 240, 255, int(90 * alpha)), 4.0))
            p.drawLine(QLineF(0, 0, sweep_len, 0))
            p.setPen(QPen(QColor(255, 255, 255, int(250 * alpha)), 1.5))
            p.drawLine(QLineF(0, 0, sweep_len, 0))

            # Tip laser beacon
            p.setBrush(QBrush(QColor(255, 255, 255, int(240 * alpha))))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(sweep_len, 0), 3.0, 3.0)

            # Trailing gradient sector
            path_tail = QPainterPath()
            path_tail.moveTo(0, 0)
            tail_deg = 45.0
            path_tail.arcTo(QRectF(-sweep_len, -sweep_len, sweep_len * 2, sweep_len * 2), 0.0, -tail_deg)
            path_tail.closeSubpath()

            g_tail = QRadialGradient(0, 0, sweep_len)
            g_tail.setColorAt(0.0, QColor(0, 255, 255, int(140 * alpha)))
            g_tail.setColorAt(0.6, QColor(0, 180, 255, int(50 * alpha)))
            g_tail.setColorAt(1.0, QColor(0, 100, 255, 0))
            p.setBrush(QBrush(g_tail))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(path_tail)
            p.restore()

            # 4. Pulsing Sonar Rings
            for ring in self._sonar_rings:
                s_r = r * ring["r"]
                s_alpha = int(220 * alpha * ring["life"])
                p.setPen(QPen(QColor(0, 255, 230, s_alpha), 1.6))
                p.drawEllipse(QPointF(cx, cy), s_r, s_r)

            # 5. Radar Target Blips with Lock-on Crosshairs & Telemetry
            for bi, b in enumerate(self._radar_blips):
                bx = cx + math.cos(b["angle"]) * (r * b["dist"])
                by = cy + math.sin(b["angle"]) * (r * b["dist"])
                b_alpha = int(255 * alpha * b["life"])

                is_primary = (bi == 0)

                if is_primary:
                    # Vector tether line to center
                    p.setPen(QPen(QColor(255, 45, 40, int(120 * alpha)), 1.0, Qt.PenStyle.DashLine))
                    p.drawLine(QLineF(cx, cy, bx, by))

                    # Dynamic rotating diamond lock reticle
                    p.save()
                    p.translate(bx, by)
                    p.rotate(math.degrees(self.t * 3.5))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.setPen(QPen(QColor(255, 45, 40, b_alpha), 1.6))
                    dia_sz = 12.0
                    p.drawPolygon(QPolygonF([
                        QPointF(0, -dia_sz), QPointF(dia_sz, 0),
                        QPointF(0, dia_sz), QPointF(-dia_sz, 0)
                    ]))
                    p.restore()

                # Outer lock ring
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(col_red if is_primary else col_cyan, 1.2))
                p.drawEllipse(QPointF(bx, by), 5.0, 5.0)

                # Center target core
                p.setBrush(QBrush(QColor(255, 255, 255, b_alpha)))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(bx, by), 2.2, 2.2)

                # Target Lock Corner Brackets
                sz = 9.0
                p.setPen(QPen(QColor(0, 250, 255, b_alpha), 1.2))
                p.drawLine(QLineF(bx - sz, by - sz, bx - sz + 4, by - sz))
                p.drawLine(QLineF(bx - sz, by - sz, bx - sz, by - sz + 4))
                p.drawLine(QLineF(bx + sz, by - sz, bx + sz - 4, by - sz))
                p.drawLine(QLineF(bx + sz, by - sz, bx + sz, by - sz + 4))
                p.drawLine(QLineF(bx - sz, by + sz, bx - sz + 4, by + sz))
                p.drawLine(QLineF(bx - sz, by + sz, bx - sz, by + sz - 4))
                p.drawLine(QLineF(bx + sz, by + sz, bx + sz - 4, by + sz))
                p.drawLine(QLineF(bx + sz, by + sz, bx + sz, by + sz - 4))

                # Telemetry label
                p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
                col_lbl = QColor(255, 225, 120, b_alpha) if is_primary else QColor(220, 245, 255, b_alpha)
                p.setPen(QPen(col_lbl, 1.0))
                stat = "PRIMARY LOCK" if is_primary else "LOCK"
                p.drawText(QRectF(bx + sz + 5, by - 10, 120, 12), Qt.AlignmentFlag.AlignLeft, f"TARGET // {b['ip']}")
                p.drawText(QRectF(bx + sz + 5, by + 1, 120, 12), Qt.AlignmentFlag.AlignLeft, f"RNG: {b['range']}m  {stat}")

            # 6. Bottom RF Spectrum Equalizer Band
            rf_x = cx - 80
            rf_y = cy + dial_r + 18
            p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
            p.setPen(QPen(col_cyan, 1.0))
            p.drawText(QRectF(rf_x - 30, rf_y - 2, 220, 12), Qt.AlignmentFlag.AlignCenter, "RF SPECTRUM // 2.45 GHz SCANNING")
            for bi in range(16):
                b_h = 3 + 8 * (0.5 + 0.5 * math.sin(self.t * 6.0 + bi * 0.7))
                p.setBrush(QBrush(col_cyan if bi % 3 != 0 else col_red))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(QRectF(rf_x + bi * 10, rf_y + 12 - b_h, 6, b_h))
        except Exception:
            pass



    # ── Category 2: PURGE / INCINERATE (Thermal Disintegration) ───────────────

    def _paint_purge(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        laser_y = cy + self._purge_laser_y * r * 1.2
        beam_w = r * 1.4

        # 1. Multi-Pass High-Voltage Laser Sweep Line with Micro-Jitter
        jitter = random.uniform(-0.8, 0.8)
        p.save()
        # Outer diffused plasma glow
        g_glow = QLinearGradient(cx - beam_w, laser_y, cx + beam_w, laser_y)
        g_glow.setColorAt(0.00, QColor(255, 30, 20, 0))
        g_glow.setColorAt(0.20, QColor(255, 60, 30, int(140 * alpha)))
        g_glow.setColorAt(0.50, QColor(255, 120, 40, int(220 * alpha)))
        g_glow.setColorAt(0.80, QColor(255, 60, 30, int(140 * alpha)))
        g_glow.setColorAt(1.00, QColor(255, 30, 20, 0))
        p.setPen(QPen(QBrush(g_glow), 8.0))
        p.drawLine(QLineF(cx - beam_w, laser_y + jitter, cx + beam_w, laser_y + jitter))

        # Core white-hot laser line
        p.setPen(QPen(QColor(255, 255, 255, int(255 * alpha)), 2.2))
        p.drawLine(QLineF(cx - beam_w * 0.85, laser_y, cx + beam_w * 0.85, laser_y))

        # Lateral electric crackle arcs branching off the beam
        p.setPen(QPen(QColor(255, 220, 140, int(190 * alpha)), 1.2))
        for side in (-1, 1):
            ax = cx + side * (beam_w * 0.7)
            ay = laser_y
            path_arc = QPainterPath()
            path_arc.moveTo(ax, ay)
            path_arc.lineTo(ax + side * 12, ay - 6 + random.uniform(-3, 3))
            path_arc.lineTo(ax + side * 22, ay + 4 + random.uniform(-3, 3))
            p.drawPath(path_arc)
        p.restore()

        # 2. Physics-based Disintegration Embers
        for pt in self._purge_particles:
            px = cx + pt["x"] * r
            py = cy + pt["y"] * r
            p_alpha = int(245 * alpha * pt["life"])
            c = QColor(pt["color"].red(), pt["color"].green(), pt["color"].blue(), p_alpha)
            p.setBrush(QBrush(c))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(px, py), pt["sz"], pt["sz"])

        # 3. Lateral Sector Disintegration Blocks
        for side in (-1, 1):
            sx = cx + side * (r * 1.25)
            num_blocks = 14
            for i in range(num_blocks):
                by = cy - r * 0.85 + i * (r * 1.7 / num_blocks)
                is_purged = (by < laser_y)
                if is_purged:
                    b_col = QColor(0, 240, 160, int(150 * alpha))   # Clean optimized
                else:
                    b_col = QColor(255, 45, 35, int(200 * alpha))    # Corrupt bloat
                p.setBrush(QBrush(b_col))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(QRectF(sx - 9, by, 18, 5.5), 1.2, 1.2)

    # ── Category 3: GHOST / OVERRIDE (Neural Precision Reticle) ───────────────

    def _paint_ghost(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        col_green = QColor(0, 255, 160, int(230 * alpha))
        col_magenta = QColor(255, 40, 180, int(120 * alpha))

        # 1. Dual-Channel Chromatic Aberration Motion Trail
        if len(self._ghost_trail) > 1:
            for i in range(len(self._ghost_trail) - 1):
                pt1 = self._ghost_trail[i]
                pt2 = self._ghost_trail[i + 1]
                t_alpha = int(200 * alpha * (i / len(self._ghost_trail)))
                # Chromatic separation
                p.setPen(QPen(QColor(0, 255, 180, t_alpha), 2.2))
                p.drawLine(QPointF(cx + pt1.x() * r, cy + pt1.y() * r),
                           QPointF(cx + pt2.x() * r, cy + pt2.y() * r))
                p.setPen(QPen(QColor(255, 60, 160, int(t_alpha * 0.5)), 1.2))
                p.drawLine(QPointF(cx + pt1.x() * r + 2.0, cy + pt1.y() * r + 1.0),
                           QPointF(cx + pt2.x() * r + 2.0, cy + pt2.y() * r + 1.0))

        # 2. Multi-Layer Shockwave Ripples
        for rip in self._ghost_ripples:
            r_alpha = int(230 * alpha * rip["life"])
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(0, 255, 210, r_alpha), 1.8))
            r_cx = cx + rip["pt"].x() * r
            r_cy = cy + rip["pt"].y() * r
            p.drawEllipse(QPointF(r_cx, r_cy), rip["radius"], rip["radius"])
            p.setPen(QPen(QColor(255, 255, 255, int(r_alpha * 0.6)), 0.9))
            p.drawEllipse(QPointF(r_cx, r_cy), rip["radius"] * 0.65, rip["radius"] * 0.65)

        # 3. Precision 4-Quadrant Reticle with Stabilizer Ticks
        gx = cx + self._ghost_cursor.x() * r
        gy = cy + self._ghost_cursor.y() * r

        p.save()
        p.translate(gx, gy)
        p.rotate(math.degrees(self.t * 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(col_green, 1.8))

        sz = 16.0
        # 4 quadrant arcs
        for deg in (25, 115, 205, 295):
            p.drawArc(QRectF(-sz, -sz, sz * 2, sz * 2), deg * 16, 40 * 16)

        # Crosshair ticks
        p.drawLine(QLineF(-sz - 6, 0, -sz + 1, 0))
        p.drawLine(QLineF(sz - 1, 0, sz + 6, 0))
        p.drawLine(QLineF(0, -sz - 6, 0, -sz + 1))
        p.drawLine(QLineF(0, sz - 1, 0, sz + 6))
        p.restore()

        # Center laser point
        p.setBrush(QBrush(QColor(255, 255, 255, int(255 * alpha))))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(gx, gy), 2.5, 2.5)

        # Floating Telemetry Tag
        p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
        p.setPen(QPen(QColor(0, 255, 180, int(210 * alpha)), 1.0))
        p.drawText(QRectF(gx + 22, gy - 12, 120, 12), Qt.AlignmentFlag.AlignLeft, "NEURAL OVERRIDE // ACTIVE")
        p.drawText(QRectF(gx + 22, gy + 1, 120, 12), Qt.AlignmentFlag.AlignLeft, f"X:{int(gx):04d} Y:{int(gy):04d}")

    # ── Category 4: SWARM / DRONES (Tactical Drone Fleet) ────────────────────

    def _paint_swarm(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        col_gold = QColor(255, 195, 45, int(235 * alpha))
        col_red = QColor(255, 55, 45, int(220 * alpha))

        # 1. Pulsing Hexagonal Hive Grid with Geodesic Diagonals
        hex_r = r * 1.35
        p.save()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 140, 20, int(75 * alpha)), 1.2, Qt.PenStyle.DashLine))
        num_sides = 6
        hex_pts = []
        for i in range(num_sides):
            ang = (i / num_sides) * math.pi * 2 + (self.t * 0.22)
            pt = QPointF(cx + math.cos(ang) * hex_r, cy + math.sin(ang) * hex_r)
            hex_pts.append(pt)
        p.drawPolygon(QPolygonF(hex_pts))
        # Internal cross-bracing
        for i in range(3):
            p.setPen(QPen(QColor(255, 120, 30, int(45 * alpha)), 0.8, Qt.PenStyle.DotLine))
            p.drawLine(hex_pts[i], hex_pts[i + 3])
        p.restore()

        # 2. Orbiting 3D Stealth Drones with Laser Telemetry Links
        for d in self._drones:
            ang = d["angle"]
            # 3D tilted orbit coordinates
            dx = cx + math.cos(ang) * (r * d["rx"])
            dy = cy + math.sin(ang) * (r * d["ry"]) + math.sin(ang) * (r * d["tilt"])
            z_depth = math.sin(ang)  # -1 (back) to +1 (front)
            scale = 0.8 + 0.35 * (z_depth * 0.5 + 0.5)

            # Laser telemetry link to central core
            p.setPen(QPen(QColor(255, 80, 40, int((60 + 50 * scale) * alpha)), 1.0, Qt.PenStyle.DotLine))
            p.drawLine(QLineF(cx, cy - r * 0.15, dx, dy))

            # Traveling data pulse along the link
            pulse_prog = (self.t * 1.5 + d["speed"]) % 1.0
            px = cx + (dx - cx) * pulse_prog
            py = (cy - r * 0.15) + ((dy - (cy - r * 0.15))) * pulse_prog
            p.setBrush(QBrush(QColor(255, 230, 100, int(220 * alpha))))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(px, py), 2.2, 2.2)

            # Draw Stealth Drone Chevron Glyph
            p.save()
            p.translate(dx, dy)
            flight_ang = math.degrees(ang + math.pi / 2.0)
            p.rotate(flight_ang)
            p.scale(scale, scale)

            path_drone = QPainterPath()
            path_drone.moveTo(0, -11)
            path_drone.lineTo(9, 8)
            path_drone.lineTo(0, 4)
            path_drone.lineTo(-9, 8)
            path_drone.closeSubpath()

            p.setBrush(QBrush(QColor(22, 28, 40, int(240 * alpha))))
            p.setPen(QPen(col_gold, 1.6))
            p.drawPath(path_drone)

            # Glowing ion thruster plume
            p.setBrush(QBrush(QColor(255, 75, 40, int(240 * alpha))))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(0, 4), 2.5, 2.5)
            p.restore()

            # Drone label
            p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
            p.setPen(QPen(QColor(255, 215, 110, int(200 * alpha)), 1.0))
            p.drawText(QRectF(dx + 12, dy - 7, 70, 14), Qt.AlignmentFlag.AlignLeft, d["label"])

    # ── Category 5: SENTRY / DEFENSE (Military Tactical Sentinel) ────────────

    def _paint_sentry(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        col_crimson = QColor(255, 30, 40, int(240 * alpha))
        col_glow = QColor(255, 30, 40, int(60 * alpha))

        # 1. Dual Sweeping Tactical Radars
        sonar_r = r * 1.35
        p.save()
        p.translate(cx, cy)

        # Fast inner sweep
        p.rotate(math.degrees(self._sentry_scan))
        p.setPen(QPen(col_crimson, 2.0))
        p.drawLine(QLineF(0, 0, sonar_r, 0))

        path_sonar = QPainterPath()
        path_sonar.moveTo(0, 0)
        path_sonar.arcTo(QRectF(-sonar_r, -sonar_r, sonar_r * 2, sonar_r * 2), 0.0, -50.0)
        path_sonar.closeSubpath()
        g_sonar = QRadialGradient(0, 0, sonar_r)
        g_sonar.setColorAt(0.0, QColor(255, 40, 40, int(130 * alpha)))
        g_sonar.setColorAt(0.7, QColor(200, 20, 30, int(40 * alpha)))
        g_sonar.setColorAt(1.0, QColor(100, 0, 0, 0))
        p.setBrush(QBrush(g_sonar))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path_sonar)
        p.restore()

        # 2. Counter-rotating outer perimeter sweep
        p.save()
        p.translate(cx, cy)
        p.rotate(math.degrees(self._sentry_scan_outer))
        p.setPen(QPen(QColor(255, 120, 40, int(180 * alpha)), 1.2, Qt.PenStyle.DashLine))
        p.drawLine(QLineF(0, 0, sonar_r * 1.08, 0))
        p.restore()

        # 3. Vibrating Laser Tripwire with Hazard Crosshatch
        trip_y = cy + math.sin(self.t * 3.8) * (r * 0.85)
        p.setPen(QPen(QColor(255, 40, 50, int(200 * alpha)), 1.4, Qt.PenStyle.DashDotLine))
        p.drawLine(QLineF(cx - r * 1.32, trip_y, cx + r * 1.32, trip_y))

        # 4. Heavy Angular Combat Brackets with Target Reticles
        ret_sz = r * 1.26
        p.setPen(QPen(col_crimson, 2.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        arm = 28.0

        for sx in (-1, 1):
            for sy in (-1, 1):
                bx = cx + sx * ret_sz
                by = cy + sy * ret_sz
                p.drawLine(QLineF(bx, by, bx - sx * arm, by))
                p.drawLine(QLineF(bx, by, bx, by - sy * arm))
                p.setBrush(QBrush(col_crimson))
                p.drawRect(QRectF(bx - 2, by - 2, 4, 4))
                p.setBrush(Qt.BrushStyle.NoBrush)

        # Tactical Warning Badge
        p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        p.setPen(QPen(col_crimson, 1.0))
        p.drawText(QRectF(cx - 100, cy + ret_sz + 6, 200, 14), Qt.AlignmentFlag.AlignCenter, "[ PERIMETER LOCKED // COMBAT SENTRY ]")

    # ── Category 6: MATRIX / SYSTEM (3D Tesseract & Equalizers) ──────────────

    def _paint_matrix(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        col_gold = QColor(255, 205, 55, int(230 * alpha))
        col_amber = QColor(255, 140, 20, int(160 * alpha))
        col_cyan = QColor(0, 240, 255, int(210 * alpha))

        # 1. 16-Thread CPU Equalizer Bars with Peak-Hold Needles
        num_threads = 16
        for i in range(num_threads):
            ang = (i / num_threads) * math.pi * 2
            load = 0.35 + 0.55 * (0.5 + 0.5 * math.sin(self.t * 3.5 + i * 0.95))
            b_len = 16.0 + load * 36.0
            p1 = QPointF(cx + math.cos(ang) * (r * 1.14), cy + math.sin(ang) * (r * 1.14))
            p2 = QPointF(cx + math.cos(ang) * (r * 1.14 + b_len), cy + math.sin(ang) * (r * 1.14 + b_len))
            p.setPen(QPen(col_gold if load > 0.65 else col_amber, 2.2))
            p.drawLine(p1, p2)

            # Peak hold needle
            pk_len = 16.0 + self._peak_holds[i] * 36.0
            pk_pt = QPointF(cx + math.cos(ang) * (r * 1.14 + pk_len + 3.0),
                            cy + math.sin(ang) * (r * 1.14 + pk_len + 3.0))
            p.setPen(QPen(QColor(255, 255, 255, int(230 * alpha)), 2.2))
            p.drawPoint(pk_pt)

        # 2. 3D Wireframe Tesseract (Hypercube) centered at top-right
        cube_cx = cx + r * 1.02
        cube_cy = cy - r * 0.78
        cube_sz = 28.0

        p.save()
        p.translate(cube_cx, cube_cy)
        p.setPen(QPen(col_cyan, 1.3))
        p.setBrush(Qt.BrushStyle.NoBrush)

        rx = self._matrix_rot_x
        ry = self._matrix_rot_y

        nodes = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    x1 = sx * math.cos(ry) + sz * math.sin(ry)
                    z1 = -sx * math.sin(ry) + sz * math.cos(ry)
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

        # Glowing vertex nodes
        p.setBrush(QBrush(QColor(255, 255, 255, int(220 * alpha))))
        p.setPen(Qt.PenStyle.NoPen)
        for n in nodes:
            p.drawEllipse(n, 2.0, 2.0)
        p.restore()

        # Tachometer Label
        p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
        p.setPen(QPen(col_gold, 1.0))
        p.drawText(QRectF(cube_cx - 45, cube_cy + cube_sz + 12, 90, 12), Qt.AlignmentFlag.AlignCenter, "TESSERACT // CORE")

    # ── Category 7: CODE / COMPILER (Neural Bytecode Matrix) ─────────────────

    def _paint_code(self, p: QPainter, cx: float, cy: float, r: float, w: float, h: float, alpha: float) -> None:
        col_green = QColor(0, 255, 140, int(220 * alpha))
        col_cyan = QColor(0, 230, 255, int(200 * alpha))
        col_gold = QColor(255, 210, 60, int(210 * alpha))
        col_dim = QColor(0, 160, 90, int(120 * alpha))

        # 1. Cascading Assembly Bytecode Ribbons with Syntax Highlighting
        line_h = 13.5
        num_visible = int((h * 0.62) / line_h)
        offset = int(self.t * 14.0)

        # Left Column
        for i in range(num_visible):
            idx = (offset + i) % len(self._code_streams)
            item = self._code_streams[idx]
            ly = 52 + i * line_h
            is_lead = (i == 0 or i % 7 == 0)
            p.setFont(QFont("Consolas", 6, QFont.Weight.Bold if is_lead else QFont.Weight.Normal))
            # Address
            p.setPen(QPen(col_cyan if is_lead else col_dim, 1.0))
            p.drawText(QRectF(14, ly, 55, line_h), Qt.AlignmentFlag.AlignLeft, item["addr"])
            # Opcode
            p.setPen(QPen(QColor(255, 255, 255) if is_lead else col_green, 1.0))
            p.drawText(QRectF(72, ly, 35, line_h), Qt.AlignmentFlag.AlignLeft, item["op"])
            # Regs
            p.setPen(QPen(col_gold if is_lead else col_dim, 1.0))
            p.drawText(QRectF(108, ly, 65, line_h), Qt.AlignmentFlag.AlignLeft, f"{item['r1']}, {item['r2']}")

        # Right Column
        for i in range(num_visible):
            idx = (offset + i + 23) % len(self._code_streams)
            item = self._code_streams[idx]
            ly = 52 + i * line_h
            is_lead = (i % 6 == 0)
            rx_pos = w - 176
            p.setFont(QFont("Consolas", 6, QFont.Weight.Bold if is_lead else QFont.Weight.Normal))
            p.setPen(QPen(col_cyan if is_lead else col_dim, 1.0))
            p.drawText(QRectF(rx_pos, ly, 55, line_h), Qt.AlignmentFlag.AlignLeft, item["addr"])
            p.setPen(QPen(QColor(255, 255, 255) if is_lead else col_green, 1.0))
            p.drawText(QRectF(rx_pos + 58, ly, 35, line_h), Qt.AlignmentFlag.AlignLeft, item["op"])
            p.setPen(QPen(col_gold if is_lead else col_dim, 1.0))
            p.drawText(QRectF(rx_pos + 95, ly, 65, line_h), Qt.AlignmentFlag.AlignLeft, f"{item['r1']}, {item['r2']}")

        # 2. Logic Oscilloscope Waveform at Bottom Center
        p.save()
        osc_w = 240.0
        osc_x = cx - osc_w / 2.0
        osc_y = cy + r * 1.15
        p.setPen(QPen(col_green, 1.4))
        path_osc = QPainterPath()
        path_osc.moveTo(osc_x, osc_y)
        for step_i in range(int(osc_w)):
            wx = osc_x + step_i
            wy = osc_y + math.sin(self.t * 8.0 + step_i * 0.12) * 8.0 * math.cos(self.t * 3.0 + step_i * 0.04)
            path_osc.lineTo(wx, wy)
        p.drawPath(path_osc)
        p.restore()

    # ── Category 8: SONIC / HARMONICS (Vibranium Resonance) ──────────────────

    def _paint_sonic(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        col_purple = QColor(210, 75, 255, int(220 * alpha))
        col_blue = QColor(65, 175, 255, int(200 * alpha))

        # 1. Concentric Harmonic Soundwave Rings
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(5):
            ring_phase = (self._sonic_phase + i * 1.4) % 7.0
            ring_r = r * 0.4 + ring_phase * (r * 0.22)
            r_alpha = int(_clamp(245 * (1.0 - ring_phase / 7.0) * alpha, 0, 255))
            p.setPen(QPen(QColor(190, 85, 255, r_alpha), 1.8))
            p.drawEllipse(QPointF(cx, cy - r * 0.1), ring_r, ring_r * 0.70)

        # 2. 32-Band Circular Frequency Spectrum Bars
        num_bars = 32
        for i in range(num_bars):
            ang = (i / num_bars) * math.pi * 2 + (self.t * 0.4)
            freq_val = 0.3 + 0.65 * (0.5 + 0.5 * math.sin(self.t * 6.0 + i * 0.8))
            bar_len = 10.0 + freq_val * 28.0
            p1 = QPointF(cx + math.cos(ang) * (r * 1.15), cy + math.sin(ang) * (r * 1.15))
            p2 = QPointF(cx + math.cos(ang) * (r * 1.15 + bar_len), cy + math.sin(ang) * (r * 1.15 + bar_len))
            p.setPen(QPen(col_purple if i % 2 == 0 else col_blue, 2.0))
            p.drawLine(p1, p2)

    # ── Category 9: WORKSPACE (Environment Synchronizer) ─────────────────────

    def _paint_workspace(self, p: QPainter, cx: float, cy: float, r: float, w: float, h: float, alpha: float) -> None:
        col_cyan = QColor(0, 240, 255, int(230 * alpha))
        col_gold = QColor(255, 205, 50, int(220 * alpha))

        # 5 Interconnected Environment Nodes: IDE, Terminal, Web, Audio, IoT
        nodes = [
            ("CORE IDE", cx - r * 1.25, cy - r * 0.65),
            ("TERMINAL", cx + r * 1.25, cy - r * 0.65),
            ("PORTALS", cx - r * 1.28, cy + r * 0.65),
            ("ACOUSTICS", cx + r * 1.28, cy + r * 0.65),
            ("SMART IOT", cx, cy + r * 1.22),
        ]

        # Draw circuit traces connecting nodes to Ultron core
        for name, nx, ny in nodes:
            # Multi-layer circuit line
            p.setPen(QPen(QColor(0, 210, 255, int(60 * alpha)), 3.0))
            p.drawLine(QLineF(cx, cy, nx, ny))
            p.setPen(QPen(col_cyan, 1.2, Qt.PenStyle.DashLine))
            p.drawLine(QLineF(cx, cy, nx, ny))

            # Node Box
            p.setBrush(QBrush(QColor(12, 16, 26, int(230 * alpha))))
            p.setPen(QPen(col_gold, 1.4))
            p.drawRoundedRect(QRectF(nx - 42, ny - 10, 84, 20), 2.0, 2.0)

            # Node text
            p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
            p.setPen(QPen(QColor(255, 255, 255, int(240 * alpha)), 1.0))
            p.drawText(QRectF(nx - 42, ny - 10, 84, 20), Qt.AlignmentFlag.AlignCenter, name)

        # Circuit Pulses racing between nodes and core
        for pulse in self._circuit_pulses:
            idx = pulse["path_idx"] % len(nodes)
            name, nx, ny = nodes[idx]
            prog = pulse["progress"]
            px = nx + (cx - nx) * prog
            py = ny + (cy - ny) * prog
            p.setBrush(QBrush(QColor(255, 255, 255, int(250 * alpha))))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(px, py), 2.5, 2.5)

    # ── Category 10: GENERIC OVERCLOCK (Tactical Directive HUD) ───────────────

    def _paint_generic(self, p: QPainter, cx: float, cy: float, r: float, alpha: float) -> None:
        try:
            col_crimson = QColor(255, 45, 40, int(220 * alpha))
            col_cyan = QColor(0, 240, 255, int(210 * alpha))
            col_gold = QColor(255, 205, 50, int(230 * alpha))

            p.save()
            p.translate(cx, cy)

            # 1. Outer Counter-Rotating Segmented Notched Rings
            p.save()
            p.rotate(math.degrees(self.t * 2.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(col_gold, 1.4, Qt.PenStyle.DashDotLine))
            p.drawEllipse(QRectF(-r * 1.34, -r * 1.34, r * 2.68, r * 2.68))

            # 8-point tick marks
            for deg in range(0, 360, 45):
                rad = math.radians(deg)
                p.setPen(QPen(col_crimson, 1.6))
                p.drawLine(QLineF(math.cos(rad) * (r * 1.34), math.sin(rad) * (r * 1.34),
                                 math.cos(rad) * (r * 1.44), math.sin(rad) * (r * 1.44)))
            p.restore()

            # 2. Inner Rapid Gyro Arc
            p.save()
            p.rotate(-math.degrees(self.t * 3.4))
            p.setPen(QPen(col_cyan, 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            for arc_s in (20, 140, 260):
                p.drawArc(QRectF(-r * 1.22, -r * 1.22, r * 2.44, r * 2.44), arc_s * 16, 80 * 16)

            # Orbiting energy beads
            for b_ang in (0.0, math.pi):
                bx = math.cos(b_ang) * (r * 1.22)
                by = math.sin(b_ang) * (r * 1.22)
                p.setBrush(QBrush(QColor(255, 255, 255, int(240 * alpha))))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(bx, by), 2.8, 2.8)
            p.restore()

            # 3. 4-Corner Tactical Framing Reticles
            sz = r * 1.15
            arm = 18.0
            p.setPen(QPen(col_crimson, 1.4))
            p.drawLine(QLineF(-sz, -sz, -sz + arm, -sz))
            p.drawLine(QLineF(-sz, -sz, -sz, -sz + arm))
            p.drawLine(QLineF(sz, -sz, sz - arm, -sz))
            p.drawLine(QLineF(sz, -sz, sz, -sz + arm))
            p.drawLine(QLineF(-sz, sz, -sz + arm, sz))
            p.drawLine(QLineF(-sz, sz, -sz, sz - arm))
            p.drawLine(QLineF(sz, sz, sz - arm, sz))
            p.drawLine(QLineF(sz, sz, sz, sz - arm))

            # Center Micro-Status
            p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
            p.setPen(QPen(col_cyan, 1.0))
            p.drawText(QRectF(-120, r * 1.05, 240, 12), Qt.AlignmentFlag.AlignCenter,
                       "OVERCLOCK // ACTIVE DIRECTIVE EXECUTION")
            p.restore()
        except Exception:
            pass

    # ── Telemetry Banner & Completion Burst ──────────────────────────────────

    def _paint_task_banner(self, p: QPainter, cx: float, cy: float, r: float, w: float, alpha: float) -> None:
        banner_y = 22.0
        p.save()

        # Chamfered HUD Telemetry Plate
        b_w = min(w * 0.84, 520.0)
        bx = cx - b_w / 2.0

        # Background gradient with cyber tech shading
        g_strip = QLinearGradient(bx, banner_y, bx + b_w, banner_y)
        g_strip.setColorAt(0.00, QColor(6, 10, 16, 0))
        g_strip.setColorAt(0.15, QColor(12, 18, 30, int(230 * alpha)))
        g_strip.setColorAt(0.85, QColor(12, 18, 30, int(230 * alpha)))
        g_strip.setColorAt(1.00, QColor(6, 10, 16, 0))
        p.setBrush(QBrush(g_strip))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(bx, banner_y, b_w, 24), 3.0, 3.0)

        # Glowing accent border line
        p.setPen(QPen(QColor(255, 45, 35, int(230 * alpha)), 1.4))
        p.drawLine(QLineF(bx + 18, banner_y + 24, bx + b_w - 18, banner_y + 24))

        # Animated Progress Scanline passing along the banner
        scan_pos = (self.t * 0.8) % 1.0
        sx = bx + 20 + scan_pos * (b_w - 40)
        p.setBrush(QBrush(QColor(255, 255, 255, int(250 * alpha))))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(sx, banner_y + 24), 2.2, 2.2)

        # Active Status Beacon LED (blinking)
        led_blink = 0.5 + 0.5 * math.sin(self.t * 7.0)
        p.setBrush(QBrush(QColor(255, 40, 30, int((150 + 105 * led_blink) * alpha))))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(bx + 26, banner_y + 12), 3.5, 3.5)

        # Banner Title
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        p.setPen(QPen(QColor(255, 225, 170, int(255 * alpha)), 1.0))
        p.drawText(QRectF(bx + 35, banner_y + 2, b_w - 70, 20), Qt.AlignmentFlag.AlignCenter, f"◈ {self.label} ◈")
        p.restore()

    def _paint_completion_burst(self, p: QPainter, cx: float, cy: float, r: float, burst: float) -> None:
        """Draw an expanding holographic dual-ring shockwave burst confirming task completion."""
        b_r1 = r * 0.4 + (1.0 - burst) * (r * 1.35)
        b_r2 = r * 0.3 + (1.0 - burst) * (r * 1.05)
        b_alpha = int(245 * burst)

        p.save()
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Dual expanding rings
        p.setPen(QPen(QColor(0, 255, 190, b_alpha), 2.8))
        p.drawEllipse(QPointF(cx, cy), b_r1, b_r1)
        p.setPen(QPen(QColor(0, 230, 255, int(b_alpha * 0.7)), 1.6))
        p.drawEllipse(QPointF(cx, cy), b_r2, b_r2)

        # Hexagonal burst brackets
        p.setPen(QPen(QColor(255, 255, 255, b_alpha), 1.6))
        hex_pts = []
        for i in range(6):
            ang = (i / 6.0) * math.pi * 2
            hex_pts.append(QPointF(cx + math.cos(ang) * b_r1, cy + math.sin(ang) * b_r1))
        p.drawPolygon(QPolygonF(hex_pts))

        # Radial sparks
        for si in range(16):
            ang = (si / 16.0) * math.pi * 2 + (1.0 - burst) * 0.4
            spk_r = b_r1 * (0.85 + 0.25 * burst)
            spk_x = cx + math.cos(ang) * spk_r
            spk_y = cy + math.sin(ang) * spk_r
            p.setBrush(QBrush(QColor(255, 255, 255, b_alpha)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(spk_x, spk_y), 2.2, 2.2)

        # "[ ✓ DIRECTIVE COMPLETED // SYMMETRY RESTORED ]" flourish
        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        p.setPen(QPen(QColor(0, 255, 190, b_alpha), 1.0))
        p.drawText(QRectF(cx - 200, cy - r * 0.85, 400, 22), Qt.AlignmentFlag.AlignCenter,
                   "[ ✓ DIRECTIVE COMPLETED // SYMMETRY RESTORED ]")
        p.restore()


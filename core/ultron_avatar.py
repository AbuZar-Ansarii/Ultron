"""
Ultron Cybernetic Holographic 3D Avatar for the HUD.

Engineered to authentically match the official MCU Ultron Prime:
  * High-fidelity multi-layer compositor using authentic Ultron Prime chassis
  * Precision-masked articulated titanium mandible plate with real-time lip-sync
  * Deep internal 3D throat cavity with glowing crimson vocal furnace & titanium grill slats
  * Additive neural energy pulse in forehead fissures and cheek cooling vents (zero chrome tinting)
  * Menacing robotic ocular sensors with concentric aperture rings, white-hot pupils, and tactical shutter
  * 3D head speech nod, breathing parallax sway, gaze saccades, and glance targeting
  * Futuristic holographic telemetry HUD rings, rotating azimuth arcs, and corner brackets
  * Zero-lag pixmap scaling cache maintaining 60 FPS performance
"""

from __future__ import annotations

import math
import random
import time
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QLineF, QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QImage, QLinearGradient, QPainter,
    QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient,
)


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


class UltronAvatar:
    """Authentic MCU Ultron Prime 3D Cybernetic Avatar with real-time vocal articulation."""

    SPAN: float = 1.35  # Normalized vertical span for HUD layout calculation

    def __init__(self, image_path: str | Path | None = None) -> None:
        self._t: float = 0.0
        self._amp: float = 0.0
        self._amp_raw: float = 0.0
        self._jaw_open: float = 0.0
        self._jaw_wide: float = 0.0
        self._vocal_flare: float = 0.0
        self._speech_nod: float = 0.0

        # State flags
        self._speaking: bool = False
        self._muted: bool = False
        self._state: str = "IDLE"

        # 3D pose and parallax
        self._yaw: float = 0.0
        self._pitch: float = 0.0
        self._roll: float = 0.0
        self._sway_phase: float = 0.0
        self._breath: float = 0.0
        self._energy_phase: float = 0.0
        self._hud_angle: float = 0.0
        self._scan_y: float = 0.0

        # Ocular tracking & tactical shutter
        self._gaze_x: float = 0.0
        self._gaze_y: float = 0.0
        self._tgt_gaze_x: float = 0.0
        self._tgt_gaze_y: float = 0.0
        self._gaze_timer: float = 0.0
        self._shutter: float = 0.90
        self._tgt_shutter: float = 0.90

        # Live cursor tracking
        self._cursor_active: bool = False
        self._cursor_x: float = 0.0
        self._cursor_y: float = 0.0
        self._cursor_timeout: float = 0.0

        # Scaling cache for 60 FPS rendering
        self._cache_key: tuple[int, int] | None = None
        self._cached_skull: QPixmap | None = None
        self._cached_chin: QPixmap | None = None
        self._cached_glow: QPixmap | None = None

        # Build multi-layer decomposition
        self._load_and_decompose_layers(image_path)

    def _load_and_decompose_layers(self, image_path: str | Path | None) -> None:
        """Load the authentic Ultron asset and separate into Skull, Mandible, and Glow layers."""
        resolved_path = None
        candidates = []
        if image_path:
            candidates.append(Path(image_path))
        candidates.extend([
            Path("ultron_avatar.png"),
            Path("ultron.jpeg"),
            Path(__file__).resolve().parent.parent / "ultron_avatar.png",
            Path(__file__).resolve().parent.parent / "ultron.jpeg",
        ])

        for c in candidates:
            if c.is_file():
                resolved_path = c
                break

        if resolved_path is not None:
            base_img = QImage(str(resolved_path))
        else:
            # Fallback procedural generation if no asset file found
            base_img = QImage(474, 530, QImage.Format.Format_ARGB32_Premultiplied)
            base_img.fill(QColor(30, 36, 48))

        w, h = base_img.width(), base_img.height()
        self._base_w = w
        self._base_h = h

        # ── 1. Precision Chin / Mandible Contour ──────────────────────────────
        # Traced exactly along Ultron Prime's anatomical grooves
        path_chin = QPainterPath()
        path_chin.moveTo(236.0 / 474.0 * w, 273.0 / 530.0 * h)
        path_chin.cubicTo(
            255.0 / 474.0 * w, 271.0 / 530.0 * h,
            285.0 / 474.0 * w, 271.0 / 530.0 * h,
            312.0 / 474.0 * w, 273.0 / 530.0 * h,
        )
        path_chin.cubicTo(
            320.0 / 474.0 * w, 298.0 / 530.0 * h,
            322.0 / 474.0 * w, 340.0 / 530.0 * h,
            314.0 / 474.0 * w, 380.0 / 530.0 * h,
        )
        path_chin.cubicTo(
            304.0 / 474.0 * w, 396.0 / 530.0 * h,
            285.0 / 474.0 * w, 404.0 / 530.0 * h,
            274.0 / 474.0 * w, 404.0 / 530.0 * h,
        )
        path_chin.cubicTo(
            260.0 / 474.0 * w, 404.0 / 530.0 * h,
            246.0 / 474.0 * w, 396.0 / 530.0 * h,
            237.0 / 474.0 * w, 380.0 / 530.0 * h,
        )
        path_chin.cubicTo(
            228.0 / 474.0 * w, 340.0 / 530.0 * h,
            229.0 / 474.0 * w, 298.0 / 530.0 * h,
            236.0 / 474.0 * w, 273.0 / 530.0 * h,
        )
        path_chin.closeSubpath()
        self._path_chin = path_chin

        # ── 2. Extract Mandible Layer ─────────────────────────────────────────
        chin_img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        chin_img.fill(Qt.GlobalColor.transparent)
        p_chin = QPainter(chin_img)
        p_chin.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p_chin.setClipPath(path_chin)
        p_chin.drawImage(0, 0, base_img)
        p_chin.end()
        self._chin_img = chin_img

        # ── 3. Extract Skull Layer with Dark Mechanical Backing ───────────────
        skull_img = QImage(base_img)
        p_skull = QPainter(skull_img)
        p_skull.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p_skull.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p_skull.setClipPath(path_chin)
        p_skull.fillRect(0, 0, w, h, Qt.GlobalColor.transparent)
        p_skull.end()

        # Throat backing to prevent bleed when jaw drops
        throat_backing = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        throat_backing.fill(Qt.GlobalColor.transparent)
        p_tb = QPainter(throat_backing)
        p_tb.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p_tb.setClipPath(path_chin)
        p_tb.fillRect(0, 0, w, h, QColor(8, 10, 14, 255))
        p_tb.end()

        skull_final = QImage(throat_backing)
        p_sf = QPainter(skull_final)
        p_sf.drawImage(0, 0, skull_img)
        p_sf.end()
        self._skull_img = skull_final

        # ── 4. Extract Molten Red Neural Glow Mask ───────────────────────────
        # Isolates red/orange crevices & eyes so screen blending brightens only energy channels
        glow_mask = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        glow_mask.fill(Qt.GlobalColor.transparent)

        try:
            # Fast vectorized extraction via numpy
            img_format = base_img.format()
            if img_format != QImage.Format.Format_ARGB32_Premultiplied:
                conv = base_img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
            else:
                conv = base_img

            ptr = conv.bits()
            ptr.setsize(h * conv.bytesPerLine())
            arr = np.frombuffer(ptr, np.uint8).reshape((h, conv.bytesPerLine() // 4, 4))[:, :w, :]
            # QImage Format_ARGB32 is BGRA in memory on little-endian
            b = arr[:, :, 0].astype(np.float32)
            g = arr[:, :, 1].astype(np.float32)
            r = arr[:, :, 2].astype(np.float32)
            a = arr[:, :, 3].astype(np.float32)

            # Redness prominence over green/blue
            redness = np.clip(r - np.maximum(g, b) * 1.3, 0.0, 255.0)
            alpha = np.clip((redness - 15.0) / 65.0, 0.0, 1.0) * (a / 255.0) * 255.0

            glow_arr = np.zeros_like(arr)
            glow_arr[:, :, 0] = np.clip(b * 0.8, 0, 255).astype(np.uint8)
            glow_arr[:, :, 1] = np.clip(g * 1.2, 0, 255).astype(np.uint8)
            glow_arr[:, :, 2] = np.clip(r * 1.45, 0, 255).astype(np.uint8)
            glow_arr[:, :, 3] = alpha.astype(np.uint8)

            glow_mask = QImage(glow_arr.data, w, h, conv.bytesPerLine(), QImage.Format.Format_ARGB32_Premultiplied).copy()
        except Exception:
            # Fallback if numpy buffer conversion fails
            pass

        self._glow_mask = glow_mask

    def set_cursor(self, nx: float, ny: float, active: bool = True) -> None:
        """Update cursor tracking coordinate offsets in normalized [-1.0, 1.0] space."""
        if active:
            self._cursor_active = True
            self._cursor_x = _clamp(float(nx), -1.0, 1.0)
            self._cursor_y = _clamp(float(ny), -1.0, 1.0)
            self._cursor_timeout = 1.6  # seconds before smoothly returning to idle gaze if mouse halts
        else:
            self._cursor_active = False

    def glance(self, dx: float, dy: float, duration: float = 0.8, hold: float | None = None) -> None:
        """Deliberately orient Ultron's ocular sensors towards coordinate offsets."""
        self._tgt_gaze_x = _clamp(dx, -0.35, 0.35)
        self._tgt_gaze_y = _clamp(dy, -0.30, 0.30)
        self._gaze_timer = max(0.4, float(hold if hold is not None else duration))

    def step(self, dt: float, amp: float, speaking: bool = False,
             muted: bool = False, state: str = "IDLE",
             v_open: float = 0.0, v_wide: float = 0.0,
             v_level: float = 0.0, cursor_x: float | None = None,
             cursor_y: float | None = None, cursor_active: bool | None = None,
             **_kwargs) -> None:
        """Advance avatar 3D state by dt seconds with full 3D mechanical lip-sync and cursor tracking."""
        dt = max(1e-4, min(0.1, float(dt) if dt is not None else 0.016))
        self._t += dt
        self._speaking = bool(speaking)
        self._muted = bool(muted)
        self._state = (state or "IDLE").upper()

        if cursor_x is not None and cursor_y is not None:
            self.set_cursor(cursor_x, cursor_y, active=True if cursor_active is None else bool(cursor_active))
        elif cursor_active is False:
            self.set_cursor(0.0, 0.0, active=False)

        amp = float(amp) if amp is not None else 0.0
        v_open = float(v_open) if v_open is not None else 0.0
        v_wide = float(v_wide) if v_wide is not None else 0.0
        self._amp_raw = amp

        # Fast attack, natural exponential release for audio energy
        lerp_sp = 0.45 if amp > self._amp else 0.20
        self._amp += (amp - self._amp) * lerp_sp

        # ── Real-Time 3D Mandible Articulation Dynamics ───────────────────────
        raw_jaw = 0.0
        if self._speaking:
            if v_open > 0.02:
                # Direct phonetic viseme opening from live audio formants
                raw_jaw = _clamp(0.35 * v_open + 0.65 * max(v_open, amp * 1.35), 0.0, 1.0)
            else:
                # Syllabic cadence driven by audio energy
                syllable_cadence = 0.85 + 0.15 * math.sin(self._t * 22.0) * math.cos(self._t * 9.5)
                raw_jaw = _clamp(amp * 1.45 * syllable_cadence, 0.0, 1.0)
                # Rapid consonant snap-shut on momentary pauses (P, B, T, K, D, M)
                if amp < 0.04:
                    raw_jaw = 0.0
        else:
            raw_jaw = 0.0

        # Asymmetric exponential smoothing: fast opening attack, instant metallic closure
        if raw_jaw > self._jaw_open:
            tau = 0.022   # fast syllable opening attack (~22ms)
        elif self._speaking:
            tau = 0.012   # instant consonant closure (~12ms)
        else:
            tau = 0.055   # smooth return to resting pose
        rate = 1.0 - math.exp(-dt / tau)
        self._jaw_open += (raw_jaw - self._jaw_open) * rate

        # Vocal aperture width modulation (vowel spread vs round)
        tgt_wide = _clamp(v_wide if v_wide else 0.0, -0.6, 0.8)
        self._jaw_wide += (tgt_wide - self._jaw_wide) * (1.0 - math.exp(-dt / 0.035))

        # Vocal plasma flare intensity surging with jaw opening and audio energy
        tgt_flare = max(self._jaw_open, amp * 1.35 if self._speaking else 0.0)
        self._vocal_flare += (tgt_flare - self._vocal_flare) * 0.35

        # 3D Speech Nod: head tilts slightly in pitch on emphasized syllables
        if self._speaking:
            self._speech_nod = -math.sin(self._t * 16.0) * (self._amp * 0.024)
        else:
            self._speech_nod += (0.0 - self._speech_nod) * 0.18

        # 3D Sway & Perspective Parallax
        b_speed = 1.8 if self._speaking else (1.2 if self._state == "LISTENING" else 0.9)
        self._breath += dt * b_speed
        self._sway_phase += dt * 0.75

        # ── Cursor Tracking & 3D Pose Target Calculation ─────────────────────
        if self._cursor_active:
            self._cursor_timeout -= dt
            if self._cursor_timeout <= 0:
                self._cursor_active = False

        if self._cursor_active:
            # 3D Head Orientation smoothly yaws and pitches towards cursor
            tgt_yaw = self._cursor_x * 0.14
            tgt_pitch = self._cursor_y * 0.10 + (self._speech_nod if self._speaking else 0.0)
            # Eyes track with greater responsiveness and deflection towards cursor
            tgt_gaze_x = self._cursor_x * 0.85
            tgt_gaze_y = self._cursor_y * 0.70

            # Menacing tactical reaction: squint slightly when cursor gets right in his face
            dist_to_face = math.hypot(self._cursor_x, self._cursor_y)
            if dist_to_face < 0.25:
                self._tgt_shutter = 0.65
            elif self._state in ("THINKING", "PROCESSING"):
                self._tgt_shutter = 0.55
            elif self._speaking:
                self._tgt_shutter = 0.88 + 0.12 * math.sin(self._breath * 3.0)
            elif self._muted:
                self._tgt_shutter = 0.25
            else:
                self._tgt_shutter = 0.95
        else:
            # Autonomous idle sway & micro-saccades when cursor is inactive
            if self._state in ("THINKING", "PROCESSING"):
                tgt_yaw = 0.07 * math.sin(self._sway_phase)
                tgt_pitch = -0.05 + 0.02 * math.cos(self._breath)
                self._tgt_shutter = 0.55   # menacing concentrated squint
            elif self._speaking:
                tgt_yaw = 0.035 * math.sin(self._sway_phase * 1.4)
                tgt_pitch = self._speech_nod
                self._tgt_shutter = 0.88 + 0.12 * math.sin(self._breath * 3.0) - (0.15 * self._vocal_flare)
            elif self._state == "LISTENING":
                tgt_yaw = 0.0
                tgt_pitch = 0.02
                self._tgt_shutter = 1.05   # attentive wide sensor aperture
            elif self._muted:
                tgt_yaw = 0.0
                tgt_pitch = 0.06
                self._tgt_shutter = 0.25   # low-power dormant sensor
            else:
                tgt_yaw = 0.025 * math.sin(self._sway_phase)
                tgt_pitch = 0.015 * math.cos(self._breath)
                self._tgt_shutter = 0.90 + 0.10 * math.sin(self._breath)

            # Saccadic eye tracking
            self._gaze_timer -= dt
            if self._gaze_timer <= 0:
                self._gaze_timer = random.uniform(1.2, 3.5)
                self._tgt_gaze_x = random.uniform(-0.15, 0.15)
                self._tgt_gaze_y = random.uniform(-0.10, 0.10)
            tgt_gaze_x = self._tgt_gaze_x
            tgt_gaze_y = self._tgt_gaze_y

        # Exponential smoothing: head has mechanical inertia (~80ms), eyes track fast (~45ms)
        rate_head = 1.0 - math.exp(-dt / 0.08)
        rate_eyes = 1.0 - math.exp(-dt / 0.045)
        self._yaw += (tgt_yaw - self._yaw) * rate_head
        self._pitch += (tgt_pitch - self._pitch) * rate_head
        self._gaze_x += (tgt_gaze_x - self._gaze_x) * rate_eyes
        self._gaze_y += (tgt_gaze_y - self._gaze_y) * rate_eyes
        self._shutter += (self._tgt_shutter - self._shutter) * 0.18

        # Telemetry HUD rotation & scanline sweep
        hud_speed = 36.0 if self._speaking else (55.0 if self._state in ("THINKING", "PROCESSING") else 18.0)
        self._hud_angle = (self._hud_angle + dt * hud_speed) % 360.0
        self._scan_y = (self._scan_y + dt * 0.45) % 1.0

        # Neural energy pulse propagation
        eng_speed = 4.5 if self._state in ("THINKING", "PROCESSING") else (3.2 if self._speaking else 1.5)
        self._energy_phase = (self._energy_phase + dt * eng_speed) % (2.0 * math.pi)

    def paint(self, p: QPainter, cx: float, cy: float, r: float,
              primary: QColor, accent: QColor, bg: QColor | None = None) -> None:
        """Render the complete authentic Ultron Prime avatar at (cx, cy) with radius r."""
        if r <= 10:
            return

        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Ultron Crimson & Tactical Palette
        red_core = QColor(255, 31, 67)       # Vibrant Ultron crimson
        red_bright = QColor(255, 80, 100)    # Hot neon scarlet
        red_dim = QColor(140, 16, 36)        # Deep shadow red
        gold_proc = QColor(255, 170, 34)     # Processing amber

        if self._muted:
            red_core = QColor(100, 70, 80)
            red_bright = QColor(140, 90, 100)
            red_dim = QColor(60, 40, 48)
        elif self._state in ("THINKING", "PROCESSING"):
            red_core = gold_proc
            red_bright = QColor(255, 210, 80)
            red_dim = QColor(160, 90, 16)

        amp = self._amp

        # ── 1. Atmosphere / Radial Backlight Aura ─────────────────────────────
        ar = r * 1.35
        g_aura = QRadialGradient(cx, cy - r * 0.05, ar)
        a0 = int(_clamp(32 + 45 * amp + (30 if self._speaking else 0), 10, 110))
        if self._muted:
            a0 = 12
        g_aura.setColorAt(0.00, QColor(red_core.red(), red_core.green(), red_core.blue(), a0))
        g_aura.setColorAt(0.50, QColor(red_dim.red(), red_dim.green(), red_dim.blue(), int(a0 * 0.35)))
        g_aura.setColorAt(1.00, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(g_aura))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - ar, cy - r * 0.05 - ar, ar * 2, ar * 2))

        # ── 2. Holographic HUD Rings & Telemetry ──────────────────────────────
        self._paint_hud_rings(p, cx, cy, r, red_core, red_dim, amp)

        # ── 3. Head Dimensions & Caching ──────────────────────────────────────
        head_w = r * 1.85
        head_h = head_w * (530.0 / 474.0)
        target_w = max(16, int(head_w))
        target_h = max(16, int(head_h))

        if self._cache_key != (target_w, target_h):
            self._cached_skull = QPixmap.fromImage(self._skull_img).scaled(
                target_w, target_h,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._cached_chin = QPixmap.fromImage(self._chin_img).scaled(
                target_w, target_h,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._cached_glow = QPixmap.fromImage(self._glow_mask).scaled(
                target_w, target_h,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._cache_key = (target_w, target_h)

        # 3D Head placement with parallax and speech nod
        px = cx + self._yaw * (r * 0.18)
        py = cy - head_h * 0.44 + self._pitch * (r * 0.15) + (self._speech_nod * r * 0.12)
        head_rect = QRectF(px - head_w / 2.0, py, head_w, head_h)

        # ── 4. Render Base Skull Layer ────────────────────────────────────────
        if self._cached_skull is not None:
            p.drawPixmap(head_rect.topLeft(), self._cached_skull)

        # ── 5. Additive Molten Crevices & Neural Glow Pulse ───────────────────
        if self._cached_glow is not None:
            p.save()
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
            pulse = 0.5 + 0.5 * math.sin(self._energy_phase * 2.0)
            if self._muted:
                glow_opacity = 0.08
            elif self._state in ("THINKING", "PROCESSING"):
                glow_opacity = 0.35 + 0.45 * pulse
            elif self._speaking:
                glow_opacity = 0.25 + 0.55 * amp + 0.20 * pulse
            else:
                glow_opacity = 0.15 + 0.15 * pulse
            p.setOpacity(_clamp(glow_opacity, 0.0, 1.0))
            p.drawPixmap(head_rect.topLeft(), self._cached_glow)
            p.restore()

        # ── 6. Internal 3D Throat Cavity & Vocal Reactor ──────────────────────
        jaw_drop = self._jaw_open * (head_rect.height() * 0.034)
        if self._jaw_open > 0.005:
            mcx = head_rect.x() + head_rect.width() * (274.0 / 474.0)
            mcy = head_rect.y() + head_rect.height() * (272.5 / 530.0)
            ap_w = head_rect.width() * (0.155 + 0.02 * self._jaw_wide)
            ap_h = jaw_drop + head_rect.height() * 0.004

            p.save()
            p.translate(mcx, mcy + jaw_drop * 0.48)

            # A. Dark internal throat cavity
            p.setBrush(QBrush(QColor(4, 2, 6, 255)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(-ap_w * 0.5, -ap_h * 0.5, ap_w, ap_h))

            # B. Glowing crimson vocal furnace
            flare = self._vocal_flare
            g_core = QRadialGradient(0, 0, ap_w * 0.45)
            a_furnace = int(_clamp(220 * flare, 0, 255))
            if self._muted:
                a_furnace = 20
            g_core.setColorAt(0.00, QColor(255, 130, 90, a_furnace))
            g_core.setColorAt(0.45, QColor(red_core.red(), red_core.green(), red_core.blue(), int(a_furnace * 0.8)))
            g_core.setColorAt(1.00, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(g_core))
            p.drawEllipse(QRectF(-ap_w * 0.5, -ap_h * 0.7, ap_w, ap_h * 1.4))

            # C. Titanium grill slats / mechanical teeth
            slat_a = int(_clamp(210 * flare + 40, 40, 255))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(235, 245, 255, slat_a), 1.2))
            num_slats = 7
            for i in range(num_slats):
                t = i / (num_slats - 1)
                sx = -ap_w * 0.38 + ap_w * 0.76 * t
                factor = 1.0 - 0.32 * abs(t - 0.5) / 0.5
                sh = ap_h * 0.85 * factor
                p.drawLine(QLineF(sx, -sh / 2.0, sx, sh / 2.0))

            # D. Horizontal anamorphic vocal laser flare
            if flare > 0.12 and not self._muted:
                beam_w = ap_w * (0.95 + 0.4 * flare)
                beam_h = max(1.5, ap_h * 0.22)
                g_beam = QLinearGradient(-beam_w, 0, beam_w, 0)
                a_beam = int(_clamp(220 * flare, 0, 240))
                g_beam.setColorAt(0.00, QColor(red_core.red(), red_core.green(), red_core.blue(), 0))
                g_beam.setColorAt(0.35, QColor(255, 75, 70, int(a_beam * 0.6)))
                g_beam.setColorAt(0.50, QColor(255, 255, 255, a_beam))
                g_beam.setColorAt(0.65, QColor(255, 75, 70, int(a_beam * 0.6)))
                g_beam.setColorAt(1.00, QColor(red_core.red(), red_core.green(), red_core.blue(), 0))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(g_beam))
                p.drawRect(QRectF(-beam_w, -beam_h / 2.0, beam_w * 2, beam_h))

            p.restore()

        # ── 7. Articulated Mandible (Chin) Layer ───────────────────────────────
        if self._cached_chin is not None:
            # Drop jaw along jawline vector with subtle horizontal wide spread & foreground parallax
            chin_x = head_rect.x() + self._yaw * (head_rect.width() * 0.02)
            chin_y = head_rect.y() + jaw_drop + self._pitch * (head_rect.height() * 0.015)
            p.drawPixmap(QPointF(chin_x, chin_y), self._cached_chin)

        # ── 8. Piercing Ocular Sensors (Eyes) ─────────────────────────────────
        self._paint_eyes(p, head_rect, red_core, amp)

        # ── 9. Tactical HUD Reticle & Corner Brackets ─────────────────────────
        self._paint_tactical_hud(p, cx, cy, r, red_core)

        p.restore()

    def _paint_eyes(self, p: QPainter, head_rect: QRectF, red: QColor, amp: float) -> None:
        """Render high-intensity concentric ocular glints aligned with authentic Ultron eyes."""
        shutter = self._shutter
        if self._state in ("THINKING", "PROCESSING"):
            base_int = 1.15 + 0.35 * math.sin(self._energy_phase * 4.0)
        elif self._speaking:
            base_int = 1.05 + 0.55 * self._vocal_flare
        elif self._muted:
            base_int = 0.20
        else:
            base_int = 0.75 + 0.25 * math.sin(self._breath * 1.2)

        intensity = _clamp(base_int, 0.15, 1.8)

        # Accurate eye landmark coordinates in reference space (474x530)
        for (ex_norm, ey_norm, slant) in [
            (224.0 / 474.0, 150.0 / 530.0, -10.0),
            (324.0 / 474.0, 158.0 / 530.0, 10.0),
        ]:
            ex = head_rect.x() + head_rect.width() * ex_norm + self._gaze_x * (head_rect.width() * 0.018)
            ey = head_rect.y() + head_rect.height() * ey_norm + self._gaze_y * (head_rect.height() * 0.014)

            p.save()
            p.translate(ex, ey)
            p.rotate(slant)

            # Volumetric pupil flare
            flare_r = head_rect.width() * 0.038 * intensity
            g_eye = QRadialGradient(0, 0, flare_r)
            a_glow = int(_clamp(135 * intensity, 0, 200))
            if self._muted:
                a_glow = 25
            g_eye.setColorAt(0.00, QColor(255, 120, 90, a_glow))
            g_eye.setColorAt(0.40, QColor(red.red(), red.green(), red.blue(), int(a_glow * 0.45)))
            g_eye.setColorAt(1.00, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(g_eye))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(-flare_r, -flare_r * shutter, flare_r * 2, flare_r * 2 * shutter))

            # Laser core glint
            if not self._muted:
                core_r = max(1.5, head_rect.width() * 0.012)
                p.setBrush(QBrush(QColor(255, 245, 240, int(_clamp(230 * intensity, 60, 255)))))
                p.drawEllipse(QRectF(-core_r, -core_r * shutter, core_r * 2, core_r * 2 * shutter))

            p.restore()

    def _paint_hud_rings(self, p: QPainter, cx: float, cy: float, r: float,
                         red: QColor, red_dim: QColor, amp: float) -> None:
        """Draw concentric futuristic HUD telemetry dials, azimuth ring, and audio arcs."""
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Outer Azimuth Ring
        r_outer = r * 1.15
        p.setPen(QPen(QColor(red_dim.red(), red_dim.green(), red_dim.blue(), 65), 1.0))
        p.drawEllipse(QRectF(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2))

        # Azimuth tick marks every 15°
        p.setPen(QPen(QColor(red.red(), red.green(), red.blue(), 80), 1.0))
        for deg in range(0, 360, 15):
            rad = math.radians(deg)
            t_len = 5.0 if deg % 90 == 0 else (3.0 if deg % 45 == 0 else 1.5)
            x1 = cx + (r_outer - t_len) * math.cos(rad)
            y1 = cy + (r_outer - t_len) * math.sin(rad)
            x2 = cx + r_outer * math.cos(rad)
            y2 = cy + r_outer * math.sin(rad)
            p.drawLine(QLineF(x1, y1, x2, y2))

        # Counter-rotating Sector HUD Arcs
        r_mid = r * 1.05
        p.save()
        p.translate(cx, cy)
        p.rotate(self._hud_angle)
        pen_arc = QPen(QColor(red.red(), red.green(), red.blue(), 130), 1.6)
        p.setPen(pen_arc)
        for ang in (0, 120, 240):
            p.drawArc(QRectF(-r_mid, -r_mid, r_mid * 2, r_mid * 2), int((ang + 10) * 16), int(45 * 16))
        p.restore()

        # Inner Audio Reactive Reticle
        r_in = r * 0.94
        p.save()
        p.translate(cx, cy)
        p.rotate(-self._hud_angle * 1.4)
        a_in = int(_clamp(60 + 130 * amp, 30, 220))
        p.setPen(QPen(QColor(red.red(), red.green(), red.blue(), a_in), 1.0, Qt.PenStyle.DashLine))
        p.drawEllipse(QRectF(-r_in, -r_in, r_in * 2, r_in * 2))
        p.restore()

    def _paint_tactical_hud(self, p: QPainter, cx: float, cy: float,
                            r: float, red: QColor) -> None:
        """Render high-tech cybernetic corner brackets, targeting markers, and scanlines."""
        p.setBrush(Qt.BrushStyle.NoBrush)
        pen_b = QPen(QColor(red.red(), red.green(), red.blue(), 120), 1.2)
        p.setPen(pen_b)

        # Tactical Corner Brackets framing the avatar
        bw = r * 0.88
        bh = r * 0.82
        c_len = 16.0

        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            bx = cx + sx * bw
            by = cy + sy * bh
            p.drawLine(QLineF(bx, by, bx - sx * c_len, by))
            p.drawLine(QLineF(bx, by, bx, by - sy * c_len))
            p.fillRect(QRectF(bx - sx * 4 - 1, by - sy * 4 - 1, 2, 2),
                       QColor(red.red(), red.green(), red.blue(), 180))

        # Subtle Sweeping Holographic Scanline
        scan_py = (cy - bh) + self._scan_y * (bh * 2)
        g_scan = QLinearGradient(cx - bw, scan_py, cx + bw, scan_py)
        g_scan.setColorAt(0.00, QColor(red.red(), red.green(), red.blue(), 0))
        g_scan.setColorAt(0.50, QColor(red.red(), red.green(), red.blue(), 40))
        g_scan.setColorAt(1.00, QColor(red.red(), red.green(), red.blue(), 0))
        p.setPen(QPen(QBrush(g_scan), 1.0))
        p.drawLine(QLineF(cx - bw * 0.9, scan_py, cx + bw * 0.9, scan_py))

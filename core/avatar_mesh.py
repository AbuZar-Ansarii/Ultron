"""
Human head mesh for the HUD avatar.

The face is **real measured human geometry** — MediaPipe's canonical face model
(`core/face_model.obj`, Apache-2.0, 468 vertices / 898 triangles), which carries
actual eyelids, nostrils, lips and cheekbones. Everything a formula cannot give
you comes from there.

Earlier revisions of this file generated the whole head procedurally from an
ellipsoid pushed around by gaussians. It could be tuned endlessly and still read
as an egg with a face drawn on it, because there was no human anatomy in it —
only smooth blobs. Real topology fixed in one step what parameter tweaking could
not fix at all.

What is still generated here, around that face:
  * the cranium — the model is an open mask, so its 36-vertex border is swept
    back and up over a skull-shaped ellipsoid and closed at the occiput;
  * a tapering neck stub that fades out instead of needing shoulders;
  * vertex normals, jaw-rig weights, a thinned wireframe, and the landmark
    index rings (eyes, brows, lips) the renderer animates.

Coordinate system after normalisation (head-local, right-handed):
    +x → viewer's right      +y → up      +z → out of the face
    y = +1.0 crown,  y = -1.0 chin,  eyes land on y ≈ 0.
"""

from __future__ import annotations

import collections
from pathlib import Path

import numpy as np

_OBJ = Path(__file__).resolve().parent / "face_model.obj"

# Cranium shape, in the model's own units (chin ≈ -9.4, forehead ≈ +8.3).
# Tuned so that brow→crown is ~0.36 of the head's height, which is the real
# proportion; a taller cranium than that immediately reads as a long face even
# though the face itself is untouched measured geometry.
_SKULL_C = (0.0, 2.0, -1.0)      # centre of the cranial ellipsoid
_SKULL_R = (8.4, 12.4, 8.2)      # its radii
_SKULL_POLE = (0.0, 0.42, -1.0)  # direction of the occiput, where the sweep closes
_SKULL_RINGS = 6
_SKULL_BLEND = 1.7               # how fast the sweep leaves the face border
_SKULL_BULGE = 1.04

_NECK_RINGS, _NECK_SEGS = 9, 14
_NECK_Z = -1.6                   # the neck tube's axis, in model units
_WIRE_STRIDE = 3                 # keep every n-th edge; the surface carries the form

# MediaPipe landmark rings. Verified against the geometry at build time — see
# `_check_landmarks` — so a wrong index can never silently animate the cheek.
LANDMARKS: dict[str, list[int]] = {
    "eye_l":  [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159,
               160, 161, 246],
    "eye_r":  [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386,
               387, 388, 466],
    "brow_l": [70, 63, 105, 66, 107],
    "brow_r": [300, 293, 334, 296, 336],
    "lips_out": [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270,
                 269, 267, 0, 37, 39, 40, 185],
    "lips_in": [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310,
                311, 312, 13, 82, 81, 80, 191],
}

# Jaw rig, in normalised units. The pivot sits between the ears, which is where
# a real mandible hinges.
JAW_PIVOT = (0.0, 0.06, -0.34)
JAW_MAX = 0.115                  # radians of drop at full amplitude (~6.6°)
#   Speech barely moves a real jaw, and a talking head is watched at HUD size
#   where a small, precise mouth reads better than a large one. The lip rig
#   (spread / round) now carries most of the articulation, so the jaw does not
#   have to swing to show that something is being said.


def _load_obj(path: Path):
    verts, faces = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            verts.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:4]])
    return np.array(verts, dtype=np.float64), np.array(faces, dtype=np.int64)


def _boundary_loop(faces: np.ndarray) -> np.ndarray:
    """Ordered ring of vertices along the open border of a triangle mesh."""
    seen = collections.Counter()
    for a, b, c in faces:
        for e in ((a, b), (b, c), (c, a)):
            seen[(min(e), max(e))] += 1
    border = [e for e, n in seen.items() if n == 1]

    adj = collections.defaultdict(list)
    for a, b in border:
        adj[a].append(b)
        adj[b].append(a)

    start = border[0][0]
    loop, prev, cur = [start], None, start
    while True:
        nxt = [v for v in adj[cur] if v != prev]
        if not nxt or nxt[0] == start:
            break
        prev, cur = cur, nxt[0]
        loop.append(cur)
    return np.array(loop)


def _slerp(a: np.ndarray, b: np.ndarray, t):
    dot = np.clip((a * b).sum(-1, keepdims=True), -1.0, 1.0)
    om = np.arccos(dot)
    so = np.sin(om)
    safe = np.where(so < 1e-6, 1.0, so)
    out = np.where(so < 1e-6, a * (1 - t) + b * t,
                   (np.sin((1 - t) * om) / safe) * a + (np.sin(t * om) / safe) * b)
    return out / np.maximum(np.linalg.norm(out, axis=-1, keepdims=True), 1e-9)


def _add_cranium(verts: np.ndarray, faces: np.ndarray):
    """Sweep the mask's open border back over a skull and close it at the occiput."""
    loop = _boundary_loop(faces)

    # Orient the loop so the generated triangles wind the same way as the face's.
    centre2d = verts[loop, :2].mean(0)
    ang = np.arctan2(verts[loop, 1] - centre2d[1], verts[loop, 0] - centre2d[0])
    if np.diff(np.unwrap(ang)).sum() < 0:
        loop = loop[::-1]

    n = len(loop)
    C = np.array(_SKULL_C)
    R = np.array(_SKULL_R)
    pole = np.array(_SKULL_POLE)
    pole = pole / np.linalg.norm(pole)
    chin_y = verts[:, 1].min()

    rim = verts[loop] - C
    rim_r = np.linalg.norm(rim, axis=1, keepdims=True)
    rim_d = rim / rim_r

    def ell_r(d):
        return 1.0 / np.sqrt(((d / R) ** 2).sum(-1, keepdims=True))

    out_v = [verts]
    out_f = list(faces)
    prev_idx = loop
    ts = np.linspace(0.0, 1.0, _SKULL_RINGS + 1)[1:]

    for t in ts:
        d = _slerp(pole, rim_d, 1.0 - t)
        w = (1.0 - t) ** _SKULL_BLEND          # meets the rim exactly at t = 0
        # A skull is fuller than the border it springs from; peak it mid-sweep.
        r = ell_r(d) * (1.0 + (_SKULL_BULGE - 1.0) * np.sin(np.pi * t) ** 0.8)
        ring = C + d * (w * rim_r + (1.0 - w) * r)
        # Never dip below the chin: the sweep passing under the jaw would
        # otherwise hang a lip of geometry below the face. Vertices that hit
        # the clamp are also drawn in towards the neck axis, so the underside
        # closes as a small floor instead of a flat skirt sticking out.
        below = ring[:, 1] < chin_y
        if below.any():
            ring[below, 1] = chin_y
            ring[below, 0] *= 0.55
            ring[below, 2] = _NECK_Z + (ring[below, 2] - _NECK_Z) * 0.55
        if t == ts[-1]:
            ring = np.repeat((C + pole * ell_r(pole[None])[0])[None], n, axis=0)

        base = sum(len(a) for a in out_v)
        out_v.append(ring)
        idx = np.arange(base, base + n)
        for i in range(n):
            a0, b0 = prev_idx[i], prev_idx[(i + 1) % n]
            a1, b1 = idx[i], idx[(i + 1) % n]
            out_f.append([a0, a1, b1])
            out_f.append([a0, b1, b0])
        prev_idx = idx

    return np.vstack(out_v), np.array(out_f, dtype=np.int64)


def _add_neck(verts: np.ndarray, faces: np.ndarray):
    """A tapering tube dropped from inside the jaw; it fades out, so no shoulders."""
    ph = np.linspace(0.0, 2.0 * np.pi, _NECK_SEGS, endpoint=False)
    # Short, and flaring hard at the bottom: a straight vertical tube reads as
    # a pedestal, whereas a neck that widens into the top of the shoulders
    # reads as a bust — and the shorter it is, the larger the head can be drawn
    # in the same HUD band.
    ys = np.linspace(-5.5, -13.0, _NECK_RINGS)
    d = (ys + 5.5) / -7.5

    rx = 4.6 * (1.0 + 0.52 * d ** 1.9)
    rz = 4.1 * (1.0 + 0.38 * d ** 1.9)
    nx = rx[:, None] * np.cos(ph)[None, :]
    nz = _NECK_Z + rz[:, None] * np.sin(ph)[None, :]
    ny = ys[:, None] * np.ones_like(ph)[None, :]

    nv = np.stack([nx.ravel(), ny.ravel(), nz.ravel()], axis=1)
    base = len(verts)
    idx = base + np.arange(_NECK_RINGS * _NECK_SEGS).reshape(_NECK_RINGS, _NECK_SEGS)

    nf = []
    for i in range(_NECK_RINGS - 1):
        for j in range(_NECK_SEGS):
            a, b = idx[i, j], idx[i, (j + 1) % _NECK_SEGS]
            c, e = idx[i + 1, (j + 1) % _NECK_SEGS], idx[i + 1, j]
            nf.append([a, b, c])
            nf.append([a, c, e])

    # Enough rings that the fade steps stay small. Each quad splits into one
    # triangle with two top vertices and one with two bottom vertices, so a
    # steep per-vertex fade gradient makes the pair land on visibly different
    # brightnesses and the neck grows a sawtooth edge.
    fade = np.ones(base)
    nd = np.repeat(d, _NECK_SEGS)
    fade = np.concatenate([fade, 1.0 - 0.72 * np.clip(nd, 0.0, 1.0) ** 1.5])
    return np.vstack([verts, nv]), np.vstack([faces, np.array(nf)]), fade


def _vertex_normals(verts: np.ndarray, faces: np.ndarray,
                    outward: np.ndarray) -> np.ndarray:
    """Area-weighted vertex normals, flipped to agree with `outward`.

    `outward` must be a per-vertex direction that genuinely points out of the
    surface. A single "away from the mesh centroid" rule is NOT good enough:
    down at the base of the neck that vector points almost straight down while
    the real normal is horizontal, so the dot product hovers around zero and
    the sign flips at random — which tears the neck into an asymmetric slab of
    half-culled, half-lit triangles.
    """
    a, b, c = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    fn = np.cross(b - a, c - a)          # length carries the area — the weighting

    n = np.zeros_like(verts)
    for k in range(3):
        np.add.at(n, faces[:, k], fn)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)

    flip = (n * outward).sum(1) < 0
    n[flip] *= -1.0
    return n


def _unique_edges(faces: np.ndarray) -> np.ndarray:
    e = np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    e = np.sort(e, axis=1)
    return np.unique(e, axis=0)


def _check_landmarks(verts: np.ndarray) -> None:
    """Fail loudly at build time if a landmark ring is not where it should be."""
    for left, right in (("eye_l", "eye_r"), ("brow_l", "brow_r")):
        cl = verts[LANDMARKS[left]].mean(0)
        cr = verts[LANDMARKS[right]].mean(0)
        assert cl[0] < 0 < cr[0], f"{left}/{right} are not on opposite sides"
        assert abs(cl[1] - cr[1]) < 0.5, f"{left}/{right} are at different heights"
    eye_y = verts[LANDMARKS["eye_l"]].mean(0)[1]
    brow_y = verts[LANDMARKS["brow_l"]].mean(0)[1]
    lips = verts[LANDMARKS["lips_out"]].mean(0)
    assert brow_y > eye_y, "brow is not above the eye"
    assert lips[1] < eye_y, "lips are not below the eyes"
    assert abs(lips[0]) < 0.5, "lips are not centred"


def build_head() -> dict:
    """Assemble the full head. Called once; `get_head_mesh()` caches the result."""
    verts, faces = _load_obj(_OBJ)
    _check_landmarks(verts)

    n_face = len(verts)
    verts, faces = _add_cranium(verts, faces)
    n_head = len(verts)
    verts, faces, fade = _add_neck(verts, faces)

    # ── normalise: crown → +1, chin → -1, eyes land on y ≈ 0 ────────────────
    head_y = verts[:n_head, 1]
    crown, chin = head_y.max(), head_y.min()
    scale = 2.0 / (crown - chin)
    centre = np.array([0.0, (crown + chin) * 0.5, 0.0])
    verts = (verts - centre) * scale

    # Outward reference, per part: the head is star-shaped about its own centre,
    # while the neck is a tube whose outward direction is radial in x/z only.
    outward = verts - np.array([0.0, verts[:n_head, 1].mean(), 0.0])
    outward[n_head:] = verts[n_head:] - np.array([0.0, 0.0, _NECK_Z * scale])
    outward[n_head:, 1] = 0.0
    normals = _vertex_normals(verts, faces, outward)

    # ── jaw rig ─────────────────────────────────────────────────────────────
    # Everything below the mouth swings on the mandible, tapering to nothing at
    # the ears and around the back so the nape and the neck stay put.
    mouth_y = verts[LANDMARKS["lips_out"], 1].mean()
    chin_y = verts[:n_head, 1].min()
    jaw = np.clip((mouth_y - verts[:, 1]) / (mouth_y - chin_y), 0.0, 1.0) ** 0.8
    jaw *= np.clip(0.30 + 0.85 * (verts[:, 2] / 0.55), 0.0, 1.0)
    jaw[n_head:] = 0.0                                  # the neck never moves
    jaw[LANDMARKS["lips_in"][:10]] = 1.0                # lower inner lip leads
    jaw[LANDMARKS["lips_out"][:10]] = 0.95

    # ── brow rig ────────────────────────────────────────────────────────────
    # Raising the brows displaces the actual surface rather than sliding a drawn
    # line over it, so the brow ridge relights as it lifts.
    brow_y = verts[LANDMARKS["brow_l"] + LANDMARKS["brow_r"], 1].mean()
    brow = np.exp(-((verts[:, 1] - brow_y) / 0.115) ** 2)
    brow *= np.clip(verts[:, 2] / 0.35, 0.0, 1.0)       # front of the face only
    brow *= np.exp(-(verts[:, 0] / 0.42) ** 2)          # fades out past the temples
    brow[n_head:] = 0.0

    # ── lip rig ─────────────────────────────────────────────────────────────
    # Vowels are not just "how far open" — /i/ spreads the lips wide, /u/ purses
    # them forward. This weight lets the renderer widen or round the mouth
    # region as a whole, so the surrounding skin follows instead of tearing away
    # from the landmark rings.
    lip_c = verts[LANDMARKS["lips_out"]].mean(axis=0)
    lips = np.exp(-((verts[:, 1] - lip_c[1]) / 0.155) ** 2)
    lips *= np.exp(-(verts[:, 0] / 0.30) ** 2)
    lips *= np.clip(verts[:, 2] / 0.40, 0.0, 1.0)
    lips[n_head:] = 0.0

    edges = _unique_edges(faces)[::_WIRE_STRIDE]

    # Neck and head interpenetrate, and a painter's-algorithm sort by triangle
    # depth interleaves them into a torn edge. Grouping fixes it: the neck is
    # always behind the head where they overlap, so draw every neck facet first.
    face_group = (faces >= n_head).all(axis=1).astype(np.int32)   # 1 = neck

    return {
        "face_group": np.ascontiguousarray(1 - face_group, dtype=np.float32),
        "brow": np.ascontiguousarray(brow, dtype=np.float32),
        "lips": np.ascontiguousarray(lips, dtype=np.float32),
        "lip_centre": np.ascontiguousarray(lip_c, dtype=np.float32),
        "verts": np.ascontiguousarray(verts, dtype=np.float32),
        "normals": np.ascontiguousarray(normals, dtype=np.float32),
        "faces": np.ascontiguousarray(faces, dtype=np.int32),
        "edges": np.ascontiguousarray(edges, dtype=np.int32),
        "jaw": np.ascontiguousarray(jaw, dtype=np.float32),
        "fade": np.ascontiguousarray(fade, dtype=np.float32),
        "landmarks": {k: np.array(v, dtype=np.int32) for k, v in LANDMARKS.items()},
        "n_face": n_face,
        "n_head": n_head,
        "span": (1.0, float(verts[:, 1].min())),        # crown, bottom of the neck
    }


_CACHE: dict | None = None


def get_head_mesh() -> dict:
    """Process-wide cached mesh — every HudCanvas shares the same arrays."""
    global _CACHE
    if _CACHE is None:
        _CACHE = build_head()
    return _CACHE

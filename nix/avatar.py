from __future__ import annotations

import hashlib
import random
import time

from rich.text import Text

BG = "#050505"

PALETTES = {
    "mint": {
        "hi": "#8ef0b4", "lo": "#2f9d6e", "belly": "#d9ffe9",
        "cheek": "#ffb3b3", "accent": "#eaffc9", "outline": "#1d5c44",
    },
    "sky": {
        "hi": "#8fd6ff", "lo": "#3a7bd6", "belly": "#dff2ff",
        "cheek": "#ffc2c2", "accent": "#ffffff", "outline": "#1f5a8a",
    },
    "grape": {
        "hi": "#c9a6ff", "lo": "#7c4fd0", "belly": "#efe2ff",
        "cheek": "#ffb3d6", "accent": "#ffe4ff", "outline": "#4a2f7a",
    },
    "rose": {
        "hi": "#ffb3d9", "lo": "#d654a6", "belly": "#ffe4f2",
        "cheek": "#ff8a8a", "accent": "#fff0f7", "outline": "#7a2f5a",
    },
    "slate": {
        "hi": "#b9c4d9", "lo": "#5a6b8f", "belly": "#e8eef7",
        "cheek": "#ffb3b3", "accent": "#cfe4ff", "outline": "#3a4660",
    },
    "acid": {
        "hi": "#c9f56f", "lo": "#6aa520", "belly": "#e9ffb8",
        "cheek": "#ffb3b3", "accent": "#f6ffd0", "outline": "#3d6b12",
    },
    "pink": {
        "hi": "#ffc2e6", "lo": "#d65fa8", "belly": "#ffe9f6",
        "cheek": "#ff8ab4", "accent": "#fff0fa", "outline": "#7a2f5e",
    },
    "slime": {
        "hi": "#7fe8d9", "lo": "#2a9c8f", "belly": "#d0fbf3",
        "cheek": "#ffb3a6", "accent": "#e6fffb", "outline": "#176a60",
    },
}

# --- easter-egg / signature palettes -------------------------------

# The Orange Octopus - a nod to Claude Code's mascot.
OCTOPUS_PAL = {
    "hi": "#ffad5c", "lo": "#e0551c", "belly": "#ffe3b8",
    "cheek": "#ff7f4f", "accent": "#fff3d6", "outline": "#8a2b06",
}

# A cheerful orange one-eyed alien.
CYCLOPS_PAL = {
    "hi": "#ffb84d", "lo": "#e86f1f", "belly": "#ffe8ad",
    "cheek": "#ff7f4f", "accent": "#fff3c9", "outline": "#8a4506",
}

# Pou - the beige "piece of dough" virtual pet with stretched eyes.
POU_PAL = {
    "hi": "#e0b386", "lo": "#a97a45", "belly": "#f5e3c0",
    "cheek": "#ff9b7a", "accent": "#fff3d0", "outline": "#6b4a1f",
}

# My Pet Alien (Tommy) - warm brown round alien with big white eyes.
TOMMY_PAL = {
    "hi": "#d99a63", "lo": "#96602e", "belly": "#f2d6b2",
    "cheek": "#ff8a6b", "accent": "#ffe9c8", "outline": "#5e3a18",
}

# Mint-green slime.
SLIME_PAL = {
    "hi": "#7fe8d9", "lo": "#2a9c8f", "belly": "#d0fbf3",
    "cheek": "#ffb3a6", "accent": "#e6fffb", "outline": "#176a60",
}

# Lavender antenna alien.
ANTENNA_PAL = {
    "hi": "#c9a6ff", "lo": "#8a5fd6", "belly": "#efe2ff",
    "cheek": "#ffb3d6", "accent": "#ffe4ff", "outline": "#4a2f7a",
}

# Crimson cone.
CONE_PAL = {
    "hi": "#ff8f8f", "lo": "#d6453d", "belly": "#ffe1de",
    "cheek": "#ffb37a", "accent": "#fff0e6", "outline": "#7a1f1f",
}

# Teal pancake-creature.
LEGGY_PAL = {
    "hi": "#4fd8d8", "lo": "#208f9f", "belly": "#d8fbfb",
    "cheek": "#ffb3a6", "accent": "#e6fffb", "outline": "#145f6b",
}

EYES = {
    "dark": "#23262e",
    "amber": "#7a4a1f",
    "blue": "#274b68",
}

W, H = 12, 16
EMPTY = "............"

# Hand-drawn 12x16 pixel masks.  '#' = body, 'b' = belly, '.' = empty.

# Orange octopus. Claude Code's mascot came home.
OCTOPUS = [
    "............",
    "............",
    "..########..",
    ".##########.",
    "############",
    "############",
    "############",
    "############",
    "############",
    ".##########.",
    ".##########.",
    "..########..",
    "....####....",
    "..##..##..##",
    "..##..##..##",
    "..##..##..##",
]

# A round orange alien with a single big eye.
CYCLOPS = [
    "............",
    "............",
    "...######...",
    "..########..",
    ".##########.",
    "############",
    "############",
    "############",
    "############",
    "############",
    ".##########.",
    "..########..",
    "....####....",
    "............",
    "............",
    "............",
]

# Pou: a beige blob, a piece of dough with small stretched eyes.
POU = [
    "............",
    "............",
    ".....##.....",
    "....###.....",
    "...#####....",
    "..#######...",
    ".#########..",
    "############",
    "############",
    "############",
    "############",
    "############",
    ".#########..",
    "..#######...",
    "............",
    "............",
]

# My Pet Alien (Tommy): round brown head, big white eyes.
TOMMY = [
    "............",
    "............",
    "....####....",
    "...######...",
    "..########..",
    ".##########.",
    "############",
    "############",
    "############",
    "############",
    ".##########.",
    ".##########.",
    "..########..",
    "...####.....",
    "............",
    "............",
]

# A wavy-bottomed slime with two goofy eyes.
SLIME = [
    "............",
    "............",
    "...######...",
    "..########..",
    ".##########.",
    "############",
    "############",
    "############",
    "############",
    "..########..",
    ".####..####.",
    ".##......##.",
    ".##......##.",
    "............",
    "............",
    "............",
]

# A green alien with two antennae sticking up.
ANTENNA = [
    "..#......#..",
    "...#....#...",
    "..###..###..",
    "..##....##..",
    ".##########.",
    "############",
    "############",
    "############",
    ".####..####.",
    ".##########.",
    "..########..",
    "...######...",
    "...######...",
    "............",
    "............",
    "............",
]

# A strangely conical alien.
CONE = [
    "............",
    "............",
    ".....##.....",
    ".....###....",
    "....#####...",
    "...#######..",
    "..#########.",
    ".##########.",
    ".##########.",
    ".####..####.",
    ".##########.",
    "..########..",
    "...######...",
    "............",
    "............",
    "............",
]

# A weird floating pancake-creature with little legs.
LEGGY = [
    "...######...",
    "..########..",
    ".##########.",
    ".##########.",
    "############",
    ".##########.",
    ".##########.",
    "..########..",
    "..####..####",
    "..##..##..##",
    "..##..##..##",
    "............",
    "............",
    "............",
    "............",
    "............",
]

VARIANTS = [
    {"kind": "octopus", "grid": OCTOPUS, "face_y": 6, "mouth_y": 9,
     "palette": OCTOPUS_PAL},
    {"kind": "cyclops", "grid": CYCLOPS, "face_y": 5, "mouth_y": 9,
     "palette": CYCLOPS_PAL, "single_eye": True},
    {"kind": "pou", "grid": POU, "face_y": 7, "mouth_y": 10,
     "palette": POU_PAL, "pou_eyes": True},
    {"kind": "tommy", "grid": TOMMY, "face_y": 5, "mouth_y": 9,
     "palette": TOMMY_PAL},
    {"kind": "slime", "grid": SLIME, "face_y": 5, "mouth_y": 8,
     "palette": SLIME_PAL},
    {"kind": "antenna", "grid": ANTENNA, "face_y": 5, "mouth_y": 8,
     "palette": ANTENNA_PAL},
    {"kind": "cone", "grid": CONE, "face_y": 6, "mouth_y": 9,
     "palette": CONE_PAL},
    {"kind": "leggy", "grid": LEGGY, "face_y": 3, "mouth_y": 7,
     "palette": LEGGY_PAL},
]

VARIANT_KINDS = [v["kind"] for v in VARIANTS]


def choose_skin(not_kind: str | None = None) -> str:
    pool = [k for k in VARIANT_KINDS if k != not_kind]
    return random.choice(pool or list(VARIANT_KINDS))


def _lerp(a: str, b: str, t: float) -> str:
    al = [int(a[i : i + 2], 16) for i in (1, 3, 5)]
    bl = [int(b[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(
        f"{round(al[k] + (bl[k] - al[k]) * max(0.0, min(1.0, t))) & 255:02x}"
        for k in range(3)
    )


def genes_for(root, pet: dict) -> dict:
    seed = f"{root}:{pet.get('name', 'pet')}"
    h = int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest()[:8], "big")
    r = random.Random(h)
    return {
        "palette": r.choice(list(PALETTES)),
        "variant": r.choice(VARIANTS)["kind"],
        "eye": r.choice(list(EYES)),
        "seed": seed,
    }


def _variant(kind: str) -> dict:
    for v in VARIANTS:
        if v["kind"] == kind:
            return v
    return VARIANTS[0]


def mutation_count(pet: dict) -> int:
    return min(
        3,
        pet.get("evolution_level", 0) + pet.get("age", 0) // 12,
    )


def _body_matrix(vm: dict, palette: dict, stage: str):
    m = [["."] * W for _ in range(H)]
    grid = vm["grid"]

    def inside(x, y) -> bool:
        return 0 <= x < W and 0 <= y < H and grid[y][x] != "."

    for y in range(H):
        row = grid[y] if len(grid) > y else EMPTY
        for x in range(W):
            ch = row[x]
            if ch == ".":
                continue
            edge = not (
                inside(x - 1, y)
                and inside(x + 1, y)
                and inside(x, y - 1)
                and inside(x, y + 1)
            )
            if ch == "b":
                m[y][x] = palette["outline"] if edge else palette["belly"]
            else:
                if edge:
                    m[y][x] = palette["outline"]
                else:
                    t = (y - 2.5) / 13.0
                    m[y][x] = _lerp(palette["hi"], palette["lo"], t)

    def paint(x, y, color):
        if 0 <= x < W and 0 <= y < H:
            m[y][x] = color

    # stage accessory (floating above the head)
    if stage == "sprout":
        paint(5, 1, "#6ce0a0")
        paint(6, 1, "#4ade80")
    elif stage == "bloom":
        paint(5, 0, "#ffd166")
        paint(5, 1, "#ff9db4")
        paint(6, 0, "#ff9db4")
        paint(6, 1, "#ffd166")
    elif stage == "mystic":
        for x in range(4, 8):
            paint(x, 0, "#ffd166")
        paint(4, 1, "#aef3ff")
        paint(7, 1, "#aef3ff")
    return m


LOOKS = ("left", "straight", "right")


def _paint_eyes(m, eyes, face_y, eye, glint, look, blink):
    """Draw open eyes as 2-tall sockets with a glinting pupil.

    *eyes* is a list of (start_x, width); the pupil (glint) travels
    inside each socket along the gaze direction, so the pet visibly
    looks left / straight / right.  Blink/tired/sleepy draw a closed
    horizontal line instead.
    """
    def paint(x, y, color):
        if 0 <= x < W and 0 <= y < H:
            m[y][x] = color

    if blink:
        for start, width in eyes:
            for x in range(start, start + width):
                paint(x, face_y + 1, eye)
        return

    for start, width in eyes:
        for yy in (face_y, face_y + 1):
            for x in range(start, start + width):
                paint(x, yy, eye)

    if look == "left":
        for start, _width in eyes:
            paint(start, face_y, glint)
    elif look == "right":
        for start, width in eyes:
            paint(start + width - 1, face_y, glint)
    else:  # straight: wide open — both cells lit for 2-wide eyes
        for start, width in eyes:
            if width == 2:
                paint(start, face_y, glint)
                paint(start + width - 1, face_y, glint)
            else:
                paint(start + width // 2, face_y, glint)


def idle_look(pet_seed: str, now: float | None = None) -> str:
    """Deterministic per-pet glance schedule: the eyes dart side to
    side every few seconds, mostly returning to straight ahead."""
    if now is None:
        now = time.time()
    h = int.from_bytes(hashlib.sha256(pet_seed.encode("utf-8")).digest()[:8],
                       "big")
    step = 4.0 + (h % 40) / 10.0
    bucket = int(now // step)
    r = random.Random(h ^ (bucket * 0x9E3779B9 & 0xFFFFFFFF))
    return r.choice(("left", "straight", "straight", "right", "straight"))


def _face(m, vm: dict, genes: dict, pal: dict, mood: str, blink: bool,
          look: str = "straight"):
    eye = EYES[genes["eye"]]
    glint = "#ffffff"
    face_y, mouth_y = vm["face_y"], vm["mouth_y"]
    cheeks_y = mouth_y - 1
    closed = blink or mood in ("tired", "sleepy")

    def paint(x, y, color):
        if 0 <= x < W and 0 <= y < H:
            m[y][x] = color

    if vm.get("single_eye"):
        _paint_eyes(m, [(4, 4)], face_y, eye, glint, look, closed)
        paint(2, cheeks_y, pal["cheek"])
        paint(9, cheeks_y, pal["cheek"])
        for x in (5, 6):
            paint(x, mouth_y, pal["outline"])
        return

    _paint_eyes(m, [(3, 2), (8, 2)], face_y, eye, glint, look, closed)
    paint(1, cheeks_y, pal["cheek"])
    paint(10, cheeks_y, pal["cheek"])

    mouth = {
        "happy": [3, 4, 5, 6, 7, 8],
        "content": [5, 6],
        "focused": [4, 5, 6, 7],
        "alert": [4, 5, 6, 7],
        "determined": [4, 5, 6],
        "thoughtful": [4, 5, 6],
        "curious": [4, 5, 6],
        "cautious": [5, 6],
        "worried": [5, 6],
        "anxious": [5, 6],
        "relieved": [5, 6],
        "tired": [5],
    }.get(mood, [5, 6])
    for x in mouth:
        paint(x, mouth_y, pal["outline"])


def _to_text(m, scale: int) -> Text:
    text = Text()
    for y in range(0, H, 2):
        top = m[y]
        bot = m[y + 1] if y + 1 < H else None
        for x in range(W):
            t = top[x]
            b = (bot[x] if bot is not None else ".")
            if t != "." and b != ".":
                glyph, seg = "\u2580", f"{t} on {b}"   # top half = fg
            elif t != ".":
                glyph, seg = "\u2580", f"{t} on {BG}"  # top half only
            elif b != ".":
                glyph, seg = "\u2584", f"{b} on {BG}"  # bottom half only
            else:
                glyph, seg = " ", ""
            if scale >= 2:
                if seg:
                    text.append(glyph * 2, style=seg)
                else:
                    text.append("  ")
            else:
                if seg:
                    text.append(glyph, style=seg)
                else:
                    text.append(" ", style="")
        text.append("\n")
    return text


def render(pet: dict, root, scale: int = 1, blink: bool = False,
           look: str = "straight") -> Text:
    genes = genes_for(root, pet)
    variant = pet.get("skin")
    if variant not in VARIANT_KINDS:
        variant = genes["variant"]
    stage = pet.get("body_pattern", "seed")
    if stage not in ("seed", "sprout", "bloom", "mystic"):
        stage = "seed"
    mood = pet.get("mood", "curious")
    vm = _variant(variant)
    palette = vm.get("palette") or PALETTES[genes["palette"]]
    m = _body_matrix(vm, palette, stage)
    _face(m, vm, genes, palette, mood, blink, look)
    return _to_text(m, scale)
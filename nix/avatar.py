from __future__ import annotations

import hashlib
import random

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
    "peach": {
        "hi": "#ffc98f", "lo": "#e07a4f", "belly": "#fff0e0",
        "cheek": "#ff9090", "accent": "#ffe9c7", "outline": "#8a4a2f",
    },
    "grape": {
        "hi": "#c9a6ff", "lo": "#7c4fd0", "belly": "#efe2ff",
        "cheek": "#ffb3d6", "accent": "#ffe4ff", "outline": "#4a2f7a",
    },
    "rose": {
        "hi": "#ffb3d9", "lo": "#d654a6", "belly": "#ffe4f2",
        "cheek": "#ff8a8a", "accent": "#fff0f7", "outline": "#7a2f5a",
    },
    "honey": {
        "hi": "#ffd98a", "lo": "#d69a3a", "belly": "#fff7e0",
        "cheek": "#ff9b7a", "accent": "#fff3d0", "outline": "#8a6520",
    },
    "slate": {
        "hi": "#b9c4d9", "lo": "#5a6b8f", "belly": "#e8eef7",
        "cheek": "#ffb3b3", "accent": "#cfe4ff", "outline": "#3a4660",
    },
    "coral": {
        "hi": "#ffabab", "lo": "#c05656", "belly": "#ffe6e0",
        "cheek": "#ff8a8a", "accent": "#ffe0d0", "outline": "#7a2f2f",
    },
}

EYES = {
    "dark": "#23262e",
    "amber": "#7a4a1f",
    "blue": "#274b68",
}

EARS = ["round", "cat", "bunny", "antenna", "none"]
PATTERNS = ["none", "dots", "stripe", "heart", "star"]

W, H = 12, 16


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
        "ear": r.choice(EARS),
        "pattern": r.choice(PATTERNS),
        "eye": r.choice(list(EYES)),
        "seed": seed,
    }


def mutation_count(pet: dict) -> int:
    return min(
        3,
        pet.get("evolution_level", 0) + pet.get("age", 0) // 12,
    )


def _body_matrix(genes: dict, stage: str, mood: str, mutations: int):
    pal = PALETTES[genes["palette"]]
    m = [["."] * W for _ in range(H)]

    def body_color(y, x):
        t = (y - 2.5) / 13.0
        return _lerp(pal["hi"], pal["lo"], t)

    cx, cy, rx, ry = 5.5, 9.5, 5.0, 6.2
    for y in range(H):
        for x in range(W):
            dx = (x - cx) / rx
            dy = (y - cy) / ry
            inside = dx * dx + dy * dy <= 1.0
            if not inside:
                continue
            edge = False
            for n in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                nx, ny = n
                nxd = (nx - cx) / rx
                nyd = (ny - cy) / ry
                if not (nxd * nxd + nyd * nyd <= 1.0):
                    edge = True
                    break
            m[y][x] = pal["outline"] if edge else body_color(y, x)

    def paint(x, y, color):
        if 0 <= x < W and 0 <= y < H:
            m[y][x] = color

    # ears
    ear = genes["ear"]
    if ear in ("round", "cat", "bunny", "antenna"):
        ear_col = _lerp(pal["hi"], pal["lo"], 0.28)
        if ear == "round":
            for off in (0, 1):
                for y in (2, 3):
                    paint(2 + off, y, ear_col)
                    paint(9 + off, y, ear_col)
        elif ear == "cat":
            for y in (2, 3, 4):
                paint(1, y, ear_col)
                paint(10, y, ear_col)
            paint(2, 2, ear_col)
            paint(9, 2, ear_col)
        elif ear == "bunny":
            for y in (1, 2, 3, 4):
                paint(3, y, ear_col)
                paint(8, y, ear_col)
            paint(2, 1, ear_col)
            paint(9, 1, ear_col)
        elif ear == "antenna":
            for x in (5, 6):
                paint(x, 2, ear_col)
            paint(5, 0, pal["accent"])
            paint(6, 1, pal["accent"])

    # belly
    bx, by, brx, bry = 5.5, 11.6, 2.6, 2.0
    for y in range(H):
        for x in range(W):
            if abs((x - bx) / brx) ** 2 + abs((y - by) / bry) ** 2 <= 1.0:
                m[y][x] = pal["belly"]

    # pattern
    pat = genes["pattern"]
    accent = pal["accent"]
    if pat == "dots":
        paint(2, 10, accent); paint(6, 12, accent); paint(9, 10, accent)
    elif pat == "stripe":
        paint(6, 8, accent); paint(6, 9, accent); paint(7, 10, accent)
    elif pat == "heart":
        paint(3, 10, accent); paint(4, 10, accent)
        paint(3, 11, accent); paint(4, 11, accent)
    elif pat == "star":
        for x in (5, 6):
            paint(x, 3, accent)
        paint(5, 2, accent); paint(6, 2, accent)

    # mutation traits
    if mutations >= 1:
        paint(5, 1, "#ffd166")
        paint(6, 1, "#ffd166")
    if mutations >= 2:
        paint(5, 0, "#ffd166")
    if mutations >= 3:
        paint(0, 8, "#aef3ff")
        paint(11, 8, "#aef3ff")

    # stage accessory
    if stage == "sprout":
        paint(5, 3, "#4ade80"); paint(6, 3, "#4ade80")
    elif stage == "bloom":
        paint(6, 3, "#ffd166")
        paint(4, 3, "#ff9db4"); paint(7, 3, "#ff9db4")
        paint(5, 2, "#ffd166"); paint(6, 2, "#b39df0")
    elif stage == "mystic":
        for x in range(4, 8):
            paint(x, 2, "#ffd166")
        paint(4, 1, "#aef3ff"); paint(7, 1, "#aef3ff")
        paint(0, 11, "#aef3ff"); paint(11, 11, "#aef3ff")
    return m


def _face(m, genes: dict, pal: dict, mood: str, blink: bool):
    eye = EYES[genes["eye"]]
    glint = "#ffffff"

    def paint(x, y, color):
        if 0 <= x < W and 0 <= y < H:
            m[y][x] = color

    eye_top = 6
    if blink or mood in ("tired", "sleepy"):
        for x in (3, 4):
            paint(x, eye_top + 1, eye)
        for x in (8, 9):
            paint(x, eye_top + 1, eye)
    elif mood in ("alert", "focused"):
        for x, g in ((3, 4), (8, 9)):
            paint(x, eye_top, eye)
        paint(3, eye_top, glint)
        paint(8, eye_top, glint)
    else:
        paint(3, eye_top, eye); paint(4, eye_top, eye)
        paint(8, eye_top, eye); paint(9, eye_top, eye)
        paint(3, eye_top, glint)
        paint(8, eye_top, glint)

    paint(1, 8, pal["cheek"])
    paint(10, 8, pal["cheek"])

    mouth = {
        "happy": [(3, 9), (4, 9), (5, 9), (6, 9), (7, 9), (8, 9)],
        "content": [(5, 9), (6, 9)],
        "focused": [(4, 9), (5, 9), (6, 9), (7, 9)],
        "alert": [(4, 9), (5, 9), (6, 9), (7, 9)],
        "determined": [(4, 9), (5, 9), (6, 9)],
        "thoughtful": [(4, 9), (5, 9), (6, 9)],
        "curious": [(4, 9), (5, 9), (6, 9)],
        "cautious": [(5, 9), (6, 9)],
        "worried": [(5, 9), (6, 9)],
        "anxious": [(5, 9), (6, 9)],
        "relieved": [(5, 9), (6, 9)],
        "tired": [(5, 9)],
    }[mood]
    for x, y in mouth:
        paint(x, y, pal["outline"])


def _to_text(m, scale: int) -> Text:
    text = Text()
    for y in range(0, H, 2):
        top = m[y]
        bot = m[y + 1] if y + 1 < H else None
        for x in range(W):
            t = top[x]
            b = (bot[x] if bot is not None else ".")
            if t != "." and b != ".":
                seg = f"{t} on {b}"
            elif t != ".":
                seg = f"{t} on {BG}"
            elif b != ".":
                seg = f"{b} on {BG}"
            else:
                seg = ""
            if scale >= 2:
                if seg:
                    text.append("\u2580\u2580", style=seg)
                else:
                    text.append("  ")
            else:
                if seg:
                    text.append("\u2580", style=seg)
                else:
                    text.append(" ", style="")
        text.append("\n")
    return text


def render(pet: dict, root, scale: int = 1, blink: bool = False) -> Text:
    genes = genes_for(root, pet)
    stage = pet.get("body_pattern", "seed")
    if stage not in ("seed", "sprout", "bloom", "mystic"):
        stage = "seed"
    mood = pet.get("mood", "curious")
    mutations = mutation_count(pet)
    m = _body_matrix(genes, stage, mood, mutations)
    _face(m, genes, PALETTES[genes["palette"]], mood, blink)
    return _to_text(m, scale)
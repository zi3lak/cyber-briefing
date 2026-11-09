#!/usr/bin/env python3
"""
CSSLTD CYBER BRIEFING — caricature engine.

Procedural pirate-hacker caricatures in engraved line style. Every article gets
a deterministic character (seeded by its hash): different hat, eyes, beard,
prop and backplate, drawn stroke-only with cross-hatching so the page reads
like a woodcut almanac of the criminal underworld.

Layout contract (100x100 box, everything inside a clipped circle):
    y  6-46   hat / hair
    y 46-64   eyes band
    y 62-72   nose
    y 72-80   mouth
    y 76-92   beard
    x 62-94   prop (bottom-right corner, never over the face)
"""
from __future__ import annotations

import hashlib
import math
import random

from art import INK, INK_DIM, CRIMSON, GOLD, SEA, defs, path_d, line, circle, ellipse

S = {"full": 1.0, "simple": 1.25}


def _w(base: float, detail: str) -> float:
    return round(base * S[detail], 2)


# ------------------------------------------------------------------ pieces


def head_shape(rnd: random.Random, d: str) -> str:
    """Gaunt hacker skull: cranium, cheekbones, jaw."""
    s = []
    s.append(path_d(
        "M50 18 C34 18 25 33 25 50 C25 61 28 69 32 76 "
        "C35 81 40 84 42 85 L42 89 L58 89 L58 85 "
        "C60 84 65 81 68 76 C72 69 75 61 75 50 C75 33 66 18 50 18 Z", _w(1.9, d)))
    # cheekbone + jaw shading
    s.append(path_d("M30 58 C32 65 35 71 41 75", _w(0.75, d), INK_DIM, "none", 0.42))
    s.append(path_d("M70 58 C68 65 65 71 59 75", _w(0.75, d), INK_DIM, "none", 0.42))
    s.append(path_d("M38 79 C42 83 46 85 50 85 C54 85 58 83 62 79", _w(0.8, d), INK_DIM, "none", 0.4))
    # ears
    s.append(path_d("M25 50 C21 50 20 56 23 60", _w(1.0, d)))
    s.append(path_d("M75 50 C79 50 80 56 77 60", _w(1.0, d)))
    return "".join(s)


def hat(rnd: random.Random, d: str) -> str:
    kind = rnd.choice(["tricorn", "hood", "beanie", "cap", "bandana", "topper", "helm", "none"])
    s = []
    if kind == "tricorn":
        s.append(path_d("M20 38 C20 22 33 11 50 11 C67 11 80 22 80 38 C64 30 36 30 20 38 Z", _w(1.9, d)))
        s.append(path_d("M12 39 C29 50 71 50 88 39 C80 52 20 52 12 39 Z", _w(1.8, d)))
        s.append(path_d("M26 27 C37 20 63 20 74 27", _w(0.8, d), INK_DIM, "none", 0.5))
        s.append(path_d("M79 20 C90 10 99 4 105 6 C103 17 96 27 85 33 C82 28 80 24 79 20 Z", _w(1.4, d), GOLD, "url(#hatchG)"))
    elif kind == "hood":
        s.append(path_d("M17 52 C17 26 31 9 50 9 C69 9 83 26 83 52 C82 42 75 37 68 35 C60 27 40 27 32 35 C25 37 18 42 17 52 Z", _w(1.9, d)))
        s.append(path_d("M28 48 C33 35 67 35 72 48 C70 38 63 32 50 32 C37 32 30 38 28 48 Z", _w(1.25, d), INK, "url(#hatchB)"))
    elif kind == "beanie":
        s.append(path_d("M22 40 C22 22 34 12 50 12 C66 12 78 22 78 40 Z", _w(1.8, d)))
        s.append(path_d("M18 40 L82 40 L82 47 L18 47 Z", _w(1.6, d)))
        s.append(circle(50, 9, 4.4, _w(1.4, d)))
        if d == "full":
            for i in range(5):
                s.append(line(29 + i * 10, 22, 31 + i * 10, 39, _w(0.65, d), INK_DIM, 0.32))
    elif kind == "cap":
        s.append(path_d("M23 39 C23 22 34 14 50 14 C66 14 77 22 77 37 Z", _w(1.8, d)))
        s.append(path_d("M21 39 L79 39 L87 44 L21 44 Z", _w(1.7, d)))
    elif kind == "bandana":
        s.append(path_d("M19 38 C21 24 33 16 50 16 C67 16 79 24 81 38 C65 32 35 32 19 38 Z", _w(1.8, d)))
        s.append(path_d("M78 32 C88 30 91 36 87 42 C83 47 79 43 80 38", _w(1.4, d)))
        if d == "full":
            for i in range(4):
                s.append(line(28 + i * 12, 22, 30 + i * 12, 35, _w(0.6, d), INK_DIM, 0.3))
    elif kind == "topper":
        s.append(path_d("M32 12 L68 12 L68 36 L32 36 Z", _w(1.8, d)))
        s.append(path_d("M21 36 L79 36 L79 45 L21 45 Z", _w(1.7, d)))
        s.append(line(35, 19, 65, 19, _w(0.7, d), INK_DIM, 0.45))
    elif kind == "helm":
        s.append(path_d("M23 48 C23 27 34 14 50 14 C66 14 77 27 77 48 C72 41 64 38 50 38 C36 38 28 41 23 48 Z", _w(1.9, d)))
        s.append(path_d("M17 50 L83 50 L83 56 L17 56 Z", _w(1.6, d)))
        s.append(line(50, 16, 50, 38, _w(0.9, d), INK_DIM, 0.5))
    return "".join(s)


def eyes(rnd: random.Random, d: str) -> str:
    """Eye band sits between y=48 and y=62 — always clear of the hat."""
    kind = rnd.choice(["visor", "glowing", "goggles", "eyepatch", "shades", "squint", "mask"])
    s = []
    if kind == "visor":
        s.append(path_d("M30 49 C38 45 62 45 70 49 L70 59 C62 63 38 63 30 59 Z", _w(1.7, d)))
        s.append(path_d("M35 50 L65 50 L65 57 L35 57 Z", _w(0.7, d), SEA, "none", 0.5))
        if d == "full":
            for i in range(4):
                s.append(line(39 + i * 7, 50, 42 + i * 7, 57, _w(0.6, d), SEA, 0.3))
    elif kind == "glowing":
        s.append(ellipse(39, 54, 6.5, 5, _w(1.5, d)))
        s.append(ellipse(61, 54, 6.5, 5, _w(1.5, d)))
        s.append(circle(39, 54, 2.1, _w(0.9, d), CRIMSON, CRIMSON))
        s.append(circle(61, 54, 2.1, _w(0.9, d), CRIMSON, CRIMSON))
        s.append(path_d("M33 49 L45 49 M55 49 L67 49", _w(1.1, d)))
    elif kind == "goggles":
        s.append(circle(39, 54, 7.5, _w(1.6, d)))
        s.append(circle(61, 54, 7.5, _w(1.6, d)))
        s.append(line(47, 53, 53, 53, _w(1.3, d)))
    elif kind == "eyepatch":
        s.append(path_d("M31 49 C34 46 44 46 47 50 L47 58 C43 61 34 60 31 56 Z", _w(1.6, d), INK, "url(#hatchR)"))
        s.append(path_d("M47 53 L70 48", _w(1.3, d)))
        s.append(ellipse(61, 54, 6, 4.5, _w(1.4, d)))
        s.append(circle(61, 54, 1.9, _w(0.9, d), INK, INK))
    elif kind == "shades":
        s.append(path_d("M29 50 L46 50 L46 58 L32 58 Z", _w(1.6, d)))
        s.append(path_d("M54 50 L71 50 L68 58 L54 58 Z", _w(1.6, d)))
        s.append(line(46, 52, 54, 52, _w(1.3, d)))
    elif kind == "squint":
        s.append(path_d("M32 56 C35 51 43 51 46 56", _w(1.5, d)))
        s.append(path_d("M54 56 C57 51 65 51 68 56", _w(1.5, d)))
    elif kind == "mask":
        s.append(path_d("M27 48 C36 43 64 43 73 48 L73 62 C64 67 36 67 27 62 Z", _w(1.7, d)))
        if d == "full":
            for i in range(5):
                s.append(line(33 + i * 7, 56, 35 + i * 7, 62, _w(0.6, d), INK_DIM, 0.3))
    return "".join(s)


def beard(rnd: random.Random, d: str) -> str:
    kind = rnd.choice(["full", "goatee", "moustache", "braid", "none", "stubble"])
    s = []
    if kind == "full":
        s.append(path_d("M34 76 C37 86 43 91 50 91 C57 91 63 86 66 76 C61 83 56 85 50 85 C44 85 39 83 34 76 Z", _w(1.7, d), INK, "url(#hatchB)"))
    elif kind == "goatee":
        s.append(path_d("M44 76 C46 85 54 85 56 76 C54 82 46 82 44 76 Z", _w(1.5, d), INK, "url(#hatchB)"))
    elif kind == "moustache":
        s.append(path_d("M38 70 C45 65 55 65 62 70 C55 72 45 72 38 70 Z", _w(1.6, d)))
    elif kind == "braid":
        s.append(path_d("M36 74 C36 85 41 90 46 94", _w(1.5, d)))
        s.append(path_d("M64 74 C64 85 59 90 54 94", _w(1.5, d)))
    elif kind == "stubble" and d == "full":
        for i in range(8):
            s.append(circle(38 + (i % 4) * 8, 74 + (i // 4) * 4, 0.8, _w(0.5, d), INK_DIM, "none", 0.6))
    return "".join(s)


def mouth_nose(rnd: random.Random, d: str) -> str:
    s = []
    s.append(path_d("M50 62 L46 69 L54 69 Z", _w(1.3, d)))
    if rnd.random() < 0.5:
        s.append(path_d("M43 74 C47 77 53 77 57 74", _w(1.4, d)))
    else:
        s.append(path_d("M42 74 L58 74", _w(1.3, d)))
    return "".join(s)


def prop(rnd: random.Random, d: str) -> str:
    """Held object — bottom-right corner (x 62-94, y 60-92), never over the face."""
    kind = rnd.choice(["pipe", "cigar", "hook", "knife", "usb", "mug", "syringe", "none"])
    s = []
    if kind == "pipe":
        s.append(path_d("M70 78 L86 73 L89 78 L73 83 Z", _w(1.5, d)))
        s.append(path_d("M72 80 L72 89 L78 89 L78 82", _w(1.4, d)))
    elif kind == "cigar":
        s.append(path_d("M70 79 L87 76 L89 82 L72 86 Z", _w(1.5, d), INK, "url(#hatchR)"))
        s.append(path_d("M87 76 L92 73 L94 79 L89 82 Z", _w(1.2, d)))
    elif kind == "hook":
        s.append(path_d("M74 90 L74 80 C74 72 83 70 87 77 C89 82 84 85 81 82", _w(1.9, d)))
        s.append(path_d("M69 90 L79 90", _w(1.5, d)))
    elif kind == "knife":
        s.append(path_d("M70 92 L88 74 L92 78 L74 96 Z", _w(1.5, d), INK, "url(#hatchA)"))
        s.append(path_d("M68 90 L74 96", _w(1.4, d)))
    elif kind == "usb":
        s.append(path_d("M74 80 L88 80 L88 91 L74 91 Z", _w(1.4, d)))
        s.append(path_d("M77 80 L77 75 L85 75 L85 80", _w(1.2, d)))
    elif kind == "mug":
        s.append(path_d("M72 74 L92 74 L89 91 L75 91 Z", _w(1.4, d), INK, "url(#hatchC)"))
        s.append(path_d("M92 77 C98 77 98 86 92 86", _w(1.2, d)))
    elif kind == "syringe":
        s.append(path_d("M72 93 L88 75", _w(2.0, d), INK, "url(#hatchC)"))
        s.append(path_d("M88 75 L93 70", _w(1.1, d)))
    return "".join(s)


def backplate(rnd: random.Random, d: str) -> str:
    kind = rnd.choice(["waves", "tentacles", "crossbones", "hex", "radial", "grid", "rings"])
    s = []
    if kind == "waves":
        for i in range(3):
            y = 76 + i * 9
            s.append(path_d(f"M2 {y} C14 {y - 8} 24 {y + 8} 36 {y} C48 {y - 8} 58 {y + 8} 70 {y} C82 {y - 8} 90 {y + 8} 98 {y}", _w(0.9, d), SEA, "none", 0.3))
    elif kind == "tentacles":
        for i in range(2):
            s.append(path_d(f"M-6 {38 + i * 24} C20 {26 + i * 22} 40 {48 + i * 22} 62 {36 + i * 24} C82 {24 + i * 22} 94 {44 + i * 22} 106 {36 + i * 24}", _w(1.2, d), INK, "none", 0.2))
    elif kind == "crossbones":
        s.append(path_d("M4 96 L96 4", _w(1.6, d), INK, "none", 0.14))
        s.append(path_d("M96 96 L4 4", _w(1.6, d), INK, "none", 0.14))
    elif kind == "hex":
        for r in range(4):
            for c in range(5):
                cx, cy = 10 + c * 20 + (r % 2) * 10, 12 + r * 22
                s.append(path_d(f"M{cx} {cy} L{cx + 10} {cy} L{cx + 15} {cy + 10} L{cx + 10} {cy + 20} L{cx} {cy + 20} L{cx - 5} {cy + 10} Z", _w(0.7, d), INK, "none", 0.12))
    elif kind == "radial":
        for i in range(12):
            a = i * 30
            x = 50 + 44 * math.cos(math.radians(a))
            y = 50 + 44 * math.sin(math.radians(a))
            s.append(line(50, 50, round(x, 2), round(y, 2), _w(0.6, d), INK, 0.11))
    elif kind == "grid":
        for i in range(9):
            s.append(line(i * 12, 0, i * 12, 100, _w(0.55, d), INK, 0.1))
        for i in range(9):
            s.append(line(0, i * 12, 100, i * 12, _w(0.55, d), INK, 0.1))
    elif kind == "rings":
        s.append(circle(50, 50, 40, _w(1.1, d), INK, "none", 0.15))
        s.append(circle(50, 50, 28, _w(0.8, d), INK, "none", 0.12))
    return "".join(s)


# ------------------------------------------------------------------ public


def caricature(seed: str, size: int = 120, cls: str = "caric") -> str:
    h = hashlib.sha256(seed.encode("utf-8", "ignore")).hexdigest()
    rnd = random.Random(int(h[:12], 16))
    d = "full" if size >= 100 else "simple"

    parts = [
        backplate(rnd, d),
        head_shape(rnd, d),
        hat(rnd, d),
        eyes(rnd, d),
        mouth_nose(rnd, d),
        beard(rnd, d),
        prop(rnd, d),
    ]
    frame = [circle(50, 50, 48, _w(1.1, d), INK_DIM, "none", 0.3)]

    clip = f'<clipPath id="clip-{h[:8]}"><circle cx="50" cy="50" r="47"/></clipPath>'
    return (
        f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 100 100" '
        f'role="img" aria-label="caricature" fill="none" stroke-linecap="round" '
        f'stroke-linejoin="round">{defs()}{clip}'
        f'<g clip-path="url(#clip-{h[:8]})" filter="url(#rough2)">{"".join(parts)}</g>'
        f'<g>{"".join(frame)}</g></svg>'
    )


def gallery(seed_prefix: str, count: int = 5, size: int = 92) -> str:
    out = [caricature(f"{seed_prefix}:{i}", size, "caric") for i in range(count)]
    return f'<div class="gallery">{"".join(out)}</div>'
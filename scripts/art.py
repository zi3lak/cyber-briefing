#!/usr/bin/env python3
"""
CSSLTD CYBER BRIEFING — line-art engine.

Generates engraved / woodcut style SVG artwork at runtime: a category icon set,
a hero illustration, a per-article emblem stamp and a jolly roger watermark.
Everything is stroke-only ("kreskowa"), hatched with SVG patterns and roughened
with a turbulence displacement filter so it reads as hand-inked, not clip-art.

No external assets, no network, deterministic output.
"""
from __future__ import annotations

import hashlib
import math
import random

INK = "#efe6d4"        # bone-white ink on dark ground
INK_DIM = "#a9a08c"
CRIMSON = "#c0392b"
GOLD = "#d8a54a"
SEA = "#4fa8a0"

# --------------------------------------------------------------------- shared defs


def defs(extra: str = "") -> str:
    return f"""<defs>
  <filter id="rough" x="-12%" y="-12%" width="124%" height="124%">
    <feTurbulence type="fractalNoise" baseFrequency="0.022" numOctaves="3" seed="7" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="2.6" xChannelSelector="R" yChannelSelector="G"/>
  </filter>
  <filter id="rough2" x="-15%" y="-15%" width="130%" height="130%">
    <feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="2" seed="19" result="n2"/>
    <feDisplacementMap in="SourceGraphic" in2="n2" scale="1.5" xChannelSelector="R" yChannelSelector="G"/>
  </filter>
  <pattern id="hatchA" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(38)">
    <line x1="0" y1="0" x2="0" y2="7" stroke="{INK}" stroke-width="1.15" opacity="0.30"/>
  </pattern>
  <pattern id="hatchB" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(-52)">
    <line x1="0" y1="0" x2="0" y2="5" stroke="{INK}" stroke-width="1" opacity="0.34"/>
  </pattern>
  <pattern id="hatchC" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(8)">
    <line x1="0" y1="0" x2="0" y2="9" stroke="{INK}" stroke-width="0.85" opacity="0.22"/>
  </pattern>
  <pattern id="hatchR" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(38)">
    <line x1="0" y1="0" x2="0" y2="6" stroke="{CRIMSON}" stroke-width="1.25" opacity="0.42"/>
  </pattern>
  <pattern id="hatchG" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-38)">
    <line x1="0" y1="0" x2="0" y2="6" stroke="{GOLD}" stroke-width="1.1" opacity="0.35"/>
  </pattern>
  <radialGradient id="vign" cx="50%" cy="42%" r="72%">
    <stop offset="0%" stop-color="#1b2029" stop-opacity="0"/>
    <stop offset="100%" stop-color="#05070a" stop-opacity="0.85"/>
  </radialGradient>
  {extra}
</defs>"""


def path_d(d: str, w: float = 2.1, color: str = INK, fill: str = "none", op: float = 1.0) -> str:
    return (
        f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{w}" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="{op}"/>'
    )


def line(x1, y1, x2, y2, w=1.4, color=INK, op=1.0, cap="round"):
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
        f'stroke-width="{w}" stroke-linecap="{cap}" opacity="{op}"/>'
    )


def circle(cx, cy, r, w=1.8, color=INK, fill="none", op=1.0):
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{color}" '
        f'stroke-width="{w}" opacity="{op}"/>'
    )


def ellipse(cx, cy, rx, ry, w=1.8, color=INK, fill="none", op=1.0, rot=0):
    return (
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{color}" '
        f'stroke-width="{w}" opacity="{op}" transform="rotate({rot} {cx} {cy})"/>'
    )


# --------------------------------------------------------------------- icons
# Every icon is drawn inside a 0 0 100 100 box, stroke-only.

def icon_skull() -> str:
    s = []
    # crossbones behind
    s.append(path_d("M18 78 L82 26", 3.4))
    s.append(path_d("M82 78 L18 26", 3.4))
    s.append(circle(20, 24, 5.4, 2.4))
    s.append(circle(80, 76, 5.4, 2.4))
    s.append(circle(80, 24, 5.4, 2.4))
    s.append(circle(20, 76, 5.4, 2.4))
    # cranium
    s.append(path_d("M50 14 C28 14 16 30 16 46 C16 58 22 64 27 68 L27 74 L73 74 L73 68 C78 64 84 58 84 46 C84 30 72 14 50 14 Z", 2.6))
    # jaw teeth
    for i in range(5):
        x = 33 + i * 8.6
        s.append(line(x, 74, x, 80, 1.3, INK_DIM, 0.9))
    s.append(path_d("M27 80 L73 80", 2.2))
    # eye sockets
    s.append(ellipse(37, 44, 8.5, 9.5, 2.2, INK, "url(#hatchA)"))
    s.append(ellipse(63, 44, 8.5, 9.5, 2.2, INK, "url(#hatchA)"))
    s.append(path_d("M31 40 L43 47", 1.2, INK_DIM, 0.65))
    s.append(path_d("M69 40 L57 47", 1.2, INK_DIM, 0.65))
    # nose
    s.append(path_d("M50 52 L45 62 L55 62 Z", 1.8))
    # teeth lines
    s.append(line(40, 70, 60, 70, 1.2, INK_DIM, 0.8))
    s.append(line(50, 66, 50, 80, 1.1, INK_DIM, 0.7))
    return "".join(s)


def icon_hook() -> str:
    s = []
    # chain
    for i in range(3):
        y = 8 + i * 11
        s.append(ellipse(50, y, 7, 4.6, 2.0, INK, "none", 1.0, -25 if i % 2 else 25))
    s.append(line(50, 20, 50, 34, 2.2))
    # shank + hook
    s.append(path_d("M50 34 L50 54 C50 66 38 70 30 62 C23 55 26 45 34 45", 3.0))
    s.append(path_d("M34 45 L42 52 L30 55", 2.2, INK))
    # barbed tip
    s.append(path_d("M30 62 L37 57", 1.7, CRIMSON))
    # rope wrap
    for i in range(4):
        y = 38 + i * 5
        s.append(path_d(f"M42 {y} L58 {y - 3}", 1.3, GOLD, "none", 0.85))
    return "".join(s)


def icon_tentacle() -> str:
    s = []
    s.append(path_d(
        "M8 12 C34 6 44 26 62 30 C80 34 88 20 84 8", 2.8))
    s.append(path_d(
        "M8 26 C30 20 42 38 58 44 C74 50 90 42 92 28", 2.6))
    s.append(path_d(
        "M10 40 C28 38 38 52 52 60 C66 68 84 64 92 52", 2.4))
    # suckers
    for i, (x, y) in enumerate([(30, 16), (48, 26), (66, 32), (80, 26),
                                (34, 31), (50, 41), (68, 47), (84, 43),
                                (38, 50), (56, 61), (74, 63)]):
        s.append(circle(x, y, 2.6 - (i % 3) * 0.45, 1.2, INK_DIM, "none", 0.9))
    # highlights
    s.append(path_d("M14 18 C36 12 46 32 62 36", 1.0, INK_DIM, "none", 0.5))
    return "".join(s)


def icon_dagger() -> str:
    s = []
    s.append(path_d("M50 8 L60 30 L56 62 L50 72 L44 62 L40 30 Z", 2.4, INK, "url(#hatchA)"))
    s.append(line(50, 14, 50, 68, 1.0, INK, 0.5))
    s.append(path_d("M28 66 L72 66 L66 74 L34 74 Z", 2.3))
    s.append(path_d("M42 74 L58 74 L56 84 L44 84 Z", 2.1))
    s.append(circle(50, 90, 5.0, 2.2))
    s.append(path_d("M46 88 L50 84 L54 88 L50 92 Z", 1.4, CRIMSON))
    return "".join(s)


def icon_compass() -> str:
    s = []
    s.append(circle(50, 50, 36, 2.4))
    s.append(circle(50, 50, 31, 1.1, INK_DIM, "none", 0.7))
    for a in range(0, 360, 15):
        r1 = 31 if a % 45 == 0 else 27
        x1 = 50 + r1 * math.cos(math.radians(a))
        y1 = 50 + r1 * math.sin(math.radians(a))
        x2 = 50 + 36 * math.cos(math.radians(a))
        y2 = 50 + 36 * math.sin(math.radians(a))
        s.append(line(round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2),
                      1.1 if a % 45 == 0 else 0.7, INK if a % 45 == 0 else INK_DIM,
                      0.85 if a % 45 == 0 else 0.5))
    # rose
    s.append(path_d("M50 16 L59 44 L88 50 L59 56 L50 84 L41 56 L12 50 L41 44 Z", 2.2, INK, "url(#hatchA)"))
    s.append(path_d("M50 16 L50 84 M12 50 L88 50", 1.0, INK_DIM, "none", 0.6))
    s.append(circle(50, 50, 3.4, 1.8, CRIMSON))
    s.append(line(50, 6, 50, 12, 1.6))
    return "".join(s)


def icon_shield() -> str:
    s = []
    s.append(path_d("M50 8 L82 20 L82 50 C82 70 68 86 50 94 C32 86 18 70 18 50 L18 20 Z", 2.5))
    s.append(path_d("M50 16 L74 25 L74 50 C74 65 63 78 50 84 C37 78 26 65 26 50 L26 25 Z", 1.3, INK_DIM, "url(#hatchC)", 0.8))
    s.append(path_d("M30 28 L30 50 C30 64 38 74 50 78", 1.1, INK_DIM, "none", 0.55))
    # skull badge
    s.append(path_d("M50 28 C40 28 34 36 34 44 C34 50 37 53 39 55 L39 59 L61 59 L61 55 C63 53 66 50 66 44 C66 36 60 28 50 28 Z", 1.9))
    s.append(circle(44, 43, 3.6, 1.5))
    s.append(circle(56, 43, 3.6, 1.5))
    s.append(path_d("M50 47 L47 52 L53 52 Z", 1.4))
    s.append(line(45, 59, 45, 62, 1.0, INK_DIM, 0.9))
    s.append(line(50, 59, 50, 62, 1.0, INK_DIM, 0.9))
    s.append(line(55, 59, 55, 62, 1.0, INK_DIM, 0.9))
    return "".join(s)


def icon_wrench() -> str:
    s = []
    # spanner
    s.append(path_d("M18 82 L64 36", 5.2))
    s.append(path_d("M56 18 C64 12 76 14 80 22 C84 30 80 40 72 42 L70 34 L62 38 L64 46 C54 48 48 42 50 32 C52 24 50 22 56 18 Z", 2.4))
    # crowbar
    s.append(path_d("M82 84 L40 42", 4.4))
    s.append(path_d("M40 42 L26 30 L22 36 L34 48", 2.2))
    s.append(path_d("M22 36 L16 22", 2.0))
    # sparks
    s.append(line(74, 14, 80, 8, 1.4, GOLD))
    s.append(line(84, 22, 92, 20, 1.2, GOLD))
    s.append(line(70, 8, 70, 2, 1.2, GOLD))
    return "".join(s)


def icon_parrot() -> str:
    s = []
    s.append(path_d("M30 88 C22 70 26 48 40 38 C52 29 70 32 76 46 C82 60 74 74 62 78 C54 81 46 80 40 84", 2.5))
    s.append(path_d("M40 38 C46 26 62 24 70 32 L76 46 C70 40 58 36 48 40 Z", 2.0, INK, "url(#hatchA)"))
    # beak
    s.append(path_d("M74 42 L92 50 L74 54 Z", 2.2, GOLD))
    # eye
    s.append(circle(62, 40, 3.2, 1.5))
    # wing
    s.append(path_d("M40 50 C50 48 60 54 62 66 C56 72 44 70 38 62 Z", 1.7, INK, "url(#hatchB)"))
    # tail
    s.append(path_d("M30 86 L14 92 L22 78 Z", 2.0))
    # feet
    s.append(path_d("M44 84 L42 94 M50 85 L52 94 M60 82 L66 90", 1.7))
    return "".join(s)


def icon_cat() -> str:
    s = []
    s.append(path_d("M28 44 L24 18 L42 30 C48 27 58 27 64 31 L80 20 L78 46 C84 60 80 76 68 84 L36 84 C24 76 22 60 28 44 Z", 2.4))
    # eyes
    s.append(path_d("M38 48 L48 52 L38 58 Z", 1.6, GOLD))
    s.append(path_d("M66 48 L56 52 L66 58 Z", 1.6, GOLD))
    s.append(path_d("M50 60 L47 66 L53 66 Z", 1.3))
    # whiskers
    s.append(line(40, 66, 20, 62, 1.1, INK_DIM, 0.8))
    s.append(line(40, 70, 22, 72, 1.1, INK_DIM, 0.8))
    s.append(line(60, 66, 80, 62, 1.1, INK_DIM, 0.8))
    s.append(line(60, 70, 78, 72, 1.1, INK_DIM, 0.8))
    # laptop
    s.append(path_d("M32 84 L68 84 L74 94 L26 94 Z", 2.2))
    s.append(path_d("M40 80 L60 80", 1.2, INK_DIM, 0.8))
    return "".join(s)


def icon_anchor() -> str:
    s = []
    s.append(circle(50, 12, 5.4, 2.2))
    s.append(line(50, 17, 50, 88, 2.6))
    s.append(line(32, 32, 68, 32, 2.4))
    s.append(path_d("M22 40 C22 68 34 84 50 84 C66 84 78 68 78 40", 2.6))
    s.append(path_d("M22 40 L12 34 L16 48 Z", 2.2, INK, "url(#hatchA)"))
    s.append(path_d("M78 40 L88 34 L84 48 Z", 2.2, INK, "url(#hatchA)"))
    s.append(path_d("M38 26 L62 38", 1.2, INK_DIM, "none", 0.7))
    return "".join(s)


def icon_ship() -> str:
    s = []
    # hull
    s.append(path_d("M14 66 L86 66 L74 86 L26 86 Z", 2.6))
    s.append(path_d("M14 66 L86 66", 2.4))
    s.append(path_d("M26 74 L74 74", 1.0, INK_DIM, "none", 0.55))
    # mast + sails
    s.append(line(50, 8, 50, 66, 2.4))
    s.append(path_d("M50 12 L86 26 L50 40 Z", 2.1, INK, "url(#hatchA)"))
    s.append(path_d("M50 42 L26 52 L50 62 Z", 2.1, INK, "url(#hatchB)"))
    # flag
    s.append(path_d("M50 8 L50 2", 1.8))
    s.append(path_d("M50 3 L68 7 L50 12 Z", 1.6, CRIMSON))
    # waves
    s.append(path_d("M10 90 C18 84 26 96 34 90 C42 84 50 96 58 90 C66 84 74 96 82 90", 1.8, SEA, "none", 0.85))
    return "".join(s)


ICONS = {
    "skull": icon_skull,
    "hook": icon_hook,
    "tentacle": icon_tentacle,
    "dagger": icon_dagger,
    "compass": icon_compass,
    "shield": icon_shield,
    "wrench": icon_wrench,
    "parrot": icon_parrot,
    "cat": icon_cat,
    "anchor": icon_anchor,
    "ship": icon_ship,
}


def icon(name: str, size: int = 64, cls: str = "ic") -> str:
    fn = ICONS.get(name, icon_skull)
    return (
        f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 100 100" '
        f'aria-hidden="true" focusable="false" fill="none" stroke-linecap="round" '
        f'stroke-linejoin="round">{defs()}<g filter="url(#rough2)">{fn()}</g></svg>'
    )


# --------------------------------------------------------------------- hero art
def hero() -> str:
    """Pirate captain at a terminal, parrot on the shoulder, jolly roger behind.

    Everything lives in the right half (x 400-880) so the headline copy on the
    left is never covered by ink.
    """
    s = []

    # ---- faint jolly roger on the back wall
    s.append('<g opacity="0.10" transform="translate(430,60) scale(3.6)">')
    s.append(icon_skull())
    s.append("</g>")

    # ---- anchor on the wall
    s.append('<g transform="translate(748,44) scale(1.15)" opacity="0.55">')
    s.append(icon_anchor())
    s.append("</g>")

    # ---- desk
    s.append(path_d("M392 424 L812 424 L842 462 L368 462 Z", 2.4))
    s.append(path_d("M368 462 L842 462", 2.2))
    s.append(path_d("M410 462 L410 492 M800 462 L800 492", 1.8, INK_DIM, "none", 0.7))

    # ---- captain: shoulders / coat
    s.append(path_d("M556 424 C548 372 556 330 588 308 C612 290 660 288 682 312 C710 342 716 384 708 424", 2.5))
    s.append(path_d("M588 308 L636 368 L612 424 L538 424 L552 344 Z", 2.2, INK, "url(#hatchA)"))
    s.append(path_d("M682 312 L636 368 L660 424 L734 424 L718 348 Z", 2.2, INK, "url(#hatchB)"))
    s.append(path_d("M636 368 L636 424", 1.6, INK_DIM, "none", 0.6))
    for i in range(3):
        s.append(circle(636, 382 + i * 14, 2.2, 1.1, INK, INK, 0.85))

    # ---- neck
    s.append(path_d("M612 296 L612 264 L660 264 L660 296 Z", 2.0, INK, "url(#hatchC)"))

    # ---- head
    s.append(path_d(
        "M600 206 C600 172 616 152 636 152 C656 152 672 172 672 206 "
        "C672 230 668 244 660 254 C652 264 644 268 636 268 "
        "C628 268 620 264 612 254 C604 244 600 230 600 206 Z", 2.4))
    # cheek line
    s.append(path_d("M610 214 C612 232 618 244 628 250", 0.9, INK_DIM, "none", 0.4))
    s.append(path_d("M662 214 C660 232 654 244 644 250", 0.9, INK_DIM, "none", 0.4))

    # ---- tricorn hat
    s.append(path_d("M578 166 C578 132 604 112 636 112 C668 112 694 132 694 166 C672 150 600 150 578 166 Z", 2.4))
    s.append(path_d("M562 168 C588 184 684 184 710 168 C698 194 574 194 562 168 Z", 2.3))
    s.append(path_d("M578 134 C594 118 612 112 636 112 C660 112 678 118 694 134", 1.1, INK_DIM, "none", 0.55))

    # ---- feather
    s.append(path_d("M694 128 C716 110 738 102 754 104 C750 124 738 144 716 156 C708 148 700 138 694 128 Z", 2.0, GOLD, "url(#hatchG)"))
    s.append(line(698, 130, 750, 106, 1.1, INK, 0.65))

    # ---- eyepatch + eye
    s.append(ellipse(613, 204, 10, 8.5, 2.0, INK, "url(#hatchR)"))
    s.append(path_d("M604 200 L590 192", 1.5))
    s.append(path_d("M622 202 C636 190 652 186 668 190", 1.5))
    s.append(ellipse(652, 206, 7.5, 6, 1.8, INK))
    s.append(circle(652, 206, 2.0, 1.0, INK, INK))
    s.append(path_d("M648 203 L656 209 M656 203 L648 209", 0.8, INK, "none", 0.7))

    # ---- nose + mouth
    s.append(path_d("M636 214 L630 230 L642 230", 1.6))
    s.append(path_d("M626 244 C632 249 641 249 647 242", 1.6))

    # ---- beard
    s.append(path_d("M618 238 C622 254 628 262 636 262 C644 262 650 254 654 238 C650 250 644 254 636 254 C628 254 622 250 618 238 Z", 2.0, INK, "url(#hatchB)"))
    s.append(path_d("M622 264 C626 278 631 284 636 284 C641 284 646 278 650 264 C646 274 642 278 636 278 C630 278 626 274 622 264 Z", 1.9, INK, "url(#hatchB)"))
    s.append(line(630, 270, 631, 280, 0.8, INK_DIM, 0.45))
    s.append(line(638, 271, 638, 281, 0.8, INK_DIM, 0.45))

    # ---- hook hand resting on the desk
    s.append(path_d("M712 392 C728 392 736 404 736 416 C736 428 726 434 718 430", 2.5))
    s.append(path_d("M718 430 L730 440", 2.1))

    # ---- laptop in front of the captain
    s.append(path_d("M498 424 L700 424 L722 396 L476 396 Z", 2.4))
    s.append(path_d("M490 396 L708 396", 1.9, INK_DIM, "none", 0.65))
    s.append(path_d("M512 386 L676 386 L670 344 L518 344 Z", 1.9, INK, "none", 0.9))
    s.append(line(526, 358, 566, 358, 1.5, SEA, 0.9))
    s.append(line(526, 367, 590, 367, 1.3, SEA, 0.75))
    s.append(line(526, 376, 548, 376, 1.3, CRIMSON, 0.85))
    s.append(path_d("M532 348 L540 353 L532 358", 1.5, SEA, "none", 0.9))

    # ---- parrot on the captain's shoulder
    s.append('<g transform="translate(676,232) scale(1.0)">')
    s.append(path_d("M30 88 C22 70 26 48 40 38 C52 29 70 32 76 46 C82 60 74 74 62 78 C54 81 46 80 40 84", 2.2))
    s.append(path_d("M40 38 C46 26 62 24 70 32 L76 46 C70 40 58 36 48 40 Z", 1.8, INK, "url(#hatchA)"))
    s.append(path_d("M74 42 L90 50 L74 54 Z", 2.0, GOLD))
    s.append(circle(62, 40, 2.8, 1.3))
    s.append(path_d("M40 50 C50 48 60 54 62 66 C56 72 44 70 38 62 Z", 1.5, INK, "url(#hatchB)"))
    s.append(path_d("M30 86 L17 92 L25 78 Z", 1.8))
    s.append("</g>")

    # ---- mug on the desk
    s.append(path_d("M752 400 L796 400 L792 434 L756 434 Z", 2.0, INK, "url(#hatchC)"))
    s.append(path_d("M796 406 C808 406 808 424 796 424", 1.8))

    # ---- waves below the desk
    s.append(path_d("M300 500 C330 492 358 510 388 502 C418 494 446 512 476 504", 1.7, SEA, "none", 0.5))
    s.append(path_d("M540 506 C570 498 598 516 628 508 C658 500 686 518 716 510", 1.7, SEA, "none", 0.5))

    return "".join(s)


def hero_svg(width: int = 880, height: int = 520) -> str:
    return (
        f'<svg class="hero-art" viewBox="0 0 880 520" width="{width}" height="{height}" '
        f'role="img" aria-label="Pirate captain at a terminal" fill="none" '
        f'stroke-linecap="round" stroke-linejoin="round">{defs()}'
        f'<rect x="0" y="0" width="880" height="520" fill="url(#vign)"/>'
        f'<g filter="url(#rough)">{hero()}</g></svg>'
    )


# --------------------------------------------------------------------- stamps
def stamp(seed: str, size: int = 44) -> str:
    """Deterministic little emblem for one article — chosen by hashing its id."""
    h = hashlib.sha256(seed.encode()).hexdigest()
    rnd = random.Random(int(h[:8], 16))
    names = list(ICONS.keys())
    name = names[rnd.randrange(len(names))]
    rot = rnd.randrange(-14, 15)
    tone = rnd.choice([CRIMSON, GOLD, SEA, INK_DIM])
    body = ICONS[name]()
    # recolour the accent strokes for variety
    body = body.replace(CRIMSON, tone) if tone != CRIMSON else body
    return (
        f'<svg class="stamp" width="{size}" height="{size}" viewBox="0 0 100 100" '
        f'aria-hidden="true" fill="none" stroke-linecap="round" stroke-linejoin="round" '
        f'transform="rotate({rot} 50 50)">{defs()}<g filter="url(#rough2)" opacity="0.85">{body}</g></svg>'
    )


def watermark() -> str:
    """Big faint jolly roger used as a page watermark."""
    return (
        '<svg class="wm" viewBox="0 0 100 100" aria-hidden="true" fill="none" '
        'stroke-linecap="round" stroke-linejoin="round">'
        + defs()
        + '<g filter="url(#rough2)" opacity="0.10">'
        + icon_skull()
        + "</g></svg>"
    )


def ascii_banner(date: str = "") -> str:
    """Fallback decorative ASCII jolly roger."""
    return r"""
        _/\/\/\/\/\/\/\/\/\_
       /                    \
      |   J O L L Y   R O G E R
      |        ___  ___
      |       /   \/   \
      |      |  o  o  |
      |      |   __   |
      |       \  \/  /
        \  ___     ___ /
         \__________/
    """
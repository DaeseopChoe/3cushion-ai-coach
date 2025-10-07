#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mark_extractor.py (v0.3)
------------------------
Compute intermediate cushion contact points (2C / 4C) from CO, 1C, 3C and tip.

Key rules (from field practice you provided):
- For long→long (TOP/BOTTOM rails):
  * Zero-tip:   x_2C = 2*x_1C  - x_CO   (mirror in horizontal line)
  * +k tip:     x_2C += k * 5  (grid)
- For short→short (LEFT/RIGHT rails):
  * Zero-tip:   y_2C = 2*y_1C  - y_CO   (mirror in vertical line)
  * +k tip:     y_2C += k * 10 (grid)
- Same rules apply for 3C→4C.
- Tip sign: + = right, − = left. (We treat tip as signed float in [-4, 4].)
- Coordinates for 2C/4C lie on frame constants (Fg):
  * long-long → y = -2.25 (BOTTOM) if 1C was TOP, or y = 42.25 (TOP) if 1C was BOTTOM
  * short-short → x = -2.25 (LEFT) if 1C was RIGHT, or x = 82.25 (RIGHT) if 1C was LEFT
- Clamp along-rail coordinate to table playable span (0..80 for x on long rails, 0..40 for y on short rails).

Examples encoded (should match your cases):
- CO_(40,-2.25) → 1C_(40,42.25)
  tip=0  → 2C_(40,-2.25)
  tip=+1 → 2C_(45,-2.25)
  tip=+2 → 2C_(50,-2.25)
  tip=+3 → 2C_(55,-2.25)
  tip=+4 → 2C_(60,-2.25)

- CO_(20,-2.25) → 1C_(40,42.25)
  tip=0  → 2C_(60,-2.25)  # 2*40 - 20 = 60
  tip=+1 → 2C_(65,-2.25)
  tip=+2 → 2C_(70,-2.25)
  tip=+3 → 2C_(75,-2.25)
  tip=+4 → 2C_(80,-2.25)

- CO_(-2.25,0) → 1C_(82.25,10) [short→short]
  tip=0  → 2C_(-2.25,20)  # 2*10 - 0 = 20
  tip=+1 → 2C_(-2.25,30)
  tip=+2 → 2C_(-2.25,40)

Usage:
  python common/tools/mark_extractor.py --co 20 -2.25 --c1 40 42.25 --tip 2
  python common/tools/mark_extractor.py --c3 11 0 --tip3 1  # compute 4C from 3C

Output (JSON):
{
  "calc": {
    "mode": "long-long" | "short-short",
    "rule": "zero_tip_mirror + tip_offset",
    "unit": 5 or 10
  },
  "C2": {"x":.., "y":..},
  "C4": {"x":.., "y":..}
}
"""
from __future__ import annotations
import argparse, json
from dataclasses import dataclass

TOL = 0.02
# Frame constants (Fg)
FG_Y_BOTTOM = -2.25
FG_Y_TOP    =  42.25
FG_X_LEFT   =  -2.25
FG_X_RIGHT  =  82.25
# Rail playable spans (Rg)
X_MIN, X_MAX = 0.0, 80.0
Y_MIN, Y_MAX = 0.0, 40.0

@dataclass
class SpinReflection:
    long_unit: float = 5.0    # per tip for long→long
    short_unit: float = 10.0  # per tip for short→short
    tip_min: float = -4.0
    tip_max: float = 4.0
    clamp_table: bool = True

SR_DEFAULT = SpinReflection()

def near(a: float, b: float, tol: float = TOL) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False

# ---------- core helpers ----------

def _clamp_long(x: float) -> float:
    return max(X_MIN, min(X_MAX, x))

def _clamp_short(y: float) -> float:
    return max(Y_MIN, min(Y_MAX, y))


def compute_2c_from_co_c1(co: tuple[float,float], c1: tuple[float,float], tip: float,
                          sr: SpinReflection = SR_DEFAULT) -> tuple[dict, dict]:
    """Return (C2 point, calc_info)."""
    x0, y0 = float(co[0]), float(co[1])
    x1, y1 = float(c1[0]), float(c1[1])
    tip = max(sr.tip_min, min(sr.tip_max, float(tip)))

    # Determine rail side at 1C
    if near(y1, FG_Y_TOP) or near(y1, FG_Y_BOTTOM):
        mode = "long-long"
        # zero-tip mirror (horizontal line): x2 = 2*x1 - x0
        x2 = 2.0 * x1 - x0
        x2 += sr.long_unit * tip
        if sr.clamp_table:
            x2 = _clamp_long(x2)
        # target y on opposite long rail
        y2 = FG_Y_BOTTOM if near(y1, FG_Y_TOP) else FG_Y_TOP
        return ({"x": x2, "y": y2}, {"mode": mode, "rule": "zero_tip_mirror + tip_offset", "unit": sr.long_unit})

    if near(x1, FG_X_LEFT) or near(x1, FG_X_RIGHT):
        mode = "short-short"
        # zero-tip mirror (vertical line): y2 = 2*y1 - y0
        y2 = 2.0 * y1 - y0
        y2 += sr.short_unit * tip
        if sr.clamp_table:
            y2 = _clamp_short(y2)
        # target x on opposite short rail
        x2 = FG_X_LEFT if near(x1, FG_X_RIGHT) else FG_X_RIGHT
        return ({"x": x2, "y": y2}, {"mode": mode, "rule": "zero_tip_mirror + tip_offset", "unit": sr.short_unit})

    raise ValueError("1C is not on a frame constant line (Fg).")


def compute_4c_from_3c(c3: tuple[float,float], tip3: float,
                       sr: SpinReflection = SR_DEFAULT) -> tuple[dict, dict]:
    """Return (C4 point, calc_info). Same rule as 1C→2C, applied to 3C→4C."""
    x3, y3 = float(c3[0]), float(c3[1])
    tip3 = max(sr.tip_min, min(sr.tip_max, float(tip3)))

    if near(y3, FG_Y_TOP) or near(y3, FG_Y_BOTTOM):
        mode = "long-long"
        # zero-tip mirror across horizontal line from a symmetric previous point is not defined here,
        # but 3C alone defines the rail; for 4C we only add tip offset along x on opposite long rail.
        x4 = x3 + sr.long_unit * tip3
        if sr.clamp_table:
            x4 = _clamp_long(x4)
        y4 = FG_Y_BOTTOM if near(y3, FG_Y_TOP) else FG_Y_TOP
        return ({"x": x4, "y": y4}, {"mode": mode, "rule": "tip_offset_only", "unit": sr.long_unit})

    if near(x3, FG_X_LEFT) or near(x3, FG_X_RIGHT):
        mode = "short-short"
        y4 = y3 + sr.short_unit * tip3
        if sr.clamp_table:
            y4 = _clamp_short(y4)
        x4 = FG_X_LEFT if near(x3, FG_X_RIGHT) else FG_X_RIGHT
        return ({"x": x4, "y": y4}, {"mode": mode, "rule": "tip_offset_only", "unit": sr.short_unit})

    raise ValueError("3C is not on a frame constant line (Fg).")

# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--co", nargs=2, type=float, metavar=("X","Y"))
    ap.add_argument("--c1", nargs=2, type=float, metavar=("X","Y"))
    ap.add_argument("--c3", nargs=2, type=float, metavar=("X","Y"))
    ap.add_argument("--tip", type=float, default=None, help="tip for 1C→2C (-4..4)")
    ap.add_argument("--tip3", type=float, default=None, help="tip for 3C→4C (-4..4)")
    ap.add_argument("--long_unit", type=float, default=5.0)
    ap.add_argument("--short_unit", type=float, default=10.0)
    ap.add_argument("--no_clamp", action="store_true")
    args = ap.parse_args()

    sr = SpinReflection(long_unit=args.long_unit, short_unit=args.short_unit,
                        tip_min=-4.0, tip_max=4.0, clamp_table=not args.no_clamp)

    out = {"calc": {"rule": "zero_tip_mirror + tip_offset", "units": {"long": sr.long_unit, "short": sr.short_unit}}}

    if args.co and args.c1 and args.tip is not None:
        C2, info = compute_2c_from_co_c1(tuple(args.co), tuple(args.c1), args.tip, sr)
        out.update({"C2": C2}); out["calc"].update(info)

    if args.c3 and args.tip3 is not None:
        C4, info4 = compute_4c_from_3c(tuple(args.c3), args.tip3, sr)
        out.update({"C4": C4, "calc_4C": info4})

    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

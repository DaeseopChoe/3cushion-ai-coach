#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
track_selector.py  (Sunrise–Sunset MVP)
- CO, 1C, 3C 좌표를 받아 sys를 보간(clamp)하고, profile의 formula로 HP_n 산출
- 3C 수평(y≈0/40)과 수직(x≈0/80) 레일 모두 지원 (value=x 또는 value=y)
- 외삽 금지, 선형 보간 + 클램프
"""

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

TOL = 0.02

# Frame constants (Fg) and Rail constants (Rg)
FG_Y_BOTTOM = -2.25
FG_Y_TOP = 42.25
RG_Y_BOTTOM = 0.0
RG_Y_TOP = 40.0
RG_X_LEFT = 0.0
RG_X_RIGHT = 80.0

# -------- utilities --------

def near(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

# -------- anchors parsing --------

ANCHOR_ID_RE = re.compile(r"^([A-Za-z0-9]+)_\(([-\d\.]+),([-\d\.]+)\)_([-\d]+)$")

@dataclass
class Anchor:
    sym: str
    x: float
    y: float
    sys: int

def parse_anchor_id(id_str: str) -> Optional[Anchor]:
    m = ANCHOR_ID_RE.match(id_str.strip())
    if not m:
        return None
    sym, xs, ys, ns = m.groups()
    return Anchor(sym=sym, x=float(xs), y=float(ys), sys=int(ns))

def load_anchors(anchors_path: str) -> Dict[str, List[Anchor]]:
    """
    returns: { track_name: [Anchor, ...] }
    """
    data = json.loads(Path(anchors_path).read_text(encoding="utf-8"))
    tracks = {}
    traj = data.get("trajectories", {})
    for tname, tblock in traj.items():
        arr = []
        for obj in tblock.get("anchors", []):
            if "id" not in obj:
                continue
            a = parse_anchor_id(obj["id"])
            if a:
                arr.append(a)
        tracks[tname] = arr
    return tracks

# -------- linear interpolation on (value -> sys) --------

def interp_sys(points: List[Tuple[float, float]], value: float) -> float:
    """
    points: list of (value_coord, sys)
    value: query coord
    clamp to ends
    """
    if not points:
        raise ValueError("no points for interpolation")
    pts = sorted(points, key=lambda p: p[0])
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    # clamp
    if value <= xs[0]:
        return ys[0]
    if value >= xs[-1]:
        return ys[-1]
    # find segment
    for i in range(len(xs) - 1):
        if xs[i] <= value <= xs[i + 1]:
            x0, y0 = xs[i], ys[i]
            x1, y1 = xs[i + 1], ys[i + 1]
            if near(x1, x0):
                return (y0 + y1) / 2.0
            t = (value - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    # fallback (should not reach)
    return ys[-1]

# -------- grouping helpers --------

def group_on_constant_y(anchors: List[Anchor], y_ref: float) -> List[Anchor]:
    return [a for a in anchors if near(a.y, y_ref)]

def group_on_constant_x(anchors: List[Anchor], x_ref: float) -> List[Anchor]:
    return [a for a in anchors if near(a.x, x_ref)]

# -------- sys lookup per symbol --------

def sys_from_CO(track_anchors: List[Anchor], x: float, y: float) -> float:
    """
    CO는 Fg 하단 상수선(y≈-2.25) 또는 상단(y≈42.25)에서 value=x로 가정.
    (앵커는 Fg 좌표로 저장된 라벨을 사용)
    """
    if near(y, FG_Y_BOTTOM) or near(y, FG_Y_TOP):
        grp = group_on_constant_y([a for a in track_anchors if a.sym == "CO"], y)
        if not grp:
            raise ValueError("no CO anchors on this frame constant line")
        pts = [(a.x, a.sys) for a in grp]
        return interp_sys(pts, x)
    raise ValueError(f"CO must be on Fg y≈{FG_Y_BOTTOM} or {FG_Y_TOP}; got y={y}")

def sys_from_1C(track_anchors: List[Anchor], x: float, y: float) -> float:
    """
    1C는 Fg 상단(y≈42.25) 또는 하단(y≈-2.25) 상수선에서 value=x.
    """
    if near(y, FG_Y_TOP) or near(y, FG_Y_BOTTOM):
        grp = group_on_constant_y([a for a in track_anchors if a.sym == "1C"], y)
        if not grp:
            raise ValueError("no 1C anchors on this frame constant line")
        pts = [(a.x, a.sys) for a in grp]
        return interp_sys(pts, x)
    raise ValueError(f"1C must be on Fg y≈{FG_Y_TOP} or {FG_Y_BOTTOM}; got y={y}")

def sys_from_3C(track_anchors: List[Anchor], x: float, y: float) -> float:
    """
    3C는 Rg 수평(y≈0/40) 또는 수직(x≈0/80) 레일 상수선 중 하나여야 함.
    - 수평이면 value=x로 보간
    - 수직이면 value=y로 보간
    """
    A = [a for a in track_anchors if a.sym == "3C"]

    # horizontal rails
    if near(y, RG_Y_BOTTOM) or near(y, RG_Y_TOP):
        grp = group_on_constant_y(A, y)
        if not grp:
            raise ValueError("no 3C anchors on horizontal rail for this track")
        pts = [(a.x, a.sys) for a in grp]  # value=x
        return interp_sys(pts, x)

    # vertical rails
    if near(x, RG_X_LEFT) or near(x, RG_X_RIGHT):
        grp = group_on_constant_x(A, x)
        if not grp:
            raise ValueError("no 3C anchors on vertical rail for this track")
        pts = [(a.y, a.sys) for a in grp]  # value=y
        return interp_sys(pts, y)

    raise ValueError(f"3C must be on Rg y≈0/40 or x≈0/80; got (x,y)=({x},{y})")

# -------- track selection (very light heuristic for MVP) --------

def select_base_from_CO(co_y: float) -> str:
    if near(co_y, FG_Y_BOTTOM):
        return "B2T"
    if near(co_y, FG_Y_TOP):
        return "T2B"
    # fallback
    return "B2T"

def select_turn_from_CO_1C(co_x: float, c1_x: float) -> str:
    dx = c1_x - co_x
    if dx > +TOL:
        return "R"
    if dx < -TOL:
        return "L"
    return "L"

def to_track_name(base: str, turn: str) -> str:
    if base == "B2T" and turn == "L":
        return "B2T_L"
    if base == "B2T" and turn == "R":
        return "B2T_R"
    if base == "T2B" and turn == "L":
        return "T2B_L"
    if base == "T2B" and turn == "R":
        return "T2B_R"
    return "B2T_L"

# -------- HP evaluation --------

def eval_hp(profile_path: str, CO_f: float, C1_f: float, C3_r: float) -> float:
    """
    MVP: profile.formula == 'CO_f + 1C_f + 3C_r = HP_n'
    """
    prof = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    # tip guard
    tr = prof.get("safety", {}).get("tip_range", {})
    tmin = tr.get("min", -4)
    tmax = tr.get("max", 4)
    # clamp inputs individually is optional; typically HP에만 가드 적용
    hp = CO_f + C1_f + C3_r
    # HP 자체에 guard를 적용하려면 아래 줄을 유지
    hp = clamp(hp, tmin + (-9999), tmax + 9999)  # 사실상 노가드; 표시에만 사용 권장
    return hp

# -------- main --------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchors", required=True, help="anchors.json")
    ap.add_argument("--profile", required=True, help="profile_sunrise_sunset.json")
    ap.add_argument("--co", nargs=2, type=float, metavar=("X", "Y"), required=True)
    ap.add_argument("--c1", nargs=2, type=float, metavar=("X", "Y"), required=True)
    ap.add_argument("--c3", nargs=2, type=float, metavar=("X", "Y"), required=True)
    args = ap.parse_args()

    tracks = load_anchors(args.anchors)

    co_x, co_y = args.co
    c1_x, c1_y = args.c1
    c3_x, c3_y = args.c3

    base = select_base_from_CO(co_y)
    turn = select_turn_from_CO_1C(co_x, c1_x)
    track_name = to_track_name(base, turn)

    if track_name not in tracks or not tracks[track_name]:
        # fallback: 가장 근접한 B2T_L을 사용
        track_name = "B2T_L"

    tanchors = tracks[track_name]

    CO_f = sys_from_CO(tanchors, co_x, co_y)
    C1_f = sys_from_1C(tanchors, c1_x, c1_y)
    C3_r = sys_from_3C(tanchors, c3_x, c3_y)

    hp = eval_hp(args.profile, CO_f, C1_f, C3_r)

    print(json.dumps({
        "selected_track": track_name,
        "CO_f": CO_f,
        "1C_f": C1_f,
        "3C_r": C3_r,
        "HP_n": hp
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

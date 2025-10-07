#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
입력: system_logic.json, anchors.json(lookup_table), profile_<system>.json(옵션), test_cases.json
역할: 각 케이스에 대해 sys 보간(좌표→sys), HP 계산, 기대값과 비교
제한: MVP용 최소 구현 (수평/수직 레일 선형보간, clamp, no extrapolation)
"""
import argparse, json, math
from bisect import bisect_left

TOL = 1e-6
HP_TOL = 1e-3

def find_group(sym, rail, axis, space):
    for g in sym.get("groups", []):
        if g.get("rail")==rail and g.get("axis")==axis and g.get("space")==space:
            return g
    return None

def rail_of_Fg(x,y):
    # returns (rail, axis)
    if abs(y + 2.25) <= 0.02: return ("BOTTOM","long")
    if abs(y - 42.25) <= 0.02: return ("TOP","long")
    if abs(x + 2.25) <= 0.02: return ("LEFT","short")
    if abs(x - 82.25) <= 0.02: return ("RIGHT","short")
    return (None,None)

def rail_of_Rg(x,y):
    if abs(y - 0.0)  <= 0.02: return ("BOTTOM","long")
    if abs(y - 40.0) <= 0.02: return ("TOP","long")
    if abs(x - 0.0)  <= 0.02: return ("LEFT","short")
    if abs(x - 80.0) <= 0.02: return ("RIGHT","short")
    return (None,None)

def interp_value_to_sys(points, value):
    # points: list of dicts {"sys":s, "value":v}; returns sys via piecewise-linear inverse, with clamp
    if not points: raise ValueError("no points for interpolation")
    pts = sorted([(p["value"], p["sys"]) for p in points])
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    i = bisect_left(xs, value)
    if i <= 0:   return ys[0]
    if i >= len(xs): return ys[-1]
    x0,x1 = xs[i-1], xs[i]
    y0,y1 = ys[i-1], ys[i]
    if abs(x1-x0) < TOL: return y0
    t = (value - x0) / (x1 - x0)
    return y0 + t*(y1-y0)

def compute_hp(co_sys, c1_sys, c3_sys, profile=None):
    # Sunrise–Sunset: HP = CO_f + 1C_f + 3C_r
    return co_sys + c1_sys + c3_sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("system_logic")
    ap.add_argument("anchors")
    ap.add_argument("cases")
    ap.add_argument("--profile", help="profile_<system>.json (optional)")
    args = ap.parse_args()

    with open(args.system_logic, "r", encoding="utf-8") as f: syslogic = json.load(f)
    with open(args.anchors, "r", encoding="utf-8") as f: anchors = json.load(f)
    with open(args.cases, "r", encoding="utf-8") as f: cases = json.load(f)
    profile = None
    if args.profile:
        with open

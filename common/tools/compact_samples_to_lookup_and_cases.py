#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
입력:  compact samples 텍스트 (예: CO_(60,-2.25)_2, 1C_(20,42.25)_0, 3C_(11,0)_2 = HP_4)
출력1: anchors.json 의 lookup_table.symbols 보강(수평/수직 레일 자동 분류)
출력2: test_cases.json (calc 검증용)
주의: anchors.json의 schema가 다르면 최소 필드만 병합합니다.
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

S_RE = re.compile(
    r'\s*CO_\(([-\d\.]+),([-\d\.]+)\)_([-\d\.]+)\s*,\s*'
    r'1C_\(([-\d\.]+),([-\d\.]+)\)_([-\d\.]+)\s*,\s*'
    r'3C_\(([-\d\.]+),([-\d\.]+)\)_([-\d\.]+)\s*=\s*HP_([-\d\.]+)\s*$'
)

TOL = 0.02

def near(v, tgt):
    return abs(float(v) - tgt) <= TOL

def rail_of(space, x, y):
    x = float(x); y = float(y)
    if space == "Fg":
        if near(y, -2.25):   return ("BOTTOM", "long", "Fg", -2.25)
        if near(y, 42.25):   return ("TOP",    "long", "Fg",  42.25)
        if near(x, -2.25):   return ("LEFT",   "short","Fg", -2.25)
        if near(x, 82.25):   return ("RIGHT",  "short","Fg",  82.25)
    else:
        if near(y, 0.0):     return ("BOTTOM", "long", "Rg",   0.0)
        if near(y, 40.0):    return ("TOP",    "long", "Rg",  40.0)
        if near(x, 0.0):     return ("LEFT",   "short","Rg",   0.0)
        if near(x, 80.0):    return ("RIGHT",  "short","Rg",  80.0)
    return (None, None, space, None)

def parse_samples(fp):
    cases = []
    with open(fp, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#"): continue
            m = S_RE.match(ln)
            if not m: 
                print(f"[WARN] skip unrecognized line: {ln}", file=sys.stderr)
                continue
            COx, COy, COs, C1x, C1y, C1s, C3x, C3y, C3s, HP = m.groups()
            cases.append({
                "CO": {"x": float(COx), "y": float(COy), "sys": float(COs)},
                "1C": {"x": float(C1x), "y": float(C1y), "sys": float(C1s)},
                "3C": {"x": float(C3x), "y": float(C3y), "sys": float(C3s)},
                "HP": float(HP)
            })
    return cases

def ensure_lookup(anchors):
    anchors.setdefault("lookup_table", {})
    anchors["lookup_table"].setdefault("symbols", {})
    for k in ("CO_f","1C_f","3C_r"):
        anchors["lookup_table"]["symbols"].setdefault(k, {"groups": []})

def upsert_group(sym, rail, axis, space, const):
    for g in sym["groups"]:
        if g.get("rail")==rail and g.get("axis")==axis and g.get("space")==space and g.get("const")==const:
            return g
    g = {"rail": rail, "axis": axis, "space": space, "const": const, "points": []}
    sym["groups"].append(g)
    return g

def add_point(group, sys_v, x, y):
    # value is x for horizontal(long), y for vertical(short)
    val = float(x) if group["axis"]=="long" else float(y)
    group["points"].append({"sys": float(sys_v), "value": val})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("samples", help="compact samples txt")
    ap.add_argument("--anchors", required=True, help="anchors.json to load")
    ap.add_argument("--out-lookup", required=True, help="anchors.json to write (in-place or new)")
    ap.add_argument("--out-cases", required=True, help="test_cases.json to write")
    args = ap.parse_args()

    cases = parse_samples(args.samples)
    with open(args.anchors, "r", encoding="utf-8") as f:
        anchors = json.load(f)

    ensure_lookup(anchors)
    sym_CO = anchors["lookup_table"]["symbols"]["CO_f"]
    sym_C1 = anchors["lookup_table"]["symbols"]["1C_f"]
    sym_C3 = anchors["lookup_table"]["symbols"]["3C_r"]

    for c in cases:
        # CO, 1C : Fg
        rail, axis, space, const = rail_of("Fg", c["CO"]["x"], c["CO"]["y"])
        g = upsert_group(sym_CO, rail, axis, space, const)
        add_point(g, c["CO"]["sys"], c["CO"]["x"], c["CO"]["y"])

        rail, axis, space, const = rail_of("Fg", c["1C"]["x"], c["1C"]["y"])
        g = upsert_group(sym_C1, rail, axis, space, const)
        add_point(g, c["1C"]["sys"], c["1C"]["x"], c["1C"]["y"])

        # 3C : Rg
        rail, axis, space, const = rail_of("Rg", c["3C"]["x"], c["3C"]["y"])
        g = upsert_group(sym_C3, rail, axis, space, const)
        add_point(g, c["3C"]["sys"], c["3C"]["x"], c["3C"]["y"])

    # write outputs
    with open(args.out_lookup, "w", encoding="utf-8") as f:
        json.dump(anchors, f, ensure_ascii=False, indent=2)

    # minimal test cases: coordinates only + expected HP
    tc = [{"CO":c["CO"], "1C":c["1C"], "3C":c["3C"], "HP":c["HP"]} for c in cases]
    with open(args.out_cases, "w", encoding="utf-8") as f:
        json.dump({"cases": tc}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()

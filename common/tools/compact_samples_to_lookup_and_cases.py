#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compact_samples_to_lookup_and_cases.py (flat symbols version)

- Compact samples(txt) -> test cases(JSON)
- Merge vertical 3C (x=0/80 & sys<0) points into anchors.lookup_table.symbols (flat):
    - B2T: 3C_r_LEFT_B2T / 3C_r_RIGHT_B2T
    - T2B: 3C_r_LEFT_T2B / 3C_r_RIGHT_T2B
- CO_f / 1C_f / 3C_r 등의 기존 심볼은 'points' (리스트)만 가진 평면 구조를 사용.
- 주석 포함 anchors.json도 로드 가능(// 라인 무시).
"""

import argparse, json, re
from pathlib import Path
from typing import List, Dict, Any

LINE_RE = re.compile(
    r"\s*CO_\(([-\d\.]+),([-\d\.]+)\)_([-\d]+)\s*,\s*"
    r"1C_\(([-\d\.]+),([-\d\.]+)\)_([-\d]+)\s*,\s*"
    r"3C_\(([-\d\.]+),([-\d\.]+)\)_([-\d]+)\s*=\s*HP_([-\d]+)\s*$"
)

FG_Y_BOTTOM = -2.25
FG_Y_TOP = 42.25
TOL = 0.02

def near(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol

def strip_json_comments(txt: str) -> str:
    out = []
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith("//"):
            continue
        out.append(line)
    return "\n".join(out)

def load_json_with_comments(path: str) -> Dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(strip_json_comments(raw))

def ensure_symbol(lookup: Dict[str, Any], key: str, space: str, rail: str, axis: str):
    if key not in lookup or not isinstance(lookup[key], dict):
        lookup[key] = {"space": space, "rail": rail, "axis": axis, "points": []}
    lookup[key].setdefault("points", [])

def merge_points(dst_points: List[Dict[str, float]], new_points: List[Dict[str, float]]):
    # sys 값 기준으로 upsert
    index = {p["sys"]: i for i, p in enumerate(dst_points)}
    for p in new_points:
        if p["sys"] in index:
            dst_points[index[p["sys"]]] = p
        else:
            dst_points.append(p)
    dst_points.sort(key=lambda d: d["sys"])

def parse_samples(path: str):
    """compact sample 줄을 파싱하여 케이스와 수직 3C 포인트 수집"""
    cases = []
    L_B2T: List[Dict[str, float]] = []
    R_B2T: List[Dict[str, float]] = []
    L_T2B: List[Dict[str, float]] = []
    R_T2B: List[Dict[str, float]] = []

    for lineno, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = LINE_RE.match(s)
        if not m:
            # 형식과 다른 줄은 무시
            continue

        COx, COy, COsys, C1x, C1y, C1sys, C3x, C3y, C3sys, HP = m.groups()
        COx, COy, C1x, C1y, C3x, C3y = map(float, (COx, COy, C1x, C1y, C3x, C3y))
        COsys, C1sys, C3sys, HP = map(int, (COsys, C1sys, C3sys, HP))

        base = "B2T" if near(COy, FG_Y_BOTTOM) else ("T2B" if near(COy, FG_Y_TOP) else None)

        # 수직 3C (x=0/80) & 음수 sys 수집
        if C3sys < 0:
            if abs(C3x - 0.0) < 1e-9:
                (L_B2T if base == "B2T" else L_T2B).append({"sys": C3sys, "value": C3y})
            if abs(C3x - 80.0) < 1e-9:
                (R_B2T if base == "B2T" else R_T2B).append({"sys": C3sys, "value": C3y})

        cases.append({
            "CO_f": COsys,
            "1C_f": C1sys,
            "3C_r": C3sys,
            "expected_HP_n": HP,
            "raw": {
                "CO": {"x": COx, "y": COy, "sys": COsys, "space": "Fg"},
                "1C": {"x": C1x, "y": C1y, "sys": C1sys, "space": "Fg"},
                "3C": {"x": C3x, "y": C3y, "sys": C3sys, "space": "Rg"}
            }
        })

    # sys 키 기준 중복 제거 후 정렬
    def dedup(points: List[Dict[str, float]]):
        d = {p["sys"]: p["value"] for p in points}
        out = [{"sys": k, "value": v} for k, v in d.items()]
        out.sort(key=lambda d: d["sys"])
        return out

    return cases, dedup(L_B2T), dedup(R_B2T), dedup(L_T2B), dedup(R_T2B)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("samples", help="compact samples txt")
    ap.add_argument("--anchors", required=True, help="anchors.json to merge with (comments allowed)")
    ap.add_argument("--out-lookup", required=True, help="output anchors with merged lookup_table")
    ap.add_argument("--out-cases", required=True, help="output test cases json")
    args = ap.parse_args()

    cases, L_B2T, R_B2T, L_T2B, R_T2B = parse_samples(args.samples)

    anchors = load_json_with_comments(args.anchors)
    lookup = anchors.setdefault("lookup_table", {}).setdefault("symbols", {})

    # 기본 심볼 보장 (flat)
    ensure_symbol(lookup, "CO_f", "Fg", "BOTTOM", "long")
    ensure_symbol(lookup, "1C_f", "Fg", "TOP", "long")
    ensure_symbol(lookup, "3C_r", "Rg", "BOTTOM", "long")

    # 수직 3C(음수 sys) per-base 보장
    ensure_symbol(lookup, "3C_r_LEFT_B2T",  "Rg", "LEFT",  "short")
    ensure_symbol(lookup, "3C_r_RIGHT_B2T", "Rg", "RIGHT", "short")
    ensure_symbol(lookup, "3C_r_LEFT_T2B",  "Rg", "LEFT",  "short")
    ensure_symbol(lookup, "3C_r_RIGHT_T2B", "Rg", "RIGHT", "short")

    # 병합
    if L_B2T: merge_points(lookup["3C_r_LEFT_B2T"]["points"], L_B2T)
    if R_B2T: merge_points(lookup["3C_r_RIGHT_B2T"]["points"], R_B2T)
    if L_T2B: merge_points(lookup["3C_r_LEFT_T2B"]["points"], L_T2B)
    if R_T2B: merge_points(lookup["3C_r_RIGHT_T2B"]["points"], R_T2B)

    # 산출 저장
    Path(args.out_lookup).write_text(json.dumps(anchors, ensure_ascii=False, indent=2), encoding="utf-8")

    out_cases = {
        "system": "Sunrise–Sunset",
        "formula": "CO_f + 1C_f + 3C_r = HP_n",
        "cases": cases,
        "meta": {"generator": "compact_samples_to_lookup_and_cases.py"}
    }
    Path(args.out_cases).write_text(json.dumps(out_cases, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] merged lookup saved to: {args.out_lookup}")
    print(f"[ok] test cases saved to: {args.out_cases}")
    print(f"[info] vertical 3C merged: L_B2T={L_B2T}, R_B2T={R_B2T}, L_T2B={L_T2B}, R_T2B={R_T2B}")

if __name__ == "__main__":
    main()

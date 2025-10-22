# 7_system_simulator.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
7_system_simulator.py
- 구조: 5_half_system 기반
- 공식: 1C_f = CO_f * 3C_f
- 규약 v1.3 호환
"""

import json, pathlib, argparse
from typing import Dict, Any, List

def load_json(path: str) -> Dict[str, Any]:
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")
    return json.loads(p.read_text(encoding="utf-8"))

def interp(val: float, xs: List[float], ys: List[float]) -> float:
    if val <= xs[0]:
        return ys[0]
    if val >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= val <= xs[i + 1]:
            x0, x1 = xs[i], xs[i + 1]
            y0, y1 = ys[i], ys[i + 1]
            if x1 == x0:
                return y0
            return y0 + (y1 - y0) * (val - x0) / (x1 - x0)
    raise ValueError("보간 실패")

def compute_mark(anchors: Dict[str, Any], co_x: float, c3_y: float) -> Dict[str, Any]:
    co_table = {10: 1, 20: 2, 30: 2.5, 40: 3, 50: 3.5, 60: 4, 70: 4.5, 82.25: 5}
    c3_table = {40: 4, 33.3: 5, 26.7: 6, 20: 7, 13.3: 8, 6.7: 9, 0: 10}

    xs_co, ys_co = list(co_table.keys()), list(co_table.values())
    ys_3c, vs_3c = list(c3_table.keys()), list(c3_table.values())

    co_sys = interp(co_x, xs_co, ys_co)
    c3_sys = interp(c3_y, ys_3c, vs_3c)

    one_c_sys = co_sys * c3_sys
    min_val = min(ys_co) * min(vs_3c)
    max_val = max(ys_co) * max(vs_3c)
    one_c_sys = max(min(one_c_sys, max_val), min_val)

    return {
        "formula": "1C_f = CO_f * 3C_f",
        "CO_sys": co_sys,
        "3C_sys": c3_sys,
        "1C_sys": one_c_sys,
        "meta": {"clamped": True, "no_extrapolation": True}
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchors", required=True, help="7_system_anchors.json 경로")
    ap.add_argument("--profile", required=True, help="profile_7_system.json 경로")
    ap.add_argument("--co", required=True, type=float, help="CO의 x_fg 값 (예: 40)")
    ap.add_argument("--c3", required=True, type=float, help="3C의 y_fg 값 (예: 20)")
    args = ap.parse_args()

    anchors = load_json(args.anchors)
    profile = load_json(args.profile)

    result = compute_mark(anchors, args.co, args.c3)
    result["profile"] = profile["system"]

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

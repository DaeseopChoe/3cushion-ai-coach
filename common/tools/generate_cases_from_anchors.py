#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_cases_from_anchors.py
- anchors.json 의 라벨을 이용해 샘플 케이스(JSON)를 생성합니다.
- 기본은 트랙 일치 테스트에 초점( expect.track ).
- profile.formula 가 유효하면, 앵커 sys 로 HP_n도 계산하여 expect.sys 에 넣을 수 있습니다(--with-formula).

Usage
-----
python common/tools/generate_cases_from_anchors.py \
  --anchors systems/sunrise_sunset/anchors.json \
  --logic   systems/sunrise_sunset/system_logic.json \
  --outdir  tests/sunrise_sunset/cases \
  --per-track 5 --with-formula

Options
-------
--per-track N      : 트랙별 케이스 수(기본 3)
--with-formula     : profile 공식이 유효하면 HP_n 기대값을 넣음
--seed SEED        : 난수 시드
"""
from __future__ import annotations
import argparse, json, random, re
from pathlib import Path
from typing import Dict, Any, List, Tuple

LABEL_RX = re.compile(r"^([A-Z0-9]+)_\(([-+]?\d+(?:\.\d+)?),([-+]?\d+(?:\.\d+)?)\)_([-+]?\d+(?:\.\d+)?)$")

TRACKS = ("B2T_L", "B2T_R", "T2B_L", "T2B_R")

# 상수선
FG_BOTTOM_Y, FG_TOP_Y = -2.25, 42.25
RG_BOTTOM_Y, RG_TOP_Y = 0.0, 40.0
FG_LEFT_X, FG_RIGHT_X = -2.25, 82.25
RG_LEFT_X, RG_RIGHT_X = 0.0, 80.0
TOL = 0.02

def near(a, b, t=TOL):
    try: return abs(float(a)-float(b)) <= t
    except: return False

# -------------- helpers --------------

def parse_labels(anchors_doc: Dict[str, Any]) -> Dict[str, Dict[str, List[Tuple[float,float]]]]:
    """트랙별로 { 'CO':[(x,y,n),...], '1C':[...], '3C':[...]} 수집"""
    out = {t: {"CO": [], "1C": [], "3C": []} for t in TRACKS}
    for trk, blk in (anchors_doc.get("trajectories") or {}).items():
        if trk not in out: continue
        for it in (blk.get("anchors") or []):
            m = LABEL_RX.match((it.get("id") or "").strip())
            if not m: continue
            ID, xs, ys, ns = m.groups()
            x, y, n = float(xs), float(ys), float(ns)
            if ID.startswith("CO"): out[trk]["CO"].append((x,y,n))
            elif ID.startswith("1C"): out[trk]["1C"].append((x,y,n))
            elif ID.startswith("3C"): out[trk]["3C"].append((x,y,n))
    return out


def choose_triplet(pool: Dict[str,List[Tuple[float,float,float]]], trk: str) -> Dict[str, Dict[str,float]]:
    """트랙 내에서 CO/1C/3C 하나씩 선택. 트랙의 방향성(R/L)에 맞게 1C.x와 CO.x 관계를 조정."""
    import math
    COs, C1s, C3s = pool.get("CO",[]), pool.get("1C",[]), pool.get("3C",[])
    if not (COs and C1s and C3s):
        raise RuntimeError("insufficient anchors to build a case")
    COx, COy, COn = random.choice(COs)

    if trk.endswith("_R"):
        # 1C.x > CO.x 인 것 우선 선택
        rights = [c for c in C1s if (c[0] - COx) > 0]
        C1x, C1y, C1n = random.choice(rights or C1s)
    else:
        lefts = [c for c in C1s if (c[0] - COx) <= 0]
        C1x, C1y, C1n = random.choice(lefts or C1s)

    C3x, C3y, C3n = random.choice(C3s)

    return {
        "CO": {"x": COx, "y": COy, "_sys": COn},
        "C1": {"x": C1x, "y": C1y, "_sys": C1n},
        "C3": {"x": C3x, "y": C3y, "_sys": C3n}
    }


def maybe_calc_HP(profile: Dict[str,Any], triplet: Dict[str,Dict[str,float]]) -> float | None:
    expr = profile.get("formula")
    if isinstance(expr, dict):
        expr = expr.get("expr")
    if not expr or expr == "REPLACE_ME":
        return None
    # 심볼 치환값 구성: 앵커 sys를 그대로 사용
    mapping = {
        "CO_f": triplet["CO"]["_sys"],
        "1C_f": triplet["C1"]["_sys"],
        "3C_r": triplet["C3"]["_sys"],
    }
    # 등장하는 토큰만 치환
    tokens = set(re.findall(r"\b(?:CO|[1-4]C)_(?:f|r)\b", expr))
    safe = expr
    for t in tokens:
        if t in mapping:
            safe = safe.replace(t, str(mapping[t]))
    try:
        return float(eval(safe, {"__builtins__": {}}, {}))
    except Exception:
        return None

# -------------- main --------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchors", required=True)
    ap.add_argument("--logic", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--per-track", type=int, default=3)
    ap.add_argument("--with-formula", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)

    anchors_doc = json.loads(Path(args.anchors).read_text(encoding="utf-8"))
    logic = json.loads(Path(args.logic).read_text(encoding="utf-8"))

    pools = parse_labels(anchors_doc)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    profile = {"formula": "REPLACE_ME"}
    prof_path_guess = Path(args.anchors).with_name("profile_" + Path(args.anchors).parent.name + ".json")
    if prof_path_guess.exists():
        try:
            profile = json.loads(prof_path_guess.read_text(encoding="utf-8"))
        except Exception:
            pass

    count = 0
    for trk in TRACKS:
        pool = pools.get(trk) or {}
        for i in range(args.per_track):
            try:
                trip = choose_triplet(pool, trk)
            except RuntimeError:
                continue
            expect = {"track": trk, "guards_ok": True}
            if args.with_formul
a:
                hp = maybe_calc_HP(profile, trip) if args.with_formula else None
                if hp is not None:
                    expect.setdefault("sys", {})["HP_n"] = hp
            case = {
                "name": f"auto_{trk}_{i+1:02d}",
                "input": {k: {"x": v["x"], "y": v["y"]} for k, v in trip.items()},
                "expect": expect
            }
            outpath = outdir / f"auto_{trk}_{i+1:02d}.json"
            outpath.write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")
            count += 1

    print(f"[OK] generated {count} cases at {outdir}")

if __name__ == "__main__":
    main()

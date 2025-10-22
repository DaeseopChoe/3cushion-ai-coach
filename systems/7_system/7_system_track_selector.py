#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
7_system_track_selector.py
- 7_system 트랙 자동 판정 + sys 계산 + 프로파일 연동(공식/좌표 규칙)
- 규약 v1.3: 계산은 sys만(_f/_r), 좌표는 표시/보간용

변경사항 (2025-09-22)
- 기본 공식(default) 을 7_system_base_manual의 규칙으로 교체:
  ▶ default formula: "1C_f = CO_f * 3C_f"
- '등식' 공식을 지원: 좌/우변을 각각 평가하고 오차(delta)를 보고
  * 좌변이 특정 항("1C_f" 등)일 경우 예측값(predicted)도 함께 출력

사용 예)
  python3 7_system_track_selector.py \
    --anchors /mnt/data/7_system_anchors.json \
    --co 40,-2.25 --c1 -2.25,20 --c3 82.25,20 \
    --profile /mnt/data/profile_7_system.json

우선순위)
  profile.formula > --formula(기본값: "1C_f = CO_f * 3C_f")
  profile.space_rule.frame_constants/tolerance 가 있으면 FG 상수/허용오차 갱신
"""

import argparse, json, pathlib, sys, math
from typing import Dict, Tuple, Any, List, Optional

# -----------------------------
# 기본 좌표 상수선(Fg) — 프로파일이 있으면 덮어씀
# -----------------------------
FG_CONSTS = {
    "BOTTOM": -2.25,
    "TOP": 42.25,
    "LEFT": -2.25,
    "RIGHT": 82.25,
}
TOL = 0.02

# -----------------------------
# 유틸 함수
# -----------------------------
def parse_coord(s: str) -> Tuple[float, float]:
    x, y = s.split(",")
    return float(x), float(y)

def nearly_eq(a: float, b: float, tol: float = None) -> bool:
    if tol is None:
        tol = TOL
    return abs(a - b) <= tol

# -----------------------------
# 프로파일 로더
# -----------------------------
def load_profile(path: str | None) -> Dict[str, Any] | None:
    if not path:
        return None
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"profile not found: {path}")
    doc = json.loads(p.read_text(encoding="utf-8"))

    # space_rule 반영: frame_constants, tolerance
    sr = doc.get("space_rule") or {}
    fc: List[float] = sr.get("frame_constants") or []
    tol = sr.get("tolerance")
    if isinstance(fc, list) and len(fc) >= 3:
        # 규약: [-2.25, 42.25, 82.25] (BOTTOM/LEFT, TOP, RIGHT)
        left_bottom = float(fc[0])
        top = float(fc[1])
        right = float(fc[2])
        FG_CONSTS.update({
            "BOTTOM": left_bottom,
            "LEFT": left_bottom,
            "TOP": top,
            "RIGHT": right,
        })
    if isinstance(tol, (int, float)):
        global TOL
        TOL = float(tol)

    return doc

# -----------------------------
# 트랙 판정
# -----------------------------
def detect_track(co: Tuple[float, float], c1: Tuple[float, float], c3: Tuple[float, float]) -> str:
    _, y_co = co
    x_c1, _ = c1
    x_c3, _ = c3

    if nearly_eq(y_co, FG_CONSTS["BOTTOM"]):
        if nearly_eq(x_c1, FG_CONSTS["LEFT"]) and nearly_eq(x_c3, FG_CONSTS["RIGHT"]):
            return "B2T_R"
        if nearly_eq(x_c1, FG_CONSTS["RIGHT"]) and nearly_eq(x_c3, FG_CONSTS["LEFT"]):
            return "B2T_L"
    if nearly_eq(y_co, FG_CONSTS["TOP"]):
        if nearly_eq(x_c1, FG_CONSTS["RIGHT"]) and nearly_eq(x_c3, FG_CONSTS["LEFT"]):
            return "T2B_R"
        if nearly_eq(x_c1, FG_CONSTS["LEFT"]) and nearly_eq(x_c3, FG_CONSTS["RIGHT"]):
            return "T2B_L"
    raise ValueError("트랙을 판정할 수 없습니다 (CO/1C/3C 좌표를 상수선에 맞춰 주세요)")

# -----------------------------
# 앵커 파싱 및 보간
# -----------------------------
def load_anchors(path: str) -> Dict[str, Any]:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))

def parse_anchor_id(anchor_id: str) -> Tuple[str, float, float, float]:
    # 예: "1C_(-2.25,20)_20"
    label, rest = anchor_id.split("_(")
    coords, sys_val = rest.split(")_")
    x, y = coords.split(",")
    return label, float(x), float(y), float(sys_val)

def build_axis_map(track_doc: Dict[str, Any], label: str) -> Tuple[List[float], List[float]]:
    pts: List[Tuple[float, float]] = []
    for a in track_doc["anchors"]:
        aid = a["id"]
        if not aid.startswith(label + "_"):
            continue
        _, x, y, sys_val = parse_anchor_id(aid)
        # x 또는 y가 frame const에 고정 -> 나머지 축 값으로 보간
        if nearly_eq(y, FG_CONSTS["BOTTOM"]) or nearly_eq(y, FG_CONSTS["TOP"]):
            pts.append((x, sys_val))
        else:
            pts.append((y, sys_val))
    if not pts:
        raise ValueError(f"앵커가 없습니다: {label}")
    pts.sort(key=lambda t: t[0])
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return xs, ys

def interp(val: float, xs: List[float], ys: List[float]) -> float:
    # clamp + 선형보간 (외삽 금지)
    if val <= xs[0]:
        return ys[0]
    if val >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= val <= xs[i+1]:
            x0, x1 = xs[i], xs[i+1]
            y0, y1 = ys[i], ys[i+1]
            if x1 == x0:
                return y0
            return y0 + (y1 - y0) * (val - x0) / (x1 - x0)
    raise ValueError("보간 실패")

# -----------------------------
# 공식 처리 (등식 및 표현식)
# -----------------------------
ALLOWED_VARS = ("CO_f", "1C_f", "3C_f", "3C_r")  # 3C_f/3C_r 모두 3C에 매핑

def eval_expr(expr: str, values: Dict[str, float]) -> float:
    env = {
        "CO_f": values["CO"],
        "1C_f": values["1C"],
        "3C_f": values["3C"],
        "3C_r": values["3C"],  # 호환용
        "abs": abs, "min": min, "max": max, "round": round,
    }
    return float(eval(expr, {"__builtins__": {}}, env))

def parse_equation(expr: str) -> Optional[Tuple[str, str]]:
    if "=" not in expr:
        return None
    lhs, rhs = expr.split("=", 1)
    return lhs.strip(), rhs.strip()

# -----------------------------
# 메인 계산
# -----------------------------
def compute(track: str, anchors: Dict[str, Any], co: Tuple[float,float], c1: Tuple[float,float], c3: Tuple[float,float], formula: str) -> Dict[str, Any]:
    tr = anchors["trajectories"][track]

    results: Dict[str, float] = {}
    for label, pos in zip(["CO","1C","3C"],[co,c1,c3]):
        xs, ys = build_axis_map(tr, label)
        # y가 TOP/BOTTOM 상수선이면 x축으로 보간, 아니면 y축 값으로 보간
        axis_val = pos[0] if (nearly_eq(pos[1], FG_CONSTS["BOTTOM"]) or nearly_eq(pos[1], FG_CONSTS["TOP"])) else pos[1]
        results[label] = interp(axis_val, xs, ys)

    out = {"track": track, "values": results, "formula": formula}

    eq = parse_equation(formula)
    if eq:
        lhs, rhs = eq
        lhs_val = eval_expr(lhs, results)
        rhs_val = eval_expr(rhs, results)
        out["consistency"] = {
            "lhs": lhs, "rhs": rhs,
            "lhs_value": lhs_val, "rhs_value": rhs_val,
            "delta": rhs_val - lhs_val,
            "ok": nearly_eq(lhs_val, rhs_val, tol=1e-6),
        }
        # 좌변이 특정 변수면 예측값 제공 (관례적으로 좌변이 종속변수)
        if lhs in ALLOWED_VARS:
            var_map = {"CO_f": "CO", "1C_f": "1C", "3C_f": "3C", "3C_r": "3C"}
            key = var_map[lhs]
            out["predicted"] = {key: rhs_val}
            out["error"] = {key: rhs_val - results[key]}
    else:
        # 등식이 아니라 단일 표현식이면 HP로 간주
        hp = eval_expr(formula, results)
        out["HP"] = hp

    return out

# -----------------------------
# CLI
# -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchors", required=True, help="anchors.json 경로")
    ap.add_argument("--co", required=True, help="예: 40,-2.25")
    ap.add_argument("--c1", required=True)
    ap.add_argument("--c3", required=True)
    ap.add_argument("--formula", default="1C_f = CO_f * 3C_f", help="공식(프로파일 없을 때 사용). 등식 또는 표현식")
    ap.add_argument("--profile", help="profile_*.json 경로 — formula 및 space_rule 반영")
    args = ap.parse_args()

    # 프로파일 로드 (있으면 FG_CONSTS/TOL 및 formula 갱신)
    profile = load_profile(args.profile)
    formula = (profile.get("formula") if profile and profile.get("formula") else args.formula)

    co = parse_coord(args.co)
    c1 = parse_coord(args.c1)
    c3 = parse_coord(args.c3)

    anchors = load_anchors(args.anchors)
    track = detect_track(co, c1, c3)
    out = compute(track, anchors, co, c1, c3, formula)

    # 메타(선택) 추가
    if profile:
        out.setdefault("meta", {})
        out["meta"]["profile_system"] = profile.get("system")
        out["meta"]["tolerance"] = TOL
        out["meta"]["frame_constants"] = {
            k: FG_CONSTS[k] for k in ("BOTTOM","TOP","LEFT","RIGHT")
        }

    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
